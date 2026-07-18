"""Run the real fiscal pipeline in an isolated acceptance workspace.

This command deliberately crosses the same subprocess boundary as the Windows GUI.
It never monkeypatches pipeline internals and never writes the production manual
store, operational database, output directory, or run-history directory.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
from typing import Any
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.audit.real_pipeline_validator import (  # noqa: E402
    validate_real_pipeline_run,
    write_acceptance_result,
)
from src.services.manual_staffing_overrides import (  # noqa: E402
    copy_missing_baselines_from_april,
)

DEFAULT_TARGET_CC = "1412000005"
DEFAULT_FISCAL_YEAR = 2027
DEFAULT_EXCHANGE_RATE = 26273.0
DEFAULT_RECOVERY_RUN_ID = "e99210faa8664ebb8bf08f99b2b6e0a7"
BASELINE_PROVENANCE = "USER_APPROVED_BASELINE_T3_FROM_T4"


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path_fingerprint(path: Path) -> dict[str, Any]:
    """Return a content fingerprint without creating or opening files writable."""
    if not path.exists():
        return {"path": str(path), "kind": "absent"}
    if path.is_file():
        stat = path.stat()
        return {
            "path": str(path),
            "kind": "file",
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": _sha256_file(path),
        }
    files: list[dict[str, Any]] = []
    for candidate in sorted(item for item in path.rglob("*") if item.is_file()):
        stat = candidate.stat()
        files.append({
            "relative_path": candidate.relative_to(path).as_posix(),
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": _sha256_file(candidate),
        })
    return {"path": str(path), "kind": "directory", "files": files}


def _readonly_connection(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(path)
    connection = sqlite3.connect(
        f"file:{path.resolve().as_posix()}?mode=ro", uri=True
    )
    connection.row_factory = sqlite3.Row
    return connection


def _immutable_connection(path: Path) -> sqlite3.Connection:
    """Open a stable SQLite source without creating or touching WAL/SHM state."""
    if not path.is_file():
        raise FileNotFoundError(path)
    wal_path = Path(f"{path}-wal")
    if wal_path.exists() and wal_path.stat().st_size:
        raise RuntimeError(
            f"SQLite source has uncheckpointed WAL content and cannot be snapshotted immutably: {path}"
        )
    connection = sqlite3.connect(
        f"file:{path.resolve().as_posix()}?mode=ro&immutable=1", uri=True
    )
    connection.row_factory = sqlite3.Row
    return connection


def _snapshot_sqlite(source: Path, destination: Path) -> None:
    """Create a stable SQLite copy without touching source WAL/SHM metadata."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(destination)
    source_connection = _immutable_connection(source)
    target_connection = sqlite3.connect(destination)
    try:
        source_connection.backup(target_connection)
        target_connection.commit()
    finally:
        target_connection.close()
        source_connection.close()


def _prepare_approved_baseline(
    manual_store: Path,
    recovery_database: Path,
    *,
    fiscal_year: int,
    target_cc: str,
) -> dict[str, Any]:
    destination = sqlite3.connect(manual_store)
    destination.row_factory = sqlite3.Row
    source = _readonly_connection(recovery_database)
    try:
        before = destination.execute(
            """SELECT description FROM fact_manual_headcount_baseline_override
               WHERE fiscal_year=? AND period=? AND CAST(cc_code AS TEXT)=?""",
            (int(fiscal_year), "202603", target_cc),
        ).fetchall()
        copied = copy_missing_baselines_from_april(
            destination,
            fiscal_year,
            target_cc=target_cc,
            source_conn=source,
        )
        destination.commit()
        after = destination.execute(
            """SELECT period,description,headcount_all,headcount_expat,
                      headcount_staff,headcount_worker,headcount_local_total
               FROM fact_manual_headcount_baseline_override
               WHERE fiscal_year=? AND period=? AND CAST(cc_code AS TEXT)=?""",
            (int(fiscal_year), "202603", target_cc),
        ).fetchall()
    finally:
        source.close()
        destination.close()

    if copied != [target_cc]:
        raise RuntimeError(
            f"Approved T4-to-T3 recovery did not resolve exactly {target_cc}: {copied}"
        )
    if len(after) != 1 or str(after[0]["description"] or "") != BASELINE_PROVENANCE:
        raise RuntimeError("Sandbox baseline does not carry the approved provenance")
    return {
        "preexisting_rows": [dict(row) for row in before],
        "copied_cost_centers": copied,
        "materialized_override": dict(after[0]),
        "source_database": str(recovery_database),
        "source_sha256": _sha256_file(recovery_database),
        "sandbox_manual_store_sha256": _sha256_file(manual_store),
    }


