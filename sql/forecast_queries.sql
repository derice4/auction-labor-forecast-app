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