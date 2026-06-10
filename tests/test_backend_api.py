import pytest
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_metadata_endpoint():
    """Verify that metadata route returns lists of districts, commodities, and date range limits."""
    response = client.get("/api/metadata")
    assert response.status_code == 200
    data = response.json()
    assert "districts" in data
    assert "commodities" in data
    assert "min_date" in data
    assert "max_date" in data
    assert isinstance(data["districts"], list)
    assert isinstance(data["commodities"], list)

def test_data_endpoint():
    """Verify that retrieve data route functions with or without query filters."""
    response = client.get("/api/data")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        row = data[0]
        assert "commodity" in row
        assert "district" in row
        assert "modal_price" in row
        assert "date" in row
        
    # With filter query
    filtered_response = client.get("/api/data?district=Nashik&commodity=Tomato")
    assert filtered_response.status_code == 200
    filtered_data = filtered_response.json()
    assert isinstance(filtered_data, list)
    for r in filtered_data:
        assert r["commodity"] == "Tomato"
        assert r["district"] == "Nashik"

def test_alerts_endpoint():
    """Verify alerts endpoint outputs structured list of alerts."""
    response = client.get("/api/alerts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        alert = data[0]
        assert "alert_date" in alert
        assert "commodity" in alert
        assert "district" in alert
        assert "volatility_score" in alert

def test_predict_untrained_fallback():
    """Verify predict returns model_exists=False before model training."""
    payload = {
        "commodity": "Rice",
        "district": "Guntur"
    }
    # Attempt prediction for a model that shouldn't be trained yet
    # We clean up model file if it exists prior to test
    import os
    from pathlib import Path
    model_file = Path("models/saved/rice_guntur.pkl")
    if model_file.exists():
        os.remove(model_file)
        
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["model_exists"] is False
    assert "XGBoost model" in data["message"]

def test_train_and_predict_flow():
    """Verify the training trigger runs and creates a saveable XGBoost model, enabling prediction."""
    payload = {
        "commodity": "Tomato",
        "district": "Nashik"
    }
    
    # Trigger model training
    train_res = client.post("/api/train", json=payload)
    assert train_res.status_code == 200
    train_data = train_res.json()
    assert train_data["success"] is True
    assert "Successfully trained" in train_data["message"]
    
    # Trigger prediction on newly trained model
    predict_res = client.post("/api/predict", json=payload)
    assert predict_res.status_code == 200
    predict_data = predict_res.json()
    assert predict_data["model_exists"] is True
    assert "predicted_modal_price" in predict_data
    assert "latest_price" in predict_data
    assert "price_change_pct" in predict_data
    assert "volatility_label" in predict_data
    assert predict_data["predicted_modal_price"] > 0
    assert predict_data["latest_price"] > 0
