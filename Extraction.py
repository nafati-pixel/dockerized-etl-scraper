import asyncio
import json
import logging
import random
import time
from datetime import datetime
from pathlib import Path
import httpx
from seleniumwire import webdriver

# --- CONFIGURATION & LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

PROXIES = ["http://proxy1.com:8080", "http://proxy2.com:8080"]
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/537.36",
]

def get_random_identity():
    return {"user_agent": random.choice(USER_AGENTS), "proxy": random.choice(PROXIES)}

# --- PHASE 1: THE Extraction ---
def get_dynamic_api_url():

    """"opens a web page in the background in order to find the right api to call to get the data""""

    logging.info("Initializing Selenium Wire...")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    try:
        driver = webdriver.Chrome(options=options)
        target_page = "https://www.mytek.tn/informatique/composants-informatique/barrettes-memoire.html"
        driver.set_page_load_timeout(55)
        driver.get(target_page)
        
        time.sleep(5)

        static_base = "opensearch_api/api/productData?ids="
        found_url = None

        for request in driver.requests:
            if request.response and static_base in request.url:
                found_url = request.url
                break

        driver.quit()
        return found_url
    except Exception as e:
        logging.error(f"extraction Error: {e}")
        return None

# --- PHASE 2: THE REQUEST ---
async def fetch_product_data(client, url):
    identity = get_random_identity()
    headers = {"User-Agent": identity["user_agent"], "Accept": "application/json"}
    response = await client.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

# --- THE ENGINE: RUN ONCE ---
async def run_extraction_task(urls):

    """ Extracts data and saves it to messy_data.jsonl. """

    if not urls:
        logging.warning("No URLs provided to extraction task.")
        return

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            logging.info(f"Starting Extraction for {len(urls)} target(s)...")
            tasks = [fetch_product_data(client, u) for u in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            BASE_DIR = Path(__file__).resolve().parent
            file_path = BASE_DIR / "messy_data.jsonl"
            
            data_written = 0
            with open(file_path, "w", encoding="utf-8") as f:
                for i, data in enumerate(results):
                    if isinstance(data, Exception):
                        logging.error(f"Task {i} failed: {data}")
                        continue
                    
                    record = {
                        "extracted_at": datetime.utcnow().isoformat(),
                        "source_url": urls[i],
                        "raw_payload": data,
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    data_written += 1
                
                f.flush()
            
            if data_written > 0:
                logging.info(f"Successfully saved {data_written} records to {file_path}")
            else:
                logging.error("No data was successfully extracted to save.")

        except Exception as e:
            logging.critical(f"Extraction Engine Failure: {e}")
            raise

if __name__ == "__main__":
    # Test block
    url = get_dynamic_api_url()
    if url:
        asyncio.run(run_extraction_task([url]))
