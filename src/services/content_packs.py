"""Install and activate signed, data-only MP2027 content packs."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from src.services.update_security import (
    ArtifactVerificationError,
    canonical_json_bytes,
    release_metadata_path,
    resolve_trusted_signing_key,
    safe_extract_zip,
    sha256_file,
    validate_manifest,
    verify_manifest_files,
    verify_payload,
)

CONTENT_SCHEMA = 1
_ALLOWED_DRIVERS = {
    "headcount_all",
    "headcount_staff",
    "headcount_worker",
    "headcount_male",
    "headcount_female",
    "working_days",
    "fixed_ratio",
}
_RULE_FIELDS = {
    "source_dept",
    "item_name",
    "account_name",
    "mfg_account",
    "ga_account",
    "sales_account",
    "posting_month",
    "unit_price",
    "unit",
    "driver_type",
    "driver_raw",
}
_REQUIRED_RULE_FIELDS = {"source_dept", "item_name", "unit_price", "driver_type"}
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class ContentPackError(ArtifactVerificationError):
    """Raised when a content pack violates its restricted data contract."""


def _version(value: str) -> tuple[int, int, int]:
    match = _SEMVER.fullmatch(str(value))
    if not match:
        raise ContentPackError(f"Phiên bản không đúng định dạng ba phần: {value}")
    return tuple(int(part) for part in match.groups())


def validate_rules(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or set(payload) != {"schema", "rules"}:
        raise ContentPackError("Tệp rules.json chỉ được chứa phiên bản cấu trúc và danh sách quy tắc")
    if payload["schema"] != CONTENT_SCHEMA:
        raise ContentPackError("Không hỗ trợ phiên bản cấu trúc quy tắc này")
    rules = payload["rules"]
    if not isinstance(rules, list) or not rules:
        raise ContentPackError("Gói quy tắc phải có ít nhất một quy tắc")
    validated: list[dict[str, Any]] = []
    identities: set[tuple[str, str]] = set()
    account_labels = {
        "mfg_account": "tài khoản sản xuất",
        "ga_account": "tài khoản hành chính",
        "sales_account": "tài khoản bán hàng",
    }
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise ContentPackError(f"Quy tắc số {index} phải là một đối tượng dữ liệu")
        unknown = set(rule) - _RULE_FIELDS
        missing = _REQUIRED_RULE_FIELDS - set(rule)
        if unknown or missing:
            raise ContentPackError(
                f"Các trường của quy tắc số {index} không hợp lệ; "
                f"trường còn thiếu={sorted(missing)}, trường không được hỗ trợ={sorted(unknown)}"
            )
        source = str(rule["source_dept"]).strip()
        name = str(rule["item_name"]).strip()
        driver = str(rule["driver_type"]).strip()
        if not source or not name:
            raise ContentPackError(f"Quy tắc số {index} phải có bộ phận nguồn và tên khoản mục")
        identity = (source.casefold(), name.casefold())
        if identity in identities:
            raise ContentPackError(f"Quy tắc bị trùng: {source}/{name}")
        identities.add(identity)
        if driver not in _ALLOWED_DRIVERS:
            raise ContentPackError(f"Quy tắc số {index} dùng cách tính không được hỗ trợ: {driver}")
        price = rule["unit_price"]
        if isinstance(price, bool) or not isinstance(price, (int, float)) or price < 0:
            raise ContentPackError(f"Quy tắc số {index} có đơn giá không hợp lệ")
        month = rule.get("posting_month")
        if month not in (None, "") and not re.fullmatch(r"(?:0?[1-9]|1[0-2])", str(month)):
            raise ContentPackError(f"Quy tắc số {index} có tháng hạch toán không hợp lệ")
        for field in ("mfg_account", "ga_account", "sales_account"):
            value = rule.get(field)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value <= 0):
                raise ContentPackError(
                    f"Quy tắc số {index} có {account_labels[field]} không hợp lệ"
                )
        validated.append(dict(rule))
    return validated


def _read_zip_member(archive: zipfile.ZipFile, name: str, *, max_bytes: int) -> bytes:
    try:
        info = archive.getinfo(name)
    except KeyError as exc:
        raise ContentPackError(f"Gói quy tắc thiếu tệp {name}") from exc
    if info.file_size > max_bytes:
        raise ContentPackError(f"Tệp trong gói quy tắc vượt quá dung lượng cho phép: {name}")
    data = archive.read(info)
    if len(data) != info.file_size:
        raise ContentPackError(f"Kích thước tệp trong gói quy tắc không khớp: {name}")
    return data


def inspect_content_pack(
    pack_path: str | os.PathLike[str],
    *,
    public_key_b64: str,
    current_app_version: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = Path(pack_path)
    try:
        with zipfile.ZipFile(path) as archive:
            names = {info.filename for info in archive.infolist() if not info.is_dir()}
            manifest_bytes = _read_zip_member(archive, "manifest.json", max_bytes=512 * 1024)
            signature = _read_zip_member(archive, "manifest.sig", max_bytes=1024).decode("ascii")
            manifest = json.loads(manifest_bytes.decode("utf-8-sig"))
            validate_manifest(manifest, artifact_kind="content")
            key_id = manifest.get("key_id")
            if not isinstance(key_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", key_id):
                raise ContentPackError("Gói quy tắc thiếu hoặc có mã khóa key_id không hợp lệ")
            if manifest.get("content_schema") != CONTENT_SCHEMA:
                raise ContentPackError("Không hỗ trợ phiên bản cấu trúc gói quy tắc này")
            if not isinstance(manifest.get("fiscal_year"), int) or manifest["fiscal_year"] < 2027:
                raise ContentPackError("Năm tài chính của gói quy tắc không hợp lệ")
            if _version(current_app_version) < _version(manifest["min_app_version"]):
                raise ContentPackError("Gói quy tắc yêu cầu phiên bản ứng dụng mới hơn")
            expected = {"manifest.json", "manifest.sig", *(item["path"] for item in manifest["files"])}
            if names != expected:
                raise ContentPackError("Gói quy tắc có tệp bị thiếu hoặc không có trong kê khai")
            verify_payload(manifest, signature, public_key_b64)
            rules_bytes = _read_zip_member(archive, "rules.json", max_bytes=8 * 1024 * 1024)
            rules_payload = json.loads(rules_bytes.decode("utf-8-sig"))
            validate_rules(rules_payload)
    except ContentPackError:
        raise
    except ArtifactVerificationError as exc:
        raise ContentPackError(str(exc)) from exc
    except (zipfile.BadZipFile, UnicodeError, json.JSONDecodeError) as exc:
        raise ContentPackError("Gói quy tắc không hợp lệ hoặc đã bị hỏng") from exc
    return manifest, rules_payload


def install_content_pack(
    pack_path: str | os.PathLike[str],
    content_root: str | os.PathLike[str],
    *,
    public_key_b64: str,
    current_app_version: str,
    activate: bool = False,
) -> Path:
    manifest, _rules = inspect_content_pack(
        pack_path,
        public_key_b64=public_key_b64,
        current_app_version=current_app_version,
    )
    root = Path(content_root).resolve()
    installed = root / "installed"
    destination = installed / manifest["id"] / manifest["version"]
    if destination.exists():
        raise ContentPackError(f"Phiên bản gói quy tắc đã được cài đặt: {destination}")
    installed.mkdir(parents=True, exist_ok=True)
    staging_parent = root / ".staging"
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="content-", dir=staging_parent))
    try:
        safe_extract_zip(pack_path, staging, artifact_kind="content")
        verify_manifest_files(manifest, staging)
        validate_rules(json.loads((staging / "rules.json").read_text(encoding="utf-8-sig")))
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging, destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    if activate:
        activate_content_pack(root, manifest["id"], manifest["version"])
    return destination


def activate_content_pack(content_root: str | os.PathLike[str], pack_id: str, version: str) -> Path:
    root = Path(content_root).resolve()
    pack_dir = root / "installed" / pack_id / version
    manifest_path = pack_dir / "manifest.json"
    if not manifest_path.is_file():
        raise ContentPackError(f"Không tìm thấy gói quy tắc đã cài đặt: {pack_id} {version}")
    state = {
        "schema": 1,
        "id": pack_id,
        "version": version,
        "manifest_sha256": sha256_file(manifest_path),
    }
    root.mkdir(parents=True, exist_ok=True)
    temporary = root / "active.json.tmp"
    temporary.write_bytes(canonical_json_bytes(state))
    os.replace(temporary, root / "active.json")
    return pack_dir


def _release_metadata_path() -> Path:
    return release_metadata_path()


def _trusted_content_public_key(metadata: Any, key_id: str) -> tuple[str, str]:
    try:
        return resolve_trusted_signing_key(metadata, key_id, purpose="content")
    except ArtifactVerificationError as exc:
        raise ContentPackError(str(exc)) from exc


def install_runtime_content_pack(
    pack_path: str | os.PathLike[str],
    runtime_root: str | os.PathLike[str],
    *,
    fiscal_year: int,
    release_metadata_path: str | os.PathLike[str] | None = None,
) -> Path:
    """Install and activate a signed pack using immutable application trust."""
    try:
        with zipfile.ZipFile(pack_path) as archive:
            manifest = json.loads(
                _read_zip_member(archive, "manifest.json", max_bytes=512 * 1024).decode("utf-8-sig")
            )
        key_id = manifest.get("key_id") if isinstance(manifest, dict) else None
        if not isinstance(key_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", key_id):
            raise ContentPackError("Gói quy tắc thiếu hoặc có mã khóa key_id không hợp lệ")
        metadata_path = Path(release_metadata_path).resolve() if release_metadata_path else _release_metadata_path()
        metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
        app_version, public_key = _trusted_content_public_key(metadata, key_id)
        verified_manifest, _rules = inspect_content_pack(
            pack_path,
            public_key_b64=public_key,
            current_app_version=app_version,
        )
        if verified_manifest.get("fiscal_year") != fiscal_year:
            raise ContentPackError(
                f"Gói quy tắc dành cho FY{verified_manifest.get('fiscal_year')}, không phải FY{fiscal_year}"
            )
    except ContentPackError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        raise ContentPackError("Không xác định được khóa tin cậy cho gói quy tắc") from exc
    return install_content_pack(
        pack_path,
        Path(runtime_root).resolve() / "content-packs",
        public_key_b64=public_key,
        current_app_version=app_version,
        activate=True,
    )


def load_runtime_content_rules(
    runtime_root: str | os.PathLike[str],
    *,
    fiscal_year: int,
    release_metadata_path: str | os.PathLike[str] | None = None,
) -> list[dict[str, Any]]:
    """Resolve and verify active content rules for one fiscal run.

    A normal installation without an active pack returns immediately and does
    not require a configured signing key. If an active pointer exists, trust or
    verification failures are fatal before allocation rules are changed.
    """
    content_root = Path(runtime_root).resolve() / "content-packs"
    active_path = content_root / "active.json"
    if not active_path.exists():
        return []
    try:
        state = json.loads(active_path.read_text(encoding="utf-8-sig"))
        pack_id = state.get("id") if isinstance(state, dict) else None
        pack_version = state.get("version") if isinstance(state, dict) else None
        if not isinstance(pack_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", pack_id):
            raise ContentPackError("Mã gói quy tắc đang dùng không hợp lệ")
        if not isinstance(pack_version, str):
            raise ContentPackError("Phiên bản gói quy tắc đang dùng không hợp lệ")
        _version(pack_version)
        manifest_path = content_root / "installed" / pack_id / pack_version / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        key_id = manifest.get("key_id") if isinstance(manifest, dict) else None
        if not isinstance(key_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", key_id):
            raise ContentPackError("Gói quy tắc thiếu hoặc có mã khóa key_id không hợp lệ")
        metadata_path = Path(release_metadata_path).resolve() if release_metadata_path else _release_metadata_path()
        metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
        app_version, public_key = _trusted_content_public_key(metadata, key_id)
    except ContentPackError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContentPackError("Không xác định được khóa tin cậy cho gói quy tắc đang dùng") from exc
    return load_active_content_rules(
        content_root,
        public_key_b64=public_key,
        current_app_version=app_version,
        fiscal_year=fiscal_year,
    )


def load_active_content_rules(
    content_root: str | os.PathLike[str],
    *,
    public_key_b64: str,
    current_app_version: str,
    fiscal_year: int,
) -> list[dict[str, Any]]:
    """Load active rules only after revalidating installed signed content."""
    root = Path(content_root).resolve()
    state_path = root / "active.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContentPackError("Không đọc được trạng thái gói quy tắc đang dùng") from exc
    required_state = {"schema", "id", "version", "manifest_sha256"}
    if not isinstance(state, dict) or set(state) != required_state or state.get("schema") != 1:
        raise ContentPackError("Trạng thái gói quy tắc đang dùng không hợp lệ")
    pack_id = state.get("id")
    version = state.get("version")
    if not isinstance(pack_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", pack_id):
        raise ContentPackError("Mã gói quy tắc đang dùng không hợp lệ")
    _version(str(version))
    pack_dir = root / "installed" / pack_id / str(version)
    manifest_path = pack_dir / "manifest.json"
    signature_path = pack_dir / "manifest.sig"
    rules_path = pack_dir / "rules.json"
    try:
        if not manifest_path.is_file() or sha256_file(manifest_path) != state.get("manifest_sha256"):
            raise ContentPackError("Tệp kê khai của gói quy tắc đang dùng bị thiếu hoặc đã thay đổi")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        validate_manifest(manifest, artifact_kind="content")
        key_id = manifest.get("key_id")
        if not isinstance(key_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", key_id):
            raise ContentPackError("Gói quy tắc thiếu hoặc có mã khóa key_id không hợp lệ")
        if manifest.get("id") != pack_id or manifest.get("version") != version:
            raise ContentPackError("Thông tin kích hoạt không khớp với tệp kê khai của gói đã cài")
        if manifest.get("content_schema") != CONTENT_SCHEMA:
            raise ContentPackError("Không hỗ trợ phiên bản cấu trúc gói quy tắc này")
        if manifest.get("fiscal_year") != fiscal_year:
            raise ContentPackError(
                f"Gói quy tắc đang dùng dành cho FY{manifest.get('fiscal_year')}, không phải FY{fiscal_year}"
            )
        if _version(current_app_version) < _version(manifest["min_app_version"]):
            raise ContentPackError("Gói quy tắc yêu cầu phiên bản ứng dụng mới hơn")
        if not signature_path.is_file():
            raise ContentPackError("Thiếu chữ ký của gói quy tắc đang dùng")
        verify_payload(manifest, signature_path.read_text(encoding="ascii"), public_key_b64)
        verify_manifest_files(manifest, pack_dir)
        if {item["path"] for item in manifest["files"]} != {"rules.json"}:
            raise ContentPackError("Gói quy tắc đang dùng chứa tệp không được hỗ trợ")
        actual_files: set[str] = set()
        for installed_path in pack_dir.rglob("*"):
            if installed_path.is_symlink():
                raise ContentPackError("Gói quy tắc đang dùng chứa liên kết tượng trưng")
            if installed_path.is_file():
                actual_files.add(installed_path.relative_to(pack_dir).as_posix())
        expected_files = {"manifest.json", "manifest.sig", "rules.json"}
        if actual_files != expected_files:
            raise ContentPackError("Gói quy tắc đang dùng có tệp bị thiếu hoặc không có trong kê khai")
        rules_payload = json.loads(rules_path.read_text(encoding="utf-8-sig"))
        return validate_rules(rules_payload)
    except ContentPackError:
        raise
    except ArtifactVerificationError as exc:
        raise ContentPackError(str(exc)) from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContentPackError("Gói quy tắc đã cài đặt không hợp lệ hoặc đã bị hỏng") from exc
