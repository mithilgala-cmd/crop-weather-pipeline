import pandas as pd
import numpy as np

def clean_mandi(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
        
    df = df.copy()
    
    # Cast to float
    for col in ['min_price', 'max_price', 'modal_price']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
    # Drop rows where modal_price is null or <= 0
    if 'modal_price' in df.columns:
        df = df.dropna(subset=['modal_price'])
        df = df[df['modal_price'] > 0]
    
    # Strip + title-case
    for col in ['district', 'commodity', 'state']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()
            
    # Parse date column to datetime
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
    # Remove duplicates
    if all(col in df.columns for col in ['date', 'commodity', 'market']):
        df = df.drop_duplicates(subset=['date', 'commodity', 'market'])
    
    return df

def clean_weather(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
        
    df = df.copy()
    
    # Cast all numeric cols to float
    numeric_cols = ['precipitation_mm', 'temp_max_c', 'temp_min_c', 'windspeed_kmh']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    # Strip + title-case district
    if 'district' in df.columns:
        df['district'] = df['district'].astype(str).str.strip().str.title()
        
    # Fill missing precipitation_mm with 0
    if 'precipitation_mm' in df.columns:
        df['precipitation_mm'] = df['precipitation_mm'].fillna(0)
        
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')

    return df
