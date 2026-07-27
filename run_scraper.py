import asyncio
import logging
from pathlib import Path

from scraper.driver.engine import AsynchronousScrapingEngine
from scraper.driver.registry import provision_parsing_strategy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

async def main():
    # 1. Provision the MyTek extraction strategy
    try:
        strategy = provision_parsing_strategy("mytek")
        logging.info(f"Loaded strategy for: {strategy.retailer_identifier}")
    except ValueError as e:
        logging.error(e)
        return

    # 2. Initialize the Engine
    engine = AsynchronousScrapingEngine()

    # 3. Define where raw HTML payloads should be saved
    output_directory = Path("./data/raw/mytek")
    output_directory.mkdir(parents=True, exist_ok=True)

    # 4. Execute the pipeline
    logging.info(f"Starting extraction pipeline for {strategy.canonical_domain}...")
    await engine.execute_extraction_pipeline(
        strategy=strategy,
        expected_slug="mytek.tn",
        output_dir=str(output_directory)
    )
    
    logging.info("Pipeline finished successfully.")

if __name__ == "__main__":
    asyncio.run(main())
