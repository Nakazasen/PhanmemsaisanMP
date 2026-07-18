import json
from pathlib import Path
import shutil
import sqlite3

import src.services.run_history as run_history_module
from src.services.fiscal_run import create_fiscal_run_context
from src.services.run_history import (
    PipelineStageEvidence,
    RUN_STATUS_FAILED,
    RUN_STATUS_LEGACY_FY2027,
    RUN_STATUS_PRECHECK_FAILED,
    RUN_STATUS_RUNNING,
    RUN_STATUS_SUCCEEDED,
    RUN_STATUS_SUCCEEDED_INCOMPLETE,
    create_run_workspace,
    filter_runs,
    list_runs,
    register_run,
    register_legacy_fy2027_database,
    write_run_manifest,
    publish_run_output,
)
from src.db.schema import create_schema, get_connection
from src.services.manual_staffing_overrides import copy_annual_manual_inputs
from scripts.run_e2e import run_universal_pipeline


def test_each_run_gets_immutable_year_scoped_workspace_and_catalogue(tmp_path):
    template = tmp_path / "FORM.xlsx"
    template.write_bytes(b"template")
    output_dir = tmp_path / "OUTPUT_FY2028"
    context = create_fiscal_run_context(
        2028,
        template_path=template,
        source_dir=tmp_path / "sources",
        headcount_source_dir=tmp_path / "headcount",
        output_dir=output_dir,
        history_root=tmp_path / "RUN_HISTORY",
        run_id="run-2028-a",
    ).with_resolution({})

    workspace_context = create_run_workspace(context, target_cc="1412000036")
    manifest = Path(write_run_manifest(workspace_context))
    register_run(workspace_context, RUN_STATUS_SUCCEEDED, target_cc="1412000036", output_path=str(output_dir))

    assert Path(workspace_context.workspace_dir) == tmp_path / "RUN_HISTORY" / "FY2028" / "run-2028-a"
    assert Path(workspace_context.database_path).name == "run.db"
    assert Path(workspace_context.database_path).is_file()
    assert manifest.is_file()
    rows = list_runs(str(tmp_path / "RUN_HISTORY"), 2028)
    assert len(rows) == 1
    assert rows[0]["run_id"] == "run-2028-a"
    assert rows[0]["status"] == RUN_STATUS_SUCCEEDED


def test_failed_run_does_not_replace_another_year_history(tmp_path):
    history = tmp_path / "RUN_HISTORY"
    first = create_fiscal_run_context(2027, history_root=history, run_id="fy2027")
    second = create_fiscal_run_context(2028, history_root=history, run_id="fy2028")

    register_run(first, RUN_STATUS_RUNNING)
    register_run(first, RUN_STATUS_SUCCEEDED)
    register_run(second, RUN_STATUS_RUNNING)
    register_run(second, RUN_STATUS_FAILED, error_summary="missing FY2028 source")

    assert [row["fiscal_year"] for row in list_runs(str(history), 2027)] == [2027]
    rows_2028 = list_runs(str(history), 2028)
    assert len(rows_2028) == 1
    assert rows_2028[0]["status"] == RUN_STATUS_FAILED


def test_preflight_failure_is_kept_in_its_own_history_workspace(tmp_path):
    messages = []
    ok, _message = run_universal_pipeline(
        fiscal_year=2028,
        template_path=str(tmp_path / "missing_FORM.xlsx"),
        source_dir=str(tmp_path / "missing_sources"),
        headcount_source_dir=str(tmp_path / "missing_headcount"),
        output_dir=str(tmp_path / "OUTPUT_FY2028"),
        run_history_root=str(tmp_path / "RUN_HISTORY"),
        log_callback=messages.append,
    )

    assert not ok
    rows = list_runs(str(tmp_path / "RUN_HISTORY"), 2028)
    assert len(rows) == 1
    assert rows[0]["status"] == "PRECHECK_FAILED"
    workspace = tmp_path / "RUN_HISTORY" / "FY2028" / str(rows[0]["run_id"])
    assert (workspace / "run.db").is_file()
    assert (workspace / "run_manifest.json").is_file()
    assert (workspace / "reports" / "preflight_report.json").is_file()
    assert (workspace / "reports" / "preflight_report.md").is_file()
    evidence = json.loads(
        (workspace / "reports" / "pipeline_stage_evidence.json").read_text(encoding="utf-8")
    )
    assert evidence["status"] == RUN_STATUS_PRECHECK_FAILED
    assert evidence["current_stage"] is None
    assert [stage["name"] for stage in evidence["stages"]] == ["preflight"]
    assert evidence["stages"][0]["status"] == "FAIL"
    assert evidence["stages"][0]["error_summary"]
    assert evidence["error_summary"]


