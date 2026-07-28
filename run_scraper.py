import asyncio
import logging

from config import config
from scraper.driver.engine import AsynchronousScrapingEngine
from scraper.driver.registry import provision_parsing_strategy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)


async def main():
    try:
        strategy = provision_parsing_strategy("mytek")
        logging.info(f"Loaded strategy for: {strategy.retailer_identifier}")
    except ValueError as e:
        logging.error(e)
        return

    engine = AsynchronousScrapingEngine()

    logging.info(f"Starting extraction pipeline for {strategy.canonical_domain}...")
    await engine.execute_extraction_pipeline(
        strategy=strategy,
        expected_slug="mytek.tn",
        output_dir=str(config.scraper_save_path),
    )
    
    logging.info("Pipeline finished successfully.")


if __name__ == "__main__":
    asyncio.run(main())
