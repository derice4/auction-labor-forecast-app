-- =============================================================================
-- forecast_queries.sql
-- Auto Auction Labor Forecasting — Core SQL Logic
-- These queries power the forecast engine and Jupyter notebook analysis.
-- Database: SQLite  |  Table: daily_operations
-- =============================================================================


-- =============================================================================
-- 1. DAILY STAFFING FORECAST
--    Given a target date, return the recommended headcount by role.
--    Replace :target_date with a real date string e.g. '2024-03-15'
-- =============================================================================
SELECT
    date,
    day_of_week,
    is_sale_day,
    planned_volume,
    staff_check_in,
    staff_detailing,
    staff_transport,
    staff_title_admin,
    staff_lane_support,
    total_planned_staff
FROM daily_operations
WHERE date = :target_date;


-- =============================================================================
-- 2. ROLLING 4-WEEK AVERAGE VOLUME BY DAY-OF-WEEK
--    Used to forecast next week's volume from recent history.
-- =============================================================================
SELECT
    day_of_week,
    ROUND(AVG(actual_volume), 0)       AS avg_volume_4wk,
    ROUND(AVG(total_actual_staff), 1)  AS avg_staff_4wk,
    COUNT(*)                           AS sample_days
FROM daily_operations
WHERE date >= DATE(:as_of_date, '-28 days')
  AND date <  :as_of_date
GROUP BY day_of_week
ORDER BY
    CASE day_of_week
        WHEN 'Monday'    THEN 1
        WHEN 'Tuesday'   THEN 2
        WHEN 'Wednesday' THEN 3
        WHEN 'Thursday'  THEN 4
        WHEN 'Friday'    THEN 5
        WHEN 'Saturday'  THEN 6
    END;


-- =============================================================================
-- 3. WEEK-OVER-WEEK VARIANCE SUMMARY
--    Compares planned vs. actual staff for the last 8 weeks.
-- =============================================================================
SELECT
    STRFTIME('%Y-W%W', date)           AS week,
    SUM(planned_volume)                AS total_planned_volume,
    SUM(actual_volume)                 AS total_actual_volume,
    SUM(total_planned_staff)           AS total_planned_staff,
    SUM(total_actual_staff)            AS total_actual_staff,
    SUM(variance_staff)                AS total_variance,
    ROUND(
        100.0 * SUM(variance_staff) / NULLIF(SUM(total_planned_staff), 0),
        1
    )                                  AS variance_pct
FROM daily_operations
WHERE date >= DATE(:as_of_date, '-56 days')
GROUP BY week
ORDER BY week;


-- =============================================================================
-- 4. UNITS PER LABOR HOUR (UPLH) BY DAY OF WEEK
--    Key productivity metric. Total cars / total labor hours worked.
-- =============================================================================
SELECT
    day_of_week,
    ROUND(AVG(actual_volume * 1.0 / (total_actual_staff * 8.0)), 2) AS avg_uplh,
    MIN(actual_volume * 1.0 / (total_actual_staff * 8.0))           AS min_uplh,
    MAX(actual_volume * 1.0 / (total_actual_staff * 8.0))           AS max_uplh
FROM daily_operations
WHERE total_actual_staff > 0
GROUP BY day_of_week
ORDER BY
    CASE day_of_week
        WHEN 'Monday'    THEN 1
        WHEN 'Tuesday'   THEN 2
        WHEN 'Wednesday' THEN 3
        WHEN 'Thursday'  THEN 4
        WHEN 'Friday'    THEN 5
        WHEN 'Saturday'  THEN 6
    END;


-- =============================================================================
-- 5. MONTHLY STAFFING TREND
--    High-level view of volume and staffing across the year.
-- =============================================================================
SELECT
    month,
    CASE month
        WHEN  1 THEN 'January'   WHEN  2 THEN 'February'
        WHEN  3 THEN 'March'     WHEN  4 THEN 'April'
        WHEN  5 THEN 'May'       WHEN  6 THEN 'June'
        WHEN  7 THEN 'July'      WHEN  8 THEN 'August'
        WHEN  9 THEN 'September' WHEN 10 THEN 'October'
        WHEN 11 THEN 'November'  WHEN 12 THEN 'December'
    END                              AS month_name,
    SUM(planned_volume)              AS total_planned_volume,
    SUM(actual_volume)               AS total_actual_volume,
    ROUND(AVG(total_planned_staff), 1) AS avg_daily_planned_staff,
    ROUND(AVG(total_actual_staff),  1) AS avg_daily_actual_staff,
    COUNT(*)                         AS operating_days
FROM daily_operations
GROUP BY month
ORDER BY month;


-- =============================================================================
-- 6. NEXT 7-DAY FORECAST VIEW
--    Returns the forecast for the upcoming week from a given start date.
-- =============================================================================
SELECT
    date,
    day_of_week,
    is_sale_day,
    planned_volume,
    staff_check_in,
    staff_detailing,
    staff_transport,
    staff_title_admin,
    staff_lane_support,
    total_planned_staff
FROM daily_operations
WHERE date >= :start_date
  AND date <  DATE(:start_date, '+7 days')
ORDER BY date;


-- =============================================================================
-- 7. ANOMALY DETECTION — HIGH VARIANCE DAYS
--    Flags days where actual staff deviated significantly from plan (>15%).
-- =============================================================================
SELECT
    date,
    day_of_week,
    total_planned_staff,
    total_actual_staff,
    variance_staff,
    ROUND(
        100.0 * variance_staff / NULLIF(total_planned_staff, 0),
        1
    )                     AS variance_pct,
    CASE
        WHEN variance_staff > 0 THEN 'OVERSTAFFED'
        ELSE 'UNDERSTAFFED'
    END                   AS status
FROM daily_operations
WHERE ABS(variance_staff * 1.0 / NULLIF(total_planned_staff, 0)) > 0.15
ORDER BY ABS(variance_staff) DESC
LIMIT 20;
