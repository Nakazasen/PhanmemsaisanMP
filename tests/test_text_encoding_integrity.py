from pathlib import Path

import tools.check_mojibake as check_mojibake
from tools.check_mojibake import scan_repository


def test_tracked_text_files_have_no_detectable_mojibake():
    assert scan_repository() == []


def test_scan_repository_ignores_missing_tracked_paths(monkeypatch):
    missing = Path.cwd() / "missing.md"
    monkeypatch.setattr(check_mojibake, "tracked_text_paths", lambda _root: [missing])
    assert check_mojibake.scan_repository(".") == []
