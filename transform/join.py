import pandas as pd

def join_mandi_weather(mandi_df: pd.DataFrame, weather_df: pd.DataFrame) -> pd.DataFrame:
    """
    Left join mandi on weather using district + date.
    Keep all mandi rows even if no weather match.
    """
    if mandi_df.empty:
        return mandi_df
        
    if weather_df.empty:
        return mandi_df
        
    mandi_copy = mandi_df.copy()
    weather_copy = weather_df.copy()
    
    # Ensure date columns have the same type for joining
    if 'date' in mandi_copy.columns:
        mandi_copy['date'] = pd.to_datetime(mandi_copy['date'], errors='coerce')
    if 'date' in weather_copy.columns:
        weather_copy['date'] = pd.to_datetime(weather_copy['date'], errors='coerce')
    
    # Left join
    joined_df = pd.merge(
        mandi_copy, 
        weather_copy, 
        on=['district', 'date'], 
        how='left'
    )
    
    # Drop overlapping columns if any (like state_y)
    if 'state_y' in joined_df.columns:
        joined_df = joined_df.drop(columns=['state_y'])
    if 'state_x' in joined_df.columns:
        joined_df = joined_df.rename(columns={'state_x': 'state'})
        
    return joined_df
