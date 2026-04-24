-- =============================================================================
-- forecast_queries.sql
-- Auto Auction Labor Forecasting — Core SQL Logic
-- These queries power the forecast engine and Jupyter notebook analysis.
-- Database: SQLite  |  Table: daily_operations
-- =============================================================================


-- 1. DAILY STAFFING FORECAST
-- Returns the staffing plan for a specific date
SELECT
    date,
    day_of_week,
    is_sale_day,
    planned_volume,
    total_planned_staff
FROM daily_operations
WHERE date = '2024-04-02';

-- =============================================================================
-- 2. AVERAGE VOLUME BY DAY OF WEEK
--    Used to understand typical demand patterns for weekly planning
-- =============================================================================

SELECT
    day_of_week,
    ROUND(AVG(actual_volume), 0) AS avg_volume
FROM daily_operations
GROUP BY day_of_week
ORDER BY day_of_week;



-- =============================================================================
-- 3. UNDERSTAFFED DAYS
--    Flags days where actual staff fell short of plan
-- =============================================================================


SELECT
    date,
    total_actual_staff,
    total_planned_staff,
    variance_staff
FROM daily_operations
WHERE variance_staff < 0


-- =============================================================================
-- 4. MONTHLY VOLUME AND STAFFING SUMMARY
--    High level view for budget and headcount planning
-- =============================================================================



SELECT
    month,
    SUM(actual_volume) AS total_actual_volume,
    ROUND(AVG(total_planned_staff), 0) AS avg_planned_staff
FROM daily_operations
GROUP BY month
ORDER BY month;

-- =============================================================================
-- 5. ANOMALY DETECTION
--    Flags days where staffing variance exceeded 15% in either direction
-- =============================================================================

SELECT
    date,
    day_of_week,
    total_planned_staff,
    total_actual_staff,
    variance_staff
FROM daily_operations
WHERE ABS(variance_staff) / total_planned_staff > 0.15

-- =============================================================================
-- 6. ROLLING 4-WEEK AVERAGE VOLUME BY DAY OF WEEK
--    Used to forecast next week's volume from recent history
-- =============================================================================

SELECT
    day_of_week,
    ROUND(AVG(total_actual_staff), 1) AS avg_staff,
    ROUND(AVG(actual_volume) , 0) AS avg_volume,
    COUNT(*)                          AS sample_days
FROM daily_operations
WHERE date >= DATE('2024-04-30', '-28 days')
  AND date <  '2024-04-30'
GROUP BY day_of_week;


-- =============================================================================
-- 7. WEEK-OVER-WEEK VARIANCE SUMMARY
--    Compares planned vs actual staff for the last 8 weeks
-- =============================================================================
SELECT
    STRFTIME('%Y-W%W', date)        AS week,
    SUM(planned_volume)             AS total_planned_volume,
    SUM(actual_volume)              AS total_actual_volume,
    SUM(total_planned_staff)        AS total_planned_staff,
    SUM(total_actual_staff)         AS total_actual_staff,
    SUM(variance_staff)             AS total_variance,
    ROUND(
        100.0 * SUM(variance_staff)
        / NULLIF(SUM(total_planned_staff), 0), 1
    )                               AS variance_pct
FROM daily_operations
WHERE date >= DATE('2024-04-30', '-56 days')
GROUP BY week
ORDER BY week;

-- =============================================================================
-- 8. UNITS PER LABOR HOUR (UPLH) BY DAY OF WEEK
--    Key productivity metric: total cars / total labor hours worked
-- =============================================================================

SELECT
    day_of_week,
    ROUND(AVG(actual_volume * 1.0 / (total_actual_staff * 8.0)), 2)  AS avg_uplh,
    MIN(actual_volume * 1.0 / (total_actual_staff * 8.0))              AS min_uplh,
    MAX(actual_volume * 1.0 / (total_actual_staff * 8.0))              AS max_uplh
FROM daily_operations
WHERE total_actual_staff > 0
GROUP BY day_of_week
ORDER BY day_of_week;
