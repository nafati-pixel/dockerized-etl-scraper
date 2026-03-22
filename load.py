import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime

from Data_Base import async_session
from models import Product, ProductPricingHistory



logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


async def get_cleaned_data(filepath: Path | str) -> list[dict]:
    """
    Extracts and parses JSON records line-by-line from the target file.
    Corrupted lines are skipped to maintain pipeline execution.
    """
    data = []
    try:

        with open(filepath, "r", encoding="utf-8") as file:
            for line in file:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning(f"Skipping unparseable line: {e}")
        return data
    except FileNotFoundError:
        logger.error(f"Source file not found at path: {filepath}")
        return []


async def save_to_db(data: list[dict]) -> None:
    """
    Transforms parsed dictionary payloads into SQLAlchemy models
    and merges them into the database transactionally.
    """
    if not data:
        logger.warning("Empty dataset provided. Aborting database operation.")
        return

    try:
        async with async_session() as session:
            for item in data:
                try:

                    product = Product(
                        id=item["id"],
                        name=item["name"],
                        sku=item["sku"]
                    )
                    await session.merge(product)


                    date_obj = datetime.fromisoformat(item["date_posted"])
                    
                    price_history = ProductPricingHistory(
                        product_id=item["id"],
                        store_id=1,  
                        price=item["price"],
                        date_extracted=date_obj
                    )
                    await session.merge(price_history)

                except Exception as e:
                    logger.error(
                        f"Validation/Merge failed for item {item.get('id', 'Unknown')}: {e}"
                    )

            try:
                await session.commit()
                logger.info(
                    f"Successfully committed {len(data)} records to the database."
                )
            except Exception as e:
                logger.critical(f"Transaction commit failed: {e}")

    except Exception as e:
        logger.error(f"Failed to initialize database session: {e}")


async def main() -> None:
    BASE_DIR = Path(__file__).resolve().parent
    SOURCE_FILE = BASE_DIR / "clean_data.jsonl"

    logger.info("Getting the data...")
    scraped_data = await get_cleaned_data(SOURCE_FILE)
    
    if not scraped_data:
        logger.warning("No data found to load. Skipping DB insertion.")
        return

    logger.info(f"Found {len(scraped_data)} records.")
    logger.info("Initializing load phase...")
    await save_to_db(scraped_data)
    logger.info("Pipeline execution completed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process terminated by user.")
    except Exception as e:
        logger.critical(f"Fatal application error: {e}")
