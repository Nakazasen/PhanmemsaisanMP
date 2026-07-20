"""Signed artifact primitives shared by content packs and full releases.

This module deliberately verifies before activation. It does not download files,
execute Python, or replace a live application directory.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption


MANIFEST_SCHEMA = 1
# Shared by update discovery, package inspection, and the release builder.  Keep
# this bounded to avoid reading arbitrarily large untrusted ZIP members, while
# leaving sufficient headroom for a full onedir application's file inventory.
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_ARTIFACT_BYTES = 512 * 1024 * 1024
FORBIDDEN_ARTIFACT_SUFFIXES = {".exe", ".dll", ".pyd", ".py", ".pyc", ".bat", ".cmd", ".ps1"}


class ArtifactVerificationError(ValueError):
    """Raised when a signed artifact is malformed, unsafe, or unverifiable."""


_KEY_ID = re.compile(r"^[A-Za-z0-9._-]+$")
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_TRUST_PURPOSES = {"application", "content"}


def release_metadata_path() -> Path:
    """Return immutable metadata bundled with the running application."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "release.json"
    return Path(__file__).resolve().parents[2] / "release.json"


def resolve_trusted_signing_key(
    metadata: Any,
    key_id: str,
    *,
    purpose: str,
) -> tuple[str, str]:
    """Resolve an untrusted key ID through the immutable application allowlist."""
    if purpose not in _TRUST_PURPOSES:
        raise ArtifactVerificationError(f"Không hỗ trợ mục đích sử dụng khóa ký: {purpose}")
    if not isinstance(key_id, str) or not _KEY_ID.fullmatch(key_id):
        raise ArtifactVerificationError("Gói có mã khóa ký không hợp lệ")
    if not isinstance(metadata, dict):
        raise ArtifactVerificationError("Thông tin phát hành của ứng dụng không hợp lệ")
    app_version = metadata.get("version")
    if not isinstance(app_version, str) or not _SEMVER.fullmatch(app_version):
        raise ArtifactVerificationError("Thông tin phát hành của ứng dụng không có phiên bản hợp lệ")
    entries = metadata.get("trusted_signing_keys", [])
    if not isinstance(entries, list):
        raise ArtifactVerificationError("Cấu hình khóa ký tin cậy của ứng dụng không hợp lệ")

    match: str | None = None
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != {"id", "public_key", "purposes"}:
            raise ArtifactVerificationError(f"Khóa ký tin cậy số {index} có các trường không hợp lệ")
        candidate_id = entry["id"]
        if not isinstance(candidate_id, str) or not _KEY_ID.fullmatch(candidate_id):
            raise ArtifactVerificationError(f"Khóa ký tin cậy số {index} có mã không hợp lệ")
        if candidate_id in seen:
            raise ArtifactVerificationError(f"Mã khóa ký tin cậy bị trùng: {candidate_id}")
        seen.add(candidate_id)
        purposes = entry["purposes"]
        if (
            not isinstance(purposes, list)
            or not purposes
            or any(item not in _TRUST_PURPOSES for item in purposes)
            or len(set(purposes)) != len(purposes)
        ):
            raise ArtifactVerificationError(f"Khóa ký tin cậy {candidate_id} có mục đích sử dụng không hợp lệ")
        public_key = entry["public_key"]
        if not isinstance(public_key, str):
            raise ArtifactVerificationError(f"Khóa ký tin cậy {candidate_id} có khóa công khai không hợp lệ")
        try:
            decoded = base64.b64decode(public_key.encode("ascii"), validate=True)
        except (UnicodeEncodeError, ValueError) as exc:
            raise ArtifactVerificationError(
                f"Khóa ký tin cậy {candidate_id} không đúng định dạng Base64"
            ) from exc
        if len(decoded) != 32:
            raise ArtifactVerificationError(
                f"Khóa ký tin cậy {candidate_id} không phải khóa công khai Ed25519"
            )
        if candidate_id == key_id and purpose in purposes:
            match = public_key
    if match is None:
        label = "bản cập nhật ứng dụng" if purpose == "application" else "gói quy tắc"
        raise ArtifactVerificationError(f"Khóa ký của {label} không nằm trong danh sách tin cậy: {key_id}")
    return app_version, match


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: str | os.PathLike[str]) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _decode_key(value: str, expected_length: int) -> bytes:
    try:
        decoded = base64.b64decode(value.encode("ascii"), validate=True)
    except Exception as exc:
        raise ArtifactVerificationError("Khóa ký không đúng định dạng Base64") from exc
    if len(decoded) != expected_length:
        raise ArtifactVerificationError(f"Khóa ký sau khi giải mã phải có {expected_length} byte")
    return decoded


def generate_signing_keypair() -> tuple[str, str]:
    """Return base64 raw private/public Ed25519 keys for offline key provisioning."""
    private = Ed25519PrivateKey.generate()
    private_bytes = private.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    public_bytes = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return (
        base64.b64encode(private_bytes).decode("ascii"),
        base64.b64encode(public_bytes).decode("ascii"),
    )


def sign_payload(payload: dict[str, Any], private_key_b64: str) -> str:
    private = Ed25519PrivateKey.from_private_bytes(_decode_key(private_key_b64, 32))
    signature = private.sign(canonical_json_bytes(payload))
    return base64.b64encode(signature).decode("ascii")


