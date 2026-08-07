"""Discover and fetch MP2027 application updates from folders or HTTPS.

Delivery metadata is only a discovery aid. A downloaded package must still pass
``install_runtime_application_update``: catalog SHA-256, manifest inventory,
safe extraction, and staged health checks.
"""

from __future__ import annotations

import json
import os
import re
import ssl
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from src.services.app_updates import ApplicationUpdateError, inspect_update_package
from src.services.update_security import (
    MAX_ARTIFACT_BYTES,
    MAX_MANIFEST_BYTES,
    ArtifactVerificationError,
    release_metadata_path,
    sha256_file,
)

CONFIG_SCHEMA = 1
CATALOG_SCHEMA = 1
MAX_CONFIG_BYTES = 256 * 1024
MAX_CATALOG_BYTES = 256 * 1024
# Backward-compatible export for delivery tests and callers. The authoritative
# ceiling is shared with package inspection and the release builder.
MAX_UPDATE_MANIFEST_BYTES = MAX_MANIFEST_BYTES
MAX_DOWNLOAD_BYTES = MAX_ARTIFACT_BYTES
DEFAULT_TIMEOUT_SECONDS = 5.0
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_SAFE_PACKAGE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.mpupdate$", re.IGNORECASE)


class UpdateDeliveryError(ValueError):
    """Raised when an update source or delivery artifact is invalid."""


@dataclass(frozen=True)
class UpdateSource:
    type: str
    location: str
    enabled: bool = True


@dataclass(frozen=True)
class UpdateCandidate:
    version: str
    source_type: str
    location: str
    package_name: str
    size: int | None = None
    sha256: str | None = None
    notes: str = ""


def _version(value: str) -> tuple[int, int, int]:
    match = _SEMVER.fullmatch(str(value))
    if not match:
        raise UpdateDeliveryError(f"Phiên bản cập nhật không hợp lệ: {value}")
    return tuple(int(part) for part in match.groups())


def default_update_config_path() -> Path:
    """Return the immutable update-source defaults bundled with the app."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "update_sources.default.json"
    return Path(__file__).resolve().parents[2] / "update_sources.default.json"


def company_update_config_path(*, program_data: str | os.PathLike[str] | None = None) -> Path | None:
    root = str(program_data or os.environ.get("PROGRAMDATA", "")).strip()
    return Path(root) / "MPManager" / "update_sources.json" if root else None


def user_update_config_path(runtime_root: str | os.PathLike[str]) -> Path:
    return Path(runtime_root).resolve() / "update_sources.json"


def _read_json_file(path: Path, *, max_bytes: int) -> Any:
    try:
        if path.stat().st_size > max_bytes:
            raise UpdateDeliveryError(f"Tệp cấu hình cập nhật quá lớn: {path}")
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except UpdateDeliveryError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise UpdateDeliveryError(f"Không đọc được cấu hình cập nhật: {path}") from exc


def _validate_source(value: Any, *, index: int) -> UpdateSource:
    if not isinstance(value, dict) or set(value) != {"type", "location", "enabled"}:
        raise UpdateDeliveryError(f"Nguồn cập nhật số {index + 1} có các trường không hợp lệ")
    source_type = value["type"]
    location = value["location"]
    enabled = value["enabled"]
    if source_type not in {"folder", "https"} or not isinstance(enabled, bool):
        raise UpdateDeliveryError(f"Nguồn cập nhật số {index + 1} không hợp lệ")
    if not isinstance(location, str) or not location.strip() or "\x00" in location:
        raise UpdateDeliveryError(f"Đường dẫn nguồn cập nhật số {index + 1} không hợp lệ")
    location = location.strip()
    if source_type == "https":
        parsed = urllib.parse.urlparse(location)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise UpdateDeliveryError("Nguồn WAN phải là HTTPS hợp lệ và không chứa thông tin đăng nhập")
    return UpdateSource(type=source_type, location=location, enabled=enabled)


def validate_update_config(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"schema", "startup_check", "sources"}:
        raise UpdateDeliveryError("Cấu hình nguồn cập nhật có các trường không hợp lệ")
    if value["schema"] != CONFIG_SCHEMA or not isinstance(value["startup_check"], bool):
        raise UpdateDeliveryError("Cấu hình nguồn cập nhật có schema hoặc startup_check không hợp lệ")
    if not isinstance(value["sources"], list):
        raise UpdateDeliveryError("Danh sách nguồn cập nhật không hợp lệ")
    sources: list[dict[str, Any]] = []
    for index, item in enumerate(value["sources"]):
        source = _validate_source(item, index=index)
        sources.append({"type": source.type, "location": source.location, "enabled": source.enabled})
    return {"schema": CONFIG_SCHEMA, "startup_check": value["startup_check"], "sources": sources}


def load_update_config(
    runtime_root: str | os.PathLike[str],
    *,
    default_path: str | os.PathLike[str] | None = None,
    program_data: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Load defaults, then user override, then company policy (highest priority)."""
    candidates: list[Path] = [Path(default_path) if default_path else default_update_config_path()]
    candidates.append(user_update_config_path(runtime_root))
    policy_path = company_update_config_path(program_data=program_data)
    if policy_path is not None:
        candidates.append(policy_path)
    selected: dict[str, Any] = {"schema": 1, "startup_check": False, "sources": []}
    for path in candidates:
        if path.is_file():
            selected = validate_update_config(_read_json_file(path, max_bytes=MAX_CONFIG_BYTES))
    return selected


