import os
import json
import requests
from pathlib import Path

from config.constants import DISTRICTS

RAW_DIR = os.getenv("RAW_DIR", "./data/raw")

def fetch_weather(date: str) -> list[dict]:
    """Fetch daily weather data for all districts using Open-Meteo API.
    Saves JSON to `{RAW_DIR}/weather_{date}.json` and returns list of dicts.
    """
    results = []
    for d in DISTRICTS:
        params = {
            "latitude": d["lat"],
            "longitude": d["lon"],
            "daily": ["precipitation_sum", "temperature_2m_max", "temperature_2m_min", "windspeed_10m_max"],
            "timezone": "Asia/Kolkata",
            "start_date": date,
            "end_date": date,
        }
        try:
            resp = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            daily = data.get("daily", {})
            idx = 0
            results.append({
                "date": date,
                "district": d["name"],
                "state": d["state"],
                "precipitation_mm": daily.get("precipitation_sum", [None])[idx],
                "temp_max_c": daily.get("temperature_2m_max", [None])[idx],
                "temp_min_c": daily.get("temperature_2m_min", [None])[idx],
                "windspeed_kmh": daily.get("windspeed_10m_max", [None])[idx],
            })
        except Exception as e:
            print(f"Failed to fetch weather for {d['name']}: {e}")
            continue
    os.makedirs(RAW_DIR, exist_ok=True)
    out_path = Path(RAW_DIR) / f"weather_{date}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    return results
