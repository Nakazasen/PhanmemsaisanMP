"""Versioned, fail-safe SQLite schema migration support."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


CURRENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class MigrationResult:
    from_version: int
    to_version: int
    backup_path: str | None = None


class SchemaCompatibilityError(RuntimeError):
    """Raised when a database cannot be opened safely by this application."""


def _database_path(conn: sqlite3.Connection) -> Path | None:
    for _seq, name, raw_path in conn.execute("PRAGMA database_list").fetchall():
        if name == "main" and raw_path:
            return Path(raw_path).resolve()
    return None


def _backup_database(conn: sqlite3.Connection) -> Path | None:
    source = _database_path(conn)
    if source is None or not source.exists():
        return None
    backup_dir = source.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = backup_dir / f"{source.stem}.before-schema-v{CURRENT_SCHEMA_VERSION}.{timestamp}{source.suffix or '.db'}"
    temporary = target.with_suffix(target.suffix + ".tmp")
    backup = sqlite3.connect(temporary)
    try:
        conn.backup(backup)
    finally:
        backup.close()
    os.replace(temporary, target)
    return target


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone() is not None


def _column_type(conn: sqlite3.Connection, table_name: str, column_name: str) -> str | None:
    for row in conn.execute(f'PRAGMA table_info("{table_name}")').fetchall():
        if str(row[1]) == column_name:
            return str(row[2] or "").upper()
    return None


def _create_ledger(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL,
            application_version TEXT NOT NULL DEFAULT 'unknown'
        )
        """
    )
    conn.commit()


def current_schema_version(conn: sqlite3.Connection) -> int:
    if not _table_exists(conn, "schema_migrations"):
        return 0
    row = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()
    return int(row[0] or 0)


def _rebuild_legacy_cost_centers(conn: sqlite3.Connection) -> None:
    """Convert an INTEGER cost-center key to TEXT without dropping business rows."""
    has_log = _table_exists(conn, "fact_allocation_log")
    required_cc = {"code", "name_jp", "name_vn", "seq_no", "saisan_type", "cost_type", "staff_count", "worker_count", "created_at"}
    available_cc = {str(row[1]) for row in conn.execute("PRAGMA table_info(dim_cost_centers)")}
    missing = sorted(required_cc - available_cc)
    if missing:
        raise SchemaCompatibilityError(
            "Legacy dim_cost_centers cannot be migrated safely; missing columns: " + ", ".join(missing)
        )

    conn.execute("ALTER TABLE dim_cost_centers RENAME TO dim_cost_centers_legacy_v0")
    if has_log:
        conn.execute("ALTER TABLE fact_allocation_log RENAME TO fact_allocation_log_legacy_v0")

    conn.execute(
        """
        CREATE TABLE dim_cost_centers (
            code TEXT PRIMARY KEY, name_jp TEXT NOT NULL, name_vn TEXT,
            seq_no REAL, saisan_type TEXT NOT NULL, cost_type TEXT NOT NULL,
            staff_count INTEGER DEFAULT 0, worker_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        INSERT INTO dim_cost_centers
            (code, name_jp, name_vn, seq_no, saisan_type, cost_type,
             staff_count, worker_count, created_at)
        SELECT CAST(code AS TEXT), name_jp, name_vn, seq_no, saisan_type, cost_type,
               staff_count, worker_count, created_at
        FROM dim_cost_centers_legacy_v0
        """
    )

    if has_log:
        required_log = {
            "id", "rule_id", "dest_cc", "period", "amount_vnd", "account_code",
            "driver_value", "driver_total", "step", "created_at",
        }
        available_log = {str(row[1]) for row in conn.execute("PRAGMA table_info(fact_allocation_log_legacy_v0)")}
        missing_log = sorted(required_log - available_log)
        if missing_log:
            raise SchemaCompatibilityError(
                "Legacy fact_allocation_log cannot be migrated safely; missing columns: "
                + ", ".join(missing_log)
            )
        conn.execute(
            """
            CREATE TABLE fact_allocation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, rule_id INTEGER NOT NULL,
                dest_cc TEXT NOT NULL, period TEXT NOT NULL, amount_vnd REAL NOT NULL,
                account_code INTEGER NOT NULL, driver_value REAL NOT NULL,
                driver_total REAL NOT NULL, step INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (rule_id) REFERENCES map_allocation_rules(id),
                FOREIGN KEY (dest_cc) REFERENCES dim_cost_centers(code)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO fact_allocation_log
                (id, rule_id, dest_cc, period, amount_vnd, account_code,
                 driver_value, driver_total, step, created_at)
            SELECT id, rule_id, CAST(dest_cc AS TEXT), period, amount_vnd, account_code,
                   driver_value, driver_total, step, created_at
            FROM fact_allocation_log_legacy_v0
            """
        )
        conn.execute("DROP TABLE fact_allocation_log_legacy_v0")

    conn.execute("DROP TABLE dim_cost_centers_legacy_v0")


def run_migrations(
    conn: sqlite3.Connection,
    *,
    application_version: str = "unknown",
) -> MigrationResult:
    """Apply known migrations transactionally and reject newer databases."""
    _create_ledger(conn)
    start_version = current_schema_version(conn)
    if start_version > CURRENT_SCHEMA_VERSION:
        raise SchemaCompatibilityError(
            f"Database schema v{start_version} is newer than supported v{CURRENT_SCHEMA_VERSION}. "
            "Install a compatible application version; the database was not modified."
        )
    if start_version == CURRENT_SCHEMA_VERSION:
        return MigrationResult(start_version, start_version)

    needs_legacy_rebuild = (
        _table_exists(conn, "dim_cost_centers")
        and (_column_type(conn, "dim_cost_centers", "code") or "") != "TEXT"
    )
    backup = _backup_database(conn) if needs_legacy_rebuild else None
    foreign_keys = int(conn.execute("PRAGMA foreign_keys").fetchone()[0])
    try:
        if needs_legacy_rebuild:
            conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("BEGIN IMMEDIATE")
        if needs_legacy_rebuild:
            _rebuild_legacy_cost_centers(conn)
        conn.execute(
            "INSERT INTO schema_migrations(version, name, applied_at, application_version) VALUES (?, ?, ?, ?)",
            (
                CURRENT_SCHEMA_VERSION,
                "baseline_and_text_cost_center_keys",
                datetime.now(timezone.utc).isoformat(),
                application_version,
            ),
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        restore_hint = f" Backup: {backup}" if backup else ""
        if isinstance(exc, SchemaCompatibilityError):
            raise
        raise SchemaCompatibilityError(f"Schema migration failed; no partial change was committed.{restore_hint}") from exc
    finally:
        conn.execute(f"PRAGMA foreign_keys={'ON' if foreign_keys else 'OFF'}")

    violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise SchemaCompatibilityError(
            f"Schema migration completed but foreign-key validation found {len(violations)} violation(s)."
            + (f" Backup: {backup}" if backup else "")
        )
    return MigrationResult(start_version, CURRENT_SCHEMA_VERSION, str(backup) if backup else None)
