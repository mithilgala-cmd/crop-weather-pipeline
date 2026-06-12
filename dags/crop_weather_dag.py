"""
Crop Price & Weather Correlation Pipeline
DAG: crop_weather_pipeline
Schedule: Daily at 6 AM IST
"""

import os
import sys
from datetime import timedelta

import pandas as pd
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

# Ensure project modules are importable (local dev + Docker via PYTHONPATH)
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

RAW_DIR = os.getenv("RAW_DIR", "/opt/airflow/data/raw")
PROCESSED_DIR = os.getenv("PROCESSED_DIR", "/opt/airflow/data/processed")
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "/opt/airflow/data/crop_weather.duckdb")

DEFAULT_ARGS = {
    "owner": "your_name",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


def create_dirs():
    """Create raw/processed dirs if not exist."""
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    print(f"Dirs ready: {RAW_DIR}, {PROCESSED_DIR}")


def fetch_mandi_prices(**context):
    """Fetch mandi prices via ingestion module."""
    from ingestion.fetch_mandi import fetch_mandi_prices as fetch_mandi

    execution_date = context["ds"]
    records = fetch_mandi(execution_date)
    print(f"Fetched {len(records)} mandi records for {execution_date}")


def fetch_weather(**context):
    """Fetch weather via ingestion module."""
    from ingestion.fetch_weather import fetch_weather as fetch_weather_data

    execution_date = context["ds"]
    results = fetch_weather_data(execution_date)
    print(f"Fetched weather for {len(results)} districts on {execution_date}")


def transform_and_join(**context):
    """Clean, join, and compute volatility using transform modules."""
    from transform.clean import clean_mandi, clean_weather
    from transform.join import join_mandi_weather
    from transform.volatility import compute_volatility

    execution_date = context["ds"]
    mandi_path = os.path.join(RAW_DIR, f"mandi_{execution_date}.json")
    weather_path = os.path.join(RAW_DIR, f"weather_{execution_date}.json")

    if not os.path.exists(mandi_path) or not os.path.exists(weather_path):
        print("Raw files missing — skipping transform.")
        return

    mandi_df = pd.read_json(mandi_path)
    weather_df = pd.read_json(weather_path)

    mandi_df = clean_mandi(mandi_df)
    weather_df = clean_weather(weather_df)
    joined = join_mandi_weather(mandi_df, weather_df)
    joined = compute_volatility(joined)

    out_path = os.path.join(PROCESSED_DIR, f"joined_{execution_date}.parquet")
    joined.to_parquet(out_path, index=False)
    print(f"Joined {len(joined)} rows → {out_path}")


def load_to_duckdb(**context):
    """Load processed parquet into DuckDB via db.loader."""
    from db.loader import load_parquet_to_duckdb

    execution_date = context["ds"]
    parquet_path = os.path.join(PROCESSED_DIR, f"joined_{execution_date}.parquet")

    if not os.path.exists(parquet_path):
        print("Parquet missing — skipping load.")
        return

    os.environ["DUCKDB_PATH"] = DUCKDB_PATH
    load_parquet_to_duckdb(parquet_path, execution_date)
    print(f"DuckDB updated at {DUCKDB_PATH}")


def generate_alerts(**context):
    """Log high-volatility alerts (alerts table populated by db.loader)."""
    import duckdb

    execution_date = context["ds"]
    con = duckdb.connect(DUCKDB_PATH)

    alerts = con.execute(
        """
        SELECT commodity, district, volatility_score, modal_price, precipitation_mm
        FROM alerts
        WHERE alert_date = ?
        ORDER BY volatility_score DESC
        LIMIT 10
        """,
        [execution_date],
    ).fetchdf()

    con.close()

    if alerts.empty:
        print("No high-volatility alerts today.")
    else:
        print(f"\nHIGH VOLATILITY ALERT — {execution_date}")
        print(alerts.to_string(index=False))


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

    t5_dbt = BashOperator(
        task_id="run_dbt_models",
        bash_command=(
            "dbt run --project-dir /opt/airflow/dbt_project "
            "--profiles-dir /opt/airflow/dbt_project"
        ),
        env={
            "RAW_DIR": RAW_DIR,
            "DUCKDB_PATH": DUCKDB_PATH,
        },
    )

    t6_alerts = PythonOperator(
        task_id="generate_alerts",
        python_callable=generate_alerts,
    )

    # setup → [mandi + weather in parallel] → transform → load → dbt → alerts
    t0_setup >> [t1_mandi, t2_weather] >> t3_transform >> t4_load >> t5_dbt >> t6_alerts
