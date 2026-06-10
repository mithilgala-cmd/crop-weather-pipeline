-- schema.sql for DuckDB
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
