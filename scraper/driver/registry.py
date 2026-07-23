from typing import Type
from driver.interface import BaseWebsiteParser
from driver.platforms.mytek import MyTekAPIParser


SCRAPERS: dict[str, Type[BaseWebsiteParser]] = {
    "mytek": MyTekAPIParser,
}

def get_scraper(name: str) -> BaseWebsiteParser:
    scraper_class = SCRAPERS.get(name.lower())
    if not scraper_class:
        raise ValueError(
            f"Scraper '{name}' is not registered. Available scrapers: {list(SCRAPERS.keys())}"
        )
    return scraper_class()
