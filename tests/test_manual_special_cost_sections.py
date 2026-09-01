from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import openpyxl
import pytest
from openpyxl.styles import PatternFill

from src.engine.manual_special_cost_sections import (
    MANUAL_SPECIAL_COST_METADATA_SHEET,
    ManualSpecialCostSectionError,
    preserve_manual_special_cost_section,
)
from scripts.run_e2e import _restore_manual_special_cost_section, _stage_manual_special_cost_source


def _make_output(path: Path, *, common_end_row: int) -> None:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Chi tiết MP"
    for row in range(37, common_end_row + 1):
        sheet.cell(row, 2).value = 5000000000 + row
        sheet.cell(row, 19).value = f"common-{row}"
        sheet.cell(row, 6).value = row
    workbook.save(path)
    workbook.close()


def _add_legacy_manual_rows(path: Path, start_row: int) -> None:
    workbook = openpyxl.load_workbook(path)
    sheet = workbook["Chi tiết MP"]
    sheet.cell(start_row, 2).value = 5005246286
    sheet.cell(start_row, 19).value = "Chi phí riêng A"
    sheet.cell(start_row, 6).value = 1250000
    sheet.cell(start_row, 18).value = f"=SUM(F{start_row}:Q{start_row})"
    sheet.cell(start_row, 19).fill = PatternFill("solid", fgColor="00FF00")
    sheet.cell(start_row + 1, 2).value = 5005246288
    sheet.cell(start_row + 1, 19).value = "Chi phí riêng B"
    sheet.cell(start_row + 1, 6).value = 2500000
    workbook.save(path)
    workbook.close()


def _metadata_row(path: Path) -> tuple[object, ...]:
    workbook = openpyxl.load_workbook(path, data_only=False)
    try:
        sheet = workbook[MANUAL_SPECIAL_COST_METADATA_SHEET]
        return tuple(sheet.cell(2, column).value for column in range(1, 8))
    finally:
        workbook.close()


def test_legacy_manual_rows_move_below_new_dynamic_common_block_without_mutating_source(tmp_path):
    source = tmp_path / "MP_CC_1412000030_FY2026.xlsx"
    generated = tmp_path / "MP_CC_1412000030_FY2027.xlsx"
    _make_output(source, common_end_row=86)
    _add_legacy_manual_rows(source, 87)
    before = source.read_bytes()
    _make_output(generated, common_end_row=90)

    result = preserve_manual_special_cost_section(
        generated,
        cc_code="1412000030",
        source_workbook_path=source,
        legacy_start_row=87,
    )

    assert result["manual_rows_preserved"] == 2
    assert result["manual_start_row"] == 92
    assert source.read_bytes() == before
    workbook = openpyxl.load_workbook(generated, data_only=False)
    try:
        sheet = workbook["Chi tiết MP"]
        assert sheet["S91"].value == "CHI PHÍ RIÊNG - NHẬP THỦ CÔNG"
        assert sheet["B92"].value == 5005246286
        assert sheet["S92"].value == "Chi phí riêng A"
        assert sheet["F92"].value == 1250000
        assert sheet["R92"].value == "=SUM(F92:Q92)"
        assert sheet["S92"].fill.fgColor.rgb.endswith("00FF00")
        assert sheet["B93"].value == 5005246288
        assert MANUAL_SPECIAL_COST_METADATA_SHEET in workbook.sheetnames
        assert workbook[MANUAL_SPECIAL_COST_METADATA_SHEET].sheet_state == "veryHidden"
    finally:
        workbook.close()
    assert _metadata_row(generated)[2:] == ("1412000030", 90, 92, 93, 1)


def test_metadata_snapshot_survives_rerun_when_common_block_grows(tmp_path):
    first = tmp_path / "MP_CC_1412000030_first.xlsx"
    rerun = tmp_path / "MP_CC_1412000030_rerun.xlsx"
    _make_output(first, common_end_row=86)
    _add_legacy_manual_rows(first, 87)
    preserve_manual_special_cost_section(first, "1412000030", source_workbook_path=first, legacy_start_row=87)
    _make_output(rerun, common_end_row=94)

    result = preserve_manual_special_cost_section(rerun, "1412000030", source_workbook_path=first)

    assert result["manual_start_row"] == 96
    workbook = openpyxl.load_workbook(rerun, data_only=False)
    try:
        sheet = workbook["Chi tiết MP"]
        assert sheet["B96"].value == 5005246286
        assert sheet["S96"].value == "Chi phí riêng A"
        assert sheet["B97"].value == 5005246288
    finally:
        workbook.close()


def test_unmarked_source_requires_explicit_start_row(tmp_path):
    source = tmp_path / "old.xlsx"
    generated = tmp_path / "new.xlsx"
    _make_output(source, common_end_row=86)
    _add_legacy_manual_rows(source, 87)
    _make_output(generated, common_end_row=90)

    with pytest.raises(ManualSpecialCostSectionError, match="chưa có dấu mốc"):
        preserve_manual_special_cost_section(generated, "1412000030", source_workbook_path=source)


def test_pipeline_prefers_current_fy_snapshot_over_prior_fy_inheritance(tmp_path):
    current_dir = tmp_path / "OUTPUT_FY2027"
    inherited_dir = tmp_path / "OUTPUT_FY2026"
    workspace = tmp_path / "workspace"
    current_dir.mkdir()
    inherited_dir.mkdir()
    workspace.mkdir()
    current = current_dir / "MP_CC_1412000030.xlsx"
    inherited = inherited_dir / "MP_CC_1412000030.xlsx"
    generated = tmp_path / "generated.xlsx"
    _make_output(current, common_end_row=86)
    _add_legacy_manual_rows(current, 87)
    _make_output(inherited, common_end_row=86)
    _add_legacy_manual_rows(inherited, 87)
    old = openpyxl.load_workbook(inherited)
    old["Chi tiết MP"]["S87"] = "Không được dùng"
    old.save(inherited)
    old.close()
    _make_output(generated, common_end_row=90)
    context = SimpleNamespace(
        output_dir=str(current_dir),
        workspace_dir=str(workspace),
        manual_special_inheritance_dir=str(inherited_dir),
        manual_special_legacy_starts={"1412000030": 87},
    )

    source, kind = _stage_manual_special_cost_source(context, "1412000030")
    result = _restore_manual_special_cost_section(
        str(generated),
        run_context=context,
        cc_code="1412000030",
        source_path=source,
        source_kind=kind,
        log_callback=lambda _message: None,
    )

    assert kind == "current_fiscal_year"
    assert result["manual_rows_preserved"] == 2
    workbook = openpyxl.load_workbook(generated, data_only=False)
    try:
        assert workbook["Chi tiết MP"]["S92"].value == "Chi phí riêng A"
    finally:
        workbook.close()
