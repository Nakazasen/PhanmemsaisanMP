from pathlib import Path

from openpyxl import Workbook, load_workbook

from src.engine.complete_v1_source_order_writer import apply_complete_v1_source_order_to_workbook
from src.engine.source_order_output import CANONICAL_SOURCE_FILE_ORDER

SHEET = "蜀・ｨｳ・假ｽｽ・・4・・譛・"


def _workbook(path: Path) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET
    for row, account, description in [
        (36, 5006016260, "facility building depreciation"),
        (38, 5006016244, "fixed asset depreciation"),
        (42, 9114120007, "fixed asset interest"),
        (59, 5004086291, "birthday"),
        (137, 5005246286, "NNN paperwork"),
        (175, None, "admin toilet paper"),
        (179, None, "system cost"),
    ]:
        ws.cell(row, 2).value = account
        ws.cell(row, 6).value = row
        ws.cell(row, 19).value = description
        ws.cell(row, 20).value = "SOURCE_DERIVED"
    wb.save(path)
    wb.close()
    return path


def test_complete_v1_writer_rewrites_legacy_rows_to_source_order_blocks(tmp_path):
    workbook = _workbook(tmp_path / "out.xlsx")

    result = apply_complete_v1_source_order_to_workbook(workbook, start_row=168, clear_until_row=190)

    assert result["rows_written"] == 7
    assert result["blank_rows_written"] == 5

    wb = load_workbook(workbook)
    try:
        ws = wb[SHEET]
        assert ws.cell(168, 19).value == "facility building depreciation"
        assert ws.cell(169, 19).value is None
        assert ws.cell(170, 19).value == "fixed asset depreciation"
        assert ws.cell(171, 19).value == "fixed asset interest"
        assert ws.cell(172, 19).value is None
        assert ws.cell(173, 19).value == "system cost"
        assert ws.cell(175, 19).value == "admin toilet paper"
        assert ws.cell(177, 19).value == "birthday"
        assert ws.cell(179, 19).value == "NNN paperwork"

        for legacy_row in [38, 42, 59, 137]:
            assert ws.cell(legacy_row, 19).value is None
            assert ws.cell(legacy_row, 6).value is None

        assert CANONICAL_SOURCE_FILE_ORDER[0] in ws.cell(168, 20).value
        assert CANONICAL_SOURCE_FILE_ORDER[1] in ws.cell(170, 20).value
        assert CANONICAL_SOURCE_FILE_ORDER[6] in ws.cell(179, 20).value
    finally:
        wb.close()


def test_run_e2e_complete_v1_calls_source_order_writer_before_reference_fill():
    text = Path("scripts/run_e2e.py").read_text(encoding="utf-8")

    assert "apply_complete_v1_source_order_to_workbook" in text
    assert text.index("apply_complete_v1_source_order_to_workbook") < text.index("apply_mp_saisan_complete_v1")
