-- Analytical queries against subsense.transactions_curated.
-- These run at whatever scale the S3 data grows to - the same partition
-- pruning (year/month) that keeps the demo fast keeps a warehouse with
-- years of multi-account transaction history fast too.


-- 1. Monthly spend by category - the numbers behind the dashboard's trend chart.
SELECT
    year,
    month,
    category,
    ROUND(SUM(amount), 2) AS total_spend,
    COUNT(*)              AS transaction_count
FROM subsense.transactions_curated
GROUP BY year, month, category
ORDER BY year DESC, month DESC, total_spend DESC;


-- 2. Top merchants by trailing-12-month spend.
SELECT
    merchant_normalized,
    category,
    ROUND(SUM(amount), 2) AS total_spend,
    COUNT(*)              AS charge_count
FROM subsense.transactions_curated
WHERE date_diff('month', DATE(txn_date), CURRENT_DATE) <= 12
GROUP BY merchant_normalized, category
ORDER BY total_spend DESC
LIMIT 25;


-- 3. Recurring-charge candidates, computed warehouse-side.
-- Same idea as the Python detector (backend/app/detection/recurring_detector.py)
-- - consistent day-gaps between consecutive same-merchant charges - expressed
-- as a window-function query instead of app code. Useful for auditing the
-- Python detector's output against an independent SQL implementation, or for
-- ad-hoc analyst queries that don't want to spin up the API.
WITH ordered_charges AS (
    SELECT
        merchant_normalized,
        category,
        amount,
        txn_date,
        LAG(txn_date) OVER (PARTITION BY merchant_normalized ORDER BY txn_date) AS prev_txn_date,
        LAG(amount)   OVER (PARTITION BY merchant_normalized ORDER BY txn_date) AS prev_amount
    FROM subsense.transactions_curated
),
gaps AS (
    SELECT
        merchant_normalized,
        category,
        amount,
        date_diff('day', prev_txn_date, txn_date) AS day_gap,
        ABS(amount - prev_amount) / NULLIF(prev_amount, 0) AS amount_pct_change
    FROM ordered_charges
    WHERE prev_txn_date IS NOT NULL
)
SELECT
    merchant_normalized,
    category,
    ROUND(AVG(amount), 2)        AS avg_amount,
    ROUND(AVG(day_gap), 1)       AS avg_day_gap,
    ROUND(STDDEV(day_gap), 1)    AS day_gap_stddev,
    COUNT(*)                     AS gap_count,
    CASE
        WHEN AVG(day_gap) BETWEEN 25 AND 35 THEN 'monthly'
        WHEN AVG(day_gap) BETWEEN 80 AND 100 THEN 'quarterly'
        WHEN AVG(day_gap) BETWEEN 350 AND 380 THEN 'annual'
        WHEN AVG(day_gap) BETWEEN 5 AND 9 THEN 'weekly'
        ELSE 'irregular'
    END AS likely_cadence
FROM gaps
WHERE amount_pct_change IS NULL OR amount_pct_change <= 0.06   -- same 6% tolerance as the Python detector
GROUP BY merchant_normalized, category
HAVING COUNT(*) >= 2                                            -- >=2 gaps = >=3 charges, same floor as MIN_OCCURRENCES
   AND STDDEV(day_gap) <= 5                                     -- tight consistency required, same principle as the confidence gate
ORDER BY avg_amount * (365.0 / NULLIF(AVG(day_gap), 0)) DESC;   -- rank by implied annualized cost


-- 4. Month-over-month recurring spend trend (for the "you're up/down X%" insight).
WITH monthly_totals AS (
    SELECT year, month, ROUND(SUM(amount), 2) AS total
    FROM subsense.transactions_curated
    GROUP BY year, month
)
SELECT
    year,
    month,
    total,
    LAG(total) OVER (ORDER BY year, month) AS prior_month_total,
    ROUND(total - LAG(total) OVER (ORDER BY year, month), 2) AS delta
FROM monthly_totals
ORDER BY year DESC, month DESC;
