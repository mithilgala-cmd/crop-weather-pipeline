import os
import sys
import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# Ensure parent directory is on path to import models
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.price_predictor import PricePredictor

# Page config with premium visual setup
st.set_page_config(
    page_title="Crop Price & Weather Analytics",
    page_icon="🌾",
    layout="wide"
)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "./data/crop_weather.duckdb")

# Helper to get database connection
def get_connection():
    return duckdb.connect(DUCKDB_PATH, read_only=True)

# ----------------- DATA LOADING -----------------
@st.cache_data
def get_unique_options():
    try:
        conn = get_connection()
        districts = [r[0] for r in conn.execute("SELECT DISTINCT district FROM price_weather WHERE district IS NOT NULL").fetchall()]
        commodities = [r[0] for r in conn.execute("SELECT DISTINCT commodity FROM price_weather WHERE commodity IS NOT NULL").fetchall()]
        
        # Get min and max dates
        date_res = conn.execute("SELECT MIN(date), MAX(date) FROM price_weather").fetchone()
        min_date = pd.to_datetime(date_res[0]).date() if date_res[0] else datetime.now().date() - timedelta(days=30)
        max_date = pd.to_datetime(date_res[1]).date() if date_res[1] else datetime.now().date()
        
        conn.close()
        return sorted(districts), sorted(commodities), min_date, max_date
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return [], [], datetime.now().date() - timedelta(days=30), datetime.now().date()

districts, commodities, db_min_date, db_max_date = get_unique_options()

# ----------------- SIDEBAR -----------------
st.sidebar.title("🌾 Filter Controls")
st.sidebar.markdown("Filter agricultural prices and local weather data to analyze price crash warnings.")

selected_districts = st.sidebar.multiselect(
    "Select Districts",
    options=districts,
    default=districts[:4] if districts else []
)

selected_commodities = st.sidebar.multiselect(
    "Select Commodities",
    options=commodities,
    default=commodities[:3] if commodities else []
)

# Date range picker
default_start = db_max_date - timedelta(days=30) if db_max_date else datetime.now().date() - timedelta(days=30)
default_end = db_max_date if db_max_date else datetime.now().date()

# Guard in case min and max dates are invalid
if db_min_date > db_max_date:
    db_min_date, db_max_date = db_max_date, db_min_date

date_range = st.sidebar.date_input(
    "Date Range",
    value=(default_start, default_end),
    min_value=db_min_date,
    max_value=db_max_date
)

# Check if selected_districts and selected_commodities are empty
if not selected_districts or not selected_commodities:
    st.warning("👈 Please select at least one district and one commodity in the sidebar to load the analytics dashboard.")
    st.stop()

# Parse date range
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = default_start, default_end

# ----------------- QUERY DATA -----------------
def load_filtered_data(districts, commodities, start, end):
    conn = get_connection()
    
    # Parametrized string substitution for in-list
    district_list = ", ".join([f"'{d}'" for d in districts])
    commodity_list = ", ".join([f"'{c}'" for c in commodities])
    
    query = f"""
        SELECT date, commodity, district, state, market, min_price, max_price, modal_price, 
               precipitation_mm, temp_max_c, temp_min_c, windspeed_kmh, volatility_score, 
               volatility_label, price_change_pct 
        FROM price_weather
        WHERE district IN ({district_list})
          AND commodity IN ({commodity_list})
          AND date BETWEEN ? AND ?
        ORDER BY date ASC
    """
    
    df = conn.execute(query, (start, end)).df()
    conn.close()
    return df

df = load_filtered_data(selected_districts, selected_commodities, start_date, end_date)

# ----------------- HEADER -----------------
st.title("🌾 Indian Crop Price & Weather Correlation Engine")
st.markdown("""
This system correlates dynamic mandi price movements across major agricultural hubs with local meteorological metrics 
(rainfall, temperature) to anticipate price volatility and mitigate crop-market risk.
""")

if df.empty:
    st.info("No mandi price data found matching the selected filters.")
    st.stop()

# ----------------- SECTION 1 & 2: Price Trend Chart with Weather Overlay -----------------
st.subheader("📈 Price Trends & Weather Correlation")
st.markdown("Visualizing daily modal prices (line charts) contrasted against regional precipitation totals (underlaid bars).")

# Create figure with secondary y-axis
fig = make_subplots(specs=[[{"secondary_y": True}]])

# Add price lines per commodity
for commodity in selected_commodities:
    comm_df = df[df['commodity'] == commodity]
    if not comm_df.empty:
        # Group by date to average across markets/districts if multiple selected
        grouped = comm_df.groupby('date').agg({'modal_price': 'mean'}).reset_index()
        fig.add_trace(
            go.Scatter(
                x=grouped['date'], 
                y=grouped['modal_price'], 
                name=f"{commodity} Avg Price", 
                mode='lines+markers',
                line=dict(width=2.5)
            ),
            secondary_y=False,
        )

