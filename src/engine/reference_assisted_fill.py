"""Reference-assisted workbook fill helpers.

These helpers deliberately label copied rows as reference-assisted. They do not
claim source-derived provenance.
"""
from __future__ import annotations

from copy import copy
import csv
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

SHEET_NAME = "内訳ﾘｽﾄ(4～3月)"
PROVENANCE_LABEL = "REFERENCE_FILLED_FROM_PRIMARY"
FALSE_GAP_CLASS = "ALREADY_GENERATED_FALSE_GAP"
BUSINESS_COLUMNS = [2, 5, *range(6, 18), 19, 20]


def _norm(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def _business_row_present(ws, row: int) -> bool:
    return any(_norm(ws.cell(row, col).value) for col in (2, 19, *range(6, 18)))


def count_business_rows(workbook_path: str | Path) -> int:
    """Count non-empty business rows on the MP detail sheet."""
    wb = load_workbook(workbook_path, data_only=False)
    try:
        if SHEET_NAME not in wb.sheetnames:
            return 0
        ws = wb[SHEET_NAME]
        return sum(1 for row in range(1, ws.max_row + 1) if _business_row_present(ws, row))
    finally:
        wb.close()


def _load_invariant_rows(invariant_csv_path: str | Path) -> list[dict[str, str]]:
    with open(invariant_csv_path, newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def identify_reference_assisted_rows(
    primary_path: str | Path,
    generated_path: str | Path,
    invariant_csv_path: str | Path,
) -> list[dict[str, Any]]:
    """Return primary rows eligible for reference-assisted copying.

    Skips false gaps and rows with an invariant generated match. The generated
    workbook parameter is retained for API clarity and future safety checks.
    """
    del generated_path
    primary_wb = load_workbook(primary_path, data_only=False)
    try:
        ws = primary_wb[SHEET_NAME]
        selected: list[dict[str, Any]] = []
        for row in _load_invariant_rows(invariant_csv_path):
            if row.get("new_classification") == FALSE_GAP_CLASS:
                continue
            if _norm(row.get("generated_match_row")):
                continue
            primary_row = int(row["primary_row"])
            if not _business_row_present(ws, primary_row):
                continue
            selected.append(
                {
                    "primary_row": primary_row,
                    "classification": row.get("new_classification", ""),
                    "account_code": _norm(ws.cell(primary_row, 2).value),
                    "description": _norm(ws.cell(primary_row, 19).value),
                }
            )
        return selected
    finally:
        primary_wb.close()


def _next_safe_row(ws, start_row: int) -> int:
    row = max(start_row, 213)
    while _business_row_present(ws, row):
        row += 1
    return row


def _copy_business_row(primary_ws, target_ws, primary_row: int, target_row: int) -> None:
    for col in BUSINESS_COLUMNS:
        source = primary_ws.cell(primary_row, col)
        dest = target_ws.cell(target_row, col)
        dest.value = source.value
        if source.has_style:
            dest._style = copy(source._style)
        if source.number_format:
            dest.number_format = source.number_format
    note_cell = target_ws.cell(target_row, 20)
    label = f"{PROVENANCE_LABEL}; primary_row={primary_row}; not source-derived"
    if _norm(note_cell.value):
        note_cell.value = f"{note_cell.value} | {label}"
    else:
        note_cell.value = label


def apply_reference_assisted_fill_to_workbook(
    workbook_path: str | Path,
    primary_path: str | Path,
    invariant_csv_path: str | Path,
    start_row: int = 213,
) -> dict[str, int]:
    """Append eligible primary rows to workbook with provenance labels."""
    selected = identify_reference_assisted_rows(primary_path, workbook_path, invariant_csv_path)
    target_wb = load_workbook(workbook_path)
    primary_wb = load_workbook(primary_path, data_only=False)
    try:
        target_ws = target_wb[SHEET_NAME]
        primary_ws = primary_wb[SHEET_NAME]
        target_row = _next_safe_row(target_ws, start_row)
        written = 0
        for item in selected:
            if target_row < 213:
                target_row = 213
            _copy_business_row(primary_ws, target_ws, item["primary_row"], target_row)
            written += 1
            target_row += 1
        target_wb.save(workbook_path)
        return {"selected": len(selected), "written": written, "start_row": start_row}
    finally:
        primary_wb.close()
        target_wb.close()
