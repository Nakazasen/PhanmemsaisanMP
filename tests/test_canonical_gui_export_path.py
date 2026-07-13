import ast
from pathlib import Path


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _tree(path: str) -> ast.AST:
    return ast.parse(_source(path))


def test_gui_runs_pipeline_out_of_process():
    source = _source("src/universal_app.py")
    assert "subprocess.Popen" in source
    assert 'scripts", "run_e2e.py' in source
    assert "run_universal_pipeline(" not in source
    assert "--legacy-export" not in source


def test_run_universal_pipeline_has_no_legacy_output_switch():
    tree = _tree("scripts/run_e2e.py")
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "run_universal_pipeline"
    )
    arguments = {argument.arg for argument in function.args.args}
    assert "mp_saisan_complete_v1" not in arguments
    assert function.args.kwarg.arg == "legacy_output_options"


def test_cli_exposes_no_fixed_row_export_mode():
    source = _source("scripts/run_e2e.py")
    tree = ast.parse(source)
    assert "--legacy-export" not in source
    assert "--facility-file-order-start-row" not in source
    assert "--admin-consumables-start-row" not in source
    assert "--system-cost-start-row" not in source
    assert "--primary-reference-fill-start-row" not in source


def test_canonical_path_is_one_dynamic_write_without_legacy_staging():
    source = _source("scripts/run_e2e.py")
    assert "export_dynamic_source_order(" in source
    assert "builder.export_to_template" not in source
    assert "apply_complete_v1_source_order_to_workbook" not in source
    assert "apply_facility_file_order_to_workbook" not in source


def test_manual_event_ui_cannot_choose_a_form_row():
    source = _source("src/universal_app.py")
    assert "form_row_var" not in source
    assert "row/form_row" not in source


def test_source_workbooks_are_resolved_from_manifest():
    source = _source("scripts/run_e2e.py")
    assert "read_source_manifest(source_dir)" in source
    assert 'os.path.join(source_dir, "施設課' not in source
    assert 'os.path.join(source_dir, "総務課' not in source


def test_fixed_assets_parser_prefers_header_detection_without_fixed_output_coordinates():
    text = _source("src/parsers/fixed_assets.py")
    assert "HEADER_ALIASES" in text
    assert "_detect_header" in text or "_find_header" in text
    assert "helpers.extract_cc_code(row[9]" not in text
