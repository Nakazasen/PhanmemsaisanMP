"""
GA parser.

Loads:
- per-unit GA costs into fact_input_data as source='ga_unit_price'
- working days into sys_params as working_days_YYYYMM
- monthly headcount by CC into fact_monthly_headcount as source='ga'
"""

import os
import re
import sqlite3
from collections import defaultdict
from typing import Any

import openpyxl
import pandas as pd

from src.utils.excel_helpers import get_fy_months, safe_float

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

GA_FILE_KEYWORDS = ("総務課", "振替予定")
CALC_SHEET_KEYWORDS = ("cach tinh", "振替", "計算", "tinh")
WORKING_DAY_KEYWORDS = ("稼働日", "ngay lam")
HEADCOUNT_KEYWORDS = ("人員数", "so nguoi", "headcount", "staff", "worker", "direct", "indirect")
STAFF_CATEGORY_KEYWORDS = ("indirect", "gian tiep", "staff", "nhan vien", "dinh phi")
WORKER_CATEGORY_KEYWORDS = ("direct", "truc tiep", "worker", "cong nhan", "bien phi", "g7")
EXCLUDE_HEADCOUNT_ROW_KEYWORDS = ("vnd", "tiền", "tien", "alloc", "rate", "ratio", "đơn giá", "don gia")


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _find_ga_file(source_dir: str | None, fiscal_year: int) -> str | None:
    search_dir = source_dir or BASE_DIR
    preferred = os.path.join(search_dir, f"総務課 FY{fiscal_year} MP 振替予定.xlsx")
    if os.path.exists(preferred):
        return preferred

    for name in os.listdir(search_dir):
        lower_name = name.lower()
        if not lower_name.endswith(".xlsx"):
            continue
        if all(token in name for token in GA_FILE_KEYWORDS):
            return os.path.join(search_dir, name)
        # Fallback: avoid matching facility/fixed-assets files.
        if str(fiscal_year) in name and "mp" in lower_name and ("ga" in lower_name or "tong vu" in lower_name):
            return os.path.join(search_dir, name)
    return None


def _iter_calc_sheet_names(sheet_names: list[str]) -> list[str]:
    result: list[str] = []
    for sheet_name in sheet_names:
        normalized = _normalize_text(sheet_name)
        if any(token in normalized for token in ("cach tinh", "振替", "計算", "tính")):
            result.append(sheet_name)
            continue
        if any(keyword in normalized for keyword in CALC_SHEET_KEYWORDS):
            result.append(sheet_name)
    return result


