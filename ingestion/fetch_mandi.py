import os
import json
import requests
from datetime import datetime
from pathlib import Path

RAW_DIR = os.getenv('RAW_DIR', './data/raw')
API_URL = 'https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070'
API_KEY = os.getenv('DATA_GOV_API_KEY')
COMMODITIES = ["Tomato", "Onion", "Potato", "Wheat", "Rice", "Maize", "Soybean"]

def fetch_mandi_prices(date: str) -> list[dict]:
    """Fetch mandi price data for a given date.
    Returns list of dicts with keys: date, commodity, district, state, market, min_price, max_price, modal_price.
    """
    records = []
    for commodity in COMMODITIES:
        params = {
            'api-key': API_KEY,
            'format': 'json',
            'limit': '500',
            'filters[commodity]': commodity,
            'filters[date]': date
        }
        try:
            response = requests.get(API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            for rec in data.get('records', []):
                records.append({
                    'date': date,
                    'commodity': rec.get('commodity'),
                    'district': rec.get('district'),
                    'state': rec.get('state'),
                    'market': rec.get('market'),
                    'min_price': rec.get('min_price'),
                    'max_price': rec.get('max_price'),
                    'modal_price': rec.get('modal_price')
                })
        except Exception as e:
            print(f"Error fetching {commodity} for {date}: {e}")
            continue
    # Save to file
    os.makedirs(RAW_DIR, exist_ok=True)
    out_path = Path(RAW_DIR) / f"mandi_{date}.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    return records
