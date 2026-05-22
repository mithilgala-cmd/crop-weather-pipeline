import os
import pickle
import pandas as pd
from pathlib import Path
from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

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
        df["date"] = pd.to_datetime(df["date"])
        df["day_of_week"] = df["date"].dt.dayofweek
        df["month"] = df["date"].dt.month
        df = df.sort_values(["district", "commodity", "date"]).reset_index(drop=True)
        df["lag_7_price"] = df.groupby(["district", "commodity"]).shift(7)["modal_price"].fillna(method="ffill")
        df["lag_14_price"] = df.groupby(["district", "commodity"]).shift(14)["modal_price"].fillna(method="ffill")
        return df[self.features]

    def train(self, df: pd.DataFrame, commodity: str, district: str):
        data = df[(df["commodity"] == commodity) & (df["district"] == district)]
        X = self._prepare_features(data)
        y = data["modal_price"]
        self.model = XGBRegressor(objective="reg:squarederror", n_estimators=200, learning_rate=0.05)
        self.model.fit(X, y)
        preds = self.model.predict(X)
        print("Training metrics:")
        print(f"RMSE: {mean_squared_error(y, preds, squared=False):.4f}")
        print(f"MAE: {mean_absolute_error(y, preds):.4f}")
        print(f"R^2: {r2_score(y, preds):.4f}")

    def predict_next_week(self, latest_row: dict) -> dict:
        if self.model is None:
            raise ValueError("Model not trained.")
        df = pd.DataFrame([latest_row])
        X = self._prepare_features(df)
        pred = self.model.predict(X)[0]
        return {"predicted_modal_price": pred}

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.model, f)

    def load(self, path: str):
        with open(path, "rb") as f:
            self.model = pickle.load(f)
