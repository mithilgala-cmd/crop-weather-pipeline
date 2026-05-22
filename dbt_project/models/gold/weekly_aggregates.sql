SELECT
    DATE_TRUNC('week', date)  AS week_start,
    commodity,
    district,
    ROUND(AVG(modal_price), 2)      AS avg_modal_price,
    ROUND(AVG(precipitation_mm), 2) AS avg_precipitation,
    ROUND(AVG(volatility_score), 4) AS avg_volatility,
    ROUND(MAX(volatility_score), 4) AS max_volatility
FROM {{ ref('joined_prices') }}
GROUP BY 1, 2, 3;
