import sqlite3
import unittest

from src.db.schema import create_schema, init_sys_params
from src.engine.allocator import AllocationEngine
from src.engine.hub_builder import HubBuilder
from src.utils.excel_helpers import get_fy_months


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


def _insert_rule(conn, posting_month, driver_type, unit_price=100, rid_label="TEST", driver_raw=None):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO map_allocation_rules
        (source_dept, item_name, account_name, mfg_account, ga_account, sales_account,
         posting_month, unit_price, unit, driver_type, driver_raw)
        VALUES ('QA', ?, 'Test Account', 500001, 600001, 700001, ?, ?, '/unit', ?, ?)
        """,
        (rid_label, posting_month, float(unit_price), driver_type, driver_raw if driver_raw is not None else posting_month),
    )
    conn.commit()
    return cur.lastrowid


def _seed_hc(conn, cc_code, values, source="department_plan", driver_kind="all"):
    fy_months = get_fy_months(2027)
    for i, val in enumerate(values):
        period = fy_months[i]
        if driver_kind == "staff":
            staff, worker = float(val), 0.0
        elif driver_kind == "worker":
            staff, worker = 0.0, float(val)
        else:
            # Keep split simple for tests
            staff, worker = float(val), 0.0
        conn.execute(
            """
            INSERT INTO fact_monthly_headcount
            (period, cc_code, headcount_all, headcount_staff, headcount_worker, source, description)
            VALUES (?, ?, ?, ?, ?, ?, 'test')
            ON CONFLICT(period, cc_code, source) DO UPDATE SET
                headcount_all=excluded.headcount_all,
                headcount_staff=excluded.headcount_staff,
                headcount_worker=excluded.headcount_worker
            """,
            (period, cc_code, staff + worker, staff, worker, source),
        )
    conn.commit()


def _set_working_days(conn, values):
    fy_months = get_fy_months(2027)
    for i, v in enumerate(values):
        conn.execute(
            "INSERT OR REPLACE INTO sys_params (key, value, description) VALUES (?, ?, 'test')",
            (f"working_days_{fy_months[i]}", str(float(v))),
        )
    conn.commit()


def _alloc_periods(conn, rule_id):
    rows = conn.execute(
        "SELECT period, SUM(amount_vnd) AS amount FROM fact_input_data WHERE source=? GROUP BY period ORDER BY period",
        (f"alloc_{rule_id}",),
    ).fetchall()
    return {r["period"]: float(r["amount"]) for r in rows}


def _missing_areas(conn, cc_code):
    rows = conn.execute(
        """
        SELECT area, COUNT(*) AS count
        FROM fact_missing_inputs
        WHERE source='allocator' AND CAST(cc_code AS TEXT)=?
        GROUP BY area
        ORDER BY area
        """,
        (str(cc_code),),
    ).fetchall()
    return {row["area"]: int(row["count"]) for row in rows}


class TestPostingMonthLogic(unittest.TestCase):
    def test_fixed_month_posts_only_in_target_month(self):
        conn = _mk_conn()
        cc = _seed_cc(conn)
        _seed_hc(conn, cc, [10] * 12)
        rid = _insert_rule(conn, "7月", "headcount_all", unit_price=100)
        months = get_fy_months(2027)
        month_7 = next(p for p in months if p.endswith("07"))

        AllocationEngine(conn)._process_allocation_rules()
        periods = _alloc_periods(conn, rid)
        self.assertEqual(set(periods.keys()), {month_7})
        self.assertEqual(periods[month_7], 1000.0)
        conn.close()

    def test_dash_posting_month_records_missing_manual_event_input(self):
        conn = _mk_conn()
        cc = _seed_cc(conn)
        _seed_hc(conn, cc, [10] * 12)
        rid = _insert_rule(conn, "-", "headcount_all", unit_price=100, rid_label="application-month event")

        AllocationEngine(conn)._process_allocation_rules()

        self.assertEqual(_alloc_periods(conn, rid), {})
        self.assertEqual(_missing_areas(conn, cc), {"manual_event_driver": 1})
        conn.close()

    def test_actual_participant_fixed_month_records_missing_manual_driver(self):
        conn = _mk_conn()
        cc = _seed_cc(conn)
        _seed_hc(conn, cc, [10] * 12)
        rid = _insert_rule(
            conn,
            "5月",
            "headcount_all",
            unit_price=100,
            rid_label="company trip",
            driver_raw="実際の参加人数で実施月に振替",
        )

        AllocationEngine(conn)._process_allocation_rules()

        self.assertEqual(_alloc_periods(conn, rid), {})
        self.assertEqual(_missing_areas(conn, cc), {"manual_distribution_driver": 1})
        conn.close()

    def test_event_month_posting_types_use_positive_delta(self):
        # 入社月, 配布月, 申請月, 取得月 use event delta logic.
        posting_types = ["入社月", "配布月", "申請月", "取得月"]
        for ptype in posting_types:
            conn = _mk_conn()
            cc = _seed_cc(conn)
            # Positive deltas: +2 in 202605, +3 in 202607
            _seed_hc(conn, cc, [10, 12, 12, 15, 15, 15, 15, 15, 15, 15, 15, 15])
            rid = _insert_rule(conn, ptype, "headcount_all", unit_price=100, rid_label=ptype)
            AllocationEngine(conn)._process_allocation_rules()
            periods = _alloc_periods(conn, rid)
            months = get_fy_months(2027)
            self.assertEqual(periods.get(months[1]), 200.0)
            self.assertEqual(periods.get(months[3]), 300.0)
            self.assertNotIn(months[0], periods)
            conn.close()

    def test_monthly_new_hire_driver_raw_uses_positive_delta_not_total_headcount(self):
        """配布数 rules require manual distribution counts and are now skipped."""
        conn = _mk_conn()
        cc = _seed_cc(conn)
        _seed_hc(conn, cc, [4, 4, 4, 4, 4, 4, 4, 4, 31, 2, 2, 3])
        rid = _insert_rule(
            conn,
            "\u8c48\u53d6\u6026",
            "headcount_all",
            unit_price=100,
            rid_label="hat monthly issue",
            driver_raw="\u524d\u670816\u65e5\u304b\u3089\u5f53\u670815\u65e5\u307e\u3067\u306e\u65b0\u5165\u793e\u54e1\u3068\u652f\u7d66\u4f9d\u983c\u8005\u306e\u914d\u5e03\u6570\u306f\u5f53\u6708\u632f\u66ff",
        )

        AllocationEngine(conn)._process_allocation_rules()

        periods = _alloc_periods(conn, rid)
        # 配布数 in driver_raw → rule is skipped, no auto-allocation
        self.assertEqual(periods, {})
        conn.close()

    def test_monthly_new_hire_driver_raw_with_no_positive_delta_creates_no_amount(self):
        conn = _mk_conn()
        cc = _seed_cc(conn)
        _seed_hc(conn, cc, [4, 4, 4, 4, 4, 4, 4, 4, 4, 3, 3, 3])
        rid = _insert_rule(
            conn,
            "豈取怦",
            "headcount_all",
            unit_price=100,
            rid_label="uniform monthly issue",
            driver_raw="\u65b0\u5165\u793e\u54e1 \u914d\u5c5e\u4eba\u6570",
        )

        AllocationEngine(conn)._process_allocation_rules()

        self.assertEqual(_alloc_periods(conn, rid), {})
        conn.close()

    def test_new_hire_photo_only_rule_is_not_auto_allocated(self):
        conn = _mk_conn()
        cc = _seed_cc(conn)
        _seed_hc(conn, cc, [1, 2, 2, 2, 2, 2, 2, 2, 31, 31, 31, 31])
        rid = _insert_rule(
            conn,
            "\u914d\u5e03\u6708",
            "headcount_all",
            unit_price=500,
            rid_label="\u793e\u54e1\u8a3c\u7528\u5199\u771f\u306e\u307f",
            driver_raw="\u914d\u5c5e\u4eba\u6570\u3067\u5165\u793e\u6708\u306b\u632f\u66ff",
        )

        AllocationEngine(conn)._process_allocation_rules()

        self.assertEqual(_alloc_periods(conn, rid), {})
        conn.close()

    def test_next_month_rule_posts_in_month_after_delta(self):
        conn = _mk_conn()
        cc = _seed_cc(conn)
        _seed_hc(conn, cc, [10, 12, 12, 15, 15, 15, 15, 15, 15, 15, 15, 15])
        rid = _insert_rule(conn, "入社月の翌月", "headcount_all", unit_price=100)
        months = get_fy_months(2027)

        AllocationEngine(conn)._process_allocation_rules()
        periods = _alloc_periods(conn, rid)
        # Delta at 202605(+2) appears at 202606; delta at 202607(+3) appears at 202608.
        self.assertEqual(periods.get(months[2]), 200.0)
        self.assertEqual(periods.get(months[4]), 300.0)
        self.assertNotIn(months[1], periods)
        conn.close()

    def test_mixed_event_and_fixed_month_rule_adds_delta_and_fixed_month_headcount(self):
        conn = _mk_conn()
        cc = _seed_cc(conn)
        months = get_fy_months(2027)
        headcounts = {
            "202603": 22,
            months[0]: 22,
            months[1]: 22,
            months[2]: 26,
            months[3]: 27,
            months[4]: 27,
            months[5]: 27,
            months[6]: 27,
            months[7]: 27,
            months[8]: 27,
            months[9]: 28,
            months[10]: 28,
            months[11]: 28,
        }
        for period, value in headcounts.items():
            conn.execute(
                """
                INSERT INTO fact_monthly_headcount
                (period, cc_code, headcount_all, headcount_staff, headcount_worker, source, description)
                VALUES (?, ?, ?, ?, 0, ?, 'mixed event fixed month')
                """,
                (period, cc, value, value, "manual" if period == "202603" else "department_plan"),
            )
        rid = _insert_rule(
            conn,
            "入社月\n入社月の翌月\n11月",
            "headcount_all",
            unit_price=760,
            rid_label="pocket calendar",
        )

        AllocationEngine(conn)._process_allocation_rules()

        periods = _alloc_periods(conn, rid)
        self.assertEqual(
            periods,
            {
                months[2]: 4 * 760.0,
                months[3]: 1 * 760.0,
                months[7]: 27 * 760.0,
                months[9]: 1 * 760.0,
            },
        )
        conn.close()

    def test_separate_count_admin_events_create_missing_count_placeholder(self):
        separate_count_items = [
            "FY2027部門方針発表会後の決起コンパ",
            "社員旅行不参加対象者へのギフト贈呈 Quà tặng cho CNV không thể tham gia du lịch",
            "10年勤続記念コンパ",
            "10年勤続記念品",
        ]
        for item_name in separate_count_items:
            conn = _mk_conn()
            cc = _seed_cc(conn)
            _seed_hc(conn, cc, [10] * 12)
            rid = _insert_rule(conn, "6月", "headcount_all", unit_price=100, rid_label=item_name)

            AllocationEngine(conn)._process_allocation_rules()

            periods = _alloc_periods(conn, rid)
            self.assertEqual(periods, {"202606": 0.0}, item_name)
            row = conn.execute(
                "SELECT form_row, description FROM fact_input_data WHERE source=?",
                (f"alloc_{rid}",),
            ).fetchone()
            self.assertIsNone(row["form_row"])
            self.assertIn("formula_expr=0*100", row["description"])
            self.assertIn("missing_separate_count=1", row["description"])
            self.assertEqual(_missing_areas(conn, cc), {})
            conn.close()

    def test_my_episode_philosophy_creates_manual_count_placeholder_for_july(self):
        conn = _mk_conn()
        cc = _seed_cc(conn)
        _seed_hc(conn, cc, [22, 23, 23, 24, 24, 24, 25, 26, 26, 26, 26, 26])
        rid = _insert_rule(
            conn,
            "7月",
            "headcount_worker",
            unit_price=100000,
            rid_label='マイエピソード ～フィロソフィの実践～参加賞\nGiải tham gia "Cảm nghĩ về triết lý kinh doanh"',
            driver_raw="対象者は3月31日の前の入社員です",
        )

        AllocationEngine(conn)._process_allocation_rules()

        self.assertEqual(_alloc_periods(conn, rid), {"202607": 0.0})
        row = conn.execute(
            "SELECT description FROM fact_input_data WHERE source=?",
            (f"alloc_{rid}",),
        ).fetchone()
        self.assertNotIn("source_month=202604", row["description"])
        self.assertNotIn("driver_value=22", row["description"])
        self.assertIn("formula_expr=0*100000", row["description"])
        self.assertIn("missing_separate_count=1", row["description"])
        self.assertIn("status=NEEDS_SEPARATE_COUNT", row["description"])
        self.assertEqual(_missing_areas(conn, cc), {})
        conn.close()

    def test_mooncake_uses_total_september_headcount(self):
        conn = _mk_conn()
        cc = _seed_cc(conn)
        _seed_hc(conn, cc, [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21])
        rid = _insert_rule(
            conn,
            "9月",
            "headcount_staff",
            unit_price=56000,
            rid_label="月餅 Bánh Trung Thu",
            driver_raw=(
                "配布数で引渡し月に振替 / Phân bổ theo số lượng phát thực tế. "
                "Trường hợp vào ngày phát bánh có người mới vào, vẫn thuộc đối tượng nhận bánh"
            ),
        )

        AllocationEngine(conn)._process_allocation_rules()

        self.assertEqual(_alloc_periods(conn, rid), {"202609": 15 * 56000.0})
        self.assertEqual(_missing_areas(conn, cc), {})
        conn.close()

    def test_company_founding_thanks_event_uses_october_total_headcount(self):
        conn = _mk_conn()
        cc = _seed_cc(conn)
        _seed_hc(conn, cc, [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21])
        rid = _insert_rule(
            conn,
            "10月",
            "headcount_all",
            unit_price=1000,
            rid_label="会社設立記念 感謝イベント Sự kiện tri ân ngày thành lập công ty",
            driver_raw="実際の参加人数で振替 / Phân bổ theo số người tham gia thực tế",
        )

        AllocationEngine(conn)._process_allocation_rules()

        self.assertEqual(_alloc_periods(conn, rid), {"202610": 16 * 1000.0})
        row = conn.execute(
            "SELECT description FROM fact_input_data WHERE source=?",
            (f"alloc_{rid}",),
        ).fetchone()
        self.assertIn("driver_type=headcount_all", row["description"])
        self.assertIn("source_month=202610", row["description"])
        self.assertEqual(_missing_areas(conn, cc), {})
        conn.close()

    def test_adding_company_founding_event_preserves_existing_dynamic_cost_rows(self):
        conn = _mk_conn()
        cc = _seed_cc(conn)
        _seed_hc(conn, cc, [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21])
        existing_rules = [
            _insert_rule(
                conn,
                "5月",
                "headcount_staff",
                unit_price=200,
                rid_label="社員旅行 Du lịch công ty",
                driver_raw="実際の参加人数で振替",
            ),
            _insert_rule(
                conn,
                "9月",
                "headcount_staff",
                unit_price=300,
                rid_label="月餅 Bánh Trung Thu",
                driver_raw="実際の配布人数で振替",
            ),
            _insert_rule(
                conn,
                "11月",
                "headcount_all",
                unit_price=400,
                rid_label="京セラフェスティバル Lễ hội Kyocera",
                driver_raw="11月",
            ),
        ]
        founding_rule = _insert_rule(
            conn,
            "10月",
            "headcount_staff",
            unit_price=1000,
            rid_label="会社設立記念 感謝イベント Sự kiện tri ân ngày thành lập công ty",
            driver_raw="実際の参加人数で振替 / Phân bổ theo số người tham gia thực tế",
        )

        AllocationEngine(conn)._process_allocation_rules()

        for rule_id in (*existing_rules, founding_rule):
            self.assertTrue(_alloc_periods(conn, rule_id), rule_id)
        dynamic_rows = HubBuilder(conn, fiscal_year=2027)._load_append_rows(cc)
        descriptions = {
            str(row["description"]).split("|", 1)[0]
            for row in dynamic_rows
        }
        self.assertEqual(
            descriptions,
            {
                "Alloc: 社員旅行 Du lịch công ty",
                "Alloc: 月餅 Bánh Trung Thu",
                "Alloc: 京セラフェスティバル Lễ hội Kyocera",
                "Alloc: 会社設立記念 感謝イベント Sự kiện tri ân ngày thành lập công ty",
            },
        )
        self.assertEqual(len(dynamic_rows), 4)
        conn.close()

    def test_lucky_money_uses_february_headcount_without_manual_input(self):
        conn = _mk_conn()
        cc = _seed_cc(conn)
        _seed_hc(conn, cc, [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21])
        rid = _insert_rule(
            conn,
            "2月",
            "headcount_all",
            unit_price=50000,
            rid_label="お年玉 Tiền lì xì",
            driver_raw="実際の配布人数で振替 / Phân bổ theo số người nhận thực tế",
        )

        AllocationEngine(conn)._process_allocation_rules()

        self.assertEqual(_alloc_periods(conn, rid), {"202702": 20 * 50000.0})
        row = conn.execute(
            "SELECT description FROM fact_input_data WHERE source=?",
            (f"alloc_{rid}",),
        ).fetchone()
        self.assertIn("source_month=202702", row["description"])
        self.assertIn("driver_value=20", row["description"])
        self.assertIn("formula_expr=20*50000", row["description"])
        self.assertNotIn("missing_separate_count=1", row["description"])
        self.assertEqual(_missing_areas(conn, cc), {})
        conn.close()

    def test_company_trip_uses_total_may_headcount(self):
        conn = _mk_conn()
        cc = _seed_cc(conn)
        _seed_hc(conn, cc, [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21])
        rid = _insert_rule(
            conn,
            "5月",
            "headcount_worker",
            unit_price=2061000,
            rid_label="社員旅行 Du lịch công ty",
            driver_raw=(
                "総額を実際の社員旅行参加人数で実施月に振替. "
                "Phân bổ vào tháng thực hiện theo số người tham gia thực tế"
            ),
        )

        AllocationEngine(conn)._process_allocation_rules()

        self.assertEqual(_alloc_periods(conn, rid), {"202605": 11 * 2061000.0})
        self.assertEqual(_missing_areas(conn, cc), {})
        conn.close()

    def test_new_hire_medical_uses_canonical_delta_with_explicit_source_price(self):
        conn = _mk_conn()
        cc = _seed_cc(conn)
        conn.execute(
            """
            INSERT INTO fact_monthly_headcount
            (period, cc_code, headcount_all, headcount_staff, headcount_worker, source, description)
            VALUES ('202603', ?, 10, 10, 0, 'manual', 'event delta baseline')
            """,
            (cc,),
        )
        conn.commit()
        _seed_hc(conn, cc, [10, 12, 12, 15, 15, 15, 15, 15, 15, 15, 15, 15])
        rid = _insert_rule(conn, "入社月の翌月", "headcount_all", unit_price=1, rid_label="採用時健診")

        AllocationEngine(conn)._process_allocation_rules()

        periods = _alloc_periods(conn, rid)
        self.assertEqual(periods["202606"], 2.0)
        self.assertEqual(periods["202608"], 3.0)
        row = conn.execute(
            "SELECT description FROM fact_input_data WHERE source=? AND period='202606'",
            (f"alloc_{rid}",),
        ).fetchone()
        self.assertIn("source_month=202605", row["description"])
        self.assertIn("formula_expr=(2+0)*1", row["description"])
        self.assertEqual(_missing_areas(conn, cc), {"headcount_event_delta": 2})
        conn.close()

    def test_working_days_driver_uses_sys_params(self):
        conn = _mk_conn()
        _seed_cc(conn)
        _set_working_days(conn, [10, 20, 30, 40, 50, 60, 70, 80, 90, 12, 14, 16])
        rid = _insert_rule(conn, "毎月", "working_days", unit_price=2)
        months = get_fy_months(2027)

        AllocationEngine(conn)._process_allocation_rules()
        periods = _alloc_periods(conn, rid)
        self.assertEqual(periods.get(months[0]), 20.0)
        self.assertEqual(periods.get(months[1]), 40.0)
        self.assertEqual(periods.get(months[2]), 60.0)
        self.assertEqual(periods.get(months[11]), 32.0)
        conn.close()


if __name__ == "__main__":
    unittest.main()
