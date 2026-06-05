import json
from pathlib import Path

import openpyxl

from tools.compare_primary_reference import compare_workbooks


def _make_workbook(path: Path, overrides=None):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "内訳ﾘｽﾄ(4～3月)"
    for row in (53, 54, 58):
        ws[f"B{row}"] = 5000000000 + row
        for col in range(6, 18):
            ws.cell(row=row, column=col).value = f"=SUM({row},{col})"
        ws[f"R{row}"] = f"=SUM(F{row}:Q{row})"
        ws[f"S{row}"] = f"description {row}"
    for coord, value in (overrides or {}).items():
        ws[coord] = value
    wb.save(path)
    wb.close()


def test_compare_primary_reference_identical_workbooks(tmp_path):
    reference = tmp_path / "reference.xlsx"
    generated = tmp_path / "generated.xlsx"
    out_dir = tmp_path / "reports"
    _make_workbook(reference)
    _make_workbook(generated)

    result = compare_workbooks(generated, reference, out_dir)

    assert result["summary"]["differences"] == 0
    assert Path(result["xlsx_path"]).is_file()
    assert Path(result["json_path"]).is_file()
    payload = json.loads(Path(result["json_path"]).read_text(encoding="utf-8"))
    assert payload["summary"]["total_cells_compared"] > 0


def test_compare_primary_reference_detects_b_account_high_severity(tmp_path):
    reference = tmp_path / "reference.xlsx"
    generated = tmp_path / "generated.xlsx"
    out_dir = tmp_path / "reports"
    _make_workbook(reference)
    _make_workbook(generated, {"B53": 9999999999})

    result = compare_workbooks(generated, reference, out_dir)

    payload = json.loads(Path(result["json_path"]).read_text(encoding="utf-8"))
    assert result["summary"]["differences"] > 0
    b53 = [
        row for row in payload["important_row_diff"]
        if row["row"] == 53 and row["column"] == "B"
    ][0]
    assert b53["match"] is False
    assert b53["severity"] == "High"


def test_compare_primary_reference_detects_fq_medium_severity(tmp_path):
    reference = tmp_path / "reference.xlsx"
    generated = tmp_path / "generated.xlsx"
    out_dir = tmp_path / "reports"
    _make_workbook(reference)
    _make_workbook(generated, {"F58": "=999"})

    result = compare_workbooks(generated, reference, out_dir)

    payload = json.loads(Path(result["json_path"]).read_text(encoding="utf-8"))
    f58 = [
        row for row in payload["important_row_diff"]
        if row["row"] == 58 and row["column"] == "F"
    ][0]
    assert result["summary"]["differences"] > 0
    assert f58["match"] is False
    assert f58["severity"] == "Medium"
