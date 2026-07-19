"""Machine-readable runtime health checks for source and packaged releases."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class HealthCheck:
    name: str
    status: str
    detail: str


def copy_missing_tree(source_dir: str | os.PathLike[str], target_dir: str | os.PathLike[str]) -> None:
    """Copy immutable seed files without overwriting user-managed data."""
    source = Path(source_dir)
    target = Path(target_dir)
    if not source.is_dir():
        return
    target.mkdir(parents=True, exist_ok=True)
    for path in source.rglob("*"):
        if not path.is_file() or path.name.startswith("~$"):
            continue
        destination = target / path.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(path, destination)


def directory_is_writable(path: str | os.PathLike[str]) -> bool:
    """Return whether *path* can host mutable project data."""
    target = Path(path)
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe = target / f".mp2027-write-probe-{os.getpid()}-{time.time_ns()}"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def packaged_project_root(
    app_dir: str | os.PathLike[str],
    *,
    local_app_data: str | None = None,
    writable_check: Callable[[str | os.PathLike[str]], bool] = directory_is_writable,
) -> str:
    """Choose stable writable storage independently from versioned app files."""
    app_root = Path(app_dir).resolve()
    portable_mode = os.environ.get("MP_MANAGER_PORTABLE_MODE", "").strip().casefold()
    if portable_mode in {"1", "true", "yes", "on"}:
        if not writable_check(app_root):
            raise PermissionError(
                "Đã bật chế độ portable nhưng thư mục chương trình không có quyền ghi: "
                f"{app_root}"
            )
        return str(app_root)

    user_root = Path(
        local_app_data
        or os.environ.get("LOCALAPPDATA")
        or os.path.join(os.path.expanduser("~"), ".mp_manager")
    )
    stable_root = (user_root / "MPManager" / "Projects" / "MP2027").resolve()
    if not writable_check(stable_root):
        raise PermissionError(
            "Không tìm thấy thư mục có quyền ghi cho dữ liệu MP2027. "
            f"Đã thử: {stable_root}"
        )
    return str(stable_root)


def ensure_external_runtime_data(
    app_dir: str | os.PathLike[str],
    bundled_root: str | os.PathLike[str],
    *,
    frozen: bool,
    local_app_data: str | None = None,
    writable_check: Callable[[str | os.PathLike[str]], bool] = directory_is_writable,
) -> str:
    """Seed bundled data into the stable runtime root and return that root."""
    if not frozen:
        return str(Path(app_dir).resolve())

    runtime_root = Path(
        packaged_project_root(
            app_dir,
            local_app_data=local_app_data,
            writable_check=writable_check,
        )
    )
    bundled = Path(bundled_root)
    copy_missing_tree(bundled / "docs" / "MP2027", runtime_root / "docs" / "MP2027")
    copy_missing_tree(bundled / "raw", runtime_root / "raw")
    os.environ["MP_MANAGER_RUNTIME_ROOT"] = str(runtime_root)
    return str(runtime_root)


def _release_path() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "release.json"
    return Path(__file__).resolve().parents[2] / "release.json"


def _check_release_metadata(_runtime_root: Path) -> HealthCheck:
    path = _release_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        version = str(payload["version"])
        app = str(payload["application"])
    except Exception as exc:
        return HealthCheck(
            "release_metadata",
            "error",
            f"Thông tin phát hành không hợp lệ tại {path}: {exc}",
        )
    return HealthCheck("release_metadata", "ok", f"{app} {version}; {path}")


def _check_runtime_write(runtime_root: Path) -> HealthCheck:
    try:
        runtime_root.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=".mp-health-",
            dir=runtime_root,
            delete=False,
        ) as handle:
            handle.write("ok")
            probe = Path(handle.name)
        probe.unlink()
    except Exception as exc:
        return HealthCheck(
            "runtime_write",
            "error",
            f"Không thể ghi vào thư mục môi trường chạy {runtime_root}: {exc}",
        )
    return HealthCheck("runtime_write", "ok", str(runtime_root))


def _check_seed_form(runtime_root: Path) -> HealthCheck:
    form = runtime_root / "docs" / "MP2027" / "FORM.xlsx"
    if not form.is_file():
        return HealthCheck("seed_form", "error", f"Không tìm thấy tệp biểu mẫu: {form}")
    return HealthCheck("seed_form", "ok", str(form))


def _check_sqlite(runtime_root: Path) -> HealthCheck:
    from src.db.migrations import CURRENT_SCHEMA_VERSION
    from src.db.schema import create_schema

    db_path: Path | None = None
    conn: sqlite3.Connection | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".mp-health-db-", suffix=".sqlite", dir=runtime_root, delete=False
        ) as handle:
            db_path = Path(handle.name)
        conn = sqlite3.connect(db_path)
        create_schema(conn)
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        version = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
        if integrity != "ok" or int(version) != CURRENT_SCHEMA_VERSION:
            raise RuntimeError(
                f"Tính toàn vẹn={integrity}; phiên bản lược đồ={version}"
            )
    except Exception as exc:
        return HealthCheck("sqlite", "error", f"Lỗi kiểm tra cơ sở dữ liệu SQLite: {exc}")
    finally:
        if conn is not None:
            conn.close()
        if db_path is not None:
            db_path.unlink(missing_ok=True)
            for suffix in ("-journal", "-wal", "-shm"):
                Path(str(db_path) + suffix).unlink(missing_ok=True)
    return HealthCheck(
        "sqlite",
        "ok",
        f"phiên bản lược đồ={CURRENT_SCHEMA_VERSION}; tính toàn vẹn=đạt",
    )


def run_health_checks(runtime_root: str | os.PathLike[str]) -> dict:
    root = Path(runtime_root).resolve()
    checks: tuple[Callable[[Path], HealthCheck], ...] = (
        _check_release_metadata,
        _check_runtime_write,
        _check_seed_form,
        _check_sqlite,
    )
    results = [check(root) for check in checks]
    return {
        "status": "ok" if all(item.status == "ok" for item in results) else "error",
        "runtime_root": str(root),
        "frozen": bool(getattr(sys, "frozen", False)),
        "checks": [asdict(item) for item in results],
    }


def print_health_report(runtime_root: str | os.PathLike[str]) -> int:
    report = run_health_checks(runtime_root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "ok" else 2
