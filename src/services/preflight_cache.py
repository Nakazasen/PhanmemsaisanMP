"""Persistent, metadata-only cache for fiscal-run source preflight reports."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from typing import Callable, Iterable

from src.services.fiscal_run import FiscalRunContext, RunPreflightReport, preflight_fiscal_run
from src.services.project_config import launcher_config_path

CACHE_SCHEMA_VERSION = 1
FINGERPRINT_RULE_VERSION = 1
CACHE_FILENAME = "preflight_cache.json"
MAX_CACHE_ENTRIES = 32


def default_preflight_cache_path(local_app_data: str | None = None) -> str:
    return str(Path(launcher_config_path(local_app_data)).with_name(CACHE_FILENAME))


def _normalized_path(path: str | os.PathLike[str] | None) -> str:
    if not path:
        return ""
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def _file_stat(path: Path) -> dict[str, object]:
    try:
        stat = path.stat()
    except OSError:
        return {"path": _normalized_path(path), "kind": "missing"}
    return {
        "path": _normalized_path(path),
        "kind": "file" if path.is_file() else "directory",
        "size": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
    }


def _directory_snapshot(path: str | os.PathLike[str] | None) -> list[dict[str, object]]:
    """Return a cheap recursive stat snapshot without opening source workbooks."""
    if not path:
        return []
    root = Path(path)
    if not root.is_dir():
        return [_file_stat(root)]
    rows: list[dict[str, object]] = [_file_stat(root)]
    try:
        candidates = sorted(
            (candidate for candidate in root.rglob("*") if candidate.is_file()),
            key=lambda candidate: os.path.normcase(str(candidate.relative_to(root))),
        )
    except OSError:
        return rows + [{"path": _normalized_path(root), "kind": "unreadable"}]
    for candidate in candidates:
        row = _file_stat(candidate)
        try:
            row["relative_path"] = candidate.relative_to(root).as_posix().lower()
        except ValueError:
            pass
        rows.append(row)
    return rows


def _annual_source_snapshot(path: str | os.PathLike[str] | None) -> list[dict[str, object]]:
    """Snapshot only top-level files consumed by the annual source inventory."""
    if not path:
        return []
    root = Path(path)
    if not root.is_dir():
        return [_file_stat(root)]
    rows: list[dict[str, object]] = [{
        "path": _normalized_path(root),
        "kind": "directory",
    }]
    relevant_suffixes = {".xls", ".xlsx", ".xlsm", ".csv"}
    try:
        candidates = sorted(
            (candidate for candidate in root.iterdir()
             if candidate.is_file() and candidate.suffix.lower() in relevant_suffixes),
            key=lambda candidate: candidate.name.casefold(),
        )
    except OSError:
        return rows + [{"path": _normalized_path(root), "kind": "unreadable"}]
    for candidate in candidates:
        row = _file_stat(candidate)
        row["relative_path"] = candidate.name.lower()
        rows.append(row)
    return rows


def preflight_fingerprint_payload(
    context: FiscalRunContext,
    *,
    extra_paths: Iterable[str | os.PathLike[str]] = (),
) -> dict[str, object]:
    direct_paths = (
        context.template_path,
        context.uniform_policy_path,
        context.manual_input_store,
        *tuple(extra_paths),
    )
    return {
        "fingerprint_rule_version": FINGERPRINT_RULE_VERSION,
        "application_version": context.application_version,
        "fiscal_year": context.fiscal_year,
        "exchange_rate": context.exchange_rate,
        "exchange_rate_source": context.exchange_rate_source,
        "reference_policy": context.reference_policy,
        "paths": [_file_stat(Path(path)) for path in direct_paths if path],
        "source_snapshot": _annual_source_snapshot(context.source_dir),
        "headcount_snapshot": _directory_snapshot(context.headcount_source_dir),
    }


def preflight_fingerprint(
    context: FiscalRunContext,
    *,
    extra_paths: Iterable[str | os.PathLike[str]] = (),
) -> str:
    encoded = json.dumps(
        preflight_fingerprint_payload(context, extra_paths=extra_paths),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _read_cache(path: str) -> dict[str, object]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError, TypeError):
        return {"schema_version": CACHE_SCHEMA_VERSION, "entries": {}}
    if not isinstance(payload, dict) or payload.get("schema_version") != CACHE_SCHEMA_VERSION:
        return {"schema_version": CACHE_SCHEMA_VERSION, "entries": {}}
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        payload["entries"] = {}
    return payload


def _write_cache(path: str, payload: dict[str, object]) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=".preflight_cache.", suffix=".json.tmp", dir=parent, text=True
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def get_cached_preflight(
    context: FiscalRunContext,
    *,
    cache_path: str | None = None,
    extra_paths: Iterable[str | os.PathLike[str]] = (),
    fingerprint: str | None = None,
) -> RunPreflightReport | None:
    path = cache_path or default_preflight_cache_path()
    fingerprint = fingerprint or preflight_fingerprint(context, extra_paths=extra_paths)
    entry = dict(_read_cache(path).get("entries", {})).get(fingerprint)
    if not isinstance(entry, dict):
        return None
    try:
        report = RunPreflightReport.from_dict(dict(entry["report"]))
    except (KeyError, TypeError, ValueError):
        return None
    if report.fiscal_year != context.fiscal_year:
        return None
    return report


def save_cached_preflight(
    context: FiscalRunContext,
    report: RunPreflightReport,
    *,
    cache_path: str | None = None,
    extra_paths: Iterable[str | os.PathLike[str]] = (),
    fingerprint: str | None = None,
) -> str:
    path = cache_path or default_preflight_cache_path()
    payload = _read_cache(path)
    entries = dict(payload.get("entries", {}))
    fingerprint = fingerprint or preflight_fingerprint(context, extra_paths=extra_paths)
    entries[fingerprint] = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "report": report.as_dict(),
    }
    if len(entries) > MAX_CACHE_ENTRIES:
        ordered = sorted(
            entries.items(),
            key=lambda item: str(item[1].get("saved_at", "")) if isinstance(item[1], dict) else "",
            reverse=True,
        )
        entries = dict(ordered[:MAX_CACHE_ENTRIES])
    payload = {"schema_version": CACHE_SCHEMA_VERSION, "entries": entries}
    _write_cache(path, payload)
    return path


def cached_preflight_fiscal_run(
    context: FiscalRunContext,
    *,
    force_refresh: bool = False,
    cache_path: str | None = None,
    extra_paths: Iterable[str | os.PathLike[str]] = (),
    checker: Callable[[FiscalRunContext], RunPreflightReport] = preflight_fiscal_run,
) -> tuple[RunPreflightReport, bool]:
    """Return a valid cached report or run and persist a fresh deep check."""
    lookup_fingerprint = preflight_fingerprint(context, extra_paths=extra_paths)
    if not force_refresh:
        cached = get_cached_preflight(
            context,
            cache_path=cache_path,
            extra_paths=extra_paths,
            fingerprint=lookup_fingerprint,
        )
        if cached is not None:
            return cached, True
    report = checker(context)
    # The checker or concurrent startup initialization may legitimately update
    # tracked metadata. Cache the report against the state that now exists,
    # otherwise the freshly saved entry can be stale before this call returns.
    final_fingerprint = preflight_fingerprint(context, extra_paths=extra_paths)
    try:
        save_cached_preflight(
            context,
            report,
            cache_path=cache_path,
            extra_paths=extra_paths,
            fingerprint=final_fingerprint,
        )
    except OSError:
        # Cache persistence must never prevent a safe deep check from completing.
        pass
    return report, False
