"""Test-wide isolation and lightweight synthetic fixtures."""

from __future__ import annotations

import sqlite3

import pytest

from src.db.schema import create_schema
from src.engine.source_order_output import CANONICAL_SOURCE_FILE_ORDER, OutputRow


@pytest.fixture(autouse=True)
def _isolate_run_history(tmp_path, monkeypatch):
    """Keep tests away from the repository's append-only runtime history."""
    monkeypatch.setenv("MP_MANAGER_TEST_HISTORY_ROOT", str(tmp_path / "RUN_HISTORY"))


@pytest.fixture
def sqlite_conn():
    """Return a schema-ready in-memory database for fast integration tests."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def synthetic_output_rows():
    """Return deterministic rows spanning known, repeated, and unknown sources."""
    return [
        OutputRow(CANONICAL_SOURCE_FILE_ORDER[4], {"item": "birthday"}),
        OutputRow(CANONICAL_SOURCE_FILE_ORDER[0], {"item": "facility-1"}),
        OutputRow(CANONICAL_SOURCE_FILE_ORDER[0], {"item": "facility-2"}),
        OutputRow("new-department-costs.xlsx", {"item": "unknown"}),
    ]
