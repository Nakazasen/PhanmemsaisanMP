"""
Manual special-cost parser.

Users can provide row-specific monthly costs in:
  source_dir/special_costs_manual.csv

This is intended for business cases that already have a fixed destination row
in FORM.xlsx but do not yet have a machine-readable source workbook, such as:
- foreign-worker visa / resident-card / GPLD paperwork
- one-off administrative costs with exact target rows
"""

from __future__ import annotations

import csv
import os
import sqlite3
from typing import Any

from src.utils.excel_helpers import get_fy_months, safe_float


TEMPLATE_FILENAME = "special_costs_manual.csv"
REQUIRED_COLUMNS = ("cc_code", "period", "form_row", "account_code", "amount_vnd", "description")


def _normalize_period(raw_period: Any, valid_periods: set[str]) -> str | None:
    if raw_period is None:
        return None
    text = str(raw_period).strip()
    if text in valid_periods:
        return text
    if text.isdigit() and 1 <= int(text) <= 12:
        month = int(text)
        for period in valid_periods:
            if int(period[-2:]) == month:
                return period
    return None


def ensure_manual_special_costs_template(source_dir: str, fiscal_year: int) -> str:
    path = os.path.join(source_dir, TEMPLATE_FILENAME)
    if os.path.exists(path):
        return path

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["cc_code", "period", "form_row", "account_code", "amount_vnd", "description"])
    return path


def parse_manual_special_costs(conn: sqlite3.Connection, source_dir: str | None = None) -> dict[str, int | str]:
    fy_row = conn.execute("SELECT value FROM sys_params WHERE key='fiscal_year'").fetchone()
    fiscal_year = int(str(fy_row[0]).upper().replace("FY", "").strip()) if fy_row else 2027
    valid_periods = set(get_fy_months(fiscal_year))

    search_dir = source_dir or os.getcwd()
    template_path = ensure_manual_special_costs_template(search_dir, fiscal_year)
    if not os.path.exists(template_path):
        return {"inserted": 0, "skipped": 0, "errors": 0, "template_path": template_path}

    valid_cc_codes = {int(row[0]) for row in conn.execute("SELECT code FROM dim_cost_centers").fetchall()}
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fact_input_data WHERE source = 'manual_special_cost'")

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
            raw_form_row = str(row.get("form_row", "")).strip()
            raw_account_code = str(row.get("account_code", "")).strip()
            raw_amount = row.get("amount_vnd", "")
            description = str(row.get("description", "") or "").strip()

            if description.lower().startswith("example only"):
                skipped += 1
                continue

            if not raw_cc and not str(raw_period).strip() and not raw_form_row and not raw_account_code and not str(raw_amount).strip():
                skipped += 1
                continue

            try:
                cc_code = int(float(raw_cc))
                form_row = int(float(raw_form_row))
                account_code = int(float(raw_account_code))
            except (ValueError, TypeError):
                errors += 1
                continue

            if cc_code not in valid_cc_codes or form_row <= 0 or account_code <= 0:
                errors += 1
                continue

            period = _normalize_period(raw_period, valid_periods)
            if period is None:
                errors += 1
                continue

            amount_vnd = safe_float(raw_amount)
            if amount_vnd <= 0:
                skipped += 1
                continue

            cursor.execute(
                """
                INSERT INTO fact_input_data
                (source, period, amount_vnd, cc_code, account_code, form_row, scenario_id, description)
                VALUES ('manual_special_cost', ?, ?, ?, ?, ?, 'base', ?)
                """,
                (period, amount_vnd, cc_code, account_code, form_row, description),
            )
            inserted += 1

    conn.commit()
    return {"inserted": inserted, "skipped": skipped, "errors": errors, "template_path": template_path}
