import pandas as pd

def clean_mandi(df: pd.DataFrame) -> pd.DataFrame:
    """Clean mandi price dataframe.
    - Cast price columns to float
    - Title‑case and strip string columns
    - Drop rows with null/zero modal_price
    - Parse date column to datetime
    - Remove duplicates on [date, commodity, market]
    """
    price_cols = ["min_price", "max_price", "modal_price"]
    for col in price_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    str_cols = ["district", "commodity", "state"]
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip().str.title()
    df = df.dropna(subset=["modal_price"]).copy()
    df = df[df["modal_price"] > 0]
    df["date"] = pd.to_datetime(df["date"], errors='coerce')
    df = df.drop_duplicates(subset=["date", "commodity", "market"])
    return df

def clean_weather(df: pd.DataFrame) -> pd.DataFrame:
    """Clean weather dataframe.
    - Cast numeric columns to float
    - Title‑case district
    - Fill missing precipitation with 0
    """
    numeric_cols = ["precipitation_mm", "temp_max_c", "temp_min_c", "windspeed_kmh"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df["district"] = df["district"].astype(str).str.strip().str.title()
    df["precipitation_mm"] = df["precipitation_mm"].fillna(0)
    return df
