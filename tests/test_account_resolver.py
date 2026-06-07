import os
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

    # ── Fail-closed: manufacturing account missing (edge values) ────────
    def test_mfg_account_empty_string_returns_none(self):
        """cost_type=製造, mfg_acc="" → None, không fallback ga/sales."""
        conn = _mk_conn()
        engine = AllocationEngine(conn)
        result = engine._get_account_for_cc(
            cost_type="製造", mfg_acc="", ga_acc=6004086651, sales_acc=6004086551
        )
        self.assertIsNone(result)
        conn.close()

    def test_mfg_account_zero_string_returns_none(self):
        """cost_type=製造, mfg_acc="0" → None, không fallback ga/sales."""
        conn = _mk_conn()
        engine = AllocationEngine(conn)
        result = engine._get_account_for_cc(
            cost_type="製造", mfg_acc="0", ga_acc=6004086651, sales_acc=6004086551
        )
        self.assertIsNone(result)
        conn.close()

    def test_mfg_account_zero_int_returns_none(self):
        """cost_type=製造, mfg_acc=0 → None, không fallback ga/sales."""
        conn = _mk_conn()
        engine = AllocationEngine(conn)
        result = engine._get_account_for_cc(
            cost_type="製造", mfg_acc=0, ga_acc=6004086651, sales_acc=6004086551
        )
        self.assertIsNone(result)
        conn.close()

    # ── Fail-closed: general account missing (edge values) ──────────────
    def test_ga_account_none_returns_none(self):
        """cost_type=一般, ga_acc=None → None, không fallback mfg/sales."""
        conn = _mk_conn()
        engine = AllocationEngine(conn)
        result = engine._get_account_for_cc(
            cost_type="一般", mfg_acc=5004086291, ga_acc=None, sales_acc=6004086551
        )
        self.assertIsNone(result)
        conn.close()

    def test_ga_account_empty_string_returns_none(self):
        """cost_type=一般, ga_acc="" → None, không fallback mfg/sales."""
        conn = _mk_conn()
        engine = AllocationEngine(conn)
        result = engine._get_account_for_cc(
            cost_type="一般", mfg_acc=5004086291, ga_acc="", sales_acc=6004086551
        )
        self.assertIsNone(result)
        conn.close()

    def test_ga_account_zero_string_returns_none(self):
        """cost_type=一般, ga_acc="0" → None, không fallback mfg/sales."""
        conn = _mk_conn()
        engine = AllocationEngine(conn)
        result = engine._get_account_for_cc(
            cost_type="一般", mfg_acc=5004086291, ga_acc="0", sales_acc=6004086551
        )
        self.assertIsNone(result)
        conn.close()

    # ── Fail-closed: sales account missing (edge values) ────────────────
    def test_sales_account_none_returns_none(self):
        """cost_type=販売, sales_acc=None → None, không fallback mfg/ga."""
        conn = _mk_conn()
        engine = AllocationEngine(conn)
        result = engine._get_account_for_cc(
            cost_type="販売", mfg_acc=5004086291, ga_acc=6004086651, sales_acc=None
        )
        self.assertIsNone(result)
        conn.close()

    def test_sales_account_empty_string_returns_none(self):
        """cost_type=販売, sales_acc="" → None, không fallback mfg/ga."""
        conn = _mk_conn()
        engine = AllocationEngine(conn)
        result = engine._get_account_for_cc(
            cost_type="販売", mfg_acc=5004086291, ga_acc=6004086651, sales_acc=""
        )
        self.assertIsNone(result)
        conn.close()

    def test_sales_account_zero_int_returns_none(self):
        """cost_type=販売, sales_acc=0 → None, không fallback mfg/ga."""
        conn = _mk_conn()
        engine = AllocationEngine(conn)
        result = engine._get_account_for_cc(
            cost_type="販売", mfg_acc=5004086291, ga_acc=6004086651, sales_acc=0
        )
        self.assertIsNone(result)
        conn.close()

    # ── Unknown cost_type ───────────────────────────────────────────────
    def test_unknown_cost_type_falls_back_to_ga(self):
        """RISK: unknown cost_type hiện tại fallback sang ga_acc (existing behavior)."""
        conn = _mk_conn()
        engine = AllocationEngine(conn)
        # Unknown cost_type → trả ga_acc (documented existing behavior)
        result = engine._get_account_for_cc(
            cost_type="UNKNOWN", mfg_acc=5004086291, ga_acc=6004086651, sales_acc=6004086551
        )
        self.assertEqual(result, 6004086651)
        conn.close()

    def test_empty_cost_type_falls_back_to_ga(self):
        """RISK: empty cost_type hiện tại fallback sang ga_acc (existing behavior)."""
        conn = _mk_conn()
        engine = AllocationEngine(conn)
        result = engine._get_account_for_cc(
            cost_type="", mfg_acc=5004086291, ga_acc=6004086651, sales_acc=6004086551
        )
        self.assertEqual(result, 6004086651)
        conn.close()


