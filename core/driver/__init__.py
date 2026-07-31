"""
Core extraction engine, parsing strategies, and registry.
Exposes a clean public API for orchestrating asynchronous web scraping.
"""

from .engine import AsynchronousScrapingEngine
from .interface import RetailerParsingStrategy
from .registry import provision_parsing_strategy

__all__ = [
    "AsynchronousScrapingEngine",
    "RetailerParsingStrategy",
    "provision_parsing_strategy",
]
