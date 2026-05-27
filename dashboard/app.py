import os
import pandas as pd
import duckdb
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# Load DuckDB path from env
DUCKDB_PATH = os.getenv('DUCKDB_PATH', './data/crop_weather.duckdb')

# Auto-seed sample database if empty or missing on app startup
def check_and_seed_db():
    db_file = Path(DUCKDB_PATH)
    db_needs_seeding = not db_file.exists()
    
    if not db_needs_seeding:
        try:
            conn = duckdb.connect(database=str(db_file), read_only=True)
            tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
            if 'price_weather' not in tables:
                db_needs_seeding = True
            else:
                row_count = conn.execute("SELECT COUNT(*) FROM price_weather").fetchone()[0]
                if row_count == 0:
                    db_needs_seeding = True
            conn.close()
        except Exception:
            db_needs_seeding = True
            
    if db_needs_seeding:
        try:
            import sys
            # Append scripts to system path to import seeding utility
            scripts_dir = str(Path(__file__).parent.parent / "scripts")
            if scripts_dir not in sys.path:
                sys.path.append(scripts_dir)
            from seed_sample_data import seed_data
            seed_data(force=True)
        except Exception as e:
            st.error(f"Failed to auto-seed database: {e}")

check_and_seed_db()

@st.cache_resource
def get_duckdb_conn():
    return duckdb.connect(database=DUCKDB_PATH, read_only=False)

def load_data():
    try:
        con = get_duckdb_conn()
        df = con.execute('SELECT * FROM price_weather').fetchdf()
        con.close()
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            return df
    except Exception as e:
        pass
    
    # Mock data fallback
    df = pd.DataFrame([
        {
            "date": pd.to_datetime("2026-05-15"),
            "commodity": "Tomato",
            "district": "Nashik",
            "state": "Maharashtra",
            "market": "Nashik",
            "min_price": 100.0,
            "max_price": 200.0,
            "modal_price": 150.0,
            "precipitation_mm": 10.0,
            "temp_max_c": 35.0,
            "temp_min_c": 24.0,
            "windspeed_kmh": 12.0,
            "volatility_score": 0.67,
            "volatility_label": "HIGH",
            "price_change_pct": 0.0
        },
        {
            "date": pd.to_datetime("2026-05-16"),
            "commodity": "Tomato",
            "district": "Nashik",
            "state": "Maharashtra",
            "market": "Nashik",
            "min_price": 110.0,
            "max_price": 180.0,
            "modal_price": 140.0,
            "precipitation_mm": 5.0,
            "temp_max_c": 34.0,
            "temp_min_c": 23.0,
            "windspeed_kmh": 10.0,
            "volatility_score": 0.50,
            "volatility_label": "HIGH",
            "price_change_pct": -6.67
        },
        {
            "date": pd.to_datetime("2026-05-17"),
            "commodity": "Tomato",
            "district": "Nashik",
            "state": "Maharashtra",
            "market": "Nashik",
            "min_price": 120.0,
            "max_price": 220.0,
            "modal_price": 170.0,
            "precipitation_mm": 20.0,
            "temp_max_c": 30.0,
            "temp_min_c": 22.0,
            "windspeed_kmh": 14.0,
            "volatility_score": 0.588,
            "volatility_label": "HIGH",
            "price_change_pct": 21.43
        },
        {
            "date": pd.to_datetime("2026-05-15"),
            "commodity": "Onion",
            "district": "Indore",
            "state": "Madhya Pradesh",
            "market": "Indore",
            "min_price": 80.0,
            "max_price": 120.0,
            "modal_price": 100.0,
            "precipitation_mm": 0.0,
            "temp_max_c": 38.0,
            "temp_min_c": 26.0,
            "windspeed_kmh": 15.0,
            "volatility_score": 0.40,
            "volatility_label": "HIGH",
            "price_change_pct": 0.0
        },
        {
            "date": pd.to_datetime("2026-05-16"),
            "commodity": "Onion",
            "district": "Indore",
            "state": "Madhya Pradesh",
            "market": "Indore",
            "min_price": 85.0,
            "max_price": 110.0,
            "modal_price": 95.0,
            "precipitation_mm": 0.0,
            "temp_max_c": 39.0,
            "temp_min_c": 27.0,
            "windspeed_kmh": 12.0,
            "volatility_score": 0.263,
            "volatility_label": "MEDIUM",
            "price_change_pct": -5.0
        }
    ])
    return df

