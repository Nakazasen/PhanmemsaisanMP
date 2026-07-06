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
        assert ws.cell(168, 18).value == "=SUM(F168:Q168)"
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


def test_complete_v1_writer_default_output_starts_at_row_30(tmp_path):
    workbook = _workbook(tmp_path / "out.xlsx")

    result = apply_complete_v1_source_order_to_workbook(workbook, clear_until_row=190)

    assert result["start_row"] == 30
    assert result["rows_written"] == 7
    assert result["blank_rows_written"] == 5

    wb = load_workbook(workbook)
    try:
        ws = wb[SHEET]
        assert ws.cell(30, 19).value == "facility building depreciation"
        assert ws.cell(30, 18).value == "=SUM(F30:Q30)"
        assert ws.cell(31, 19).value is None
        assert ws.cell(32, 19).value == "fixed asset depreciation"
        assert ws.cell(33, 19).value == "fixed asset interest"
        assert ws.cell(34, 19).value is None
        assert ws.cell(35, 19).value == "system cost"
    finally:
        wb.close()


def test_complete_v1_writer_manages_bus_rows_in_admin_source_block(tmp_path):
    path = tmp_path / "out.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET
    ws.cell(179, 2).value = 5004086291
    ws.cell(179, 6).value = 6111363
    ws.cell(179, 19).value = "system cost"
    ws.cell(53, 2).value = 5004086291
    ws.cell(53, 6).value = "=3*856107"
    ws.cell(53, 18).value = "=SUM(F53:Q53)"
    ws.cell(53, 19).value = "出向者BUS送迎費/Chi phí xe bus người JP"
    ws.cell(54, 2).value = 5004086291
    ws.cell(54, 6).value = "=20*1031546"
    ws.cell(54, 18).value = "=SUM(F54:Q54)"
    ws.cell(54, 19).value = "ローカル社BUS送迎費/Chi phí xe bus người VN"
    ws.cell(175, 2).value = 5004086291
    ws.cell(175, 6).value = 18895
    ws.cell(175, 19).value = "トイレットペーパー"
    wb.save(path)
    wb.close()

    result = apply_complete_v1_source_order_to_workbook(path, start_row=30, clear_until_row=199)

    assert result["rows_written"] == 4
    assert result["preserved_rows_written"] == 0
    assert result["blank_rows_written"] == 1

    wb = load_workbook(path)
    try:
        ws = wb[SHEET]
        assert ws.cell(30, 19).value == "system cost"
        assert ws.cell(31, 19).value is None
        assert ws.cell(32, 19).value == "出向者BUS送迎費/Chi phí xe bus người JP"
        assert ws.cell(32, 6).value == "=3*856107"
        assert ws.cell(32, 18).value == "=SUM(F32:Q32)"
        assert CANONICAL_SOURCE_FILE_ORDER[3] in ws.cell(32, 20).value
        assert "original_row=53" in ws.cell(32, 20).value
        assert ws.cell(33, 19).value == "ローカル社BUS送迎費/Chi phí xe bus người VN"
        assert ws.cell(33, 6).value == "=20*1031546"
        assert ws.cell(33, 18).value == "=SUM(F33:Q33)"
        assert "original_row=54" in ws.cell(33, 20).value
        assert ws.cell(34, 19).value == "トイレットペーパー"
        assert ws.cell(53, 19).value is None
        assert ws.cell(54, 19).value is None
    finally:
        wb.close()


def test_complete_v1_writer_keeps_source_rows_without_month_costs(tmp_path):
    path = tmp_path / "out.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET
    for row, account, description, amount in [
        (36, 5006016260, "facility building depreciation", 100),
        (175, 5004086291, "admin toilet paper", 200),
        (177, 5004086291, "admin alcohol placeholder", None),
        (59, 5004086291, "birthday", 300),
    ]:
        ws.cell(row, 2).value = account
        ws.cell(row, 5).value = "placeholder" if row == 177 else None
        ws.cell(row, 6).value = amount
        ws.cell(row, 19).value = description
        ws.cell(row, 20).value = "SOURCE_DERIVED"
    wb.save(path)
    wb.close()

    result = apply_complete_v1_source_order_to_workbook(path, start_row=168, clear_until_row=190)

    assert result["rows_written"] == 4
    assert result["blank_rows_written"] == 2

    wb = load_workbook(path)
    try:
        ws = wb[SHEET]
        assert ws.cell(168, 19).value == "facility building depreciation"
        assert ws.cell(169, 19).value is None
        assert ws.cell(170, 19).value == "admin toilet paper"
        assert ws.cell(171, 19).value == "admin alcohol placeholder"
        assert ws.cell(172, 19).value is None
        assert ws.cell(173, 19).value == "birthday"
        assert ws.cell(177, 19).value is None
        assert ws.cell(177, 5).value is None
    finally:
        wb.close()


