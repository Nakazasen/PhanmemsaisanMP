"""Các phép kiểm tra toàn vẹn dùng chung cho gói nội dung và bản phát hành đầy đủ.

Bộ cập nhật MP2027 không có khóa ký và không cần cấp phát khóa. Thư mục cập
nhật nội bộ được kiểm soát là ranh giới tin cậy; mô-đun dùng danh sách SHA-256
để bảo vệ khỏi hỏng dữ liệu, sao chép dở dang và đường dẫn lưu trữ không an toàn.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


MANIFEST_SCHEMA = 1
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_ARTIFACT_BYTES = 512 * 1024 * 1024
FORBIDDEN_ARTIFACT_SUFFIXES = {".exe", ".dll", ".pyd", ".py", ".pyc", ".bat", ".cmd", ".ps1"}


class ArtifactVerificationError(ValueError):
    """Raised when a hash-checked artifact is malformed or unsafe."""


def release_metadata_path() -> Path:
    """Return immutable metadata bundled with the running application."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "release.json"
    return Path(__file__).resolve().parents[2] / "release.json"


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
        path = _safe_relative_path(str(entry["path"]), allow_executable=artifact_kind == "application")
        if path in seen:
            raise ArtifactVerificationError(f"Đường dẫn bị trùng trong tệp kê khai: {path}")
        seen.add(path)
        digest = str(entry["sha256"])
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest.lower()):
            raise ArtifactVerificationError(f"Giá trị SHA-256 không hợp lệ cho {path}")
        if not isinstance(entry["size"], int) or isinstance(entry["size"], bool) or not 0 <= entry["size"] <= MAX_ARTIFACT_BYTES:
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
        relative = _safe_relative_path(entry["path"], allow_executable=artifact_kind == "application")
        path = (root / Path(relative)).resolve()
        if root not in path.parents:
            raise ArtifactVerificationError(f"Tệp trong gói nằm ngoài thư mục cho phép: {relative}")
        if not path.is_file():
            raise ArtifactVerificationError(f"Thiếu tệp đã kê khai: {relative}")
        if path.stat().st_size != entry["size"] or sha256_file(path) != entry["sha256"].lower():
            raise ArtifactVerificationError(f"Giá trị băm hoặc kích thước không khớp: {relative}")


ZIP_COPY_BUFFER_BYTES = 1024 * 1024


class _CountingReader:
    """Wrap a binary reader and retain the byte count copied by ``copyfileobj``."""

    def __init__(self, source) -> None:
        self._source = source
        self.bytes_read = 0

    def read(self, size: int = -1) -> bytes:
        block = self._source.read(size)
        self.bytes_read += len(block)
        return block


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
            relative = _safe_relative_path(info.filename, allow_executable=artifact_kind == "application")
            total += info.file_size
            if total > MAX_ARTIFACT_BYTES:
                raise ArtifactVerificationError("Dung lượng sau giải nén vượt quá giới hạn cho phép")
            destination = (target / Path(relative)).resolve()
            if target not in destination.parents:
                raise ArtifactVerificationError(f"Tệp nén ghi ra ngoài thư mục đích: {info.filename}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                with archive.open(info) as source, open(destination, "xb") as output:
                    counted_source = _CountingReader(source)
                    shutil.copyfileobj(
                        counted_source,
                        output,
                        length=ZIP_COPY_BUFFER_BYTES,
                    )
                if counted_source.bytes_read != info.file_size:
                    raise ArtifactVerificationError(
                        f"Kích thước mục trong tệp nén không khớp: {info.filename}"
                    )
            except Exception:
                destination.unlink(missing_ok=True)
                raise
