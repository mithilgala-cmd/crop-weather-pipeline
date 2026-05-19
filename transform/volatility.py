import pandas as pd
import numpy as np

def compute_volatility(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
        
    df = df.copy()
    
    # Add column volatility_score = (max_price - min_price) / modal_price
    df['volatility_score'] = (df['max_price'] - df['min_price']) / df['modal_price']
    
    # Add column volatility_label
    def get_label(score):
        if pd.isna(score):
            return "UNKNOWN"
        elif score > 0.3:
            return "HIGH"
        elif score > 0.1:
            return "MEDIUM"
        else:
            return "LOW"
            
    df['volatility_label'] = df['volatility_score'].apply(get_label)
    
    # Add column price_change_pct: % change in modal_price vs previous day for same commodity+district 
    # (use .shift(1) after sorting by date)
    if all(col in df.columns for col in ['commodity', 'district', 'date', 'modal_price']):
        df = df.sort_values(by=['commodity', 'district', 'date'])
        
        # Calculate percentage change and multiply by 100 to get a percentage value
        # pct_change computes (current - previous) / previous
        df['price_change_pct'] = df.groupby(['commodity', 'district'])['modal_price'].pct_change() * 100
        
    return df
