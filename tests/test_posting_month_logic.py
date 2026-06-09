import sqlite3
import unittest

from src.db.schema import create_schema, init_sys_params
from src.engine.allocator import AllocationEngine
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


def _insert_rule(conn, posting_month, driver_type, unit_price=100, rid_label="TEST"):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO map_allocation_rules
        (source_dept, item_name, account_name, mfg_account, ga_account, sales_account,
         posting_month, unit_price, unit, driver_type, driver_raw)
        VALUES ('QA', ?, 'Test Account', 500001, 600001, 700001, ?, ?, '/unit', ?, ?)
        """,
        (rid_label, posting_month, float(unit_price), driver_type, posting_month),
    )
    conn.commit()
    return cur.lastrowid


def _seed_hc(conn, cc_code, values, source="manual", driver_kind="all"):
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

    def test_separate_count_admin_events_require_manual_event_source(self):
        separate_count_items = [
            "FY2027部門方針発表会後の決起コンパ",
            "社員旅行不参加対象者へのギフト贈呈 Quà tặng cho CNV không thể tham gia du lịch",
            "マイエピソード ～フィロソフィの実践～参加賞",
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
            self.assertEqual(periods, {}, item_name)
            conn.close()

    def test_new_hire_medical_requires_manual_or_explicit_source_price(self):
        conn = _mk_conn()
        cc = _seed_cc(conn)
        _seed_hc(conn, cc, [10, 12, 12, 15, 15, 15, 15, 15, 15, 15, 15, 15])
        rid = _insert_rule(conn, "入社月の翌月", "headcount_all", unit_price=1, rid_label="採用時健診")

        AllocationEngine(conn)._process_allocation_rules()

        self.assertEqual(_alloc_periods(conn, rid), {})
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
