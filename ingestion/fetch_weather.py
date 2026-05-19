import os
import json
import logging
import requests
from dotenv import load_dotenv
from typing import List, Dict, Any

# Load environment variables
load_dotenv()

RAW_DIR = os.getenv("RAW_DIR", "./data/raw")

BASE_URL = "https://api.open-meteo.com/v1/forecast"

DISTRICTS = [
    {"name": "Nashik",    "lat": 20.0059, "lon": 73.7898, "state": "Maharashtra"},
    {"name": "Agra",      "lat": 27.1767, "lon": 78.0081, "state": "Uttar Pradesh"},
    {"name": "Ludhiana",  "lat": 30.9010, "lon": 75.8573, "state": "Punjab"},
    {"name": "Guntur",    "lat": 16.3067, "lon": 80.4365, "state": "Andhra Pradesh"},
    {"name": "Indore",    "lat": 22.7196, "lon": 75.8577, "state": "Madhya Pradesh"},
    {"name": "Jaipur",    "lat": 26.9124, "lon": 75.7873, "state": "Rajasthan"},
    {"name": "Patna",     "lat": 25.5941, "lon": 85.1376, "state": "Bihar"},
    {"name": "Bhopal",    "lat": 23.2599, "lon": 77.4126, "state": "Madhya Pradesh"},
]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_weather(date: str) -> List[Dict[str, Any]]:
    """
    Fetch daily weather forecasts for specific districts.
    """
    all_weather_records = []
    
    for district in DISTRICTS:
        params = {
            "latitude": district["lat"],
            "longitude": district["lon"],
            "daily": ["precipitation_sum", "temperature_2m_max", "temperature_2m_min", "windspeed_10m_max"],
            "timezone": "Asia/Kolkata",
            "start_date": date,
            "end_date": date
        }
        
        try:
            logging.info(f"Fetching weather data for district: {district['name']} on {date}")
            response = requests.get(BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            daily_data = data.get("daily", {})
            
            # Since we requested a single date, lists should have length 1
            if "time" in daily_data and len(daily_data["time"]) > 0:
                record = {
                    "date": date,
                    "district": district["name"],
                    "state": district["state"],
                    "precipitation_mm": daily_data.get("precipitation_sum", [None])[0],
                    "temp_max_c": daily_data.get("temperature_2m_max", [None])[0],
                    "temp_min_c": daily_data.get("temperature_2m_min", [None])[0],
                    "windspeed_kmh": daily_data.get("windspeed_10m_max", [None])[0]
                }
                all_weather_records.append(record)
            else:
                logging.warning(f"No daily weather data found for {district['name']} on {date}")
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to fetch weather data for district {district['name']}: {e}")
            continue
            
    # Save output to JSON
    os.makedirs(RAW_DIR, exist_ok=True)
    output_path = os.path.join(RAW_DIR, f"weather_{date}.json")
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_weather_records, f, indent=4)
        logging.info(f"Successfully saved {len(all_weather_records)} weather records to {output_path}")
    except IOError as e:
        logging.error(f"Failed to save weather data to {output_path}: {e}")
        
    return all_weather_records

if __name__ == "__main__":
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    fetch_weather(today)
