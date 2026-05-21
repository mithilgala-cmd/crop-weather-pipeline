import os
import pandas as pd
import duckdb
import streamlit as st
import plotly.express as px
from pathlib import Path

# Load DuckDB path from env
DUCKDB_PATH = os.getenv('DUCKDB_PATH', './data/crop_weather.duckdb')

@st.cache_resource
def get_duckdb_conn():
    return duckdb.connect(database=DUCKDB_PATH, read_only=False)

@st.cache_data(ttl=300)
def load_data():
    con = get_duckdb_conn()
    df = con.execute('SELECT * FROM price_weather').fetchdf()
    con.close()
    df['date'] = pd.to_datetime(df['date'])
    return df

def main():
    st.set_page_config(page_title='Crop Price & Weather Dashboard', layout='wide')
    st.title('🌾 Crop Price & Weather Correlation Engine')

    df = load_data()

    # Sidebar filters
    districts = df['district'].unique().tolist()
    commodities = df['commodity'].unique().tolist()
    st.sidebar.header('Filters')
    selected_districts = st.sidebar.multiselect('District(s)', districts, default=districts[:3])
    selected_commodities = st.sidebar.multiselect('Commodity(ies)', commodities, default=commodities[:3])
    date_range = st.sidebar.date_input('Date range', [], help='Select start and end dates')
    if len(date_range) == 2:
        start_date, end_date = date_range
        mask = (df['date'] >= pd.Timestamp(start_date)) & (df['date'] <= pd.Timestamp(end_date))
        df = df.loc[mask]
    df = df[df['district'].isin(selected_districts) & df['commodity'].isin(selected_commodities)]

    # Section 1: Price Trend
    st.subheader('📈 Price Trend')
    fig_price = px.line(df, x='date', y='modal_price', color='commodity',
                       title='Modal Price Over Time')
    st.plotly_chart(fig_price, use_container_width=True)

    # Section 2: Weather Overlay
    st.subheader('☔ Weather Overlay')
    fig_weather = px.line(df, x='date', y='precipitation_mm', color='commodity',
                         title='Precipitation (mm) Over Time')
    fig_weather.update_yaxes(title_text='Precipitation (mm)')
    st.plotly_chart(fig_weather, use_container_width=True)

    # Section 3: Volatility Heatmap
    st.subheader('🔥 Volatility Heatmap')
    heatmap_df = df.groupby(['district', 'commodity'])['volatility_score'].mean().reset_index()
    heatmap = px.density_heatmap(heatmap_df, x='district', y='commodity', z='volatility_score',
                                 color_continuous_scale='RdYlGn_r',
                                 title='Average Volatility')
    st.plotly_chart(heatmap, use_container_width=True)

    # Section 4: Alerts Table
    st.subheader('🚨 High Volatility Alerts')
    alerts = con = get_duckdb_conn()
    alerts_df = con.execute('SELECT * FROM alerts WHERE volatility_label = \'HIGH\'').fetchdf()
    con.close()
    st.dataframe(alerts_df)

    # Bottom: Prediction Card
    st.subheader('🔮 Next‑Week Price Prediction')
    predictor_path = Path('models/saved')
    if not predictor_path.exists():
        st.info('No trained model found yet.')
    else:
        st.info('Model loading and prediction UI to be implemented.')

if __name__ == '__main__':
    main()
