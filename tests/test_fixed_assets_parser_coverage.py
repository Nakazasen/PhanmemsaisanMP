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
    account_rows = (
        (5006016242, "減価償却費（製） 機械装置", "減価償却費"),
        (5006016243, "減価償却費（製） 車輌運搬具", "減価償却費"),
        (5006016244, "減価償却費（製） 工具器具備品", "減価償却費"),
        (5006016247, "減価償却費（製） その他有形固定資産", "減価償却費"),
        (5005036246, "減価償却費（製） 金型", "金型償却費"),
        (9114120007, "社内金利（固定資産）", "固定資産金利"),
    )
    conn.executemany(
        """INSERT INTO dim_accounts(code,name_jp,group_name,mfg_code,ga_code,sales_code)
           VALUES(?,?,?,?,?,?)""",
        [(code, name, group, code, code if code == 9114120007 else None, code if code == 9114120007 else None) for code, name, group in account_rows],
    )
    _seed_cost_centers(conn, ("1412000040", "1412000018"))
    conn.commit()
    return conn


def _seed_cost_centers(conn, codes):
    conn.executemany(
        "INSERT OR IGNORE INTO dim_cost_centers(code,name_jp,saisan_type,cost_type) VALUES(?,?,'MFG','製造')",
        [(str(code), str(code)) for code in codes],
    )


def _asset_row(category, asset_no, text, control_cc, depreciation_cc, monthly, last_month, last_amount, apr, may):
    row = [None] * 23
    row[1], row[2], row[3] = category, asset_no, text
    row[7], row[9] = control_cc, depreciation_cc
    row[11], row[15], row[16] = monthly, last_month, last_amount
    row[21], row[22] = apr, may
    return row


def _write_fixed_assets_fixture(path: Path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "2025.11"
    for _ in range(4):
        ws.append([None] * 23)
    ws.append(_asset_row("MFG)MACHINERY AND EQUIPMENT", "A-001", "Machine A", "9999999999", "1412000040", 10, "2026-05-31", 4, 1, 2))
    ws.append(_asset_row("MFG)VEHICLES", "A-002", "Vehicle B", "9999999999", "1412000040", 20, "2027-11-30", 5, 3, 4))
    ws.append(_asset_row("MFG)TOOLS FURNITURE AND FIXTURES", "B-001", "Tool C", "1412000040", "1412000018", 7, None, None, 0, 0))
    ws.append(_asset_row("MFG)SOFTWARE", "OUT-001", "Software", "1412000040", "1412000040", 9, None, None, 0, 0))
    ws.append(_asset_row("MFG)MOLD", "NOCC", "Skipped", "1412000040", None, 99, None, None, 0, 0))

    history = wb.create_sheet("2025.10")
    for _ in range(4):
        history.append([None] * 23)
    history.append(_asset_row("MFG)MACHINERY AND EQUIPMENT", "OLD-001", "Historical", "1412000040", "1412000040", 999, None, None, 0, 0))
    wb.save(path)


def test_parse_fixed_assets_uses_current_sheet_depreciation_cc_and_is_idempotent(tmp_path):
    workbook = tmp_path / "Fixed_Assets_Information_fixture.xlsx"
    _write_fixed_assets_fixture(workbook)
    conn = _mk_conn()

    result = parse_fixed_assets(conn, fa_path=str(workbook))

    assert result["source_rows"] == 3
    assert result["parsed_assets"] == 3
    assert result["selected_sheets"] == ["2025.11"]
    assert result["by_cc"]["1412000040"] == 2
    assert result["by_cc"]["1412000018"] == 1
    assert result["skipped_reasons"]["missing_depreciation_cc"] == 1
    assert result["skipped_reasons"]["out_of_scope_category"] == 1

    row_count = conn.execute("SELECT COUNT(*) FROM fact_input_data WHERE source='fixed_assets'").fetchone()[0]
    assert row_count > 0
    parse_fixed_assets(conn, fa_path=str(workbook))
    assert conn.execute("SELECT COUNT(*) FROM fact_input_data WHERE source='fixed_assets'").fetchone()[0] == row_count

    depr_may = conn.execute(
        """
        SELECT amount_usd, account_code FROM fact_input_data
        WHERE cc_code='1412000040' AND period='202605'
          AND description LIKE 'fixed_assets_depr|machinery_equipment|A-001%'
        """
    ).fetchone()
    assert float(depr_may[0]) == 4.0
    assert int(depr_may[1]) == 5006016242

    after_last = conn.execute(
        """
        SELECT COUNT(*) FROM fact_input_data
        WHERE cc_code='1412000040' AND period='202606'
          AND description LIKE 'fixed_assets_depr|machinery_equipment|A-001%'
        """
    ).fetchone()[0]
    assert after_last == 0
    conn.close()


def test_fixed_assets_coverage_report_is_non_sensitive_and_flags_missing_parse(tmp_path):
    workbook = tmp_path / "Fixed_Assets_Information_fixture.xlsx"
    _write_fixed_assets_fixture(workbook)
    conn = _mk_conn()

    source_only = inspect_fixed_assets_workbook(workbook)
    assert source_only["source_rows"] == 3
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
    source_only = inspect_fixed_assets_workbook(workbook)
    _seed_cost_centers(conn, source_only["by_cc"])
    conn.commit()
    result = parse_fixed_assets(conn, fa_path=str(workbook))
    report = build_fixed_assets_coverage_report(conn, workbook)
    assert result["source_rows"] >= result["parsed_assets"]
    assert isinstance(report["source"].get("by_cc", {}), dict)
    conn.close()
