import json
import os
import pytest
from scraper_etl import process_and_cleanup

def test_process_and_cleanup_black_box(tmp_path):
    test_input_path = tmp_path / "test_messy.jsonl"
    test_output_path = tmp_path / "test_clean.jsonl"

    mock_raw_data = {
        "extracted_at": "2026-03-22",
        "raw_payload": {
            "item_1": {
                "id": "999", 
                "name": "Gaming Mouse", 
                "sku": "MOUSE-01", 
                "price": "1 250,000 DT"
            }
        }
    }

    with open(test_input_path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(mock_raw_data) + '\n')

    process_and_cleanup(str(test_input_path), str(test_output_path))
    
    assert os.path.exists(test_output_path) is True, "Output file was not created."
    assert os.path.exists(test_input_path) is False, "Source file was not deleted."

    with open(test_output_path, 'r', encoding='utf-8') as f:
        processed_record = json.loads(f.readline())
        
        assert processed_record["price"] == 1250.0, "Price parsing logic failed."
        assert processed_record["id"] == "999", "Record ID mapping failed."
