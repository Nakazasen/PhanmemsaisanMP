from pathlib import Path

import openpyxl

from src.engine.source_order_output import (
    CANONICAL_SOURCE_FILE_ORDER,
    OutputRow,
    place_rows_by_source_file_order,
    source_order_index,
)
from src.utils.source_manifest import (
    detect_source_files,
    inventory_source_files,
    merge_manifest_with_detected,
    read_source_manifest_inventory_fast,
)


def test_canonical_source_order_matches_user_requirement():
    assert len(CANONICAL_SOURCE_FILE_ORDER) == 7
    assert CANONICAL_SOURCE_FILE_ORDER[0].endswith("MPFY2027.xlsx")
    assert "Fixed_Assets_Information_2025.11 - Nov.xlsx" in CANONICAL_SOURCE_FILE_ORDER[1]
    assert "Simulation)_FY2027_Apr.2026 ~ June.2026.xls" in CANONICAL_SOURCE_FILE_ORDER[2]
    assert "FY2027 MP" in CANONICAL_SOURCE_FILE_ORDER[3]
    assert CANONICAL_SOURCE_FILE_ORDER[4].startswith("Sinh")
    assert "(2025.12.29).xlsx" in CANONICAL_SOURCE_FILE_ORDER[5]
    assert "NNN FY2027.xlsx" in CANONICAL_SOURCE_FILE_ORDER[6]


def test_source_order_index_unknown_files_go_last():
    assert source_order_index(CANONICAL_SOURCE_FILE_ORDER[0]) == 0
    assert source_order_index(CANONICAL_SOURCE_FILE_ORDER[6]) == 6
    assert source_order_index("unknown.xlsx") > 6


def test_place_rows_by_source_order_inserts_one_blank_between_file_blocks():
    rows = [
        OutputRow(CANONICAL_SOURCE_FILE_ORDER[4], {"item": "birthday-1"}),
        OutputRow(CANONICAL_SOURCE_FILE_ORDER[0], {"item": "facility-1"}),
        OutputRow(CANONICAL_SOURCE_FILE_ORDER[0], {"item": "facility-2"}),
        OutputRow(CANONICAL_SOURCE_FILE_ORDER[6], {"item": "nnn-1"}),
    ]

    placed = place_rows_by_source_file_order(rows, start_row=200)

    assert [(r.output_row, r.source_file, r.values.get("item"), r.is_blank_separator) for r in placed] == [
        (200, CANONICAL_SOURCE_FILE_ORDER[0], "facility-1", False),
        (201, CANONICAL_SOURCE_FILE_ORDER[0], "facility-2", False),
        (202, CANONICAL_SOURCE_FILE_ORDER[0], None, True),
        (203, CANONICAL_SOURCE_FILE_ORDER[4], "birthday-1", False),
        (204, CANONICAL_SOURCE_FILE_ORDER[4], None, True),
        (205, CANONICAL_SOURCE_FILE_ORDER[6], "nnn-1", False),
    ]


def test_no_fixed_form_rows_are_required_by_policy():
    rows = [
        OutputRow(CANONICAL_SOURCE_FILE_ORDER[1], {"amount": 1}),
        OutputRow(CANONICAL_SOURCE_FILE_ORDER[6], {"amount": 2}),
    ]

    placed = place_rows_by_source_file_order(rows, start_row=1)

    assert [r.output_row for r in placed if not r.is_blank_separator] == [1, 3]
    assert all(r.output_row not in [38, 42, 58, 59, 97, 98, 137] for r in placed)


def _write_facility_source(path: Path) -> None:
    workbook = openpyxl.Workbook()
    workbook.active.title = "減価償却費（Depreciation）"
    workbook.create_sheet("固定資産金利（Interest）")
    workbook.create_sheet("水道光熱費（Electric & Water）")
    workbook.save(path)
    workbook.close()


