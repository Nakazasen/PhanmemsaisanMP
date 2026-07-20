"""Stage, health-check, activate, and roll back signed onedir releases."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Callable

from src.services.update_security import (
    ArtifactVerificationError,
    MAX_MANIFEST_BYTES,
    canonical_json_bytes,
    release_metadata_path,
    resolve_trusted_signing_key,
    safe_extract_zip,
    sha256_file,
    validate_manifest,
    verify_manifest_files,
    verify_payload,
)

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class ApplicationUpdateError(ArtifactVerificationError):
    """Raised when a full application update cannot be safely processed."""


def _version(value: str) -> tuple[int, int, int]:
    match = _SEMVER.fullmatch(str(value))
    if not match:
        raise ApplicationUpdateError(f"Phiên bản không đúng định dạng ba phần: {value}")
    return tuple(int(part) for part in match.groups())


def application_install_root(application_dir: str | os.PathLike[str]) -> Path:
    """Resolve ``<install>/apps/<version>`` to the stable launcher root."""
    version_dir = Path(application_dir).resolve()
    if version_dir.parent.name.lower() != "apps" or not _SEMVER.fullmatch(version_dir.name):
        raise ApplicationUpdateError(
            "Tự cập nhật chỉ dùng được với bản MP2027 đã cài đặt."
        )
    return version_dir.parent.parent


def _safe_entrypoint(value: Any) -> str:
    text = str(value or "").replace("\\", "/")
    if not text or text.startswith("/") or ".." in text.split("/") or ":" in text:
        raise ApplicationUpdateError(f"Tệp khởi động trong bản cập nhật không an toàn: {value}")
    if not text.casefold().endswith(".exe"):
        raise ApplicationUpdateError("Tệp khởi động trong bản cập nhật phải có phần mở rộng .exe")
    return text


def _read_member(archive: zipfile.ZipFile, name: str, max_bytes: int) -> bytes:
    try:
        info = archive.getinfo(name)
    except KeyError as exc:
        raise ApplicationUpdateError(f"Bản cập nhật thiếu tệp {name}") from exc
    if info.file_size > max_bytes:
        raise ApplicationUpdateError(f"Tệp trong bản cập nhật vượt quá dung lượng cho phép: {name}")
    data = archive.read(info)
    if len(data) != info.file_size:
        raise ApplicationUpdateError(f"Kích thước tệp trong bản cập nhật không khớp: {name}")
    return data


def validate_application_manifest(
    manifest: dict[str, Any],
    *,
    current_app_version: str,
    current_database_schema: int,
) -> None:
    validate_manifest(manifest, artifact_kind="application")
    required = {"database_schema", "health_check", "entrypoint", "key_id"}
    missing = sorted(required - set(manifest))
    if missing:
        raise ApplicationUpdateError("Tệp kê khai ứng dụng thiếu các trường: " + ", ".join(missing))
    key_id = manifest["key_id"]
    if not isinstance(key_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", key_id):
        raise ApplicationUpdateError("Tệp kê khai ứng dụng có mã khóa key_id không hợp lệ")
    target = _version(manifest["version"])
    current = _version(current_app_version)
    minimum = _version(manifest["min_app_version"])
    if target <= current:
        raise ApplicationUpdateError("Phiên bản cập nhật ứng dụng phải mới hơn phiên bản hiện tại")
    if current < minimum:
        raise ApplicationUpdateError("Bản cập nhật yêu cầu phiên bản khởi đầu mới hơn")
    schema = manifest["database_schema"]
    if not isinstance(schema, int) or isinstance(schema, bool) or schema < current_database_schema:
        raise ApplicationUpdateError("Bản cập nhật không được hạ phiên bản lược đồ cơ sở dữ liệu")
    if manifest["health_check"] != "--health-check":
        raise ApplicationUpdateError("Không hỗ trợ lệnh kiểm tra tình trạng ứng dụng này")
    entrypoint = _safe_entrypoint(manifest["entrypoint"])
    if entrypoint not in {item["path"].replace("\\", "/") for item in manifest["files"]}:
        raise ApplicationUpdateError("Tệp khởi động ứng dụng không có trong danh sách tệp kê khai")


def inspect_update_package(
    update_path: str | os.PathLike[str],
    *,
    public_key_b64: str,
    current_app_version: str,
    current_database_schema: int,
) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(update_path) as archive:
            manifest = json.loads(_read_member(archive, "manifest.json", MAX_MANIFEST_BYTES).decode("utf-8-sig"))
            signature = _read_member(archive, "manifest.sig", 1024).decode("ascii")
            validate_application_manifest(
                manifest,
                current_app_version=current_app_version,
                current_database_schema=current_database_schema,
            )
            verify_payload(manifest, signature, public_key_b64)
            names = {info.filename.replace("\\", "/") for info in archive.infolist() if not info.is_dir()}
            expected = {"manifest.json", "manifest.sig", *(item["path"].replace("\\", "/") for item in manifest["files"])}
            if names != expected:
                raise ApplicationUpdateError("Bản cập nhật có tệp bị thiếu hoặc không có trong kê khai")
    except ApplicationUpdateError:
        raise
    except ArtifactVerificationError as exc:
        raise ApplicationUpdateError(str(exc)) from exc
    except (zipfile.BadZipFile, UnicodeError, json.JSONDecodeError) as exc:
        raise ApplicationUpdateError("Bản cập nhật ứng dụng không hợp lệ hoặc đã bị hỏng") from exc
    return manifest


def stage_application_update(
    update_path: str | os.PathLike[str],
    app_root: str | os.PathLike[str],
    *,
    public_key_b64: str,
    current_app_version: str,
    current_database_schema: int,
) -> Path:
    manifest = inspect_update_package(
        update_path,
        public_key_b64=public_key_b64,
        current_app_version=current_app_version,
        current_database_schema=current_database_schema,
    )
    root = Path(app_root).resolve()
    destination = root / "apps" / manifest["version"]
    if destination.exists():
        raise ApplicationUpdateError(f"Phiên bản ứng dụng đã được chuẩn bị trước đó: {manifest['version']}")
    staging_parent = root / ".staging"
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="app-", dir=staging_parent))
    try:
        safe_extract_zip(update_path, staging, artifact_kind="application")
        verify_manifest_files(manifest, staging)
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging, destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return destination


def _read_update_identity(update_path: str | os.PathLike[str]) -> tuple[str, str]:
    try:
        with zipfile.ZipFile(update_path) as archive:
            manifest = json.loads(
                _read_member(archive, "manifest.json", 512 * 1024).decode("utf-8-sig")
            )
    except ApplicationUpdateError:
        raise
    except (OSError, zipfile.BadZipFile, UnicodeError, json.JSONDecodeError) as exc:
        raise ApplicationUpdateError("Bản cập nhật ứng dụng không hợp lệ hoặc đã bị hỏng") from exc
    if not isinstance(manifest, dict):
        raise ApplicationUpdateError("Tệp kê khai bản cập nhật ứng dụng phải là một đối tượng dữ liệu")
    key_id = manifest.get("key_id")
    version = manifest.get("version")
    if not isinstance(key_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", key_id):
        raise ApplicationUpdateError("Tệp kê khai ứng dụng có mã khóa key_id không hợp lệ")
    if not isinstance(version, str):
        raise ApplicationUpdateError("Tệp kê khai ứng dụng có phiên bản không hợp lệ")
    return key_id, version


def run_staged_health(
    version_dir: str | os.PathLike[str],
    manifest: dict[str, Any],
    *,
    health_data_root: str | os.PathLike[str],
    runner: Callable[..., Any] = subprocess.run,
) -> None:
    version = Path(version_dir).resolve()
    executable = (version / _safe_entrypoint(manifest["entrypoint"])).resolve()
    if version not in executable.parents or not executable.is_file():
        raise ApplicationUpdateError(f"Không tìm thấy tệp khởi động của phiên bản đang chuẩn bị: {executable}")
    env = os.environ.copy()
    env["LOCALAPPDATA"] = str(Path(health_data_root).resolve())
    env.pop("MP_MANAGER_PORTABLE_MODE", None)
    try:
        runner(
            [str(executable), manifest["health_check"]],
            check=True,
            cwd=str(version),
            env=env,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ApplicationUpdateError("Phiên bản đang chuẩn bị không vượt qua kiểm tra tình trạng") from exc


def backup_runtime_databases(
    runtime_root: str | os.PathLike[str],
    backup_root: str | os.PathLike[str],
    *,
    target_version: str,
) -> Path:
    source = Path(runtime_root).resolve()
    destination = Path(backup_root).resolve() / f"before-{target_version}"
    if destination.exists():
        raise ApplicationUpdateError(f"Bản sao lưu trước cập nhật đã tồn tại: {destination}")
    candidates = sorted(
        path for path in source.rglob("*")
        if path.is_file() and path.suffix.casefold() in {".db", ".sqlite", ".sqlite3"}
        and "backup" not in {part.casefold() for part in path.relative_to(source).parts}
    )
    destination.mkdir(parents=True, exist_ok=False)
    inventory: list[dict[str, Any]] = []
    try:
        for path in candidates:
            relative = path.relative_to(source)
            copied = destination / relative
            copied.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, copied)
            inventory.append({"path": relative.as_posix(), "sha256": sha256_file(copied), "size": copied.stat().st_size})
        (destination / "backup.json").write_bytes(canonical_json_bytes({
            "schema": 1,
            "target_version": target_version,
            "files": inventory,
        }))
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return destination


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ApplicationUpdateError(f"Không đọc được trạng thái cập nhật tại {path}") from exc
    if not isinstance(value, dict):
        raise ApplicationUpdateError(f"Trạng thái cập nhật không hợp lệ: {path}")
    return value


def _write_pointer(root: Path, name: str, state: dict[str, Any]) -> None:
    temporary = root / f"{name}.tmp"
    temporary.write_bytes(canonical_json_bytes(state))
    os.replace(temporary, root / name)


def activate_staged_update(
    app_root: str | os.PathLike[str],
    version: str,
    *,
    public_key_b64: str,
    health_data_root: str | os.PathLike[str],
    runtime_root: str | os.PathLike[str] | None = None,
    health_runner: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    root = Path(app_root).resolve()
    version_dir = root / "apps" / version
    manifest_path = version_dir / "manifest.json"
    signature_path = version_dir / "manifest.sig"
    if not manifest_path.is_file() or not signature_path.is_file():
        raise ApplicationUpdateError(f"Phiên bản đang chuẩn bị chưa đầy đủ: {version}")
    manifest = _read_json(manifest_path)
    if manifest.get("version") != version or manifest.get("kind") != "application":
        raise ApplicationUpdateError("Thông tin nhận dạng trong tệp kê khai không khớp với thư mục phiên bản")
    try:
        verify_payload(manifest, signature_path.read_text(encoding="ascii"), public_key_b64)
        verify_manifest_files(manifest, version_dir)
    except ArtifactVerificationError as exc:
        raise ApplicationUpdateError(str(exc)) from exc
    run_staged_health(version_dir, manifest, health_data_root=health_data_root, runner=health_runner)
    if runtime_root is not None:
        backup_runtime_databases(runtime_root, root / "backups", target_version=version)
    current_path = root / "current.json"
    if current_path.exists():
        current = _read_json(current_path)
        _write_pointer(root, "previous.json", current)
    state = {
        "schema": 1,
        "version": version,
        "entrypoint": manifest["entrypoint"],
        "manifest_sha256": sha256_file(manifest_path),
    }
    root.mkdir(parents=True, exist_ok=True)
    _write_pointer(root, "current.json", state)
    return state


def rollback_activation(app_root: str | os.PathLike[str]) -> dict[str, Any]:
    root = Path(app_root).resolve()
    current_path = root / "current.json"
    previous_path = root / "previous.json"
    if not current_path.is_file() or not previous_path.is_file():
        raise ApplicationUpdateError("Không có phiên bản ứng dụng trước đó để hoàn tác")
    current = _read_json(current_path)
    previous = _read_json(previous_path)
    previous_dir = root / "apps" / str(previous.get("version", ""))
    entrypoint = (previous_dir / _safe_entrypoint(previous.get("entrypoint"))).resolve()
    if previous_dir.resolve() not in entrypoint.parents or not entrypoint.is_file():
        raise ApplicationUpdateError("Thiếu các tệp của phiên bản ứng dụng trước đó")
    _write_pointer(root, "current.json", previous)
    _write_pointer(root, "previous.json", current)
    return previous


def install_runtime_application_update(
    update_path: str | os.PathLike[str],
    app_root: str | os.PathLike[str],
    runtime_root: str | os.PathLike[str],
    *,
    current_database_schema: int,
    release_metadata_path_override: str | os.PathLike[str] | None = None,
    health_data_root: str | os.PathLike[str] | None = None,
    health_runner: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    """Verify, stage, health-check, back up, and activate an offline update."""
    try:
        key_id, version = _read_update_identity(update_path)
        metadata_path = (
            Path(release_metadata_path_override).resolve()
            if release_metadata_path_override
            else release_metadata_path()
        )
        metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
        current_version, public_key = resolve_trusted_signing_key(
            metadata,
            key_id,
            purpose="application",
        )
    except ApplicationUpdateError:
        raise
    except (ArtifactVerificationError, OSError, json.JSONDecodeError) as exc:
        raise ApplicationUpdateError(str(exc)) from exc

    root = Path(app_root).resolve()
    staged: Path | None = None
    try:
        staged = stage_application_update(
            update_path,
            root,
            public_key_b64=public_key,
            current_app_version=current_version,
            current_database_schema=current_database_schema,
        )
        return activate_staged_update(
            root,
            version,
            public_key_b64=public_key,
            health_data_root=health_data_root or (root / ".health"),
            runtime_root=runtime_root,
            health_runner=health_runner,
        )
    except ApplicationUpdateError:
        if staged is not None:
            shutil.rmtree(staged, ignore_errors=True)
        raise
    except Exception as exc:
        if staged is not None:
            shutil.rmtree(staged, ignore_errors=True)
        raise ApplicationUpdateError("Cập nhật ứng dụng không thành công") from exc


def resolve_current_entrypoint(app_root: str | os.PathLike[str]) -> Path:
    root = Path(app_root).resolve()
    state = _read_json(root / "current.json")
    version_dir = root / "apps" / str(state.get("version", ""))
    manifest_path = version_dir / "manifest.json"
    if not manifest_path.is_file() or sha256_file(manifest_path) != state.get("manifest_sha256"):
        raise ApplicationUpdateError("Tệp kê khai của phiên bản đang dùng bị thiếu hoặc đã thay đổi")
    entrypoint = (version_dir / _safe_entrypoint(state.get("entrypoint"))).resolve()
    if version_dir.resolve() not in entrypoint.parents or not entrypoint.is_file():
        raise ApplicationUpdateError("Không tìm thấy tệp khởi động của phiên bản đang dùng")
    return entrypoint
