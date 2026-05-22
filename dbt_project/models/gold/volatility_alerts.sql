SELECT
    date AS alert_date,
    commodity,
    district,
    volatility_score,
    modal_price,
    precipitation_mm,
    'HIGH_VOLATILITY' AS alert_reason
FROM {{ ref('joined_prices') }}
WHERE volatility_label = 'HIGH'
