import os
import pickle
from pathlib import Path

import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


class PricePredictor:
    """XGBoost based price predictor for a specific commodity and district.

    The model expects the following features:
    - precipitation_mm
    - temp_max_c
    - temp_min_c
    - volatility_score
    - day_of_week (int, Monday=0)
    - month (int)
    - lag_7_price (modal_price 7 days ago)
    - lag_14_price (modal_price 14 days ago)
    """

    def __init__(self):
        self.model = None
        self.feature_names = [
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
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["day_of_week"] = df["date"].dt.dayofweek
        df["month"] = df["date"].dt.month
        df = df.sort_values("date")
        df["lag_7_price"] = df["modal_price"].shift(7)
        df["lag_14_price"] = df["modal_price"].shift(14)
        # Fill missing lags with median modal_price
        median_price = df["modal_price"].median()
        df["lag_7_price"].fillna(median_price, inplace=True)
        df["lag_14_price"].fillna(median_price, inplace=True)
        return df[self.feature_names]

    def train(self, df: pd.DataFrame, commodity: str, district: str):
        """Train the model on historical data for a given commodity and district.

        Parameters
        ----------
        df : pd.DataFrame
            Full dataset containing price and weather columns.
        commodity : str
            Commodity to filter on.
        district : str
            District to filter on.
        """
        # Filter rows
        data = df[(df["commodity"] == commodity) & (df["district"] == district)].copy()
        if data.empty:
            raise ValueError(f"No data for commodity={commodity}, district={district}")

        X = self._prepare_features(data)
        y = data["modal_price"]
        dmatrix = xgb.DMatrix(X, label=y, feature_names=self.feature_names)
        params = {
            "objective": "reg:squarederror",
            "eval_metric": "rmse",
            "seed": 42,
        }
        self.model = xgb.train(params, dmatrix, num_boost_round=200)

        # Metrics
        preds = self.model.predict(dmatrix)
        rmse = mean_squared_error(y, preds, squared=False)
        mae = mean_absolute_error(y, preds)
        r2 = r2_score(y, preds)
        print(f"Training complete for {commodity}/{district}: RMSE={rmse:.2f}, MAE={mae:.2f}, R2={r2:.3f}")

    def predict_next_week(self, latest_row: dict) -> dict:
        """Predict the modal_price for the next day given the latest row.

        `latest_row` must contain all feature columns used in training.
        """
        if self.model is None:
            raise RuntimeError("Model has not been trained or loaded.")
        # Build dataframe with a single row
        df = pd.DataFrame([latest_row])
        X = self._prepare_features(df)
        dmatrix = xgb.DMatrix(X, feature_names=self.feature_names)
        pred = self.model.predict(dmatrix)[0]
        return {"predicted_modal_price": float(pred)}

    def save(self, path: str):
        """Serialize the trained model to a pickle file.
        """
        if self.model is None:
            raise RuntimeError("No model to save.")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.model, f)
        print(f"Model saved to {path}")

    def load(self, path: str):
        """Load a previously saved model.
        """
        with open(path, "rb") as f:
            self.model = pickle.load(f)
        print(f"Model loaded from {path}")
