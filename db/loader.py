import duckdb
import os
from dotenv import load_dotenv
import logging

load_dotenv()
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "./data/crop_weather.duckdb")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_parquet_to_duckdb(parquet_path: str, date: str):
    if not os.path.exists(parquet_path):
        logging.error(f"Parquet file {parquet_path} does not exist.")
        return
        
    try:
        # Create database directory if it doesn't exist
        os.makedirs(os.path.dirname(DUCKDB_PATH), exist_ok=True)
        
        # Connect to DuckDB
        conn = duckdb.connect(DUCKDB_PATH)
        
        # Run schema.sql on first run
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, "r") as f:
            schema_sql = f.read()
            conn.execute(schema_sql)
            
        # Delete existing rows for that date before inserting (idempotent)
        conn.execute("DELETE FROM price_weather WHERE date = ?", [date])
        conn.execute("DELETE FROM alerts WHERE alert_date = ?", [date])
        
        # Insert from parquet using read_parquet()
        logging.info(f"Loading data from {parquet_path} into DuckDB for date {date}")
        conn.execute(f"INSERT INTO price_weather SELECT * FROM read_parquet('{parquet_path}')")
        
        # Also populate alerts table where volatility_label = 'HIGH'
        alert_sql = f"""
        INSERT INTO alerts (alert_date, commodity, district, volatility_score, modal_price, precipitation_mm, alert_reason)
        SELECT 
            date as alert_date, 
            commodity, 
            district, 
            volatility_score, 
            modal_price, 
            precipitation_mm, 
            'High Volatility Alert' as alert_reason
        FROM read_parquet('{parquet_path}')
        WHERE volatility_label = 'HIGH'
        """
        conn.execute(alert_sql)
        
        logging.info("Successfully loaded data into DuckDB.")
        
    except Exception as e:
        logging.error(f"Failed to load data to DuckDB: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3:
        load_parquet_to_duckdb(sys.argv[1], sys.argv[2])
    else:
        logging.warning("Usage: python db/loader.py <parquet_path> <date>")
