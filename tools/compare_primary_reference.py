"""Compare a generated MP2027 workbook against the primary trusted reference.

This tool intentionally compares only a narrow set of important rows/cells in
`内訳ﾘｽﾄ(4～3月)`. Differences are reported for review; they are not treated as
proof of a business bug without user confirmation.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook

DETAIL_SHEET = "内訳ﾘｽﾄ(4～3月)"
IMPORTANT_ROWS = (38, 42, 53, 54, 57, 58, 66, 75, 97, 98, 137)
COMPARE_COLUMNS = ("B", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S")
HIGH_COLUMNS = {"B", "R", "S"}
MEDIUM_COLUMNS = {"F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q"}


@dataclass
class CellDiff:
    row: int
    column: str
    generated: Any
    reference: Any
    match: bool
    severity: str
    note: str


def _cell_value(ws, row: int, column: str):
    return ws[f"{column}{row}"].value


def _severity(column: str, generated, reference, match: bool) -> tuple[str, str]:
    if match:
        return "None", ""
    if column == "B":
        return "High", "B account differs"
    if column == "R":
        return "High", "R total formula/value differs or is missing"
    if column == "S":
        if generated in (None, ""):
            return "High", "S description is unexpectedly blank"
        return "High", "S description differs"
    if column in MEDIUM_COLUMNS:
        return "Medium", "F:Q formula/value differs"
    return "Low", "Formatting is not compared in this first tool"


def compare_workbooks(generated_path: Path, reference_path: Path, out_dir: Path) -> dict[str, Any]:
    if not generated_path.is_file():
        raise FileNotFoundError(f"Generated workbook not found: {generated_path}")
    if not reference_path.is_file():
        raise FileNotFoundError(f"Reference workbook not found: {reference_path}")

    out_dir.mkdir(parents=True, exist_ok=True)
    gen_wb = load_workbook(generated_path, data_only=False)
    ref_wb = load_workbook(reference_path, data_only=False)
    try:
        missing_sheets = []
        if DETAIL_SHEET not in gen_wb.sheetnames:
            missing_sheets.append(f"generated:{DETAIL_SHEET}")
        if DETAIL_SHEET not in ref_wb.sheetnames:
            missing_sheets.append(f"reference:{DETAIL_SHEET}")
        if missing_sheets:
            raise ValueError("Required sheet missing: " + ", ".join(missing_sheets))

        gen_ws = gen_wb[DETAIL_SHEET]
        ref_ws = ref_wb[DETAIL_SHEET]
        diffs: list[CellDiff] = []
        row_summary: list[dict[str, Any]] = []

        for row in IMPORTANT_ROWS:
            row_diff_count = 0
            for column in COMPARE_COLUMNS:
                generated = _cell_value(gen_ws, row, column)
                reference = _cell_value(ref_ws, row, column)
                match = generated == reference
                severity, note = _severity(column, generated, reference, match)
                if not match:
                    row_diff_count += 1
                diffs.append(CellDiff(row, column, generated, reference, match, severity, note))
            row_summary.append(
                {
                    "row": row,
                    "description_generated": _cell_value(gen_ws, row, "S"),
                    "description_reference": _cell_value(ref_ws, row, "S"),
                    "differences_count": row_diff_count,
                    "status": "OK" if row_diff_count == 0 else "DIFF",
                }
            )

        total_cells = len(diffs)
        differences = sum(1 for diff in diffs if not diff.match)
        summary = {
            "generated_path": str(generated_path),
            "reference_path": str(reference_path),
            "total_cells_compared": total_cells,
            "exact_matches": total_cells - differences,
            "differences": differences,
            "missing_sheets": [],
            "missing_rows_or_cells": [],
        }

        xlsx_path = out_dir / "MP2027_primary_reference_compare.xlsx"
        json_path = out_dir / "MP2027_primary_reference_compare.json"
        _write_excel_report(xlsx_path, summary, diffs, row_summary)
        json_payload = {
            "summary": summary,
            "important_row_diff": [asdict(diff) for diff in diffs],
            "row_summary": row_summary,
        }
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return {"summary": summary, "xlsx_path": str(xlsx_path), "json_path": str(json_path)}
    finally:
        gen_wb.close()
        ref_wb.close()


def _write_excel_report(path: Path, summary: dict[str, Any], diffs: list[CellDiff], row_summary: list[dict[str, Any]]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    for key, value in summary.items():
        ws.append([key, json.dumps(value, ensure_ascii=False) if isinstance(value, list) else value])

    ws = wb.create_sheet("Important_Row_Diff")
    ws.append(["Row", "Column", "Generated value/formula", "Reference value/formula", "Match?", "Severity", "Note"])
    for diff in diffs:
        ws.append([diff.row, diff.column, diff.generated, diff.reference, diff.match, diff.severity, diff.note])

    ws = wb.create_sheet("Row_Summary")
    ws.append(["Row", "Description generated", "Description reference", "Differences count", "Status"])
    for row in row_summary:
        ws.append([
            row["row"],
            row["description_generated"],
            row["description_reference"],
            row["differences_count"],
            row["status"],
        ])

    ws = wb.create_sheet("Guidance")
    guidance = [
        "Primary reference is expected output baseline.",
        "Differences are not automatically bugs; user must confirm business meaning.",
        "Secondary references are edge-case only.",
        "Formatting is not compared in this first tool.",
    ]
    for item in guidance:
        ws.append([item])

    wb.save(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare MP2027 generated output with primary trusted reference.")
    parser.add_argument("--generated", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    result = compare_workbooks(args.generated, args.reference, args.out_dir)
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    print(f"Excel report: {result['xlsx_path']}")
    print(f"JSON report: {result['json_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
