# Crop Price & Weather Correlation Engine
### AI Agent Build Instructions

---

## Project Overview

Build an end-to-end data engineering pipeline that:
1. Ingests daily mandi (agricultural market) prices from India's open government API
2. Ingests weather data (rainfall, temperature) for major farming districts
3. Joins, cleans, and transforms both datasets
4. Stores results in DuckDB
5. Computes price volatility scores
6. Serves insights via a Streamlit dashboard

**Goal:** Help farmers and analysts anticipate crop price crashes by correlating weather patterns with market price volatility.

---

## Tech Stack

| Layer          | Tool                        |
|----------------|-----------------------------|
| Orchestration  | Apache Airflow 2.x          |
| Ingestion      | Python + requests           |
| Storage (raw)  | Local filesystem (JSON/CSV) |
| Transform      | pandas + dbt Core           |
| Query engine   | DuckDB                      |
| ML             | scikit-learn (LinearRegression, XGBoost) |
| Dashboard      | Streamlit                   |
| Containerize   | Docker + Docker Compose     |
| Language       | Python 3.10+                |

---

## Project Structure

Build the following folder structure exactly:

```
crop-pipeline/
├── dags/
│   └── crop_weather_dag.py        # Main Airflow DAG (already provided)
├── ingestion/
│   ├── __init__.py
│   ├── fetch_mandi.py             # Mandi price fetcher
│   └── fetch_weather.py          # Weather fetcher
├── transform/
│   ├── __init__.py
│   ├── clean.py                   # Cleaning functions
│   ├── join.py                    # Join mandi + weather
│   └── volatility.py             # Volatility score computation
├── models/
│   ├── __init__.py
│   └── price_predictor.py        # ML model: predict next week price
├── db/
│   ├── __init__.py
│   ├── schema.sql                 # DuckDB table definitions
│   └── loader.py                  # Load parquet → DuckDB
├── dashboard/
│   └── app.py                     # Streamlit dashboard
├── dbt_project/
│   ├── dbt_project.yml
│   └── models/
│       ├── bronze/
│       │   ├── stg_mandi.sql
│       │   └── stg_weather.sql
│       ├── silver/
│       │   └── joined_prices.sql
│       └── gold/
│           ├── weekly_aggregates.sql
│           └── volatility_alerts.sql
├── data/
│   ├── raw/                       # Raw JSON dumps (gitignored)
│   └── processed/                 # Parquet files (gitignored)
├── tests/
│   ├── test_fetch_mandi.py
│   ├── test_transform.py
│   └── test_loader.py
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## Step-by-Step Build Instructions

### STEP 1 — Project Setup

**Task:** Initialize the project.

- Create the full folder structure above
- Create `requirements.txt` with:
  ```
  apache-airflow==2.8.1
  duckdb==0.10.0
  pandas==2.2.0
  pyarrow==15.0.0
  requests==2.31.0
  scikit-learn==1.4.0
  xgboost==2.0.3
  streamlit==1.32.0
  plotly==5.19.0
  dbt-duckdb==1.7.0
  python-dotenv==1.0.0
  pytest==8.0.0
  ```
- Create `.env.example`:
  ```
  DATA_GOV_API_KEY=your_key_here
  AIRFLOW_HOME=./airflow
  RAW_DIR=./data/raw
  PROCESSED_DIR=./data/processed
  DUCKDB_PATH=./data/crop_weather.duckdb
  ```
- Create `.gitignore` that ignores `data/raw/`, `data/processed/`, `.env`, `*.duckdb`, `__pycache__/`

---

### STEP 2 — Ingestion Layer

#### `ingestion/fetch_mandi.py`

**Task:** Build a function `fetch_mandi_prices(date: str) -> list[dict]`

- Hit `https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070`
- Params: `api-key`, `format=json`, `limit=500`, `filters[commodity]` for each commodity
- Commodities list: `["Tomato", "Onion", "Potato", "Wheat", "Rice", "Maize", "Soybean"]`
- Handle HTTP errors with try/except, log failures, continue on error
- Return list of dicts with keys: `date, commodity, district, state, market, min_price, max_price, modal_price`
- Save output to `{RAW_DIR}/mandi_{date}.json`

#### `ingestion/fetch_weather.py`

**Task:** Build a function `fetch_weather(date: str) -> list[dict]`

- Hit `https://api.open-meteo.com/v1/forecast` — free, no API key
- Fetch for these districts (hardcode as a list of dicts with name/lat/lon/state):
  ```python
  DISTRICTS = [
      {"name": "Nashik",    "lat": 20.0059, "lon": 73.7898, "state": "Maharashtra"},
      {"name": "Agra",      "lat": 27.1767, "lon": 78.0081, "state": "Uttar Pradesh"},
      {"name": "Ludhiana",  "lat": 30.9010, "lon": 75.8573, "state": "Punjab"},
      {"name": "Guntur",    "lat": 16.3067, "lon": 80.4365, "state": "Andhra Pradesh"},
      {"name": "Indore",    "lat": 22.7196, "lon": 75.8577, "state": "Madhya Pradesh"},
      {"name": "Jaipur",    "lat": 26.9124, "lon": 75.7873, "state": "Rajasthan"},
      {"name": "Patna",     "lat": 25.5941, "lon": 85.1376, "state": "Bihar"},
      {"name": "Bhopal",    "lat": 23.2599, "lon": 77.4126, "state": "Madhya Pradesh"},
  ]
  ```
