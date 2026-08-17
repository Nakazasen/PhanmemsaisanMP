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
        raise ArtifactVerificationError(
            f"Thiếu hoặc không hỗ trợ phiên bản cấu trúc tệp kê khai ({manifest.get('schema') if isinstance(manifest, dict) else type(manifest).__name__}). "
            f"Nguyên nhân: Trường 'schema' trong manifest.json không khớp với phiên bản hệ thống hỗ trợ ({MANIFEST_SCHEMA}). "
            f"Cách xử lý: Đảm bảo trường 'schema' trong manifest.json có giá trị là {MANIFEST_SCHEMA}."
        )
    required = {"schema", "kind", "id", "version", "min_app_version", "files"}
    missing = sorted(required - set(manifest))
    if missing:
        raise ArtifactVerificationError(
            f"Tệp kê khai thiếu các trường: {', '.join(missing)}. "
            "Nguyên nhân: manifest.json không chứa đủ các trường dữ liệu bắt buộc. "
            f"Cách xử lý: Bổ sung các trường {', '.join(missing)} vào manifest.json."
        )
    if manifest["kind"] != artifact_kind:
        raise ArtifactVerificationError(
            f"Loại gói phải là {artifact_kind!r} (nhận được {manifest.get('kind')!r}). "
            "Nguyên nhân: Giá trị trường 'kind' trong manifest.json không khớp với loại gói đang xử lý. "
            f"Cách xử lý: Đặt trường 'kind' trong manifest.json là '{artifact_kind}'."
        )
    if not all(isinstance(manifest[key], str) and manifest[key].strip() for key in ("id", "version", "min_app_version")):
        raise ArtifactVerificationError(
            "Các trường định danh và phiên bản trong tệp kê khai phải là chuỗi không rỗng. "
            "Nguyên nhân: 'id', 'version' hoặc 'min_app_version' trong manifest.json đang để trống. "
            "Cách xử lý: Nhập đầy đủ chuỗi định danh và phiên bản trong manifest.json."
        )
    files = manifest["files"]
    if not isinstance(files, list) or not files:
        raise ArtifactVerificationError(
            "Danh sách tệp trong tệp kê khai không được để trống. "
            "Nguyên nhân: Mảng 'files' trong manifest.json không chứa phần tử nào. "
            "Cách xử lý: Kê khai ít nhất một tệp trong mảng 'files'."
        )
    seen: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "size"}:
            raise ArtifactVerificationError(
                "Mỗi tệp trong tệp kê khai phải có đường dẫn, SHA-256 và kích thước. "
                "Nguyên nhân: Một phần tử trong 'files' bị thiếu trường 'path', 'sha256' hoặc 'size'. "
                "Cách xử lý: Nhập đầy đủ 3 trường cho từng phần tử trong 'files'."
            )
        path = _safe_relative_path(str(entry["path"]), allow_executable=artifact_kind == "application")
        if path in seen:
            raise ArtifactVerificationError(
                f"Đường dẫn bị trùng trong tệp kê khai: {path}. "
                "Nguyên nhân: Có hai tệp cùng đường dẫn trong danh sách files. "
                "Cách xử lý: Xóa bỏ mục kê khai trùng lặp."
            )
        seen.add(path)
        digest = str(entry["sha256"])
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest.lower()):
            raise ArtifactVerificationError(
                f"Giá trị SHA-256 không hợp lệ cho {path}. "
                "Nguyên nhân: Chuỗi băm SHA-256 phải là chuỗi hexa 64 ký tự. "
                f"Cách xử lý: Tính toán và cập nhật lại mã băm SHA-256 chuẩn cho tệp {path}."
            )
        if not isinstance(entry["size"], int) or isinstance(entry["size"], bool) or not 0 <= entry["size"] <= MAX_ARTIFACT_BYTES:
            raise ArtifactVerificationError(
                f"Kích thước không hợp lệ cho {path}. "
                f"Nguyên nhân: Kích thước tệp (size) phải là số nguyên từ 0 đến {MAX_ARTIFACT_BYTES}. "
                f"Cách xử lý: Cập nhật lại kích thước chính xác của tệp {path}."
            )


