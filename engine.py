"""Asynchronous network orchestration engine and payload management."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Tuple

from bs4 import BeautifulSoup, SoupStrainer
from curl_cffi.requests import AsyncSession
from curl_cffi.requests.errors import RequestsError

from config import DEFAULT_HEADERS, MAX_CONCURRENT_REQUESTS, MAX_RETRIES, TIMEOUT_SECONDS
from transformer import RawPayload

if TYPE_CHECKING:
    # Assuming your strategy now inherits from our new BasePlatformTransformer
    from transformer import BasePlatformTransformer

logger = logging.getLogger(__name__)

# Optimize BeautifulSoup parsing to avoid building full ASTs
_CANONICAL_STRAINER = SoupStrainer("link", rel="canonical")


def _verify_canonical_slug(raw_html: str, expected_slug: str) -> bool:
    """Safely verifies the canonical URL integrity to detect bot-blocking redirects."""
    if not raw_html:
        return False
        
    # parse_only forces bs4 to ignore the rest of the DOM, saving massive CPU/Memory
    soup = BeautifulSoup(raw_html, "lxml", parse_only=_CANONICAL_STRAINER)
    canonical_tag = soup.find("link", rel="canonical")
    
    if not canonical_tag:
        return False
        
    return expected_slug in canonical_tag.get("href", "")


class AsynchronousScrapingEngine:
    """
    Enterprise network orchestrator. 
    Handles concurrency semaphores, TLS-fingerprint impersonation, and robust fault tolerance.
    """

    def __init__(self) -> None:
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        self.max_retries = MAX_RETRIES
        self.timeout = TIMEOUT_SECONDS

    async def fetch_network_payload(self, session: AsyncSession, target_url: str) -> Tuple[str | None, int]:
        """
        Executes a rate-limited, fault-tolerant HTTP request with exponential backoff.
        Returns: (HTML Content, HTTP Status Code)
        """
        async with self.semaphore:
            for attempt in range(1, self.max_retries + 1):
                try:
                    logger.info(f"Dispatching [attempt {attempt}/{self.max_retries}]: {target_url}")
                    
                    response = await session.get(
                        target_url, 
                        timeout=self.timeout, 
                        headers=DEFAULT_HEADERS
                    )

                    if response.status_code == 200:
                        return response.text, response.status_code

                    logger.warning(f"Unexpected HTTP {response.status_code} for {target_url}")
                    # Capture the failing status code so it can be logged in the DLQ later
                    return response.text, response.status_code

                except RequestsError as e:
                    logger.error(f"Network transport error on attempt {attempt} for {target_url}: {e}")
                except Exception as e:
                    logger.critical(f"Unhandled fault on attempt {attempt} for {target_url}: {e}")

                await asyncio.sleep(attempt * 1.5)

            logger.error(f"Exhausted all {self.max_retries} connection attempts for: {target_url}")
            return None, 0

    async def execute_extraction_pipeline(
        self,
        strategy: "BasePlatformTransformer",
        expected_slug: str
    ) -> None:
        """
        Orchestrates the full temporal pagination sequence.
        Streams data directly in-memory to the Transform layer.
        """
        # Assuming your strategy still defines the starting URL
        active_url: str | None = getattr(strategy, "entry_point_url", None)
        sequence_number = 1

        # Impersonate modern Chrome architecture to evade WAFs
        async with AsyncSession(impersonate="chrome120") as session:
            while active_url:
                
                # 1. Network Fetch Layer
                html_payload, status_code = await self.fetch_network_payload(session, active_url)
                if not html_payload or status_code != 200:
                    logger.warning(f"Pipeline halting: Unrecoverable network failure at sequence {sequence_number}.")
                    break

                # 2. Validation Layer - Offloaded to a thread to prevent blocking on large DOMs
                is_valid = await asyncio.to_thread(_verify_canonical_slug, html_payload, expected_slug)
                if not is_valid:
                    logger.error(f"Integrity check failed for {active_url}. Suspected bot-block redirect.")
                    break

                # 3. Build the Immutable In-Memory Payload
                payload_dto = RawPayload(
                    url=active_url,
                    content=html_payload,
                    status_code=status_code,
                    fetched_at=datetime.now()
                )

                # 4. Transform & Load Layer (Handles its own DLQ if it crashes)
                logger.info(f"Passing sequence {sequence_number} to {strategy.retailer_identifier} transformer...")
                transform_result = strategy.transform(payload_dto)
                
                logger.info(
                    f"Sequence {sequence_number} results: {len(transform_result.successful_items)} succeeded, "
                    f"{transform_result.failed_count} failed."
                )

                # 5. Pagination Resolution
                # Note: Ensure your new Transformer class has this method ported over from the old strategy
                active_url = strategy.resolve_pagination_target(html_payload)
                sequence_number += 1

                if active_url:
                    await asyncio.sleep(1.0)

        logger.info(f"Extraction pipeline terminated for domain '{strategy.retailer_identifier}'.")