def _catalog_candidates(
    history_root: Path,
    *,
    fiscal_year: int,
    target_cc: str,
) -> list[dict[str, Any]]:
    catalog = history_root / "run_history.db"
    connection = _readonly_connection(catalog)
    try:
        rows = connection.execute(
            """SELECT run_id,fiscal_year,status,selected_cost_center,exchange_rate,
                      output_path,database_path,error_summary,started_at,finished_at,created_at
               FROM planning_runs
               WHERE fiscal_year=? AND CAST(selected_cost_center AS TEXT)=?
               ORDER BY created_at""",
            (int(fiscal_year), target_cc),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def _seed_public_output(source: Path, destination: Path, target_cc: str) -> dict[str, str]:
    """Seed merge publication and return hashes of workbooks that must survive."""
    if not source.is_dir():
        raise FileNotFoundError(f"Production output seed is absent: {source}")
    shutil.copytree(source, destination)
    target_name = f"MP_CC_{target_cc}.xlsx"
    preserved = {
        workbook.name: _sha256_file(workbook)
        for workbook in sorted(destination.glob("MP_CC_*.xlsx"))
        if workbook.name != target_name
    }
    if not preserved:
        raise RuntimeError("No non-target public workbook is available to verify merge publication")
    return preserved


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run isolated real-pipeline acceptance for one fiscal cost center."
    )
    parser.add_argument("--fy", type=int, default=DEFAULT_FISCAL_YEAR)
    parser.add_argument("--target-cc", default=DEFAULT_TARGET_CC)
    parser.add_argument("--exchange-rate", type=float, default=DEFAULT_EXCHANGE_RATE)
    parser.add_argument(
        "--exchange-rate-source",
        default="FORM!B2 / người dùng xác nhận trên giao diện",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=PROJECT_ROOT / ".tmp_test_artifacts" / "real_pipeline_acceptance",
    )
    parser.add_argument("--template", type=Path, default=None)
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--headcount-source", type=Path, default=None)
    parser.add_argument("--uniform-policy", type=Path, default=None)
    parser.add_argument("--manual-input-store", type=Path, default=None)
    parser.add_argument("--operational-db", type=Path, default=None)
    parser.add_argument("--production-output", type=Path, default=None)
    parser.add_argument("--production-run-history", type=Path, default=None)
    parser.add_argument("--recovery-source-db", type=Path, default=None)
    return parser


