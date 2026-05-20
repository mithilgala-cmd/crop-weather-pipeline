import os
import pickle
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from typing import Dict, Any

class PricePredictor:
    def __init__(self):
        self.model = xgb.XGBRegressor(
            objective='reg:squarederror',
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        self.features = [
            'precipitation_mm', 
            'temp_max_c', 
            'temp_min_c', 
            'volatility_score', 
            'day_of_week', 
            'month', 
            'lag_7_price', 
            'lag_14_price'
        ]

    def _prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # Ensure date is datetime
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Create time features
        df['day_of_week'] = df['date'].dt.dayofweek
        df['month'] = df['date'].dt.month
        
        # Create lag features
        df['lag_7_price'] = df['modal_price'].shift(7)
        df['lag_14_price'] = df['modal_price'].shift(14)
        
        # Create target (next day's modal price)
        df['target_price'] = df['modal_price'].shift(-1)
        
        return df

    def train(self, df: pd.DataFrame, commodity: str, district: str):
        """Train the model on historical data for a specific commodity and district."""
        # Filter for specific commodity and district
        filtered_df = df[(df['commodity'] == commodity) & (df['district'] == district)]
        
        if len(filtered_df) < 15:
            print(f"Not enough data to train model for {commodity} in {district} (needs at least 15 days)")
            return
            
        prepared_df = self._prepare_data(filtered_df)
        
        # Drop rows with NaN (due to lags or missing target for the last day)
        train_df = prepared_df.dropna(subset=self.features + ['target_price'])
        
        if train_df.empty:
            print(f"No complete data available for training {commodity} in {district}")
            return
            
        X = train_df[self.features]
        y = train_df['target_price']
        
        self.model.fit(X, y)
        
        predictions = self.model.predict(X)
        
        rmse = np.sqrt(mean_squared_error(y, predictions))
        mae = mean_absolute_error(y, predictions)
        r2 = r2_score(y, predictions)
        
        print(f"--- Training Metrics for {commodity} in {district} ---")
        print(f"RMSE: {rmse:.4f}")
        print(f"MAE:  {mae:.4f}")
        print(f"R²:   {r2:.4f}")
        
    def predict_next_week(self, latest_row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict the next day's price given the latest available row.
        """
        row_copy = dict(latest_row)
        
        if 'date' in row_copy:
            date_obj = pd.to_datetime(row_copy['date'])
            if 'day_of_week' not in row_copy or pd.isna(row_copy.get('day_of_week')):
                row_copy['day_of_week'] = date_obj.dayofweek
            if 'month' not in row_copy or pd.isna(row_copy.get('month')):
                row_copy['month'] = date_obj.month
                
        if 'modal_price' in row_copy:
            if 'lag_7_price' not in row_copy or pd.isna(row_copy.get('lag_7_price')):
                row_copy['lag_7_price'] = row_copy['modal_price']
            if 'lag_14_price' not in row_copy or pd.isna(row_copy.get('lag_14_price')):
                row_copy['lag_14_price'] = row_copy['modal_price']

        # Convert to DataFrame to ensure correct order and shape
        input_df = pd.DataFrame([row_copy])
        
        # Ensure all required features are present
        missing_features = [f for f in self.features if f not in input_df.columns or pd.isna(input_df[f].iloc[0])]
        if missing_features:
            raise ValueError(f"Missing required features: {missing_features}")
                
        X = input_df[self.features]
        pred = self.model.predict(X)[0]
        
        return {"predicted_price": float(pred)}

    def save(self, path: str):
        """Save the model as a pickle file."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            pickle.dump(self.model, f)
        print(f"Model saved to {path}")

    def load(self, path: str):
        """Load the model from a pickle file."""
        with open(path, 'rb') as f:
            self.model = pickle.load(f)
        print(f"Model loaded from {path}")
