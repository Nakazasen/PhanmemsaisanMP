import csv
import sqlite3
import unittest
from pathlib import Path
import shutil
import uuid

import openpyxl

from src.db.loader import _apply_mp2026_reference_unit_price, _parse_unit_price
from src.db.schema import create_schema, init_sys_params
from src.engine.allocator import AllocationEngine
from src.engine.hub_builder import HubBuilder
from src.parsers.birthday import parse_birthday_workbook
from src.parsers.manual_event_drivers import parse_manual_event_drivers
from src.parsers.manual_headcount import parse_manual_headcount
from src.parsers.manual_special_costs import parse_manual_special_costs
from src.parsers.nnn_paperwork import parse_nnn_paperwork
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

    def test_mp2026_reference_unit_price_fills_zero_rule_prices(self):
        self.assertEqual(_apply_mp2026_reference_unit_price("月餅 Bánh Trung Thu", 0), 56000.0)
        self.assertEqual(_apply_mp2026_reference_unit_price("運動会 Đại hội thể thao", 0), 107000.0)
        self.assertEqual(_apply_mp2026_reference_unit_price("運動会 Đại hội thể thao", 123), 123.0)

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
    def test_manual_event_driver_parser_exports_formula_to_explicit_row(self):
        conn = _mk_conn()
        cc_code = _seed_cc(conn)
        conn.execute(
            "INSERT INTO dim_accounts (code, name_jp, name_vn) VALUES (5004086291, '福利厚生費', 'Welfare')"
        )
        conn.commit()
        period = get_fy_months(2027)[1]

        tmpdir = _mk_tmpdir()
        try:
            csv_path = tmpdir / "event_drivers_manual.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "cc_code",
                        "period",
                        "event_name",
                        "count",
                        "unit_price",
                        "amount_vnd",
                        "account_code",
                        "form_row",
                        "description",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "cc_code": str(cc_code),
                        "period": period,
                        "event_name": "no_trip_gift",
                        "count": "3",
                        "unit_price": "4000",
                        "amount_vnd": "",
                        "account_code": "5004086291",
                        "form_row": "137",
                        "description": "Manual event count",
                    }
                )

            result = parse_manual_event_drivers(conn, source_dir=str(tmpdir))
            self.assertEqual(result["inserted"], 1)
            self.assertEqual(result["errors"], 0)

            template_path = Path(__file__).resolve().parents[1] / "docs" / "MP2027" / "FORM.xlsx"
            output_path = tmpdir / "out_manual_event.xlsx"
            ok = HubBuilder(conn, fiscal_year=2027).export_to_template(str(template_path), str(output_path), cc_code=cc_code)
            self.assertTrue(ok)

            workbook = openpyxl.load_workbook(output_path, data_only=False)
            try:
                ws = workbook[find_hub_sheet_name(workbook)]
                self.assertEqual(ws["B137"].value, 5004086291)
                self.assertEqual(ws["G137"].value, "=3*4000")
                self.assertEqual(ws["S137"].value, "出向者の書類申請費/Chi phí làm giấy tờ cho người biệt phái")
            finally:
                workbook.close()
        finally:
            conn.close()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_manual_travel_event_driver_posts_may_to_row_66(self):
        conn = _mk_conn()
        cc_code = _seed_cc(conn, code=1412000089)
        conn.execute(
            "INSERT INTO dim_accounts (code, name_jp, name_vn) VALUES (5004086291, '福利厚生費', 'Welfare')"
        )
        conn.commit()
        period = "202705"

        tmpdir = _mk_tmpdir()
        try:
            csv_path = tmpdir / "event_drivers_manual.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "cc_code",
                        "target_month",
                        "event_name",
                        "event_type",
                        "count",
                        "unit_price",
                        "account_code",
                        "row",
                        "note",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "cc_code": str(cc_code),
                        "target_month": period,
                        "event_name": "社員旅行 Du lịch công ty",
                        "event_type": "month_specific_driver",
                        "count": "111",
                        "unit_price": "1874000",
                        "account_code": "5004086291",
                        "row": "66",
                        "note": "Company trip manual driver for May",
                    }
                )

            result = parse_manual_event_drivers(conn, source_dir=str(tmpdir))
            self.assertEqual(result["inserted"], 1)
            self.assertEqual(result["errors"], 0)

            fact_row = conn.execute(
                """
                SELECT source, period, cc_code, account_code, form_row, amount_vnd, description
                FROM fact_input_data
                WHERE source = 'manual_event_driver'
                """
            ).fetchone()
            self.assertIsNotNone(fact_row)
            self.assertEqual(fact_row["period"], "202705")
            self.assertEqual(str(fact_row["cc_code"]), "1412000089")
            self.assertEqual(int(fact_row["account_code"]), 5004086291)
            self.assertEqual(int(fact_row["form_row"]), 66)
            self.assertEqual(float(fact_row["amount_vnd"]), 208014000.0)
            self.assertIn("formula_expr=111*1874000", fact_row["description"])

            template_path = Path(__file__).resolve().parents[1] / "docs" / "MP2027" / "FORM.xlsx"
            output_path = tmpdir / "out_manual_travel_event.xlsx"
            ok = HubBuilder(conn, fiscal_year=2027).export_to_template(str(template_path), str(output_path), cc_code=cc_code)
            self.assertTrue(ok)

            workbook = openpyxl.load_workbook(output_path, data_only=False)
            try:
                ws = workbook[find_hub_sheet_name(workbook)]
                self.assertEqual(ws["B66"].value, 5004086291)
                self.assertEqual(ws["G66"].value, "=111*1874000")
                month_cells = ["F66", "H66", "I66", "J66", "K66", "L66", "M66", "N66", "O66", "P66", "Q66"]
                self.assertNotIn("=111*1874000", [ws[cell].value for cell in month_cells])
            finally:
                workbook.close()
        finally:
            conn.close()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_manual_event_driver_without_form_row_appends_with_formula(self):
        conn = _mk_conn()
        cc_code = _seed_cc(conn)
        conn.execute(
            "INSERT INTO dim_accounts (code, name_jp, name_vn) VALUES (5004086291, '福利厚生費', 'Welfare')"
        )
        conn.commit()
        period = get_fy_months(2027)[0]

        tmpdir = _mk_tmpdir()
        try:
            csv_path = tmpdir / "event_drivers_manual.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "cc_code",
                        "period",
                        "event_name",
                        "count",
                        "unit_price",
                        "amount_vnd",
                        "account_code",
                        "form_row",
                        "description",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "cc_code": str(cc_code),
                        "period": period,
                        "event_name": "other",
                        "count": "2",
                        "unit_price": "5000",
                        "amount_vnd": "",
                        "account_code": "5004086291",
                        "form_row": "",
                        "description": "Append manual event",
                    }
                )

            result = parse_manual_event_drivers(conn, source_dir=str(tmpdir))
            self.assertEqual(result["inserted"], 1)
            self.assertEqual(result["errors"], 0)

            template_path = Path(__file__).resolve().parents[1] / "docs" / "MP2027" / "FORM.xlsx"
            output_path = tmpdir / "out_manual_event_append.xlsx"
            ok = HubBuilder(conn, fiscal_year=2027).export_to_template(str(template_path), str(output_path), cc_code=cc_code)
            self.assertTrue(ok)

            workbook = openpyxl.load_workbook(output_path, data_only=False)
            try:
                ws = workbook[find_hub_sheet_name(workbook)]
                self.assertEqual(ws["B200"].value, 5004086291)
                self.assertEqual(ws["F200"].value, "=2*5000")
                self.assertEqual(ws["S200"].value, "other: Append manual event")
            finally:
                workbook.close()
        finally:
            conn.close()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_manual_event_driver_template_includes_friendly_schema_columns(self):
        from src.parsers.manual_event_drivers import ensure_manual_event_drivers_template

        tmpdir = _mk_tmpdir()
        try:
            csv_path = Path(ensure_manual_event_drivers_template(str(tmpdir), 2027))
            with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
                header = next(csv.reader(f))

            self.assertEqual(
                header,
                [
                    "cc_code",
                    "period",
                    "target_month",
                    "event_name",
                    "event_type",
                    "count",
                    "unit_price",
                    "amount_vnd",
                    "account_code",
                    "account_group",
                    "form_row",
                    "row",
                    "source_month",
                    "headcount_basis",
                    "description",
                    "note",
                ],
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_manual_event_driver_accepts_new_alias_columns(self):
        conn = _mk_conn()
        cc_code = _seed_cc(conn)
        conn.execute(
            "INSERT INTO dim_accounts (code, name_jp, name_vn) VALUES (5004086291, '福利厚生費', 'Welfare')"
        )
        conn.commit()
        period = get_fy_months(2027)[2]

        tmpdir = _mk_tmpdir()
        try:
            csv_path = tmpdir / "event_drivers_manual.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "cc_code",
                        "target_month",
                        "event_name",
                        "event_type",
                        "count",
                        "unit_price",
                        "account_code",
                        "row",
                        "note",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "cc_code": str(cc_code),
                        "target_month": period,
                        "event_name": "month_specific_driver",
                        "event_type": "manual_count_unit_price",
                        "count": "4",
                        "unit_price": "2500",
                        "account_code": "5004086291",
                        "row": "137",
                        "note": "Alias driven event",
                    }
                )

            result = parse_manual_event_drivers(conn, source_dir=str(tmpdir))
            self.assertEqual(result["inserted"], 1)
            self.assertEqual(result["errors"], 0)

            row = conn.execute(
                """
                SELECT period, amount_vnd, form_row, description
                FROM fact_input_data
                WHERE source = 'manual_event_driver'
                """
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["period"], period)
            self.assertEqual(float(row["amount_vnd"]), 10000.0)
            self.assertEqual(int(row["form_row"]), 137)
            self.assertEqual(row["description"], "month_specific_driver: Alias driven event|formula_expr=4*2500")
        finally:
            conn.close()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_manual_event_driver_rejects_conflicting_alias_values(self):
        conn = _mk_conn()
        cc_code = _seed_cc(conn)
        conn.execute(
            "INSERT INTO dim_accounts (code, name_jp, name_vn) VALUES (5004086291, '福利厚生費', 'Welfare')"
        )
        conn.commit()
        periods = get_fy_months(2027)

        tmpdir = _mk_tmpdir()
        try:
            csv_path = tmpdir / "event_drivers_manual.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "cc_code",
                        "period",
                        "target_month",
                        "event_name",
                        "count",
                        "unit_price",
                        "account_code",
                        "form_row",
                        "row",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "cc_code": str(cc_code),
                        "period": periods[0],
                        "target_month": periods[1],
                        "event_name": "period conflict",
                        "count": "1",
                        "unit_price": "100",
                        "account_code": "5004086291",
                        "form_row": "46",
                        "row": "46",
                    }
                )
                writer.writerow(
                    {
                        "cc_code": str(cc_code),
                        "period": periods[0],
                        "target_month": periods[0],
                        "event_name": "row conflict",
                        "count": "1",
                        "unit_price": "100",
                        "account_code": "5004086291",
                        "form_row": "46",
                        "row": "47",
                    }
                )

            result = parse_manual_event_drivers(conn, source_dir=str(tmpdir))
            self.assertEqual(result["inserted"], 0)
            self.assertEqual(result["errors"], 2)
        finally:
            conn.close()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_manual_event_driver_validates_event_type(self):
        conn = _mk_conn()
        cc_code = _seed_cc(conn)
        conn.execute(
            "INSERT INTO dim_accounts (code, name_jp, name_vn) VALUES (5004086291, '福利厚生費', 'Welfare')"
        )
        conn.commit()
        period = get_fy_months(2027)[0]

        tmpdir = _mk_tmpdir()
        try:
            csv_path = tmpdir / "event_drivers_manual.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "cc_code",
                        "period",
                        "event_name",
                        "event_type",
                        "amount_vnd",
                        "account_code",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "cc_code": str(cc_code),
                        "period": period,
                        "event_name": "manual amount",
                        "event_type": "manual_amount",
                        "amount_vnd": "1234",
                        "account_code": "5004086291",
                    }
                )
                writer.writerow(
                    {
                        "cc_code": str(cc_code),
                        "period": period,
                        "event_name": "bad type",
                        "event_type": "unknown_event",
                        "amount_vnd": "5678",
                        "account_code": "5004086291",
                    }
                )

            result = parse_manual_event_drivers(conn, source_dir=str(tmpdir))
            self.assertEqual(result["inserted"], 1)
            self.assertEqual(result["errors"], 1)
        finally:
            conn.close()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_nnn_paperwork_workbook_parser_exports_to_row_137(self):
        conn = _mk_conn()
        cc_code = _seed_cc(conn)

        tmpdir = _mk_tmpdir()
        try:
            workbook_path = tmpdir / "Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx"
            workbook = openpyxl.Workbook()
            ws = workbook.active
            ws.title = "FY2027"
            ws.cell(row=2, column=4, value="Mã costcenter")
            ws.cell(row=2, column=5, value="Mã tài khoản")
            ws.cell(row=2, column=6, value="2026/04")
            ws.cell(row=2, column=7, value="2026/05")
            ws.cell(row=3, column=2, value="VN000001")
            ws.cell(row=3, column=3, value="TEST USER")
            ws.cell(row=3, column=4, value=cc_code)
            ws.cell(row=3, column=5, value=5005246286)
            ws.cell(row=3, column=6, value=1000)
            ws.cell(row=3, column=7, value=2000)
            workbook.save(workbook_path)
            workbook.close()

            result = parse_nnn_paperwork(conn, source_dir=str(tmpdir))
            self.assertEqual(result["inserted"], 2)
            self.assertEqual(result["errors"], 0)

            template_path = Path(__file__).resolve().parents[1] / "docs" / "MP2027" / "FORM.xlsx"
            output_path = tmpdir / "out_nnn_workbook.xlsx"
            ok = HubBuilder(conn, fiscal_year=2027).export_to_template(str(template_path), str(output_path), cc_code=cc_code)
            self.assertTrue(ok)

            workbook = openpyxl.load_workbook(output_path, data_only=False)
            try:
                ws = workbook[find_hub_sheet_name(workbook)]
                self.assertEqual(ws["B137"].value, 5005246286)
                self.assertEqual(ws["F137"].value, "=1000")
                self.assertEqual(ws["G137"].value, "=2000")
            finally:
                workbook.close()
        finally:
            conn.close()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_birthday_workbook_parser_exports_to_row_59(self):
        conn = _mk_conn()
        cc_code = _seed_cc(conn)

        tmpdir = _mk_tmpdir()
        try:
            workbook_path = tmpdir / "Sinh nhật MP FY2027.xlsx"
            workbook = openpyxl.Workbook()
            ws = workbook.active
            ws.title = "Sinh nhật MP FY2027"
            ws.cell(row=3, column=1, value="CostCenter")
            ws.cell(row=4, column=1, value=cc_code)
            ws.cell(row=4, column=2, value="TEST_CC")
            ws.cell(row=4, column=3, value=3)
            ws.cell(row=4, column=4, value=4)
            workbook.save(workbook_path)
            workbook.close()

            result = parse_birthday_workbook(conn, source_dir=str(tmpdir))
            self.assertEqual(result["inserted"], 2)
            self.assertEqual(result["errors"], 0)

            template_path = Path(__file__).resolve().parents[1] / "docs" / "MP2027" / "FORM.xlsx"
            output_path = tmpdir / "out_birthday_workbook.xlsx"
            ok = HubBuilder(conn, fiscal_year=2027).export_to_template(str(template_path), str(output_path), cc_code=cc_code)
            self.assertTrue(ok)

            workbook = openpyxl.load_workbook(output_path, data_only=False)
            try:
                ws = workbook[find_hub_sheet_name(workbook)]
                self.assertEqual(ws["B59"].value, 5004086291)
                self.assertEqual(ws["F59"].value, "=3*152000")
                self.assertEqual(ws["G59"].value, "=4*152000")
            finally:
                workbook.close()
        finally:
            conn.close()
            shutil.rmtree(tmpdir, ignore_errors=True)

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
                self.assertEqual(ws["F113"].value, "=500")
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
            ('ga_unit_price', ?, 100, 0, 0, 'gas|headcount_per_person'),
            ('ga_unit_price', ?, 110, 0, 0, 'gas|headcount_per_person'),
            ('ga_unit_price', ?, 120, 0, 0, 'gas|headcount_per_person'),
            ('ga_unit_price', ?, 200, 0, 0, '手洗い洗剤|headcount_per_person'),
            ('ga_unit_price', ?, 300, 0, 0, 'giay ve sinh|headcount_per_person'),
            ('ga_unit_price', ?, 400, 0, 0, 'cleaning|headcount_per_person'),
            ('manual', ?, 1, ?, 500001, 'seed')
            """,
            (
                periods[0],
                periods[1],
                periods[2],
                periods[1],
                periods[1],
                periods[2],
                periods[0],
                cc_code,
            ),
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
                # Gas: April uses April headcount; May uses April, not May; June uses May.
                self.assertEqual(ws["F46"].value, "=SUM(F$24:F$25)*100")
                self.assertEqual(ws["G46"].value, "=SUM(F$24:F$25)*110")
                self.assertNotIn("G$24:G$25", ws["G46"].value)
                self.assertEqual(ws["H46"].value, "=SUM(G$24:G$25)*120")

                # Other recurring administrative allocations follow the same previous-month pattern.
                self.assertEqual(ws["G48"].value, "=SUM(F$24:F$25)*200")
                self.assertEqual(ws["G49"].value, "=SUM(F$24:F$25)*300")
                self.assertEqual(ws["H51"].value, "=SUM(G$24:G$25)*400")
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
                self.assertEqual(ws["F200"].value, "=123")
                self.assertEqual(ws["G200"].value, "=456")
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
                self.assertEqual(ws["G66"].value, "=111")
                self.assertEqual(ws["K66"].value, "=222")
                self.assertEqual(ws["I79"].value, "=333")
                self.assertIsNone(ws["F67"].value)
                self.assertEqual(ws["S200"].value, "desc")
            finally:
                workbook.close()
        finally:
            conn.close()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_fixed_rows_follow_mp2027_form_layout(self):
        conn = _mk_conn()
        cc_code = _seed_cc(conn)
        periods = get_fy_months(2027)
        period = periods[0]
        conn.executemany(
            """
            INSERT INTO fact_input_data
            (source, period, amount_vnd, amount_usd, cc_code, account_code, form_row, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("facility", period, 0, 1.5, cc_code, 0, None, "depreciation_building"),
                ("facility", period, 0, 2.5, cc_code, 0, None, "depreciation_land"),
                ("fixed_assets", period, 0, 3.5, cc_code, 0, None, "fixed_assets_depr|asset"),
                ("facility", period, 0, 4.5, cc_code, 0, None, "interest_building"),
                ("facility", period, 0, 5.5, cc_code, 0, None, "interest_land"),
                ("fixed_assets", period, 0, 6.5, cc_code, 0, None, "fixed_assets_interest|asset"),
                ("facility", period, 100, 0, cc_code, 0, None, "electric"),
                ("facility", period, 200, 0, cc_code, 0, None, "water"),
                ("ga_unit_price", period, 300, 0, 0, 0, None, "gas|headcount_per_person"),
                ("ga_unit_price", period, 400, 0, 0, 0, None, "nuoc rua tay|headcount_per_person"),
                ("ga_unit_price", period, 500, 0, 0, 0, None, "giay ve sinh|headcount_per_person"),
                ("ga_unit_price", period, 600, 0, 0, 0, None, "cleaning|headcount_per_person"),
                ("alloc_health", period, 700, 0, cc_code, 5004086291, None, "Alloc: kham suc khoe (cho cnv nam)"),
                ("alloc_new_hire_health", period, 800, 0, cc_code, 5004086291, None, "Alloc: kham suc khoe khi tuyen dung"),
                ("alloc_birthday", period, 900, 0, cc_code, 5004086291, None, "Alloc: sinh nhat"),
                ("it_sim", period, 0, 30, cc_code, 5005246282, None, "it_sim|component_term|vpn|qty=10|unit_usd=3"),
                ("alloc_note_staff", period, 1000, 0, cc_code, 5005246288, None, "Alloc: note staff"),
                ("alloc_note_worker", period, 1100, 0, cc_code, 5005246288, None, "Alloc: note worker"),
                ("manual_special_cost", period, 1200, 0, cc_code, 5005246286, 137, "manual NNN"),
            ],
        )
        conn.commit()

        template_path = Path(__file__).resolve().parents[1] / "docs" / "MP2027" / "FORM.xlsx"
        tmpdir = _mk_tmpdir()
        try:
            output_path = tmpdir / "out_fixed_form_layout.xlsx"
            ok = HubBuilder(conn, fiscal_year=2027).export_to_template(str(template_path), str(output_path), cc_code=cc_code)
            self.assertTrue(ok)

            workbook = openpyxl.load_workbook(output_path, data_only=False)
            try:
                ws = workbook[find_hub_sheet_name(workbook)]
                expected_accounts = {
                    36: 5006016260,
                    37: 5006016261,
                    38: 5006016244,
                    40: 9114120007,
                    41: 9114120007,
                    42: 9114120007,
                    44: 5005066281,
                    45: 5005066282,
                    46: 5005056281,
                    48: 5005016372,
                    49: 5005016372,
                    51: 5005246286,
                    57: 5004086291,
                    58: 5004086291,
                    59: 5004086291,
                    75: 5005246282,
                    97: 5005246288,
                    98: 5005246288,
                    137: 5005246286,
                }
                for row_index, account_code in expected_accounts.items():
                    self.assertEqual(ws.cell(row_index, 2).value, account_code, f"B{row_index}")

                self.assertIn("Khấu hao (Nhà)", ws["S36"].value)
                self.assertIn("Lãi (Nhà)", ws["S40"].value)
                self.assertIn("Tiền điện", ws["S44"].value)
                self.assertIn("Hand wash", ws["S48"].value)
                self.assertIn("Chi phí khám sức khỏe hàng năm", ws["S57"].value)
                self.assertIn("Tiền sinh nhật", ws["S59"].value)
                self.assertIn("System Cost", ws["S75"].value)
                self.assertIn("Sổ tay", ws["S97"].value)
                self.assertIn("Chi phí làm giấy tờ", ws["S137"].value)

                self.assertEqual(ws["F36"].value, "=ROUND(1.5*$B$2,0)")
                self.assertEqual(ws["F37"].value, "=ROUND(2.5*$B$2,0)")
                self.assertEqual(ws["F38"].value, "=ROUND(3.5*$B$2,0)")
                self.assertEqual(ws["F40"].value, "=ROUND(4.5*$B$2,0)")
                self.assertEqual(ws["F41"].value, "=ROUND(5.5*$B$2,0)")
                self.assertEqual(ws["F42"].value, "=ROUND(6.5*$B$2,0)")
                self.assertEqual(ws["F44"].value, "=100")
                self.assertEqual(ws["F45"].value, "=200")
                self.assertEqual(ws["F46"].value, "=SUM(F$24:F$25)*300")
                self.assertEqual(ws["F48"].value, "=SUM(F$24:F$25)*400")
                self.assertEqual(ws["F49"].value, "=SUM(F$24:F$25)*500")
                self.assertEqual(ws["F51"].value, "=SUM(F$24:F$25)*600")
                self.assertEqual(ws["F57"].value, "=700")
                self.assertEqual(ws["F58"].value, "=800")
                self.assertEqual(ws["F59"].value, "=900")
                self.assertEqual(ws["F75"].value, "=ROUND((10*3)*$B$2,0)")
                self.assertEqual(ws["F97"].value, "=1000")
                self.assertEqual(ws["F98"].value, "=1100")
                self.assertEqual(ws["F137"].value, "=1200")
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

    def test_nnn_paperwork_exports_to_row_137_f_to_q(self):
        conn = _mk_conn()
        cc_code = _seed_cc(conn)
        periods = get_fy_months(2027)
        conn.execute(
            """
            INSERT INTO fact_input_data
            (source, period, amount_vnd, cc_code, account_code, form_row, scenario_id, description)
            VALUES
            ('nnn_paperwork', ?, 1000000, ?, 5005246286, 137, 'base', 'NNN paperwork: VN0001 Worker A|formula_expr=1000000'),
            ('nnn_paperwork', ?, 2000000, ?, 5005246286, 137, 'base', 'NNN paperwork: VN0001 Worker A|formula_expr=2000000'),
            ('nnn_paperwork', ?, 12000000, ?, 5005246286, 137, 'base', 'NNN paperwork: VN0001 Worker A|formula_expr=12000000')
            """,
            (periods[0], cc_code, periods[1], cc_code, periods[11], cc_code),
        )
        conn.commit()

        template_path = Path(__file__).resolve().parents[1] / "docs" / "MP2027" / "FORM.xlsx"
        tmpdir = _mk_tmpdir()
        try:
            output_path = tmpdir / "out_nnn_f_to_q.xlsx"
            ok = HubBuilder(conn, fiscal_year=2027).export_to_template(str(template_path), str(output_path), cc_code=cc_code)
            self.assertTrue(ok)

            workbook = openpyxl.load_workbook(output_path, data_only=False)
            try:
                ws = workbook[find_hub_sheet_name(workbook)]
                self.assertEqual(ws["B137"].value, 5005246286)
                self.assertEqual(ws["F137"].value, "=1000000")
                self.assertEqual(ws["G137"].value, "=2000000")
                self.assertEqual(ws["Q137"].value, "=12000000")
                self.assertEqual(ws["R137"].value, "=SUM(F137:Q137)")
                # Other months should be cleared/empty
                for month_col in ("H", "I", "J", "K", "L", "M", "N", "O", "P"):
                    self.assertIsNone(ws[f"{month_col}137"].value)
            finally:
                workbook.close()
        finally:
            conn.close()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_nnn_paperwork_sums_multiple_records_on_row_137(self):
        conn = _mk_conn()
        cc_code = _seed_cc(conn)
        periods = get_fy_months(2027)
        conn.execute(
            """
            INSERT INTO fact_input_data
            (source, period, amount_vnd, cc_code, account_code, form_row, scenario_id, description)
            VALUES
            ('nnn_paperwork', ?, 1000000, ?, 5005246286, 137, 'base', 'NNN paperwork: VN0001 Worker A|formula_expr=1000000'),
            ('nnn_paperwork', ?, 6000000, ?, 5005246286, 137, 'base', 'NNN paperwork: VN0002 Worker B|formula_expr=2000*3')
            """,
            (periods[0], cc_code, periods[0], cc_code),
        )
        conn.commit()

        template_path = Path(__file__).resolve().parents[1] / "docs" / "MP2027" / "FORM.xlsx"
        tmpdir = _mk_tmpdir()
        try:
            output_path = tmpdir / "out_nnn_sum.xlsx"
            ok = HubBuilder(conn, fiscal_year=2027).export_to_template(str(template_path), str(output_path), cc_code=cc_code)
            self.assertTrue(ok)

            workbook = openpyxl.load_workbook(output_path, data_only=False)
            try:
                ws = workbook[find_hub_sheet_name(workbook)]
                self.assertEqual(ws["B137"].value, 5005246286)
                self.assertEqual(ws["F137"].value, "=1000000+2000*3")
            finally:
                workbook.close()
        finally:
            conn.close()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_nnn_paperwork_does_not_export_unknown_cost_center(self):
        conn = _mk_conn()
        cc_code_target = _seed_cc(conn, code=1412000004)
        cc_code_other = _seed_cc(conn, code=1412000018)
        periods = get_fy_months(2027)
        conn.execute(
            """
            INSERT INTO fact_input_data
            (source, period, amount_vnd, cc_code, account_code, form_row, scenario_id, description)
            VALUES
            ('nnn_paperwork', ?, 1000000, ?, 5005246286, 137, 'base', 'NNN paperwork: VN0001 Worker A|formula_expr=1000000')
            """,
            (periods[0], cc_code_other),
        )
        conn.commit()

        # Seed at least one dummy record for the target CC so that HubBuilder knows the CC has fact input data
        conn.execute(
            """
            INSERT INTO fact_input_data
            (source, period, amount_vnd, cc_code, account_code, form_row, scenario_id, description)
            VALUES
            ('dummy', ?, 1, ?, 500001, 200, 'base', 'dummy')
            """,
            (periods[0], cc_code_target),
        )
        conn.commit()

        template_path = Path(__file__).resolve().parents[1] / "docs" / "MP2027" / "FORM.xlsx"
        tmpdir = _mk_tmpdir()
        try:
            output_path = tmpdir / "out_nnn_other_cc.xlsx"
            ok = HubBuilder(conn, fiscal_year=2027).export_to_template(str(template_path), str(output_path), cc_code=cc_code_target)
            self.assertTrue(ok)

            workbook = openpyxl.load_workbook(output_path, data_only=False)
            try:
                ws = workbook[find_hub_sheet_name(workbook)]
                self.assertIsNone(ws["F137"].value)
            finally:
                workbook.close()
        finally:
            conn.close()
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
