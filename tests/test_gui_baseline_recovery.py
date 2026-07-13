import pytest

from scripts.run_e2e import _staffing_preflight
from src.db.schema import create_schema, get_connection
from src.services.manual_staffing_overrides import (
    apply_manual_baseline_overrides,
    apply_manual_time_overrides,
    copy_missing_baselines_from_april,
    normalize_manual_time_rows,
    save_manual_time_overrides,
)
from src.utils.fiscal_periods import fiscal_baseline_period, fiscal_periods


def make_conn(tmp_path):
    conn = get_connection(str(tmp_path / "test.db"))
    create_schema(conn)
    return conn


def insert_plan_series(conn, cc="101", fiscal_year=2027):
    for index, period in enumerate(fiscal_periods(fiscal_year), start=1):
        conn.execute(
            """INSERT INTO fact_monthly_headcount
               (period,cc_code,headcount_all,headcount_expat,headcount_staff,
                headcount_worker,headcount_local_total,source,split_status)
               VALUES(?,?,15,1,10,4,14,'department_plan','READY')""",
            (period, cc),
        )


def test_blank_manual_times_create_complete_zero_rows(tmp_path):
    conn = make_conn(tmp_path)
    try:
        count = save_manual_time_overrides(conn, 2027, "101", {})
        conn.commit()
        rows = conn.execute(
            "SELECT * FROM fact_headcount_time_source WHERE cc_code='101' ORDER BY period"
        ).fetchall()
        assert count == 12
        assert len(rows) == 12
        assert all(float(row["fixed_hours_expat"]) == 0 for row in rows)
        assert all(float(row["overtime_hours_local"]) == 0 for row in rows)
    finally:
        conn.close()


def test_manual_time_decimal_validation():
    rows = normalize_manual_time_rows(
        ["202604"], {"202604": {"fixed_hours_expat": "1,5", "fixed_hours_local": ""}}
    )
    assert rows[0]["fixed_hours_expat"] == 1.5
    assert rows[0]["fixed_hours_local"] == 0
    with pytest.raises(ValueError, match="số không âm"):
        normalize_manual_time_rows(["202604"], {"202604": {"overtime_hours_local": "-1"}})


def test_time_override_survives_source_delete_and_preflight(tmp_path):
    conn = make_conn(tmp_path)
    try:
        insert_plan_series(conn)
        save_manual_time_overrides(conn, 2027, "101", {})
        conn.execute("DELETE FROM fact_headcount_time_source WHERE cc_code='101'")
        assert apply_manual_time_overrides(conn, 2027, target_cc="101") == 12
        baseline = fiscal_baseline_period(2027)
        conn.execute(
            """INSERT INTO fact_monthly_headcount
               (period,cc_code,headcount_all,headcount_expat,headcount_staff,
                headcount_worker,headcount_local_total,source,split_status)
               VALUES(?,?,15,1,10,4,14,'manual','READY')""",
            (baseline, "101"),
        )
        conn.commit()
        _staffing_preflight(conn, 2027, target_cc="101")
    finally:
        conn.close()


def test_user_approved_t4_copy_is_persistent_and_does_not_overwrite_t3(tmp_path):
    conn = make_conn(tmp_path)
    try:
        insert_plan_series(conn)
        copied = copy_missing_baselines_from_april(conn, 2027, target_cc="101")
        assert copied == ["101"]
        baseline = fiscal_baseline_period(2027)
        saved = conn.execute(
            "SELECT * FROM fact_manual_headcount_baseline_override WHERE period=? AND cc_code='101'",
            (baseline,),
        ).fetchone()
        assert saved["description"] == "USER_APPROVED_BASELINE_T3_FROM_T4"
        assert float(saved["headcount_all"]) == 15

        conn.execute(
            "UPDATE fact_monthly_headcount SET headcount_all=99 WHERE period=? AND cc_code='101' AND source='manual'",
            (baseline,),
        )
        assert copy_missing_baselines_from_april(conn, 2027, target_cc="101") == ["101"]
        current = conn.execute(
            "SELECT headcount_all FROM fact_monthly_headcount WHERE period=? AND cc_code='101' AND source='manual'",
            (baseline,),
        ).fetchone()
        assert float(current[0]) == 99

        conn.execute("DELETE FROM fact_monthly_headcount WHERE source='manual'")
        assert apply_manual_baseline_overrides(conn, 2027, target_cc="101") == 1
        restored = conn.execute(
            "SELECT description FROM fact_monthly_headcount WHERE period=? AND cc_code='101' AND source='manual'",
            (baseline,),
        ).fetchone()
        assert restored[0] == "USER_APPROVED_BASELINE_T3_FROM_T4"
    finally:
        conn.close()
