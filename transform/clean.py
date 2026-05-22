import pandas as pd


def clean_mandi(df: pd.DataFrame) -> pd.DataFrame:
    """Clean mandi price DataFrame.

    - Cast price columns to float
    - Strip and title‑case string columns
    - Drop rows with null or non‑positive modal_price
    - Parse date column
    - Remove duplicates on [date, commodity, market]
    """
    # Cast numeric columns
    for col in ["min_price", "max_price", "modal_price"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # Strip and title‑case string columns
    for col in ["district", "commodity", "state"]:
        df[col] = df[col].astype(str).str.strip().str.title()
    # Drop invalid modal_price rows
    df = df.dropna(subset=["modal_price"])
    df = df[df["modal_price"] > 0]
    # Parse date
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    # Remove duplicates
    df = df.drop_duplicates(subset=["date", "commodity", "market"])
    return df


def clean_weather(df: pd.DataFrame) -> pd.DataFrame:
    """Clean weather DataFrame.

    - Cast numeric columns to float
    - Strip and title‑case district
    - Fill missing precipitation with 0
    """
    numeric_cols = ["precipitation_sum", "temperature_2m_max", "temperature_2m_min", "windspeed_10m_max"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["district"] = df["district"].astype(str).str.strip().str.title()
    df["precipitation_sum"] = df["precipitation_sum"].fillna(0)
    return df
