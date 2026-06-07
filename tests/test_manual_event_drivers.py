import csv
import sqlite3

from src.db.schema import create_schema, init_sys_params
from src.parsers.manual_event_drivers import parse_manual_event_drivers


ACCOUNT_WELFARE = "\u798f\u5229\u539a\u751f\u8cbb"
ACCOUNT_MISSING = "\u5b58\u5728\u3057\u306a\u3044\u79d1\u76ee"
ACCOUNT_MFG_ONLY = "\u88fd\u9020\u306e\u307f"


def _mk_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    init_sys_params(conn, exchange_rate=26273, fiscal_year=2027)
    conn.executemany(
        """
        INSERT INTO dim_cost_centers
        (code, name_jp, seq_no, saisan_type, cost_type, staff_count, worker_count)
        VALUES (?, ?, 1, ?, ?, 0, 0)
        """,
        [
            ("1412000040", "電気製造技術課", "製造", "製造"),
            ("1412000099", "一般テスト課", "一般", "一般"),
        ],
    )
    conn.executemany(
        """
        INSERT INTO dim_accounts
        (code, name_jp, name_vn, group_name, group_vn, mfg_code, ga_code, sales_code)
        VALUES (?, ?, NULL, NULL, NULL, ?, ?, ?)
        """,
        [
            (5004086291, "福利厚生費", 5004086291, 6004086551, 7004086777),
            (5000000001, "製造のみ", 5001111111, None, None),
        ],
    )
    conn.commit()
    return conn


def _write_event_csv(tmp_path, rows):
    path = tmp_path / "event_drivers_manual.csv"
    fieldnames = [
        "cc_code",
        "period",
        "target_month",
        "source_month",
        "posting_rule",
        "event_name",
        "event_type",
        "count",
        "unit_price",
        "unit_price_key",
        "allocation_content",
        "amount_vnd",
        "account_code",
        "account_jp_name",
        "account_name",
        "account_group",
        "form_row",
        "row",
        "headcount_basis",
        "description",
        "note",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_manual_event_driver_resolves_account_name_by_cost_type(tmp_path):
    conn = _mk_conn()
    _write_event_csv(
        tmp_path,
        [
            {
                "cc_code": "1412000040",
                "period": "202704",
                "event_name": "birthday",
                "count": "2",
                "unit_price": "1000",
                "account_jp_name": ACCOUNT_WELFARE,
                "form_row": "59",
            }
        ],
    )
    result = parse_manual_event_drivers(conn, source_dir=str(tmp_path))
    assert result["inserted"] == 1
    row = conn.execute("SELECT account_code, amount_vnd FROM fact_input_data WHERE source='manual_event_driver'").fetchone()
    assert row["account_code"] == 5004086291
    assert row["amount_vnd"] == 2000
    conn.close()


def test_manual_event_driver_missing_account_reports_clear_error(tmp_path):
    conn = _mk_conn()
    _write_event_csv(
        tmp_path,
        [
            {
                "cc_code": "1412000040",
                "period": "202704",
                "event_name": "missing_account",
                "count": "1",
                "unit_price": "1000",
                "account_jp_name": ACCOUNT_MISSING,
                "form_row": "59",
            }
        ],
    )
    result = parse_manual_event_drivers(conn, source_dir=str(tmp_path))
    assert result["inserted"] == 0
    assert result["errors"] == 1
    assert "Account not found" in result["error_message"]
    conn.close()


def test_manual_event_driver_does_not_fallback_to_wrong_account_column(tmp_path):
    conn = _mk_conn()
    _write_event_csv(
        tmp_path,
        [
            {
                "cc_code": "1412000099",
                "period": "202704",
                "event_name": "wrong_column_guard",
                "count": "1",
                "unit_price": "1000",
                "account_jp_name": ACCOUNT_MFG_ONLY,
                "form_row": "59",
            }
        ],
    )
    result = parse_manual_event_drivers(conn, source_dir=str(tmp_path))
    assert result["inserted"] == 0
    assert result["errors"] == 1
    assert "has no ga_code value" in result["error_message"]
    conn.close()
