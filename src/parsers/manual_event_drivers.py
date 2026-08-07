"""Bộ đọc chỉ tiêu sự kiện nhập tay khi số liệu nghiệp vụ không thể suy ra."""

from __future__ import annotations

import csv
import os
import sqlite3
from typing import Any

from src.engine.account_resolver import AccountResolutionError, resolve_account_code_for_connection
from src.utils.excel_helpers import get_fy_months, normalize_cc_code, safe_float
from src.utils.fiscal_periods import fiscal_period_for_month


TEMPLATE_FILENAME = "event_drivers_manual.csv"
SOURCE_NAME = "manual_event_driver"
EXPLICIT_ZERO_COUNT_MARKER = "explicit_zero_count=1"

EVENT_DEFAULTS = (
    {
        "tokens": ("cốc xếp định kỳ", "coc xep dinh ky", "折りたたみコップ定期"),
        "period": None,
        "form_row": None,
        "unit_price_key": "折りたたみコップ Cốc xếp",
        "account_jp_name": "福利厚生費",
        "business_identity": "periodic_cup",
        "separate_count": True,
    },
    {
        "tokens": ("部門方針発表会後の決起コンパ", "phương châm bộ phận", "phuong cham bo phan"),
        "posting_month": 4,
        "form_row": None,
        "unit_price_key": "部門方針発表会後の決起コンパ",
        "separate_count": True,
    },
    {
        "tokens": ("tiệc khuấy động năm tài chính", "決起コンパ"),
        "posting_month": 5,
        "form_row": None,
        "unit_price_key": "Tiệc khuấy động năm tài chính決起コンパ",
        "separate_count": False,
    },
    {
        "tokens": ("社員旅行不参加", "không thể tham gia du lịch", "khong the tham gia du lich"),
        "posting_month": 6,
        "form_row": None,
        "unit_price_key": "社員旅行不参加対象者へのギフト贈呈",
        "separate_count": True,
    },
    {
        "tokens": ("マイエピソード", "cảm nghĩ về triết lý kinh doanh", "cam nghi ve triet ly kinh doanh"),
        "posting_month": 7,
        "form_row": None,
        "unit_price_key": "マイエピソード ～フィロソフィの実践～参加賞",
        "separate_count": True,
    },
    {
        "tokens": ("京セラフェスティバル", "lễ hội kyocera", "le hoi kyocera"),
        "posting_month": 9,
        "form_row": 66,
        "unit_price_key": "京セラフェスティバル",
        "separate_count": False,
    },
    {
        "tokens": ("月餅", "bánh trung thu", "banh trung thu"),
        "posting_month": 9,
        "form_row": 71,
        "unit_price_key": "月餅",
        "separate_count": False,
    },
    {
        "tokens": ("10年勤続記念コンパ", "tiệc kỷ niệm 10 năm", "tiec ky niem 10 nam"),
        "posting_month": 10,
        "form_row": None,
        "unit_price_key": "10年勤続記念コンパ",
        "separate_count": True,
    },
    {
        "tokens": ("10年勤続記念品", "quà kỷ niệm", "qua ky niem"),
        "posting_month": 10,
        "form_row": None,
        "unit_price_key": "10年勤続記念品",
        "separate_count": True,
    },
    {
        "tokens": ("会社設立記念", "sự kiện tri ân", "su kien tri an"),
        "posting_month": 10,
        "form_row": 68,
        "unit_price_key": "会社設立記念 感謝イベント",
        "separate_count": False,
    },
    {
        "tokens": ("ポケットカレンダー", "lịch bỏ túi", "lich bo tui"),
        "posting_month": 11,
        "form_row": 82,
        "unit_price_key": "ポケットカレンダー",
        "separate_count": False,
    },
    {
        "tokens": ("運動会", "đại hội thể thao", "dai hoi the thao"),
        "posting_month": 11,
        "form_row": 67,
        "unit_price_key": "運動会",
        "separate_count": False,
    },
    {
        "tokens": ("忘年会補助金", "hỗ trợ tiệc tất niên", "ho tro tiec tat nien"),
        "posting_month": 2,
        "form_row": None,
        "unit_price_key": "忘年会補助金",
        "separate_count": False,
    },
    {
        "tokens": ("お年玉", "tiền lì xì", "tien li xi"),
        "posting_month": 2,
        "form_row": 63,
        "unit_price_key": "お年玉",
        "separate_count": False,
    },
)
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
    "bus_expat_people",
    "bus_vietnamese_people",
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
    "bus_expat_people",
    "bus_vietnamese_people",
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
        return [], False, "", "Giá trị posting_rule và target_month_rule bị mâu thuẫn"
    if not _is_next_month_rule(posting_rule):
        period_text, period_ok = _merged_value(row, "period", "target_month")
        if not period_ok:
            return [], False, "", "Giá trị period và target_month bị mâu thuẫn"
        target_periods, repeat_all_months = _target_periods(period_text, fy_months, valid_periods)
        return target_periods, repeat_all_months, "", None

    source_text = str(row.get("source_month") or "").strip()
    shifted_period = _next_calendar_month(source_text)
    if shifted_period is None:
        return [], False, "", "Quy tắc chuyển sang tháng kế tiếp yêu cầu source_month hợp lệ"
    if shifted_period not in valid_periods:
        return [], False, "", f"Tháng kế tiếp của source_month {source_text} nằm ngoài các kỳ của năm tài chính"
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


