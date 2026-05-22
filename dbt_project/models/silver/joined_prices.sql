SELECT
    m.*,
    w.precipitation_mm,
    w.temp_max_c,
    w.temp_min_c,
    ROUND((m.max_price - m.min_price) / NULLIF(m.modal_price, 0), 4) AS volatility_score,
    CASE
        WHEN (m.max_price - m.min_price) / NULLIF(m.modal_price, 0) > 0.3 THEN 'HIGH'
        WHEN (m.max_price - m.min_price) / NULLIF(m.modal_price, 0) > 0.1 THEN 'MEDIUM'
        ELSE 'LOW'
    END AS volatility_label,
    (m.modal_price - LAG(m.modal_price) OVER (PARTITION BY m.district, m.commodity ORDER BY m.date)) / NULLIF(LAG(m.modal_price) OVER (PARTITION BY m.district, m.commodity ORDER BY m.date), 0) * 100 AS price_change_pct
FROM {{ ref('stg_mandi') }} m
LEFT JOIN {{ ref('stg_weather') }} w
    ON m.district = w.district AND m.date = w.date