# Add weather bars (averaged across selected districts)
weather_grouped = df.groupby('date')['precipitation_mm'].mean().reset_index()
fig.add_trace(
    go.Bar(
        x=weather_grouped['date'], 
        y=weather_grouped['precipitation_mm'], 
        name="Avg Precipitation (mm)", 
        opacity=0.25, 
        marker_color="dodgerblue"
    ),
    secondary_y=True,
)

fig.update_layout(
    xaxis_title="Date",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ),
    margin=dict(l=40, r=40, t=40, b=40),
    hovermode="x unified"
)

fig.update_yaxes(title_text="Modal Price (₹/Quintal)", secondary_y=False)
fig.update_yaxes(title_text="Precipitation (mm)", secondary_y=True)

st.plotly_chart(fig, use_container_width=True)

# ----------------- HEATMAP & ALERTS LAYOUT -----------------
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🔥 Volatility Heatmap")
    st.markdown("Average price volatility `(max_price - min_price) / modal_price` by district and commodity.")
    
    # Compute average volatility by district and commodity
    heatmap_data = df.groupby(['district', 'commodity'])['volatility_score'].mean().unstack(fill_value=0)
    
    if not heatmap_data.empty:
        fig_heatmap = px.imshow(
            heatmap_data,
            labels=dict(x="Commodity", y="District", color="Avg Volatility"),
            x=heatmap_data.columns,
            y=heatmap_data.index,
            color_continuous_scale="RdYlGn_r",  # green (low) -> red (high)
            aspect="auto"
        )
        fig_heatmap.update_layout(
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)
    else:
        st.info("Insufficient data to build a volatility heatmap.")

with col2:
    st.subheader("🚨 High Volatility Alerts")
    st.markdown("Automated alarms raised when the price spread exceeds 30% of modal market rates.")
    
    def load_alerts(start, end):
        conn = get_connection()
        query = """
            SELECT alert_date, commodity, district, volatility_score, modal_price, precipitation_mm, alert_reason
            FROM alerts
            WHERE alert_date BETWEEN ? AND ?
            ORDER BY alert_date DESC
        """
        alerts_df = conn.execute(query, (start, end)).df()
        conn.close()
        return alerts_df

    alerts_df = load_alerts(start_date, end_date)

    def style_alerts(row):
        # Highlight high volatility alerts in red
        return ['background-color: rgba(220, 53, 69, 0.25)' if row['volatility_score'] > 0.3 else '' for _ in row]

    if not alerts_df.empty:
        # Filter table based on sidebar selections
        filtered_alerts = alerts_df[
            alerts_df['district'].isin(selected_districts) & 
            alerts_df['commodity'].isin(selected_commodities)
        ]
        
        if not filtered_alerts.empty:
            st.dataframe(
                filtered_alerts.style.apply(style_alerts, axis=1),
                use_container_width=True,
                height=300
            )
        else:
            st.success("No alerts triggered for selected district + commodity combinations.")
    else:
        st.success("No volatility alerts triggered globally for this time range.")

# ----------------- SECTION 5: Predictions (Bottom) -----------------
st.subheader("🔮 Price Predictions (Next-Day Forecast)")
st.markdown("XGBoost forecasts predicting the next day's price based on historical lag records, recent price actions, and local precipitation.")

# Grid of prediction cards
cols = st.columns(4)
col_idx = 0

for district in selected_districts:
    for commodity in selected_commodities:
        # Load the latest row from DB for this combo
        conn = get_connection()
        latest_query = """
            SELECT * FROM price_weather
            WHERE district = ? AND commodity = ?
            ORDER BY date DESC
            LIMIT 1
        """
        latest_row_df = conn.execute(latest_query, (district, commodity)).df()
        conn.close()
        
        if latest_row_df.empty:
            continue
            
        latest_row = latest_row_df.iloc[0].to_dict()
        
        # Model path
        model_path = f"models/saved/{commodity}_{district}.pkl"
        
        # Select grid column
        current_col = cols[col_idx % 4]
        col_idx += 1
        
        with current_col:
            st.info(f"📍 **{commodity}** — *{district}*")
            if os.path.exists(model_path):
                try:
                    predictor = PricePredictor()
                    predictor.load(model_path)
                    
                    # Predict using fallback-aware predict_next_week
                    pred_res = predictor.predict_next_week(latest_row)
                    pred_price = pred_res["predicted_price"]
                    latest_price = latest_row["modal_price"]
                    change = pred_price - latest_price
                    pct_change = (change / latest_price) * 100 if latest_price > 0 else 0
                    
                    delta_color = "normal" if abs(change) < 2 else "inverse" # optional visual refinement
                    
                    st.metric(
                        label="Predicted Next-Day Price",
                        value=f"₹{pred_price:.2f}",
                        delta=f"{change:+.2f} ({pct_change:+.2f}%)"
                    )
                    st.caption(f"Latest actual: ₹{latest_price:.2f} ({latest_row['date'].strftime('%Y-%m-%d')})")
                except Exception as e:
                    st.error(f"Error predicting: {e}")
            else:
                st.warning("Model not trained.")
                st.caption("Run training script for this combo to enable predictions.")
