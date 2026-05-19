"""
Crop Price & Weather Correlation Pipeline
DAG: crop_weather_pipeline
Schedule: Daily at 6 AM IST
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import requests
import pandas as pd
import json
import os

# ──────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────

RAW_DIR = "/opt/airflow/data/raw"
PROCESSED_DIR = "/opt/airflow/data/processed"

COMMODITIES = ["Tomato", "Onion", "Potato", "Wheat", "Rice"]

# Districts: (name, lat, lon, state)
DISTRICTS = [
    ("Nashik",      20.0059, 73.7898, "Maharashtra"),
    ("Agra",        27.1767, 78.0081, "Uttar Pradesh"),
    ("Ludhiana",    30.9010, 75.8573, "Punjab"),
    ("Guntur",      16.3067, 80.4365, "Andhra Pradesh"),
    ("Indore",      22.7196, 75.8577, "Madhya Pradesh"),
]

DEFAULT_ARGS = {
    "owner": "your_name",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


# ──────────────────────────────────────────
# TASK FUNCTIONS
# ──────────────────────────────────────────

def create_dirs():
    """Create raw/processed dirs if not exist."""
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    print(f"Dirs ready: {RAW_DIR}, {PROCESSED_DIR}")


def fetch_mandi_prices(**context):
    """
    Fetch mandi prices from data.gov.in API.
    Replace API_KEY with your key from https://data.gov.in
    Free registration required.
    """
    execution_date = context["ds"]  # YYYY-MM-DD
    API_KEY = os.getenv("DATA_GOV_API_KEY", "YOUR_API_KEY_HERE")
    
    records = []

    for commodity in COMMODITIES:
        url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
        params = {
            "api-key": API_KEY,
            "format": "json",
            "limit": 100,
            "filters[commodity]": commodity,
        }
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            for record in data.get("records", []):
                records.append({
                    "date": record.get("arrival_date", execution_date),
                    "commodity": record.get("commodity"),
                    "district": record.get("district"),
                    "state": record.get("state"),
                    "market": record.get("market"),
                    "min_price": record.get("min_price"),
                    "max_price": record.get("max_price"),
                    "modal_price": record.get("modal_price"),
                })
        except Exception as e:
            print(f"Failed fetching {commodity}: {e}")

    # Save raw
    out_path = f"{RAW_DIR}/mandi_{execution_date}.json"
    with open(out_path, "w") as f:
        json.dump(records, f, indent=2)
    print(f"Saved {len(records)} mandi records to {out_path}")


def fetch_weather(**context):
    """
    Fetch weather from Open-Meteo API. Free, no API key needed.
    Docs: https://open-meteo.com/en/docs
    """
    execution_date = context["ds"]
    all_weather = []

    for district_name, lat, lon, state in DISTRICTS:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min",
            "start_date": execution_date,
            "end_date": execution_date,
            "timezone": "Asia/Kolkata",
        }
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            daily = data.get("daily", {})
            all_weather.append({
                "date": execution_date,
                "district": district_name,
                "state": state,
                "latitude": lat,
                "longitude": lon,
                "precipitation_mm": daily.get("precipitation_sum", [None])[0],
                "temp_max_c": daily.get("temperature_2m_max", [None])[0],
                "temp_min_c": daily.get("temperature_2m_min", [None])[0],
            })
        except Exception as e:
            print(f"Failed fetching weather for {district_name}: {e}")

    out_path = f"{RAW_DIR}/weather_{execution_date}.json"
    with open(out_path, "w") as f:
        json.dump(all_weather, f, indent=2)
    print(f"Saved weather for {len(all_weather)} districts to {out_path}")


def transform_and_join(**context):
    """
    Clean + join mandi prices with weather data.
    Output: processed/joined_YYYY-MM-DD.parquet
    """
    execution_date = context["ds"]

    mandi_path = f"{RAW_DIR}/mandi_{execution_date}.json"
    weather_path = f"{RAW_DIR}/weather_{execution_date}.json"

    if not os.path.exists(mandi_path) or not os.path.exists(weather_path):
        print("Raw files missing — skipping transform.")
        return

    # Load
    mandi_df = pd.read_json(mandi_path)
    weather_df = pd.read_json(weather_path)

    # Clean mandi
    mandi_df["modal_price"] = pd.to_numeric(mandi_df["modal_price"], errors="coerce")
    mandi_df["district"] = mandi_df["district"].str.strip().str.title()
    mandi_df.dropna(subset=["modal_price"], inplace=True)

    # Clean weather
    weather_df["district"] = weather_df["district"].str.strip().str.title()

    # Join on district + date
    joined = mandi_df.merge(
        weather_df[["date", "district", "precipitation_mm", "temp_max_c", "temp_min_c"]],
        on=["date", "district"],
        how="left"
    )

    # Volatility score: (max_price - min_price) / modal_price
    joined["volatility_score"] = (
        (pd.to_numeric(joined["max_price"], errors="coerce") -
         pd.to_numeric(joined["min_price"], errors="coerce")) /
        joined["modal_price"]
    ).round(4)

    out_path = f"{PROCESSED_DIR}/joined_{execution_date}.parquet"
    joined.to_parquet(out_path, index=False)
    print(f"Joined {len(joined)} rows → {out_path}")


def load_to_duckdb(**context):
    """
    Load processed parquet into DuckDB.
    Install: pip install duckdb
    """
    import duckdb

    execution_date = context["ds"]
    parquet_path = f"{PROCESSED_DIR}/joined_{execution_date}.parquet"

    if not os.path.exists(parquet_path):
        print("Parquet missing — skipping load.")
        return

    db_path = "/opt/airflow/data/crop_weather.duckdb"
    con = duckdb.connect(db_path)

    # Create table if not exists
    con.execute("""
        CREATE TABLE IF NOT EXISTS price_weather (
            date VARCHAR,
            commodity VARCHAR,
            district VARCHAR,
            state VARCHAR,
            market VARCHAR,
            min_price DOUBLE,
            max_price DOUBLE,
            modal_price DOUBLE,
            precipitation_mm DOUBLE,
            temp_max_c DOUBLE,
            temp_min_c DOUBLE,
            volatility_score DOUBLE
        )
    """)

    # Insert new records (avoid duplicates)
    con.execute(f"""
        INSERT INTO price_weather
        SELECT * FROM read_parquet('{parquet_path}')
        WHERE date NOT IN (SELECT DISTINCT date FROM price_weather WHERE date = '{execution_date}')
    """)

    count = con.execute("SELECT COUNT(*) FROM price_weather").fetchone()[0]
    con.close()
    print(f"DuckDB updated. Total rows: {count}")


def generate_alerts(**context):
    """
    Check volatility — print/log high-risk commodities.
    Extend: send email / Slack / save to alerts table.
    """
    import duckdb

    execution_date = context["ds"]
    db_path = "/opt/airflow/data/crop_weather.duckdb"
    con = duckdb.connect(db_path)

    alerts = con.execute(f"""
        SELECT commodity, district, state, modal_price, volatility_score, precipitation_mm
        FROM price_weather
        WHERE date = '{execution_date}'
          AND volatility_score > 0.3
        ORDER BY volatility_score DESC
        LIMIT 10
    """).fetchdf()

    con.close()

    if alerts.empty:
        print("No high-volatility alerts today.")
    else:
        print(f"\n⚠️  HIGH VOLATILITY ALERT — {execution_date}")
        print(alerts.to_string(index=False))
        # TODO: integrate with Slack/email notifier here


# ──────────────────────────────────────────
# DAG DEFINITION
# ──────────────────────────────────────────

with DAG(
    dag_id="crop_weather_pipeline",
    default_args=DEFAULT_ARGS,
    description="Daily crop price + weather ingestion and correlation pipeline",
    schedule_interval="0 1 * * *",  # 6:30 AM IST = 1:00 AM UTC
    start_date=days_ago(1),
    catchup=False,
    tags=["data-engineering", "agriculture", "social-impact"],
) as dag:

    t0_setup = PythonOperator(
        task_id="create_directories",
        python_callable=create_dirs,
    )

    t1_mandi = PythonOperator(
        task_id="fetch_mandi_prices",
        python_callable=fetch_mandi_prices,
    )

    t2_weather = PythonOperator(
        task_id="fetch_weather_data",
        python_callable=fetch_weather,
    )

    t3_transform = PythonOperator(
        task_id="transform_and_join",
        python_callable=transform_and_join,
    )

    t4_load = PythonOperator(
        task_id="load_to_duckdb",
        python_callable=load_to_duckdb,
    )

    t5_alerts = PythonOperator(
        task_id="generate_alerts",
        python_callable=generate_alerts,
    )

    # ── Pipeline order ──
    # setup → [mandi + weather in parallel] → transform → load → alerts
    t0_setup >> [t1_mandi, t2_weather] >> t3_transform >> t4_load >> t5_alerts
