import pytest
import pandas as pd
from pathlib import Path
from ingestion import fetch_mandi, fetch_weather
from transform import clean, join, volatility
from db import loader
from models.price_predictor import PricePredictor

# Mock data for tests

@pytest.fixture
def sample_mandi_df():
    data = {
        'date': ['2023-01-01', '2023-01-01'],
        'commodity': ['Tomato', 'Onion'],
        'district': ['Nashik', 'Agra'],
        'state': ['Maharashtra', 'Uttar Pradesh'],
        'market': ['MarketA', 'MarketB'],
        'min_price': [10.0, 12.5],
        'max_price': [15.0, 18.0],
        'modal_price': [12.0, 15.0]
    }
    return pd.DataFrame(data)

@pytest.fixture
def sample_weather_df():
    data = {
        'date': ['2023-01-01', '2023-01-01'],
        'district': ['Nashik', 'Agra'],
        'state': ['Maharashtra', 'Uttar Pradesh'],
        'precipitation_mm': [5.0, 0.0],
        'temp_max_c': [30.0, 25.0],
        'temp_min_c': [15.0, 10.0],
        'windspeed_kmh': [10.0, 5.0]
    }
    return pd.DataFrame(data)

# Ingestion tests (basic structure, no external calls)

def test_fetch_mandi_structure(monkeypatch, tmp_path):
    # Mock requests.get to return a predefined JSON
    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self._json = json_data
            self.status_code = status_code
        def json(self):
            return self._json
        def raise_for_status(self):
            if self.status_code != 200:
                raise Exception('HTTP error')
    def mock_get(*args, **kwargs):
        return MockResponse({'records': []})
    monkeypatch.setattr(fetch_mandi, 'RAW_DIR', str(tmp_path))
    monkeypatch.setattr('requests.get', mock_get)
    result = fetch_mandi.fetch_mandi_prices('2023-01-01')
    assert isinstance(result, list)

def test_fetch_weather_structure(monkeypatch, tmp_path):
    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self._json = json_data
            self.status_code = status_code
        def json(self):
            return self._json
        def raise_for_status(self):
            if self.status_code != 200:
                raise Exception('HTTP error')
    def mock_get(*args, **kwargs):
        return MockResponse({'daily': {'time': ['2023-01-01'], 'precipitation_sum': [0], 'temperature_2m_max': [30], 'temperature_2m_min': [15], 'windspeed_10m_max': [10]}})
    monkeypatch.setattr(fetch_weather, 'RAW_DIR', str(tmp_path))
    monkeypatch.setattr('requests.get', mock_get)
    result = fetch_weather.fetch_weather('2023-01-01')
    assert isinstance(result, list)

# Transformation tests

def test_clean_mandi(sample_mandi_df):
    cleaned = clean.clean_mandi(sample_mandi_df)
    assert cleaned['min_price'].dtype == float
    assert cleaned['max_price'].dtype == float
    assert cleaned['modal_price'].dtype == float
    assert pd.api.types.is_datetime64_any_dtype(cleaned['date'])

def test_clean_weather(sample_weather_df):
    cleaned = clean.clean_weather(sample_weather_df)
    assert cleaned['precipitation_mm'].dtype == float

def test_join(sample_mandi_df, sample_weather_df):
    joined = join.join_mandi_weather(sample_mandi_df, sample_weather_df)
    # Left join should keep mandi rows
    assert len(joined) == len(sample_mandi_df)
    assert 'precipitation_mm' in joined.columns

def test_volatility(sample_mandi_df):
    df = volatility.compute_volatility(sample_mandi_df)
    assert 'volatility_score' in df.columns
    assert 'volatility_label' in df.columns
    assert df['volatility_label'].isin(['HIGH', 'MEDIUM', 'LOW']).all()

# Database loader test (mock DuckDB connection using in-memory)

def test_loader(monkeypatch, tmp_path):
    # Create a simple parquet file
    df = pd.DataFrame({
        'date': pd.to_datetime(['2023-01-01']),
        'commodity': ['Tomato'],
        'district': ['Nashik'],
        'state': ['Maharashtra'],
        'market': ['MarketA'],
        'min_price': [10.0],
        'max_price': [15.0],
        'modal_price': [12.0],
        'precipitation_mm': [5.0],
        'temp_max_c': [30.0],
        'temp_min_c': [15.0],
        'windspeed_kmh': [10.0],
        'volatility_score': [0.25],
        'volatility_label': ['MEDIUM'],
        'price_change_pct': [0.0]
    })
    parquet_path = tmp_path / 'test.parquet'
    df.to_parquet(parquet_path)
    # Patch DUCKDB_PATH variable directly on the loader module
    monkeypatch.setattr(loader, 'DUCKDB_PATH', str(tmp_path / 'test.duckdb'))
    loader.load_parquet_to_duckdb(str(parquet_path), '2023-01-01')
    # Verify file exists
    assert Path(str(tmp_path / 'test.duckdb')).exists()

# Model predictor test (basic train/predict flow)

def test_price_predictor(sample_mandi_df):
    predictor = PricePredictor()
    predictor.train(sample_mandi_df, 'Tomato', 'Nashik')
    latest = sample_mandi_df.iloc[-1].to_dict()
    result = predictor.predict_next_week(latest)
    assert isinstance(result, dict)
    assert 'predicted_price' in result
