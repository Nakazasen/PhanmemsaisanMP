"""Manual event-driver parser for business counts that cannot be inferred."""

from __future__ import annotations

import csv
import os
import sqlite3
from typing import Any

from src.utils.excel_helpers import get_fy_months, normalize_cc_code, safe_float


TEMPLATE_FILENAME = "event_drivers_manual.csv"
SOURCE_NAME = "manual_event_driver"
ALLOWED_EVENT_TYPES = {"", "manual_amount", "manual_count_unit_price", "month_specific_driver"}
REQUIRED_COLUMNS = ("cc_code", "event_name", "account_code")
OPTIONAL_COLUMNS = (
    "period",
    "target_month",
    "event_type",
    "count",
    "unit_price",
    "amount_vnd",
    "account_group",
    "form_row",
    "row",
    "source_month",
    "headcount_basis",
    "description",
    "note",
)
TEMPLATE_COLUMNS = (
    "cc_code",
    "period",
    "target_month",
    "event_name",
    "event_type",
    "count",
    "unit_price",
    "amount_vnd",
    "account_code",
    "account_group",
    "form_row",
    "row",
    "source_month",
    "headcount_basis",
    "description",
    "note",
)


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


def _format_number(value: float) -> str:
    return str(int(round(value))) if abs(value - round(value)) < 1e-9 else str(value)


def ensure_manual_event_drivers_template(source_dir: str, fiscal_year: int) -> str:
    path = os.path.join(source_dir, TEMPLATE_FILENAME)
    if os.path.exists(path):
        return path

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(TEMPLATE_COLUMNS)
    return path


def _same_nonempty_values(left: str, right: str) -> bool:
    return not left or not right or left == right


def _merged_value(row: dict[str, Any], primary: str, alias: str) -> tuple[str, bool]:
    primary_value = str(row.get(primary, "") or "").strip()
    alias_value = str(row.get(alias, "") or "").strip()
    if not _same_nonempty_values(primary_value, alias_value):
        return "", False
    return primary_value or alias_value, True


def parse_manual_event_drivers(conn: sqlite3.Connection, source_dir: str | None = None) -> dict[str, int | str]:
    """Load manual event counts/amounts into fact_input_data.

    This is intentionally explicit: if a value cannot be inferred from source workbooks,
    users provide the business count and destination row/account instead of the system
    guessing.
    """
    fy_row = conn.execute("SELECT value FROM sys_params WHERE key='fiscal_year'").fetchone()
    fiscal_year = int(str(fy_row[0]).upper().replace("FY", "").strip()) if fy_row else 2027
    valid_periods = set(get_fy_months(fiscal_year))

    search_dir = source_dir or os.getcwd()
    template_path = ensure_manual_event_drivers_template(search_dir, fiscal_year)
    if not os.path.exists(template_path):
        return {"inserted": 0, "skipped": 0, "errors": 0, "template_path": template_path}

    valid_cc_codes = {
        str(row[0]).strip()
        for row in conn.execute("SELECT code FROM dim_cost_centers").fetchall()
        if row[0] is not None
    }
    valid_accounts = {
        int(row[0])
        for row in conn.execute("SELECT code FROM dim_accounts").fetchall()
        if row[0] is not None
    }
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fact_input_data WHERE source = ?", (SOURCE_NAME,))

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
            raw_values = [str(row.get(col, "") or "").strip() for col in REQUIRED_COLUMNS + OPTIONAL_COLUMNS]
            if not any(raw_values):
                skipped += 1
                continue

            period_text, period_ok = _merged_value(row, "period", "target_month")
            form_row_text, form_row_ok = _merged_value(row, "form_row", "row")
            if not period_ok or not form_row_ok:
                errors += 1
                continue

            cc_code = normalize_cc_code(row.get("cc_code"))
            period = _normalize_period(period_text, valid_periods)
            event_name = str(row.get("event_name", "") or "").strip()
            event_type = str(row.get("event_type", "") or "").strip()
            description = str(row.get("description", "") or "").strip()
            note = str(row.get("note", "") or "").strip()
            if not description:
                description = note

            if event_type not in ALLOWED_EVENT_TYPES:
                errors += 1
                continue

            try:
                account_code = int(float(str(row.get("account_code", "")).strip()))
            except (TypeError, ValueError):
                errors += 1
                continue

            if not cc_code or cc_code not in valid_cc_codes or period is None or not event_name:
                errors += 1
                continue
            if account_code not in valid_accounts:
                errors += 1
                continue

            form_row = None
            if form_row_text:
                try:
                    form_row = int(float(form_row_text))
                except (TypeError, ValueError):
                    errors += 1
                    continue
                if form_row <= 0:
                    errors += 1
                    continue

            count = safe_float(row.get("count"))
            unit_price = safe_float(row.get("unit_price"))
            amount_vnd = safe_float(row.get("amount_vnd"))
            formula_expr = None
            if count > 0 and unit_price > 0:
                amount_vnd = count * unit_price
                formula_expr = f"{_format_number(count)}*{_format_number(unit_price)}"
            elif amount_vnd > 0:
                formula_expr = _format_number(amount_vnd)
            else:
                skipped += 1
                continue

            final_description = description or event_name
            final_description = f"{event_name}: {final_description}|formula_expr={formula_expr}"
            cursor.execute(
                """
                INSERT INTO fact_input_data
                (source, period, amount_vnd, cc_code, account_code, form_row, scenario_id, description)
                VALUES (?, ?, ?, ?, ?, ?, 'base', ?)
                """,
                (SOURCE_NAME, period, amount_vnd, cc_code, account_code, form_row, final_description),
            )
            inserted += 1

    conn.commit()
    return {"inserted": inserted, "skipped": skipped, "errors": errors, "template_path": template_path}
