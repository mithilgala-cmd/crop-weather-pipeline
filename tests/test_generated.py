import pytest
import json
from pathlib import Path
from ingestion import fetch_mandi, fetch_weather
from transform import clean, join, volatility
from db import loader
from models import price_predictor

# Helper fixtures
@pytest.fixture
def sample_mandi_data():
    return [{
        "date": "2023-01-01",
        "commodity": "Tomato",
        "district": "Nashik",
        "state": "Maharashtra",
        "market": "Market1",
        "min_price": 10.0,
        "max_price": 15.0,
        "modal_price": 12.5,
    }]

@pytest.fixture
def sample_weather_data():
    return [{
        "date": "2023-01-01",
        "district": "Nashik",
        "precipitation_mm": 5.0,
        "temperature_2m_max": 30.0,
        "temperature_2m_min": 20.0,
        "windspeed_10m_max": 15.0,
    }]

def test_fetch_mandi_returns_list(monkeypatch, tmp_path):
    class DummyResponse:
        status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return {"records": []}
    monkeypatch.setattr(fetch_mandi, 'RAW_DIR', str(tmp_path))
    monkeypatch.setattr('requests.get', lambda *args, **kwargs: DummyResponse())
    result = fetch_mandi.fetch_mandi_prices('2023-01-01')
    assert isinstance(result, list)

def test_fetch_weather_returns_list(monkeypatch, tmp_path):
    class DummyResponse:
        status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return {"daily": {"time": ["2023-01-01"], "precipitation_sum": [0], "temperature_2m_max": [25], "temperature_2m_min": [15], "windspeed_10m_max": [10]}}
    monkeypatch.setattr(fetch_weather, 'RAW_DIR', str(tmp_path))
    monkeypatch.setattr('requests.get', lambda *args, **kwargs: DummyResponse())
    result = fetch_weather.fetch_weather('2023-01-01')
    assert isinstance(result, list)
    assert len(result) == 8
    assert result[0]["district"] == "Nashik"

def test_clean_mandi(sample_mandi_data):
    import pandas as pd
    df = pd.DataFrame(sample_mandi_data)
    cleaned = clean.clean_mandi(df)
    assert not cleaned.empty
    assert cleaned['modal_price'].dtype == float

def test_join_mandi_weather(sample_mandi_data, sample_weather_data):
    import pandas as pd
    mandi_df = pd.DataFrame(sample_mandi_data)
    weather_df = pd.DataFrame(sample_weather_data)
    joined = join.join_mandi_weather(mandi_df, weather_df)
    assert len(joined) == len(mandi_df)
    assert 'precipitation_mm' in joined.columns

def test_compute_volatility(sample_mandi_data):
    import pandas as pd
    df = pd.DataFrame(sample_mandi_data)
    result = volatility.compute_volatility(df)
    assert 'volatility_score' in result.columns
    assert 'volatility_label' in result.columns
    score = result['volatility_score'].iloc[0]
    if score > 0.3:
        assert result['volatility_label'].iloc[0] == 'HIGH'
    elif score > 0.1:
        assert result['volatility_label'].iloc[0] == 'MEDIUM'
    else:
        assert result['volatility_label'].iloc[0] == 'LOW'

def test_loader_inserts_data(monkeypatch, tmp_path):
    import pandas as pd, duckdb, os
    df = pd.DataFrame({
        "date": ["2023-01-01"],
        "commodity": ["Tomato"],
        "district": ["Nashik"],
        "state": ["Maharashtra"],
        "market": ["Market1"],
        "min_price": [10.0],
        "max_price": [15.0],
        "modal_price": [12.5],
        "precipitation_mm": [5.0],
        "temp_max_c": [30.0],
        "temp_min_c": [20.0],
        "windspeed_kmh": [15.0],
        "volatility_score": [0.2],
        "volatility_label": ["MEDIUM"],
        "price_change_pct": [0.0]
    })
    parquet_path = tmp_path / "test.parquet"
    df.to_parquet(parquet_path)
    monkeypatch.setattr(loader, 'DUCKDB_PATH', str(tmp_path / "test.duckdb"))
    loader.load_parquet_to_duckdb(str(parquet_path), "2023-01-01")
    con = duckdb.connect(str(tmp_path / "test.duckdb"))
    rows = con.execute('SELECT * FROM price_weather').fetchall()
    assert len(rows) == 1

def test_price_predictor_train_and_predict(monkeypatch):
    import pandas as pd
    data = pd.DataFrame({
        "precipitation_sum": [0, 5, 10],
        "temp_max_c": [25, 30, 35],
        "temp_min_c": [15, 20, 25],
        "volatility_score": [0.1, 0.2, 0.3],
        "day_of_week": [1, 2, 3],
        "month": [1, 1, 1],
        "lag_7_price": [10, 12, 14],
        "lag_14_price": [8, 10, 12],
        "modal_price": [11, 13, 15]
    })
    pred = price_predictor.PricePredictor()
    pred.train(data, "Tomato", "Nashik")
    latest = data.iloc[-1].to_dict()
    result = pred.predict_next_week(latest)
    assert isinstance(result, dict)
    assert 'predicted_price' in result
