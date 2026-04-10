import csv
import sqlite3
import unittest
from pathlib import Path
import shutil
import uuid

import openpyxl

from src.db.loader import _parse_unit_price
from src.db.schema import create_schema, init_sys_params
from src.engine.allocator import AllocationEngine
from src.engine.hub_builder import HubBuilder
from src.parsers.manual_headcount import parse_manual_headcount
from src.parsers.manual_special_costs import parse_manual_special_costs
from src.utils.excel_helpers import find_hub_sheet_name, get_fy_months


TEST_TMP_ROOT = Path.cwd() / ".tmp_test_artifacts"
TEST_TMP_ROOT.mkdir(exist_ok=True)


def _mk_tmpdir() -> Path:
    path = TEST_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def _mk_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    init_sys_params(conn, exchange_rate=26273, fiscal_year=2027)
    return conn


def _seed_cc(conn, code=1412000004):
    conn.execute(
        """
        INSERT INTO dim_cost_centers
        (code, name_jp, seq_no, saisan_type, cost_type, staff_count, worker_count)
        VALUES (?, 'TEST_CC', 1, '製造', '一般', 0, 0)
        """,
        (code,),
    )
    conn.commit()
    return code


class TestManualHeadcountGenderSplit(unittest.TestCase):
    def test_manual_parser_reads_optional_gender_columns(self):
        conn = _mk_conn()
        cc_code = _seed_cc(conn)
        periods = get_fy_months(2027)

        tmpdir = _mk_tmpdir()
        try:
            csv_path = tmpdir / "headcount_manual.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "cc_code",
                        "period",
                        "headcount_staff",
                        "headcount_worker",
                        "headcount_male",
                        "headcount_female",
                        "description",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "cc_code": str(cc_code),
                        "period": periods[8],
                        "headcount_staff": "5",
                        "headcount_worker": "10",
                        "headcount_male": "6",
                        "headcount_female": "7",
                        "description": "health check split",
                    }
                )

            result = parse_manual_headcount(conn, source_dir=str(tmpdir))
            self.assertEqual(result["inserted"], 1)

            row = conn.execute(
                """
                SELECT headcount_all, headcount_staff, headcount_worker, headcount_male, headcount_female
                FROM fact_monthly_headcount
                WHERE cc_code=? AND period=? AND source='manual'
                """,
                (cc_code, periods[8]),
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(float(row["headcount_all"]), 15.0)
            self.assertEqual(float(row["headcount_male"]), 6.0)
            self.assertEqual(float(row["headcount_female"]), 7.0)
        finally:
            conn.close()
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestHealthCheckAllocation(unittest.TestCase):
    def test_health_check_rules_use_gender_specific_counts(self):
        conn = _mk_conn()
        cc_code = _seed_cc(conn)
        periods = get_fy_months(2027)

        conn.execute(
            """
            INSERT INTO fact_monthly_headcount
            (
                period, cc_code, headcount_all, headcount_staff, headcount_worker,
                headcount_male, headcount_female, source, description
            )
            VALUES (?, ?, 20, 5, 15, 6, 9, 'manual', 'december split')
            """,
            (periods[8], cc_code),
        )

        conn.execute(
            """
            INSERT INTO map_allocation_rules
            (source_dept, item_name, account_name, mfg_account, ga_account, sales_account,
             posting_month, unit_price, unit, driver_type, driver_raw)
            VALUES
            ('QA', 'Khám sức khỏe (cho CNV nam)', 'HC', 500001, 600001, 700001, '12月', 100, '/unit', 'headcount_worker', '12月'),
            ('QA', 'Khám sức khỏe (cho CNV nữ)', 'HC', 500002, 600002, 700002, '12月', 200, '/unit', 'headcount_worker', '12月')
            """
        )
        conn.commit()

        AllocationEngine(conn)._process_allocation_rules()

        male_amount = conn.execute(
            "SELECT amount_vnd FROM fact_input_data WHERE description='Alloc: Khám sức khỏe (cho CNV nam)'"
        ).fetchone()
        female_amount = conn.execute(
            "SELECT amount_vnd FROM fact_input_data WHERE description='Alloc: Khám sức khỏe (cho CNV nữ)'"
        ).fetchone()

        self.assertIsNotNone(male_amount)
        self.assertIsNotNone(female_amount)
        self.assertEqual(float(male_amount["amount_vnd"]), 600.0)
        self.assertEqual(float(female_amount["amount_vnd"]), 1800.0)
        conn.close()


class TestPostingMonthOverride(unittest.TestCase):
    def test_override_uses_months_from_business_sheet(self):
        conn = _mk_conn()
        cc_code = _seed_cc(conn)
        periods = get_fy_months(2027)

        conn.execute(
            """
            INSERT INTO fact_monthly_headcount
            (
                period, cc_code, headcount_all, headcount_staff, headcount_worker,
                headcount_male, headcount_female, source, description
            )
            VALUES
            (?, ?, 3, 0, 3, 0, 0, 'manual', 'may worker'),
            (?, ?, 4, 0, 4, 0, 0, 'manual', 'feb worker')
            """,
            (periods[1], cc_code, periods[10], cc_code),
        )
        conn.execute(
            """
            INSERT INTO map_allocation_rules
            (source_dept, item_name, account_name, mfg_account, ga_account, sales_account,
             posting_month, unit_price, unit, driver_type, driver_raw)
            VALUES
            ('GA', 'Tiệc khuấy động năm tài chính / 決起コンパ（対象：全部門）', 'GA', 5004086291, 6004086651, 6004086551, '-', 300000, '/unit', 'headcount_worker', '-'),
            ('GA', '忘年会補助金 Hỗ trợ tiệc tất niên', 'GA', 5004086291, 6004086651, 6004086551, '-', 200000, '/unit', 'headcount_worker', '-')
            """
        )
        conn.commit()

        AllocationEngine(conn)._process_allocation_rules()

        kickoff = conn.execute(
            """
            SELECT period, amount_vnd
            FROM fact_input_data
            WHERE description LIKE 'Alloc: Tiệc khuấy động năm tài chính%'
            """
        ).fetchall()
        bonenkai = conn.execute(
            """
            SELECT period, amount_vnd
            FROM fact_input_data
            WHERE description = 'Alloc: 忘年会補助金 Hỗ trợ tiệc tất niên'
            """
        ).fetchall()

        self.assertEqual([(row["period"], float(row["amount_vnd"])) for row in kickoff], [(periods[1], 900000.0)])
        self.assertEqual([(row["period"], float(row["amount_vnd"])) for row in bonenkai], [(periods[10], 800000.0)])
        conn.close()


class TestRuleLoaderAndManualEventSafeguard(unittest.TestCase):
    def test_parse_unit_price_supports_currency_suffix(self):
        self.assertEqual(_parse_unit_price("145$"), 145.0)
        self.assertEqual(_parse_unit_price("1,259,500"), 1259500.0)
        self.assertEqual(_parse_unit_price(3000000), 3000000.0)
        self.assertIsNone(_parse_unit_price("abc"))

    def test_acquisition_month_rules_are_skipped_until_manual_event_data_exists(self):
        conn = _mk_conn()
        cc_code = _seed_cc(conn)
        period = get_fy_months(2027)[0]
        conn.execute(
            """
            INSERT INTO fact_monthly_headcount
            (
                period, cc_code, headcount_all, headcount_staff, headcount_worker,
                headcount_male, headcount_female, source, description
            )
            VALUES (?, ?, 20, 5, 15, 0, 0, 'manual', 'seed')
            """,
            (period, cc_code),
        )
        conn.execute(
            """
            INSERT INTO map_allocation_rules
            (source_dept, item_name, account_name, mfg_account, ga_account, sales_account,
             posting_month, unit_price, unit, driver_type, driver_raw)
            VALUES
            ('GA', '旅券申請費用 Chi phi lam ho chieu', 'GA', 5005246286, 6005246673, 6005246542, '取得月', 1900000, '/nguoi', 'headcount_all', 'manual event')
            """
        )
        conn.commit()

        AllocationEngine(conn)._process_allocation_rules()
        count = conn.execute("SELECT COUNT(*) FROM fact_input_data WHERE source LIKE 'alloc_%'").fetchone()[0]
        self.assertEqual(count, 0)
        conn.close()


class TestManualSpecialCosts(unittest.TestCase):
    def test_manual_special_cost_parser_and_export_to_explicit_form_row(self):
        conn = _mk_conn()
        cc_code = _seed_cc(conn)
        periods = get_fy_months(2027)

        tmpdir = _mk_tmpdir()
        try:
            csv_path = tmpdir / "special_costs_manual.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["cc_code", "period", "form_row", "account_code", "amount_vnd", "description"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "cc_code": str(cc_code),
                        "period": periods[0],
                        "form_row": "113",
                        "account_code": "5005246286",
                        "amount_vnd": "500",
                        "description": "manual row 113",
                    }
                )

            result = parse_manual_special_costs(conn, source_dir=str(tmpdir))
            self.assertEqual(result["inserted"], 1)

            template_path = Path(__file__).resolve().parents[1] / "docs" / "MP2027" / "FORM.xlsx"
            output_path = tmpdir / "out_special_cost.xlsx"
            ok = HubBuilder(conn, fiscal_year=2027).export_to_template(str(template_path), str(output_path), cc_code=cc_code)
            self.assertTrue(ok)

            workbook = openpyxl.load_workbook(output_path, data_only=False)
            try:
                ws = workbook[find_hub_sheet_name(workbook)]
                self.assertEqual(ws["F113"].value, 500)
                self.assertIsNone(ws["G137"].value)
                self.assertIsNone(ws["O138"].value)
                self.assertIsNone(ws["S200"].value)
            finally:
                workbook.close()
        finally:
            conn.close()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_recurring_admin_rows_use_previous_month_headcount_formulas(self):
        conn = _mk_conn()
        cc_code = _seed_cc(conn)
        periods = get_fy_months(2027)
        conn.execute(
            """
            INSERT INTO fact_input_data
            (source, period, amount_vnd, cc_code, account_code, description)
            VALUES
            ('ga_unit_price', ?, 100, 0, 0, '手洗い洗剤|headcount_per_person'),
            ('ga_unit_price', ?, 110, 0, 0, '手洗い洗剤|headcount_per_person'),
            ('manual', ?, 1, ?, 500001, 'seed')
            """,
            (periods[0], periods[1], periods[0], cc_code),
        )
        conn.commit()

        template_path = Path(__file__).resolve().parents[1] / "docs" / "MP2027" / "FORM.xlsx"
        tmpdir = _mk_tmpdir()
        try:
            output_path = tmpdir / "out_prev_month_formula.xlsx"
            ok = HubBuilder(conn, fiscal_year=2027).export_to_template(str(template_path), str(output_path), cc_code=cc_code)
            self.assertTrue(ok)

            workbook = openpyxl.load_workbook(output_path, data_only=False)
            try:
                ws = workbook[find_hub_sheet_name(workbook)]
                self.assertEqual(ws["F93"].value, "=SUM(F$24:F$25)*100")
                self.assertEqual(ws["G93"].value, "=SUM(F$24:F$25)*110")
            finally:
                workbook.close()
        finally:
            conn.close()
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestHubBuilderExport(unittest.TestCase):
    def test_export_preserves_form_layout_and_appends_unmapped_rows(self):
        conn = _mk_conn()
        cc_code = _seed_cc(conn)
        periods = get_fy_months(2027)
        conn.execute(
            """
            INSERT INTO dim_accounts
            (code, name_jp, name_vn, group_name, group_vn, mfg_code, ga_code, sales_code)
            VALUES (500001, 'TEST_ACC', 'Test Account', 'G', 'GV', 500001, 600001, 700001)
            """
        )
        conn.execute(
            """
            INSERT INTO fact_input_data
            (source, period, amount_vnd, cc_code, account_code, description)
            VALUES
            ('manual', ?, 123, ?, 500001, 'desc'),
            ('manual', ?, 456, ?, 500001, 'desc')
            """,
            (periods[0], cc_code, periods[1], cc_code),
        )
        conn.commit()

        template_path = Path(__file__).resolve().parents[1] / "docs" / "MP2027" / "FORM.xlsx"
        tmpdir = _mk_tmpdir()
        try:
            output_path = tmpdir / "out.xlsx"
            builder = HubBuilder(conn, fiscal_year=2027)
            ok = builder.export_to_template(str(template_path), str(output_path), cc_code=cc_code)
            self.assertTrue(ok)

            workbook = openpyxl.load_workbook(output_path, data_only=False)
            try:
                ws = workbook[find_hub_sheet_name(workbook)]
                self.assertEqual(ws["B5"].value, cc_code)
                self.assertEqual(ws["B200"].value, 500001)
                self.assertEqual(ws["S200"].value, "desc")
                self.assertEqual(ws["F200"].value, 123)
                self.assertEqual(ws["G200"].value, 456)
                self.assertEqual(ws["R200"].value, "=SUM(F200:Q200)")
            finally:
                workbook.close()
        finally:
            conn.close()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_export_routes_fixed_items_to_form_rows_and_clears_sample_rows(self):
        conn = _mk_conn()
        cc_code = _seed_cc(conn)
        periods = get_fy_months(2027)
        conn.executemany(
            """
            INSERT INTO dim_accounts
            (code, name_jp, name_vn, group_name, group_vn, mfg_code, ga_code, sales_code)
            VALUES (?, 'TEST_ACC', 'Test Account', 'G', 'GV', ?, ?, ?)
            """,
            [
                (5004086291, 5004086291, 6004086651, 6004086551),
                (5005246281, 5005246281, 6005146627, 6005146541),
            ],
        )
        conn.execute(
            """
            INSERT INTO fact_input_data
            (source, period, amount_vnd, cc_code, account_code, description)
            VALUES
            ('alloc_238', ?, 111, ?, 5004086291, 'Alloc: 社員旅行 Du lịch công ty'),
            ('alloc_240', ?, 222, ?, 5004086291, 'Alloc: 京セラフェスティバルLễ hội Kyocera'),
            ('alloc_201', ?, 333, ?, 5005246281, 'Alloc: 社員証（新入社員用・再発行時、写真含む）\nThẻ từ chấm công + ảnh'),
            ('manual', ?, 444, ?, 500001, 'desc')
            """,
            (periods[1], cc_code, periods[5], cc_code, periods[3], cc_code, periods[0], cc_code),
        )
        conn.commit()

        template_path = Path(__file__).resolve().parents[1] / "docs" / "MP2027" / "FORM.xlsx"
        tmpdir = _mk_tmpdir()
        try:
            output_path = tmpdir / "out_fixed_rows.xlsx"
            builder = HubBuilder(conn, fiscal_year=2027)
            ok = builder.export_to_template(str(template_path), str(output_path), cc_code=cc_code)
            self.assertTrue(ok)

            workbook = openpyxl.load_workbook(output_path, data_only=False)
            try:
                ws = workbook[find_hub_sheet_name(workbook)]
                self.assertEqual(ws["G66"].value, 111)
                self.assertEqual(ws["K66"].value, 222)
                self.assertEqual(ws["I79"].value, 333)
                self.assertIsNone(ws["F67"].value)
                self.assertEqual(ws["S200"].value, "desc")
            finally:
                workbook.close()
        finally:
            conn.close()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_it_system_row_prefers_detail_formula_terms(self):
        conn = _mk_conn()
        cc_code = _seed_cc(conn)
        periods = get_fy_months(2027)
        conn.execute(
            """
            INSERT INTO fact_input_data
            (source, period, amount_vnd, amount_usd, cc_code, account_code, description)
            VALUES
            ('it_sim', ?, 0, 31.9, ?, 5005246282, 'it_sim|component_term|vpn|qty=10|unit_usd=3.19'),
            ('it_sim', ?, 0, 230.2, ?, 5005246282, 'it_sim|component_term|mail|qty=20|unit_usd=11.51'),
            ('it_sim', ?, 0, 60.04, ?, 5005246282, 'it_sim|component_term|mes|qty=2|unit_usd=30.02'),
            ('it_sim', ?, 0, 45, ?, 5005246282, 'it_sim|component_term|vps|qty=20|unit_usd=2.25'),
            ('it_sim', ?, 9645870, 0, ?, 5005246282, 'it_sim|system_usage_total')
            """,
            (periods[0], cc_code, periods[0], cc_code, periods[0], cc_code, periods[0], cc_code, periods[0], cc_code),
        )
        conn.commit()

        template_path = Path(__file__).resolve().parents[1] / "docs" / "MP2027" / "FORM.xlsx"
        tmpdir = _mk_tmpdir()
        try:
            output_path = tmpdir / "out_it_formula.xlsx"
            ok = HubBuilder(conn, fiscal_year=2027).export_to_template(str(template_path), str(output_path), cc_code=cc_code)
            self.assertTrue(ok)

            workbook = openpyxl.load_workbook(output_path, data_only=False)
            try:
                ws = workbook[find_hub_sheet_name(workbook)]
                self.assertEqual(ws["B75"].value, 5005246282)
                self.assertEqual(ws["F75"].value, "=ROUND((10*3.19+20*11.51+2*30.02+20*2.25)*$B$2,0)")
            finally:
                workbook.close()
        finally:
            conn.close()
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
