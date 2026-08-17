"""Kiểm thử tính kế thừa của sales_account, mfg_account, ga_account cho các dòng tiếp nối trong load_allocation_rules."""

import sqlite3
import pandas as pd
import pytest

from src.db.loader import load_allocation_rules
from src.db.schema import create_schema


def test_allocation_rules_loader_inherits_sales_account_on_continuation_rows(tmp_path):
    """Đảm bảo dòng tiếp nối của cùng một khoản mục kế thừa đầy đủ sales_account từ dòng trước."""
    excel_path = tmp_path / "allocation_rules_test.xlsx"

    # Tạo DataFrame giả lập quy tắc phân bổ:
    # Dòng 0: Header
    # Dòng 1: Header chi tiết
    # Dòng 2: Mục A, MFG=500001, GA=600001, Sales=700001, Month=every month, Price=100
    # Dòng 3: Dòng tiếp nối của Mục A (raw_item=None, account_name=None, mfg=None, ga=None, sales=None), Month=every month, Price=200
    # Dòng 4: Mục B, MFG=500002, GA=600002, Sales=700002, Month=4, Price=300
    data = [
        ["Phòng ban", "Khoản mục", "Tên tài khoản", "Mã MFG", "Mã GA", "Mã Sales", "Tháng", "Số tiền/Tỷ lệ", "Đơn vị", "Driver"],
        ["Phòng GA", "Chi phí đồng phục", "Đồng phục", 500001, 600001, 700001, "every month", "100", "bộ", "headcount_all"],
        ["Phòng GA", None, None, None, None, None, "every month", "200", "bộ", "headcount_all"],
        ["Phòng HR", "Chi phí khám sức khỏe", "Khám SK", 500002, 600002, 700002, "4", "300", "người", "headcount_staff"],
        ["Phòng HR", None, None, None, None, None, "5", "400", "người", "headcount_staff"],
    ]
    df = pd.DataFrame(data)
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="FY2027", index=False, header=False)

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    count = load_allocation_rules(conn, alloc_path=str(excel_path), fiscal_year=2027)
    assert count == 4, f"Expected 4 loaded rules, got {count}"

    rules = conn.execute("SELECT * FROM map_allocation_rules ORDER BY id").fetchall()
    assert len(rules) == 4

    # Quy tắc 1 (dòng gốc mục A)
    assert rules[0]["item_name"] == "Chi phí đồng phục"
    assert rules[0]["mfg_account"] == 500001
    assert rules[0]["ga_account"] == 600001
    assert rules[0]["sales_account"] == 700001
    assert float(rules[0]["unit_price"]) == 100.0

    # Quy tắc 2 (dòng tiếp nối mục A) - Phải kế thừa đầy đủ cả 3 loại tài khoản
    assert rules[1]["item_name"] == "Chi phí đồng phục"
    assert rules[1]["mfg_account"] == 500001
    assert rules[1]["ga_account"] == 600001
    assert rules[1]["sales_account"] == 700001, f"Expected sales_account 700001, got {rules[1]['sales_account']}"
    assert float(rules[1]["unit_price"]) == 200.0

    # Quy tắc 3 (dòng gốc mục B)
    assert rules[2]["item_name"] == "Chi phí khám sức khỏe"
    assert rules[2]["mfg_account"] == 500002
    assert rules[2]["ga_account"] == 600002
    assert rules[2]["sales_account"] == 700002

    # Quy tắc 4 (dòng tiếp nối mục B) - Phải kế thừa đầy đủ cả 3 loại tài khoản từ mục B
    assert rules[3]["item_name"] == "Chi phí khám sức khỏe"
    assert rules[3]["mfg_account"] == 500002
    assert rules[3]["ga_account"] == 600002
    assert rules[3]["sales_account"] == 700002, f"Expected sales_account 700002, got {rules[3]['sales_account']}"

    conn.close()
