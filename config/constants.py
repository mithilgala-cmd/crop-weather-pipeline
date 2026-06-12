"""Shared pipeline constants — single source of truth for districts and commodities."""

DISTRICTS = [
    {"name": "Nashik", "lat": 20.0059, "lon": 73.7898, "state": "Maharashtra", "base_temp": 30.0, "rain_prob": 0.15},
    {"name": "Agra", "lat": 27.1767, "lon": 78.0081, "state": "Uttar Pradesh", "base_temp": 32.0, "rain_prob": 0.10},
    {"name": "Ludhiana", "lat": 30.9010, "lon": 75.8573, "state": "Punjab", "base_temp": 28.0, "rain_prob": 0.12},
    {"name": "Guntur", "lat": 16.3067, "lon": 80.4365, "state": "Andhra Pradesh", "base_temp": 34.0, "rain_prob": 0.20},
    {"name": "Indore", "lat": 22.7196, "lon": 75.8577, "state": "Madhya Pradesh", "base_temp": 31.0, "rain_prob": 0.14},
    {"name": "Jaipur", "lat": 26.9124, "lon": 75.7873, "state": "Rajasthan", "base_temp": 35.0, "rain_prob": 0.08},
    {"name": "Patna", "lat": 25.5941, "lon": 85.1376, "state": "Bihar", "base_temp": 29.0, "rain_prob": 0.16},
    {"name": "Bhopal", "lat": 23.2599, "lon": 77.4126, "state": "Madhya Pradesh", "base_temp": 31.0, "rain_prob": 0.14},
]

COMMODITIES = ["Tomato", "Onion", "Potato", "Wheat", "Rice", "Maize", "Soybean"]

SEED_COMMODITY_PROFILES = {
    "Tomato": {"base_price": 1500.0, "volatility": 0.25},
    "Onion": {"base_price": 1800.0, "volatility": 0.20},
    "Potato": {"base_price": 1200.0, "volatility": 0.12},
    "Wheat": {"base_price": 2300.0, "volatility": 0.06},
    "Rice": {"base_price": 3100.0, "volatility": 0.05},
    "Maize": {"base_price": 1900.0, "volatility": 0.08},
    "Soybean": {"base_price": 4600.0, "volatility": 0.07},
}
