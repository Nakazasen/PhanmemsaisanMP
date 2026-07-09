import ast
from pathlib import Path


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
    assert "COMPLETE_V1_SOURCE_ORDER_START_ROW = 30" in source
    assert "COMPLETE_V1_SOURCE_ORDER_CLEAR_UNTIL_ROW = 199" in source
    assert "_apply_complete_v1_source_order(out_path, log_callback, phase=\"final\")" in source


def test_complete_v1_single_export_finalizes_source_order_after_reference_layer(monkeypatch, tmp_path):
    import scripts.run_e2e as run_e2e

    calls = []

    class Cursor:
        def execute(self, *args, **kwargs):
            return None

        def fetchall(self):
            return []

    class Conn:
        def cursor(self):
            return Cursor()

        def commit(self):
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
    monkeypatch.setattr(run_e2e, "get_connection", lambda db_path: Conn())
    monkeypatch.setattr(run_e2e, "create_schema", lambda conn: None)
    monkeypatch.setattr(run_e2e, "init_sys_params", lambda conn, exchange_rate, fiscal_year: None)
    monkeypatch.setattr(run_e2e, "load_all", lambda **kwargs: None)
    monkeypatch.setattr(run_e2e, "describe_manifest", lambda source_dir: [])
    monkeypatch.setattr(run_e2e, "parse_facility", lambda conn, source_dir: {})
    monkeypatch.setattr(run_e2e, "parse_fixed_assets", lambda conn, source_dir: {})
    monkeypatch.setattr(run_e2e, "parse_it_simulation", lambda conn, source_dir: {})
    monkeypatch.setattr(run_e2e, "parse_ga", lambda conn, source_dir: {})
    monkeypatch.setattr(run_e2e, "parse_birthday_workbook", lambda conn, source_dir: {})
    monkeypatch.setattr(run_e2e, "parse_manual_headcount", lambda conn, source_dir, base_dir=None: {})
    monkeypatch.setattr(run_e2e, "parse_manual_special_costs", lambda conn, source_dir: {})
    monkeypatch.setattr(run_e2e, "parse_manual_event_drivers", lambda conn, source_dir: {})
    monkeypatch.setattr(run_e2e, "parse_nnn_paperwork", lambda conn, source_dir: {})
    monkeypatch.setattr(run_e2e, "AllocationEngine", lambda conn: type("Engine", (), {"run_allocation": lambda self: None})())
    monkeypatch.setattr(run_e2e, "HubBuilder", Builder)
    monkeypatch.setattr(run_e2e, "write_pipeline_audit_report", lambda **kwargs: {"report_path": "audit.md", "missing_csv_path": "missing.csv"})
    monkeypatch.setattr(run_e2e, "apply_facility_file_order_to_workbook", lambda **kwargs: calls.append("facility"))
    monkeypatch.setattr(run_e2e, "apply_admin_consumables_to_workbook", lambda **kwargs: calls.append("admin"))
    monkeypatch.setattr(run_e2e, "apply_system_cost_to_workbook", lambda **kwargs: calls.append("system"))
    monkeypatch.setattr(run_e2e, "_resolve_primary_reference_path", lambda **kwargs: str(tmp_path / "ref.xlsx"))
    monkeypatch.setattr(run_e2e, "apply_mp_saisan_complete_v1", lambda **kwargs: calls.append("complete-reference") or {})

    def fake_source_order(workbook_path, start_row, clear_until_row):
        calls.append(("source-order", start_row, clear_until_row))
        return {"source_blocks_written": 1, "rows_written": 1, "blank_rows_written": 0, "start_row": start_row, "end_row": start_row}

    monkeypatch.setattr(run_e2e, "apply_complete_v1_source_order_to_workbook", fake_source_order)

    ok, _ = run_e2e.run_universal_pipeline(
        fiscal_year=2027,
        template_path="FORM.xlsx",
        source_dir="raw",
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
        ("source-order", 30, 199),
        "complete-reference",
        ("source-order", 30, 199),
    ]


