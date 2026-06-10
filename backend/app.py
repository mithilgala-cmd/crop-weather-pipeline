import os
import sys
import duckdb
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional

# Setup absolute paths and resolve sys.path to avoid ImportErrors
root_dir = Path(__file__).parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# Add dashboard folder to import analyst.py
dashboard_dir = root_dir / "dashboard"
if str(dashboard_dir) not in sys.path:
    sys.path.append(str(dashboard_dir))

load_dotenv(dotenv_path=root_dir / ".env")

# Detect Vercel serverless runs
IS_VERCEL = os.environ.get("VERCEL") == "1"

if IS_VERCEL:
    DUCKDB_PATH = "/tmp/crop_weather.duckdb"
    os.environ['DUCKDB_PATH'] = DUCKDB_PATH
    MODELS_DIR = Path("/tmp/models/saved")
    
    # Copy pre-seeded database to writable /tmp
    src_db = root_dir / "data" / "crop_weather.duckdb"
    dest_db = Path(DUCKDB_PATH)
    if src_db.exists() and not dest_db.exists():
        try:
            import shutil
            dest_db.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(str(src_db), str(dest_db))
            print("Pre-seeded database copied to /tmp successfully.")
        except Exception as e:
            print(f"Failed to copy database to /tmp: {e}")
else:
    DUCKDB_PATH = os.getenv('DUCKDB_PATH', str(root_dir / 'data' / 'crop_weather.duckdb'))
    os.environ['DUCKDB_PATH'] = DUCKDB_PATH
    MODELS_DIR = root_dir / "models" / "saved"


# Auto-seed sample database if empty or missing
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
            from backend.seed_sample_data import seed_data
            seed_data(force=True)
            print("Database successfully seeded.")
        except Exception as e:
            # Fallback to local script import if backend folder is not packages
            try:
                scripts_dir = root_dir / "scripts"
                if str(scripts_dir) not in sys.path:
                    sys.path.append(str(scripts_dir))
                from seed_sample_data import seed_data
                seed_data(force=True)
                print("Database successfully seeded via local scripts.")
            except Exception as e2:
                print(f"Failed to auto-seed database: {e2}")

check_and_seed_db()

app = FastAPI(
    title="Crop Weather Volatility Engine API",
    description="Backend API serving crop pricing and weather correlation observations, predicting next-week swings using XGBoost, and analyzing anomalies with Google Gemini.",
    version="1.0.0"
)

# Enable CORS for local testing/cross-origin frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper function to get DuckDB connection
def get_duckdb_conn():
    return duckdb.connect(database=DUCKDB_PATH, read_only=False)

