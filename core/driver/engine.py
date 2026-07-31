"""Asynchronous network orchestration engine and payload management."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup, SoupStrainer
from curl_cffi.requests import AsyncSession
from curl_cffi.requests.errors import RequestsError

from config import DEFAULT_HEADERS, MAX_CONCURRENT_REQUESTS, MAX_RETRIES, TIMEOUT_SECONDS

if TYPE_CHECKING:
    from .interface import RetailerParsingStrategy

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


def _is_payload_cached(output_directory: Path, sequence_number: int) -> bool:
    """Checks if a validated network payload already exists in the local filesystem."""
    target_path = output_directory / f"raw_payload_{sequence_number}.html"
    return target_path.exists()


def _persist_html_payload(raw_html: str, output_directory: Path, sequence_number: int) -> Path:
    """Safely writes a raw HTML payload to disk, resolving strict sandbox boundaries."""
    output_directory.mkdir(parents=True, exist_ok=True)
    
    # Path.resolve() guards against directory climbing injections (../)
    secure_filepath = (output_directory / f"raw_payload_{sequence_number}.html").resolve()
    
    with secure_filepath.open("w", encoding="utf-8") as file_handler:
        file_handler.write(raw_html)
        
    return secure_filepath


def _read_cached_payload(output_directory: Path, sequence_number: int) -> str:
    """Reads a previously persisted payload from the local sandbox."""
    secure_filepath = (output_directory / f"raw_payload_{sequence_number}.html").resolve()
    
    with secure_filepath.open("r", encoding="utf-8") as file_handler:
        return file_handler.read()


class AsynchronousScrapingEngine:
    """
    Enterprise network orchestrator. 
    Handles concurrency semaphores, TLS-fingerprint impersonation, and robust fault tolerance.
    """

    def __init__(self) -> None:
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        self.max_retries = MAX_RETRIES
        self.timeout = TIMEOUT_SECONDS

    async def fetch_network_payload(self, session: AsyncSession, target_url: str) -> str | None:
        """Executes a rate-limited, fault-tolerant HTTP request with exponential backoff."""
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
                        return response.text

                    logger.warning(f"Unexpected HTTP {response.status_code} for {target_url}")

                except RequestsError as e:
                    logger.error(f"Network transport error on attempt {attempt} for {target_url}: {e}")
                except Exception as e:
                    logger.critical(f"Unhandled fault on attempt {attempt} for {target_url}: {e}")

                await asyncio.sleep(attempt * 1.5)

            logger.error(f"Exhausted all {self.max_retries} connection attempts for: {target_url}")
            return None

    async def execute_extraction_pipeline(
        self,
        strategy: RetailerParsingStrategy,
        expected_slug: str,
        output_dir: str,
    ) -> None:
        """
        Orchestrates the full temporal pagination sequence.
        Offloads blocking file I/O to worker threads to protect the async event loop.
        """
        active_url: str | None = strategy.entry_point_url
        sequence_number = 1
        sandbox_path = Path(output_dir).resolve()

        # Impersonate modern Chrome architecture to evade WAFs
        async with AsyncSession(impersonate="chrome120") as session:
            while active_url:
                # 1. Cache Layer Check - Offloaded to a thread
                is_cached = await asyncio.to_thread(_is_payload_cached, sandbox_path, sequence_number)
                
                if is_cached:
                    logger.info(f"Sequence {sequence_number} located in cache, bypassing network.")
                    html_payload = await asyncio.to_thread(
                        _read_cached_payload, sandbox_path, sequence_number
                    )
                    active_url = strategy.resolve_pagination_target(html_payload)
                    sequence_number += 1
                    continue

                # 2. Network Fetch Layer
                html_payload = await self.fetch_network_payload(session, active_url)
                if not html_payload:
                    logger.warning(f"Pipeline halting: Unrecoverable network failure at sequence {sequence_number}.")
                    break

                # 3. Validation Layer - Offloaded to a thread to prevent blocking on large DOMs
                is_valid = await asyncio.to_thread(_verify_canonical_slug, html_payload, expected_slug)
                if not is_valid:
                    logger.error(f"Integrity check failed for {active_url}. Suspected bot-block redirect.")
                    break

                # 4. Persistence Layer - Offloaded to a thread
                await asyncio.to_thread(
                    _persist_html_payload, html_payload, sandbox_path, sequence_number
                )
                logger.info(f"Successfully persisted payload for sequence {sequence_number}.")

                # 5. Pagination Resolution
                active_url = strategy.resolve_pagination_target(html_payload)
                sequence_number += 1

                if active_url:
                    await asyncio.sleep(1.0)

        logger.info(f"Extraction pipeline terminated for domain '{strategy.retailer_identifier}'.")
