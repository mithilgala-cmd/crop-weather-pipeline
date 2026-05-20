import os
import json
import unittest
from unittest.mock import patch, mock_open, MagicMock
from ingestion.fetch_mandi import fetch_mandi_prices

class TestFetchMandi(unittest.TestCase):
    
    @patch('ingestion.fetch_mandi.requests.get')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_fetch_mandi_prices_success(self, mock_makedirs, mock_file, mock_get):
        # Configure mocked response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "records": [
                {
                    "arrival_date": "2026-05-19",
                    "commodity": "Tomato",
                    "district": "Nashik",
                    "state": "Maharashtra",
                    "market": "Nashik",
                    "min_price": "100",
                    "max_price": "200",
                    "modal_price": "150"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Call fetch function
        records = fetch_mandi_prices("2026-05-19")
        
        # Verify returned data
        self.assertTrue(len(records) > 0)
        
        # Check all required keys exist in returned records
        first_record = records[0]
        keys = ["date", "commodity", "district", "state", "market", "min_price", "max_price", "modal_price"]
        for key in keys:
            self.assertIn(key, first_record)
            
        self.assertEqual(first_record["commodity"], "Tomato")
        self.assertEqual(first_record["modal_price"], "150")

    @patch('ingestion.fetch_mandi.requests.get')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_fetch_mandi_prices_failure(self, mock_makedirs, mock_file, mock_get):
        # Mock requests exception
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("API Failure")
        
        # Call fetch function
        records = fetch_mandi_prices("2026-05-19")
        
        # Should not raise exception, but return empty list
        self.assertEqual(records, [])
