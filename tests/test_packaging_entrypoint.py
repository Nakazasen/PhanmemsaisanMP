import importlib
import importlib.util
from pathlib import Path


def test_run_e2e_exposes_callable_main():
    module = importlib.import_module("scripts.run_e2e")

    assert callable(module.main)


def test_packaging_entrypoint_file_import_has_callable_main():
    entrypoint = Path("packaging/mp2027_portable_entry.py")
    spec = importlib.util.spec_from_file_location("mp2027_portable_entry_smoke", entrypoint)
    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    assert callable(module.main)
