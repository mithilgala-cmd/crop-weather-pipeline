SELECT
    m.date,
    m.commodity,
    m.district,
    m.state,
    m.market,
    m.min_price,
    m.max_price,
    m.modal_price,
    w.precipitation_mm,
    w.temp_max_c,
    w.temp_min_c,
    ROUND((m.max_price - m.min_price) / NULLIF(m.modal_price, 0), 4) AS volatility_score
FROM {{ ref('stg_mandi') }} m
LEFT JOIN {{ ref('stg_weather') }} w
    ON m.district = w.district AND m.date = w.date;
