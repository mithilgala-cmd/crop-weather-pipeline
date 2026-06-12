import os
import duckdb
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

from config.constants import DISTRICTS, SEED_COMMODITY_PROFILES

# Load config from env or defaults
DUCKDB_PATH = os.getenv('DUCKDB_PATH', './data/crop_weather.duckdb')
ROOT_DIR = Path(__file__).parent.parent.resolve()

def seed_data(force=False):
    db_path = Path(DUCKDB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Connecting to DuckDB at {DUCKDB_PATH}...")
    conn = duckdb.connect(database=DUCKDB_PATH, read_only=False)
    
    # Drop legacy views/tables if they exist to prevent dbt view compilation conflicts
    print("Preparing clean database schema...")
    for item in ['price_weather', 'weekly_aggregates', 'alerts']:
        try:
            conn.execute(f"DROP VIEW IF EXISTS {item} CASCADE;")
        except Exception:
            pass
        try:
            conn.execute(f"DROP TABLE IF EXISTS {item} CASCADE;")
        except Exception:
            pass
    
    # Initialize schema
    schema_path = ROOT_DIR / "db" / "schema.sql"
    if schema_path.exists():
        print("Initializing tables from db/schema.sql...")
        with open(schema_path, "r") as sf:
            conn.execute(sf.read())
    else:
        # Fallback table DDL
        print("Schema file not found. Generating default tables DDL...")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS price_weather (
            date DATE, commodity VARCHAR, district VARCHAR, state VARCHAR, market VARCHAR,
            min_price DOUBLE, max_price DOUBLE, modal_price DOUBLE,
            precipitation_mm DOUBLE, temp_max_c DOUBLE, temp_min_c DOUBLE, windspeed_kmh DOUBLE,
            volatility_score DOUBLE, volatility_label VARCHAR, price_change_pct DOUBLE
        );
        CREATE TABLE IF NOT EXISTS weekly_aggregates (
            week_start DATE, commodity VARCHAR, district VARCHAR,
            avg_modal_price DOUBLE, avg_precipitation DOUBLE, avg_volatility DOUBLE, max_volatility DOUBLE
        );
        CREATE TABLE IF NOT EXISTS alerts (
            alert_date DATE, commodity VARCHAR, district VARCHAR,
            volatility_score DOUBLE, modal_price DOUBLE, precipitation_mm DOUBLE, alert_reason VARCHAR
        );
        """)
    
    # Check if database has data already
    if not force:
        count = conn.execute("SELECT COUNT(*) FROM price_weather").fetchone()[0]
        if count > 0:
            print(f"Database already seeded with {count} rows. Skipping seeding.")
            conn.close()
            return False
            
    print("Generating 60 days of realistic simulated crop + weather observations...")
    np.random.seed(42)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    dates = pd.date_range(start=start_date, end=end_date)
    
    records = []
    
    for dt in dates:
        date_str = dt.strftime("%Y-%m-%d")
        day_of_year = dt.dayofyear
        
        for district_info in DISTRICTS:
            dist_name = district_info["name"]
            state = district_info["state"]
            
            # Weather factors
            rain_occurred = np.random.rand() < district_info["rain_prob"]
            precipitation = np.random.exponential(15.0) if rain_occurred else 0.0
            
            base_t = district_info["base_temp"] + 4.0 * np.sin(day_of_year / 58.0)
            temp_max = base_t + np.random.normal(0, 1.5)
            temp_min = base_t - 8.0 + np.random.normal(0, 1.2)
            windspeed = np.random.uniform(5.0, 25.0)
            
            for commodity, crop_info in SEED_COMMODITY_PROFILES.items():
                # Base price calculation with seasonal cycles and district offsets
                dist_offset = 0.90 if dist_name == "Nashik" and commodity == "Onion" else 1.0
                dist_offset = 0.88 if dist_name == "Agra" and commodity == "Potato" else dist_offset
                dist_offset = 0.92 if dist_name == "Ludhiana" and commodity == "Wheat" else dist_offset
                
                seasonal_multiplier = 1.0 + crop_info["volatility"] * np.sin(day_of_year / 12.0)
                random_walk = 1.0 + np.random.normal(0, 0.015)
                
                # Precipitation increases price volatility spike
                weather_impact = 1.0 + (0.003 * precipitation) if precipitation > 5 else 1.0
                
                modal_price = round(crop_info["base_price"] * dist_offset * seasonal_multiplier * random_walk * weather_impact, 2)
                
                # Spread expands during high rain/supply shocks
                spread_factor = crop_info["volatility"] * (1.2 if precipitation > 15 else 1.0)
                price_range = modal_price * np.random.uniform(0.04, spread_factor)
                
                min_price = round(modal_price - (price_range * 0.45), 2)
                max_price = round(modal_price + (price_range * 0.55), 2)
                
                volatility_score = round((max_price - min_price) / modal_price, 4)
                
                volatility_label = "LOW"
                if volatility_score > 0.3:
                    volatility_label = "HIGH"
                elif volatility_score > 0.1:
                    volatility_label = "MEDIUM"
                
                records.append({
                    "date": dt,
                    "commodity": commodity,
                    "district": dist_name,
                    "state": state,
                    "market": f"{dist_name} Mandi",
                    "min_price": min_price,
                    "max_price": max_price,
                    "modal_price": modal_price,
                    "precipitation_mm": round(precipitation, 2),
                    "temp_max_c": round(temp_max, 1),
                    "temp_min_c": round(temp_min, 1),
                    "windspeed_kmh": round(windspeed, 1),
                    "volatility_score": volatility_score,
                    "volatility_label": volatility_label,
                    "price_change_pct": 0.0  # calculated in next step
                })
                
    df = pd.DataFrame(records)
    
    # Calculate price change percentage safely using sort + groupby shifts
    df = df.sort_values(by=["commodity", "district", "date"]).reset_index(drop=True)
    df["prev_price"] = df.groupby(["commodity", "district"])["modal_price"].shift(1)
    df["price_change_pct"] = np.where(
        df["prev_price"].notna() & (df["prev_price"] > 0),
        round(((df["modal_price"] - df["prev_price"]) / df["prev_price"]) * 100, 2),
        0.0
    )
    df = df.drop(columns=["prev_price"])
    
    # Clear old data before seed (idempotent)
    conn.execute("DELETE FROM price_weather")
    conn.execute("DELETE FROM alerts")
    conn.execute("DELETE FROM weekly_aggregates")
    
    print("Loading data into price_weather...")
    conn.execute("INSERT INTO price_weather SELECT * FROM df")
    
    print("Loading data into alerts...")
    conn.execute("""
    INSERT INTO alerts (alert_date, commodity, district, volatility_score, modal_price, precipitation_mm, alert_reason)
    SELECT 
        date as alert_date,
        commodity,
        district,
        volatility_score,
        modal_price,
        precipitation_mm,
        'High Volatility Alert' as alert_reason
    FROM price_weather
    WHERE volatility_label = 'HIGH'
    """)
    
    print("Calculating and loading weekly aggregates...")
    conn.execute("""
    INSERT INTO weekly_aggregates (week_start, commodity, district, avg_modal_price, avg_precipitation, avg_volatility, max_volatility)
    SELECT 
        DATE_TRUNC('week', date) as week_start,
        commodity,
        district,
        ROUND(AVG(modal_price), 2) as avg_modal_price,
        ROUND(AVG(precipitation_mm), 2) as avg_precipitation,
        ROUND(AVG(volatility_score), 4) as avg_volatility,
        ROUND(MAX(volatility_score), 4) as max_volatility
    FROM price_weather
    GROUP BY 1, 2, 3
    """)
    
    total_loaded = conn.execute("SELECT COUNT(*) FROM price_weather").fetchone()[0]
    alerts_count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    weekly_count = conn.execute("SELECT COUNT(*) FROM weekly_aggregates").fetchone()[0]
    
    print(f"Successfully seeded database!")
    print(f"  price_weather:     {total_loaded} rows")
    print(f"  alerts:            {alerts_count} rows")
    print(f"  weekly_aggregates: {weekly_count} rows")
    
    conn.close()
    return True

if __name__ == "__main__":
    import sys
    force_seed = "--force" in sys.argv
    seed_data(force=force_seed)
