"""Xem trước chỉ đọc thứ tự tệp chi phí hệ thống cho MP2027."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import xlrd
from src.engine.cost_center_context import require_cost_center
from src.utils.fiscal_periods import fiscal_periods, map_system_source_periods

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

def preview_system_cost_file_order(
    system_source_paths,
    *,
    fiscal_year: int,
    cost_center: str | int | None = None,
    start_row: int = 211,
):
    cc_key = require_cost_center(cost_center, context="System Cost preview")
    assignments = map_system_source_periods(
        system_source_paths,
        fiscal_year,
        require_complete=False,
    )
    period_indexes = {
        period: index for index, period in enumerate(fiscal_periods(fiscal_year))
    }
    values = [None] * 12
    evidence = []
    for assignment in assignments:
        path = Path(assignment.path)
        total, ev = _summary_total_for_cc(path, cc_key)
        evidence.append(ev)
        for period in assignment.periods:
            values[period_indexes[period]] = total
    confidence = 'HIGH' if all(value is not None for value in values) else 'UNKNOWN'
    item = SystemCostPreviewItem(
        item_id='system_cost_combined',
        display_name='System Cost / システム課金',
        source_files=tuple(assignment.path for assignment in assignments),
        source_evidence=tuple(evidence),
        month_values=tuple(values),
        planned_row=start_row,
        formula_policy='COPY_SUMMARY_VND_TOTAL_BY_PERIOD' if confidence == 'HIGH' else 'UNKNOWN',
        confidence=confidence,
        note='Ánh xạ kỳ từ tên từng file System Cost; không phụ thuộc thứ tự file.',
    )
    return SystemCostFileOrderPreview(cc_key, start_row, start_row, start_row + 1, (item,))
