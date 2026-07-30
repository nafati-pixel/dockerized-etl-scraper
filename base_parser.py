import hashlib
import json
import logging
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Generic, Optional, Type, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from selectolax.parser import HTMLParser, Node

from config import config

logger = logging.getLogger(__name__)


# Core Data Structures
T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True, slots=True)
class RawPayload:
    """Immutable DTO transferred from the Extraction (E) engine to Transform (T)."""
    url: str
    content: str
    status_code: int
    fetched_at: datetime


@dataclass(frozen=True, slots=True)
class TransformResult(Generic[T]):
    """Returns execution metrics (success vs failure counts) for the runner."""
    successful_items: list[T]
    failed_count: int
    url: str


class ProductData(BaseModel):
    """The strict domain data contract."""
    model_config = ConfigDict(strict=True)

    url: str
    title: str = Field(..., min_length=2)
    price: float
    stock_status: Optional[str] = None


# Abstract Base Transformer
class BasePlatformTransformer(ABC, Generic[T]):
    """
    Template Method Strategy.
    Handles error boundaries, DLQ fallbacks, and item-level validation centrally.
    Subclasses ONLY implement parsing rules for their specific target DOM.
    """

    @property
    @abstractmethod
    def retailer_identifier(self) -> str:
        """Unique retailer tag (e.g., 'mytek', 'scoop')."""
        pass

    @property
    @abstractmethod
    def target_schema(self) -> Type[T]:
        """Binds the Base Class to a specific Pydantic model for validation."""
        pass

    def transform(self, payload: RawPayload) -> TransformResult[T]:
        """Item-level fault tolerance: saves good items, DLQs bad ones."""
        try:
            # Parse HTML (throws exception if DOM is fundamentally broken)
            raw_items = self._parse_html(payload.content)
        except Exception as err:
            logger.error(f"[{self.retailer_identifier}] DOM parsing crashed for {payload.url}")
            self._dump_to_dlq(payload, err, context="DOM_PARSING_FAILED")
            raise err

        successful_items: list[T] = []
        item_errors: list[dict[str, Any]] = []

        # Item-Level Validation (preserves partial batch success)
        for index, item in enumerate(raw_items):
            if "url" not in item:
                item["url"] = payload.url

            try:
                validated_item = self.target_schema(**item)
                successful_items.append(validated_item)
            except ValidationError as err:
                item_errors.append({
                    "index": index,
                    "data": item,
                    "errors": err.errors()
                })

        # Handle Partial Failures
        if item_errors:
            logger.warning(
                f"[{self.retailer_identifier}] Partial failure on {payload.url}: "
                f"{len(item_errors)} items failed validation."
            )
            self._dump_to_dlq(payload, ValueError("Partial Validation Failure"), item_errors)

        return TransformResult(
            successful_items=successful_items,
            failed_count=len(item_errors),
            url=payload.url
        )

    @abstractmethod
    def _parse_html(self, raw_html: str) -> list[dict[str, Any]]:
        """Extracts raw dictionaries from HTML using Selectolax."""
        pass

    # Helper Utilities
    @staticmethod
    def _get_text(node: Optional[Node], default: str = "") -> str:
        """Safe extraction: prevents AttributeError if the HTML node is missing."""
        if node is None:
            return default
        return node.text(strip=True)

    def _dump_to_dlq(self, payload: RawPayload, error: Exception, context: Any = None) -> None:
        """Centralized Dead Letter Queue persistence with collision-proof naming."""
        timestamp = payload.fetched_at.strftime("%Y%m%d_%H%M%S")
        url_hash = hashlib.md5(payload.url.encode()).hexdigest()[:8]
        base_name = f"failed_{self.retailer_identifier}_{timestamp}_{url_hash}"

        # Save Raw HTML
        html_path = config.scraper_save_path / f"{base_name}.html"
        html_path.write_text(payload.content, encoding="utf-8")

        # Save Failure Metadata
        meta_path = config.scraper_save_path / f"{base_name}_meta.json"
        error_details = str(error)

        metadata = {
            "retailer": self.retailer_identifier,
            "url": payload.url,
            "status_code": payload.status_code,
            "error_type": type(error).__name__,
            "error_details": error_details,
            "extra_context": context,
            "traceback": traceback.format_exc(),
        }
        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


# Platform Implementation
class MyTekTransformer(BasePlatformTransformer[ProductData]):
    """MyTek specific implementation bound strictly to ProductData."""

    @property
    def retailer_identifier(self) -> str:
        return "mytek"

    @property
    def target_schema(self) -> Type[ProductData]:
        return ProductData

    def _parse_html(self, raw_html: str) -> list[dict[str, Any]]:
        tree = HTMLParser(raw_html)
        products = []
        
        nodes = tree.css(".product-item-info") or [tree]

        for node in nodes:
            title_node = node.css_first("h1.page-title span, a.product-item-link")
            price_node = node.css_first("span.price")
            stock_node = node.css_first("div.stock span")

            if title_node and price_node:
                products.append({
                    "title": self._get_text(title_node),
                    "price": self._clean_price(self._get_text(price_node)),
                    "stock_status": self._get_text(stock_node, default="In Stock"),
                })

        return products

    @staticmethod
    def _clean_price(raw_price: str) -> float:
        """Cleans MyTek price strings: '1 499,00 TND' -> 1499.00"""
        if not raw_price:
            return 0.0
        
        clean_str = raw_price.replace("TND", "").replace("DT", "").replace(" ", "").replace(",", ".")
        try:
            return float(clean_str)
        except ValueError:
            return 0.0