def test_complete_v1_single_export_without_reference_still_finalizes_source_order(monkeypatch, tmp_path):
    import scripts.run_e2e as run_e2e

    calls = []

    class Cursor:
        def execute(self, *args, **kwargs):
            return None

        def fetchall(self):
            return []

    class Conn:
        def cursor(self):
            return Cursor()

        def commit(self):
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
    monkeypatch.setattr(run_e2e, "get_connection", lambda db_path: Conn())
    monkeypatch.setattr(run_e2e, "create_schema", lambda conn: None)
    monkeypatch.setattr(run_e2e, "init_sys_params", lambda conn, exchange_rate, fiscal_year: None)
    monkeypatch.setattr(run_e2e, "load_all", lambda **kwargs: None)
    monkeypatch.setattr(run_e2e, "describe_manifest", lambda source_dir: [])
    monkeypatch.setattr(run_e2e, "parse_facility", lambda conn, source_dir: {})
    monkeypatch.setattr(run_e2e, "parse_fixed_assets", lambda conn, source_dir: {})
    monkeypatch.setattr(run_e2e, "parse_it_simulation", lambda conn, source_dir: {})
    monkeypatch.setattr(run_e2e, "parse_ga", lambda conn, source_dir: {})
    monkeypatch.setattr(run_e2e, "parse_birthday_workbook", lambda conn, source_dir: {})
    monkeypatch.setattr(run_e2e, "parse_manual_headcount", lambda conn, source_dir, base_dir=None: {})
    monkeypatch.setattr(run_e2e, "parse_manual_special_costs", lambda conn, source_dir: {})
    monkeypatch.setattr(run_e2e, "parse_manual_event_drivers", lambda conn, source_dir: {})
    monkeypatch.setattr(run_e2e, "parse_nnn_paperwork", lambda conn, source_dir: {})
    monkeypatch.setattr(run_e2e, "AllocationEngine", lambda conn: type("Engine", (), {"run_allocation": lambda self: None})())
    monkeypatch.setattr(run_e2e, "HubBuilder", Builder)
    monkeypatch.setattr(run_e2e, "write_pipeline_audit_report", lambda **kwargs: {"report_path": "audit.md", "missing_csv_path": "missing.csv"})
    monkeypatch.setattr(run_e2e, "apply_facility_file_order_to_workbook", lambda **kwargs: calls.append("facility"))
    monkeypatch.setattr(run_e2e, "apply_admin_consumables_to_workbook", lambda **kwargs: calls.append("admin"))
    monkeypatch.setattr(run_e2e, "apply_system_cost_to_workbook", lambda **kwargs: calls.append("system"))
    monkeypatch.setattr(run_e2e, "_resolve_primary_reference_path", lambda **kwargs: (_ for _ in ()).throw(AssertionError("reference should not be required")))
    monkeypatch.setattr(run_e2e, "apply_mp_saisan_complete_v1", lambda **kwargs: calls.append("complete-reference") or {})

    def fake_source_order(workbook_path, start_row, clear_until_row):
        calls.append(("source-order", start_row, clear_until_row))
        return {"source_blocks_written": 1, "rows_written": 1, "blank_rows_written": 0, "start_row": start_row, "end_row": start_row}

    monkeypatch.setattr(run_e2e, "apply_complete_v1_source_order_to_workbook", fake_source_order)

    ok, _ = run_e2e.run_universal_pipeline(
        fiscal_year=2027,
        template_path="FORM.xlsx",
        source_dir="raw",
        target_cc=1412000006,
        reference_map_path=None,
    )

    assert ok
    assert calls == [
        "export",
        "facility",
        "admin",
        "system",
        ("source-order", 30, 199),
    ]


def test_fixed_assets_parser_uses_audited_header_detection_not_h_to_j_shortcut():
    text = Path("src/parsers/fixed_assets.py").read_text(encoding="utf-8")
    assert "HEADER_ALIASES" in text
    assert "LEGACY_COLUMN_MAP" in text
    assert '"cc_code": 7' in text
    assert "helpers.extract_cc_code(row[9]" not in text
