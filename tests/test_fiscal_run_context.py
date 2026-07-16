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
