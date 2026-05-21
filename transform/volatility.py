import pandas as pd


def compute_volatility(df: pd.DataFrame) -> pd.DataFrame:
    """Compute volatility score and related columns.
    - volatility_score = (max_price - min_price) / modal_price
    - volatility_label based on score thresholds
    - price_change_pct: % change of modal_price vs previous day per commodity+district
    """
    # Ensure numeric columns
    price_cols = ["min_price", "max_price", "modal_price"]
    for col in price_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Calculate volatility_score
    df["volatility_score"] = (df["max_price"] - df["min_price"]) / df["modal_price"]
    df["volatility_score"] = df["volatility_score"].round(4)

    # Assign volatility_label
    def label(score):
        if score > 0.3:
            return "HIGH"
        if score > 0.1:
            return "MEDIUM"
        return "LOW"
    df["volatility_label"] = df["volatility_score"].apply(label)

    # Compute price_change_pct per commodity+district sorted by date
    df = df.sort_values(["date", "commodity", "district"]).copy()
    df["price_change_pct"] = (
        df.groupby(["commodity", "district"])["modal_price"].pct_change() * 100
    ).round(2)
    return df