def save_user_update_config(runtime_root: str | os.PathLike[str], config: Any) -> Path:
    validated = validate_update_config(config)
    path = user_update_config_path(runtime_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(validated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return path


def _release_metadata(metadata_path: str | os.PathLike[str] | None) -> dict[str, Any]:
    path = Path(metadata_path) if metadata_path else release_metadata_path()
    value = _read_json_file(path, max_bytes=MAX_CONFIG_BYTES)
    if not isinstance(value, dict):
        raise UpdateDeliveryError("Thông tin phát hành của ứng dụng không hợp lệ")
    return value


def current_release_version(
    release_metadata_path_override: str | os.PathLike[str] | None = None,
) -> str:
    metadata = _release_metadata(release_metadata_path_override)
    version = str(metadata.get("version", ""))
    _version(version)
    return version


def _manifest_identity(package_path: Path) -> str:
    try:
        with zipfile.ZipFile(package_path) as archive:
            info = archive.getinfo("manifest.json")
            if info.file_size > MAX_UPDATE_MANIFEST_BYTES:
                raise UpdateDeliveryError("Tệp kê khai cập nhật quá lớn")
            manifest = json.loads(archive.read(info).decode("utf-8-sig"))
        return str(manifest.get("version", ""))
    except UpdateDeliveryError:
        raise
    except (OSError, KeyError, zipfile.BadZipFile, UnicodeError, json.JSONDecodeError) as exc:
        raise UpdateDeliveryError(f"Bỏ qua gói cập nhật bị hỏng: {package_path.name}") from exc


def _verified_folder_candidate(
    path: Path,
    current_app_version: str,
    *,
    current_database_schema: int,
) -> UpdateCandidate:
    _manifest_identity(path)
    try:
        manifest = inspect_update_package(
            path,
            current_app_version=current_app_version,
            current_database_schema=current_database_schema,
        )
    except (ApplicationUpdateError, ArtifactVerificationError) as exc:
        raise UpdateDeliveryError(str(exc)) from exc
    return UpdateCandidate(
        version=str(manifest["version"]),
        source_type="folder",
        location=str(path),
        package_name=path.name,
        size=path.stat().st_size,
    )


def discover_folder_updates(
    folder: str | os.PathLike[str],
    *,
    current_database_schema: int,
    release_metadata_path_override: str | os.PathLike[str] | None = None,
) -> list[UpdateCandidate]:
    root = Path(folder).expanduser()
    if not root.is_dir():
        raise UpdateDeliveryError(f"Không truy cập được thư mục cập nhật: {root}")
    metadata = _release_metadata(release_metadata_path_override)
    current_app_version = str(metadata.get("version", ""))
    _version(current_app_version)
    catalog_path = root / "latest.json"
    if catalog_path.is_file():
        package_name, catalog_version, digest, size, notes = _validated_catalog(
            _read_json_file(catalog_path, max_bytes=MAX_CATALOG_BYTES)
        )
        package_path = root / package_name
        candidate = _verified_folder_candidate(
            package_path,
            current_app_version,
            current_database_schema=current_database_schema,
        )
        if candidate.version != catalog_version:
            raise UpdateDeliveryError("Catalog có phiên bản không khớp gói cập nhật")
        if candidate.size != size or sha256_file(package_path) != digest:
            raise UpdateDeliveryError("Catalog có hash hoặc dung lượng không khớp gói cập nhật")
        return [
            UpdateCandidate(
                version=candidate.version,
                source_type="folder",
                location=candidate.location,
                package_name=candidate.package_name,
                size=size,
                sha256=digest,
                notes=notes,
            )
        ]

    # Legacy shares without latest.json still work, but cannot carry release notes.
    candidates: list[UpdateCandidate] = []
    for path in sorted(root.glob("*.mpupdate")):
        if not path.is_file():
            continue
        try:
            candidates.append(_verified_folder_candidate(path, current_app_version, current_database_schema=current_database_schema))
        except (UpdateDeliveryError, OSError):
            continue
    return candidates


def _read_https_json(url: str, *, timeout: float) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "MP2027-Update/1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            content_type = response.headers.get_content_type()
            if content_type not in {"application/json", "text/json", "text/plain"}:
                raise UpdateDeliveryError("Máy chủ cập nhật không trả về JSON")
            data = response.read(MAX_CATALOG_BYTES + 1)
    except UpdateDeliveryError:
        raise
    except Exception as exc:
        raise UpdateDeliveryError("Không kết nối được máy chủ cập nhật HTTPS") from exc
    if len(data) > MAX_CATALOG_BYTES:
        raise UpdateDeliveryError("Catalog cập nhật vượt quá dung lượng cho phép")
    try:
        return json.loads(data.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise UpdateDeliveryError("Catalog cập nhật không phải JSON hợp lệ") from exc


def _validated_catalog(value: Any) -> tuple[str, str, str, int, str]:
    required = {"schema", "channel", "version", "package", "sha256", "size", "notes"}
    if not isinstance(value, dict) or set(value) != required or value["schema"] != CATALOG_SCHEMA:
        raise UpdateDeliveryError("Catalog cập nhật có các trường không hợp lệ")
    version = str(value["version"])
    _version(version)
    package_name = value["package"]
    digest = value["sha256"]
    size = value["size"]
    notes = value["notes"]
    if not isinstance(package_name, str) or not _SAFE_PACKAGE_NAME.fullmatch(package_name):
        raise UpdateDeliveryError("Catalog có tên gói cập nhật không an toàn")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise UpdateDeliveryError("Catalog có SHA-256 không hợp lệ")
    if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= MAX_DOWNLOAD_BYTES:
        raise UpdateDeliveryError("Catalog có dung lượng gói không hợp lệ")
    if not isinstance(value["channel"], str) or not isinstance(notes, str) or len(notes) > 2000:
        raise UpdateDeliveryError("Catalog có channel hoặc ghi chú không hợp lệ")
    return package_name, version, digest, size, notes


def discover_https_update(base_url: str, *, current_version: str, timeout: float = 5.0) -> UpdateCandidate | None:
    base = base_url.rstrip("/") + "/"
    package_name, version, digest, size, notes = _validated_catalog(
        _read_https_json(urllib.parse.urljoin(base, "latest.json"), timeout=timeout)
    )
    if _version(version) <= _version(current_version):
        return None
    return UpdateCandidate(
        version=version,
        source_type="https",
        location=urllib.parse.urljoin(base, urllib.parse.quote(package_name)),
        package_name=package_name,
        size=size,
        sha256=digest,
        notes=notes,
    )


def validate_update_source(source_type: str, location: str, *, enabled: bool = True) -> UpdateSource:
    """Validate one source with the same rules used for persisted configuration."""
    return _validate_source(
        {"type": source_type, "location": location, "enabled": enabled},
        index=0,
    )


def check_update_source(source: UpdateSource, *, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
    """Raise when a configured source is unavailable or malformed."""
    if source.type == "folder":
        folder = Path(source.location).expanduser()
        if not folder.is_dir():
            raise UpdateDeliveryError(f"Không truy cập được thư mục cập nhật: {folder}")
        try:
            next(folder.iterdir(), None)
        except OSError as exc:
            raise UpdateDeliveryError(f"Không đọc được thư mục cập nhật: {folder}") from exc
        return
    if source.type == "https":
        discover_https_update(source.location, current_version="0.0.0", timeout=timeout)
        return
    raise UpdateDeliveryError(f"Không hỗ trợ loại nguồn cập nhật: {source.type}")


def discover_available_update(
    sources: Iterable[dict[str, Any] | UpdateSource],
    *,
    current_version: str,
    current_database_schema: int,
    release_metadata_path_override: str | os.PathLike[str] | None = None,
    timeout: float = 5.0,
) -> UpdateCandidate | None:
    found: list[UpdateCandidate] = []
    for raw_source in sources:
        try:
            source = raw_source if isinstance(raw_source, UpdateSource) else _validate_source(raw_source, index=0)
            if not source.enabled:
                continue
            if source.type == "folder":
                found.extend(discover_folder_updates(
                    source.location,
                    current_database_schema=current_database_schema,
                    release_metadata_path_override=release_metadata_path_override,
                ))
            elif source.type == "https":
                candidate = discover_https_update(source.location, current_version=current_version, timeout=timeout)
                if candidate is not None:
                    found.append(candidate)
        except (UpdateDeliveryError, TypeError):
            continue
    eligible = [item for item in found if _version(item.version) > _version(current_version)]
    return max(eligible, key=lambda item: _version(item.version), default=None)


def fetch_update_candidate(
    candidate: UpdateCandidate,
    runtime_root: str | os.PathLike[str],
    *,
    timeout: float = 30.0,
) -> Path:
    """Copy/download an update to a local atomic cache and validate catalog hash."""
    cache = Path(runtime_root).resolve() / ".updates" / "downloads"
    cache.mkdir(parents=True, exist_ok=True)
    destination = cache / f"MP2027_Manager_{candidate.version}.mpupdate"
    descriptor, temp_name = tempfile.mkstemp(prefix="download-", suffix=".tmp", dir=cache)
    os.close(descriptor)
    temporary = Path(temp_name)
    total = 0
    try:
        if candidate.source_type == "folder":
            source = Path(candidate.location)
            with source.open("rb") as input_file, temporary.open("wb") as output_file:
                for block in iter(lambda: input_file.read(1024 * 1024), b""):
                    total += len(block)
                    if total > MAX_DOWNLOAD_BYTES:
                        raise UpdateDeliveryError("Gói cập nhật vượt quá dung lượng cho phép")
                    output_file.write(block)
        elif candidate.source_type == "https":
            request = urllib.request.Request(candidate.location, headers={"User-Agent": "MP2027-Update/1"})
            with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response, temporary.open("wb") as output_file:
                for block in iter(lambda: response.read(1024 * 1024), b""):
                    total += len(block)
                    if total > MAX_DOWNLOAD_BYTES:
                        raise UpdateDeliveryError("Gói cập nhật vượt quá dung lượng cho phép")
                    output_file.write(block)
        else:
            raise UpdateDeliveryError("Không hỗ trợ loại nguồn cập nhật này")
        if candidate.size is not None and total != candidate.size:
            raise UpdateDeliveryError("Dung lượng gói tải về không khớp catalog")
        if candidate.sha256 is not None and sha256_file(temporary) != candidate.sha256:
            raise UpdateDeliveryError("SHA-256 của gói tải về không khớp catalog")
        os.replace(temporary, destination)
        return destination
    except UpdateDeliveryError:
        temporary.unlink(missing_ok=True)
        raise
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        raise UpdateDeliveryError("Không tải được gói cập nhật về máy") from exc
