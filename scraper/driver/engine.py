import asyncio
import logging
import random
import json
from datetime import datetime
from typing import List, Dict, Any
from curl_cffi import requests
from scraper.platforms.mytek import MyTekParser

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

class ExtractionEngine:
    def __init__(self, max_concurrent: int = 2):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }

    async def fetch_page(self, session: requests.AsyncSession, url: str, retries: int = 3) -> str:
        for attempt in range(retries):
            try:
                response = await session.get(url, impersonate="chrome120", headers=self.headers, timeout=15.0)
                
                if response.status_code == 200:
                    return response.text
                elif response.status_code in (429, 503, 504):
                    logging.warning(f"Rate limited/error ({response.status_code}) on {url}. Retrying...")
                    await asyncio.sleep(2 ** attempt)
                else:
                    logging.error(f"Failed {url} with status {response.status_code}")
                    return ""
            except Exception as e:
                logging.error(f"Network error on {url}: {e}")
                await asyncio.sleep(2 ** attempt)
                
        return ""

    async def scrape_category(self, parser: MyTekParser, session: requests.AsyncSession, category: str, start_url: str) -> List[Dict[str, Any]]:
        all_records = []
        current_url = start_url
        page_num = 1

        async with self.semaphore:
            while current_url:
                logging.info(f"Scraping {category} - Page {page_num}: {current_url}")
                
                await asyncio.sleep(random.uniform(1.5, 3.0))
                
                html = await self.fetch_page(session, current_url)
                if not html:
                    break

                records = parser.extract_raw_records(html, category)
                
                if len(records) == 0:
                    logging.warning(f"Circuit Breaker triggered: 0 records extracted on {current_url}. Halting category.")
                    break

                all_records.extend(records)
                logging.info(f"Extracted {len(records)} items from page {page_num}.")

                next_url = parser.get_next_page_url(html)
                
                # Dynamic Referer Update
                session.headers.update({"Referer": current_url})
                current_url = next_url
                page_num += 1

        return all_records

    async def run(self) -> List[Dict[str, Any]]:
        parser = MyTekParser()
        all_data = []
        
        async with requests.AsyncSession() as session:
            tasks = []
            for category, url in parser.target_categories.items():
                tasks.append(self.scrape_category(parser, session, category, url))
            
            results = await asyncio.gather(*tasks)
            
            for category_records in results:
                all_data.extend(category_records)
                
        logging.info(f"Extraction complete. Total records: {len(all_data)}")
        
        if all_data:
            # Bronze Layer Checkpointing
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"raw_extract_{timestamp}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
            logging.info(f"Checkpoint saved to {filename}")

            print("\n--- Sample Extracted Item ---")
            for key, value in all_data[0].items():
                print(f"{key}: {value}")
            print("-" * 29 + "\n")
            
        return all_data

if __name__ == "__main__":
    engine = ExtractionEngine(max_concurrent=2)
    asyncio.run(engine.run())
