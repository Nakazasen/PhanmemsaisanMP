from __future__ import annotations

import csv
from pathlib import Path

from src.db.loader import load_uniform_entitlements
from src.db.schema import create_schema, get_connection, init_sys_params
from src.engine.allocator import AllocationEngine
from src.parsers.manual_event_drivers import TEMPLATE_COLUMNS, parse_manual_event_drivers
from src.utils.excel_helpers import get_fy_months


CC = "1412000036"
WELFARE_MFG = 5004086291
WELFARE_GA = 6004086651
WELFARE_SALES = 6004086551


def _connection(tmp_path, *, cc_code=CC, cost_type="製造"):
    conn = get_connection(str(tmp_path / "uniform.db"))
    create_schema(conn)
    init_sys_params(conn, exchange_rate=25_000, fiscal_year=2027)
    conn.execute(
        """
        INSERT INTO dim_cost_centers(code,name_jp,seq_no,saisan_type,cost_type)
        VALUES (?, 'Test', 1, '部内間接', ?)
        """,
        (cc_code, cost_type),
    )
    conn.execute(
        """
        INSERT INTO dim_accounts
        (code,name_jp,name_vn,group_name,group_vn,mfg_code,ga_code,sales_code)
        VALUES (999, '福利厚生費', 'Chi phí phúc lợi', '福利厚生費', 'Chi phí phúc lợi', ?, ?, ?)
        """,
        (WELFARE_MFG, WELFARE_GA, WELFARE_SALES),
    )
    for code, suffix in (
        (WELFARE_MFG, "製"),
        (WELFARE_GA, "販管"),
        (WELFARE_SALES, "販"),
    ):
        conn.execute(
            "INSERT INTO dim_accounts(code,name_jp) VALUES (?, ?)",
            (code, f"福利厚生費（{suffix}）"),
        )
    conn.commit()
    return conn


def _rule(conn, item_name, unit_price, *, mfg=WELFARE_MFG, ga=WELFARE_GA, sales=WELFARE_SALES):
    cursor = conn.execute(
        """
        INSERT INTO map_allocation_rules
        (source_dept,item_name,account_name,mfg_account,ga_account,sales_account,
         posting_month,unit_price,unit,driver_type,driver_raw)
        VALUES ('総務課', ?, '福利厚生費', ?, ?, ?, '毎月', ?, '/個', 'headcount_all', '配布数')
        """,
        (item_name, mfg, ga, sales, unit_price),
    )
    return cursor.lastrowid


def _entitlement(conn, item_key, item_name, *, cc_code=CC, eligible=1, cell="I14"):
    conn.execute(
        """
        INSERT INTO map_cost_center_uniform_items
        (cc_code,item_key,item_name,eligible,source_file,source_sheet,source_cell)
        VALUES (?, ?, ?, ?, 'requirements.xlsx', '原価センタ', ?)
        """,
        (cc_code, item_key, item_name, eligible, cell),
    )


def _headcount_cache(engine, changes, *, cc_code=CC, staff=10, worker=20):
    rows = {}
    for period in ["202603", *get_fy_months(2027)]:
        staff_change, worker_change = changes.get(period, (0, 0))
        staff += staff_change
        worker += worker_change
        rows[(cc_code, period)] = {
            "headcount_all": staff + worker,
            "headcount_staff": staff,
            "headcount_worker": worker,
            "headcount_expat": 0,
            "headcount_male": 0,
            "headcount_female": 0,
        }
    engine.hc_cache = rows


def test_current_requirement_has_mutually_exclusive_summer_shirts(tmp_path):
    conn = _connection(tmp_path)
    # Replace the one-CC fixture with the real 65-CC catalogue for source parity.
    conn.execute("DELETE FROM dim_cost_centers")
    from src.db.loader import load_cost_centers

    assert load_cost_centers(conn, "docs/MP2027/FORM.xlsx") == 65
    assert load_uniform_entitlements(conn) == 65 * 16
    dual = conn.execute(
        """
        SELECT cc_code
        FROM map_cost_center_uniform_items
        WHERE eligible=1 AND item_key IN ('short_sleeve','polo','security_short_sleeve')
        GROUP BY cc_code HAVING COUNT(*) > 1
        """
    ).fetchall()
    polo = {
        row[0]
        for row in conn.execute(
            "SELECT cc_code FROM map_cost_center_uniform_items WHERE eligible=1 AND item_key='polo'"
        )
    }
    assert dual == []
    assert polo == {"1412000036", "1412000103", "1412000073", "1412000072"}
    conn.close()


