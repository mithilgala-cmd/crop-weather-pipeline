SELECT
    CAST(date AS DATE)       AS date,
    TRIM(district)          AS district,
    CAST(precipitation_mm AS DOUBLE) AS precipitation_mm,
    CAST(temp_max_c AS DOUBLE) AS temp_max_c,
    CAST(temp_min_c AS DOUBLE) AS temp_min_c,
    CAST(windspeed_kmh AS DOUBLE) AS windspeed_kmh
FROM {{ source('raw', 'weather_raw') }}
WHERE precipitation_mm IS NOT NULL
