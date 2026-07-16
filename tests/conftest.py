"""Test-wide isolation for runtime artifacts.

The production pipeline intentionally preserves immutable run history.  Tests
must never use the repository's real RUN_HISTORY catalogue while exercising
that path.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_run_history(tmp_path, monkeypatch):
    monkeypatch.setenv("MP_MANAGER_TEST_HISTORY_ROOT", str(tmp_path / "RUN_HISTORY"))
