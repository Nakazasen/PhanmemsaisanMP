import sqlite3
from pathlib import Path

import openpyxl

from src.db.schema import create_schema, init_sys_params
from src.parsers.fixed_assets import inspect_fixed_assets_workbook, parse_fixed_assets
from src.audit.fixed_assets_coverage import build_fixed_assets_coverage_report
from src.utils.fiscal_periods import fiscal_periods


def _mk_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    init_sys_params(conn, exchange_rate=100.0, fiscal_year=2027)
    return conn


def _write_fixed_assets_fixture(path: Path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "2025.11"
    ws.append([
        "Asset No",
        "Asset Text",
        "Control Cost Center",
        "Code phòng chịu chi phí / Depreciation Cost Center",
        "Chi phí khấu hao",
        "Tháng khấu hao cuối cùng",
        "Chi phí khấu hao của tháng cuối cùng",
        "Chi phí lãi tháng 4",
        "Chi phí lãi",
    ])
    ws.append(["A-001", "Machine A", "CONTROL-IGNORED", "1412000040", 10, "2026-05-31", 4, 1, 2])
    ws.append(["A-002", "Machine B", "CONTROL-IGNORED", "1412000040", 20, "2027-11-30", 5, 3, 4])
    ws.append(["B-001", "Machine C", "CONTROL-IGNORED", "1412000018", 7, None, None, 0, 0])
    ws.append(["NOCC", "Skipped", "CONTROL-IGNORED", None, 99, None, None, 0, 0])
    ws2 = wb.create_sheet("Extra")
    ws2.append([
        "Asset No",
        "Asset Text",
        "Depreciation Cost Center",
        "Monthly depreciation",
        "Last depreciation month",
        "Last month depreciation",
        "Apr interest",
        "May interest",
    ])
    ws2.append(["C-001", "Machine D", "1412000040", 5, "2026-04-30", 2, 9, 8])
    wb.save(path)


def test_parse_fixed_assets_reads_all_matching_sheets_and_cc_rows(tmp_path):
    workbook = tmp_path / "Fixed_Assets_Information_fixture.xlsx"
    _write_fixed_assets_fixture(workbook)
    conn = _mk_conn()

    result = parse_fixed_assets(conn, fa_path=str(workbook))

    assert result["source_rows"] == 4
    assert result["parsed_assets"] == 4
    assert result["by_cc"]["1412000040"] == 3
    assert result["by_cc"]["1412000018"] == 1
    assert result["skipped_reasons"]["missing_cc"] == 1

    cc_4040_rows = conn.execute(
        "SELECT COUNT(*) FROM fact_input_data WHERE source='fixed_assets' AND cc_code='1412000040'"
    ).fetchone()[0]
    assert cc_4040_rows > 0

    depr_may = conn.execute(
        """
        SELECT amount_usd FROM fact_input_data
        WHERE cc_code='1412000040' AND period='202605' AND description LIKE 'fixed_assets_depr|A-001%'
        """
    ).fetchone()
    assert float(depr_may[0]) == 4.0

    after_last = conn.execute(
        """
        SELECT COUNT(*) FROM fact_input_data
        WHERE cc_code='1412000040' AND period='202606' AND description LIKE 'fixed_assets_depr|A-001%'
        """
    ).fetchone()[0]
    assert after_last == 0

    before_last_interest = conn.execute(
        """
        SELECT amount_usd FROM fact_input_data
        WHERE cc_code='1412000040' AND period='202605' AND description LIKE 'fixed_assets_interest|A-001%'
        """
    ).fetchone()
    assert float(before_last_interest[0]) == 2.0

    interest_after_last = conn.execute(
        """
        SELECT COUNT(*) FROM fact_input_data
        WHERE cc_code='1412000040' AND period='202606' AND description LIKE 'fixed_assets_interest|A-001%'
        """
    ).fetchone()[0]
    assert interest_after_last == 0
    conn.close()


def test_fixed_assets_coverage_report_is_non_sensitive_and_flags_missing_parse(tmp_path):
    workbook = tmp_path / "Fixed_Assets_Information_fixture.xlsx"
    _write_fixed_assets_fixture(workbook)
    conn = _mk_conn()

    source_only = inspect_fixed_assets_workbook(workbook)
    assert source_only["source_rows"] == 4
    assert "1412000040" in source_only["by_cc"]

    report_before = build_fixed_assets_coverage_report(conn, workbook)
    assert "1412000040" in report_before["mismatches"]

    parse_fixed_assets(conn, fa_path=str(workbook))
    report_after = build_fixed_assets_coverage_report(conn, workbook)
    assert report_after["mismatches"] == {}
    assert report_after["db"]["period_rows_by_cc"]["1412000040"] > 0
    conn.close()


def test_fixed_assets_raw_workbook_coverage_if_present():
    workbook = Path("docs/MP2027/固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx")
    if not workbook.exists():
        workbook = Path("raw/固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx")
    if not workbook.exists():
        return
    conn = _mk_conn()
    result = parse_fixed_assets(conn, fa_path=str(workbook))
    report = build_fixed_assets_coverage_report(conn, workbook)
    assert result["source_rows"] >= result["parsed_assets"]
    assert isinstance(report["source"].get("by_cc", {}), dict)
    conn.close()



def test_fixed_assets_legacy_layout_uses_depreciation_cost_center_column(tmp_path):
    workbook = tmp_path / "Fixed_Assets_Information_legacy.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "2025.11"
    ws.append([None] * 23)
    ws.append([None] * 23)
    ws.append([None] * 23)
    ws.append([
        "No", "Category", "Assets No", "Text", "Material", "Date", "Life",
        "Control Cost Center", "Control Name",
        "Depreciation Cost Center", "Depreciation Name",
        "November 2025 Depreciation", "Interest in December 2025", "Balance",
        "Class", "Last Depreciation Month", "Last Month Depr", "Allocation", "WBS", None,
        "FY2027 Beginning balance", "Interest in April 2026", "Interest from May 2026",
    ])
    row = [None] * 23
    row[0] = 1
    row[2] = "LEG-001"
    row[3] = "Legacy machine"
    row[7] = "1412000084"   # control/owner CC, must not drive output
    row[9] = "1412000004"   # cost-bearing depreciation CC
    row[11] = 375.31
    row[15] = "2026-08-31"
    row[16] = 123.45
    row[21] = 19.14
    row[22] = 5.63
    ws.append(row)
    wb.save(workbook)

    conn = _mk_conn()
    result = parse_fixed_assets(conn, fa_path=str(workbook))
    assert result["by_cc"] == {"1412000004": 1}
    assert "1412000084" not in result["by_cc"]
    assert conn.execute(
        "SELECT COUNT(*) FROM fact_input_data WHERE cc_code='1412000004' AND source='fixed_assets'"
    ).fetchone()[0] > 0
    assert conn.execute(
        "SELECT COUNT(*) FROM fact_input_data WHERE cc_code='1412000084' AND source='fixed_assets'"
    ).fetchone()[0] == 0
    conn.close()
