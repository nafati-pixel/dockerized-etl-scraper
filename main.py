import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

from curl_cffi.requests import AsyncSession

from engine import AsynchronousScrapingEngine
from registry import _STRATEGY_REGISTRY, provision_parsing_strategy
from transformer import RawPayload

# Configure structured stream logging for stdout runtime tracking
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Scraper")


async def main() -> None:
    """
    Master orchestration loop. Iterates over registered retailer strategies,
    executing the full Extract-Transform-Load (ETL) pipeline page-by-page.
    """
    targets = list(_STRATEGY_REGISTRY.keys())
    
    # Local buffer directory for streaming parsed output without database overhead
    temp_dir = Path("./temp_output")
    temp_dir.mkdir(parents=True, exist_ok=True)

    for retailer in targets:
        try:
            strategy, scraper_config = provision_parsing_strategy(retailer)
            engine = AsynchronousScrapingEngine(
                concurrency=scraper_config.concurrency_limit,
                request_delay=scraper_config.request_delay,
            )

            output_file = temp_dir / f"temp_{retailer}_products.jsonl"
            logger.info(f"Starting ETL pipeline for: '{retailer}' -> Output: {output_file}")

            async with AsyncSession(impersonate="chrome120") as session:
                target_url = strategy.entry_point_url
                page_count = 0

                # Open target file in append mode to write incremental records per page
                with open(output_file, "a", encoding="utf-8") as f:
                    while target_url and page_count < 50:
                        page_count += 1

                        # EXTRACT: Fetch HTML network payload via curl_cffi
                        html, status_code = await engine.fetch_network_payload(session, target_url)
                        if not html or status_code != 200:
                            logger.error(f"[E] Extraction failed at {target_url}")
                            break

                        raw_payload = RawPayload(
                            url=target_url,
                            content=html,
                            status_code=status_code,
                            fetched_at=datetime.now(),
                        )

                        # TRANSFORM: Parse DOM & validate into Pydantic models
                        transform_result = strategy.transform(raw_payload)
                        logger.info(
                            f"[T] Transformed {len(transform_result.successful_items)} records "
                            f"({transform_result.failed_count} failures logged to DLQ)"
                        )

                        # Stream validated JSON lines to local disk
                        if transform_result.successful_items:
                            for item in transform_result.successful_items:
                                f.write(item.model_dump_json() + "\n")
                            f.flush()  # Force OS buffer write to prevent data loss on crash
                            logger.info(f"[L] Loaded {len(transform_result.successful_items)} items to {output_file.name}")

                        # Resolve pagination target anchor for next iteration
                        target_url = strategy.resolve_pagination_target(html)
                        if target_url and scraper_config.request_delay > 0:
                            await asyncio.sleep(scraper_config.request_delay)

        except Exception as err:
            logger.critical(f"Fatal error in pipeline for '{retailer}': {err}", exc_info=True)


if __name__ == "__main__":
    # Windows Bug Fix: Python 3.8+ on Windows defaults to ProactorEventLoop, which causes 
    # asynchronous socket driver conflicts with curl_cffi's underlying C-bindings (libcurl).
    # Explicitly setting WindowsSelectorEventLoopPolicy restores selector-based loop compatibility.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Pipeline execution interrupted by user.")
