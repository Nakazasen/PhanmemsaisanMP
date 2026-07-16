import json
import os
from pathlib import Path

from src.parsers.manual_event_drivers import _default_period_for_fiscal_year
from src.parsers.nnn_paperwork import month_map_for_fiscal_year
from src.services.fiscal_run import (
    _filename_period_coverage,
    annual_default_paths,
    create_fiscal_run_context,
    inspect_fiscal_year_evidence,
    preflight_fiscal_run,
    validate_fiscal_year_evidence,
)
from src.utils.fiscal_periods import fiscal_baseline_period, fiscal_periods
from src.utils.source_manifest import read_source_manifest
from src.services.project_config import (
    ProjectConfig,
    discover_or_create_project,
    read_last_project,
    remember_last_project,
)
from scripts.run_e2e import _resolve_primary_reference_path


def test_fiscal_periods_are_unbounded_and_keep_april_to_march_boundary():
    assert fiscal_periods(2028) == [
        "202704", "202705", "202706", "202707", "202708", "202709",
        "202710", "202711", "202712", "202801", "202802", "202803",
    ]
    assert fiscal_baseline_period(2028) == "202703"
    assert fiscal_periods(2029)[0] == "202804"
    assert fiscal_periods(2029)[-1] == "202903"


def test_new_fy_defaults_use_only_its_own_directories(tmp_path):
    defaults = annual_default_paths(2028, tmp_path)
    assert defaults["template_path"] == str(tmp_path / "docs" / "MP2028" / "FORM.xlsx")
    assert defaults["source_dir"] == str(tmp_path / "docs" / "MP2028")
    assert defaults["headcount_source_dir"] == str(tmp_path / "raw" / "FY2028")
    assert defaults["output_dir"] == str(tmp_path / "OUTPUT_FY2028")


def test_preflight_fy2028_never_falls_back_to_fy2027_sources(tmp_path):
    legacy_dir = tmp_path / "raw"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "only_FY2027.xlsx").write_bytes(b"not an FY2028 policy")
    (tmp_path / "docs" / "MP2028").mkdir(parents=True)
    (tmp_path / "raw" / "FY2028").mkdir(parents=True)

    context = create_fiscal_run_context(2028, base_dir=tmp_path)
    report = preflight_fiscal_run(context)

    assert not report.ok
    assert context.uniform_policy_path is None
    assert not report.resolved_sources["uniform_policy"]
    assert any(issue.category == "uniform_policy" for issue in report.issues)
    assert all("FY2027" not in " ".join(paths) for paths in report.resolved_sources.values())
    checks = report.as_dict()["checks"]
    assert any(check["category"] == "uniform_policy" and check["status"] == "FAILED" for check in checks)
    assert "Kiểm tra nguồn trước khi chạy FY2028" in report.as_markdown()


def test_dynamic_event_and_nnn_month_mappings_use_selected_fiscal_year():
    assert _default_period_for_fiscal_year({"period": "202604"}, 2028) == "202704"
    assert _default_period_for_fiscal_year({"period": "202702"}, 2028) == "202802"

    mapping = month_map_for_fiscal_year(2028)
    assert mapping["202704"] == 0
    assert mapping["202803"] == 11
    assert "202604" not in mapping


def test_system_source_filename_ranges_cover_the_selected_fiscal_year():
    covered = set()
    for name in (
        "system_FY2028_Apr.2027 ~ June.2027.xls",
        "system_FY2028_July.2027 ~ Dec.2027.xls",
        "system_FY2028_Jan.2028 ~ March.2028.xls",
    ):
        covered.update(_filename_period_coverage(name, 2028))
    assert covered == set(fiscal_periods(2028))


def test_manifest_cannot_escape_selected_annual_source_directory(tmp_path):
    source_dir = tmp_path / "docs" / "MP2028"
    source_dir.mkdir(parents=True)
    (tmp_path / "docs" / "MP2027.xlsx").write_bytes(b"legacy")
    (source_dir / "source_file_order.csv").write_text(
        "order,category,filename,enabled\n1,facility,../MP2027.xlsx,1\n",
        encoding="utf-8",
    )
    entries = read_source_manifest(str(source_dir), include_missing=True)
    assert entries[0]["_invalid_path"] == "1"


def test_future_manual_input_store_rejects_rows_from_another_fy(tmp_path):
    from src.db.schema import create_schema, get_connection

    annual_dir = tmp_path / "raw" / "FY2028"
    annual_dir.mkdir(parents=True)
    store = annual_dir / "manual_inputs.db"
    conn = get_connection(str(store))
    create_schema(conn)
    conn.execute(
        "INSERT INTO fact_bus_headcount_drivers(cc_code,fiscal_year,bus_expat_count) VALUES('CC',2027,1)"
    )
    conn.commit()
    conn.close()
    context = create_fiscal_run_context(
        2028,
        headcount_source_dir=annual_dir,
        manual_input_store=str(store),
        base_dir=tmp_path,
    )

    report = preflight_fiscal_run(context)

    assert any(issue.category == "manual_inputs" for issue in report.issues)


