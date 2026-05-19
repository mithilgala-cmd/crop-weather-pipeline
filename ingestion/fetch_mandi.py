import os
import json
import logging
import requests
from dotenv import load_dotenv
from typing import List, Dict, Any

# Load environment variables
load_dotenv()

DATA_GOV_API_KEY = os.getenv("DATA_GOV_API_KEY")
RAW_DIR = os.getenv("RAW_DIR", "./data/raw")

COMMODITIES = ["Tomato", "Onion", "Potato", "Wheat", "Rice", "Maize", "Soybean"]
BASE_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_mandi_prices(date: str) -> List[Dict[str, Any]]:
    """
    Fetch daily mandi prices for specified commodities.
    """
    if not DATA_GOV_API_KEY or DATA_GOV_API_KEY == "your_key_here":
        logging.warning("DATA_GOV_API_KEY is not set or is using the default placeholder.")
        
    all_records = []
    
    for commodity in COMMODITIES:
        params = {
            "api-key": DATA_GOV_API_KEY,
            "format": "json",
            "limit": 500,
            "filters[commodity]": commodity
        }
        
        try:
            logging.info(f"Fetching Mandi prices for commodity: {commodity} on {date}")
            response = requests.get(BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            records = data.get("records", [])
            
            for record in records:
                processed_record = {
                    "date": record.get("arrival_date", date),
                    "commodity": record.get("commodity"),
                    "district": record.get("district"),
                    "state": record.get("state"),
                    "market": record.get("market"),
                    "min_price": record.get("min_price"),
                    "max_price": record.get("max_price"),
                    "modal_price": record.get("modal_price")
                }
                all_records.append(processed_record)
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to fetch data for commodity {commodity}: {e}")
            continue
            
    # Save output to JSON
    os.makedirs(RAW_DIR, exist_ok=True)
    output_path = os.path.join(RAW_DIR, f"mandi_{date}.json")
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_records, f, indent=4)
        logging.info(f"Successfully saved {len(all_records)} records to {output_path}")
    except IOError as e:
        logging.error(f"Failed to save data to {output_path}: {e}")
        
    return all_records

if __name__ == "__main__":
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    fetch_mandi_prices(today)
