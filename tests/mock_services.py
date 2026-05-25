import json
import time
import random
from typing import Dict, List, Any, Optional, Union
from unittest.mock import patch, Mock
import requests

class MockResponse:
    """Mock standard requests.Response object for robust API mocking."""
    def __init__(self, json_data: Any, status_code: int = 200, headers: Optional[Dict[str, str]] = None):
        self._json = json_data
        self.status_code = status_code
        self.headers = headers or {"Content-Type": "application/json"}

    def json(self) -> Any:
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            http_error_msg = f"{self.status_code} Client/Server Error"
            raise requests.exceptions.HTTPError(http_error_msg, response=self)

class MockAPIServer:
    """Enterprise API Mocking and Observability Server for Mandi and Open-Meteo APIs."""
    
    DISTRICTS = [
        {"name": "Nashik", "lat": 20.0059, "lon": 73.7898, "state": "Maharashtra"},
        {"name": "Agra", "lat": 27.1767, "lon": 78.0081, "state": "Uttar Pradesh"},
        {"name": "Ludhiana", "lat": 30.9010, "lon": 75.8573, "state": "Punjab"},
        {"name": "Guntur", "lat": 16.3067, "lon": 80.4365, "state": "Andhra Pradesh"},
        {"name": "Indore", "lat": 22.7196, "lon": 75.8577, "state": "Madhya Pradesh"},
        {"name": "Jaipur", "lat": 26.9124, "lon": 75.7873, "state": "Rajasthan"},
        {"name": "Patna", "lat": 25.5941, "lon": 85.1376, "state": "Bihar"},
        {"name": "Bhopal", "lat": 23.2599, "lon": 77.4126, "state": "Madhya Pradesh"},
    ]
    
    COMMODITIES = ["Tomato", "Onion", "Potato", "Wheat", "Rice", "Maize", "Soybean"]

    def __init__(self, scenario: str = "happy_path", delay_ms: float = 0.0, rate_limit_threshold: int = 5, seed: int = 42):
        self.scenario = scenario
        self.delay_ms = delay_ms
        self.rate_limit_threshold = rate_limit_threshold
        self.seed = seed
        
        self.request_count = 0
        self.request_history = []
        self._patcher = None
        
        # Reset the random state for reproducible randomized testing
        random.seed(seed)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self) -> None:
        """Starts intercepting requests.get calls with the mock server."""
        self._patcher = patch("requests.get", side_effect=self.handle_request)
        self._patcher.start()

    def stop(self) -> None:
        """Stops intercepting requests."""
        if self._patcher:
            self._patcher.stop()

    def handle_request(self, url: str, *args, **kwargs) -> MockResponse:
        """Central router and proxy for intercepted HTTP requests."""
        self.request_count += 1
        
        # Record raw request observability parameters
        request_metadata = {
            "timestamp": time.time(),
            "request_index": self.request_count,
            "url": url,
            "params": kwargs.get("params", {}),
            "headers": kwargs.get("headers", {}),
            "timeout": kwargs.get("timeout", None)
        }
        self.request_history.append(request_metadata)

        # Inject configured latency
        if self.delay_ms > 0:
            time.sleep(self.delay_ms / 1000.0)

        # Route requests based on scenario parameters
        if self.scenario == "server_error":
            return MockResponse({"error": "Internal Server Error"}, status_code=500)
            
        elif self.scenario == "rate_limit" and self.request_count > self.rate_limit_threshold:
            return MockResponse({"error": "Too Many Requests", "retry_after": 60}, status_code=429)
            
        elif self.scenario == "timeout":
            raise requests.exceptions.Timeout(f"Mock Connection to {url} timed out.")

        # Identify which API is requested
        if "api.data.gov.in" in url:
            return self._mock_mandi_api(kwargs.get("params", {}))
        elif "api.open-meteo.com" in url:
            return self._mock_weather_api(kwargs.get("params", {}))
        else:
            return MockResponse({"message": "Unknown Endpoint"}, status_code=404)

    def _mock_mandi_api(self, params: Dict[str, Any]) -> MockResponse:
        """Generates realistic mock data mimicking India's data.gov.in mandi portal."""
        if self.scenario == "malformed_response":
            # Returns corrupted schema (e.g. empty lists, string lists, or missing keys)
            return MockResponse({"records": [{"commodity": None, "invalid_key": True}]})

        commodity = params.get("filters[commodity]", "Tomato")
        date = params.get("filters[date]", "2023-01-01")
        
        records = []
        
        # In happy path and randomized scenario, return realistic items
        for dist in self.DISTRICTS:
            # Generate deterministic values based on commodity/district/date
            base_price = self._get_base_price(commodity)
            variance = self._get_volatility_variance(dist["name"], base_price)
            
            if self.scenario == "randomized":
                # Inject a dynamic fluctuation factor
                fluctuation = random.uniform(-0.15, 0.25)
                modal = round(base_price * (1 + fluctuation), 2)
                min_p = round(modal * (1 - random.uniform(0.05, 0.15)), 2)
                max_p = round(modal * (1 + random.uniform(0.1, 0.3)), 2)
            else:
                # Flat happy path responses
                modal = base_price
                min_p = base_price - variance
                max_p = base_price + variance
                
            records.append({
                "date": date,
                "commodity": commodity,
                "district": dist["name"],
                "state": dist["state"],
                "market": f"{dist['name']} Market",
                "min_price": str(min_p),
                "max_price": str(max_p),
                "modal_price": str(modal)
            })
            
        return MockResponse({"records": records}, status_code=200)

    def _mock_weather_api(self, params: Dict[str, Any]) -> MockResponse:
        """Generates weather metrics aligned with the Open-Meteo daily response schemas."""
        if self.scenario == "malformed_response":
            return MockResponse({"daily": {}})

        lat = params.get("latitude")
        lon = params.get("longitude")
        
        # Match back to district list
        district_name = "Nashik"
        for dist in self.DISTRICTS:
            if abs(dist["lat"] - float(lat)) < 0.1 and abs(dist["lon"] - float(lon)) < 0.1:
                district_name = dist["name"]
                break

        if self.scenario == "randomized":
            # Generate dynamic realistic meteorological metrics
            precipitation = round(max(0.0, random.gauss(2.5, 5.0)), 2)
            temp_max = round(random.uniform(22.0, 42.0), 1)
            temp_min = round(temp_max - random.uniform(8.0, 15.0), 1)
            windspeed = round(random.uniform(5.0, 25.0), 1)
        else:
            # Deterministic, standard healthy metrics
            precipitation = 5.0 if district_name == "Nashik" else 0.0
            temp_max = 30.0
            temp_min = 20.0
            windspeed = 12.0
            
        return MockResponse({
            "daily": {
                "time": [params.get("start_date", "2023-01-01")],
                "precipitation_sum": [precipitation],
                "temperature_2m_max": [temp_max],
                "temperature_2m_min": [temp_min],
                "windspeed_10m_max": [windspeed]
            }
        }, status_code=200)

    def _get_base_price(self, commodity: str) -> float:
        """Returns standard commodity market price base metrics."""
        prices = {
            "Tomato": 25.0,
            "Onion": 30.0,
            "Potato": 20.0,
            "Wheat": 22.0,
            "Rice": 45.0,
            "Maize": 18.0,
            "Soybean": 50.0
        }
        return prices.get(commodity, 25.0)

    def _get_volatility_variance(self, district: str, base_price: float) -> float:
        """Calculates mock volatility variances based on district profiles."""
        volatilities = {
            "Nashik": 0.25,  # Onion & Tomato hubs have higher default swings
            "Agra": 0.15,
            "Ludhiana": 0.08,
            "Guntur": 0.18
        }
        factor = volatilities.get(district, 0.1)
        return round(base_price * factor, 2)
