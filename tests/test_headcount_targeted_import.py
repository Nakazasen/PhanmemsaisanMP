from pathlib import Path

from src.services.headcount_source_importer import _target_workbook_paths


def test_single_cc_headcount_scan_uses_only_matching_department_file(tmp_path: Path):
    selected = tmp_path / "14.KDTVN メカ製造技術1課_FY2027マスタープラン人員・時間計画表.xls"
    unrelated = tmp_path / "15.KDTVN メカ製造技術2課_FY2027マスタープラン人員・時間計画表.xls"
    paths = [str(selected), str(unrelated)]

    assert _target_workbook_paths(paths, "1412000006", ("メカ製造技術1課", "")) == [str(selected)]


def test_single_cc_headcount_scan_falls_back_when_filename_cannot_be_matched(tmp_path: Path):
    paths = [str(tmp_path / "opaque_FY2027.xls")]

    assert _target_workbook_paths(paths, "1412000006", ("メカ製造技術1課", "")) == paths
