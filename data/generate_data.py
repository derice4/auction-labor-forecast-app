"""
generate_data.py
Generates a synthetic year of auto auction operational data and loads it into SQLite.
Run this first before anything else in the project.
"""

import sqlite3
import random
import os
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "auction_data.db")
SEED = 42
random.seed(SEED)
SHIFT_MINUTES = 480

LABOR_STANDARDS = {
    "check_in":    8,
    "detailing":   45,
    "transport":   12,
    "title_admin":  6,
    "lane_support": 10,
}
SEASONAL = {
    1: 0.80,  2: 0.85,  3: 1.05,  4: 1.15,  5: 1.10,
    6: 1.00,  7: 0.90,  8: 0.95,  9: 1.10, 10: 1.15,
   11: 1.05, 12: 0.75,
}
DOW = {0: 1.10, 1: 1.20, 2: 1.30, 3: 1.25, 4: 1.15, 5: 0.60, 6: 0.00}
SALE_DAYS = {1, 2}

def generate_year(year: int = 2024):
    records = []
    start = date(year, 1, 1)
    end   = date(year, 12, 31)
    delta = timedelta(days=1)
    current = start

while current <= end:
        dow = current.weekday()
        if DOW[dow] == 0.0:
            current += delta
            continue

base_volume = 180
volume = int(
            base_volume
            * SEASONAL[current.month]
            * DOW[dow]
            * random.uniform(0.88, 1.12)
        )
volume = max(volume, 10)
is_sale_day = 1 if dow in SALE_DAYS else 0

def heads(role):
            minutes_needed = volume * LABOR_STANDARDS[role]
            raw = minutes_needed / SHIFT_MINUTES
            if role == "lane_support" and not is_sale_day:
                return 0
            return max(1, -(-int(raw) // 1))
planned = {role: heads(role) for role in LABOR_STANDARDS}
total_planned = sum(planned.values())

callout_factor = random.uniform(0.90, 1.05)
total_actual = max(1, int(total_planned * callout_factor))
actual_volume = int(volume * random.uniform(0.95, 1.05))

records.append({
            "date":                current.isoformat(),
            "day_of_week":         current.strftime("%A"),
            "month":               current.month,
            "is_sale_day":         is_sale_day,
            "planned_volume":      volume,
            "actual_volume":       actual_volume,
            "staff_check_in":      planned["check_in"],
            "staff_detailing":     planned["detailing"],
            "staff_transport":     planned["transport"],
            "staff_title_admin":   planned["title_admin"],
            "staff_lane_support":  planned["lane_support"],
            "total_planned_staff": total_planned,
            "total_actual_staff":  total_actual,
            "variance_staff":      total_actual - total_planned,
        })

current += delta

return records

def load_to_sqlite(records, db_path: str):
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS daily_operations")
    cur.execute("""
        CREATE TABLE daily_operations (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            date                TEXT NOT NULL,
            day_of_week         TEXT,
            month               INTEGER,
            is_sale_day         INTEGER,
            planned_volume      INTEGER,
            actual_volume       INTEGER,
            staff_check_in      INTEGER,
            staff_detailing     INTEGER,
            staff_transport     INTEGER,
            staff_title_admin   INTEGER,
            staff_lane_support  INTEGER,
            total_planned_staff INTEGER,
            total_actual_staff  INTEGER,
            variance_staff      INTEGER
        )
    """)

    cur.executemany("""
        INSERT INTO daily_operations (
            date, day_of_week, month, is_sale_day,
            planned_volume, actual_volume,
            staff_check_in, staff_detailing, staff_transport,
            staff_title_admin, staff_lane_support,
            total_planned_staff, total_actual_staff, variance_staff
        ) VALUES (
            :date, :day_of_week, :month, :is_sale_day,
            :planned_volume, :actual_volume,
            :staff_check_in, :staff_detailing, :staff_transport,
            :staff_title_admin, :staff_lane_support,
            :total_planned_staff, :total_actual_staff, :variance_staff
        )
    """, records)

    conn.commit()
    conn.close()
    print(f"✅  Loaded {len(records)} days into {db_path}")

    if __name__ == "__main__":
    print("Generating 2024 auction data...")
    records = generate_year(2024)
    load_to_sqlite(records, DB_PATH)
    print("Done. Run the Streamlit app or open the notebook next.")