def test_polo_timing_and_worker_only_new_hire_cup(tmp_path):
    conn = _connection(tmp_path)
    _rule(conn, "ポロ制服 Áo Polo", 139_000)
    _rule(conn, "制服（冬） Đồng phục dài tay", 175_000)
    _rule(conn, "折りたたみコップ Cốc xếp", 8_500)
    _entitlement(conn, "polo", "Áo polo", cell="L14")
    _entitlement(conn, "long_sleeve", "Đồng phục dài tay", cell="H14")
    _entitlement(conn, "collapsible_cup", "Cốc xếp", cell="U14")
    conn.commit()

    engine = AllocationEngine(conn, target_cc=CC)
    changes = {
        "202604": (1, 2),
        "202605": (0, 1),
        "202701": (1, 0),
        "202702": (0, 1),
    }
    _headcount_cache(engine, changes)
    engine.run_allocation()

    april_polo = conn.execute(
        "SELECT issue_quantity,amount_vnd FROM audit_uniform_cup_calculation WHERE item_key='polo' AND period='202604'"
    ).fetchone()
    may_long = conn.execute(
        "SELECT COUNT(*) FROM audit_uniform_cup_calculation WHERE item_key='long_sleeve' AND period='202605'"
    ).fetchone()[0]
    october_long = conn.execute(
        "SELECT issue_quantity,source_periods FROM audit_uniform_cup_calculation WHERE item_key='long_sleeve' AND period='202610'"
    ).fetchone()
    february_polo = conn.execute(
        "SELECT issue_quantity,source_periods FROM audit_uniform_cup_calculation WHERE item_key='polo' AND period='202702'"
    ).fetchone()
    april_cup = conn.execute(
        "SELECT issue_quantity,amount_vnd FROM audit_uniform_cup_calculation WHERE item_key='collapsible_cup' AND period='202604' AND release_type='new_worker'"
    ).fetchone()

    assert tuple(april_polo) == (6, 834_000)
    assert may_long == 0
    assert tuple(october_long) == (2, "202605")
    assert tuple(february_polo) == (4, "202702;202701")
    assert tuple(april_cup) == (2, 17_000)
    assert conn.execute("SELECT COUNT(*) FROM fact_missing_inputs WHERE area='periodic_cup_count'").fetchone()[0] == 2

    audit_count = conn.execute("SELECT COUNT(*) FROM audit_uniform_cup_calculation").fetchone()[0]
    fact_count = conn.execute(
        "SELECT COUNT(*) FROM fact_input_data WHERE source LIKE 'alloc_uniform_%'"
    ).fetchone()[0]
    second_run = AllocationEngine(conn, target_cc=CC)
    _headcount_cache(second_run, changes)
    second_run.run_allocation()
    assert conn.execute("SELECT COUNT(*) FROM audit_uniform_cup_calculation").fetchone()[0] == audit_count
    assert conn.execute(
        "SELECT COUNT(*) FROM fact_input_data WHERE source LIKE 'alloc_uniform_%'"
    ).fetchone()[0] == fact_count
    conn.close()


def test_ambiguous_summer_shirt_fails_closed(tmp_path):
    conn = _connection(tmp_path)
    _rule(conn, "制服（夏） Đồng phục ngắn tay", 165_000)
    _rule(conn, "ポロ制服 Áo Polo", 139_000)
    _entitlement(conn, "short_sleeve", "Đồng phục ngắn tay", cell="I14")
    _entitlement(conn, "polo", "Áo polo", cell="L14")
    conn.commit()
    engine = AllocationEngine(conn, target_cc=CC)
    _headcount_cache(engine, {"202604": (1, 1)})
    engine.run_allocation()
    assert conn.execute(
        "SELECT COUNT(*) FROM audit_uniform_cup_calculation WHERE item_key IN ('short_sleeve','polo')"
    ).fetchone()[0] == 0
    warning = conn.execute(
        "SELECT message FROM fact_missing_inputs WHERE area='uniform_ambiguous_shirt'"
    ).fetchone()
    assert warning is not None and "I14" in warning[0] and "L14" in warning[0]
    conn.close()


def test_periodic_cup_explicit_zero_is_confirmed_without_warning(tmp_path):
    conn = _connection(tmp_path)
    _rule(conn, "折りたたみコップ Cốc xếp", 8_500)
    _entitlement(conn, "collapsible_cup", "Cốc xếp", cell="U14")
    conn.commit()
    csv_path = tmp_path / "event_drivers_manual.csv"
    row = {column: "" for column in TEMPLATE_COLUMNS}
    row.update(
        {
            "cc_code": CC,
            "period": "202608",
            "event_name": "Cốc xếp định kỳ",
            "event_type": "manual_count_unit_price",
            "count": "0",
        }
    )
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TEMPLATE_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    result = parse_manual_event_drivers(conn, source_dir=str(tmp_path))
    assert result["inserted"] == 1 and result["errors"] == 0

    engine = AllocationEngine(conn, target_cc=CC)
    _headcount_cache(engine, {})
    engine.run_allocation()
    assert conn.execute(
        "SELECT COUNT(*) FROM fact_missing_inputs WHERE area='periodic_cup_count' AND period='202608'"
    ).fetchone()[0] == 0
    assert conn.execute(
        "SELECT status FROM audit_uniform_cup_calculation WHERE item_key='collapsible_cup' AND period='202608'"
    ).fetchone()[0] == "EXPLICIT_ZERO"
    assert conn.execute(
        "SELECT COUNT(*) FROM fact_missing_inputs WHERE area='periodic_cup_count' AND period='202702'"
    ).fetchone()[0] == 1
    conn.close()


def test_security_uses_only_security_specific_items(tmp_path):
    security_cc = "1412000091"
    conn = _connection(tmp_path, cc_code=security_cc, cost_type="一般")
    _rule(conn, "保安課の半袖 Áo ngắn tay phòng an ninh", 250_500, mfg=None)
    _rule(conn, "制服（夏） Đồng phục ngắn tay", 165_000)
    _entitlement(conn, "security_short_sleeve", "Áo ngắn tay phòng an ninh", cc_code=security_cc, cell="K58")
    conn.commit()
    engine = AllocationEngine(conn, target_cc=security_cc)
    _headcount_cache(engine, {"202604": (1, 0)}, cc_code=security_cc)
    engine.run_allocation()
    row = conn.execute(
        "SELECT item_key,issue_quantity,account_code FROM audit_uniform_cup_calculation"
    ).fetchone()
    assert tuple(row) == ("security_short_sleeve", 2, WELFARE_GA)
    assert conn.execute(
        "SELECT COUNT(*) FROM audit_uniform_cup_calculation WHERE item_key='short_sleeve'"
    ).fetchone()[0] == 0
    conn.close()
