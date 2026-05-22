import pandas as pd


def join_mandi_weather(mandi_df: pd.DataFrame, weather_df: pd.DataFrame) -> pd.DataFrame:
    """Left join mandi data with weather on `district` and `date`.
    
    Parameters
    ----------
    mandi_df : pd.DataFrame
        Cleaned mandi price data.
    weather_df : pd.DataFrame
        Cleaned weather data.
    
    Returns
    -------
    pd.DataFrame
        DataFrame containing all mandi rows plus matching weather columns where available.
    """
    mandi_df = mandi_df.copy()
    weather_df = weather_df.copy()
    # Ensure date columns are datetime for both frames
    mandi_df['date'] = pd.to_datetime(mandi_df['date'])
    weather_df['date'] = pd.to_datetime(weather_df['date'])
    # Perform left join on district and date
    merged = pd.merge(
        mandi_df,
        weather_df,
        how='left',
        on=['district', 'date'],
        suffixes=('', '_weather')
    )
    return merged