def _is_explicit_zero(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    try:
        return abs(float(text.replace(",", ""))) < 1e-9
    except (TypeError, ValueError):
        return False


def _event_match_text(value: Any) -> str:
    return _normalize_unit_price_key(value).lower()


def _event_default_for_name(event_name: Any) -> dict[str, Any] | None:
    text = _event_match_text(event_name)
    if not text:
        return None
    for default in EVENT_DEFAULTS:
        if any(_event_match_text(token) in text for token in default["tokens"]):
            return default
    return None


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


def _default_period_for_fiscal_year(event_default: dict[str, Any], fiscal_year: int) -> str | None:
    """Resolve a business posting month for the selected fiscal year."""
    posting_month = event_default.get("posting_month")
    if posting_month not in (None, ""):
        try:
            month = int(posting_month)
        except (TypeError, ValueError):
            return None
        return fiscal_period_for_month(fiscal_year, month) if 1 <= month <= 12 else None
    # Read old user-maintained rows for FY2027, but always translate the month
    # instead of carrying their calendar year into a later fiscal run.
    value = str(event_default.get("period", "") or "").strip()
    if not value:
        return None
    if not (len(value) == 6 and value.isdigit()):
        return value
    return fiscal_period_for_month(fiscal_year, int(value[-2:]))


def _resolve_default_unit_price(conn: sqlite3.Connection, event_default: dict[str, Any]) -> float | None:
    direct = _resolve_unit_price(conn, str(event_default.get("unit_price_key", "") or ""))
    if direct is not None:
        return direct
    tokens = [_normalize_unit_price_key(token) for token in event_default.get("tokens", ())]
    tokens = [token for token in tokens if len(token) >= 4]
    matches = []
    for row in conn.execute("SELECT item_name, unit_price FROM map_allocation_rules").fetchall():
        item = _normalize_unit_price_key(row["item_name"])
        if any(token in item for token in tokens):
            matches.append(row)
    if len(matches) != 1:
        return None
    price = safe_float(matches[0]["unit_price"])
    return price if price > 0 else None


def parse_manual_event_drivers(conn: sqlite3.Connection, source_dir: str | None = None) -> dict[str, int | str]:
    """Load manual event counts/amounts into fact_input_data.

    This is intentionally explicit: if a value cannot be inferred from source workbooks,
    users provide the business count and destination row/account instead of the system
    guessing.
    """
    fy_row = conn.execute("SELECT value FROM sys_params WHERE key='fiscal_year'").fetchone()
    if not fy_row:
        raise ValueError("Thiếu năm tài chính trong dữ liệu lần chạy; không được tự mặc định FY2027.")
    fiscal_year = int(str(fy_row[0]).upper().replace("FY", "").strip())
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
    periodic_cup_keys: set[tuple[str, str]] = set()

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
                "error_message": f"Thiếu các cột bắt buộc: {', '.join(missing_cols)}",
            }

        for row in reader:
            raw_values = [str(row.get(col, "") or "").strip() for col in REQUIRED_COLUMNS + OPTIONAL_COLUMNS]
            if not any(raw_values):
                skipped += 1
                continue

            cc_code = normalize_cc_code(row.get("cc_code"))
            event_name = str(row.get("event_name", "") or "").strip()
            event_default = _event_default_for_name(event_name)
            if (
                event_default
                and (event_default.get("posting_month") not in (None, "") or event_default.get("period"))
                and not any(str(row.get(col, "") or "").strip() for col in ("period", "target_month", "source_month", "posting_rule", "target_month_rule"))
            ):
                row["period"] = _default_period_for_fiscal_year(event_default, fiscal_year)
            if (
                event_default
                and event_default.get("form_row") is not None
                and not event_default.get("separate_count")
                and not str(row.get("form_row", "") or "").strip()
                and not str(row.get("row", "") or "").strip()
            ):
                row["form_row"] = str(event_default["form_row"])

            target_periods, repeat_all_months, shift_metadata, period_error = _target_periods_from_rule(
                row, fy_months, valid_periods
            )
            if period_error:
                errors += 1
                error_messages.append(period_error)
                continue

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
            if not account_jp_name and event_default:
                account_jp_name = str(event_default.get("account_jp_name", "") or "")

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
            business_identity = str(event_default.get("business_identity", "") or "") if event_default else ""
            if business_identity == "periodic_cup":
                if any(int(period[-2:]) not in {2, 8} for period in target_periods):
                    errors += 1
                    error_messages.append("Cốc xếp định kỳ chỉ được nhập cho tháng 2 hoặc tháng 8")
                    continue
                entitlement = conn.execute(
                    """
                    SELECT source_file, source_sheet, source_cell
                    FROM map_cost_center_uniform_items
                    WHERE cc_code = ? AND item_key = 'collapsible_cup' AND eligible = 1
                    """,
                    (cc_code,),
                ).fetchone()
                if entitlement is None:
                    errors += 1
                    error_messages.append(f"Phòng {cc_code} không thuộc đối tượng cốc xếp")
                    continue
                duplicate_keys = {(cc_code, period) for period in target_periods} & periodic_cup_keys
                if duplicate_keys:
                    errors += 1
                    error_messages.append(
                        "Dòng cốc xếp định kỳ bị trùng: "
                        + ", ".join(f"{cc}/{period}" for cc, period in sorted(duplicate_keys))
                    )
                    continue
                periodic_cup_keys.update((cc_code, period) for period in target_periods)
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
            explicit_zero_count = _is_explicit_zero(row.get("count"))
            if business_identity == "periodic_cup":
                raw_count = str(row.get("count", "") or "").strip()
                if not raw_count or count < 0 or abs(count - round(count)) > 1e-9:
                    errors += 1
                    error_messages.append(
                        f"Số lượng cốc xếp định kỳ phải là số nguyên từ 0 trở lên: cc={cc_code}"
                    )
                    continue
            unit_price = safe_float(row.get("unit_price"))
            amount_vnd = safe_float(row.get("amount_vnd"))
            formula_expr = None
            if (count > 0 or explicit_zero_count) and unit_price <= 0:
                unit_price_key, unit_price_key_ok = _merged_value(row, "unit_price_key", "allocation_content")
                if not unit_price_key_ok:
                    errors += 1
                    continue
                if not unit_price_key and event_default:
                    unit_price_key = str(event_default.get("unit_price_key", "") or "")
                if unit_price_key:
                    resolved_unit_price = _resolve_unit_price(conn, unit_price_key)
                    if resolved_unit_price is None and event_default:
                        resolved_unit_price = _resolve_default_unit_price(conn, event_default)
                    if resolved_unit_price is None:
                        errors += 1
                        continue
                    unit_price = resolved_unit_price

            if count > 0 and unit_price > 0:
                amount_vnd = count * unit_price
                formula_expr = f"{_format_number(count)}*{_format_number(unit_price)}"
            elif explicit_zero_count:
                amount_vnd = 0.0
                if unit_price > 0:
                    formula_expr = f"0*{_format_number(unit_price)}"
                else:
                    formula_expr = "0"
            elif amount_vnd > 0:
                formula_expr = _format_number(amount_vnd)
            else:
                skipped += 1
                continue

            final_description = description or event_name
            final_description = f"{event_name}: {final_description}|formula_expr={formula_expr}{shift_metadata}"
            if business_identity:
                final_description += (
                    f"|business_identity={business_identity}"
                    f"|driver_value={_format_number(count)}|unit_price={_format_number(unit_price)}"
                )
            if business_identity == "periodic_cup":
                final_description += (
                    f"|entitlement_source_file={entitlement['source_file']}"
                    f"|entitlement_source_sheet={entitlement['source_sheet']}"
                    f"|entitlement_source_cell={entitlement['source_cell']}"
                )
            if explicit_zero_count:
                final_description = f"{final_description}|{EXPLICIT_ZERO_COUNT_MARKER}"
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
