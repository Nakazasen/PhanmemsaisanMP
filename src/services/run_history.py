"""Immutable workspace and catalogue for fiscal planning runs."""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
import json
import shutil
import sqlite3

from src.services.fiscal_run import FiscalRunContext, sha256_file


RUN_STATUS_PRECHECK_FAILED = "PRECHECK_FAILED"
RUN_STATUS_RUNNING = "RUNNING"
RUN_STATUS_SUCCEEDED = "SUCCEEDED"
RUN_STATUS_FAILED = "FAILED"
RUN_STATUS_LEGACY_FY2027 = "LEGACY_FY2027"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _catalog_path(history_root: str) -> Path:
    return Path(history_root) / "run_history.db"


def _catalog_connection(history_root: str) -> sqlite3.Connection:
    root = Path(history_root)
    root.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_catalog_path(history_root))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS planning_runs (
            run_id TEXT PRIMARY KEY,
            fiscal_year INTEGER NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT,
            selected_cost_center TEXT,
            source_paths_json TEXT NOT NULL DEFAULT '{}',
            source_checksums_json TEXT NOT NULL DEFAULT '{}',
            template_checksum TEXT,
            exchange_rate REAL NOT NULL,
            exchange_rate_source TEXT,
            output_path TEXT,
            database_path TEXT,
            error_summary TEXT,
            application_version TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    columns = {row[1] for row in conn.execute("PRAGMA table_info(planning_runs)").fetchall()}
    if "exchange_rate_source" not in columns:
        conn.execute("ALTER TABLE planning_runs ADD COLUMN exchange_rate_source TEXT")
    conn.commit()
    return conn


def create_run_workspace(
    context: FiscalRunContext,
    *,
    target_cc: object | None = None,
    initial_status: str = RUN_STATUS_RUNNING,
    initial_error_summary: str | None = None,
) -> FiscalRunContext:
    root = Path(context.history_root or Path(context.output_dir).parent / "RUN_HISTORY")
    workspace = root / f"FY{context.fiscal_year}" / context.run_id
    workspace.mkdir(parents=True, exist_ok=False)
    (workspace / "outputs").mkdir()
    (workspace / "reports").mkdir()
    sqlite3.connect(workspace / "run.db").close()
    updated = replace(
        context,
        history_root=str(root),
        workspace_dir=str(workspace),
        database_path=str(workspace / "run.db"),
    )
    register_run(
        updated,
        initial_status,
        target_cc=target_cc,
        error_summary=initial_error_summary,
    )
    return updated


def _source_checksums(context: FiscalRunContext) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    for category, paths in context.resolved_sources.items():
        result[category] = []
        for path in paths:
            candidate = Path(path)
            if candidate.is_file():
                result[category].append({"path": str(candidate), "sha256": sha256_file(candidate)})
    manual_store = Path(context.manual_input_store or "")
    if manual_store.is_file():
        result["manual_inputs"] = [{"path": str(manual_store), "sha256": sha256_file(manual_store)}]
    return result


def write_run_manifest(context: FiscalRunContext) -> str:
    if not context.workspace_dir:
        raise ValueError("Không có thư mục lịch sử cho lần chạy.")
    target = Path(context.workspace_dir) / "run_manifest.json"
    payload = asdict(context)
    payload["source_checksums"] = _source_checksums(context)
    if Path(context.template_path).is_file():
        payload["template_checksum"] = sha256_file(context.template_path)
    manual_store = Path(context.manual_input_store or "")
    if manual_store.is_file():
        payload["manual_input_checksum"] = sha256_file(manual_store)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(target)


def register_run(
    context: FiscalRunContext,
    status: str,
    *,
    target_cc: object | None = None,
    error_summary: str | None = None,
    output_path: str | None = None,
) -> None:
    if not context.history_root:
        return
    conn = _catalog_connection(context.history_root)
    try:
        started = _now() if status == RUN_STATUS_RUNNING else None
        finished = _now() if status in {RUN_STATUS_SUCCEEDED, RUN_STATUS_FAILED, RUN_STATUS_PRECHECK_FAILED, RUN_STATUS_LEGACY_FY2027} else None
        checksums = _source_checksums(context) if context.resolved_sources else {}
        template_checksum = sha256_file(context.template_path) if Path(context.template_path).is_file() else None
        existing = conn.execute(
            "SELECT status FROM planning_runs WHERE run_id=?", (context.run_id,)
        ).fetchone()
        if existing is None:
            if status not in {RUN_STATUS_RUNNING, RUN_STATUS_PRECHECK_FAILED, RUN_STATUS_LEGACY_FY2027}:
                raise ValueError(f"Lần chạy mới chỉ có thể bắt đầu ở RUNNING hoặc PRECHECK_FAILED, không phải {status}.")
            conn.execute(
                """INSERT INTO planning_runs
                (run_id, fiscal_year, status, started_at, finished_at, selected_cost_center,
                 source_paths_json, source_checksums_json, template_checksum, exchange_rate,
                 exchange_rate_source, output_path, database_path, error_summary, application_version, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    context.run_id, context.fiscal_year, status, started, finished,
                    str(target_cc) if target_cc is not None else None,
                    json.dumps(context.resolved_sources, ensure_ascii=False),
                    json.dumps(checksums, ensure_ascii=False), template_checksum,
                    context.exchange_rate, context.exchange_rate_source, output_path, context.database_path, error_summary,
                    context.application_version, _now(),
                ),
            )
        else:
            current_status = existing[0]
            if current_status != RUN_STATUS_RUNNING:
                raise ValueError(f"Lịch sử {context.run_id} đã kết thúc ({current_status}) và không thể sửa.")
            if status not in {RUN_STATUS_SUCCEEDED, RUN_STATUS_FAILED}:
                raise ValueError(f"Chuyển trạng thái không hợp lệ: {current_status} -> {status}")
            conn.execute(
                """UPDATE planning_runs SET status=?, finished_at=?, output_path=?, error_summary=?
                   WHERE run_id=? AND status=?""",
                (status, finished, output_path, error_summary, context.run_id, RUN_STATUS_RUNNING),
            )
        conn.commit()
    finally:
        conn.close()


def publish_run_output(
    context: FiscalRunContext,
    staging_output_dir: str,
    *,
    failure_injector=None,
) -> str:
    """Atomically replace a public FY output directory, with rollback on failure."""
    source = Path(staging_output_dir)
    destination = Path(context.output_dir)
    if not source.is_dir():
        raise FileNotFoundError(f"Không có thư mục kết quả tạm để công bố: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    prepared = destination.parent / f".{destination.name}.{context.run_id}.publishing"
    backup = destination.parent / f".{destination.name}.{context.run_id}.backup"
    if prepared.exists() or backup.exists():
        raise FileExistsError("Còn thư mục công bố dở dang; cần kiểm tra lịch sử trước khi chạy lại.")
    shutil.copytree(source, prepared)
    if failure_injector:
        failure_injector("prepared")
    moved_current = False
    try:
        if destination.exists():
            destination.rename(backup)
            moved_current = True
        if failure_injector:
            failure_injector("backed_up")
        prepared.rename(destination)
        if failure_injector:
            failure_injector("published")
    except Exception:
        if destination.exists() and moved_current:
            shutil.rmtree(destination)
        if moved_current and backup.exists():
            backup.rename(destination)
        raise
    finally:
        if prepared.exists():
            shutil.rmtree(prepared)
    if backup.exists():
        shutil.rmtree(backup)
    return str(destination)


def register_legacy_fy2027_database(history_root: str, legacy_database_path: str | Path) -> str | None:
    """Register the old shared FY2027 database as read-only history metadata.

    The legacy file is never opened for writing.  A checksum-derived id makes
    this operation idempotent even when the application starts repeatedly.
    """
    path = Path(legacy_database_path)
    if not path.is_file():
        return None
    digest = sha256_file(path)
    context = FiscalRunContext(
        run_id=f"legacy-fy2027-{digest[:16]}",
        fiscal_year=2027,
        fiscal_periods=(),
        baseline_period="",
        template_path="",
        source_dir="",
        headcount_source_dir="",
        uniform_policy_path=None,
        output_dir="",
        exchange_rate=0.0,
        history_root=str(history_root),
        database_path=str(path.resolve()),
        application_version="legacy-import",
    )
    conn = _catalog_connection(str(history_root))
    try:
        existing = conn.execute("SELECT 1 FROM planning_runs WHERE run_id=?", (context.run_id,)).fetchone()
    finally:
        conn.close()
    if existing is None:
        register_run(
            context,
            RUN_STATUS_LEGACY_FY2027,
            error_summary="Bản ghi chỉ đọc đăng ký từ mp2027.db cũ.",
        )
    return context.run_id


def list_runs(history_root: str, fiscal_year: int | None = None) -> list[dict[str, object]]:
    conn = _catalog_connection(history_root)
    try:
        if fiscal_year is None:
            rows = conn.execute("SELECT * FROM planning_runs ORDER BY created_at DESC").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM planning_runs WHERE fiscal_year=? ORDER BY created_at DESC", (int(fiscal_year),)
            ).fetchall()
        columns = [item[1] for item in conn.execute("PRAGMA table_info(planning_runs)").fetchall()]
        return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()
