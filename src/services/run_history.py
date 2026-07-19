"""Immutable workspace and catalogue for fiscal planning runs."""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
import json
import shutil
import sqlite3
import time
from typing import Any

from src.services.fiscal_run import FiscalRunContext, sha256_file


RUN_STATUS_PRECHECK_FAILED = "PRECHECK_FAILED"
RUN_STATUS_RUNNING = "RUNNING"
RUN_STATUS_SUCCEEDED = "SUCCEEDED"
RUN_STATUS_SUCCEEDED_INCOMPLETE = "SUCCEEDED_INCOMPLETE"
RUN_STATUS_FAILED = "FAILED"
RUN_STATUS_LEGACY_FY2027 = "LEGACY_FY2027"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _remove_tree_with_retry(path: Path, *, attempts: int = 6, initial_delay: float = 0.05) -> None:
    """Remove a tree, tolerating only short-lived Windows directory locks."""
    delay = initial_delay
    for attempt in range(attempts):
        try:
            shutil.rmtree(path)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 0.4)


class PipelineStageEvidence:
    """Atomically persist stage timing and terminal evidence inside one run workspace."""

    def __init__(
        self,
        workspace_dir: str | Path,
        run_id: str,
        *,
        started_perf: float | None = None,
    ) -> None:
        self.path = Path(workspace_dir) / "reports" / "pipeline_stage_evidence.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._started_perf = started_perf if started_perf is not None else time.perf_counter()
        self._stage_started_perf: float | None = None
        self._terminal = False
        self.payload: dict[str, Any] = {
            "schema_version": 1,
            "run_id": str(run_id),
            "status": RUN_STATUS_RUNNING,
            "started_at": _now(),
            "current_stage": None,
            "stages": [],
        }
        self._write()

    def _write(self) -> None:
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(self.payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(self.path)

    def start(self, name: str, *, started_perf: float | None = None) -> None:
        if self._terminal:
            raise ValueError("Bằng chứng các bước pipeline đã ở trạng thái kết thúc")
        if self.payload["current_stage"] is not None:
            raise ValueError(f"Một bước pipeline đang chạy: {self.payload['current_stage']}")
        self._stage_started_perf = (
            started_perf if started_perf is not None else time.perf_counter()
        )
        self.payload["current_stage"] = str(name)
        self._write()

    def complete(self, *, details: dict[str, Any] | None = None) -> None:
        name = self.payload.get("current_stage")
        if not name or self._stage_started_perf is None:
            raise ValueError("Không có bước pipeline nào đang chạy")
        elapsed = time.perf_counter() - self._stage_started_perf
        entry: dict[str, Any] = {
            "name": name,
            "status": "PASS",
            "elapsed_seconds": round(elapsed, 3),
            "finished_at": _now(),
        }
        if details:
            entry["details"] = details
        self.payload["stages"].append(entry)
        self.payload["current_stage"] = None
        self._stage_started_perf = None
        self._write()

    def finalize(self, status: str, *, error_summary: str | None = None) -> None:
        if self._terminal:
            return
        current = self.payload.get("current_stage")
        if current and self._stage_started_perf is not None:
            failed_stage: dict[str, Any] = {
                "name": current,
                "status": "FAIL",
                "elapsed_seconds": round(time.perf_counter() - self._stage_started_perf, 3),
                "finished_at": _now(),
            }
            if error_summary:
                failed_stage["error_summary"] = error_summary
            self.payload["stages"].append(failed_stage)
        self.payload["current_stage"] = None
        self.payload["status"] = str(status)
        self.payload["finished_at"] = _now()
        self.payload["total_elapsed_seconds"] = round(
            time.perf_counter() - self._started_perf, 3
        )
        if error_summary:
            self.payload["error_summary"] = error_summary
        self._terminal = True
        self._write()


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
        finished = _now() if status in {
            RUN_STATUS_SUCCEEDED,
            RUN_STATUS_SUCCEEDED_INCOMPLETE,
            RUN_STATUS_FAILED,
            RUN_STATUS_PRECHECK_FAILED,
            RUN_STATUS_LEGACY_FY2027,
        } else None
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
            if status not in {RUN_STATUS_SUCCEEDED, RUN_STATUS_SUCCEEDED_INCOMPLETE, RUN_STATUS_FAILED}:
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
    mode: str = "replace",
    target_cc: object | None = None,
    failure_injector=None,
) -> str:
    """Atomically publish a complete snapshot or one targeted CC workbook.

    ``replace`` publishes the staging directory as the complete public FY
    snapshot. ``merge`` starts from the accepted public snapshot and overlays
    only ``MP_CC_<target_cc>.xlsx`` plus the reports from the targeted run.
    """
    source = Path(staging_output_dir)
    destination = Path(context.output_dir)
    if not source.is_dir():
        raise FileNotFoundError(f"Không có thư mục kết quả tạm để công bố: {source}")
    if mode not in {"replace", "merge"}:
        raise ValueError(f"Chế độ công bố không hợp lệ: {mode}")

    target_name: str | None = None
    if mode == "merge":
        normalized_cc = str(target_cc or "").strip()
        if not normalized_cc:
            raise ValueError("Công bố merge yêu cầu cost center đích.")
        target_name = f"MP_CC_{normalized_cc}.xlsx"
        staged_target = source / target_name
        if not staged_target.is_file():
            raise FileNotFoundError(f"Không có workbook CC đích để công bố: {staged_target}")
        unexpected = [
            path.name
            for path in source.glob("MP_CC_*.xlsx")
            if path.name != target_name
        ]
        if unexpected:
            raise ValueError(
                "Kết quả single-CC chứa workbook CC khác: " + ", ".join(sorted(unexpected))
            )

    destination.parent.mkdir(parents=True, exist_ok=True)
    prepared = destination.parent / f".{destination.name}.{context.run_id}.publishing"
    backup = destination.parent / f".{destination.name}.{context.run_id}.backup"
    if prepared.exists() or backup.exists():
        raise FileExistsError("Còn thư mục công bố dở dang; cần kiểm tra lịch sử trước khi chạy lại.")

    moved_current = False
    published = False
    publication_complete = False
    try:
        if mode == "replace" or not destination.exists():
            shutil.copytree(source, prepared)
        else:
            staged_reports = source / "BAO_CAO_KIEM_TRA"
            if staged_reports.is_dir():
                shutil.copytree(
                    destination,
                    prepared,
                    ignore=shutil.ignore_patterns("BAO_CAO_KIEM_TRA"),
                )
            else:
                shutil.copytree(destination, prepared)
            shutil.copy2(source / str(target_name), prepared / str(target_name))
            if staged_reports.is_dir():
                prepared_reports = prepared / "BAO_CAO_KIEM_TRA"
                shutil.copytree(staged_reports, prepared_reports)

        if failure_injector:
            failure_injector("prepared")
        if destination.exists():
            destination.rename(backup)
            moved_current = True
        if failure_injector:
            failure_injector("backed_up")
        prepared.rename(destination)
        published = True
        if failure_injector:
            failure_injector("published")
        publication_complete = True
    except Exception:
        if published and destination.exists():
            _remove_tree_with_retry(destination)
        if moved_current and backup.exists():
            backup.rename(destination)
        raise
    finally:
        if prepared.exists():
            _remove_tree_with_retry(prepared)
        if backup.exists():
            if publication_complete and destination.exists():
                try:
                    _remove_tree_with_retry(backup)
                except PermissionError:
                    # The new snapshot is already public. Windows indexing or
                    # antivirus may retain a handle on the retired snapshot;
                    # keeping that hidden backup is safer than misreporting a
                    # successful publication as a failed business run.
                    pass
            elif not destination.exists():
                backup.rename(destination)
            # If a failed rollback leaves both paths present, retain the old
            # backup for recovery instead of deleting the last known-good data.
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


