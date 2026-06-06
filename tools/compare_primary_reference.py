"""Compare generated MP2027 output against the primary trusted reference."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook

DETAIL_SHEET = "内訳ﾘｽﾄ(4～3月)"
FIXED_ROW_RULES = {
    53: "Bus JP",
    54: "Bus VN",
    58: "Recruitment health",
    66: "Company trip",
    97: "Staff notebook",
    98: "Worker notebook",
    137: "NNN paperwork",
}
IDENTITY_ROW_CANDIDATES = {
    38: "Fixed Assets depreciation",
    42: "Fixed Assets interest",
    75: "System Cost",
}
COMPARE_COLUMNS = ("B", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S")
MEDIUM_COLUMNS = set("FGHIJKLMNOPQ")
IDENTITY_TOKENS = {
    "system": ("system cost", "mail", "vpn", "r3", "mes", "plm", "vps", "システム"),
    "depreciation": ("減価償却", "khấu hao", "khau hao", "depreciation"),
    "interest": ("金利", "lãi", "lai", "interest"),
    "building": ("建物", "nhà", "nha", "building"),
    "equipment": ("設備", "thiết bị", "thiet bi", "equipment"),
}


@dataclass
class CellDiff:
    row: int
    column: str
    generated: Any
    reference: Any
    match: bool
    severity: str
    note: str
    compare_mode: str = "fixed_row"
    reference_row: int | None = None


@dataclass
class IdentityAlignment:
    generated_row: int
    generated_account: Any
    generated_description: Any
    reference_matched_row: int | None
    reference_account: Any
    reference_description: Any
    match_method: str
    confidence: str
    same_business_item: bool
    note: str


def normalize_text(text: Any) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text).strip().lower())


def _cell_value(ws, row: int, column: str):
    return ws[f"{column}{row}"].value


def _severity(column: str, generated, reference, match: bool, mode: str = "fixed_row") -> tuple[str, str]:
    if match:
        return "None", ""
    if mode == "identity":
        if column in MEDIUM_COLUMNS:
            return "Medium", "Aligned identity row F:Q formula/value differs"
        return "Medium", "Aligned identity row differs"
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


def _token_hits(text: Any) -> set[str]:
    normalized = normalize_text(text)
    return {name for name, tokens in IDENTITY_TOKENS.items() if any(token in normalized for token in tokens)}


def _find_identity_match(gen_ws, ref_ws, generated_row: int) -> IdentityAlignment:
    gen_account = _cell_value(gen_ws, generated_row, "B")
    gen_desc = _cell_value(gen_ws, generated_row, "S")
    gen_tokens = _token_hits(gen_desc)
    best = None
    max_row = ref_ws.max_row or 1
    for row in range(1, max_row + 1):
        ref_account = _cell_value(ref_ws, row, "B")
        ref_desc = _cell_value(ref_ws, row, "S")
        ref_tokens = _token_hits(ref_desc)
        same_account = gen_account not in (None, "") and gen_account == ref_account
        token_overlap = bool(gen_tokens & ref_tokens)
        if same_account and normalize_text(gen_desc) == normalize_text(ref_desc):
            return IdentityAlignment(generated_row, gen_account, gen_desc, row, ref_account, ref_desc, "same_account", "High", True, "same account and description")
        if same_account:
            candidate = (3, row, ref_account, ref_desc, "same_account", "High", True, "same account")
        elif token_overlap:
            candidate = (2, row, ref_account, ref_desc, "token_overlap", "Medium", True, "strong description token overlap")
        else:
            continue
        if best is None or candidate[0] > best[0]:
            best = candidate
    if best:
        _, row, ref_account, ref_desc, method, confidence, same, note = best
        return IdentityAlignment(generated_row, gen_account, gen_desc, row, ref_account, ref_desc, method, confidence, same, note)
    return IdentityAlignment(generated_row, gen_account, gen_desc, None, None, None, "not_found", "Low", False, "no same account or strong token overlap found")


def _compare_row(gen_ws, ref_ws, generated_row: int, reference_row: int, mode: str) -> tuple[list[CellDiff], dict[str, Any]]:
    diffs = []
    row_diff_count = 0
    for column in COMPARE_COLUMNS:
        generated = _cell_value(gen_ws, generated_row, column)
        reference = _cell_value(ref_ws, reference_row, column)
        match = generated == reference
        severity, note = _severity(column, generated, reference, match, mode)
        if not match:
            row_diff_count += 1
        diffs.append(CellDiff(generated_row, column, generated, reference, match, severity, note, mode, reference_row))
    summary = {
        "row": generated_row,
        "reference_row": reference_row,
        "compare_mode": mode,
        "description_generated": _cell_value(gen_ws, generated_row, "S"),
        "description_reference": _cell_value(ref_ws, reference_row, "S"),
        "differences_count": row_diff_count,
        "status": "OK" if row_diff_count == 0 else "DIFF",
    }
    return diffs, summary


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
        alignments: list[IdentityAlignment] = []
        fixed_row_differences = 0
        identity_differences = 0

        for row in FIXED_ROW_RULES:
            row_diffs, summary_row = _compare_row(gen_ws, ref_ws, row, row, "fixed_row")
            fixed_row_differences += sum(1 for diff in row_diffs if not diff.match)
            diffs.extend(row_diffs)
            row_summary.append(summary_row)

        for row in IDENTITY_ROW_CANDIDATES:
            alignment = _find_identity_match(gen_ws, ref_ws, row)
            alignments.append(alignment)
            if alignment.reference_matched_row is not None:
                row_diffs, summary_row = _compare_row(gen_ws, ref_ws, row, alignment.reference_matched_row, "identity")
                identity_differences += sum(1 for diff in row_diffs if not diff.match)
                diffs.extend(row_diffs)
                row_summary.append(summary_row)

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
            "fixed_rows_compared": len(FIXED_ROW_RULES),
            "identity_rows_checked": len(IDENTITY_ROW_CANDIDATES),
            "identity_rows_matched": sum(1 for a in alignments if a.reference_matched_row is not None),
            "identity_rows_not_found": sum(1 for a in alignments if a.reference_matched_row is None),
            "fixed_row_differences": fixed_row_differences,
            "identity_differences": identity_differences,
        }
        xlsx_path = out_dir / "MP2027_primary_reference_compare.xlsx"
        json_path = out_dir / "MP2027_primary_reference_compare.json"
        _write_excel_report(xlsx_path, summary, diffs, row_summary, alignments)
        json_payload = {
            "summary": summary,
            "important_row_diff": [asdict(diff) for diff in diffs],
            "row_summary": row_summary,
            "identity_row_alignment": [asdict(alignment) for alignment in alignments],
        }
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return {"summary": summary, "xlsx_path": str(xlsx_path), "json_path": str(json_path)}
    finally:
        gen_wb.close()
        ref_wb.close()


def _write_excel_report(path: Path, summary: dict[str, Any], diffs: list[CellDiff], row_summary: list[dict[str, Any]], alignments: list[IdentityAlignment]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    for key, value in summary.items():
        ws.append([key, json.dumps(value, ensure_ascii=False) if isinstance(value, list) else value])
    ws = wb.create_sheet("Important_Row_Diff")
    ws.append(["Row", "Reference row", "Mode", "Column", "Generated value/formula", "Reference value/formula", "Match?", "Severity", "Note"])
    for diff in diffs:
        ws.append([diff.row, diff.reference_row, diff.compare_mode, diff.column, diff.generated, diff.reference, diff.match, diff.severity, diff.note])
    ws = wb.create_sheet("Row_Summary")
    ws.append(["Row", "Reference row", "Mode", "Description generated", "Description reference", "Differences count", "Status"])
    for row in row_summary:
        ws.append([row["row"], row["reference_row"], row["compare_mode"], row["description_generated"], row["description_reference"], row["differences_count"], row["status"]])
    ws = wb.create_sheet("Identity_Row_Alignment")
    ws.append(["Generated row", "Generated account", "Generated description", "Reference matched row", "Reference account", "Reference description", "Match method", "Confidence", "Same business item?", "Note"])
    for alignment in alignments:
        ws.append([alignment.generated_row, alignment.generated_account, alignment.generated_description, alignment.reference_matched_row, alignment.reference_account, alignment.reference_description, alignment.match_method, alignment.confidence, alignment.same_business_item, alignment.note])
    ws = wb.create_sheet("Guidance")
    for item in [
        "Primary reference is expected output baseline.",
        "Fixed-row differences apply only to rows locked by requirement/user/FORM.",
        "Identity rows are aligned by account or strong description tokens before value comparison.",
        "Differences are not automatically bugs; user must confirm business meaning.",
        "Secondary references are edge-case only.",
    ]:
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
