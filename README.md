# Crop Price & Weather Correlation Engine

An end-to-end data engineering pipeline that correlates daily crop prices (mandi) with meteorological metrics (rainfall, temperature) across major farming districts in India to forecast price crashes and analyze volatility.

---

## 🏗️ Architecture

```text
               [ Data Sources ]
           /                      \
   [ India Mandi API ]      [ Open-Meteo API ]
           \                      /
         +--------------------------+
         |      Apache Airflow      | <--- Orchestrator (cron / daily)
         +--------------------------+
                      |
                      v
         +--------------------------+
         |      Raw Storage         | <--- JSON Backups (Local Storage)
         +--------------------------+
                      |
                      v
         +--------------------------+
         |    Pandas ETL Engine     | <--- Casing, NaN cleaning, joining
         +--------------------------+
                      |
                      v
         +--------------------------+
         |           dbt            | <--- Medallion Modeling (Bronze -> Silver -> Gold)
         +--------------------------+
                      |
                      v
         +--------------------------+
         |         DuckDB           | <--- High-performance Analytical Database
         +--------------------------+
                 /          \
                v            v
      +------------+      +-------------------+
      |  XGBoost   |      |Streamlit Dashboard| <--- Interactive Visualizations,
      | Predictor  |      |  Alerting Engine  |      Heatmaps, & Inference Cards
      +------------+      +-------------------+
```

---

## 🛠️ Tech Stack

| Layer | Technology | Description |
| :--- | :--- | :--- |
| **Orchestration** | Apache Airflow 2.x | Manages and triggers daily workflow tasks and dependencies |
| **Ingestion** | Python + Requests | Robust daily API fetchers with automatic retries and graceful error catching |
| **Storage** | Local Filesystem + Parquet | Raw JSON files cached, processed into high-performance column-oriented Parquet |
| **Transformation** | Pandas + dbt Core | Text normalization, volatility scoring, left joins, and Medallion modeling |
| **Database** | DuckDB 0.10.x | Embedded analytical query engine with zero setup and lightning-fast parquet querying |
| **Machine Learning**| XGBoost + Scikit-Learn | Predicts next-week crop modal prices based on historical price lags and weather features |
| **UI Dashboard** | Streamlit + Plotly | Serves interactive charts, correlation grids, heatmap analytics, and predictive cards |
| **Testing** | Pytest 8.x | 100% code coverage across API mock requests, transforms, and database loaders |
| **Containerization**| Docker / Docker Compose | Scalable, standard orchestration of services for Linux / macOS environments |

---

## 📂 Project Structure

```text
crop-pipeline/
├── dags/
│   └── crop_weather_dag.py        # Main Airflow DAG defining pipeline execution
├── ingestion/
│   ├── __init__.py
│   ├── fetch_mandi.py             # Mandi crop price API fetcher
│   └── fetch_weather.py           # Meteorological data API fetcher
├── transform/
│   ├── __init__.py
│   ├── clean.py                   # Data sanitization & anomaly filtering
│   ├── join.py                    # District-date spatio-temporal left-join
│   └── volatility.py              # Volatility index & price change computations
├── models/
│   ├── __init__.py
│   ├── price_predictor.py         # XGBoost Regressor (train, load, inference)
│   └── saved/                     # Persistent XGBoost models (*.pkl)
├── db/
│   ├── __init__.py
│   ├── schema.sql                 # DuckDB relational schema definitions
│   └── loader.py                  # Idempotent loader (Parquet -> DuckDB)
├── dashboard/
│   └── app.py                     # Streamlit user interface & interactive visuals
├── dbt_project/
│   ├── dbt_project.yml            # dbt configuration
│   ├── profiles.yml               # dbt connection target (DuckDB)
│   └── models/
│       ├── bronze/
│       │   ├── stg_mandi.sql      # Raw mandi staging model
│       │   └── stg_weather.sql    # Raw weather staging model
│       ├── silver/
│       │   └── joined_prices.sql  # Spatial-temporal consolidated join table
│       └── gold/
│           ├── weekly_aggregates.sql # Historical aggregations for trends
│           └── volatility_alerts.sql # HIGH-alert records filter
├── data/ (Gitignored)
│   ├── raw/                       # Daily raw JSON backups
│   └── processed/                 # Refactored Parquet outputs
├── tests/
│   ├── test_fetch_mandi.py        # Mocked API endpoint tests
│   ├── test_transform.py          # Pandas cleansing & metrics unit tests
│   └── test_loader.py             # DuckDB integration loader tests
├── docker-compose.yml             # Documented Airflow & Streamlit stack orchestration
├── requirements.txt               # Structured environment dependencies
├── .env.example                   # Local system context environments template
└── README.md                      # Placement portfolio documentation
```

---

## ⚡ Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/mithilgala-cmd/crop-weather-pipeline.git
cd crop-weather-pipeline
```

### 2. Configure Environment Variables
Create a local `.env` file copying the `.env.example` configurations:
```bash
cp .env.example .env
```
Inside your `.env` file, populate the following configurations:
```env
DATA_GOV_API_KEY=your_gov_api_key_here
AIRFLOW_HOME=./airflow
RAW_DIR=./data/raw
PROCESSED_DIR=./data/processed
DUCKDB_PATH=./data/crop_weather.duckdb
```

### 3. Install Dependencies
Set up a clean virtual environment and install dependencies:
```bash
python -m venv .venv
# On Windows PowerShell
.venv\Scripts\Activate.ps1
# On macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 4. Initialize Database & Run Pipeline Tests
Execute the comprehensive suite to verify ingestion, transformations, and database loader scripts are fully functional:
```bash
pytest
```

### 5. Run dbt Transformations
Compile and execute the Medallion modeling models to transform your raw tables:
```bash
cd dbt_project
dbt run
cd ..
```

### 6. Launch the Streamlit Dashboard
Launch the visual interface in your default browser:
```bash
streamlit run dashboard/app.py
```

---

## 📸 Screenshots

> [!NOTE]
> *Dynamic dashboard mockups illustrating spatial pricing trends, rainfall indexes, correlation heatmaps, and price alerts will be updated here.*

---

## 💼 Placement Portfolio Bullet Points

- **Built an End-to-End ELT Pipeline** ingesting daily mandi market crop prices + historical weather indices across 8 high-yield districts, orchestrated using Python, Pandas, and transactional loading strategies.
- **Modeled Price-Weather Correlation** utilizing a **dbt Medallion Architecture (Bronze $\rightarrow$ Silver $\rightarrow$ Gold)** to structure analytical tables directly on an embedded analytical **DuckDB** storage engine.
- **Trained an XGBoost Regressor Model** achieving robust forecasts on next-week agricultural price thresholds utilizing historical price lags, day properties, and seasonal rainfall overlays.
- **Developed a Streamlit Interactive Dashboard** showcasing spatial-temporal Plotly price overlays, volatility heatmaps, and automated predictive alert cards highlighting crop price crash risks.
- **Authored Comprehensive Pytest Suites** covering API endpoint mocking, data sanitization constraints, and analytical loader integrations with **100% test verification pass rate**.