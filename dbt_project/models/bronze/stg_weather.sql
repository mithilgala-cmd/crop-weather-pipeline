SELECT
    CAST(date AS DATE)       AS date,
    TRIM(district)           AS district,
    TRIM(state)              AS state,
    CAST(precipitation_sum   AS DOUBLE) AS precipitation_mm,
    CAST(temperature_2m_max   AS DOUBLE) AS temp_max_c,
    CAST(temperature_2m_min   AS DOUBLE) AS temp_min_c,
    CAST(windspeed_10m_max    AS DOUBLE) AS windspeed_kmh
FROM {{ source('raw', 'weather_raw') }}
WHERE precipitation_sum IS NOT NULL;