def _parse_ga_main_sheet(df: pd.DataFrame, fy_months: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    header_row = None

    for i in range(min(25, len(df))):
        first_col = _normalize_text(df.iloc[i, 0] if len(df.columns) > 0 else "")
        if "item" in first_col or "内容" in first_col:
            header_row = i
            break

    if header_row is None:
        return records

    for i in range(header_row + 1, len(df)):
        row = df.iloc[i]
        item_name = str(row.iloc[0]).strip() if not pd.isna(row.iloc[0]) else ""
        if not item_name:
            continue

        lowered_name = item_name.lower()
        if "total" in lowered_name or "tổng" in lowered_name or "tong" in lowered_name or "合計" in item_name:
            continue

        basis = _normalize_text(row.iloc[14] if len(row) > 14 else "")
        driver = "working_days" if any(keyword in basis for keyword in WORKING_DAY_KEYWORDS) else "headcount_per_person"

        for month_index in range(min(12, len(fy_months))):
            value_index = month_index + 1
            if value_index >= len(row):
                continue
            amount = safe_float(row.iloc[value_index])
            if amount <= 0:
                continue
            records.append(
                {
                    "period": fy_months[month_index],
                    "amount": amount,
                    "item": item_name,
                    "driver": driver,
                }
            )

    return records


def _parse_working_days_sheet(df: pd.DataFrame, fy_months: list[str]) -> dict[str, float]:
    working_days: dict[str, float] = {}
    for i in range(len(df)):
        label = _normalize_text(df.iloc[i, 1] if len(df.columns) > 1 else "")
        if not any(keyword in label for keyword in WORKING_DAY_KEYWORDS):
            continue
        for month_index in range(min(12, len(fy_months))):
            col_index = month_index + 2
            if col_index >= len(df.columns):
                continue
            value = safe_float(df.iloc[i, col_index])
            if value > 0:
                working_days[fy_months[month_index]] = value
        break
    return working_days


def _detect_category(row_text: str, current_category: str) -> str:
    if any(keyword in row_text for keyword in WORKER_CATEGORY_KEYWORDS):
        return "worker"
    if any(keyword in row_text for keyword in STAFF_CATEGORY_KEYWORDS):
        return "staff"
    return current_category


def _extract_candidate_numbers(cell_value: Any) -> list[int]:
    candidates: list[int] = []
    if cell_value is None:
        return candidates

    text = str(cell_value).strip()
    if not text:
        return candidates

    try:
        as_int = int(float(text))
        candidates.append(as_int)
    except (ValueError, TypeError):
        pass

    for token in re.findall(r"\d{4,10}", text):
        try:
            candidates.append(int(token))
        except ValueError:
            continue

    # Keep stable order and remove duplicates.
    seen: set[int] = set()
    ordered: list[int] = []
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        ordered.append(candidate)
    return ordered


def _extract_valid_cc_from_row(row: tuple[Any, ...], valid_cc_codes: set[int]) -> int | None:
    # Scan left-side cells first where CC usually appears.
    for cell in row[:20]:
        candidates = _extract_candidate_numbers(cell)
        for candidate in candidates:
            if candidate in valid_cc_codes:
                return candidate
            # Suffix match for 4-8 digit codes (e.g. 1136 matches 1412001136)
            if 4 <= len(str(candidate)) <= 8:
                str_cand = str(candidate)
                for valid in valid_cc_codes:
                    if str(valid).endswith(str_cand):
                        return valid
    return None


def _parse_ga_headcount_sheet(
    workbook: openpyxl.Workbook,
    sheet_name: str,
    fy_months: list[str],
    valid_cc_codes: set[int],
) -> dict[tuple[int, str], dict[str, float]]:
    try:
        worksheet = workbook[sheet_name]
    except Exception:
        return {}

    aggregated: dict[tuple[int, str], dict[str, float]] = defaultdict(
        lambda: {"headcount_all": 0.0, "headcount_staff": 0.0, "headcount_worker": 0.0}
    )

    active_cc: int | None = None
    current_category = "staff"

    try:
        for row in worksheet.iter_rows(values_only=True):
            if not row:
                continue

            cc_from_row = _extract_valid_cc_from_row(row, valid_cc_codes)
            if cc_from_row is not None:
                active_cc = cc_from_row
                current_category = "staff"

            if active_cc is None:
                continue

            row_text = " ".join(str(value) for value in row[:20] if value is not None).lower()
            current_category = _detect_category(row_text, current_category)

            if not any(keyword in row_text for keyword in HEADCOUNT_KEYWORDS):
                continue
            if any(keyword in row_text for keyword in EXCLUDE_HEADCOUNT_ROW_KEYWORDS):
                continue

            for start in range(1, 20):
                sequence = [safe_float(row[start + offset]) for offset in range(12) if start + offset < len(row)]
                if len(sequence) != 12:
                    continue
                if not any(value > 0 for value in sequence):
                    continue
                if not all(value < 5000 for value in sequence):
                    continue

                category = current_category
                if any(keyword in row_text for keyword in WORKER_CATEGORY_KEYWORDS):
                    category = "worker"
                elif any(keyword in row_text for keyword in STAFF_CATEGORY_KEYWORDS):
                    category = "staff"

                for month_index, value in enumerate(sequence):
                    if value <= 0:
                        continue
                    key = (active_cc, fy_months[month_index])
                    aggregated[key]["headcount_all"] += value
                    if category == "worker":
                        aggregated[key]["headcount_worker"] += value
                    else:
                        aggregated[key]["headcount_staff"] += value
                break
    except Exception:
        return {}

    return aggregated


def parse_ga(conn: sqlite3.Connection, source_dir: str | None = None) -> dict[str, int]:
    """Main entry for GA parsing."""
    fy_row = conn.execute("SELECT value FROM sys_params WHERE key='fiscal_year'").fetchone()
    fiscal_year = int(str(fy_row[0]).upper().replace("FY", "").strip()) if fy_row else 2027
    fy_months = get_fy_months(fiscal_year)

    path = _find_ga_file(source_dir, fiscal_year)
    if not path or not os.path.exists(path):
        return {"total": 0, "working_days": 0, "headcount": 0}

    cursor = conn.cursor()
    cursor.execute("DELETE FROM fact_input_data WHERE source = 'ga_unit_price'")
    cursor.execute("DELETE FROM fact_monthly_headcount WHERE source = 'ga'")

    excel_file = pd.ExcelFile(path, engine="openpyxl")

    main_sheet = excel_file.sheet_names[0]
    main_df = pd.read_excel(excel_file, sheet_name=main_sheet, header=None, engine="openpyxl")
    unit_price_records = _parse_ga_main_sheet(main_df, fy_months)
    for record in unit_price_records:
        cursor.execute(
            """
            INSERT INTO fact_input_data
            (source, period, amount_vnd, cc_code, account_code, scenario_id, description)
            VALUES ('ga_unit_price', ?, ?, 0, 0, 'base', ?)
            """,
            (record["period"], record["amount"], f"{record['item']}|{record['driver']}"),
        )

    working_days_written = 0
    calc_sheet_names = _iter_calc_sheet_names(excel_file.sheet_names)
    for sheet_name in calc_sheet_names:
        calc_df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None, engine="openpyxl")
        working_days = _parse_working_days_sheet(calc_df, fy_months)
        for period, value in working_days.items():
            cursor.execute(
                """
                INSERT OR REPLACE INTO sys_params (key, value, description)
                VALUES (?, ?, ?)
                """,
                (f"working_days_{period}", str(value), f"Working days for {period}"),
            )
            working_days_written += 1
        if working_days:
            break

    valid_cc_codes = {int(row[0]) for row in conn.execute("SELECT code FROM dim_cost_centers").fetchall()}

    aggregated_headcount: dict[tuple[int, str], dict[str, float]] = defaultdict(
        lambda: {"headcount_all": 0.0, "headcount_staff": 0.0, "headcount_worker": 0.0}
    )
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        for sheet_name in calc_sheet_names:
            sheet_data = _parse_ga_headcount_sheet(workbook, sheet_name, fy_months, valid_cc_codes)
            for key, values in sheet_data.items():
                aggregated_headcount[key]["headcount_all"] += values["headcount_all"]
                aggregated_headcount[key]["headcount_staff"] += values["headcount_staff"]
                aggregated_headcount[key]["headcount_worker"] += values["headcount_worker"]
    finally:
        workbook.close()

    for (cc_code, period), values in aggregated_headcount.items():
        cursor.execute(
            """
            INSERT INTO fact_monthly_headcount
            (period, cc_code, headcount_all, headcount_staff, headcount_worker, source)
            VALUES (?, ?, ?, ?, ?, 'ga')
            ON CONFLICT(period, cc_code, source) DO UPDATE SET
                headcount_all = excluded.headcount_all,
                headcount_staff = excluded.headcount_staff,
                headcount_worker = excluded.headcount_worker
            """,
            (period, cc_code, values["headcount_all"], values["headcount_staff"], values["headcount_worker"]),
        )

    conn.commit()
    return {"total": len(unit_price_records), "working_days": working_days_written, "headcount": len(aggregated_headcount)}