def run_acceptance(args: argparse.Namespace) -> tuple[bool, Path]:
    fiscal_year = int(args.fy)
    target_cc = str(args.target_cc).strip()
    if not target_cc:
        raise ValueError("Target cost center is required")
    if fiscal_year != 2027:
        raise ValueError("This recovery-backed acceptance scenario is intentionally limited to FY2027")

    attempt_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    workspace_root = Path(args.workspace_root).resolve()
    attempt = workspace_root / attempt_id
    attempt.mkdir(parents=True, exist_ok=False)
    evidence_path = attempt / "acceptance_evidence.json"
    validator_path = attempt / "validator_result.json"
    stdout_path = attempt / "pipeline_stdout.log"
    stderr_path = attempt / "pipeline_stderr.log"

    template = Path(args.template or PROJECT_ROOT / "docs" / "MP2027" / "FORM.xlsx").resolve()
    source_dir = Path(args.source or PROJECT_ROOT / "docs" / "MP2027").resolve()
    headcount_source = Path(args.headcount_source or PROJECT_ROOT / "raw" / "10.07.2026").resolve()
    uniform_policy = Path(
        args.uniform_policy
        or PROJECT_ROOT / "raw" / "Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx"
    ).resolve()
    production_manual = Path(
        args.manual_input_store or PROJECT_ROOT / "raw" / "FY2027" / "manual_inputs.db"
    ).resolve()
    production_operational = Path(args.operational_db or PROJECT_ROOT / "mp2027.db").resolve()
    production_output = Path(
        args.production_output or PROJECT_ROOT / f"OUTPUT_FY{fiscal_year}"
    ).resolve()
    production_history = Path(
        args.production_run_history or PROJECT_ROOT / "RUN_HISTORY"
    ).resolve()
    recovery_source = Path(
        args.recovery_source_db
        or production_history / f"FY{fiscal_year}" / DEFAULT_RECOVERY_RUN_ID / "run.db"
    ).resolve()

    protected_paths = {
        "manual_input_store": production_manual,
        "operational_database": production_operational,
        "production_output": production_output,
        "production_run_history": production_history,
        "recovery_source_database": recovery_source,
    }
    evidence: dict[str, Any] = {
        "schema_version": 1,
        "attempt_id": attempt_id,
        "status": "FAIL",
        "fiscal_year": fiscal_year,
        "target_cc": target_cc,
        "exchange_rate": float(args.exchange_rate),
        "workspace": str(attempt),
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "paths": {
            "template": str(template),
            "source": str(source_dir),
            "headcount_source": str(headcount_source),
            "uniform_policy": str(uniform_policy),
            **{name: str(path) for name, path in protected_paths.items()},
        },
        "issues": [],
    }

    production_before: dict[str, Any] = {}
    try:
        required = [
            template,
            source_dir,
            headcount_source,
            uniform_policy,
            production_manual,
            production_operational,
            production_output,
            production_history,
            recovery_source,
        ]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise FileNotFoundError("Required real acceptance inputs are absent: " + ", ".join(missing))

        production_before = {
            name: _path_fingerprint(path) for name, path in protected_paths.items()
        }
        evidence["production_state_before"] = production_before

        sandbox_manual = attempt / "inputs" / "manual_inputs.db"
        sandbox_operational = attempt / "inputs" / "operational.db"
        sandbox_recovery = attempt / "inputs" / "recovery_run.db"
        sandbox_output = attempt / f"OUTPUT_FY{fiscal_year}"
        sandbox_history = attempt / "RUN_HISTORY"
        _snapshot_sqlite(production_manual, sandbox_manual)
        _snapshot_sqlite(production_operational, sandbox_operational)
        _snapshot_sqlite(recovery_source, sandbox_recovery)
        evidence["baseline_recovery"] = _prepare_approved_baseline(
            sandbox_manual,
            sandbox_recovery,
            fiscal_year=fiscal_year,
            target_cc=target_cc,
        )
        evidence["baseline_recovery"]["production_source_database"] = str(recovery_source)
        evidence["baseline_recovery"]["production_source_sha256"] = _sha256_file(recovery_source)
        preserved = _seed_public_output(production_output, sandbox_output, target_cc)
        evidence["preserved_public_workbooks"] = preserved

        command = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "run_e2e.py"),
            "--fy", str(fiscal_year),
            "--template", str(template),
            "--source", str(source_dir),
            "--headcount-source", str(headcount_source),
            "--uniform-policy", str(uniform_policy),
            "--operational-db", str(sandbox_operational),
            "--manual-input-store", str(sandbox_manual),
            "--output-dir", str(sandbox_output),
            "--run-history-root", str(sandbox_history),
            "--exchange-rate", str(float(args.exchange_rate)),
            "--exchange-rate-source", str(args.exchange_rate_source),
            "--target-cc", target_cc,
            "--reference-policy", "LEGACY_FY2027_MAP",
        ]
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "utf-8"
        environment["PYTHONUTF8"] = "1"
        started = time.perf_counter()
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        elapsed = time.perf_counter() - started
        stdout_path.write_text(completed.stdout, encoding="utf-8")
        stderr_path.write_text(completed.stderr, encoding="utf-8")
        hidden_traceback = "Traceback (most recent call last)" in (
            completed.stdout + "\n" + completed.stderr
        )
        evidence["subprocess"] = {
            "command": command,
            "cwd": str(PROJECT_ROOT),
            "return_code": completed.returncode,
            "elapsed_seconds": round(elapsed, 3),
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "hidden_traceback": hidden_traceback,
        }

        candidates = _catalog_candidates(
            sandbox_history,
            fiscal_year=fiscal_year,
            target_cc=target_cc,
        )
        evidence["catalog_candidates"] = candidates
        if len(candidates) != 1:
            raise RuntimeError(
                f"Expected exactly one new FY{fiscal_year}/CC{target_cc} run; found {len(candidates)}"
            )
        run_id = str(candidates[0]["run_id"])
        evidence["run_id"] = run_id
        validator = validate_real_pipeline_run(
            history_root=sandbox_history,
            fiscal_year=fiscal_year,
            target_cc=target_cc,
            run_id=run_id,
            expected_exchange_rate=float(args.exchange_rate),
            public_output_dir=sandbox_output,
            preserved_public_workbooks=preserved,
        )
        write_acceptance_result(validator, validator_path)
        evidence["validator_result_path"] = str(validator_path)
        evidence["validator_status"] = "PASS" if validator.passed else "FAIL"
        evidence["business_follow_up"] = validator.business_follow_up

        if completed.returncode != 0:
            evidence["issues"].append(
                f"Real pipeline subprocess exited with code {completed.returncode}"
            )
        if hidden_traceback:
            evidence["issues"].append("Pipeline logs contain a Python traceback")
        if not validator.passed:
            evidence["issues"].extend(
                f"{issue.check}: {issue.message}" for issue in validator.issues
            )
    except Exception as exc:
        evidence["issues"].append(f"{type(exc).__name__}: {exc}")
    finally:
        production_after = {
            name: _path_fingerprint(path) for name, path in protected_paths.items()
        }
        evidence["production_state_after"] = production_after
        production_unchanged = bool(production_before) and production_after == production_before
        evidence["production_unchanged"] = production_unchanged
        if not production_unchanged:
            evidence["issues"].append(
                "Protected production state changed during acceptance or could not be compared"
            )
        evidence["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        evidence["status"] = "PASS" if not evidence["issues"] else "FAIL"
        evidence_path.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return evidence["status"] == "PASS", evidence_path


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        passed, evidence_path = run_acceptance(args)
    except Exception as exc:
        print(f"Acceptance runner failed before evidence creation: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(f"Real pipeline acceptance: {'PASS' if passed else 'FAIL'}")
    print(f"Evidence: {evidence_path}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