def verify_payload(payload: dict[str, Any], signature_b64: str, public_key_b64: str) -> None:
    try:
        signature = base64.b64decode(signature_b64.encode("ascii"), validate=True)
        public = Ed25519PublicKey.from_public_bytes(_decode_key(public_key_b64, 32))
        public.verify(signature, canonical_json_bytes(payload))
    except (InvalidSignature, ValueError, TypeError, ArtifactVerificationError) as exc:
        raise ArtifactVerificationError("Không xác thực được chữ ký của gói") from exc


def validate_manifest(manifest: dict[str, Any], *, artifact_kind: str) -> None:
    if not isinstance(manifest, dict) or manifest.get("schema") != MANIFEST_SCHEMA:
        raise ArtifactVerificationError("Thiếu hoặc không hỗ trợ phiên bản cấu trúc tệp kê khai")
    required = {"schema", "kind", "id", "version", "min_app_version", "files"}
    missing = sorted(required - set(manifest))
    if missing:
        raise ArtifactVerificationError("Tệp kê khai thiếu các trường: " + ", ".join(missing))
    if manifest["kind"] != artifact_kind:
        raise ArtifactVerificationError(f"Loại gói phải là {artifact_kind!r}")
    if not all(isinstance(manifest[key], str) and manifest[key].strip() for key in ("id", "version", "min_app_version")):
        raise ArtifactVerificationError("Các trường định danh và phiên bản trong tệp kê khai phải là chuỗi không rỗng")
    files = manifest["files"]
    if not isinstance(files, list) or not files:
        raise ArtifactVerificationError("Danh sách tệp trong tệp kê khai không được để trống")
    seen: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "size"}:
            raise ArtifactVerificationError("Mỗi tệp trong tệp kê khai phải có đường dẫn, SHA-256 và kích thước")
        path = _safe_relative_path(
            str(entry["path"]),
            allow_executable=artifact_kind == "application",
        )
        if path in seen:
            raise ArtifactVerificationError(f"Đường dẫn bị trùng trong tệp kê khai: {path}")
        seen.add(path)
        if len(str(entry["sha256"])) != 64 or any(char not in "0123456789abcdef" for char in str(entry["sha256"]).lower()):
            raise ArtifactVerificationError(f"Giá trị SHA-256 không hợp lệ cho {path}")
        if not isinstance(entry["size"], int) or not 0 <= entry["size"] <= MAX_ARTIFACT_BYTES:
            raise ArtifactVerificationError(f"Kích thước không hợp lệ cho {path}")


def _safe_relative_path(raw_path: str, *, allow_executable: bool = False) -> str:
    normalized = raw_path.replace("\\", "/")
    pure = PurePosixPath(normalized)
    if not normalized or pure.is_absolute() or ":" in pure.parts[0] or ".." in pure.parts:
        raise ArtifactVerificationError(f"Đường dẫn trong gói không an toàn: {raw_path}")
    if any(part in {"", "."} for part in pure.parts) or any(part.startswith(".") for part in pure.parts):
        raise ArtifactVerificationError(f"Đường dẫn ẩn hoặc không rõ ràng trong gói: {raw_path}")
    if not allow_executable and pure.suffix.casefold() in FORBIDDEN_ARTIFACT_SUFFIXES:
        raise ArtifactVerificationError(f"Gói quy tắc không được chứa tệp thực thi: {raw_path}")
    return pure.as_posix()


def verify_manifest_files(manifest: dict[str, Any], artifact_root: str | os.PathLike[str]) -> None:
    artifact_kind = str(manifest.get("kind", ""))
    validate_manifest(manifest, artifact_kind=artifact_kind)
    root = Path(artifact_root).resolve()
    for entry in manifest["files"]:
        relative = _safe_relative_path(
            entry["path"],
            allow_executable=artifact_kind == "application",
        )
        path = (root / Path(relative)).resolve()
        if root not in path.parents:
            raise ArtifactVerificationError(f"Tệp trong gói nằm ngoài thư mục cho phép: {relative}")
        if not path.is_file():
            raise ArtifactVerificationError(f"Thiếu tệp đã kê khai: {relative}")
        if path.stat().st_size != entry["size"] or sha256_file(path) != entry["sha256"].lower():
            raise ArtifactVerificationError(f"Giá trị băm hoặc kích thước không khớp: {relative}")


def safe_extract_zip(
    archive_path: str | os.PathLike[str],
    target_dir: str | os.PathLike[str],
    *,
    artifact_kind: str = "content",
) -> None:
    if artifact_kind not in {"content", "application"}:
        raise ArtifactVerificationError(f"Không hỗ trợ loại gói: {artifact_kind}")
    target = Path(target_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        total = 0
        for info in archive.infolist():
            if info.is_dir():
                continue
            relative = _safe_relative_path(
                info.filename,
                allow_executable=artifact_kind == "application",
            )
            total += info.file_size
            if total > MAX_ARTIFACT_BYTES:
                raise ArtifactVerificationError("Dung lượng sau giải nén vượt quá giới hạn cho phép")
            destination = (target / Path(relative)).resolve()
            if target not in destination.parents:
                raise ArtifactVerificationError(f"Tệp nén ghi ra ngoài thư mục đích: {info.filename}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source:
                data = source.read(MAX_ARTIFACT_BYTES + 1)
            if len(data) != info.file_size:
                raise ArtifactVerificationError(f"Kích thước mục trong tệp nén không khớp: {info.filename}")
            with open(destination, "xb") as output:
                output.write(data)
