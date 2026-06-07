"""Read-only System Cost file-order preview for MP2027."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import xlrd

MONTH_RANGES = ((0,3),(3,9),(9,12))
SUMMARY_SHEET = '部門別サマリー(VND)'

@dataclass(frozen=True)
class SystemCostPreviewItem:
    item_id: str
    display_name: str
    source_files: tuple[str, ...]
    source_evidence: tuple[str, ...]
    month_values: tuple[Any, ...]
    planned_row: int
    formula_policy: str
    confidence: str
    note: str

@dataclass(frozen=True)
class SystemCostFileOrderPreview:
    cost_center: str
    planned_start_row: int
    planned_end_row: int
    blank_row_after: int
    items: tuple[SystemCostPreviewItem, ...]

def _norm_cc(value: Any) -> str:
    text = str(value or '').strip()
    if text.endswith('.0'):
        text = text[:-2]
    return text

def _summary_total_for_cc(path: str | Path, cost_center: str) -> tuple[float | None, str]:
    book = xlrd.open_workbook(str(path))
    sh = book.sheet_by_name(SUMMARY_SHEET)
    for r in range(sh.nrows):
        vals = [sh.cell_value(r, c) for c in range(sh.ncols)]
        if len(vals) > 11 and _norm_cc(vals[1]) == str(cost_center):
            total = vals[11]
            try:
                return float(total), f"{Path(path).name}|{SUMMARY_SHEET}|row={r+1}|cc={_norm_cc(vals[1])}|total_vnd={total}"
            except Exception:
                return None, f"{Path(path).name}|{SUMMARY_SHEET}|row={r+1}|cc={_norm_cc(vals[1])}|total_vnd={total}"
    return None, f"{Path(path).name}|{SUMMARY_SHEET}|cc_not_found"

def preview_system_cost_file_order(system_source_paths, cost_center: str | int = '1412000040', start_row: int = 211):
    paths = [Path(p) for p in system_source_paths]
    values = [None] * 12
    evidence = []
    for path, (start, end) in zip(paths, MONTH_RANGES):
        total, ev = _summary_total_for_cc(path, str(cost_center))
        evidence.append(ev)
        for idx in range(start, end):
            values[idx] = total
    confidence = 'HIGH' if all(v is not None for v in values) and len(paths) == 3 else 'UNKNOWN'
    item = SystemCostPreviewItem(
        item_id='system_cost_combined',
        display_name='System Cost / システム課金',
        source_files=tuple(str(p) for p in paths),
        source_evidence=tuple(evidence),
        month_values=tuple(values),
        planned_row=start_row,
        formula_policy='COPY_SUMMARY_VND_TOTAL_BY_PERIOD' if confidence == 'HIGH' else 'UNKNOWN',
        confidence=confidence,
        note='FILE_ORDER_SINGLE_ROW from three System Cost period workbooks',
    )
    return SystemCostFileOrderPreview(str(cost_center), start_row, start_row, start_row + 1, (item,))