def test_terminal_history_cannot_be_mutated(tmp_path):
    context = create_fiscal_run_context(2028, history_root=tmp_path, run_id="immutable")
    register_run(context, RUN_STATUS_RUNNING)
    register_run(context, RUN_STATUS_SUCCEEDED, output_path="done")
    try:
        register_run(context, RUN_STATUS_FAILED, error_summary="late change")
    except ValueError as exc:
        assert "không thể sửa" in str(exc)
    else:
        raise AssertionError("terminal run must be immutable")


def test_publish_replaces_the_complete_directory_without_leaving_stale_files(tmp_path):
    destination = tmp_path / "OUTPUT_FY2028"
    destination.mkdir()
    (destination / "old.txt").write_text("old", encoding="utf-8")
    staged = tmp_path / "staged"
    staged.mkdir()
    (staged / "new.txt").write_text("new", encoding="utf-8")
    context = create_fiscal_run_context(2028, output_dir=destination, history_root=tmp_path, run_id="publish")
    assert publish_run_output(context, str(staged)) == str(destination)
    assert (destination / "new.txt").read_text(encoding="utf-8") == "new"
    assert not (destination / "old.txt").exists()


def test_publish_failure_restores_the_previous_public_output(tmp_path):
    destination = tmp_path / "OUTPUT_FY2028"
    destination.mkdir()
    (destination / "accepted.txt").write_text("accepted", encoding="utf-8")
    staged = tmp_path / "staged"
    staged.mkdir()
    (staged / "new.txt").write_text("new", encoding="utf-8")
    context = create_fiscal_run_context(2028, output_dir=destination, history_root=tmp_path, run_id="rollback")

    def fail_after_backup(stage):
        if stage == "backed_up":
            raise RuntimeError("simulated publication failure")

    try:
        publish_run_output(context, str(staged), failure_injector=fail_after_backup)
    except RuntimeError:
        pass
    else:
        raise AssertionError("publication failure must be surfaced")

    assert (destination / "accepted.txt").read_text(encoding="utf-8") == "accepted"
    assert not (destination / "new.txt").exists()
    assert not list(tmp_path.glob(".OUTPUT_FY2028.*"))


def test_publish_merge_updates_only_target_cc_and_current_reports(tmp_path):
    destination = tmp_path / "OUTPUT_FY2028"
    reports = destination / "BAO_CAO_KIEM_TRA"
    reports.mkdir(parents=True)
    (destination / "MP_CC_1412000006.xlsx").write_bytes(b"accepted-cc06")
    (destination / "MP_CC_1412000004.xlsx").write_bytes(b"old-cc04")
    (reports / "BAO_CAO_LAN_CHAY.xlsx").write_bytes(b"old-report")

    staged = tmp_path / "staged"
    staged_reports = staged / "BAO_CAO_KIEM_TRA"
    staged_reports.mkdir(parents=True)
    (staged / "MP_CC_1412000004.xlsx").write_bytes(b"new-cc04")
    (staged_reports / "BAO_CAO_LAN_CHAY.xlsx").write_bytes(b"new-report")
    context = create_fiscal_run_context(2028, output_dir=destination, history_root=tmp_path, run_id="merge")

    assert publish_run_output(
        context,
        str(staged),
        mode="merge",
        target_cc="1412000004",
    ) == str(destination)

    assert (destination / "MP_CC_1412000006.xlsx").read_bytes() == b"accepted-cc06"
    assert (destination / "MP_CC_1412000004.xlsx").read_bytes() == b"new-cc04"
    assert (destination / "BAO_CAO_KIEM_TRA" / "BAO_CAO_LAN_CHAY.xlsx").read_bytes() == b"new-report"
    assert not list(tmp_path.glob(".OUTPUT_FY2028.*"))


