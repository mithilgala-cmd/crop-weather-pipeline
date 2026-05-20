import unittest
import pandas as pd
import numpy as np
from transform.clean import clean_mandi, clean_weather
from transform.join import join_mandi_weather
from transform.volatility import compute_volatility

class TestTransform(unittest.TestCase):
    
    def test_clean_mandi_drops_null_modal_price(self):
        # Create dataframe with null/negative modal price and spaces/mixed cases
        df = pd.DataFrame({
            'date': ['2026-05-19', '2026-05-19', '2026-05-19', '2026-05-19'],
            'commodity': [' tomato ', 'onion', 'potato', 'wheat'],
            'district': [' nashik ', 'nashik', 'nashik', 'nashik'],
            'state': [' maharashtra ', 'maharashtra', 'maharashtra', 'maharashtra'],
            'market': ['nashik', 'nashik', 'nashik', 'nashik'],
            'min_price': ['100', '100', '100', '100'],
            'max_price': ['200', '200', '200', '200'],
            'modal_price': ['150', None, '-10', '0']
        })
        
        cleaned = clean_mandi(df)
        
        # Expected: Tomato is cleaned and kept, others with null, negative or zero modal_price are dropped
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned.iloc[0]['commodity'], 'Tomato')
        self.assertEqual(cleaned.iloc[0]['district'], 'Nashik')
        self.assertEqual(cleaned.iloc[0]['state'], 'Maharashtra')
        self.assertEqual(cleaned.iloc[0]['modal_price'], 150.0)

    def test_compute_volatility_labels(self):
        df = pd.DataFrame({
            'commodity': ['Tomato', 'Tomato', 'Tomato'],
            'district': ['Nashik', 'Nashik', 'Nashik'],
            'min_price': [100.0, 100.0, 100.0],
            'max_price': [200.0, 120.0, 105.0],
            'modal_price': [150.0, 110.0, 102.0]
        })
        
        result = compute_volatility(df)
        
        # Volatility score = (max - min) / modal
        # Row 0: (200 - 100) / 150 = 100 / 150 = 0.6667 (> 0.3) -> HIGH
        # Row 1: (120 - 100) / 110 = 20 / 110 = 0.1818 (0.1 < score <= 0.3) -> MEDIUM
        # Row 2: (105 - 100) / 102 = 5 / 102 = 0.0490 (<= 0.1) -> LOW
        
        self.assertEqual(result.iloc[0]['volatility_label'], 'HIGH')
        self.assertEqual(result.iloc[1]['volatility_label'], 'MEDIUM')
        self.assertEqual(result.iloc[2]['volatility_label'], 'LOW')

    def test_join_mandi_weather_left_join(self):
        mandi_df = pd.DataFrame({
            'date': ['2026-05-19', '2026-05-20'],
            'district': ['Nashik', 'Nashik'],
            'commodity': ['Tomato', 'Tomato'],
            'modal_price': [150.0, 160.0]
        })
        
        weather_df = pd.DataFrame({
            'date': ['2026-05-19'],
            'district': ['Nashik'],
            'precipitation_mm': [10.0]
        })
        
        joined = join_mandi_weather(mandi_df, weather_df)
        
        # Should keep both mandi rows (left join)
        self.assertEqual(len(joined), 2)
        self.assertEqual(joined.iloc[0]['precipitation_mm'], 10.0)
        self.assertTrue(pd.isna(joined.iloc[1]['precipitation_mm']))
