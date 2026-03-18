import sys
import logging
import asyncio
import random
from pathlib import Path
from Extraction import get_dynamic_api_url, run_extraction_task
from Transformation import process_and_cleanup
from load import main as load_to_db

# --- SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

BASE_DIR = Path(__file__).resolve().parent

async def pipeline_cycle():
    """Runs one complete cycle of Extract, Transform, and Load."""
    logging.info("--- Starting New ETL Cycle ---")

    # PHASE 1: DISCOVERY
    logging.info("Phase 1: Intercepting Dynamic API URL...")
    dynamic_url = get_dynamic_api_url() 
    if not dynamic_url:
        logging.error("Could not find source URL. Skipping this cycle.")
        return False

    # PHASE 2: EXTRACTION
    logging.info("Phase 2: Extracting data...")
    try:
        await run_extraction_task([dynamic_url])
    except Exception as e:
        logging.error(f"Extraction Failed: {e}")
        return False

    # PHASE 3: TRANSFORMATION
    logging.info("Phase 3: Cleaning Data...")
    SOURCE_FILE = BASE_DIR / "messy_data.jsonl"
    FINAL_CLEAN_FILE = BASE_DIR / "clean_data.jsonl"
    try:
        process_and_cleanup(str(SOURCE_FILE), str(FINAL_CLEAN_FILE))
    except Exception as e:
        logging.error(f"Transformation Error: {e}")
        return False

    # PHASE 4: LOAD
    logging.info("Phase 4: Loading Data into Database...")
    try:
        await load_to_db()
    except Exception as e:
        logging.error(f"Database Load Error: {e}")
        return False

    return True

async def main():
    # This is the heartbeat of your 24/7 scraper.
    while True:
        success = await pipeline_cycle()
        
        if success:
            logging.info("Cycle completed successfully.")
        else:
            logging.warning("Cycle failed, but keeping the system alive.")

        # --- THE RANDOM 5 TO 12 HOUR SLEEP ---
        wait_time = random.uniform(18000, 43200) 
        logging.info(f"Going to sleep for {wait_time / 3600:.2f} hours. See you soon...")
        await asyncio.sleep(wait_time)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("System killed manually by user.")
    except Exception as e:
        logging.critical(f"Fatal System Error: {e}")