class TestSharedAccountResolver(unittest.TestCase):
    def _mk_file_db(self):
        import tempfile
        from pathlib import Path
        from src.engine.account_resolver import AccountResolutionError
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db_path = Path(path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        create_schema(conn)
        conn.executemany(
            """
            INSERT INTO dim_cost_centers
            (code, name_jp, seq_no, saisan_type, cost_type, staff_count, worker_count)
            VALUES (?, ?, 1, ?, ?, 0, 0)
            """,
            [
                ("1412000040", "電気製造技術課", "製造", "製造"),
                ("1412000099", "一般テスト課", "一般", "一般"),
                ("1412000100", "販売テスト課", "販売", "販売"),
            ],
        )
        conn.executemany(
            """
            INSERT INTO dim_accounts
            (code, name_jp, name_vn, group_name, group_vn, mfg_code, ga_code, sales_code)
            VALUES (?, ?, NULL, NULL, NULL, ?, ?, ?)
            """,
            [
                (5000000000, "福利厚生費", 5004086291, 6004086551, 7004086777),
                (5000000001, "製造のみ", 5001111111, None, None),
            ],
        )
        conn.commit()
        return db_path, conn, AccountResolutionError

    def test_shared_target_cc_1412000040_resolves_cost_type(self):
        from src.engine.account_resolver import resolve_cost_type_for_cc
        db_path, conn, _ = self._mk_file_db()
        conn.close()
        self.assertEqual(resolve_cost_type_for_cc(db_path, 1412000040), "製造")

    def test_shared_account_name_resolves_correct_column_by_cost_type(self):
        from src.engine.account_resolver import resolve_account_code
        db_path, conn, _ = self._mk_file_db()
        conn.close()
        self.assertEqual(resolve_account_code(db_path, 1412000040, "福利厚生費"), 5004086291)
        self.assertEqual(resolve_account_code(db_path, 1412000099, "福利厚生費"), 6004086551)
        self.assertEqual(resolve_account_code(db_path, 1412000100, "福利厚生費"), 7004086777)

    def test_shared_missing_cc_fails_clearly(self):
        from src.engine.account_resolver import resolve_cost_type_for_cc
        db_path, conn, error_cls = self._mk_file_db()
        conn.close()
        with self.assertRaisesRegex(error_cls, "Cost center not found"):
            resolve_cost_type_for_cc(db_path, 9999999999)

    def test_shared_missing_account_fails_clearly(self):
        from src.engine.account_resolver import resolve_account_code
        db_path, conn, error_cls = self._mk_file_db()
        conn.close()
        with self.assertRaisesRegex(error_cls, "Account not found"):
            resolve_account_code(db_path, 1412000040, "存在しない科目")

    def test_shared_resolver_does_not_fallback_to_wrong_column(self):
        from src.engine.account_resolver import resolve_account_code
        db_path, conn, error_cls = self._mk_file_db()
        conn.close()
        with self.assertRaisesRegex(error_cls, "has no ga_code value"):
            resolve_account_code(db_path, 1412000099, "製造のみ")

    def test_manual_event_driver_uses_shared_connection_resolver(self):
        from unittest.mock import patch
        from src.parsers import manual_event_drivers
        db_path, conn, _ = self._mk_file_db()
        try:
            with patch(
                "src.parsers.manual_event_drivers.resolve_account_code_for_connection",
                return_value=5004086291,
            ) as mocked:
                self.assertEqual(
                    manual_event_drivers._resolve_account_code_or_error(conn, "1412000040", "福利厚生費"),
                    5004086291,
                )
            mocked.assert_called_once_with(conn, "1412000040", "福利厚生費")
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
