SELECT
    alert_date,
    commodity,
    district,
    volatility_score,
    modal_price,
    precipitation_mm,
    alert_reason
FROM {{ ref('alerts') }}
WHERE volatility_score > 0.3;
