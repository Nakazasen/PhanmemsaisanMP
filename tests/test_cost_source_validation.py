from pathlib import Path
from unittest.mock import patch

import openpyxl
import pytest

from src.universal_app import _validate_selected_source_dir
from src.utils.source_manifest import merge_manifest_with_detected, validate_cost_source_manifest
from scripts.run_e2e import run_universal_pipeline


def _write_manifest(directory: Path, filename: str, *, enabled: str = "1") -> None:
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append(
        ("order", "category", "filename", "enabled", "description", "period_start", "period_end")
    )
    worksheet.append(("1", "it_simulation", filename, enabled, "IT", "202604", "202703"))
    workbook.save(directory / "source_file_order.xlsx")
    workbook.close()


def test_staffing_only_directory_is_rejected_as_cost_source(tmp_path):
    (tmp_path / "headcount_manual.csv").write_text("cc_code,period\n", encoding="utf-8")

    with pytest.raises(ValueError, match="không có source_file_order"):
        validate_cost_source_manifest(str(tmp_path))

    message = _validate_selected_source_dir(str(tmp_path))
    assert message is not None
    assert "không chọn thư mục chỉ chứa dữ liệu nhân sự" in message


def test_explicit_manifest_with_existing_enabled_source_is_accepted(tmp_path):
    source = tmp_path / "renamed-system-source.xlsx"
    source.write_bytes(b"placeholder")
    _write_manifest(tmp_path, source.name)

    entries = validate_cost_source_manifest(str(tmp_path))

    assert [entry["filename"] for entry in entries] == [source.name]
    assert _validate_selected_source_dir(str(tmp_path)) is None


def test_manifest_missing_enabled_file_is_rejected(tmp_path):
    _write_manifest(tmp_path, "missing.xlsx")

    with pytest.raises(FileNotFoundError, match="missing.xlsx"):
        validate_cost_source_manifest(str(tmp_path))


def test_manifest_refresh_preserves_it_period_metadata(tmp_path):
    source = tmp_path / "system-simulation-FY2027.xlsx"
    source.write_bytes(b"placeholder")
    _write_manifest(tmp_path, source.name)

    entries = merge_manifest_with_detected(str(tmp_path))

    assert entries[0]["period_start"] == "202604"
    assert entries[0]["period_end"] == "202703"


def test_pipeline_rejects_wrong_cost_source_before_opening_database(tmp_path):
    with patch("scripts.run_e2e.get_connection") as get_connection:
        success, message = run_universal_pipeline(
            fiscal_year=2027,
            template_path="unused.xlsx",
            source_dir=str(tmp_path),
            db_path=str(tmp_path / "isolated.db"),
            output_dir=str(tmp_path / "output"),
        )

    assert success is False
    assert "source_file_order" in message
    get_connection.assert_not_called()
