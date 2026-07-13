import importlib
import importlib.util
import sys
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


def test_run_e2e_tolerates_windowed_packaged_streams(monkeypatch):
    module = importlib.import_module("scripts.run_e2e")

    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    module._ensure_text_streams()
    module._safe_console_print("headless packaged log")

    assert sys.stdout is not None
    assert sys.stderr is not None
