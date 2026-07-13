import sqlite3

from src.db.schema import create_schema, init_sys_params
from src.engine.allocator import AllocationEngine


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    init_sys_params(conn, exchange_rate=26273, fiscal_year=2027)
    for seq, code in enumerate(("1412000006", "1412000007"), start=1):
        conn.execute("INSERT INTO dim_cost_centers(code,name_jp,seq_no,saisan_type,cost_type) VALUES (?, 'TEST', ?, '製造', '一般')", (code, seq))
    conn.commit()
    return conn


def test_target_cc_limits_cost_centers_and_mapping_rows(monkeypatch):
    conn = _conn()
    for cc_code in ("1412000006", "1412000007"):
        conn.execute("INSERT INTO fact_input_data(source,period,amount_vnd,cc_code,account_code,description) VALUES ('manual_special','202604',100,?,0,'same identity')", (cc_code,))
    conn.commit()
    calls = []
    def resolve(_conn, source, cc_code, **_kwargs):
        calls.append((source, str(cc_code)))
        return 5005136291
    monkeypatch.setattr("src.engine.allocator.resolve_account_code_for_source", resolve)
    engine = AllocationEngine(conn, target_cc="1412000006")
    stats = engine._map_direct_costs()
    assert [str(row["code"]) for row in engine.cost_centers] == ["1412000006"]
    assert stats == {"examined": 1, "mapped": 1, "unresolved": 0}
    assert calls == [("manual_special", "1412000006")]
    mapped = conn.execute("SELECT cc_code,account_code FROM fact_input_data ORDER BY cc_code").fetchall()
    assert [(str(row["cc_code"]), row["account_code"]) for row in mapped] == [("1412000006", 5005136291), ("1412000007", 0)]


def test_target_cc_cleanup_preserves_other_allocator_missing_rows():
    conn = _conn()
    for cc_code in ("1412000006", "1412000007"):
        conn.execute("INSERT INTO fact_missing_inputs(severity,cc_code,period,area,message,action,source) VALUES ('action',?,'202604','test','m','a','allocator')", (cc_code,))
    conn.commit()
    AllocationEngine(conn, target_cc="1412000006")._clear_allocator_missing_inputs()
    rows = conn.execute("SELECT cc_code FROM fact_missing_inputs WHERE source='allocator' ORDER BY cc_code").fetchall()
    assert [row["cc_code"] for row in rows] == ["1412000007"]