- Daily params: `precipitation_sum`, `temperature_2m_max`, `temperature_2m_min`, `windspeed_10m_max`
- Timezone: `Asia/Kolkata`
- Save output to `{RAW_DIR}/weather_{date}.json`

---

### STEP 3 — Transform Layer

#### `transform/clean.py`

**Task:** Build two functions:

1. `clean_mandi(df: pd.DataFrame) -> pd.DataFrame`
   - Cast `min_price`, `max_price`, `modal_price` to float
   - Strip + title-case `district`, `commodity`, `state`
   - Drop rows where `modal_price` is null or <= 0
   - Parse `date` column to `datetime`
   - Remove duplicates on `[date, commodity, market]`

2. `clean_weather(df: pd.DataFrame) -> pd.DataFrame`
   - Cast all numeric cols to float
   - Strip + title-case `district`
   - Fill missing `precipitation_mm` with 0

#### `transform/join.py`

**Task:** Build `join_mandi_weather(mandi_df, weather_df) -> pd.DataFrame`
- Left join mandi on weather using `district` + `date`
- Keep all mandi rows even if no weather match

#### `transform/volatility.py`

**Task:** Build `compute_volatility(df: pd.DataFrame) -> pd.DataFrame`
- Add column `volatility_score = (max_price - min_price) / modal_price`
- Add column `volatility_label`:
  - `"HIGH"` if score > 0.3
  - `"MEDIUM"` if 0.1 < score <= 0.3
  - `"LOW"` if score <= 0.1
- Add column `price_change_pct`: % change in modal_price vs previous day for same commodity+district (use `.shift(1)` after sorting by date)

---

### STEP 4 — Database Layer

#### `db/schema.sql`

Create these DuckDB tables:
```sql
CREATE TABLE IF NOT EXISTS price_weather (
    date DATE,
    commodity VARCHAR,
    district VARCHAR,
    state VARCHAR,
    market VARCHAR,
    min_price DOUBLE,
    max_price DOUBLE,
    modal_price DOUBLE,
    precipitation_mm DOUBLE,
    temp_max_c DOUBLE,
    temp_min_c DOUBLE,
    windspeed_kmh DOUBLE,
    volatility_score DOUBLE,
    volatility_label VARCHAR,
    price_change_pct DOUBLE
);

CREATE TABLE IF NOT EXISTS weekly_aggregates (
    week_start DATE,
    commodity VARCHAR,
    district VARCHAR,
    avg_modal_price DOUBLE,
    avg_precipitation DOUBLE,
    avg_volatility DOUBLE,
    max_volatility DOUBLE
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_date DATE,
    commodity VARCHAR,
    district VARCHAR,
    volatility_score DOUBLE,
    modal_price DOUBLE,
    precipitation_mm DOUBLE,
    alert_reason VARCHAR
);
```

#### `db/loader.py`

**Task:** Build `load_parquet_to_duckdb(parquet_path: str, date: str)`
- Connect to DuckDB at `DUCKDB_PATH`
- Run schema.sql on first run
- Delete existing rows for that date before inserting (idempotent)
- Insert from parquet using `read_parquet()`
- Also populate `alerts` table where `volatility_label = 'HIGH'`

---

### STEP 5 — dbt Models

#### `dbt_project/models/bronze/stg_mandi.sql`
```sql
SELECT
    CAST(date AS DATE)       AS date,
    TRIM(commodity)          AS commodity,
    TRIM(district)           AS district,
    TRIM(state)              AS state,
    CAST(modal_price AS DOUBLE) AS modal_price,
    CAST(min_price AS DOUBLE)   AS min_price,
    CAST(max_price AS DOUBLE)   AS max_price
FROM {{ source('raw', 'mandi_raw') }}
WHERE modal_price IS NOT NULL AND modal_price > 0
```

#### `dbt_project/models/silver/joined_prices.sql`
```sql
SELECT
    m.*,
    w.precipitation_mm,
    w.temp_max_c,
    w.temp_min_c,
    ROUND((m.max_price - m.min_price) / NULLIF(m.modal_price, 0), 4) AS volatility_score
FROM {{ ref('stg_mandi') }} m
LEFT JOIN {{ ref('stg_weather') }} w
    ON m.district = w.district AND m.date = w.date
```

