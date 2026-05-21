import pandas as pd

def join_mandi_weather(mandi_df: pd.DataFrame, weather_df: pd.DataFrame) -> pd.DataFrame:
    """Left join mandi data with weather data on `district` and `date`.
    Keeps all mandi rows even if weather is missing.
    """
    # Ensure columns are comparable
    mandi_df['date'] = pd.to_datetime(mandi_df['date']).dt.date
    weather_df['date'] = pd.to_datetime(weather_df['date']).dt.date
    merged = pd.merge(
        mandi_df,
        weather_df,
        how='left',
        left_on=['district', 'date'],
        right_on=['district', 'date']
    )
    return merged
