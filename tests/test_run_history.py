from pathlib import Path

from src.services.fiscal_run import create_fiscal_run_context
from src.services.run_history import (
    RUN_STATUS_FAILED,
    RUN_STATUS_LEGACY_FY2027,
    RUN_STATUS_RUNNING,
    RUN_STATUS_SUCCEEDED,
    create_run_workspace,
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
