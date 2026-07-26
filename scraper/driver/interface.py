"""Domain contracts for platform-specific extraction strategies."""

from abc import ABC, abstractmethod
from typing import Any


class RetailerParsingStrategy(ABC):
    """
    Contract enforcing the Strategy Pattern for platform-specific parsing.
    Every retailer extraction algorithm must strictly implement this interface.
    """

    @property
    @abstractmethod
    def retailer_identifier(self) -> str:
        """Human-readable identifier for this domain entity (e.g. 'mytek')."""

    @property
    @abstractmethod
    def entry_point_url(self) -> str:
        """The foundational URL for initializing the category traversal."""

    @property
    @abstractmethod
    def canonical_domain(self) -> str:
        """Root domain (e.g. 'https://www.mytek.tn') used for resolving relative URIs."""

    @abstractmethod
    def extract_product_entities(self, raw_html_payload: str) -> list[dict[str, Any]]:
        """
        Parses DOM nodes from a raw HTML payload into standardized domain dictionaries.
        Must yield entities containing at minimum: 'name', 'price', and 'product_url'.
        """

    @abstractmethod
    def resolve_pagination_target(self, raw_html_payload: str) -> str | None:
        """Calculates and returns the absolute URI for the next sequential page, or None."""