def load_alerts():
    try:
        con = get_duckdb_conn()
        alerts_df = con.execute('SELECT * FROM alerts').fetchdf()
        con.close()
        return alerts_df
    except Exception as e:
        pass
    
    # Mock alerts fallback
    return pd.DataFrame([
        {
            "alert_date": "2026-05-17",
            "commodity": "Tomato",
            "district": "Nashik",
            "volatility_score": 0.588,
            "modal_price": 170.0,
            "precipitation_mm": 20.0,
            "alert_reason": "High Volatility Alert"
        },
        {
            "alert_date": "2026-05-15",
            "commodity": "Onion",
            "district": "Indore",
            "volatility_score": 0.40,
            "modal_price": 100.0,
            "precipitation_mm": 0.0,
            "alert_reason": "High Volatility Alert"
        }
    ])

def main():
    st.set_page_config(
        page_title='Crop Price & Weather Correlation Engine',
        page_icon='🌾',
        layout='wide',
        initial_sidebar_state='expanded'
    )

    # Inject global CSS styles
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Outfit', sans-serif;
        background-color: #0b0f19;
        color: #e2e8f0;
    }
    
    /* Header decoration */
    .header-container {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.4) 0%, rgba(15, 23, 42, 0.6) 100%);
        padding: 2rem;
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        margin-bottom: 2rem;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(10px);
    }
    
    .gradient-text {
        background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 50%, #f472b6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        font-weight: 700;
        margin: 0;
    }
    
    /* Sleek Cards */
    .glass-card {
        background: rgba(30, 41, 59, 0.35);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 16px;
        padding: 1.5rem;
        backdrop-filter: blur(10px);
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .glass-card:hover {
        transform: translateY(-2px);
        border-color: rgba(255, 255, 255, 0.12);
    }
    
    /* Stat Metric details */
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #ffffff;
        margin: 0.5rem 0;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #94a3b8;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Buttons and controls */
    div.stButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%) !important;
        color: white !important;
        border: none !important;
        padding: 0.6rem 1.8rem !important;
        border-radius: 50px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4) !important;
        transition: all 0.2s ease !important;
        width: 100%;
    }
    
    div.stButton > button:hover {
        transform: scale(1.02) !important;
        box-shadow: 0 6px 20px rgba(139, 92, 246, 0.5) !important;
    }
    
    /* Red alert block */
    .danger-badge {
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.25);
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 600;
        display: inline-block;
        margin-top: 0.5rem;
    }
    
    .success-badge {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.25);
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 600;
        display: inline-block;
        margin-top: 0.5rem;
    }
    
    /* Crop-specific glowing glass cards */
    .glass-card-tomato {
        border-left: 4px solid #ef4444 !important;
        box-shadow: 0 8px 32px 0 rgba(239, 68, 68, 0.08) !important;
    }
    .glass-card-onion {
        border-left: 4px solid #a855f7 !important;
        box-shadow: 0 8px 32px 0 rgba(168, 85, 247, 0.08) !important;
    }
    .glass-card-potato {
        border-left: 4px solid #f59e0b !important;
        box-shadow: 0 8px 32px 0 rgba(245, 158, 11, 0.08) !important;
    }
    .glass-card-wheat {
        border-left: 4px solid #eab308 !important;
        box-shadow: 0 8px 32px 0 rgba(234, 179, 8, 0.08) !important;
    }
    .glass-card-generic {
        border-left: 4px solid #3b82f6 !important;
        box-shadow: 0 8px 32px 0 rgba(59, 130, 246, 0.08) !important;
    }
    .glass-card-footer {
        padding: 0.6rem 1rem;
        font-size: 0.8rem;
        color: #94a3b8;
    }
    </style>
    """, unsafe_allow_html=True)

    # Header section
    st.markdown("""
    <div class="header-container">
        <h1 class="gradient-text">🌾 Crop Weather Volatility Dashboard</h1>
        <p style="color: #94a3b8; font-size: 1.1rem; margin: 0.5rem 0 0 0;">
            Correlating Indian Mandi price variations with daily rain and heat indexes using ML and dbt core.
        </p>
    </div>
    """, unsafe_allow_html=True)

    df = load_data()

    # Sidebar styling
    st.sidebar.markdown("<h2 style='font-weight: 700; color: #ffffff;'>🔍 Control Center</h2>", unsafe_allow_html=True)
    st.sidebar.markdown("---")

    # Filters
    districts = sorted(df['district'].unique().tolist())
    commodities = sorted(df['commodity'].unique().tolist())
    
    selected_districts = st.sidebar.multiselect('📍 Selected District(s)', districts, default=districts[:3])
    selected_commodities = st.sidebar.multiselect('📦 Selected Commodity(ies)', commodities, default=commodities[:2])
    
    # Sensible defaults for date range (last 30 days of dataset)
    min_date = df['date'].min().date()
    max_date = df['date'].max().date()
    default_start = max(min_date, max_date - pd.Timedelta(days=30))
    
    date_range = st.sidebar.date_input(
        '📅 Analysis Date Range',
        value=(default_start, max_date),
        min_value=min_date,
        max_value=max_date,
        help='Select start and end dates'
    )
    
    # Filter dataset
    filtered_df = df.copy()
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date, end_date = date_range
        mask = (filtered_df['date'].dt.date >= start_date) & (filtered_df['date'].dt.date <= end_date)
        filtered_df = filtered_df.loc[mask]
        
    filtered_df = filtered_df[filtered_df['district'].isin(selected_districts) & filtered_df['commodity'].isin(selected_commodities)]

    if filtered_df.empty:
        st.warning("⚠️ No data matches the selected filters. Please expand your selection in the sidebar.")
        return

    # Dynamic Stat Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        avg_price = filtered_df['modal_price'].mean()
        st.markdown(f"""
        <div class="glass-card">
            <div class="metric-label">Avg Modal Price</div>
            <div class="metric-value">₹{avg_price:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        max_volatility = filtered_df['volatility_score'].max()
        st.markdown(f"""
        <div class="glass-card">
            <div class="metric-label">Max Volatility</div>
            <div class="metric-value">{max_volatility:.3f}</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        tot_rain = filtered_df['precipitation_mm'].sum()
        st.markdown(f"""
        <div class="glass-card">
            <div class="metric-label">Cumulative Rainfall</div>
            <div class="metric-value">{tot_rain:.1f} mm</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        avg_temp = filtered_df['temp_max_c'].mean()
        st.markdown(f"""
        <div class="glass-card">
            <div class="metric-label">Avg Max Temp</div>
            <div class="metric-value">{avg_temp:.1f}°C</div>
        </div>
        """, unsafe_allow_html=True)

    # Section 1 & 2: Chart Overlay
    st.markdown("<h3 style='margin-top: 1.5rem; font-weight: 600;'>📈 Price & Weather Overlay</h3>", unsafe_allow_html=True)
    
    # Double axis plot or two charts in premium tabs
    tab1, tab2 = st.tabs(["📊 Price & Weather Trends", "🗺️ Volatility Heatmap & Alerts"])
    
    with tab1:
        # Dual-axis Plotly trend chart
        fig = go.Figure()
        
        # Add modal price line per commodity
        for crop in selected_commodities:
            crop_df = filtered_df[filtered_df['commodity'] == crop].sort_values('date')
            if not crop_df.empty:
                fig.add_trace(go.Scatter(
                    x=crop_df['date'],
                    y=crop_df['modal_price'],
                    name=f"{crop} Price (₹)",
                    mode='lines+markers',
                    line=dict(width=3),
                    marker=dict(size=6),
                    yaxis='y1'
                ))
        
        # Add precipitation bar chart as a background overlay
        rain_df = filtered_df.groupby('date')['precipitation_mm'].mean().reset_index()
        fig.add_trace(go.Bar(
            x=rain_df['date'],
            y=rain_df['precipitation_mm'],
            name="Avg Rainfall (mm)",
            opacity=0.25,
            marker_color='#3b82f6',
            yaxis='y2'
        ))
        
        fig.update_layout(
            title=dict(
                text="Commodity Modal Price correlated with Rainfall",
                font=dict(size=16, color="#ffffff")
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="#94a3b8"),
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(255,255,255,0.05)',
                title="Date"
            ),
            yaxis1=dict(
                title="Modal Price (₹/Quintal)",
                showgrid=True,
                gridcolor='rgba(255,255,255,0.05)',
                titlefont=dict(color="#a78bfa"),
                tickfont=dict(color="#a78bfa")
            ),
            yaxis2=dict(
                title="Precipitation (mm)",
                overlaying='y',
                side='right',
                titlefont=dict(color="#3b82f6"),
                tickfont=dict(color="#3b82f6"),
                showgrid=False
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=40, r=40, t=80, b=40)
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        col_left, col_right = st.columns([1, 1])
        
        with col_left:
            st.markdown("<h4 style='font-weight: 600; text-align: center;'>🔥 Volatility Heatmap</h4>", unsafe_allow_html=True)
            heatmap_df = filtered_df.groupby(['district', 'commodity'])['volatility_score'].mean().reset_index()
            
            # Accessible sequential scale
            fig_heat = px.density_heatmap(
                heatmap_df,
                x='district',
                y='commodity',
                z='volatility_score',
                color_continuous_scale=['#10b981', '#f59e0b', '#ef4444'],
                labels={'volatility_score': 'Avg Volatility', 'commodity': 'Commodity', 'district': 'District'}
            )
            fig_heat.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color="#94a3b8"),
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_heat, use_container_width=True)
            
        with col_right:
            st.markdown("<h4 style='font-weight: 600;'>🚨 Real-time Volatility Alerts</h4>", unsafe_allow_html=True)
            alerts_df = load_alerts()
            
            # Clean "Pototo" typo in loaded/mocked alerts if present
            if not alerts_df.empty:
                if 'district' in alerts_df.columns:
                    alerts_df['district'] = alerts_df['district'].replace('Pototo', 'Potato')
                if 'commodity' in alerts_df.columns:
                    alerts_df['commodity'] = alerts_df['commodity'].replace('Pototo', 'Potato')
                
                alerts_df = alerts_df[
                    alerts_df['district'].isin(selected_districts) & 
                    alerts_df['commodity'].isin(selected_commodities)
                ]
                
            if alerts_df.empty:
                st.markdown("<div style='color: #34d399; font-weight: 600; padding: 1rem;'>🟢 No active volatility alerts in selected area.</div>", unsafe_allow_html=True)
            else:
                # Add calculated labels if not present
                if 'volatility_label' not in alerts_df.columns:
                    alerts_df['volatility_label'] = alerts_df['volatility_score'].apply(
                        lambda x: 'HIGH' if x > 0.3 else ('MEDIUM' if x > 0.1 else 'LOW')
                    )
                
                # Render beautiful custom glassmorphic list rows for visual excellence
                for idx, row in alerts_df.iterrows():
                    st.markdown(f"""
                    <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 0.8rem 1.2rem; margin-bottom: 0.6rem; display: flex; justify-content: space-between; align-items: center; backdrop-filter: blur(10px);">
                        <div>
                            <span style="background: { '#ef444426' if row['volatility_label'] == 'HIGH' else '#f59e0b26' }; color: { '#ef4444' if row['volatility_label'] == 'HIGH' else '#f59e0b' }; border: 1px solid { '#ef444440' if row['volatility_label'] == 'HIGH' else '#f59e0b40' }; padding: 0.25rem 0.5rem; border-radius: 6px; font-weight: 600; font-size: 0.75rem; margin-right: 0.8rem;">{row['volatility_label']} RISK</span>
                            <span style="font-weight: 600; color: #ffffff; font-size: 0.95rem;">{row['commodity']} &mdash; {row['district']}</span>
                        </div>
                        <div style="text-align: right; font-size: 0.85rem; color: #94a3b8;">
                            💧 {row['precipitation_mm']:.1f} mm Rain | 📈 Volatility: <b>{row['volatility_score']:.3f}</b>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    # ML Prediction Dashboard Section
    st.markdown("<h3 style='margin-top: 2rem; font-weight: 600;'>🔮 Predictive AI Price Forecasting</h3>", unsafe_allow_html=True)
    
    # Crop metadata configuration
    CROP_META = {
        "Tomato": {"emoji": "🍅", "color": "#ef4444", "class": "glass-card-tomato"},
        "Onion": {"emoji": "🧅", "color": "#a855f7", "class": "glass-card-onion"},
        "Potato": {"emoji": "🥔", "color": "#f59e0b", "class": "glass-card-potato"},
        "Wheat": {"emoji": "🌾", "color": "#eab308", "class": "glass-card-wheat"},
        "Rice": {"emoji": "🍚", "color": "#3b82f6", "class": "glass-card-generic"},
        "Maize": {"emoji": "🌽", "color": "#10b981", "class": "glass-card-generic"},
        "Soybean": {"emoji": "🫘", "color": "#6366f1", "class": "glass-card-generic"}
    }
    
    # District selector
    pred_district = st.selectbox("📍 Select Target District for Forecasting Models", districts)
    
    # Dynamic card grid rendering
    cols_per_row = 3
    for row_idx in range(0, len(selected_commodities), cols_per_row):
        row_commodities = selected_commodities[row_idx:row_idx + cols_per_row]
        cols = st.columns(len(row_commodities))
        
        for col, crop in zip(cols, row_commodities):
            with col:
                crop_meta = CROP_META.get(crop, {"emoji": "📦", "color": "#3b82f6", "class": "glass-card-generic"})
                crop_emoji = crop_meta["emoji"]
                crop_color = crop_meta["color"]
                
                # Check for trained model
                model_filename = f"models/saved/{crop.lower().replace(' ', '_')}_{pred_district.lower().replace(' ', '_')}.pkl"
                model_exists = Path(model_filename).exists()
                
                if not model_exists:
                    st.markdown(f"""
                    <div class="glass-card {crop_meta.get('class', 'glass-card-generic')}" style="border: 1px dashed {crop_color}40; margin-bottom: 0.5rem; padding-bottom: 1rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h4 style="margin: 0; color: #ffffff; font-size: 1.1rem;">{crop_emoji} {crop}</h4>
                            <span style="background: rgba(239, 68, 68, 0.1); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.2); padding: 0.15rem 0.4rem; border-radius: 4px; font-weight: 600; font-size: 0.7rem;">Untrained</span>
                        </div>
                        <p style="color: #94a3b8; font-size: 0.85rem; margin-top: 0.8rem; min-height: 48px;">
                            No XGBoost model exists for <b>{crop}</b> in <b>{pred_district}</b>.
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"⚡ Train {crop} Model", key=f"train_{crop}_{pred_district}"):
                        from models.price_predictor import PricePredictor
                        with st.spinner(f"Training model for {crop}..."):
                            try:
                                # Query data from DuckDB for training
                                con = get_duckdb_conn()
                                df_train = con.execute("""
                                    SELECT * FROM price_weather 
                                    WHERE commodity = ? AND district = ?
                                    ORDER BY date ASC
                                """, [crop, pred_district]).fetchdf()
                                con.close()
                                
                                if len(df_train) < 3:
                                    # Fallback: train on all districts for this commodity
                                    con = get_duckdb_conn()
                                    df_train = con.execute("""
                                        SELECT * FROM price_weather 
                                        WHERE commodity = ?
                                        ORDER BY date ASC
                                    """, [crop]).fetchdf()
                                    con.close()
                                
                                if df_train.empty:
                                    df_train = load_data()
                                    df_train = df_train[df_train['commodity'] == crop]
                                    
                                # Initialize & Train
                                predictor = PricePredictor()
                                predictor.train(df_train, crop, pred_district)
                                
                                # Save
                                os.makedirs("models/saved", exist_ok=True)
                                predictor.save(model_filename)
                                
                                st.toast(f"🎉 Model trained successfully for {crop}!")
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Error: {ex}")
                else:
                    # Model exists! Load and predict
                    from models.price_predictor import PricePredictor
                    try:
                        predictor = PricePredictor()
                        predictor.load(model_filename)
                        
                        # Fetch latest row for this combo
                        con = get_duckdb_conn()
                        latest_row_df = con.execute("""
                            SELECT * FROM price_weather 
                            WHERE commodity = ? AND district = ?
                            ORDER BY date DESC
                            LIMIT 1
                        """, [crop, pred_district]).fetchdf()
                        con.close()
                        
                        if latest_row_df.empty:
                            temp_df = df[(df['commodity'] == crop) & (df['district'] == pred_district)]
                            if not temp_df.empty:
                                latest_row = temp_df.sort_values('date').iloc[-1].to_dict()
                            else:
                                latest_row = df.iloc[-1].to_dict()
                        else:
                            latest_row = latest_row_df.iloc[0].to_dict()
                        
                        # Predict
                        result = predictor.predict_next_week(latest_row)
                        pred_price = result["predicted_modal_price"]
                        latest_price = latest_row.get("modal_price", 100.0)
                        price_change = ((pred_price - latest_price) / latest_price) * 100
                        
                        # Sparkline line chart setup
                        crop_history = filtered_df[
                            (filtered_df['commodity'] == crop) & 
                            (filtered_df['district'] == pred_district)
                        ].sort_values('date')
                        
                        st.markdown(f"""
                        <div class="glass-card {crop_meta.get('class', 'glass-card-generic')}" style="margin-bottom: 0.2rem; padding-bottom: 0.5rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <h4 style="margin: 0; color: #ffffff; font-size: 1.1rem;">{crop_emoji} {crop}</h4>
                                {"<span style='background: rgba(239, 68, 68, 0.1); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.2); padding: 0.15rem 0.4rem; border-radius: 4px; font-weight: 600; font-size: 0.7rem;'>High Volatility</span>" if abs(price_change) > 15 else "<span style='background: rgba(16, 185, 129, 0.1); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.2); padding: 0.15rem 0.4rem; border-radius: 4px; font-weight: 600; font-size: 0.7rem;'>Stable</span>"}
                            </div>
                            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 1rem;">
                                <div>
                                    <span class="metric-label" style="font-size:0.75rem;">Forecast (1W)</span>
                                    <div style="font-size: 1.6rem; font-weight: 700; color: #60a5fa; margin-top: 0.2rem;">₹{pred_price:,.2f}</div>
                                </div>
                                <div style="text-align: right;">
                                    <span class="metric-label" style="font-size:0.75rem;">Expected Swing</span>
                                    <div style="font-size: 1.25rem; font-weight: 600; color: {'#f87171' if price_change < 0 else '#34d399'}; margin-top: 0.2rem;">{price_change:+.2f}%</div>
                                </div>
                            </div>
                            <div style="margin-top: 0.8rem; margin-bottom: 0.2rem;">
                                <span class="metric-label" style="font-size:0.7rem;">Recent Price Sparkline</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if len(crop_history) > 1:
                            fig_spark = go.Figure()
                            fig_spark.add_trace(go.Scatter(
                                x=crop_history['date'],
                                y=crop_history['modal_price'],
                                mode='lines',
                                line=dict(color=crop_color, width=2.5),
                                hoverinfo='skip'
                            ))
                            fig_spark.update_layout(
                                xaxis=dict(visible=False),
                                yaxis=dict(visible=False),
                                showlegend=False,
                                margin=dict(l=0, r=0, t=0, b=0),
                                height=45,
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)'
                            )
                            st.plotly_chart(fig_spark, use_container_width=True, config={'displayModeBar': False})
                        else:
                            st.markdown("<div style='height:45px; display:flex; align-items:center; color:#64748b; font-size:0.75rem;'>No trend history available.</div>", unsafe_allow_html=True)
                            
                        st.markdown(f"""
                        <div class="glass-card-footer" style="background: rgba(30, 41, 59, 0.2); border-top: 1px solid rgba(255,255,255,0.03); padding: 0.5rem 1rem; margin-top: -0.2rem; font-size: 0.75rem; color: #94a3b8; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; display: flex; justify-content: space-between;">
                            <span>Current: ₹{latest_price:,.2f}</span>
                            <span>XGBoost v2.0</span>
                        </div>
                        <div style="margin-bottom: 1.5rem;"></div>
                        """, unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Error: {e}")

if __name__ == '__main__':
    main()