def test_publish_merge_does_not_delete_prepared_report_directory(tmp_path, monkeypatch):
    destination = tmp_path / "OUTPUT_FY2028"
    reports = destination / "BAO_CAO_KIEM_TRA"
    reports.mkdir(parents=True)
    (destination / "MP_CC_1412000004.xlsx").write_bytes(b"old-cc04")
    (reports / "BAO_CAO_LAN_CHAY.xlsx").write_bytes(b"old-report")

    staged = tmp_path / "staged"
    staged_reports = staged / "BAO_CAO_KIEM_TRA"
    staged_reports.mkdir(parents=True)
    (staged / "MP_CC_1412000004.xlsx").write_bytes(b"new-cc04")
    (staged_reports / "BAO_CAO_LAN_CHAY.xlsx").write_bytes(b"new-report")
    context = create_fiscal_run_context(2028, output_dir=destination, history_root=tmp_path, run_id="merge-no-delete")

    real_rmtree = shutil.rmtree

    def reject_report_delete(path, *args, **kwargs):
        candidate = Path(path)
        if candidate.name == "BAO_CAO_KIEM_TRA" and ".publishing" in str(candidate.parent):
            raise AssertionError("merge must not delete the prepared report directory")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(run_history_module.shutil, "rmtree", reject_report_delete)

    assert publish_run_output(
        context,
        str(staged),
        mode="merge",
        target_cc="1412000004",
    ) == str(destination)
    assert (reports / "BAO_CAO_LAN_CHAY.xlsx").read_bytes() == b"new-report"
    assert not list(tmp_path.glob(".OUTPUT_FY2028.*"))


def test_successful_publish_retains_locked_backup_without_failing(tmp_path, monkeypatch):
    destination = tmp_path / "OUTPUT_FY2028"
    destination.mkdir()
    (destination / "accepted.txt").write_text("accepted", encoding="utf-8")
    staged = tmp_path / "staged"
    staged.mkdir()
    (staged / "new.txt").write_text("new", encoding="utf-8")
    context = create_fiscal_run_context(
        2028,
        output_dir=destination,
        history_root=tmp_path,
        run_id="locked-backup",
    )

    real_rmtree = shutil.rmtree
    locked_attempts = []

    def lock_retired_backup(path, *args, **kwargs):
        candidate = Path(path)
        if candidate.name.endswith(".backup"):
            locked_attempts.append(candidate)
            raise PermissionError(5, "simulated Windows backup lock", str(candidate))
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(run_history_module.shutil, "rmtree", lock_retired_backup)
    monkeypatch.setattr(run_history_module.time, "sleep", lambda _seconds: None)

    assert publish_run_output(context, str(staged)) == str(destination)
    backup = tmp_path / ".OUTPUT_FY2028.locked-backup.backup"
    assert len(locked_attempts) == 6
    assert (destination / "new.txt").read_text(encoding="utf-8") == "new"
    assert not (destination / "accepted.txt").exists()
    assert (backup / "accepted.txt").read_text(encoding="utf-8") == "accepted"


