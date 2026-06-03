import sqlite3
import unittest
from src.db.schema import create_schema, init_sys_params
from src.engine.allocator import AllocationEngine

def _mk_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    init_sys_params(conn, exchange_rate=26273, fiscal_year=2027)
    return conn

def _seed_cc(conn, code, name_jp="TEST_CC", saisan_type="一般", cost_type="一般"):
    conn.execute(
        """
        INSERT INTO dim_cost_centers
        (code, name_jp, seq_no, saisan_type, cost_type, staff_count, worker_count)
        VALUES (?, ?, 1, ?, ?, 0, 0)
        """,
        (str(code), name_jp, saisan_type, cost_type),
    )
    conn.commit()

def _seed_hc(conn, cc_code, value=10.0):
    periods = ["202604", "202605", "202606", "202607", "202608", "202609", "202610", "202611", "202612", "202701", "202702", "202703"]
    for p in periods:
        conn.execute(
            """
            INSERT INTO fact_monthly_headcount
            (period, cc_code, headcount_all, headcount_staff, headcount_worker, source, description)
            VALUES (?, ?, ?, ?, ?, 'manual', 'test')
            """,
            (p, cc_code, value, value, 0.0),
        )
    conn.commit()

class TestAccountResolver(unittest.TestCase):
    def test_resolve_account_uses_manufacturing_column_for_mfg_cost_center(self):
        """Cost Center có cost_type = 製造 thì Account Resolver phải chọn cột mfg_acc."""
        conn = _mk_conn()
        engine = AllocationEngine(conn)

        resolved = engine._get_account_for_cc(
            cost_type="製造",
            mfg_acc=5004086291,
            ga_acc=6004086651,
            sales_acc=6004086551
        )
        self.assertEqual(resolved, 5004086291)
        conn.close()

    def test_resolve_account_uses_general_column_for_ga_cost_center(self):
        """Cost Center có cost_type = 一般 thì Account Resolver phải chọn cột ga_acc."""
        conn = _mk_conn()
        engine = AllocationEngine(conn)

        resolved = engine._get_account_for_cc(
            cost_type="一般",
            mfg_acc=5004086291,
            ga_acc=6004086651,
            sales_acc=6004086551
        )
        self.assertEqual(resolved, 6004086651)
        conn.close()

    def test_resolve_account_uses_sales_column_for_sales_cost_center(self):
        """Cost Center có cost_type = 販売 thì Account Resolver phải chọn cột sales_acc."""
        conn = _mk_conn()
        engine = AllocationEngine(conn)

        resolved = engine._get_account_for_cc(
            cost_type="販売",
            mfg_acc=5004086291,
            ga_acc=6004086651,
            sales_acc=6004086551
        )
        self.assertEqual(resolved, 6004086551)
        conn.close()

    def test_resolve_account_does_not_use_saisan_type_for_account_column(self):
        """Chứng minh chương trình không dùng nhầm saisan_type (採算区分)."""
        conn = _mk_conn()
        # CC có saisan_type = 部外間接1 nhưng cost_type = 製造
        _seed_cc(conn, code="1412000006", name_jp="TEST_CC", saisan_type="部外間接1", cost_type="製造")

        engine = AllocationEngine(conn)
        cc = next(x for x in engine.cost_centers if str(x["code"]).strip() == "1412000006")

        resolved = engine._get_account_for_cc(
            cost_type=cc["cost_type"],
            mfg_acc=5004086291,
            ga_acc=6004086651,
            sales_acc=6004086551
        )
        self.assertEqual(resolved, 5004086291)
        conn.close()

    def test_resolve_account_missing_mapping_does_not_guess_wrong_account(self):
        """Nếu account theo nhóm cần lấy bị thiếu, chương trình không đoán bừa sang account khác."""
        conn = _mk_conn()
        engine = AllocationEngine(conn)

        # 1. Kiểm tra trực tiếp method get_account_for_cc với mfg_acc là None
        resolved_none = engine._get_account_for_cc(
            cost_type="製造",
            mfg_acc=None,
            ga_acc=6004086651,
            sales_acc=6004086551
        )
        self.assertIsNone(resolved_none)
        self.assertNotEqual(resolved_none, 6004086651)
        self.assertNotEqual(resolved_none, 6004086551)

        # 2. Kiểm tra tích hợp: khi mfg_account của rule là NULL và CC thuộc nhóm 製造,
        # engine sẽ skip CC này và không tạo dòng dữ liệu phân bổ sai.
        _seed_cc(conn, code="1412000089", name_jp="TEST_CC", saisan_type="一般", cost_type="製造")
        _seed_hc(conn, "1412000089", 10.0)

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO map_allocation_rules
            (source_dept, item_name, account_name, mfg_account, ga_account, sales_account,
             posting_month, unit_price, unit, driver_type, driver_raw)
            VALUES ('QA', 'TEST_ITEM', 'Test Account', NULL, 6004086651, 6004086551, '毎月', 100.0, '/unit', 'headcount_all', '毎月')
            """
        )
        conn.commit()
        rule_id = cursor.lastrowid

        engine = AllocationEngine(conn)
        engine._process_allocation_rules()

        # Kiểm tra bảng fact_input_data xem có bản ghi phân bổ nào cho rule này không
        allocs = conn.execute(
            "SELECT * FROM fact_input_data WHERE source = ?",
            (f"alloc_{rule_id}",)
        ).fetchall()

        # Phải bằng 0 vì target_acc = None nên rule đã bị bỏ qua (fail-closed)
        self.assertEqual(len(allocs), 0)
        conn.close()

if __name__ == "__main__":
    unittest.main()
