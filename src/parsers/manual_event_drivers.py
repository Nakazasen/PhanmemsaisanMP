"""Manual event-driver parser for business counts that cannot be inferred."""

from __future__ import annotations

import csv
import os
import sqlite3
from typing import Any

from src.engine.account_resolver import AccountResolutionError, resolve_account_code_for_connection
from src.utils.excel_helpers import get_fy_months, normalize_cc_code, safe_float


TEMPLATE_FILENAME = "event_drivers_manual.csv"
SOURCE_NAME = "manual_event_driver"
ALLOWED_EVENT_TYPES = {"", "manual_amount", "manual_count_unit_price", "month_specific_driver"}
REQUIRED_COLUMNS = ("cc_code", "event_name")
OPTIONAL_COLUMNS = (
    "period",
    "target_month",
    "source_month",
    "posting_rule",
    "target_month_rule",
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
    "headcount_basis",
    "description",
    "note",
)
TEMPLATE_COLUMNS = (
    "cc_code",
    "period",
    "target_month",
    "source_month",
    "posting_rule",
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


def _normalize_posting_rule(value: Any) -> str:
    return str(value or "").replace("\u3000", " ").strip().lower()


def _is_next_month_rule(value: Any) -> bool:
    return _normalize_posting_rule(value) in {"next_month", "next_month_from_source", "source_month_next"}


def _next_calendar_month(period: str) -> str | None:
    text = str(period or "").strip()
    if len(text) != 6 or not text.isdigit():
        return None
    year = int(text[:4])
    month = int(text[4:])
    if not 1 <= month <= 12:
        return None
    if month == 12:
        return f"{year + 1}01"
    return f"{year}{month + 1:02d}"


def _target_periods_from_rule(
    row: dict[str, Any], fy_months: list[str], valid_periods: set[str]
) -> tuple[list[str], bool, str, str | None]:
    posting_rule, posting_rule_ok = _merged_value(row, "posting_rule", "target_month_rule")
    if not posting_rule_ok:
        return [], False, "", "Conflicting posting_rule/target_month_rule values"
    if not _is_next_month_rule(posting_rule):
        period_text, period_ok = _merged_value(row, "period", "target_month")
        if not period_ok:
            return [], False, "", "Conflicting period/target_month values"
        target_periods, repeat_all_months = _target_periods(period_text, fy_months, valid_periods)
        return target_periods, repeat_all_months, "", None

    source_text = str(row.get("source_month") or "").strip()
    shifted_period = _next_calendar_month(source_text)
    if shifted_period is None:
        return [], False, "", "posting_rule next_month requires a valid source_month"
    if shifted_period not in valid_periods:
        return [], False, "", f"next month from source_month {source_text} is outside FY months"
    source_period = _normalize_period(source_text, valid_periods)
    if source_period is None:
        source_period = source_text
    return [shifted_period], False, f"|source_month={source_period}|posting_rule=next_month|shifted_to={shifted_period}", None


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


def _resolve_account_code(conn: sqlite3.Connection, cc_code: str, account_jp_name: str) -> int | None:
    try:
        return resolve_account_code_for_connection(conn, cc_code, account_jp_name)
    except AccountResolutionError:
        return None


def _resolve_account_code_or_error(conn: sqlite3.Connection, cc_code: str, account_jp_name: str) -> int:
    return resolve_account_code_for_connection(conn, cc_code, account_jp_name)


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
    error_messages: list[str] = []

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

            target_periods, repeat_all_months, shift_metadata, period_error = _target_periods_from_rule(
                row, fy_months, valid_periods
            )
            if period_error:
                errors += 1
                error_messages.append(period_error)
                continue

            cc_code = normalize_cc_code(row.get("cc_code"))
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
                try:
                    account_code = _resolve_account_code_or_error(conn, cc_code, account_jp_name)
                except AccountResolutionError as exc:
                    errors += 1
                    error_messages.append(str(exc))
                    continue

            if not cc_code or cc_code not in valid_cc_codes or not target_periods or not event_name:
                errors += 1
                continue
            form_row_text, form_row_ok = _merged_value(row, "form_row", "row")
            if not form_row_ok:
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
            final_description = f"{event_name}: {final_description}|formula_expr={formula_expr}{shift_metadata}"
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
    result: dict[str, int | str] = {"inserted": inserted, "skipped": skipped, "errors": errors, "template_path": template_path}
    if error_messages:
        result["error_message"] = "; ".join(error_messages)
    return result
