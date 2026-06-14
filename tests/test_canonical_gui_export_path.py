import ast
from pathlib import Path


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _tree(path: str) -> ast.AST:
    return ast.parse(_source(path))


def test_gui_callback_passes_canonical_export_mode():
    tree = _tree("src/universal_app.py")
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "run_universal_pipeline"]
    assert calls, "GUI module must call run_universal_pipeline"
    kw = {keyword.arg: keyword.value for keyword in calls[-1].keywords}
    assert isinstance(kw.get("mp_saisan_complete_v1"), ast.Constant)
    assert kw["mp_saisan_complete_v1"].value is True


def test_run_universal_pipeline_default_is_canonical():
    tree = _tree("scripts/run_e2e.py")
    funcs = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "run_universal_pipeline"]
    assert funcs
    defaults = funcs[0].args.defaults
    assert isinstance(defaults[-1], ast.Constant)
    assert defaults[-1].value is True


def test_cli_default_and_legacy_export_mapping():
    source = Path("scripts/run_e2e.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    call = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "run_universal_pipeline"][-1]
    kw = {keyword.arg: keyword.value for keyword in call.keywords}
    assert isinstance(kw["mp_saisan_complete_v1"], ast.UnaryOp)
    assert isinstance(kw["mp_saisan_complete_v1"].op, ast.Not)
    assert isinstance(kw["mp_saisan_complete_v1"].operand, ast.Attribute)
    assert kw["mp_saisan_complete_v1"].operand.attr == "legacy_export"
    assert "--legacy-export" in source


def test_reference_path_optional_for_canonical_source_order():
    source = _source("scripts/run_e2e.py")
    assert "if mp_saisan_complete_v1 and (primary_reference_path or reference_map_path):" in source
    assert "except ValueError:" in source
    assert "complete_v1_primary_path = None" in source
    assert "if mp_saisan_complete_v1 and complete_v1_primary_path:" in source


def test_source_order_writers_are_enabled_by_canonical_default():
    source = _source("scripts/run_e2e.py")
    assert "if mp_saisan_complete_v1:" in source
    assert "facility_file_order_export = True" in source
    assert "apply_complete_v1_source_order_to_workbook" in source

def test_fixed_assets_parser_not_changed_in_phase_commit():
    # Guard against accidentally staging the unproven H->J parser change.
    text = Path("src/parsers/fixed_assets.py").read_text(encoding="utf-8")
    assert "helpers.extract_cc_code(row[7]" in text
    assert "helpers.extract_cc_code(row[9]" not in text
