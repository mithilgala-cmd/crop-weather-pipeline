"""
LLM Market Analyst – dashboard/analyst.py
Uses Google Gemini API (GEMINI_API_KEY) to answer natural-language questions
over filtered crop-price + weather data pulled from the pipeline.
"""

from __future__ import annotations

import os
import json
import textwrap
from typing import Optional

import pandas as pd
import requests


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_context_summary(df: pd.DataFrame, commodity: str, district: str) -> str:
    """
    Summarises the filtered DataFrame into a compact JSON-like text block
    that fits safely inside a prompt without hitting token limits.
    """
    subset = df[
        (df["commodity"].str.strip().str.title() == commodity.strip().title()) &
        (df["district"].str.strip().str.title() == district.strip().title())
    ].copy()

    if subset.empty:
        # Fallback: use all data for this commodity across any district
        subset = df[
            df["commodity"].str.strip().str.title() == commodity.strip().title()
        ].copy()

    if subset.empty:
        return "No data available for the selected commodity and district."

    subset = subset.sort_values("date")

    # Compute summary statistics
    latest = subset.iloc[-1]
    stats = {
        "commodity": commodity,
        "district": district,
        "days_in_dataset": int(len(subset)),
        "date_range": f"{subset['date'].min().date()} → {subset['date'].max().date()}",
        "avg_modal_price_inr": round(float(subset["modal_price"].mean()), 2),
        "max_modal_price_inr": round(float(subset["modal_price"].max()), 2),
        "min_modal_price_inr": round(float(subset["modal_price"].min()), 2),
        "avg_volatility_score": round(float(subset["volatility_score"].mean()), 4),
        "max_volatility_score": round(float(subset["volatility_score"].max()), 4),
        "high_volatility_days": int((subset["volatility_score"] > 0.3).sum()),
        "avg_precipitation_mm": round(float(subset["precipitation_mm"].mean()), 2),
        "total_precipitation_mm": round(float(subset["precipitation_mm"].sum()), 2),
        "avg_temp_max_c": round(float(subset["temp_max_c"].mean()), 2),
        "avg_temp_min_c": round(float(subset["temp_min_c"].mean()), 2),
        "latest_modal_price_inr": round(float(latest.get("modal_price", 0)), 2),
        "latest_volatility_score": round(float(latest.get("volatility_score", 0)), 4),
        "latest_precipitation_mm": round(float(latest.get("precipitation_mm", 0)), 2),
        "latest_temp_max_c": round(float(latest.get("temp_max_c", 0)), 2),
    }

    # Add optional lag / change columns if present
    if "price_change_pct" in subset.columns:
        stats["latest_price_change_pct"] = round(
            float(latest.get("price_change_pct", 0) or 0), 2
        )

    # Last 5 days quick table
    recent = subset[["date", "modal_price", "volatility_score", "precipitation_mm"]].tail(5)
    recent_records = recent.rename(columns={
        "modal_price": "price_inr",
        "volatility_score": "volatility",
        "precipitation_mm": "rain_mm",
    }).to_dict(orient="records")

    for r in recent_records:
        if hasattr(r.get("date"), "date"):
            r["date"] = str(r["date"].date())

    stats["recent_5_days"] = recent_records

    return json.dumps(stats, indent=2)


def _call_gemini(prompt: str, api_key: str) -> str:
    """
    Calls Gemini API with fallbacks and retry logic to handle rate limits (429) and high demand (503).
    """
    import time
    
    # List of models to try in sequence as fallbacks
    models = ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-2.0-flash", "gemini-flash-latest"]
    max_retries = 3
    base_delay = 1.0 # second
    
    last_error = ""
    
    for model in models:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 2048,
            },
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, timeout=30)
                
                # Handle rate-limiting or service unavailability with delay + retry
                if response.status_code in (429, 503):
                    try:
                        err_msg = response.json().get("error", {}).get("message", response.text)
                    except Exception:
                        err_msg = response.text
                    last_error = f"HTTP {response.status_code}: {err_msg}"
                    
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                
                response.raise_for_status()
                data = response.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return "⚠️ The model returned no response. Please try again."
                parts = candidates[0].get("content", {}).get("parts", [])
                return " ".join(p.get("text", "") for p in parts).strip()
                
            except requests.exceptions.Timeout:
                last_error = "Request timed out."
                continue
            except requests.exceptions.HTTPError as e:
                # If the model is not found (HTTP 404), switch to the next fallback model immediately
                if e.response.status_code == 404:
                    last_error = f"Model {model} not found (HTTP 404)."
                    break
                
                try:
                    err_msg = e.response.json().get("error", {}).get("message", e.response.text)
                except Exception:
                    err_msg = e.response.text
                last_error = f"HTTP {e.response.status_code}: {err_msg}"
                break
            except Exception as e:
                last_error = str(e)
                break
                
    return f"⚠️ API error after trying fallback models: {last_error[:300]}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ask_analyst(
    df: pd.DataFrame,
    commodity: str,
    district: str,
    question: str,
    api_key: Optional[str] = None,
) -> str:
    """
    Ask a natural-language question about a specific commodity+district
    using the surrounding pipeline data as grounding context.

    Parameters
    ----------
    df        : Filtered price_weather DataFrame from the dashboard.
    commodity : Crop name (e.g. 'Tomato').
    district  : District name (e.g. 'Nashik').
    question  : The user's question string.
    api_key   : Gemini API key (falls back to GEMINI_API_KEY env var).

    Returns
    -------
    str : Analyst's natural-language answer.
    """
    if not question or not question.strip():
        return "Please enter a question first."

    key = api_key or os.getenv("GEMINI_API_KEY", "")
    if not key:
        return (
            "⚠️ No Gemini API key found. "
            "Set GEMINI_API_KEY in your .env file and restart the dashboard."
        )

    context = _build_context_summary(df, commodity, district)

    system_role = textwrap.dedent("""\
        You are an expert agricultural market analyst specialising in Indian mandi (wholesale market) prices.
        You have deep knowledge of how weather patterns — especially rainfall, temperature extremes, and
        droughts — affect crop supply chains and price volatility.
        Be concise (3-5 sentences), data-driven, and farmer-friendly in your language.
        Always reference specific numbers from the data context when they are relevant.
    """)

    prompt = textwrap.dedent(f"""\
        {system_role}

        === MARKET DATA CONTEXT ===
        {context}
        ===========================

        User question: {question}

        Provide a clear, insightful answer based on the data above.
    """)

    return _call_gemini(prompt, key)


# ---------------------------------------------------------------------------
# Preset questions
# ---------------------------------------------------------------------------

PRESET_QUESTIONS = [
    "Why is {commodity} showing high volatility in {district} this period?",
    "How is rainfall affecting {commodity} prices in {district}?",
    "What is the price trend for {commodity} in {district} and should farmers sell now?",
    "Is the current temperature extreme likely to push {commodity} prices higher next week?",
]


def get_preset_questions(commodity: str, district: str) -> list[str]:
    """Returns the 4 preset questions with commodity/district interpolated."""
    return [q.format(commodity=commodity, district=district) for q in PRESET_QUESTIONS]
