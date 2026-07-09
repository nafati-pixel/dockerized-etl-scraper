import json
import os
import logging
from pathlib import Path
from pydantic import ValidationError
from models import ScrapedItem

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)

def process_and_cleanup(input_filepath: str, final_output_filepath: str):
     """"ensures idempotency through creating an intermediate file and appending that file to the final file""""



    logger.info(f"Starting to process file: {input_filepath}")
    
    temp_filepath = final_output_filepath + ".tmp"

    if os.path.exists(temp_filepath): #the new file
        os.remove(temp_filepath)

    try:
        with open(input_filepath, 'r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, start=1):
                if not line.strip():
                    continue 
                
                try: # gets a list of the data to validate
                    raw_data = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning(f"Line {line_number} is broken. Skipping.")
                    continue

                extraction_date = raw_data.get("extracted_at", "Unknown")
                

                raw_payload = raw_data.get("raw_payload", {})
                
                
                if isinstance(raw_payload, dict):#in case we get nested dicts

                    products = list(raw_payload.values())
                elif isinstance(raw_payload, list):

                    products = raw_payload
                else:
                    logger.warning(f"Unexpected payload format on line {line_number}")
                    continue

                valid_chunk = []


                for prod_data in products:
                    try:
                        raw_price = prod_data.get("price")
                        clean_price = 0.0
                        if raw_price:
                            # This handles "1 250,000 DT" -> 1250.0
                            p_str = str(raw_price).replace("DT", "").replace(" ", "").replace(",", ".").strip()
                            clean_price = float(p_str)

                        item_dict = {
                            "id": prod_data.get("id"),
                            "name": prod_data.get("name"),
                            "sku": prod_data.get("sku"),
                            "price": clean_price,
                            "date_posted": extraction_date
                        }
                        

                        item = ScrapedItem(**item_dict) 
                        valid_chunk.append(item.model_dump())

                    except (ValidationError, ValueError) as e:
                        p_id = prod_data.get('id', 'Unknown')
                        logger.error(f"Item {p_id} failed validation/parsing: {e}")
                

                if valid_chunk:
                    with open(temp_filepath, 'a', encoding='utf-8') as temp_f:
                        for valid_item in valid_chunk:
                            temp_f.write(json.dumps(valid_item, ensure_ascii=False) + '\n')

    except FileNotFoundError:
        logger.error(f"File not found: {input_filepath}")
        return


    try:
        if os.path.exists(temp_filepath):
            os.replace(temp_filepath, final_output_filepath)
            logger.info(f"Success! Final data saved to {final_output_filepath}")
        else:
            logger.warning("No valid data was found to save.")
            
        if os.path.exists(input_filepath):
            os.remove(input_filepath)
            logger.info(f"Deleted original file: {input_filepath}")
            
    except Exception as e:
        logger.critical(f"Failed to finish file swap: {e}")

if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    process_and_cleanup(str(BASE_DIR / "messy_data.jsonl"), str(BASE_DIR / "clean_data.jsonl"))
