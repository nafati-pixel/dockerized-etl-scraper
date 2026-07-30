import hashlib
import json
import logging
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from selectolax.parser import HTMLParser, Node

from config import config

logger = logging.getLogger(__name__)


# 1. The memory-optimized Data Transfer Object (DTO)
@dataclass(frozen=True, slots=True)
class RawPayload:
    url: str
    content: str
    status_code: int
    fetched_at: datetime


# 2. The Data Contract: Enforces strict rules on what valid data looks like
class ProductData(BaseModel):
    model_config = ConfigDict(strict=True)

    url: str
    title: str = Field(..., min_length=2)
    price: float
    stock_status: Optional[str] = None


# 3. The Transform Engine
class ProductTransformer:
    
    def transform(self, payload: RawPayload) -> ProductData:
        """Main pipeline entry point: Parse -> Validate -> Return or DLQ."""
        try:
            # Step A: Parse raw HTML into a raw dictionary
            raw_dict = self._parse_html(payload.content)
            raw_dict["url"] = payload.url
            
            # Step B: Validate the dictionary against our strict Pydantic rules
            validated_data = ProductData(**raw_dict)
            return validated_data

        except Exception as err:
            logger.error(
                f"Transformation failed for {payload.url}: {type(err).__name__}. "
                f"Dumping to DLQ."
            )
            self._dump_to_dlq(payload, err)
            raise err  # Re-raise so the runner knows this item failed

    def _parse_html(self, raw_html: str) -> dict:
        """Uses Selectolax C-engine for extreme speed."""
        tree = HTMLParser(raw_html)
        
        # Example CSS Selectors - Adjust to your target site
        title_node = tree.css_first("h1.product-title")
        price_node = tree.css_first("span.price-current")
        stock_node = tree.css_first("div.stock-badge")

        return {
            "title": self._get_text(title_node, default=""),
            "price": self._clean_price(self._get_text(price_node, default="0")),
            "stock_status": self._get_text(stock_node, default="Unknown")
        }

    @staticmethod
    def _get_text(node: Optional[Node], default: str = "") -> str:
        """Safe extraction: prevents AttributeError if the HTML node is missing."""
        if node is None:
            return default
        return node.text(strip=True)

    @staticmethod
    def _clean_price(raw_price: str) -> float:
        """Converts extracted string like '1 499,00 TND' into a clean float."""
        clean_str = raw_price.replace("TND", "").replace(" ", "").replace(",", ".")
        try:
            return float(clean_str)
        except ValueError:
            return 0.0

    def _dump_to_dlq(self, payload: RawPayload, error: Exception) -> None:
        """Saves unparseable HTML and a detailed Error JSON to disk."""
        timestamp = payload.fetched_at.strftime('%Y%m%d_%H%M%S')
        # Hash the URL to prevent filename collisions during concurrent runs
        url_hash = hashlib.md5(payload.url.encode()).hexdigest()[:8]
        base_name = f"failed_{timestamp}_{url_hash}"
        
        # 1. Save the raw HTML payload
        html_path = config.scraper_save_path / f"{base_name}.html"
        html_path.write_text(payload.content, encoding="utf-8")
        
        # 2. Save the debug context (Why it failed)
        meta_path = config.scraper_save_path / f"{base_name}_meta.json"
        
        # Differentiate between bad HTML layout vs. Pydantic validation failures
        error_details = str(error)
        if isinstance(error, ValidationError):
            error_details = error.errors()

        metadata = {
            "url": payload.url,
            "status_code": payload.status_code,
            "error_type": type(error).__name__,
            "error_details": error_details,
            "traceback": traceback.format_exc()
        }
        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

def resolve_pagination_target(self, raw_html: str) -> str | None:
        """Finds the 'Next Page' button. Returns the URL or None if last page."""
        tree = HTMLParser(raw_html)
        next_button = tree.css_first("a.next.pages-item-next")
        if next_button:
            return next_button.attributes.get("href")
        return None
