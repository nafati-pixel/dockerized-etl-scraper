from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING, Optional
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession

import config

if TYPE_CHECKING:
    from driver.interface import BaseWebsiteParser

logger = logging.getLogger(__name__)

# --- Utility Functions ---

def is_valid_page(raw_html: str, expected_slug: str) -> bool:
    """Verifies the canonical link matches the expected category slug."""
    if not raw_html:
        return False
        
    soup = BeautifulSoup(raw_html, "lxml")
    canonical_tag = soup.find("link", rel="canonical")
    
    if not canonical_tag:
        return False
        
    return expected_slug in canonical_tag.get("href", "")

def is_page_downloaded(output_dir: str, page_number: int) -> bool:
    """Checks if a page's HTML file already exists."""
    filepath = os.path.join(output_dir, f"raw_page_{page_number}.html")
    return os.path.exists(filepath)

def save_raw_html(raw_html: str, output_dir: str, page_number: int) -> str:
    """Saves the unparsed HTML to a file."""
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"raw_page_{page_number}.html")
    
    with open(filepath, "w", encoding="utf-8") as file:
        file.write(raw_html)
        
    return filepath

# --- Scraper Engine ---

class ScraperEngine:
    """
    Asynchronous network engine responsible for fetching web pages,
    enforcing concurrency limits, executing retries, and controlling pagination.
    """

    def __init__(self):
        self.semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_REQUESTS)
        self.max_retries = config.MAX_RETRIES
        self.timeout = config.TIMEOUT_SECONDS

    async def fetch_html(self, session: AsyncSession, url: str) -> Optional[str]:
        """Fetches a single URL with rate-limiting and backoff retries."""
        async with self.semaphore:
            for attempt in range(1, self.max_retries + 1):
                try:
                    logger.info(f"Fetching [Attempt {attempt}/{self.max_retries}]: {url}")
                    
                    response = await session.get(
                        url,
                        timeout=self.timeout,
                        headers=config.DEFAULT_HEADERS,
                    )

                    if response.status_code == 200:
                        return response.text
                    
                    logger.warning(
                        f"Non-200 HTTP status ({response.status_code}) received for {url}"
                    )

                except Exception as err:
                    logger.error(f"Network error on attempt {attempt} for {url}: {err}")

                # Exponential backoff delay 
                await asyncio.sleep(attempt * 1.5)

            logger.error(f"Exhausted retries. Failed to retrieve: {url}")
            return None

    async def run(self, parser: BaseWebsiteParser, expected_slug: str, output_dir: str) -> None:
        """
        Executes the extraction loop for any platform parser.
        Saves raw HTML to disk and handles pagination.
        """
        next_url: Optional[str] = parser.start_url
        page_number = 1

        async with AsyncSession(impersonate="chrome120") as session:
            while next_url:
                # Checkpoint: Skip network request if already downloaded
                if is_page_downloaded(output_dir, page_number):
                    logger.info(f"Page {page_number} already downloaded. Skipping network request.")
                    
                    # Read the local file to find the next page URL
                    with open(os.path.join(output_dir, f"raw_page_{page_number}.html"), "r", encoding="utf-8") as f:
                        html = f.read()
                        
                    next_url = parser.get_next_page_url(html)
                    page_number += 1
                    continue

                # Fetch from network
                html = await self.fetch_html(session, next_url)
                if not html:
                    logger.warning(f"Stopping crawl loop due to fetch error at {next_url}")
                    break

                # Validate
                if not is_valid_page(html, expected_slug):
                    logger.error(f"Validation failed for {next_url}. Possible redirect or bot challenge.")
                    break

                # Save raw data (The 'L' in ELT)
                save_raw_html(html, output_dir, page_number)
                logger.info(f"Successfully saved raw HTML for page {page_number}.")

                # Fetch next page URL from parser
                next_url = parser.get_next_page_url(html)
                page_number += 1

                if next_url:
                    await asyncio.sleep(1.0)

        logger.info(f"Completed raw HTML extraction for '{parser.provider_name}'.")