def test_publish_merge_failure_after_publish_restores_complete_public_output(tmp_path):
    destination = tmp_path / "OUTPUT_FY2028"
    destination.mkdir()
    (destination / "MP_CC_1412000006.xlsx").write_bytes(b"accepted-cc06")
    (destination / "MP_CC_1412000004.xlsx").write_bytes(b"accepted-cc04")
    staged = tmp_path / "staged"
    staged.mkdir()
    (staged / "MP_CC_1412000004.xlsx").write_bytes(b"rejected-cc04")
    context = create_fiscal_run_context(2028, output_dir=destination, history_root=tmp_path, run_id="merge-rollback")

    def fail_after_publish(stage):
        if stage == "published":
            raise RuntimeError("simulated merge publication failure")

    try:
        publish_run_output(
            context,
            str(staged),
            mode="merge",
            target_cc="1412000004",
            failure_injector=fail_after_publish,
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("merge publication failure must be surfaced")

    assert (destination / "MP_CC_1412000006.xlsx").read_bytes() == b"accepted-cc06"
    assert (destination / "MP_CC_1412000004.xlsx").read_bytes() == b"accepted-cc04"
    assert not list(tmp_path.glob(".OUTPUT_FY2028.*"))


def test_legacy_fy2027_database_is_catalogued_without_modifying_the_file(tmp_path):
    history = tmp_path / "RUN_HISTORY"
    legacy = tmp_path / "mp2027.db"
    legacy.write_bytes(b"legacy-db-content")
    before = legacy.read_bytes()

    run_id = register_legacy_fy2027_database(str(history), legacy)

    assert run_id
    assert legacy.read_bytes() == before
    rows = list_runs(str(history), 2027)
    assert len(rows) == 1
    assert rows[0]["status"] == RUN_STATUS_LEGACY_FY2027
    assert rows[0]["database_path"] == str(legacy.resolve())


def test_annual_manual_input_store_is_copied_only_for_selected_fy(tmp_path):
    input_db = tmp_path / "manual_inputs.db"
    source = get_connection(str(input_db))
    create_schema(source)
    source.execute(
        "INSERT INTO fact_manual_headcount_baseline_override(period,cc_code,fiscal_year,headcount_all) VALUES('202703','CC',2028,9)"
    )
    source.execute(
        "INSERT INTO fact_manual_headcount_baseline_override(period,cc_code,fiscal_year,headcount_all) VALUES('202603','CC',2027,7)"
    )
    source.commit()
    target = get_connection(str(tmp_path / "run.db"))
    create_schema(target)
    copied = copy_annual_manual_inputs(target, 2028, input_db)
    assert copied["fact_manual_headcount_baseline_override"] == 1
    assert target.execute(
        "SELECT headcount_all FROM fact_manual_headcount_baseline_override WHERE period='202703'"
    ).fetchone()[0] == 9
    assert target.execute(
        "SELECT COUNT(*) FROM fact_manual_headcount_baseline_override WHERE period='202603'"
    ).fetchone()[0] == 0


def test_unscoped_manual_input_is_not_copied_into_a_new_fy_run(tmp_path):
    input_db = tmp_path / "manual_inputs.db"
    source = get_connection(str(input_db))
    create_schema(source)
    source.execute(
        "INSERT INTO fact_manual_headcount_baseline_override(period,cc_code,headcount_all) VALUES('202703','CC',9)"
    )
    source.commit()
    target = get_connection(str(tmp_path / "run.db"))
    create_schema(target)

    copied = copy_annual_manual_inputs(target, 2028, input_db)

    assert copied["fact_manual_headcount_baseline_override"] == 0


def test_selected_fy_bus_input_is_copied_and_visible_to_the_run(tmp_path):
    input_db = tmp_path / "manual_inputs.db"
    source = get_connection(str(input_db))
    create_schema(source)
    source.execute(
        """INSERT INTO fact_bus_headcount_drivers
           (cc_code,fiscal_year,bus_expat_count,bus_vietnamese_count,source)
           VALUES('CC',2028,3,4,'manual')"""
    )
    source.commit()
    target = get_connection(str(tmp_path / "run.db"))
    create_schema(target)

    copied = copy_annual_manual_inputs(target, 2028, input_db)

    assert copied["fact_bus_headcount_drivers"] == 1
    row = target.execute(
        "SELECT fiscal_year,bus_expat_count,bus_vietnamese_count FROM fact_bus_headcount_drivers WHERE cc_code='CC'"
    ).fetchone()
    assert tuple(row) == (2028, 3, 4)


def test_pipeline_connection_cleanup_rolls_back_before_close():
    from scripts.run_e2e import _close_pipeline_connection

    events = []

    class Connection:
        def rollback(self):
            events.append("rollback")

        def close(self):
            events.append("close")

    _close_pipeline_connection(Connection(), rollback=True)

    assert events == ["rollback", "close"]


def test_pipeline_connection_cleanup_does_not_mask_original_failure():
    from scripts.run_e2e import _close_pipeline_connection

    messages = []

    class BrokenConnection:
        def rollback(self):
            raise RuntimeError("rollback failed")

        def close(self):
            raise RuntimeError("close failed")

    _close_pipeline_connection(
        BrokenConnection(),
        rollback=True,
        log_callback=messages.append,
        suppress_errors=True,
    )

    assert len(messages) == 1
    assert "rollback failed" in messages[0]
    assert "close failed" in messages[0]


def test_pipeline_stage_evidence_is_atomic_and_terminal(tmp_path):
    recorder = PipelineStageEvidence(tmp_path, "run-stage-test")

    recorder.start("preflight")
    recorder.complete(details={"status": "PASS"})
    recorder.finalize(RUN_STATUS_SUCCEEDED)

    payload = json.loads(recorder.path.read_text(encoding="utf-8"))
    assert payload["run_id"] == "run-stage-test"
    assert payload["status"] == RUN_STATUS_SUCCEEDED
    assert payload["current_stage"] is None
    assert payload["total_elapsed_seconds"] >= 0
    assert payload["stages"] == [
        {
            "name": "preflight",
            "status": "PASS",
            "elapsed_seconds": payload["stages"][0]["elapsed_seconds"],
            "finished_at": payload["stages"][0]["finished_at"],
            "details": {"status": "PASS"},
        }
    ]
    assert not recorder.path.with_suffix(".json.tmp").exists()


def test_incomplete_success_is_a_distinct_terminal_history_state(tmp_path):
    context = create_fiscal_run_context(2028, history_root=tmp_path, run_id="incomplete")
    register_run(context, RUN_STATUS_RUNNING)
    register_run(
        context,
        RUN_STATUS_SUCCEEDED_INCOMPLETE,
        output_path="published",
        error_summary="KẾT QUẢ CHƯA ĐẦY ĐỦ",
    )

    rows = list_runs(str(tmp_path), 2028)
    assert rows[0]["status"] == RUN_STATUS_SUCCEEDED_INCOMPLETE
    assert rows[0]["error_summary"] == "KẾT QUẢ CHƯA ĐẦY ĐỦ"


def test_filter_runs_matches_item_without_failing_on_incomplete_run_database(tmp_path):
    history = tmp_path / "RUN_HISTORY"
    first = create_run_workspace(
        create_fiscal_run_context(2028, history_root=history, run_id="matching"),
        target_cc="1412000036",
    )
    create_run_workspace(
        create_fiscal_run_context(2028, history_root=history, run_id="without-table"),
        target_cc="1412000099",
    )

    conn = sqlite3.connect(first.database_path)
    try:
        conn.execute("CREATE TABLE fact_input_data (source TEXT, description TEXT)")
        conn.execute(
            "INSERT INTO fact_input_data(source, description) VALUES (?, ?)",
            ("facility", "Chi phí thuê văn phòng"),
        )
        conn.commit()
    finally:
        conn.close()

    rows = filter_runs(str(history), 2028, item="thuê văn phòng")
    assert [row["run_id"] for row in rows] == ["matching"]

    rows = filter_runs(str(history), 2028, cost_center="1412000099")
    assert [row["run_id"] for row in rows] == ["without-table"]