def _safe_relative_path(raw_path: str, *, allow_executable: bool = False) -> str:
    normalized = raw_path.replace("\\", "/")
    pure = PurePosixPath(normalized)
    if not normalized or pure.is_absolute() or ":" in pure.parts[0] or ".." in pure.parts:
        raise ArtifactVerificationError(
            f"Đường dẫn trong gói không an toàn: {raw_path}. "
            "Nguyên nhân: Đường dẫn chứa ký tự tuyệt đối hoặc dấu đi ngược thư mục '..'. "
            "Cách xử lý: Sử dụng đường dẫn tương đối an toàn trong gói."
        )
    if any(part in {"", "."} for part in pure.parts) or any(part.startswith(".") for part in pure.parts):
        raise ArtifactVerificationError(
            f"Đường dẫn ẩn hoặc không rõ ràng trong gói: {raw_path}. "
            "Nguyên nhân: Tên tệp hoặc thư mục bắt đầu bằng dấu chấm '.' hoặc rỗng. "
            "Cách xử lý: Đổi tên tệp không bắt đầu bằng dấu chấm."
        )
    if not allow_executable and pure.suffix.casefold() in FORBIDDEN_ARTIFACT_SUFFIXES:
        raise ArtifactVerificationError(
            f"Gói quy tắc không được chứa tệp thực thi: {raw_path}. "
            f"Nguyên nhân: Gói quy tắc chứa phần mở rộng tệp thực thi bị cấm ({', '.join(sorted(FORBIDDEN_ARTIFACT_SUFFIXES))}). "
            "Cách xử lý: Loại bỏ tệp thực thi ra khỏi gói quy tắc."
        )
    return pure.as_posix()


def verify_manifest_files(manifest: dict[str, Any], artifact_root: str | os.PathLike[str]) -> None:
    artifact_kind = str(manifest.get("kind", ""))
    validate_manifest(manifest, artifact_kind=artifact_kind)
    root = Path(artifact_root).resolve()
    for entry in manifest["files"]:
        relative = _safe_relative_path(entry["path"], allow_executable=artifact_kind == "application")
        path = (root / Path(relative)).resolve()
        if root not in path.parents:
            raise ArtifactVerificationError(
                f"Tệp trong gói nằm ngoài thư mục cho phép: {relative}. "
                "Nguyên nhân: Tệp sau khi giải nén trỏ ra ngoài thư mục đích an toàn. "
                "Cách xử lý: Đóng gói lại tệp không sử dụng đường dẫn thoát thư mục."
            )
        if not path.is_file():
            raise ArtifactVerificationError(
                f"Thiếu tệp đã kê khai: {relative}. "
                f"Nguyên nhân: Tệp {relative} có trong manifest.json nhưng không tồn tại thực tế sau khi giải nén. "
                f"Cách xử lý: Bổ sung tệp {relative} vào gói nén."
            )
        if path.stat().st_size != entry["size"] or sha256_file(path) != entry["sha256"].lower():
            raise ArtifactVerificationError(
                f"Giá trị băm hoặc kích thước không khớp: {relative}. "
                f"Nguyên nhân: Tệp {relative} bị thay đổi nội dung hoặc dung lượng so với thông tin trong manifest.json. "
                "Cách xử lý: Đóng gói lại gói từ nguồn tệp nguyên bản không bị sửa đổi."
            )


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
        raise ArtifactVerificationError(
            f"Không hỗ trợ loại gói: {artifact_kind}. "
            "Nguyên nhân: Loại gói yêu cầu không nằm trong danh sách hỗ trợ ('content' hoặc 'application'). "
            "Cách xử lý: Kiểm tra và cung cấp tham số loại gói hợp lệ."
        )
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
                raise ArtifactVerificationError(
                    f"Dung lượng sau giải nén vượt quá giới hạn cho phép ({total} > {MAX_ARTIFACT_BYTES} bytes). "
                    f"Nguyên nhân: Tổng dung lượng các tệp trong gói vượt mức an toàn tối đa {MAX_ARTIFACT_BYTES // (1024 * 1024)} MB. "
                    "Cách xử lý: Giảm bớt dung lượng hoặc chia nhỏ gói dữ liệu."
                )
            destination = (target / Path(relative)).resolve()
            if target not in destination.parents:
                raise ArtifactVerificationError(
                    f"Tệp nén ghi ra ngoài thư mục đích: {info.filename}. "
                    "Nguyên nhân: Tệp nén cố gắng ghi đè ra ngoài thư mục giải nén an toàn. "
                    "Cách xử lý: Đóng gói lại tệp nén mà không sử dụng đường dẫn tương đối thoát thư mục."
                )
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
                        f"Kích thước mục trong tệp nén không khớp: {info.filename} "
                        f"(thực tế {counted_source.bytes_read}, kê khai {info.file_size}). "
                        "Nguyên nhân: Quá trình giải nén bị ngắt quãng hoặc tệp nén bị lỗi giải mã. "
                        "Cách xử lý: Kiểm tra tính toàn vẹn của tệp nén và thử giải nén lại."
                    )
            except Exception:
                destination.unlink(missing_ok=True)
                raise
