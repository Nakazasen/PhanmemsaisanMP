import sqlite3
from pathlib import Path

import pytest

from src.db.schema import create_schema, init_sys_params
from src.engine.allocator import AllocationEngine
from src.services.i18n import DEFAULT_LANGUAGE, set_current_language, t
from src.services.manual_staffing_overrides import (
    copy_annual_manual_inputs,
    save_manual_g6_to_g5_transitions,
)
from src.utils.fiscal_periods import fiscal_periods


def make_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    init_sys_params(conn, fiscal_year=2027)
    return conn


def seed_transition_case(conn, cc="1412000044"):
    conn.execute(
        """INSERT INTO dim_cost_centers(code,name_jp,seq_no,saisan_type,cost_type)
           VALUES(?, 'TEST', 1, 'x', 'x')""",
        (cc,),
    )
    for period, staff, worker in (("202604", 10, 100), ("202605", 15, 95)):
        conn.execute(
            """INSERT INTO fact_monthly_headcount
               (period,cc_code,headcount_all,headcount_staff,headcount_worker,
                headcount_local_total,source,split_status)
               VALUES(?,?,?,?,?,?, 'department_plan', 'READY')""",
            (period, cc, staff + worker, staff, worker, staff + worker),
        )
    conn.commit()
    return cc


def insert_rule(conn, item_name, posting_month, driver_type, unit_price=100):
    cursor = conn.execute(
        """INSERT INTO map_allocation_rules
           (source_dept,item_name,account_name,mfg_account,ga_account,sales_account,
            posting_month,unit_price,unit,driver_type,driver_raw)
           VALUES('GA', ?, 'test', 5001, 5001, 5001, ?, ?, '/person', ?, ?)""",
        (item_name, posting_month, unit_price, driver_type, posting_month),
    )
    conn.commit()
    return cursor.lastrowid


def test_g6_to_g5_transitions_are_fy_scoped_and_copied_to_run_db(tmp_path):
    store = sqlite3.connect(tmp_path / "manual_inputs.db")
    store.row_factory = sqlite3.Row
    create_schema(store)
    save_manual_g6_to_g5_transitions(
        store,
        2027,
        "1412000044",
        {"202604": "3", "202605": ""},
    )
    store.commit()

    run = make_conn()
    copied = copy_annual_manual_inputs(run, 2027, tmp_path / "manual_inputs.db")
    row = run.execute(
        """SELECT transition_count FROM fact_manual_g6_to_g5_transition
           WHERE fiscal_year=2027 AND cc_code='1412000044' AND period='202604'"""
    ).fetchone()
    assert copied["fact_manual_g6_to_g5_transition"] == len(fiscal_periods(2027))
    assert float(row["transition_count"]) == 3

    with pytest.raises(ValueError, match="non-negative integer"):
        save_manual_g6_to_g5_transitions(store, 2027, "1412000044", {"202604": "-1"})


def test_g6_to_g5_reduces_only_new_hire_staff_counts():
    conn = make_conn()
    cc = seed_transition_case(conn)
    save_manual_g6_to_g5_transitions(conn, 2027, cc, {"202605": "3"})
    staff_rule = insert_rule(conn, "New staff notebook", "入社月", "headcount_staff")
    all_rule = insert_rule(conn, "New hire pen", "入社月", "headcount_all")
    monthly_rule = insert_rule(conn, "Normal monthly staff cost", "毎月", "headcount_staff")

    engine = AllocationEngine(conn)
    assert engine._uniform_new_hires(cc, "202605") == (2.0, 0.0, 2.0)
    assert engine._recruitment_health_new_hires(cc, "202605", None) == (2.0, 0.0)
    engine._process_allocation_rules()

    staff_amount = conn.execute(
        "SELECT amount_vnd FROM fact_input_data WHERE source=? AND period='202605'",
        (f"alloc_{staff_rule}",),
    ).fetchone()["amount_vnd"]
    all_amount = conn.execute(
        "SELECT amount_vnd FROM fact_input_data WHERE source=? AND period='202605'",
        (f"alloc_{all_rule}",),
    ).fetchone()["amount_vnd"]
    monthly_amount = conn.execute(
        "SELECT amount_vnd FROM fact_input_data WHERE source=? AND period='202605'",
        (f"alloc_{monthly_rule}",),
    ).fetchone()["amount_vnd"]
    assert float(staff_amount) == 200
    assert float(all_amount) == 200
    assert float(monthly_amount) == 1500


def test_missing_g6_to_g5_keeps_existing_new_hire_result():
    conn = make_conn()
    cc = seed_transition_case(conn)
    rule_id = insert_rule(conn, "New staff notebook", "入社月", "headcount_staff")

    AllocationEngine(conn)._process_allocation_rules()

    amount = conn.execute(
        "SELECT amount_vnd FROM fact_input_data WHERE source=? AND period='202605'",
        (f"alloc_{rule_id}",),
    ).fetchone()["amount_vnd"]
    assert float(amount) == 500


def test_g6_to_g5_label_is_available_in_all_ui_languages():
    expected = {"vi": "G6=>G5", "ja": "G6→G5", "en": "G6 to G5"}
    try:
        for language, label in expected.items():
            set_current_language(language)
            assert t("hc_header_g6_to_g5") == label
    finally:
        set_current_language(DEFAULT_LANGUAGE)


def test_manual_headcount_screen_loads_and_saves_the_transition_series():
    source = Path("src/universal_app.py").read_text(encoding="utf-8")
    assert '"g6_to_g5"' in source
    assert 't("hc_header_g6_to_g5")' in source
    assert "fact_manual_g6_to_g5_transition" in source
    assert "save_manual_g6_to_g5_transitions(conn,fiscal_year,cc" in source
