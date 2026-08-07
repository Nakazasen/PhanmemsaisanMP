"""Trình khởi chạy ổn định cho các bản phát hành onedir MP2027 theo phiên bản."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.cli import VietnameseArgumentParser


class LauncherStateError(ValueError):
    """Raised when the active application pointer is missing or unsafe."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LauncherStateError(f"Không đọc được trạng thái khởi động {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LauncherStateError(f"Trạng thái khởi động không hợp lệ: {path}")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_entrypoint(value: Any) -> str:
    text = str(value or "").replace("\\", "/")
    if not text or text.startswith("/") or ".." in text.split("/") or ":" in text:
        raise LauncherStateError(f"Tệp khởi động ứng dụng không an toàn: {value}")
    if not text.casefold().endswith(".exe"):
        raise LauncherStateError("Tệp khởi động ứng dụng phải có phần mở rộng .exe")
    return text


def resolve_current_entrypoint(app_root: str | os.PathLike[str]) -> Path:
    """Resolve the active version without importing update services."""
    root = Path(app_root).resolve()
    state = _read_json(root / "current.json")
    version_dir = root / "apps" / str(state.get("version", ""))
    manifest_path = version_dir / "manifest.json"
    if not manifest_path.is_file() or _sha256_file(manifest_path) != state.get("manifest_sha256"):
        raise LauncherStateError("Tệp kê khai của phiên bản đang dùng bị thiếu hoặc đã thay đổi")
    entrypoint = (version_dir / _safe_entrypoint(state.get("entrypoint"))).resolve()
    if version_dir.resolve() not in entrypoint.parents or not entrypoint.is_file():
        raise LauncherStateError("Không tìm thấy tệp khởi động của phiên bản đang dùng")
    return entrypoint


def default_app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return PROJECT_ROOT / "release_artifacts" / "install_bundle"


def main(argv=None) -> int:
    parser = VietnameseArgumentParser(description="Khởi chạy phiên bản MP2027 đang hoạt động")
    parser.add_argument("--app-root", default=str(default_app_root()))
    parser.add_argument("--health-check", action="store_true")
    parser.add_argument("app_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    app_args = args.app_args[1:] if args.app_args[:1] == ["--"] else args.app_args
    try:
        executable = resolve_current_entrypoint(args.app_root)
        if args.health_check:
            completed = subprocess.run(
                [str(executable), "--health-check", *app_args],
                cwd=str(executable.parent),
                timeout=180,
                check=False,
            )
            return completed.returncode
        subprocess.Popen([str(executable), *app_args], cwd=str(executable.parent))
    except (LauncherStateError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"Lỗi khởi động MP2027: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
