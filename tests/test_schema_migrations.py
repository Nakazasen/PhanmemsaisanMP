import sqlite3

import pytest

from src.db.migrations import CURRENT_SCHEMA_VERSION, SchemaCompatibilityError, current_schema_version
from src.db.schema import create_schema, get_connection


def test_fresh_database_records_current_schema_version():
    conn = sqlite3.connect(":memory:")
    try:
        create_schema(conn)
        assert current_schema_version(conn) == CURRENT_SCHEMA_VERSION
        create_schema(conn)
        assert conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == 1
    finally:
        conn.close()


def test_legacy_integer_cost_centers_are_migrated_without_data_loss(tmp_path):
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE dim_cost_centers (
            code INTEGER PRIMARY KEY, name_jp TEXT NOT NULL, name_vn TEXT,
            seq_no REAL, saisan_type TEXT NOT NULL, cost_type TEXT NOT NULL,
            staff_count INTEGER DEFAULT 0, worker_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE map_allocation_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT, source_dept TEXT NOT NULL,
            item_name TEXT NOT NULL, unit_price REAL NOT NULL, driver_type TEXT NOT NULL
        );
        INSERT INTO dim_cost_centers(code, name_jp, saisan_type, cost_type)
        VALUES (1412000018, 'Legacy CC', 'MFG', 'MFG');
        INSERT INTO map_allocation_rules(source_dept, item_name, unit_price, driver_type)
        VALUES ('GA', 'Legacy rule', 1, 'headcount');
        CREATE TABLE fact_allocation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, rule_id INTEGER NOT NULL,
            dest_cc INTEGER NOT NULL, period TEXT NOT NULL, amount_vnd REAL NOT NULL,
            account_code INTEGER NOT NULL, driver_value REAL NOT NULL,
            driver_total REAL NOT NULL, step INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO fact_allocation_log(rule_id, dest_cc, period, amount_vnd,
            account_code, driver_value, driver_total)
        VALUES (1, 1412000018, '202604', 123, 6421, 1, 1);
        """
    )
    conn.commit()
    conn.close()

    migrated = get_connection(str(path))
    try:
        create_schema(migrated)
        assert migrated.execute("PRAGMA table_info(dim_cost_centers)").fetchall()[0][2].upper() == "TEXT"
        assert migrated.execute("SELECT code FROM dim_cost_centers").fetchone()[0] == "1412000018"
        row = migrated.execute("SELECT dest_cc, amount_vnd FROM fact_allocation_log").fetchone()
        assert tuple(row) == ("1412000018", 123.0)
        assert current_schema_version(migrated) == CURRENT_SCHEMA_VERSION
    finally:
        migrated.close()

    backups = list((tmp_path / "backups").glob("legacy.before-schema-v1.*.db"))
    assert len(backups) == 1


def test_newer_database_schema_is_rejected_without_mutation():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL, application_version TEXT NOT NULL)"
    )
    conn.execute("INSERT INTO schema_migrations VALUES (999, 'future', 'now', 'future')")
    conn.commit()

    with pytest.raises(SchemaCompatibilityError, match="mới hơn phiên bản ứng dụng hỗ trợ"):
        create_schema(conn)

    assert conn.execute("SELECT version FROM schema_migrations").fetchone()[0] == 999
    assert conn.execute("SELECT name FROM sqlite_master WHERE name='dim_cost_centers'").fetchone() is None


def test_default_connection_prefers_explicit_runtime_root(tmp_path, monkeypatch):
    runtime_root = tmp_path / "runtime"
    monkeypatch.setenv("MP_MANAGER_RUNTIME_ROOT", str(runtime_root))

    conn = get_connection()
    try:
        path = conn.execute("PRAGMA database_list").fetchone()[2]
    finally:
        conn.close()

    assert path == str(runtime_root / "mp2027.db")


def test_frozen_default_connection_uses_local_app_data_not_executable(tmp_path, monkeypatch):
    import src.db.schema as schema

    local_data = tmp_path / "local"
    executable_dir = tmp_path / "Program Files" / "MP2027"
    monkeypatch.delenv("MP_MANAGER_RUNTIME_ROOT", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(local_data))
    monkeypatch.setattr(schema.sys, "frozen", True, raising=False)
    monkeypatch.setattr(schema.sys, "executable", str(executable_dir / "MP2027_Portable.exe"))

    conn = get_connection()
    try:
        path = conn.execute("PRAGMA database_list").fetchone()[2]
    finally:
        conn.close()

    expected = local_data / "MPManager" / "Projects" / "MP2027" / "mp2027.db"
    assert path == str(expected)
    assert executable_dir not in expected.parents
