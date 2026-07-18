"""Parse departmental FY headcount/time plan workbooks submitted as source truth."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

import xlrd
from openpyxl import load_workbook

from src.utils.excel_helpers import get_fy_months, normalize_cc_code

HEADCOUNT_SOURCE = "department_plan"


@dataclass
class PlanParseResult:
    path: str
    status: str
    cc_code: str = ""
    department_name: str = ""
    fiscal_year: int = 0
    sheet_name: str = ""
    department_no: str = ""
    rows: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    department_name_jp: str = ""
    department_name_vn: str = ""
    lookup_status: str = "not_applicable"
    verification_method: str = ""


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _cc_text(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value or "").strip()


def _normalized_text(value: Any) -> str:
    import unicodedata
    return unicodedata.normalize("NFKC", str(value or "")).strip()


def _resolve_lookup_identity(
    cc_code: str,
    displayed_name: str,
    lookup_rows: list[tuple[str, str, str]],
) -> tuple[str, str, str]:
    """Return lookup status and the JP/VN pair relevant to CC + displayed B5."""
    cc_matches = [row for row in lookup_rows if row[0] == cc_code]
    if not cc_matches:
        return "missing", "", ""
    displayed = _normalized_text(displayed_name)
    name_matches = [
        row for row in cc_matches
        if displayed in {_normalized_text(row[1]), _normalized_text(row[2])}
    ]
    matching_pairs = {(row[1], row[2]) for row in name_matches}
    if len(matching_pairs) == 1:
        name_jp, name_vn = next(iter(matching_pairs))
        return "matched", name_jp, name_vn
    if len(matching_pairs) > 1:
        return "ambiguous", "", ""
    cc_pairs = {(row[1], row[2]) for row in cc_matches}
    if len(cc_pairs) == 1:
        name_jp, name_vn = next(iter(cc_pairs))
        return "mismatch", name_jp, name_vn
    return "mismatch", "", ""


def parse_headcount_time_plan(path: str, fiscal_year: int) -> PlanParseResult:
    """Parse one departmental plan layout without writing the database."""
    result = PlanParseResult(path=os.path.abspath(path), status="error", fiscal_year=fiscal_year)
    match = re.match(r"\s*(\d+)\.", os.path.basename(path))
    result.department_no = match.group(1) if match else ""
    workbook = None
    try:
        if path.lower().endswith(".xlsx"):
            workbook = load_workbook(path, read_only=True, data_only=True, keep_links=False)
            sheet = workbook.worksheets[0]
            cell_value = lambda row, col: sheet.cell(row + 1, col + 1).value
            nrows, ncols, sheet_name = sheet.max_row, sheet.max_column, sheet.title
            lookup_rows = []
            for candidate in workbook.worksheets[1:]:
                for row in candidate.iter_rows(min_col=1, max_col=3, values_only=True):
                    code = normalize_cc_code(_cc_text(row[0])) or _cc_text(row[0])
                    if code:
                        lookup_rows.append((code, _cc_text(row[1]), _cc_text(row[2])))
        else:
            workbook = xlrd.open_workbook(path)
            sheet = workbook.sheet_by_index(0)
            cell_value = sheet.cell_value
            nrows, ncols, sheet_name = sheet.nrows, sheet.ncols, sheet.name
            lookup_rows = []
            for candidate in workbook.sheets()[1:]:
                for row_index in range(candidate.nrows):
                    code = normalize_cc_code(_cc_text(candidate.cell_value(row_index, 0))) or _cc_text(candidate.cell_value(row_index, 0))
                    if code:
                        name_jp = _cc_text(candidate.cell_value(row_index, 1)) if candidate.ncols > 1 else ""
                        name_vn = _cc_text(candidate.cell_value(row_index, 2)) if candidate.ncols > 2 else ""
                        lookup_rows.append((code, name_jp, name_vn))
    except Exception as exc:
        result.errors.append(f"Không mở được file: {type(exc).__name__}: {exc}")
        return result
    try:
        result.sheet_name = sheet_name
        if nrows < 28 or ncols < 14:
            result.errors.append(f"Cấu trúc không đủ: {nrows} dòng, {ncols} cột")
            return result
        raw_cc = _cc_text(cell_value(4, 0))
        result.cc_code = normalize_cc_code(raw_cc) or raw_cc
        result.department_name = _cc_text(cell_value(4, 1))
        lookup_status, name_jp, name_vn = _resolve_lookup_identity(
            result.cc_code, result.department_name, lookup_rows
        )
        result.lookup_status = lookup_status
        result.department_name_jp = name_jp
        result.department_name_vn = name_vn
        if lookup_status == "matched":
            result.verification_method = "workbook_bilingual_lookup"
        elif lookup_status == "mismatch":
            result.verification_method = "name_confirmation_required"
        elif lookup_status == "ambiguous":
            result.errors.append("Lookup nội bộ có nhiều cặp tên cùng khớp CC và B5")
        months = [int(_number(cell_value(7, col)) or 0) for col in range(2, 14)]
        if months != [int(period[-2:]) for period in get_fy_months(fiscal_year)]:
            result.errors.append(f"Thứ tự tháng không đúng FY{fiscal_year}: {months}")
            return result
        row_map = {
            "headcount_expat": 9, "headcount_staff": 10, "headcount_worker": 11,
            "headcount_local_total": 12, "headcount_total": 13,
            "fixed_hours_expat": 16, "fixed_hours_staff": 17, "fixed_hours_worker": 18,
            "fixed_hours_local_total": 19, "fixed_hours_total": 20,
            "overtime_hours_expat": 23, "overtime_hours_staff": 24, "overtime_hours_worker": 25,
            "overtime_hours_local_total": 26, "overtime_hours_total": 27,
        }
        values: dict[str, list[float]] = {}
        for metric, row_index in row_map.items():
            parsed = [_number(cell_value(row_index, col)) for col in range(2, 14)]
            if any(value is None for value in parsed):
                result.errors.append(f"Giá trị không phải số tại dòng {row_index + 1} ({metric})")
            else:
                values[metric] = [float(value or 0) for value in parsed]
        if result.errors:
            return result
        for index, period in enumerate(get_fy_months(fiscal_year)):
            checks = (
                (values["headcount_local_total"][index], values["headcount_staff"][index] + values["headcount_worker"][index], "tổng người Việt"),
                (values["headcount_total"][index], values["headcount_expat"][index] + values["headcount_local_total"][index], "tổng số người"),
                (values["fixed_hours_local_total"][index], values["fixed_hours_staff"][index] + values["fixed_hours_worker"][index], "tổng giờ cố định người Việt"),
                (values["fixed_hours_total"][index], values["fixed_hours_expat"][index] + values["fixed_hours_local_total"][index], "tổng giờ cố định"),
                (values["overtime_hours_local_total"][index], values["overtime_hours_staff"][index] + values["overtime_hours_worker"][index], "tổng tăng ca người Việt"),
                (values["overtime_hours_total"][index], values["overtime_hours_expat"][index] + values["overtime_hours_local_total"][index], "tổng tăng ca"),
            )
            for actual, expected, label in checks:
                if abs(actual - expected) > 0.01:
                    result.errors.append(f"{period}: {label} không khớp ({actual} != {expected})")
            result.rows.append({
                "period": period,
                "headcount_expat": values["headcount_expat"][index],
                "headcount_staff": values["headcount_staff"][index],
                "headcount_worker": values["headcount_worker"][index],
                "fixed_hours_expat": values["fixed_hours_expat"][index],
                "fixed_hours_staff": values["fixed_hours_staff"][index],
                "fixed_hours_worker": values["fixed_hours_worker"][index],
                "fixed_hours_local": values["fixed_hours_local_total"][index],
                "overtime_hours_expat": values["overtime_hours_expat"][index],
                "overtime_hours_staff": values["overtime_hours_staff"][index],
                "overtime_hours_worker": values["overtime_hours_worker"][index],
                "overtime_hours_local": values["overtime_hours_local_total"][index],
                "source_cells": "C:N; rows 10-28",
            })
        result.status = "valid" if not result.errors else "error"
        return result
    finally:
        if path.lower().endswith(".xlsx") and workbook is not None:
            workbook.close()
