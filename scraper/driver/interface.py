from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseWebsiteParser(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identifier for the retail origin (e.g., 'mytek')."""
        pass

    @property
    @abstractmethod
    def start_url(self) -> str:
        """The entry-point URL to begin the extraction loop."""
        pass

    @property
    @abstractmethod
    def base_domain(self) -> str:
        """
        The root domain (e.g., 'https://www.mytek.tn').
        Required to resolve relative href links extracted from the DOM.
        """
        pass

    @abstractmethod
    def extract_raw_records(self, raw_html: str) -> List[Dict[str, Any]]:
        """
        Extracts item nodes into dictionaries. 
        Mandatory keys: 'name', 'price', 'product_url'
        """
        pass

    @abstractmethod
    def get_next_page_url(self, raw_html: str) -> Optional[str]:
        """
        Parses the DOM for the 'Next Page' button.
        Returns the absolute URL string, or None if it is the last page.
        """
        pass