def test_complete_v1_writer_reorders_existing_source_order_rows_idempotently(tmp_path):
    path = tmp_path / "out.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET
    ws.cell(168, 6).value = 100
    ws.cell(168, 19).value = "facility building depreciation"
    ws.cell(168, 20).value = f"source_file={CANONICAL_SOURCE_FILE_ORDER[0]}; original_row=36; source-order-complete-v1"
    ws.cell(170, 5).value = "alcohol_disinfectant"
    ws.cell(170, 19).value = "admin alcohol placeholder"
    ws.cell(170, 20).value = f"source_file={CANONICAL_SOURCE_FILE_ORDER[3]}; original_row=177; source-order-complete-v1"
    ws.cell(171, 6).value = 300
    ws.cell(171, 19).value = "birthday"
    ws.cell(171, 20).value = f"source_file={CANONICAL_SOURCE_FILE_ORDER[4]}; original_row=59; source-order-complete-v1"
    wb.save(path)
    wb.close()

    result = apply_complete_v1_source_order_to_workbook(path, start_row=168, clear_until_row=190)

    assert result["rows_written"] == 3
    assert result["blank_rows_written"] == 2

    wb = load_workbook(path)
    try:
        ws = wb[SHEET]
        assert ws.cell(168, 19).value == "facility building depreciation"
        assert ws.cell(169, 19).value is None
        assert ws.cell(170, 19).value == "admin alcohol placeholder"
        assert ws.cell(171, 19).value is None
        assert ws.cell(172, 19).value == "birthday"
        assert ws.cell(172, 18).value == "=SUM(F172:Q172)"
    finally:
        wb.close()


def test_complete_v1_writer_preserves_unmanaged_business_rows_inside_clear_range(tmp_path):
    path = tmp_path / "out.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET
    ws.cell(36, 6).value = 100
    ws.cell(36, 19).value = "facility building depreciation"
    ws.cell(52, 2).value = 5000000052
    ws.cell(52, 6).value = "=$B52*100"
    ws.cell(52, 18).value = "=SUM(F52:Q52)"
    ws.cell(52, 19).value = "preserved legacy row"
    wb.save(path)
    wb.close()

    result = apply_complete_v1_source_order_to_workbook(path, start_row=30, clear_until_row=90)

    assert result["rows_written"] == 1
    assert result["preserved_rows_written"] == 1

    wb = load_workbook(path)
    try:
        ws = wb[SHEET]
        assert ws.cell(30, 19).value == "facility building depreciation"
        assert ws.cell(32, 19).value == "preserved legacy row"
        assert ws.cell(32, 6).value == "=$B32*100"
        assert ws.cell(32, 18).value == "=SUM(F32:Q32)"
        assert ws.cell(52, 19).value is None
    finally:
        wb.close()


def test_complete_v1_writer_does_not_duplicate_source_order_marker_on_rerun(tmp_path):
    path = tmp_path / "out.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET
    ws.cell(168, 6).value = 100
    ws.cell(168, 19).value = "facility building depreciation"
    ws.cell(168, 20).value = (
        "COPY_SOURCE_MONTH_SAMPLE | "
        f"source_file={CANONICAL_SOURCE_FILE_ORDER[0]}; original_row=36; source-order-complete-v1"
    )
    wb.save(path)
    wb.close()

    apply_complete_v1_source_order_to_workbook(path, start_row=30, clear_until_row=190)
    apply_complete_v1_source_order_to_workbook(path, start_row=30, clear_until_row=190)

    wb = load_workbook(path)
    try:
        ws = wb[SHEET]
        note = ws.cell(30, 20).value
        assert note.startswith("COPY_SOURCE_MONTH_SAMPLE | source_file=")
        assert note.count("source-order-complete-v1") == 1
    finally:
        wb.close()


def test_run_e2e_complete_v1_final_source_order_writer_runs_after_reference_fill():
    text = Path("scripts/run_e2e.py").read_text(encoding="utf-8")

    assert "_apply_complete_v1_source_order(out_path, log_callback, phase=\"pre-reference\")" in text
    assert "_apply_complete_v1_source_order(out_path, log_callback, phase=\"final\")" in text
    assert text.index("phase=\"pre-reference\"") < text.index("apply_mp_saisan_complete_v1(")
    assert text.index("apply_mp_saisan_complete_v1(") < text.index("phase=\"final\"")
