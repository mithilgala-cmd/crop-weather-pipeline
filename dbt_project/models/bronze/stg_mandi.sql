SELECT
    CAST(date AS DATE)       AS date,
    TRIM(commodity)          AS commodity,
    TRIM(district)           AS district,
    TRIM(state)              AS state,
    CAST(modal_price AS DOUBLE) AS modal_price,
    CAST(min_price AS DOUBLE)   AS min_price,
    CAST(max_price AS DOUBLE)   AS max_price
FROM {{ source('raw', 'mandi_raw') }}
WHERE modal_price IS NOT NULL AND modal_price > 0;