def test_future_fy_reference_must_be_explicit_and_same_year(tmp_path):
    legacy = tmp_path / "reference FY2027.xlsx"
    legacy.write_bytes(b"not a workbook")
    try:
        _resolve_primary_reference_path("CC", str(legacy), fiscal_year=2028)
    except ValueError as exc:
        assert "FY2028" in str(exc)
    else:
        raise AssertionError("cross-year reference must be rejected")

    try:
        _resolve_primary_reference_path("CC", None, fiscal_year=2028)
    except ValueError as exc:
        assert "FY từ 2028" in str(exc)
    else:
        raise AssertionError("future FY reference must be explicit")

    unknown = tmp_path / "reference.xlsx"
    unknown.write_bytes(b"not a workbook")
    try:
        _resolve_primary_reference_path("CC", str(unknown), fiscal_year=2028)
    except ValueError as exc:
        assert "FY2028" in str(exc)
    else:
        raise AssertionError("future FY reference with no annual evidence must be rejected")


def test_fy_filename_cannot_mask_a_conflicting_business_sheet(tmp_path):
    from openpyxl import Workbook

    workbook_path = tmp_path / "reference_FY2028.xlsx"
    workbook = Workbook()
    workbook.active.title = "FY2027"
    workbook.active["A1"] = "FY2027 approved result"
    workbook.save(workbook_path)

    evidence = inspect_fiscal_year_evidence(workbook_path)
    assert evidence.conflict
    assert validate_fiscal_year_evidence(evidence, 2028)
    try:
        _resolve_primary_reference_path("CC", str(workbook_path), fiscal_year=2028)
    except ValueError as exc:
        assert "FY2028" in str(exc)
    else:
        raise AssertionError("conflicting evidence must be rejected")


def test_project_paths_are_relative_and_portable_when_project_moves(tmp_path):
    original = tmp_path / "original"
    original.mkdir()
    project = ProjectConfig.create_legacy_compatible(str(original), 2027)
    project.save()

    payload = json.loads((original / "project.json").read_text(encoding="utf-8"))
    assert payload["operational_database"] == "mp2027.db"
    assert payload["fiscal_years"]["2027"]["manual_input_store"] == "raw/FY2027/manual_inputs.db"

    moved = tmp_path / "moved"
    original.rename(moved)
    reloaded = ProjectConfig.load(str(moved / "project.json"))
    paths = reloaded.fiscal_paths(2027)

    assert reloaded.operational_database == os.path.abspath(moved / "mp2027.db")
    assert paths.template_path == os.path.abspath(moved / "docs" / "MP2027" / "FORM.xlsx")
    assert paths.manual_input_store == os.path.abspath(moved / "raw" / "FY2027" / "manual_inputs.db")


def test_manual_input_store_is_physically_isolated_by_fiscal_year(tmp_path):
    project = ProjectConfig.create_legacy_compatible(str(tmp_path), 2027)
    project.ensure_fiscal_year(2028)

    fy2027 = project.fiscal_paths(2027)
    fy2028 = project.fiscal_paths(2028)

    assert fy2027.manual_input_store != fy2028.manual_input_store
    assert fy2027.manual_input_store.endswith(os.path.join("raw", "FY2027", "manual_inputs.db"))
    assert fy2028.manual_input_store.endswith(os.path.join("raw", "FY2028", "manual_inputs.db"))


def test_recent_project_is_loaded_automatically_from_local_app_data(tmp_path):
    app_dir = tmp_path / "application"
    project_dir = tmp_path / "business-data"
    local_app_data = tmp_path / "local-app-data"
    app_dir.mkdir()
    project_dir.mkdir()

    project = ProjectConfig.create_legacy_compatible(str(project_dir), 2027)
    project.save()
    remember_last_project(project.config_path, local_app_data=str(local_app_data))

    assert read_last_project(local_app_data=str(local_app_data)) == project.config_path
    discovered, created = discover_or_create_project(
        str(app_dir), 2027, local_app_data=str(local_app_data)
    )

    assert created is False
    assert discovered.config_path == project.config_path
    assert not (app_dir / "project.json").exists()


def test_project_rejects_shared_manual_store_without_partial_mutation(tmp_path):
    project = ProjectConfig.create_legacy_compatible(str(tmp_path), 2027)
    project.ensure_fiscal_year(2028)
    original = json.dumps(project.data, sort_keys=True)
    shared_store = project.fiscal_paths(2027).manual_input_store

    try:
        project.update_fiscal_paths(2028, manual_input_store=shared_store)
    except ValueError as exc:
        assert "không được dùng chung kho nhập tay" in str(exc)
    else:
        raise AssertionError("two fiscal years must not share one manual input store")

    assert json.dumps(project.data, sort_keys=True) == original


def test_project_rejects_operational_database_that_is_a_manual_store(tmp_path):
    project = ProjectConfig.create_legacy_compatible(str(tmp_path), 2027)
    original = json.dumps(project.data, sort_keys=True)
    manual_store = project.fiscal_paths(2027).manual_input_store

    try:
        project.set_operational_database(manual_store)
    except ValueError as exc:
        assert "không được trùng kho nhập tay FY2027" in str(exc)
    else:
        raise AssertionError("operational database must not also be a manual input store")

    assert json.dumps(project.data, sort_keys=True) == original


def test_project_load_rejects_manual_store_reused_by_two_fiscal_years(tmp_path):
    project = ProjectConfig.create_legacy_compatible(str(tmp_path), 2027)
    project.ensure_fiscal_year(2028)
    project.data["fiscal_years"]["2028"]["manual_input_store"] = (
        project.data["fiscal_years"]["2027"]["manual_input_store"]
    )
    project.save()

    try:
        ProjectConfig.load(project.config_path)
    except ValueError as exc:
        assert "không được dùng chung kho nhập tay" in str(exc)
    else:
        raise AssertionError("invalid manually edited project.json must be rejected at load time")