def filter_runs(
    history_root: str,
    fiscal_year: int | None = None,
    *,
    status: str = "",
    cost_center: str = "",
    item: str = "",
    run_date: str = "",
) -> list[dict[str, object]]:
    """Filter catalogue rows; item searches may inspect each immutable run database."""
    status = str(status or "").strip()
    cost_center = str(cost_center or "").strip()
    item = str(item or "").strip()
    run_date = str(run_date or "").strip()
    filtered: list[dict[str, object]] = []

    for row in list_runs(history_root, fiscal_year):
        if status and str(row.get("status") or "") != status:
            continue
        if cost_center and cost_center not in str(row.get("selected_cost_center") or ""):
            continue
        if run_date and run_date not in str(row.get("started_at") or ""):
            continue
        if item:
            database_path = str(row.get("database_path") or "")
            if not Path(database_path).is_file():
                continue
            try:
                conn = sqlite3.connect(database_path)
                try:
                    found = conn.execute(
                        "SELECT 1 FROM fact_input_data "
                        "WHERE source LIKE ? OR description LIKE ? LIMIT 1",
                        (f"%{item}%", f"%{item}%"),
                    ).fetchone()
                finally:
                    conn.close()
            except sqlite3.Error:
                continue
            if found is None:
                continue
        filtered.append(row)
    return filtered
