"""Tests for packaged-runtime raw/headcount_manual.csv resolution parity.

Gate 2C guard: verify that resolve_manual_headcount_source_dir correctly
finds raw/ both in IDE (project root) and packaged (_MEIPASS) layouts.
"""
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

from src.parsers.manual_headcount import (
    TEMPLATE_FILENAME,
    BUS_DRIVER_FILENAME,
    resolve_manual_headcount_source_dir,
)


class TestIDERawResolution:
    """IDE mode: base_dir is the repo root with raw/ as a sibling."""

    def test_docs_mp2027_redirects_to_raw(self, tmp_path):
        base = tmp_path / "project"
        raw = base / "raw"
        raw.mkdir(parents=True)
        docs = base / "docs" / "MP2027"
        docs.mkdir(parents=True)

        result = resolve_manual_headcount_source_dir(
            source_dir=str(docs), base_dir=str(base)
        )
        assert Path(result) == raw

    def test_project_root_returns_raw(self, tmp_path):
        base = tmp_path / "project"
        raw = base / "raw"
        raw.mkdir(parents=True)

        result = resolve_manual_headcount_source_dir(
            source_dir=str(base), base_dir=str(base)
        )
        assert Path(result) == raw


class TestPackagedRawResolution:
    """Packaged mode: base_dir (exe dir) does NOT have raw/, but _MEIPASS does."""

    def test_meipass_raw_fallback_when_exe_dir_has_no_raw(self, tmp_path):
        exe_dir = tmp_path / "dist" / "MyApp"
        exe_dir.mkdir(parents=True)
        meipass = tmp_path / "dist" / "MyApp" / "_internal"
        meipass_raw = meipass / "raw"
        meipass_raw.mkdir(parents=True)
        (meipass_raw / TEMPLATE_FILENAME).write_text("cc_code,period,headcount_staff,headcount_worker\n")
        meipass_docs = meipass / "docs" / "MP2027"
        meipass_docs.mkdir(parents=True)

        with mock.patch.object(sys, "_MEIPASS", str(meipass), create=True):
            result = resolve_manual_headcount_source_dir(
                source_dir=str(meipass_docs), base_dir=str(exe_dir)
            )

        assert Path(result) == meipass_raw

    def test_external_raw_next_to_exe_takes_priority_over_bundled(self, tmp_path):
        exe_dir = tmp_path / "dist" / "MyApp"
        external_raw = exe_dir / "raw"
        external_raw.mkdir(parents=True)
        (external_raw / TEMPLATE_FILENAME).write_text("cc_code,period,headcount_staff,headcount_worker\n")

        meipass = tmp_path / "dist" / "MyApp" / "_internal"
        meipass_raw = meipass / "raw"
        meipass_raw.mkdir(parents=True)
        (meipass_raw / TEMPLATE_FILENAME).write_text("cc_code,period,headcount_staff,headcount_worker\n")

        with mock.patch.object(sys, "_MEIPASS", str(meipass), create=True):
            result = resolve_manual_headcount_source_dir(
                source_dir=str(exe_dir), base_dir=str(exe_dir)
            )

        # External raw/ next to exe must win over bundled raw/.
        assert Path(result) == external_raw

    def test_no_meipass_no_raw_still_returns_raw_path(self, tmp_path):
        base = tmp_path / "project"
        base.mkdir()

        result = resolve_manual_headcount_source_dir(
            source_dir=str(base), base_dir=str(base)
        )
        # Should return raw/ path even if directory doesn't exist yet
        # (parse_manual_headcount will mkdir it)
        assert result.endswith("raw")


class TestSpecBundlesRawCSVs:
    """Guard: MP2027_Portable.spec must include raw CSV input files."""

    def test_spec_includes_raw_headcount_manual(self):
        spec_path = Path("MP2027_Portable.spec")
        if not spec_path.exists():
            pytest.skip("MP2027_Portable.spec not found (not at project root)")
        content = spec_path.read_text(encoding="utf-8")
        assert "headcount_manual.csv" in content, (
            "MP2027_Portable.spec must bundle raw/headcount_manual.csv"
        )

    def test_spec_includes_raw_bus_headcount(self):
        spec_path = Path("MP2027_Portable.spec")
        if not spec_path.exists():
            pytest.skip("MP2027_Portable.spec not found (not at project root)")
        content = spec_path.read_text(encoding="utf-8")
        assert "bus_headcount_manual.csv" in content, (
            "MP2027_Portable.spec must bundle raw/bus_headcount_manual.csv"
        )


class TestRunE2EPassesBaseDir:
    """Guard: run_e2e.py must pass base_dir to parse_manual_headcount."""

    def test_run_e2e_passes_base_dir(self):
        run_e2e_path = Path("scripts/run_e2e.py")
        if not run_e2e_path.exists():
            pytest.skip("scripts/run_e2e.py not found")
        content = run_e2e_path.read_text(encoding="utf-8")
        assert "base_dir=BASE_DIR" in content, (
            "run_e2e.py must pass base_dir=BASE_DIR to parse_manual_headcount "
            "so packaged mode resolves raw/ correctly"
        )


class TestHeadlessCLIEntry:
    """Gate 2D: universal_app.py must support headless export via CLI args."""

    def test_universal_app_has_cli_detection(self):
        app_path = Path("src/universal_app.py")
        if not app_path.exists():
            pytest.skip("src/universal_app.py not found")
        content = app_path.read_text(encoding="utf-8")
        assert "--target-cc" in content, (
            "universal_app.py must detect --target-cc for headless CLI export"
        )

    def test_universal_app_delegates_to_run_e2e(self):
        app_path = Path("src/universal_app.py")
        if not app_path.exists():
            pytest.skip("src/universal_app.py not found")
        content = app_path.read_text(encoding="utf-8")
        assert "run_e2e" in content, (
            "universal_app.py must delegate CLI export to run_e2e"
        )

    def test_no_args_preserves_gui(self):
        """Without CLI args, the GUI entry path must remain intact."""
        app_path = Path("src/universal_app.py")
        if not app_path.exists():
            pytest.skip("src/universal_app.py not found")
        content = app_path.read_text(encoding="utf-8")
        assert "tk.Tk()" in content, "GUI entry must remain when no CLI args"
        assert "mainloop()" in content, "mainloop must remain for GUI"


class TestRunE2EMEIPASSDefaults:
    """Gate 2D: run_e2e.py defaults must handle _MEIPASS for packaged mode."""

    def test_default_source_dir_has_meipass_fallback(self):
        run_e2e = Path("scripts/run_e2e.py")
        if not run_e2e.exists():
            pytest.skip("scripts/run_e2e.py not found")
        content = run_e2e.read_text(encoding="utf-8")
        assert "_MEIPASS" in content, (
            "run_e2e.py must check sys._MEIPASS for packaged mode defaults"
        )

    def test_default_template_path_has_meipass_fallback(self):
        run_e2e = Path("scripts/run_e2e.py")
        if not run_e2e.exists():
            pytest.skip("scripts/run_e2e.py not found")
        content = run_e2e.read_text(encoding="utf-8")
        # The _default_template_path function must have _MEIPASS fallback
        # so packaged exe can find FORM.xlsx in _internal/docs/MP2027/
        lines = content.split("\n")
        in_template_func = False
        has_meipass = False
        for line in lines:
            if "def _default_template_path" in line:
                in_template_func = True
            elif in_template_func and line.startswith("def "):
                break
            elif in_template_func and "_MEIPASS" in line:
                has_meipass = True
                break
        assert has_meipass, (
            "_default_template_path must have _MEIPASS fallback"
        )
