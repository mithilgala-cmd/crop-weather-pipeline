import pytest
import requests
import time
from tests.mock_services import MockAPIServer
from ingestion.fetch_mandi import fetch_mandi_prices
from ingestion.fetch_weather import fetch_weather

def test_mock_server_happy_path(tmp_path, monkeypatch):
    """Verifies that the mock server correctly generates healthy deterministic responses in standard scenarios."""
    monkeypatch.setattr("ingestion.fetch_mandi.RAW_DIR", str(tmp_path))
    monkeypatch.setattr("ingestion.fetch_weather.RAW_DIR", str(tmp_path))
    
    with MockAPIServer(scenario="happy_path") as server:
        # Fetch mandi prices
        mandi_records = fetch_mandi_prices("2023-01-01")
        assert len(mandi_records) > 0
        assert mandi_records[0]["commodity"] == "Tomato"
        assert mandi_records[0]["district"] == "Nashik"
        assert float(mandi_records[0]["modal_price"]) == 25.0
        assert float(mandi_records[0]["min_price"]) == 18.75  # 25 * 0.75
        
        # Fetch weather metrics
        weather_records = fetch_weather("2023-01-01")
        assert len(weather_records) == 8
        assert weather_records[0]["district"] == "Nashik"
        assert weather_records[0]["precipitation_mm"] == 5.0
        assert weather_records[0]["temp_max_c"] == 30.0
        assert weather_records[0]["temp_min_c"] == 20.0
        
        # Check telemetry logs and observability history
        assert server.request_count == 15  # 7 commodities + 8 districts
        assert len(server.request_history) == 15
        assert "api.data.gov.in" in server.request_history[0]["url"]
        assert "api.open-meteo.com" in server.request_history[-1]["url"]

def test_mock_server_server_error_resiliency(tmp_path, monkeypatch):
    """Asserts that the ingestion functions handle HTTP 500 server errors gracefully without crashing."""
    monkeypatch.setattr("ingestion.fetch_mandi.RAW_DIR", str(tmp_path))
    monkeypatch.setattr("ingestion.fetch_weather.RAW_DIR", str(tmp_path))
    
    with MockAPIServer(scenario="server_error") as server:
        mandi_records = fetch_mandi_prices("2023-01-01")
        # Under HTTP 500, fetch_mandi should handle exception and return empty records
        assert isinstance(mandi_records, list)
        assert len(mandi_records) == 0
        
        weather_records = fetch_weather("2023-01-01")
        # Under HTTP 500, fetch_weather should handle exception and return empty list
        assert isinstance(weather_records, list)
        assert len(weather_records) == 0

def test_mock_server_timeout_resiliency(tmp_path, monkeypatch):
    """Asserts that connection timeouts are handled gracefully by logging the failure and skipping records."""
    monkeypatch.setattr("ingestion.fetch_mandi.RAW_DIR", str(tmp_path))
    monkeypatch.setattr("ingestion.fetch_weather.RAW_DIR", str(tmp_path))
    
    with MockAPIServer(scenario="timeout") as server:
        mandi_records = fetch_mandi_prices("2023-01-01")
        assert len(mandi_records) == 0
        
        weather_records = fetch_weather("2023-01-01")
        assert len(weather_records) == 0

def test_mock_server_rate_limiting_partial_success(tmp_path, monkeypatch):
    """Verifies pipeline behavior under progressive rate limiting scenarios."""
    monkeypatch.setattr("ingestion.fetch_mandi.RAW_DIR", str(tmp_path))
    
    # Trigger 429 after 3 successful requests
    with MockAPIServer(scenario="rate_limit", rate_limit_threshold=3) as server:
        mandi_records = fetch_mandi_prices("2023-01-01")
        
        # We fetch 7 commodities sequentially. 3 should succeed, the next 4 should trigger 429 and be skipped.
        # Since each successful commodity returns 8 district records, total should be 3 * 8 = 24
        assert len(mandi_records) == 24
        assert server.request_count == 7
        
        # Check that the 429 requests are tracked in history
        history_429 = [r for r in server.request_history if "api.data.gov.in" in r["url"]]
        assert len(history_429) == 7

def test_mock_server_malformed_response_handling(tmp_path, monkeypatch):
    """Ensures downstream models can parse missing or malformed keys gracefully without raising exceptions."""
    monkeypatch.setattr("ingestion.fetch_mandi.RAW_DIR", str(tmp_path))
    monkeypatch.setattr("ingestion.fetch_weather.RAW_DIR", str(tmp_path))
    
    with MockAPIServer(scenario="malformed_response") as server:
        # Under malformed response, record structures might have missing keys or None values
        mandi_records = fetch_mandi_prices("2023-01-01")
        assert len(mandi_records) == 7  # 7 commodities return 1 malformed record each
        assert mandi_records[0]["commodity"] is None
        
        weather_records = fetch_weather("2023-01-01")
        # Under malformed response, list will be populated with Nones for fields
        assert len(weather_records) == 8
        assert weather_records[0]["precipitation_mm"] is None
        assert weather_records[0]["temp_max_c"] is None

def test_mock_server_randomized_scenarios(tmp_path, monkeypatch):
    """Validates dynamic statistical data generation to emulate fluctuating markets and seasonal weather."""
    monkeypatch.setattr("ingestion.fetch_mandi.RAW_DIR", str(tmp_path))
    monkeypatch.setattr("ingestion.fetch_weather.RAW_DIR", str(tmp_path))
    
    with MockAPIServer(scenario="randomized", seed=100) as server:
        mandi_records_1 = fetch_mandi_prices("2023-01-01")
        weather_records_1 = fetch_weather("2023-01-01")
        
    with MockAPIServer(scenario="randomized", seed=200) as server:
        mandi_records_2 = fetch_mandi_prices("2023-01-01")
        weather_records_2 = fetch_weather("2023-01-01")
        
    # Verify that different seeds generate mathematically randomized but schema-compliant values
    assert float(mandi_records_1[0]["modal_price"]) != float(mandi_records_2[0]["modal_price"])
    assert weather_records_1[0]["precipitation_mm"] != weather_records_2[0]["precipitation_mm"]
    assert float(mandi_records_1[0]["min_price"]) <= float(mandi_records_1[0]["modal_price"]) <= float(mandi_records_1[0]["max_price"])

def test_mock_server_latency_observability(tmp_path, monkeypatch):
    """Confirms that the response latency can be measured and tracked within the request metadata."""
    monkeypatch.setattr("ingestion.fetch_mandi.RAW_DIR", str(tmp_path))
    
    # Run a simple fetch with a simulated delay of 50ms per request
    with MockAPIServer(scenario="happy_path", delay_ms=50.0) as server:
        start_time = time.time()
        mandi_records = fetch_mandi_prices("2023-01-01")
        elapsed = time.time() - start_time
        
        # 7 commodities * 50ms = 350ms minimum duration
        assert elapsed >= 0.35
        assert len(server.request_history) == 7
        assert server.request_history[0]["timeout"] == 10  # Verifies the 10-second timeout parameter is preserved
