from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from scripts.run_e2e import run_universal_pipeline
from src.engine.mp_saisan_complete_export import (
    PROVENANCE_PRIORITY,
    _append_secondary_skeleton_deduped,
    canonical_description,
    collect_existing_identities,
    count_provenance_rows,
    resolve_reference_path,
    row_identity_key,
)

SHEET = "内訳ﾘｽﾄ(4～3月)"


def _wb(path: Path, rows=None):
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET
    for idx, row in enumerate(rows or [], start=1):
        ws.cell(idx, 2).value = row.get("account")
        ws.cell(idx, 19).value = row.get("description")
        ws.cell(idx, 20).value = row.get("note")
        ws.cell(idx, 6).value = row.get("f")
        ws.cell(idx, 17).value = row.get("q")
    wb.save(path)
    wb.close()
    return path


def _csv(path: Path, descriptions):
    path.write_text(
        "classification,account,description,pattern_signature,month_F_sample,month_Q_sample\n"
        + "".join(
            f"REFERENCE_ASSISTED_FILL_CANDIDATE,5005026371,{desc},sig{i},,\n"
            for i, desc in enumerate(descriptions)
        ),
        encoding="utf-8",
    )
    return path


def test_priority_source_derived_wins_over_reference():
    assert PROVENANCE_PRIORITY["SOURCE_DERIVED"] < PROVENANCE_PRIORITY["REFERENCE_FILLED_FROM_PRIMARY"]


def test_primary_reference_wins_over_secondary_skeleton():
    assert PROVENANCE_PRIORITY["REFERENCE_FILLED_FROM_PRIMARY"] < PROVENANCE_PRIORITY["REFERENCE_ASSISTED_SECONDARY_SKELETON"]


def test_secondary_skeleton_writes_only_without_duplicate_identity(tmp_path):
    target = _wb(tmp_path / "target.xlsx", [{"account": "5005026371", "description": "A", "note": "REFERENCE_FILLED_FROM_PRIMARY"}])
    csvp = _csv(tmp_path / "candidates.csv", ["A", "B"])
    result = _append_secondary_skeleton_deduped(target, csvp, 1412000040)
    assert result["written"] == 1
    assert result["skipped_duplicate"] == 1
    counts = count_provenance_rows(target)
    assert counts["fixed_assets_skeleton_rows"] == 1


def test_electricity_water_aliases_do_not_duplicate():
    assert canonical_description("電気代") == canonical_description("electricity")
    assert canonical_description("水道代") == canonical_description("water")
    assert canonical_description("Điện") == canonical_description("electricity")
    assert canonical_description("Nước") == canonical_description("water")


def test_complete_mode_default_off(tmp_path):
    ok, message = run_universal_pipeline(2027, str(_wb(tmp_path / "target.xlsx")), str(tmp_path), target_cc=1412000040)
    assert ok is False
    assert "System Cost row" in message or "template" in message


def test_complete_mode_uses_reference_map_for_1412000040(tmp_path):
    ref = _wb(tmp_path / "ref.xlsx")
    m = tmp_path / "map.csv"
    m.write_text("target_cc,reference_role,reference_path\n1412000040,primary_reference,ref.xlsx\n", encoding="utf-8")
    assert resolve_reference_path(1412000040, reference_map_path=m).name == ref.name


def test_other_cc_without_reference_fails_clearly(tmp_path):
    with pytest.raises(ValueError, match="requires a primary reference"):
        resolve_reference_path(999, reference_map_path=tmp_path / "missing.csv")


def test_provenance_counts_are_returned(tmp_path):
    target = _wb(
        tmp_path / "target.xlsx",
        [
            {"account": "1", "description": "source", "note": ""},
            {"account": "2", "description": "primary", "note": "REFERENCE_FILLED_FROM_PRIMARY"},
            {"account": "3", "description": "secondary", "note": "REFERENCE_ASSISTED_SECONDARY_SKELETON"},
        ],
    )
    assert count_provenance_rows(target) == {"source_rows": 1, "primary_reference_rows": 1, "fixed_assets_skeleton_rows": 1}


def test_no_overwrite_rows_200_212(tmp_path):
    target = _wb(tmp_path / "target.xlsx")
    wb = load_workbook(target)
    ws = wb[SHEET]
    ws.cell(200, 2).value = "KEEP"
    ws.cell(200, 19).value = "source-layer"
    wb.save(target)
    wb.close()
    csvp = _csv(tmp_path / "candidates.csv", ["new"])
    result = _append_secondary_skeleton_deduped(target, csvp, 1412000040)
    assert result["written"] == 1
    wb = load_workbook(target)
    ws = wb[SHEET]
    assert ws.cell(200, 2).value == "KEEP"
    assert ws.cell(213, 2).value == "5005026371"
    wb.close()
