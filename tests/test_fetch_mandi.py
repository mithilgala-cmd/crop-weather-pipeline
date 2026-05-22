import json
import pathlib
from unittest.mock import patch
import pytest
from ingestion.fetch_mandi import fetch_mandi_prices

def test_fetch_mandi_prices_success(tmp_path, monkeypatch):
    # Mock response data
    mock_data = {
        "records": [
            {
                "date": "2023-01-01",
                "commodity": "Tomato",
                "district": "Nashik",
                "state": "Maharashtra",
                "market": "Nashik Market",
                "min_price": "20",
                "max_price": "30",
                "modal_price": "25"
            }
        ]
    }
    import ingestion.fetch_mandi
    monkeypatch.setattr(ingestion.fetch_mandi, 'RAW_DIR', str(tmp_path))
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_data
        result = fetch_mandi_prices("2023-01-01")
        assert isinstance(result, list)
        assert len(result) == 7
        assert result[0]["commodity"] == "Tomato"
        # Verify file was written
        expected_file = tmp_path / "mandi_2023-01-01.json"
        assert expected_file.is_file()
        with open(expected_file) as f:
            content = json.load(f)
            assert len(content) == 7
            assert content[0]["commodity"] == "Tomato"
