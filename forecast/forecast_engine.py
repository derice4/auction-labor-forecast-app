"""
forecast_engine.py
Loads auction data from SQLite and produces structured forecast outputs
used by both the Streamlit app and the AI summary module.
"""

import sqlite3
import os
from datetime import date, timedelta
from typing import Optional
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "auction_data.db")

# Labor standards: minutes per unit per role (must match generate_data.py)
LABOR_STANDARDS = {
    "check_in":       8,
    "detailing":     45,
    "transport":     12,
    "title_admin":    6,
    "lane_support":  10,
}
SHIFT_MINUTES = 480

SALE_DAYS = {"Tuesday", "Wednesday"}


def get_connection() -> sqlite3.Connection:
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. "
            "Run data/generate_data.py first."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Core forecast helpers ─────────────────────────────────────────────────────

def forecast_staff_for_volume(volume: int, is_sale_day: bool) -> dict:
    """Given a volume number, return headcount needed by role."""
    def heads(role):
        if role == "lane_support" and not is_sale_day:
            return 0
        minutes = volume * LABOR_STANDARDS[role]
        return max(1, -(-minutes // SHIFT_MINUTES))   # ceiling division

    breakdown = {role: heads(role) for role in LABOR_STANDARDS}
    breakdown["total"] = sum(breakdown.values())
    return breakdown


def get_rolling_avg_volume(as_of: date, days: int = 28) -> dict:
    """Return average volume by day-of-week over the last `days` days."""
    conn = get_connection()
    query = """
        SELECT day_of_week,
               ROUND(AVG(actual_volume), 0) AS avg_volume,
               ROUND(AVG(total_actual_staff), 1) AS avg_staff
        FROM daily_operations
        WHERE date >= DATE(:as_of, :offset)
          AND date <  :as_of
        GROUP BY day_of_week
    """
    df = pd.read_sql_query(
        query, conn,
        params={"as_of": as_of.isoformat(), "offset": f"-{days} days"}
    )
    conn.close()
    return df.set_index("day_of_week").to_dict(orient="index")


def get_week_forecast(start_date: date) -> pd.DataFrame:
    """Return the 7-day forecast starting from start_date."""
    conn = get_connection()
    query = """
        SELECT date, day_of_week, is_sale_day, planned_volume,
               staff_check_in, staff_detailing, staff_transport,
               staff_title_admin, staff_lane_support, total_planned_staff
        FROM daily_operations
        WHERE date >= :start
          AND date <  DATE(:start, '+7 days')
        ORDER BY date
    """
    df = pd.read_sql_query(query, conn, params={"start": start_date.isoformat()})
    conn.close()
    return df


def get_wow_variance(as_of: date, weeks: int = 8) -> pd.DataFrame:
    """Week-over-week planned vs actual variance for the last N weeks."""
    conn = get_connection()
    query = """
        SELECT STRFTIME('%Y-W%W', date) AS week,
               SUM(planned_volume)              AS planned_volume,
               SUM(actual_volume)               AS actual_volume,
               SUM(total_planned_staff)         AS planned_staff,
               SUM(total_actual_staff)          AS actual_staff,
               SUM(variance_staff)              AS variance,
               ROUND(100.0 * SUM(variance_staff)
                     / NULLIF(SUM(total_planned_staff), 0), 1) AS variance_pct
        FROM daily_operations
        WHERE date >= DATE(:as_of, :offset)
        GROUP BY week
        ORDER BY week
    """
    df = pd.read_sql_query(
        query, conn,
        params={"as_of": as_of.isoformat(), "offset": f"-{weeks * 7} days"}
    )
    conn.close()
    return df


def get_monthly_trend() -> pd.DataFrame:
    conn = get_connection()
    query = """
        SELECT month,
               CASE month
                   WHEN  1 THEN 'Jan' WHEN  2 THEN 'Feb'
                   WHEN  3 THEN 'Mar' WHEN  4 THEN 'Apr'
                   WHEN  5 THEN 'May' WHEN  6 THEN 'Jun'
                   WHEN  7 THEN 'Jul' WHEN  8 THEN 'Aug'
                   WHEN  9 THEN 'Sep' WHEN 10 THEN 'Oct'
                   WHEN 11 THEN 'Nov' WHEN 12 THEN 'Dec'
               END AS month_name,
               SUM(actual_volume)               AS total_volume,
               ROUND(AVG(total_planned_staff),1) AS avg_daily_staff,
               COUNT(*)                          AS operating_days
        FROM daily_operations
        GROUP BY month ORDER BY month
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def get_anomalies(threshold_pct: float = 15.0) -> pd.DataFrame:
    conn = get_connection()
    query = """
        SELECT date, day_of_week, total_planned_staff, total_actual_staff,
               variance_staff,
               ROUND(100.0 * variance_staff
                     / NULLIF(total_planned_staff,0), 1) AS variance_pct,
               CASE WHEN variance_staff > 0 THEN 'Overstaffed'
                    ELSE 'Understaffed' END AS status
        FROM daily_operations
        WHERE ABS(variance_staff * 1.0 / NULLIF(total_planned_staff,0))
              > (:threshold / 100.0)
        ORDER BY ABS(variance_staff) DESC
        LIMIT 20
    """
    df = pd.read_sql_query(query, conn, params={"threshold": threshold_pct})
    conn.close()
    return df


# ── Summary object for AI module ─────────────────────────────────────────────

def build_forecast_context(target_date: Optional[date] = None) -> dict:
    """
    Assemble a rich context dict for the AI summary module.
    Defaults to today if no date given (uses nearest available data date).
    """
    if target_date is None:
        target_date = date.today()

    # Pull the closest available record
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM daily_operations WHERE date <= ? ORDER BY date DESC LIMIT 1",
        (target_date.isoformat(),)
    ).fetchone()
    conn.close()

    if row is None:
        raise ValueError("No data available on or before the requested date.")

    row = dict(row)

    wow = get_wow_variance(target_date, weeks=4)
    recent_variance_pct = wow["variance_pct"].mean() if not wow.empty else 0.0

    anomalies = get_anomalies()
    anomaly_count = len(anomalies)

    return {
        "date":               row["date"],
        "day_of_week":        row["day_of_week"],
        "is_sale_day":        bool(row["is_sale_day"]),
        "planned_volume":     row["planned_volume"],
        "actual_volume":      row["actual_volume"],
        "staff_breakdown": {
            "check_in":       row["staff_check_in"],
            "detailing":      row["staff_detailing"],
            "transport":      row["staff_transport"],
            "title_admin":    row["staff_title_admin"],
            "lane_support":   row["staff_lane_support"],
        },
        "total_planned_staff":   row["total_planned_staff"],
        "total_actual_staff":    row["total_actual_staff"],
        "variance_staff":        row["variance_staff"],
        "recent_avg_variance_pct": round(recent_variance_pct, 1),
        "anomaly_days_last_month": anomaly_count,
    }
def forecast_staff_for_volume(volume: int, is_sale_day: bool) -> dict:
    breakdown = {}
    for role in LABOR_STANDARDS:
        minutes_needed = volume * LABOR_STANDARDS[role]
        raw = minutes_needed / SHIFT_MINUTES
        if role == "lane_support" and not is_sale_day:
            breakdown[role] = 0
        else:
            breakdown[role] = max(1, -(-int(raw) // 1))
    breakdown["total"] = sum(breakdown.values())
    return breakdown