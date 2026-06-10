import os
import pickle
import pandas as pd
import numpy as np
from pathlib import Path

# Optional ML imports to support lightweight serverless deployments (like Vercel)
try:
    from xgboost import XGBRegressor
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    HAS_ML = True
except ImportError:
    HAS_ML = False

class PricePredictor:
    def __init__(self):
        self.model = None
        self.features = [
            "precipitation_mm",
            "temp_max_c",
            "temp_min_c",
            "volatility_score",
            "day_of_week",
            "month",
            "lag_7_price",
            "lag_14_price",
        ]

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # Ensure 'date' is present
        if "date" not in df.columns:
            df["date"] = pd.date_range(start="2023-01-01", periods=len(df))
        else:
            df["date"] = pd.to_datetime(df["date"])
            
        df["day_of_week"] = df["date"].dt.dayofweek
        df["month"] = df["date"].dt.month
        
        # If 'precipitation_mm' is missing but 'precipitation_sum' is present, map it
        if "precipitation_mm" not in df.columns and "precipitation_sum" in df.columns:
            df["precipitation_mm"] = df["precipitation_sum"]
            
        # Ensure basic feature columns exist
        for f in ["precipitation_mm", "temp_max_c", "temp_min_c", "volatility_score"]:
            if f not in df.columns:
                df[f] = 0.0
        
        # Ensure lag_7_price and lag_14_price exist
        if "lag_7_price" not in df.columns:
            if "modal_price" in df.columns:
                sort_cols = []
                for c in ["district", "commodity", "date"]:
                    if c in df.columns:
                        sort_cols.append(c)
                if sort_cols:
                    df = df.sort_values(sort_cols).reset_index(drop=True)
                
                groupby_cols = []
                for c in ["district", "commodity"]:
                    if c in df.columns:
                        groupby_cols.append(c)
                
                if groupby_cols:
                    df["lag_7_price"] = df.groupby(groupby_cols)["modal_price"].shift(7)
                else:
                    df["lag_7_price"] = df["modal_price"].shift(7)
            else:
                df["lag_7_price"] = 0.0
                
        if "lag_14_price" not in df.columns:
            if "modal_price" in df.columns:
                sort_cols = []
                for c in ["district", "commodity", "date"]:
                    if c in df.columns:
                        sort_cols.append(c)
                if sort_cols:
                    df = df.sort_values(sort_cols).reset_index(drop=True)
                
                groupby_cols = []
                for c in ["district", "commodity"]:
                    if c in df.columns:
                        groupby_cols.append(c)
                
                if groupby_cols:
                    df["lag_14_price"] = df.groupby(groupby_cols)["modal_price"].shift(14)
                else:
                    df["lag_14_price"] = df["modal_price"].shift(14)
            else:
                df["lag_14_price"] = 0.0

        # Fill lag NaNs safely using modern pandas methods
        df["lag_7_price"] = df["lag_7_price"].ffill().bfill().fillna(0.0)
        df["lag_14_price"] = df["lag_14_price"].ffill().bfill().fillna(0.0)
        
        # Safe numeric cast and fill for all features
        for f in self.features:
            if f in df.columns:
                df[f] = pd.to_numeric(df[f], errors="coerce").fillna(0.0)
                
        return df[self.features]

    def train(self, df: pd.DataFrame, commodity: str, district: str):
        # Handle cases where training data is passed without commodity/district grouping columns
        if "commodity" in df.columns and "district" in df.columns:
            data = df[(df["commodity"] == commodity) & (df["district"] == district)]
        else:
            data = df.copy()
            data["commodity"] = commodity
            data["district"] = district
            
        if data.empty:
            raise ValueError(f"No training data found for {commodity} and {district}")
            
        if HAS_ML:
            X = self._prepare_features(data)
            y = data["modal_price"]
            self.model = XGBRegressor(objective="reg:squarederror", n_estimators=200, learning_rate=0.05)
            self.model.fit(X, y)
            preds = self.model.predict(X)
            
            rmse = float(mean_squared_error(y, preds) ** 0.5)
            mae = float(mean_absolute_error(y, preds))
            r2 = float(r2_score(y, preds))
            
            print("Training metrics (XGBoost):")
            print(f"RMSE: {rmse:.4f}")
            print(f"MAE: {mae:.4f}")
            print(f"R^2: {r2:.4f}")
        else:
            # Fallback simple linear regression using numpy
            y = data["modal_price"].values
            x = np.arange(len(y))
            if len(y) > 1:
                slope, intercept = np.polyfit(x, y, 1)
            else:
                slope, intercept = 0.0, float(y[0]) if len(y) > 0 else 100.0
                
            self.model = {
                "is_fallback": True,
                "slope": float(slope),
                "intercept": float(intercept),
                "latest_price": float(y[-1]) if len(y) > 0 else 100.0
            }
            print("Training metrics (Fallback Simple Linear Regression):")
            print(f"Slope: {slope:.4f}, Intercept: {intercept:.4f}")

    def predict_next_week(self, latest_row: dict) -> dict:
        if self.model is None:
            raise ValueError("Model not trained.")
            
        if isinstance(self.model, dict) and self.model.get("is_fallback"):
            # Fallback linear forecast
            latest_price = latest_row.get("modal_price")
            if latest_price is None:
                latest_price = self.model.get("latest_price", 100.0)
            
            slope = self.model.get("slope", 0.0)
            pred = float(latest_price) + (slope * 7)
            # Ensure price doesn't drop below 40% of latest
            pred = max(pred, float(latest_price) * 0.4)
            return {
                "predicted_modal_price": float(pred),
                "predicted_price": float(pred)
            }
        else:
            # Standard XGBoost inference
            df = pd.DataFrame([latest_row])
            X = self._prepare_features(df)
            pred = self.model.predict(X)[0]
            return {
                "predicted_modal_price": float(pred),
                "predicted_price": float(pred)
            }

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.model, f)

    def load(self, path: str):
        with open(path, "rb") as f:
            self.model = pickle.load(f)