#### `dbt_project/models/gold/weekly_aggregates.sql`
```sql
SELECT
    DATE_TRUNC('week', date)  AS week_start,
    commodity,
    district,
    ROUND(AVG(modal_price), 2)      AS avg_modal_price,
    ROUND(AVG(precipitation_mm), 2) AS avg_precipitation,
    ROUND(AVG(volatility_score), 4) AS avg_volatility,
    ROUND(MAX(volatility_score), 4) AS max_volatility
FROM {{ ref('joined_prices') }}
GROUP BY 1, 2, 3
```

---

### STEP 6 — ML Model

#### `models/price_predictor.py`

**Task:** Build `PricePredictor` class with:

```python
class PricePredictor:
    def train(self, df: pd.DataFrame, commodity: str, district: str): ...
    def predict_next_week(self, latest_row: dict) -> dict: ...
    def save(self, path: str): ...
    def load(self, path: str): ...
```

- Features: `precipitation_mm`, `temp_max_c`, `temp_min_c`, `volatility_score`, `day_of_week`, `month`, `lag_7_price` (modal_price 7 days ago), `lag_14_price`
- Target: `modal_price` (next day)
- Model: XGBoost Regressor
- Metrics to print: RMSE, MAE, R²
- Save model as pickle to `models/saved/{commodity}_{district}.pkl`

---

### STEP 7 — Streamlit Dashboard

#### `dashboard/app.py`

Build dashboard with these sections:

**Sidebar:**
- District multiselect (all districts from DB)
- Commodity multiselect
- Date range picker (default: last 30 days)

**Main page — 4 sections:**

1. **Price Trend Chart**
   - Plotly line chart: modal_price over time per commodity
   - Color-coded by commodity

2. **Weather Overlay**
   - Secondary y-axis: precipitation bars on same chart
   - Shows rainfall vs price correlation visually

3. **Volatility Heatmap**
   - Plotly heatmap: rows = districts, cols = commodities, value = avg volatility
   - Color: green (low) → red (high)

4. **Alerts Table**
   - Show rows from `alerts` table for selected date range
   - Highlight HIGH volatility rows in red

**Bottom:**
- "Predicted price next week" card per selected commodity+district
- Call `PricePredictor.predict_next_week()` with latest row

---

### STEP 8 — Docker Setup

#### `docker-compose.yml`

**Task:** Create Docker Compose with these services:

1. **airflow-webserver** — `apache/airflow:2.8.1`, port 8080
2. **airflow-scheduler** — same image, runs scheduler
3. **airflow-init** — runs `airflow db init` on first boot
4. **streamlit** — custom Dockerfile, port 8501

Mount `./dags` → `/opt/airflow/dags`, `./data` → `/opt/airflow/data`

Pass `.env` variables to all services.

---

### STEP 9 — Tests

#### `tests/test_fetch_mandi.py`
- Mock `requests.get` with sample response
- Assert returned list has correct keys
- Assert empty list returned on API failure (no exception raised)

#### `tests/test_transform.py`
- Test `clean_mandi` drops null modal_price rows
- Test `compute_volatility` labels HIGH/MEDIUM/LOW correctly
- Test `join_mandi_weather` keeps all mandi rows (left join)

#### `tests/test_loader.py`
- Create temp DuckDB, load sample parquet, assert row count matches

---

## Environment Variables

```
DATA_GOV_API_KEY    → get free from https://data.gov.in (register, then generate key)
AIRFLOW_HOME        → path to airflow home dir
RAW_DIR             → where raw JSON files go
PROCESSED_DIR       → where parquet files go
DUCKDB_PATH         → path to .duckdb file
```

---

## What NOT To Do

- Do NOT use SQLite — use DuckDB only
- Do NOT hardcode API keys — always read from env
- Do NOT use Spark — pandas is sufficient for this scale
- Do NOT use `SELECT *` in dbt models — always name columns explicitly
- Do NOT skip error handling in fetch functions — pipeline must not crash on single API failure

---

## Definition of Done

- [ ] `docker-compose up` starts Airflow + Streamlit with no errors
- [ ] DAG runs successfully for today's date end-to-end
- [ ] DuckDB has data in all 3 tables
- [ ] Streamlit dashboard loads and shows charts
- [ ] All 3 test files pass with `pytest`
- [ ] `dbt run` completes all models green

---

## Resume Bullets (fill after build)

- "Built end-to-end ELT pipeline ingesting mandi prices + weather across 8 districts, orchestrated via Airflow DAGs with daily scheduling"
- "Modeled price-weather correlation using dbt medallion architecture (Bronze→Silver→Gold) on DuckDB"
- "Trained XGBoost price predictor achieving RMSE of __ on 7-day forecasts for 7 commodities"
- "Deployed Streamlit dashboard with volatility heatmap and real-time alerts for high price-swing commodities"
