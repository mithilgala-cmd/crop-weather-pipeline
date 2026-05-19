SELECT
    date AS alert_date,
    commodity,
    district,
    volatility_score,
    modal_price,
    precipitation_mm,
    'High Volatility Alert' AS alert_reason
FROM {{ ref('joined_prices') }}
WHERE volatility_score > 0.3
