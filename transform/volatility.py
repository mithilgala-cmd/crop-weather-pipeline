import pandas as pd
import numpy as np


def compute_volatility(df: pd.DataFrame) -> pd.DataFrame:
    """Compute volatility score, label, and day‑over‑day price change.

    Adds three columns:
    - ``volatility_score`` = (max_price - min_price) / modal_price
    - ``volatility_label`` based on score thresholds
    - ``price_change_pct`` percentage change of ``modal_price`` compared to the previous day for the same commodity & district
    """
    # Ensure numeric columns are float
    for col in ["min_price", "max_price", "modal_price"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Compute volatility_score safely (avoid division by zero)
    df["volatility_score"] = (df["max_price"] - df["min_price"]) / df["modal_price"].replace({0: pd.NA})

    # Assign volatility_label using numpy.select
    conditions = [
        df["volatility_score"] > 0.3,
        (df["volatility_score"] > 0.1) & (df["volatility_score"] <= 0.3),
        df["volatility_score"] <= 0.1,
    ]
    choices = ["HIGH", "MEDIUM", "LOW"]
    df["volatility_label"] = np.select(conditions, choices, default=pd.NA)

    # Compute price_change_pct per commodity and district
    df = df.sort_values(by=["commodity", "district", "date"]).reset_index(drop=True)
    df["price_change_pct"] = (
        df.groupby(["commodity", "district"])["modal_price"].pct_change() * 100
    )
    return df