def test_source_inventory_never_hides_unknown_workbooks(tmp_path):
    _write_facility_source(tmp_path / "renamed-without-keywords.xlsx")
    workbook = openpyxl.Workbook()
    workbook.active.title = "Freight FY2026"
    workbook.save(tmp_path / "new-cost-layout.xlsx")
    workbook.close()
    (tmp_path / "FORM.xlsx").write_bytes(b"system file")
    (tmp_path / "~$editing.xlsx").write_bytes(b"temporary file")

    inventory = inventory_source_files(str(tmp_path))
    detected = detect_source_files(str(tmp_path))

    assert [path.name for path in inventory] == [
        "new-cost-layout.xlsx",
        "renamed-without-keywords.xlsx",
    ]
    assert {entry["filename"] for entry in detected} == {
        "new-cost-layout.xlsx",
        "renamed-without-keywords.xlsx",
    }
    by_name = {entry["filename"]: entry for entry in detected}
    assert by_name["renamed-without-keywords.xlsx"]["category"] == "facility"
    assert by_name["renamed-without-keywords.xlsx"]["status"] == "recognized"
    assert by_name["renamed-without-keywords.xlsx"]["detection_method"] == "structure"
    assert by_name["new-cost-layout.xlsx"]["category"] == ""
    assert by_name["new-cost-layout.xlsx"]["status"] == "needs_review"


def test_manual_manifest_decision_survives_rename_but_not_structure_change(tmp_path):
    path = tmp_path / "totally-renamed.xlsx"
    _write_facility_source(path)
    detected = detect_source_files(str(tmp_path))[0]
    saved = [
        {
            **detected,
            "category": "facility",
            "status": "recognized",
            "detection_method": "manual",
            "reason": "Đã chọn thủ công",
        }
    ]

    compatible = merge_manifest_with_detected(str(tmp_path), saved)
    assert compatible[0]["category"] == "facility"
    assert compatible[0]["status"] == "recognized"
    assert compatible[0]["detection_method"] == "manual"

    workbook = openpyxl.load_workbook(path)
    workbook.remove(workbook["固定資産金利（Interest）"])
    workbook.save(path)
    workbook.close()

    changed = merge_manifest_with_detected(str(tmp_path), saved)
    assert changed[0]["category"] == ""
    assert changed[0]["status"] == "needs_review"
    assert "thay đổi" in changed[0]["reason"].lower()


def test_manual_decision_survives_raw_multi_match_structure(monkeypatch, tmp_path):
    from src.utils import source_manifest

    path = tmp_path / "ambiguous.xlsx"
    path.write_bytes(b"fixture")
    current = {
        "order": "1",
        "category": "",
        "filename": path.name,
        "enabled": "0",
        "description": "Cần xác nhận loại nguồn",
        "status": "needs_review",
        "detection_method": "structure",
        "signature": "new-signature",
        "reason": "Cấu trúc khớp nhiều loại.",
        "_matches": "facility|ga",
        "_path": str(path.resolve()),
    }
    monkeypatch.setattr(source_manifest, "detect_source_files", lambda _source_dir: [current])

    saved = [{
        **current,
        "category": "facility",
        "enabled": "1",
        "status": "recognized",
        "detection_method": "manual",
        "reason": "Đã chọn thủ công",
    }]

    merged = merge_manifest_with_detected(str(tmp_path), saved)

    assert merged[0]["category"] == "facility"
    assert merged[0]["status"] == "recognized"
    assert merged[0]["detection_method"] == "manual"


def test_fast_manifest_inventory_never_opens_or_classifies_workbooks(monkeypatch, tmp_path):
    from src.utils import source_manifest

    (tmp_path / "new-source.xlsx").write_bytes(b"metadata-only fixture")

    def fail_if_deep_scan_runs(_source_dir):
        raise AssertionError("fast inventory must not classify workbook contents")

    monkeypatch.setattr(source_manifest, "detect_source_files", fail_if_deep_scan_runs)

    rows = read_source_manifest_inventory_fast(str(tmp_path))

    assert len(rows) == 1
    assert rows[0]["filename"] == "new-source.xlsx"
    assert rows[0]["category"] == ""
    assert rows[0]["enabled"] == "0"
    assert rows[0]["status"] == "needs_review"
    assert rows[0]["detection_method"] == "inventory"
