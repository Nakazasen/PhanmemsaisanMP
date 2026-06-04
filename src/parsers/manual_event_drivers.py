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
REQUIRED_COLUMNS = ("cc_code", "event_name")
OPTIONAL_COLUMNS = (
    "period",
    "target_month",
    "event_type",
    "count",
    "unit_price",
    "unit_price_key",
    "allocation_content",
    "amount_vnd",
    "account_code",
    "account_jp_name",
    "account_name",
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
    "unit_price_key",
    "allocation_content",
    "amount_vnd",
    "account_code",
    "account_jp_name",
    "account_name",
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


def _target_periods(raw_period: Any, fy_months: list[str], valid_periods: set[str]) -> tuple[list[str], bool]:
    text = str(raw_period or "").strip().lower()
    if text in {"all", "every_month", "12months"}:
        return list(fy_months), True
    period = _normalize_period(raw_period, valid_periods)
    return ([period], False) if period is not None else ([], False)


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


def _is_valid_account_code(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() not in ("", "0")
    return value != 0


def _account_for_cost_type(cost_type: str, account_row: sqlite3.Row) -> int | None:
    text = str(cost_type or "")
    if "製造" in text:
        value = account_row["mfg_code"]
    elif "販売" in text:
        value = account_row["sales_code"]
    else:
        value = account_row["ga_code"]

    if not _is_valid_account_code(value):
        return None
    return int(value)


def _resolve_account_code(conn: sqlite3.Connection, cc_code: str, account_jp_name: str) -> int | None:
    account_name = str(account_jp_name or "").strip()
    if not cc_code or not account_name:
        return None

    cc_row = conn.execute(
        "SELECT cost_type FROM dim_cost_centers WHERE code = ?",
        (str(cc_code).strip(),),
    ).fetchone()
    if cc_row is None:
        return None

    account_rows = conn.execute(
        "SELECT mfg_code, ga_code, sales_code FROM dim_accounts WHERE name_jp = ?",
        (account_name,),
    ).fetchall()
    if len(account_rows) != 1:
        return None

    return _account_for_cost_type(str(cc_row["cost_type"] or ""), account_rows[0])


def _normalize_unit_price_key(value: Any) -> str:
    text = str(value or "").replace("\u3000", " ").strip()
    if ":" in text:
        text = text.split(":", 1)[0].strip()
    return " ".join(text.split())


def _resolve_unit_price(conn: sqlite3.Connection, unit_price_key: str) -> float | None:
    normalized_key = _normalize_unit_price_key(unit_price_key)
    if not normalized_key:
        return None

    rows = conn.execute(
        "SELECT item_name, unit_price FROM map_allocation_rules"
    ).fetchall()
    matches = [
        row
        for row in rows
        if _normalize_unit_price_key(row["item_name"]) == normalized_key
    ]
    if len(matches) != 1:
        return None

    unit_price = safe_float(matches[0]["unit_price"])
    return unit_price if unit_price > 0 else None


def parse_manual_event_drivers(conn: sqlite3.Connection, source_dir: str | None = None) -> dict[str, int | str]:
    """Load manual event counts/amounts into fact_input_data.

    This is intentionally explicit: if a value cannot be inferred from source workbooks,
    users provide the business count and destination row/account instead of the system
    guessing.
    """
    fy_row = conn.execute("SELECT value FROM sys_params WHERE key='fiscal_year'").fetchone()
    fiscal_year = int(str(fy_row[0]).upper().replace("FY", "").strip()) if fy_row else 2027
    fy_months = get_fy_months(fiscal_year)
    valid_periods = set(fy_months)

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
            target_periods, repeat_all_months = _target_periods(period_text, fy_months, valid_periods)
            event_name = str(row.get("event_name", "") or "").strip()
            event_type = str(row.get("event_type", "") or "").strip()
            description = str(row.get("description", "") or "").strip()
            note = str(row.get("note", "") or "").strip()
            if not description:
                description = note

            if event_type not in ALLOWED_EVENT_TYPES:
                errors += 1
                continue

            account_jp_name, account_name_ok = _merged_value(row, "account_jp_name", "account_name")
            if not account_name_ok:
                errors += 1
                continue

            account_code_text = str(row.get("account_code", "") or "").strip()
            if account_code_text:
                try:
                    account_code = int(float(account_code_text))
                except (TypeError, ValueError):
                    errors += 1
                    continue
            else:
                account_code = _resolve_account_code(conn, cc_code, account_jp_name)
                if account_code is None:
                    errors += 1
                    continue

            if not cc_code or cc_code not in valid_cc_codes or not target_periods or not event_name:
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
            if count > 0 and unit_price <= 0:
                unit_price_key, unit_price_key_ok = _merged_value(row, "unit_price_key", "allocation_content")
                if not unit_price_key_ok:
                    errors += 1
                    continue
                if unit_price_key:
                    resolved_unit_price = _resolve_unit_price(conn, unit_price_key)
                    if resolved_unit_price is None:
                        errors += 1
                        continue
                    unit_price = resolved_unit_price

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
            if repeat_all_months:
                final_description = f"{final_description}|repeat=all_months"
            cursor.executemany(
                """
                INSERT INTO fact_input_data
                (source, period, amount_vnd, cc_code, account_code, form_row, scenario_id, description)
                VALUES (?, ?, ?, ?, ?, ?, 'base', ?)
                """,
                [
                    (SOURCE_NAME, period, amount_vnd, cc_code, account_code, form_row, final_description)
                    for period in target_periods
                ],
            )
            inserted += len(target_periods)

    conn.commit()
    return {"inserted": inserted, "skipped": skipped, "errors": errors, "template_path": template_path}
