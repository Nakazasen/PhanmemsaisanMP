import pytest

from scripts.run_e2e import _staffing_preflight
from src.universal_app import _failed_run_database_from_output
from src.db.schema import create_schema, get_connection
from src.services.manual_staffing_overrides import (
    apply_manual_baseline_overrides,
    apply_manual_time_overrides,
    copy_missing_baselines_from_april,
    find_missing_baseline_ccs,
    has_valid_manual_baseline,
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


def test_missing_baseline_check_uses_selected_scope_and_saved_overrides(tmp_path):
    conn = make_conn(tmp_path)
    try:
        baseline = fiscal_baseline_period(2027)
        conn.execute(
            """INSERT INTO fact_manual_headcount_baseline_override
               (period,cc_code,fiscal_year,headcount_all,headcount_expat,
                headcount_staff,headcount_worker,headcount_local_total,description)
               VALUES(?,?,2027,15,1,10,4,14,'USER_APPROVED_BASELINE_T3_FROM_T4')""",
            (baseline, "101"),
        )
        conn.commit()

        assert find_missing_baseline_ccs(
            conn,
            2027,
            scope_ccs=("101", "102"),
        ) == ["102"]
    finally:
        conn.close()


def test_legacy_blank_zero_baseline_does_not_unlock_calculation(tmp_path):
    conn = make_conn(tmp_path)
    try:
        baseline = fiscal_baseline_period(2027)
        conn.execute(
            """INSERT INTO fact_manual_headcount_baseline_override
               (period,cc_code,fiscal_year,headcount_all,headcount_expat,
                headcount_staff,headcount_worker,headcount_local_total,
                description,source_file)
               VALUES(?,?,2027,0,0,0,0,0,'MANUAL_BASELINE_T3','MANUAL_GUI')""",
            (baseline, "101"),
        )
        conn.commit()

        assert not has_valid_manual_baseline(conn, 2027, "101")
        assert find_missing_baseline_ccs(
            conn,
            2027,
            scope_ccs=("101",),
        ) == ["101"]
    finally:
        conn.close()


def test_explicit_zero_baseline_is_valid_after_user_confirms_it(tmp_path):
    conn = make_conn(tmp_path)
    try:
        from src.services.manual_staffing_overrides import save_manual_baseline_override

        save_manual_baseline_override(conn, 2027, "101", 0, 0, 0)
        conn.commit()

        assert has_valid_manual_baseline(conn, 2027, "101")
        assert find_missing_baseline_ccs(
            conn,
            2027,
            scope_ccs=("101",),
        ) == []
    finally:
        conn.close()


def test_pipeline_staffing_preflight_rejects_legacy_blank_zero_baseline(tmp_path):
    conn = make_conn(tmp_path)
    try:
        insert_plan_series(conn)
        save_manual_time_overrides(conn, 2027, "101", {})
        baseline = fiscal_baseline_period(2027)
        conn.execute(
            """INSERT INTO fact_monthly_headcount
               (period,cc_code,headcount_all,headcount_expat,headcount_staff,
                headcount_worker,headcount_local_total,source,split_status,
                description,source_file)
               VALUES(?,?,0,0,0,0,0,'manual','READY',
                      'MANUAL_BASELINE_T3','MANUAL_GUI')""",
            (baseline, "101"),
        )
        conn.commit()

        issues = _staffing_preflight(conn, 2027, target_cc="101")

        assert issues
        assert "202603" not in issues[0]
        assert "03/2026" in issues[0]
    finally:
        conn.close()


def test_user_approved_t4_copy_reads_separate_run_snapshot(tmp_path):
    annual = make_conn(tmp_path / "annual")
    run = make_conn(tmp_path / "run")
    try:
        insert_plan_series(run, cc="1412000005")
        copied = copy_missing_baselines_from_april(
            annual,
            2027,
            target_cc="1412000005",
            source_conn=run,
        )
        annual.commit()

        assert copied == ["1412000005"]
        baseline = fiscal_baseline_period(2027)
        saved = annual.execute(
            """SELECT headcount_all,headcount_expat,headcount_staff,headcount_worker,
                      description,source_file,source_sheet
               FROM fact_manual_headcount_baseline_override
               WHERE period=? AND cc_code='1412000005'""",
            (baseline,),
        ).fetchone()
        assert tuple(saved[:4]) == (15, 1, 10, 4)
        assert saved[4] == "USER_APPROVED_BASELINE_T3_FROM_T4"
        applied = annual.execute(
            """SELECT headcount_all,source,description FROM fact_monthly_headcount
               WHERE period=? AND cc_code='1412000005'""",
            (baseline,),
        ).fetchone()
        assert tuple(applied) == (15, "manual", "USER_APPROVED_BASELINE_T3_FROM_T4")
        assert run.execute(
            "SELECT 1 FROM fact_monthly_headcount WHERE period=? AND cc_code='1412000005'",
            (baseline,),
        ).fetchone() is None
    finally:
        annual.close()
        run.close()


def test_failed_run_database_resolver_accepts_only_expected_fy_history(tmp_path):
    history = tmp_path / "RUN_HISTORY"
    expected = history / "FY2027" / "run-005"
    reports = expected / "reports"
    reports.mkdir(parents=True)
    run_db = expected / "run.db"
    run_db.touch()
    trace = reports / "failure_traceback.txt"
    trace.touch()
    lines = [f"Chi tiết lỗi đã lưu: {trace}"]

    assert _failed_run_database_from_output(lines, str(history), 2027) == str(run_db.resolve())
    assert _failed_run_database_from_output(lines, str(history), 2028) is None

    outside = tmp_path / "outside" / "reports"
    outside.mkdir(parents=True)
    outside_trace = outside / "failure_traceback.txt"
    outside_trace.touch()
    (outside.parent / "run.db").touch()
    assert _failed_run_database_from_output(
        [f"Chi tiết lỗi đã lưu: {outside_trace}"], str(history), 2027
    ) is None


def test_t4_copy_rejects_missing_required_staffing_components(tmp_path):
    annual = make_conn(tmp_path / "annual")
    run = make_conn(tmp_path / "run")
    try:
        run.execute(
            """INSERT INTO fact_monthly_headcount
               (period,cc_code,headcount_all,headcount_expat,headcount_staff,
                headcount_worker,headcount_local_total,source,split_status)
               VALUES('202604','1412000005',NULL,0,103,1373,1476,'department_plan','READY')"""
        )
        with pytest.raises(ValueError, match="thiếu thành phần nhân sự bắt buộc"):
            copy_missing_baselines_from_april(
                annual,
                2027,
                target_cc="1412000005",
                source_conn=run,
            )
        assert annual.execute(
            "SELECT 1 FROM fact_manual_headcount_baseline_override"
        ).fetchone() is None
    finally:
        annual.close()
        run.close()
