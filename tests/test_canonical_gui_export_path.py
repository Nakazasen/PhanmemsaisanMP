import ast
from pathlib import Path
from types import SimpleNamespace

from src.services.fiscal_run import RunPreflightReport, SourceIssue


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _tree(path: str) -> ast.AST:
    return ast.parse(_source(path))


def test_gui_runs_pipeline_out_of_process():
    source = _source("src/universal_app.py")
    assert "subprocess.Popen" in source
    assert "scripts\", \"run_e2e.py" in source
    assert "run_universal_pipeline(" not in source
    assert "--legacy-export" not in source


def test_run_universal_pipeline_default_is_canonical():
    tree = _tree("scripts/run_e2e.py")
    funcs = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "run_universal_pipeline"]
    assert funcs
    defaults = funcs[0].args.defaults
    assert isinstance(defaults[-1], ast.Constant)
    assert defaults[-1].value is True


def test_cli_always_uses_canonical_export_mode():
    source = Path("scripts/run_e2e.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    call = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "run_universal_pipeline"][-1]
    kw = {keyword.arg: keyword.value for keyword in call.keywords}
    assert isinstance(kw["mp_saisan_complete_v1"], ast.Constant)
    assert kw["mp_saisan_complete_v1"].value is True
    assert "--legacy-export" not in source


def test_reference_path_resolves_from_map_for_canonical_source_order():
    source = _source("scripts/run_e2e.py")
    assert "def _resolve_primary_reference_path" in source
    assert "def _try_resolve_primary_reference_path" in source
    assert 'target_text = str(target_cc or "")' in source
    assert 'row.get("target_cc") == target_text' in source
    assert 'return str(target_cc or "") == "1412000040"' not in source
    assert "complete_v1_primary_path = _try_resolve_primary_reference_path" in source
    assert "if mp_saisan_complete_v1 and complete_v1_primary_path:" in source


def test_source_order_writers_are_enabled_by_canonical_default():
    source = _source("scripts/run_e2e.py")
    assert "if mp_saisan_complete_v1:" in source
    assert "facility_file_order_export = True" in source
    assert "COMPLETE_V1_SOURCE_ORDER_START_ROW = 38" in source
    assert '"clear_until_row": None' in source
    assert 'phase="final"' in source
    assert "source_file_order=_annual_complete_v1_source_order(run_context)" in source


def test_complete_v1_output_order_uses_only_eligible_saved_manifest_entries():
    import scripts.run_e2e as run_e2e

    context = SimpleNamespace(
        resolved_sources={
            "facility": (r"C:\\raw\\facility.xlsx",),
            "ga": (r"C:\\raw\\ga.xlsx",),
            "birthday": (r"C:\\raw\\birthday.xlsx",),
        },
        ordered_sources=(
            {"path": r"C:\\raw\\birthday.xlsx", "filename": "birthday.xlsx"},
            {"path": r"C:\\raw\\disabled.xlsx", "filename": "disabled.xlsx"},
            {"path": r"C:\\raw\\ga.xlsx", "filename": "ga.xlsx"},
            {"path": r"C:\\raw\\facility.xlsx", "filename": "facility.xlsx"},
        ),
    )

    assert run_e2e._annual_complete_v1_output_source_order(context) == [
        "birthday.xlsx",
        "ga.xlsx",
        "facility.xlsx",
    ]


def test_complete_v1_output_order_appends_eligible_legacy_fallbacks():
    import scripts.run_e2e as run_e2e

    context = SimpleNamespace(
        resolved_sources={
            "facility": (r"C:\\raw\\facility.xlsx",),
            "ga": (r"C:\\raw\\ga.xlsx",),
            "birthday": (r"C:\\raw\\birthday.xlsx",),
        },
        ordered_sources=(
            {"path": r"C:\\raw\\ga.xlsx", "filename": "ga.xlsx"},
        ),
    )

    assert run_e2e._annual_complete_v1_output_source_order(context) == [
        "ga.xlsx",
        "facility.xlsx",
        "birthday.xlsx",
    ]


def test_complete_v1_single_export_finalizes_source_order_after_reference_layer(monkeypatch, tmp_path):
    import scripts.run_e2e as run_e2e

    calls = []

    class Cursor:
        def execute(self, *args, **kwargs):
            return None

        def fetchall(self):
            return []

        def fetchone(self):
            return (0,)

    class Conn:
        def cursor(self):
            return Cursor()

        def execute(self, *args, **kwargs):
            return Cursor()

        def executemany(self, *args, **kwargs):
            return Cursor()

        def commit(self):
            return None

        def rollback(self):
            return None

        def close(self):
            return None

    class Builder:
        def __init__(self, *args, **kwargs):
            pass

        def export_to_template(self, template_path, output_path, cc_code=None):
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text("placeholder", encoding="utf-8")
            calls.append("export")
            return True

    monkeypatch.chdir(tmp_path)
    (tmp_path / "raw").mkdir()
    monkeypatch.setattr(run_e2e, "get_connection", lambda db_path: Conn())
    monkeypatch.setattr(
        run_e2e,
        "preflight_fiscal_run",
        lambda context: RunPreflightReport(
            fiscal_year=2027,
            resolved_sources={
                "facility": (str(tmp_path / "facility.xlsx"),),
                "ga": (str(tmp_path / "ga.xlsx"),),
                "allocation_rules": (str(tmp_path / "allocation.xlsx"),),
                "it_simulation": tuple(str(tmp_path / f"it-{idx}.xlsx") for idx in range(3)),
            },
        ),
    )
    monkeypatch.setattr(
        run_e2e,
        "import_headcount_time_sources",
        lambda *args, **kwargs: {
            "files": 1,
            "imported_files": 1,
            "skipped": [],
            "errors": [],
            "results": [],
        },
    )
    monkeypatch.setattr(run_e2e, "_staffing_preflight", lambda *args, **kwargs: [])
    monkeypatch.setattr(run_e2e, "create_schema", lambda conn: None)
    monkeypatch.setattr(run_e2e, "init_sys_params", lambda conn, exchange_rate, fiscal_year, **kwargs: None)
    monkeypatch.setattr(run_e2e, "load_all", lambda **kwargs: None)
    monkeypatch.setattr(run_e2e, "describe_manifest", lambda source_dir: [])
    monkeypatch.setattr(run_e2e, "parse_facility", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "parse_fixed_assets", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "parse_it_simulation", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "parse_ga", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "parse_birthday_workbook", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "parse_manual_headcount", lambda conn, source_dir, base_dir=None: {})
    monkeypatch.setattr(run_e2e, "parse_manual_special_costs", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "parse_manual_event_drivers", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "parse_nnn_paperwork", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "AllocationEngine", lambda conn: type("Engine", (), {"run_allocation": lambda self: None})())
    monkeypatch.setattr(run_e2e, "HubBuilder", Builder)
    monkeypatch.setattr(run_e2e, "write_pipeline_audit_report", lambda **kwargs: {"report_path": "audit.md", "missing_csv_path": "missing.csv"})
    monkeypatch.setattr(run_e2e, "audit_exchange_rate_workbook", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "write_exchange_rate_audit_report", lambda *args, **kwargs: "exchange-audit.xlsx")
    monkeypatch.setattr(run_e2e, "apply_facility_file_order_to_workbook", lambda **kwargs: calls.append("facility"))
    monkeypatch.setattr(run_e2e, "apply_admin_consumables_to_workbook", lambda **kwargs: calls.append("admin"))
    monkeypatch.setattr(run_e2e, "apply_system_cost_to_workbook", lambda **kwargs: calls.append("system"))
    monkeypatch.setattr(run_e2e, "_resolve_primary_reference_path", lambda **kwargs: str(tmp_path / "ref.xlsx"))
    monkeypatch.setattr(run_e2e, "apply_mp_saisan_complete_v1", lambda **kwargs: calls.append("complete-reference") or {})

    def fake_source_order(workbook_path, start_row, clear_until_row, **kwargs):
        calls.append(("source-order", start_row, clear_until_row))
        return {"source_blocks_written": 1, "rows_written": 1, "blank_rows_written": 0, "start_row": start_row, "end_row": start_row}

    monkeypatch.setattr(run_e2e, "apply_complete_v1_source_order_to_workbook", fake_source_order)

    ok, _ = run_e2e.run_universal_pipeline(
        fiscal_year=2027,
        template_path="FORM.xlsx",
        source_dir="raw",
        exchange_rate=25450,
        target_cc=1412000040,
        primary_reference_path=str(tmp_path / "ref.xlsx"),
        reference_map_path=str(tmp_path / "map.csv"),
    )

    assert ok
    assert calls == [
        "export",
        "facility",
        "admin",
        "system",
        ("source-order", 38, None),
        "complete-reference",
        ("source-order", 38, None),
    ]


def test_complete_v1_single_export_without_reference_still_finalizes_source_order(monkeypatch, tmp_path):
    import scripts.run_e2e as run_e2e

    calls = []

    class Cursor:
        def execute(self, *args, **kwargs):
            return None

        def fetchall(self):
            return []

        def fetchone(self):
            return (0,)

    class Conn:
        def cursor(self):
            return Cursor()

        def execute(self, *args, **kwargs):
            return Cursor()

        def executemany(self, *args, **kwargs):
            return Cursor()

        def commit(self):
            return None

        def rollback(self):
            return None

        def close(self):
            return None

    class Builder:
        def __init__(self, *args, **kwargs):
            pass

        def export_to_template(self, template_path, output_path, cc_code=None):
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text("placeholder", encoding="utf-8")
            calls.append("export")
            return True

    monkeypatch.chdir(tmp_path)
    (tmp_path / "raw").mkdir()
    monkeypatch.setattr(run_e2e, "get_connection", lambda db_path: Conn())
    monkeypatch.setattr(
        run_e2e,
        "preflight_fiscal_run",
        lambda context: RunPreflightReport(
            fiscal_year=2027,
            issues=(
                SourceIssue(
                    category="uniform_policy",
                    path="",
                    detected_fiscal_year=None,
                    reason="Không có nguồn trong phạm vi lần chạy.",
                    action="Category được bỏ qua độc lập.",
                    status="SKIPPED",
                    severity="SOURCE_SKIPPED",
                ),
            ),
            resolved_sources={
                "facility": (str(tmp_path / "facility.xlsx"),),
                "ga": (str(tmp_path / "ga.xlsx"),),
                "allocation_rules": (str(tmp_path / "allocation.xlsx"),),
                "it_simulation": tuple(str(tmp_path / f"it-{idx}.xlsx") for idx in range(3)),
            },
        ),
    )
    monkeypatch.setattr(
        run_e2e,
        "import_headcount_time_sources",
        lambda *args, **kwargs: {
            "files": 1,
            "imported_files": 1,
            "skipped": [],
            "errors": [],
            "results": [],
        },
    )
    monkeypatch.setattr(run_e2e, "_staffing_preflight", lambda *args, **kwargs: [])
    monkeypatch.setattr(run_e2e, "create_schema", lambda conn: None)
    monkeypatch.setattr(run_e2e, "init_sys_params", lambda conn, exchange_rate, fiscal_year, **kwargs: None)
    monkeypatch.setattr(run_e2e, "load_all", lambda **kwargs: None)
    monkeypatch.setattr(run_e2e, "describe_manifest", lambda source_dir: [])
    monkeypatch.setattr(run_e2e, "parse_facility", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "parse_fixed_assets", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "parse_it_simulation", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "parse_ga", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "parse_birthday_workbook", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "parse_manual_headcount", lambda conn, source_dir, base_dir=None: {})
    monkeypatch.setattr(run_e2e, "parse_manual_special_costs", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "parse_manual_event_drivers", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "parse_nnn_paperwork", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "AllocationEngine", lambda conn: type("Engine", (), {"run_allocation": lambda self: None})())
    monkeypatch.setattr(run_e2e, "HubBuilder", Builder)
    monkeypatch.setattr(run_e2e, "write_pipeline_audit_report", lambda **kwargs: {"report_path": "audit.md", "missing_csv_path": "missing.csv"})
    monkeypatch.setattr(run_e2e, "audit_exchange_rate_workbook", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "write_exchange_rate_audit_report", lambda *args, **kwargs: "exchange-audit.xlsx")
    monkeypatch.setattr(run_e2e, "apply_facility_file_order_to_workbook", lambda **kwargs: calls.append("facility"))
    monkeypatch.setattr(run_e2e, "apply_admin_consumables_to_workbook", lambda **kwargs: calls.append("admin"))
    monkeypatch.setattr(run_e2e, "apply_system_cost_to_workbook", lambda **kwargs: calls.append("system"))
    monkeypatch.setattr(run_e2e, "_resolve_primary_reference_path", lambda **kwargs: (_ for _ in ()).throw(AssertionError("reference should not be required")))
    monkeypatch.setattr(run_e2e, "apply_mp_saisan_complete_v1", lambda **kwargs: calls.append("complete-reference") or {})

    def fake_source_order(workbook_path, start_row, clear_until_row, **kwargs):
        calls.append(("source-order", start_row, clear_until_row))
        return {"source_blocks_written": 1, "rows_written": 1, "blank_rows_written": 0, "start_row": start_row, "end_row": start_row}

    monkeypatch.setattr(run_e2e, "apply_complete_v1_source_order_to_workbook", fake_source_order)

    ok, published_output = run_e2e.run_universal_pipeline(
        fiscal_year=2027,
        template_path="FORM.xlsx",
        source_dir="raw",
        exchange_rate=25450,
        target_cc=1412000006,
        reference_map_path=None,
    )

    assert ok
    assert calls == [
        "export",
        "facility",
        "admin",
        "system",
        ("source-order", 38, None),
    ]
    incomplete_marker = Path(published_output) / "BAO_CAO_KIEM_TRA" / "KET_QUA_CHUA_DAY_DU.txt"
    assert incomplete_marker.is_file()
    assert "uniform_policy" in incomplete_marker.read_text(encoding="utf-8")


def test_fixed_assets_parser_uses_audited_header_detection_not_h_to_j_shortcut():
    text = Path("src/parsers/fixed_assets.py").read_text(encoding="utf-8")
    assert "HEADER_ALIASES" in text
    assert "LEGACY_COLUMN_MAP" in text
    assert '"control_cc": 7' in text
    assert "helpers.extract_cc_code(row[9]" not in text


def test_visible_header_fiscal_year_labels_follow_selected_run_year():
    from openpyxl import Workbook

    from src.engine.hub_builder import HubBuilder

    workbook = Workbook()
    visible = workbook.active
    visible.title = "Output"
    visible["A1"] = "MP FY2027_各予定"
    visible["A2"] = "FY 2027"
    visible["A3"] = '=IF(A2="FY2027", 1, 0)'
    visible["A11"] = "Historical note FY2027"

    hidden = workbook.create_sheet("Metadata")
    hidden.sheet_state = "hidden"
    hidden["A1"] = "FY2027"

    builder = HubBuilder.__new__(HubBuilder)
    builder.fiscal_year = 2026

    changed = builder._normalize_visible_fiscal_year_labels(workbook)

    assert changed == 2
    assert visible["A1"].value == "MP FY2026_各予定"
    assert visible["A2"].value == "FY2026"
    assert visible["A3"].value == '=IF(A2="FY2027", 1, 0)'
    assert visible["A11"].value == "Historical note FY2027"
    assert hidden["A1"].value == "FY2027"
