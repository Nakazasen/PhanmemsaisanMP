import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

import pytest

from src.db.schema import create_schema
from src.parsers.headcount_time_plan import parse_headcount_time_plan
from src.services.headcount_source_importer import (
    cleanup_headcount_truth,
    count_headcount_truth_rows,
    fiscal_year_periods,
    import_headcount_time_sources,
)
from scripts.run_e2e import (
    _exclude_incomplete_staffing_ccs_for_audit,
    _simulate_missing_baseline_from_april,
    _staffing_preflight,
    run_universal_pipeline,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "raw" / "10.07.2026"

class HeadcountTimeSourceTests(unittest.TestCase):
    @pytest.mark.requires_raw_excel
    def test_department_16_parses_all_months_and_metrics(self):
        path = next(SOURCE.glob("16.*.xls"))
        result = parse_headcount_time_plan(str(path), 2027)
        self.assertEqual(result.status, "valid", result.errors)
        self.assertEqual(result.cc_code, "1412000040")
        self.assertEqual(len(result.rows), 12)
        self.assertEqual(result.rows[0]["period"], "202604")
        self.assertEqual(result.rows[0]["headcount_expat"], 1)
        self.assertEqual(result.rows[0]["headcount_staff"], 17)
        self.assertEqual(result.rows[0]["fixed_hours_expat"], 153)
        self.assertEqual(result.rows[0]["overtime_hours_local"], 186)

    @pytest.mark.requires_raw_excel
    def test_import_is_idempotent_and_skips_unknown_cc(self):
        conn=sqlite3.connect(":memory:"); conn.row_factory=sqlite3.Row; create_schema(conn)
        departments = (
            ("1412000006", "メカ製造技術1課"),
            ("1412000040", "電気製造技術課"),
            ("1412000039", "製造技術管理課"),
        )
        for code, name in departments:
            conn.execute("INSERT INTO dim_cost_centers(code,name_jp,saisan_type,cost_type) VALUES(?,?,'MFG','Fixed')",(code,name))
        first=import_headcount_time_sources(conn,str(SOURCE),2027)
        second=import_headcount_time_sources(conn,str(SOURCE),2027)
        self.assertEqual(first["files"],64)
        self.assertEqual(first["imported_files"],3)
        self.assertEqual(first["imported_rows"],36)
        self.assertEqual(second["imported_rows"],36)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM fact_monthly_headcount WHERE source='department_plan'").fetchone()[0],36)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM fact_headcount_time_source").fetchone()[0],36)
        selected = conn.execute("SELECT DISTINCT description FROM fact_monthly_headcount WHERE cc_code='1412000039' AND source='department_plan'").fetchone()[0]
        self.assertEqual(selected, "製造技術管理課")

    def test_cleanup_truth_is_fy_scoped_and_preserves_manual_data(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        create_schema(conn)
        fy2027 = fiscal_year_periods(2027)
        self.assertEqual(fy2027[0], "202604")
        self.assertEqual(fy2027[-1], "202703")
        self.assertEqual(len(fy2027), 12)

        for period in ("202604", "202703", "202704"):
            conn.execute(
                """INSERT INTO fact_monthly_headcount
                (period,cc_code,headcount_all,source) VALUES(?,?,?,?)""",
                (period, "CC01", 10, "department_plan"),
            )
            conn.execute(
                """INSERT INTO fact_headcount_time_source
                (period,cc_code,fixed_hours_local) VALUES(?,?,?)""",
                (period, "CC01", 100),
            )
        conn.executemany(
            """INSERT INTO fact_monthly_headcount
            (period,cc_code,headcount_all,source) VALUES(?,?,?,?)""",
            (
                ("202604", "CC01", 9, "manual"),
                ("202604", "CC01", 8, "ga"),
            ),
        )
        conn.executemany(
            """INSERT INTO sys_params(key,value,description)
            VALUES(?,?,'test')""",
            (
                ("headcount_source_dir", r"D:\source"),
                ("headcount_source_fiscal_year", "2027"),
                ("headcount_source_updated_at", "2026-07-12T15:00:00"),
            ),
        )
        conn.commit()

        before = count_headcount_truth_rows(conn, 2027)
        self.assertEqual(before["monthly_headcount_rows"], 2)
        self.assertEqual(before["headcount_time_rows"], 2)
        self.assertEqual(before["total_rows"], 4)

        removed = cleanup_headcount_truth(conn, 2027)
        self.assertEqual(removed["total_rows"], 4)
        self.assertEqual(
            conn.execute(
                "SELECT COUNT(*) FROM fact_monthly_headcount WHERE source='department_plan'"
            ).fetchone()[0],
            1,
        )
        self.assertEqual(
            conn.execute(
                "SELECT COUNT(*) FROM fact_monthly_headcount WHERE source='manual'"
            ).fetchone()[0],
            1,
        )
        self.assertEqual(
            conn.execute(
                "SELECT COUNT(*) FROM fact_monthly_headcount WHERE source='ga'"
            ).fetchone()[0],
            1,
        )
        self.assertEqual(
            conn.execute("SELECT COUNT(*) FROM fact_headcount_time_source").fetchone()[0],
            1,
        )
        self.assertEqual(
            conn.execute(
                "SELECT value FROM sys_params WHERE key='headcount_source_dir'"
            ).fetchone()[0],
            r"D:\source",
        )
        self.assertIsNone(
            conn.execute(
                "SELECT value FROM sys_params WHERE key='headcount_source_updated_at'"
            ).fetchone()
        )
        self.assertEqual(cleanup_headcount_truth(conn, 2027)["total_rows"], 0)

    @pytest.mark.requires_raw_excel
    def test_cleanup_then_import_recreates_truth_rows(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        create_schema(conn)
        departments = (
            ("1412000006", "メカ製造技術1課"),
            ("1412000040", "電気製造技術課"),
            ("1412000039", "製造技術管理課"),
        )
        for code, name in departments:
            conn.execute(
                "INSERT INTO dim_cost_centers(code,name_jp,saisan_type,cost_type) VALUES(?,?,'MFG','Fixed')",
                (code, name),
            )
        imported = import_headcount_time_sources(conn, str(SOURCE), 2027)
        self.assertEqual(imported["imported_rows"], 36)
        self.assertEqual(cleanup_headcount_truth(conn, 2027)["total_rows"], 72)
        self.assertEqual(
            conn.execute("SELECT COUNT(*) FROM fact_headcount_time_source").fetchone()[0],
            0,
        )
        reimported = import_headcount_time_sources(conn, str(SOURCE), 2027)
        self.assertEqual(reimported["imported_rows"], 36)
        self.assertEqual(
            conn.execute(
                "SELECT COUNT(*) FROM fact_monthly_headcount WHERE source='department_plan'"
            ).fetchone()[0],
            36,
        )
        self.assertEqual(
            conn.execute("SELECT COUNT(*) FROM fact_headcount_time_source").fetchone()[0],
            36,
        )

    @pytest.mark.requires_raw_excel
    def test_real_bilingual_duplicate_corrupt_and_xlsx_cases(self):
        vietnamese = parse_headcount_time_plan(str(next(SOURCE.glob("12.*.xls"))), 2027)
        duplicate_cc = parse_headcount_time_plan(str(next(SOURCE.glob("15.*.xls"))), 2027)
        corrupt = parse_headcount_time_plan(str(next(SOURCE.glob("44.*.xls"))), 2027)
        missing_lookup = parse_headcount_time_plan(str(next(SOURCE.glob("64.*.xlsx"))), 2027)

        self.assertEqual(vietnamese.status, "valid", vietnamese.errors)
        self.assertEqual(vietnamese.lookup_status, "matched")
        self.assertEqual(vietnamese.verification_method, "workbook_bilingual_lookup")
        self.assertEqual(duplicate_cc.status, "valid", duplicate_cc.errors)
        self.assertEqual(duplicate_cc.lookup_status, "matched")
        self.assertEqual(duplicate_cc.department_name_jp, "メカ製造技術2課")
        self.assertEqual(corrupt.status, "error")
        self.assertIn("Không mở được file", corrupt.errors[0])
        self.assertEqual(missing_lookup.status, "valid", missing_lookup.errors)
        self.assertEqual(missing_lookup.lookup_status, "missing")

    @pytest.mark.requires_raw_excel
    def test_xlsx_missing_lookup_uses_matching_master_fallback(self):
        parsed = parse_headcount_time_plan(str(next(SOURCE.glob("64.*.xlsx"))), 2027)
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        create_schema(conn)
        conn.execute(
            "INSERT INTO dim_cost_centers(code,name_jp,saisan_type,cost_type) VALUES(?,?,'MFG','Fixed')",
            (parsed.cc_code, parsed.department_name),
        )

        result = import_headcount_time_sources(
            conn, str(SOURCE), 2027, scan_results=[parsed]
        )

        self.assertEqual(result["imported_files"], 1)
        self.assertEqual(parsed.verification_method, "fallback_master_name")
        self.assertEqual(
            conn.execute("SELECT COUNT(*) FROM fact_monthly_headcount").fetchone()[0], 12
        )

    @pytest.mark.requires_raw_excel
    def test_unknown_cc_requires_confirmation_then_imports_without_master_and_audits(self):
        parsed = parse_headcount_time_plan(str(next(SOURCE.glob("72.*.xls"))), 2027)
        self.assertEqual(parsed.status, "valid", parsed.errors)
        self.assertEqual(parsed.lookup_status, "matched")
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        create_schema(conn)

        blocked = import_headcount_time_sources(
            conn, str(SOURCE), 2027, scan_results=[parsed]
        )
        self.assertEqual(blocked["imported_files"], 0)
        self.assertEqual(
            conn.execute("SELECT COUNT(*) FROM audit_headcount_source_decisions").fetchone()[0], 0
        )

        confirmed = import_headcount_time_sources(
            conn,
            str(SOURCE),
            2027,
            approved_unknown_files={parsed.path},
            scan_results=[parsed],
        )

        self.assertEqual(confirmed["imported_files"], 1)
        self.assertEqual(confirmed["imported_rows"], 12)
        self.assertIsNone(
            conn.execute("SELECT 1 FROM dim_cost_centers WHERE code=?", (parsed.cc_code,)).fetchone()
        )
        audit = conn.execute(
            "SELECT decision,cc_code,source_file FROM audit_headcount_source_decisions"
        ).fetchone()
        self.assertEqual(audit["decision"], "CONFIRMED_IMPORT")
        self.assertEqual(audit["cc_code"], parsed.cc_code)
        self.assertEqual(audit["source_file"], os.path.abspath(parsed.path))

    def test_audit_baseline_simulation_uses_canonical_period_and_preserves_observed(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        create_schema(conn)
        conn.executemany(
            """INSERT INTO fact_monthly_headcount
            (period,cc_code,headcount_staff,headcount_worker,headcount_all,source,description)
            VALUES(?,?,?,?,?,?,?)""",
            (
                ("202604", "CC_SIM", 3, 7, 10, "department_plan", "April"),
                ("202604", "CC_OBS", 4, 8, 12, "department_plan", "April"),
                ("202603", "CC_OBS", 5, 8, 13, "manual", "Observed baseline"),
            ),
        )
        conn.commit()

        inserted = _simulate_missing_baseline_from_april(conn, 2027)

        self.assertEqual(inserted, 1)
        simulated = conn.execute(
            """SELECT period,headcount_staff,headcount_worker,headcount_all,description
            FROM fact_monthly_headcount WHERE cc_code='CC_SIM' AND source='manual'"""
        ).fetchone()
        self.assertEqual(tuple(simulated), ("202603", 3.0, 7.0, 10.0, "SIMULATED_BASELINE_T3_FROM_T4"))
        observed = conn.execute(
            "SELECT headcount_all,description FROM fact_monthly_headcount WHERE cc_code='CC_OBS' AND period='202603'"
        ).fetchall()
        self.assertEqual([tuple(row) for row in observed], [(13.0, "Observed baseline")])

    def test_audit_scope_excludes_incomplete_cc_from_preflight(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        create_schema(conn)
        periods = fiscal_year_periods(2027)
        conn.executemany(
            "INSERT INTO dim_cost_centers(code,name_jp,saisan_type,cost_type) VALUES(?,?,'MFG','Fixed')",
            (("CC_OK", "Complete"), ("CC_BLOCKED", "Incomplete")),
        )
        for period in periods:
            conn.execute(
                "INSERT INTO fact_monthly_headcount(period,cc_code,headcount_all,source) VALUES(?,?,10,'department_plan')",
                (period, "CC_OK"),
            )
            conn.execute(
                "INSERT INTO fact_headcount_time_source(period,cc_code,fixed_hours_local) VALUES(?,?,100)",
                (period, "CC_OK"),
            )
        conn.executemany(
            "INSERT INTO fact_input_data(source,period,amount_vnd,cc_code,account_code) VALUES('test','202604',1,?,1)",
            (("CC_OK",), ("CC_BLOCKED",)),
        )
        conn.execute(
            "INSERT INTO fact_monthly_headcount(period,cc_code,headcount_all,source) VALUES('202603','CC_OK',9,'manual')"
        )
        conn.commit()

        excluded = _exclude_incomplete_staffing_ccs_for_audit(conn, 2027)
        issues = _staffing_preflight(conn, 2027, excluded_ccs=set(excluded))

        self.assertEqual(excluded, ["CC_BLOCKED"])
        self.assertEqual(issues, [])
        self.assertIsNone(conn.execute("SELECT 1 FROM dim_cost_centers WHERE code='CC_BLOCKED'").fetchone())

    def test_audit_flags_require_nonproduction_database_path(self):
        common = {
            "fiscal_year": 2027,
            "template_path": "unused-form.xlsx",
            "source_dir": "unused-source",
            "simulate_baseline_t3_from_t4": True,
        }
        missing_path = run_universal_pipeline(**common)
        production_path = run_universal_pipeline(
            **common,
            db_path=str(ROOT / "mp2027.db"),
        )

        self.assertFalse(missing_path[0])
        self.assertFalse(production_path[0])
        self.assertIn("db_path cô lập", missing_path[1])
        self.assertIn("db_path cô lập", production_path[1])


if __name__ == "__main__": unittest.main()