# Helper to run a filtered query and return a DataFrame
def get_filtered_df(
    districts: Optional[List[str]] = None,
    commodities: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    query = "SELECT * FROM price_weather WHERE 1=1"
    params = []
    
    if districts:
        placeholders = ", ".join(["?"] * len(districts))
        query += f" AND district IN ({placeholders})"
        params.extend(districts)
        
    if commodities:
        placeholders = ", ".join(["?"] * len(commodities))
        query += f" AND commodity IN ({placeholders})"
        params.extend(commodities)
        
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
        
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
        
    query += " ORDER BY date ASC"
    
    con = get_duckdb_conn()
    try:
        df = con.execute(query, params).fetchdf()
    finally:
        con.close()
        
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        
    return df

# Model definition for training/predictive tasks
class ModelTaskRequest(BaseModel):
    commodity: str
    district: str

# Model definition for Gemini Market Analyst Q&A
class AnalystRequest(BaseModel):
    commodity: str
    district: str
    question: str
    districts: Optional[List[str]] = None
    commodities: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

# --- API Endpoints ---

@app.get("/api/metadata")
def get_metadata():
    """Returns available distinct districts, commodities, and date boundaries in the database."""
    con = get_duckdb_conn()
    try:
        districts = [r[0] for r in con.execute("SELECT DISTINCT district FROM price_weather ORDER BY district").fetchall()]
        commodities = [r[0] for r in con.execute("SELECT DISTINCT commodity FROM price_weather ORDER BY commodity").fetchall()]
        min_max_dates = con.execute("SELECT MIN(date), MAX(date) FROM price_weather").fetchone()
        
        min_date = str(min_max_dates[0]) if min_max_dates[0] else None
        max_date = str(min_max_dates[1]) if min_max_dates[1] else None
        
        return {
            "districts": districts,
            "commodities": commodities,
            "min_date": min_date,
            "max_date": max_date
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database metadata query failed: {str(e)}")
    finally:
        con.close()

@app.get("/api/data")
def get_data(
    district: Optional[List[str]] = Query(None),
    commodity: Optional[List[str]] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """Retrieves records from price_weather based on optional filters."""
    try:
        df = get_filtered_df(
            districts=district,
            commodities=commodity,
            start_date=start_date,
            end_date=end_date
        )
        
        if df.empty:
            return []
            
        # Format dates to YYYY-MM-DD for JSON response
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        # Replace NaNs for JSON compatibility
        df = df.fillna(0.0)
        
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve filtered records: {str(e)}")

@app.get("/api/alerts")
def get_alerts(
    district: Optional[List[str]] = Query(None),
    commodity: Optional[List[str]] = Query(None)
):
    """Retrieves high-volatility risk alerts, with automatic label generation."""
    con = get_duckdb_conn()
    try:
        query = "SELECT * FROM alerts WHERE 1=1"
        params = []
        
        if district:
            placeholders = ", ".join(["?"] * len(district))
            query += f" AND district IN ({placeholders})"
            params.extend(district)
            
        if commodity:
            placeholders = ", ".join(["?"] * len(commodity))
            query += f" AND commodity IN ({placeholders})"
            params.extend(commodity)
            
        query += " ORDER BY alert_date DESC"
        
        df = con.execute(query, params).fetchdf()
        
        if df.empty:
            return []
            
        # Clean 'Pototo' typo
        if 'district' in df.columns:
            df['district'] = df['district'].replace('Pototo', 'Potato')
        if 'commodity' in df.columns:
            df['commodity'] = df['commodity'].replace('Pototo', 'Potato')
            
        # Ensure volatility labels are defined
        if 'volatility_label' not in df.columns:
            df['volatility_label'] = df['volatility_score'].apply(
                lambda x: 'HIGH' if x > 0.3 else ('MEDIUM' if x > 0.1 else 'LOW')
            )
            
        df['alert_date'] = pd.to_datetime(df['alert_date']).dt.strftime('%Y-%m-%d')
        df = df.fillna(0.0)
        
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query alerts: {str(e)}")
    finally:
        con.close()

@app.post("/api/predict")
def predict_price(req: ModelTaskRequest):
    """Executes next-week price forecasting using the XGBoost model for the crop & district."""
    from models.price_predictor import PricePredictor
    
    crop = req.commodity
    district = req.district
    
    model_filename = f"{crop.lower().replace(' ', '_')}_{district.lower().replace(' ', '_')}.pkl"
    model_path = MODELS_DIR / model_filename
    
    if not model_path.exists():
        return {
            "model_exists": False,
            "message": f"No XGBoost model trained yet for {crop} in {district}."
        }
        
    try:
        predictor = PricePredictor()
        try:
            predictor.load(str(model_path))
        except (ModuleNotFoundError, Exception):
            # Auto-train fallback model on-the-fly if loading failed (e.g. missing xgboost on Vercel)
            con = get_duckdb_conn()
            df_train = con.execute("""
                SELECT * FROM price_weather 
                WHERE commodity = ? AND district = ?
                ORDER BY date ASC
            """, [crop, district]).fetchdf()
            con.close()
            
            if len(df_train) < 3:
                con = get_duckdb_conn()
                df_train = con.execute("""
                    SELECT * FROM price_weather 
                    WHERE commodity = ?
                    ORDER BY date ASC
                """, [crop]).fetchdf()
                con.close()
                
            predictor.train(df_train, crop, district)
            os.makedirs(str(model_path.parent), exist_ok=True)
            predictor.save(str(model_path))
        
        # Fetch the latest record for this combo to serve as predictor input
        con = get_duckdb_conn()
        latest_row_df = con.execute("""
            SELECT * FROM price_weather 
            WHERE commodity = ? AND district = ?
            ORDER BY date DESC
            LIMIT 1
        """, [crop, district]).fetchdf()
        con.close()
        
        if latest_row_df.empty:
            # Fallback to the latest record of this commodity across any district
            con = get_duckdb_conn()
            latest_row_df = con.execute("""
                SELECT * FROM price_weather 
                WHERE commodity = ?
                ORDER BY date DESC
                LIMIT 1
            """, [crop]).fetchdf()
            con.close()
            
        if latest_row_df.empty:
            raise HTTPException(
                status_code=404, 
                detail=f"No record found in database for commodity {crop} to run prediction."
            )
            
        latest_row = latest_row_df.iloc[0].to_dict()
        latest_price = latest_row.get("modal_price", 100.0)
        
        result = predictor.predict_next_week(latest_row)
        pred_price = result["predicted_modal_price"]
        
        price_change = ((pred_price - latest_price) / latest_price) * 100
        volatility_label = "HIGH" if abs(price_change) > 15 else "STABLE"
        
        return {
            "model_exists": True,
            "predicted_modal_price": round(pred_price, 2),
            "latest_price": round(latest_price, 2),
            "price_change_pct": round(price_change, 2),
            "volatility_label": volatility_label
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.post("/api/train")
def train_model(req: ModelTaskRequest):
    """Triggers dynamic training of the XGBoost PricePredictor model for a crop & district."""
    from models.price_predictor import PricePredictor
    
    crop = req.commodity
    district = req.district
    
    try:
        con = get_duckdb_conn()
        df_train = con.execute("""
            SELECT * FROM price_weather 
            WHERE commodity = ? AND district = ?
            ORDER BY date ASC
        """, [crop, district]).fetchdf()
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
            # Load all records
            con = get_duckdb_conn()
            df_train = con.execute("SELECT * FROM price_weather ORDER BY date ASC").fetchdf()
            con.close()
            
        predictor = PricePredictor()
        predictor.train(df_train, crop, district)
        
        model_filename = f"{crop.lower().replace(' ', '_')}_{district.lower().replace(' ', '_')}.pkl"
        model_path = MODELS_DIR / model_filename
        
        os.makedirs(str(model_path.parent), exist_ok=True)
        predictor.save(str(model_path))
        
        return {
            "success": True,
            "message": f"Successfully trained and saved model for {crop} in {district}."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model training failed: {str(e)}")

@app.post("/api/analyst")
def call_analyst(req: AnalystRequest):
    """Executes Gemini agricultural Q&A over the currently filtered context."""
    try:
        from backend.analyst import ask_analyst
    except ImportError:
        from analyst import ask_analyst
    
    try:
        # Load filtered dataframe matching user filters
        df = get_filtered_df(
            districts=req.districts,
            commodities=req.commodities,
            start_date=req.start_date,
            end_date=req.end_date
        )
        
        if df.empty:
            raise HTTPException(status_code=400, detail="Cannot query Gemini with an empty dataset. Adjust your date boundaries or filters.")
            
        answer = ask_analyst(
            df=df,
            commodity=req.commodity,
            district=req.district,
            question=req.question
        )
        
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini analyst failed to answer: {str(e)}")

# Mount static files at the root route last to avoid shadowing API endpoints only if not on Vercel
if not IS_VERCEL:
    frontend_dir = root_dir / "frontend"
    if not frontend_dir.exists():
        os.makedirs(str(frontend_dir), exist_ok=True)
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="static")
