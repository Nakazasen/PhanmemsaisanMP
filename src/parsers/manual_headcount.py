"""
Manual headcount parser.

Users can provide monthly staff/worker headcount by CC in:
  source_dir/headcount_manual.csv

CSV columns:
  cc_code,period,headcount_staff,headcount_worker,description
"""

import csv
import os
import sqlite3
from typing import Any

from src.utils.excel_helpers import get_fy_months, safe_float

TEMPLATE_FILENAME = "headcount_manual.csv"
REQUIRED_COLUMNS = ("cc_code", "period", "headcount_staff", "headcount_worker")


def _normalize_period(raw_period: Any, valid_periods: set[str]) -> str | None:
    if raw_period is None:
        return None
    text = str(raw_period).strip()
    if text in valid_periods:
        return text

    # Accept MM for fiscal month label, map to FY period.
    if text.isdigit() and 1 <= int(text) <= 12:
        month = int(text)
        for period in valid_periods:
            if int(period[-2:]) == month:
                return period
    return None


def ensure_manual_headcount_template(source_dir: str, fiscal_year: int) -> str:
    """Create template file if not found. Returns the template path."""
    path = os.path.join(source_dir, TEMPLATE_FILENAME)
    if os.path.exists(path):
        return path

    periods = get_fy_months(fiscal_year)
    sample_rows = [
        ["1412000004", periods[0], "21", "180", "Example row - update numbers before run"],
        ["1412000004", periods[1], "21", "182", "Month-by-month update"],
        ["1412000025", periods[0], "35", "0", "Admin department example"],
    ]

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["cc_code", "period", "headcount_staff", "headcount_worker", "description"])
        writer.writerows(sample_rows)
    return path


def parse_manual_headcount(conn: sqlite3.Connection, source_dir: str | None = None) -> dict[str, int | str]:
    """Load manual headcount from CSV and write to fact_monthly_headcount source='manual'."""
    fy_row = conn.execute("SELECT value FROM sys_params WHERE key='fiscal_year'").fetchone()
    fiscal_year = int(str(fy_row[0]).upper().replace("FY", "").strip()) if fy_row else 2027
    valid_periods = set(get_fy_months(fiscal_year))

    search_dir = source_dir or os.getcwd()
    template_path = ensure_manual_headcount_template(search_dir, fiscal_year)
    if not os.path.exists(template_path):
        return {"inserted": 0, "skipped": 0, "errors": 0, "template_path": template_path}

    valid_cc_codes = {int(row[0]) for row in conn.execute("SELECT code FROM dim_cost_centers").fetchall()}
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fact_monthly_headcount WHERE source = 'manual'")

    inserted = 0
    skipped = 0
    errors = 0

    with open(template_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return {"inserted": 0, "skipped": 0, "errors": 1, "template_path": template_path}

        missing_cols = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing_cols:
            return {
                "inserted": 0,
                "skipped": 0,
                "errors": 1,
                "template_path": template_path,
                "error_message": f"Missing required columns: {', '.join(missing_cols)}",
            }

        for row in reader:
            raw_cc = str(row.get("cc_code", "")).strip()
            raw_period = row.get("period", "")
            raw_staff = row.get("headcount_staff", "")
            raw_worker = row.get("headcount_worker", "")
            description = str(row.get("description", "") or "").strip()

            # Allow blank rows in template.
            if not raw_cc and not str(raw_period).strip() and not str(raw_staff).strip() and not str(raw_worker).strip():
                skipped += 1
                continue

            try:
                cc_code = int(float(raw_cc))
            except (ValueError, TypeError):
                errors += 1
                continue
            if cc_code not in valid_cc_codes:
                errors += 1
                continue

            period = _normalize_period(raw_period, valid_periods)
            if period is None:
                errors += 1
                continue

            staff = safe_float(raw_staff)
            worker = safe_float(raw_worker)
            if staff < 0 or worker < 0:
                errors += 1
                continue

            headcount_all = staff + worker
            if headcount_all <= 0:
                skipped += 1
                continue

            cursor.execute(
                """
                INSERT INTO fact_monthly_headcount
                (period, cc_code, headcount_all, headcount_staff, headcount_worker, source, description)
                VALUES (?, ?, ?, ?, ?, 'manual', ?)
                ON CONFLICT(period, cc_code, source) DO UPDATE SET
                    headcount_all = excluded.headcount_all,
                    headcount_staff = excluded.headcount_staff,
                    headcount_worker = excluded.headcount_worker,
                    description = excluded.description
                """,
                (period, cc_code, headcount_all, staff, worker, description),
            )
            inserted += 1

    conn.commit()
    return {"inserted": inserted, "skipped": skipped, "errors": errors, "template_path": template_path}
