import os
import unittest
import pandas as pd
import duckdb
from db.loader import load_parquet_to_duckdb
from unittest.mock import patch

class TestLoader(unittest.TestCase):
    def setUp(self):
        self.test_db_path = "./data/test_crop_weather.duckdb"
        self.parquet_path = "./data/test_joined.parquet"
        
        # Ensure directories exist
        os.makedirs("./data", exist_ok=True)
        
        # Create a sample dataframe and save to Parquet
        self.df = pd.DataFrame({
            'date': [pd.to_datetime('2026-05-19'), pd.to_datetime('2026-05-19')],
            'commodity': ['Tomato', 'Onion'],
            'district': ['Nashik', 'Nashik'],
            'state': ['Maharashtra', 'Maharashtra'],
            'market': ['Nashik', 'Nashik'],
            'min_price': [100.0, 80.0],
            'max_price': [200.0, 120.0],
            'modal_price': [150.0, 100.0],
            'precipitation_mm': [10.0, 10.0],
            'temp_max_c': [35.0, 35.0],
            'temp_min_c': [24.0, 24.0],
            'windspeed_kmh': [12.0, 12.0],
            'volatility_score': [0.67, 0.40],
            'volatility_label': ['HIGH', 'HIGH'],
            'price_change_pct': [0.0, 0.0]
        })
        self.df.to_parquet(self.parquet_path, index=False)

    def tearDown(self):
        # Clean up files
        if os.path.exists(self.parquet_path):
            os.remove(self.parquet_path)
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    @patch('db.loader.DUCKDB_PATH', "./data/test_crop_weather.duckdb")
    def test_load_parquet_to_duckdb(self):
        # Run loader
        load_parquet_to_duckdb(self.parquet_path, "2026-05-19")
        
        # Verify db contents
        conn = duckdb.connect(self.test_db_path)
        
        # Check rows in price_weather
        row_count = conn.execute("SELECT COUNT(*) FROM price_weather").fetchone()[0]
        self.assertEqual(row_count, 2)
        
        # Check rows in alerts (since both are HIGH volatility)
        alert_count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        self.assertEqual(alert_count, 2)
        
        conn.close()
