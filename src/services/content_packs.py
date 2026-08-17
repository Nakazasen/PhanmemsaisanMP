"""Cài đặt và kích hoạt các gói nội dung MP2027 chỉ chứa dữ liệu có kiểm tra toàn vẹn."""

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
    release_metadata_path as bundled_release_metadata_path,
    safe_extract_zip,
    sha256_file,
    validate_manifest,
    verify_manifest_files,
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
        raise ContentPackError(
            f"Phiên bản không đúng định dạng ba phần: {value}. "
            "Nguyên nhân: Chuỗi phiên bản phải theo chuẩn Semantic Versioning (ví dụ: 1.0.0). "
            "Cách xử lý: Kiểm tra và hiệu chỉnh lại trường phiên bản (version) trong tệp kê khai manifest.json."
        )
    return tuple(int(part) for part in match.groups())


def validate_rules(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or set(payload) != {"schema", "rules"}:
        raise ContentPackError(
            "Tệp rules.json chỉ được chứa phiên bản cấu trúc và danh sách quy tắc. "
            "Nguyên nhân: Tệp rules.json chứa các trường ngoài đặc tả hệ thống. "
            "Cách xử lý: Đảm bảo rules.json chỉ chứa đúng hai khóa gốc là 'schema' và 'rules'."
        )
    if payload["schema"] != CONTENT_SCHEMA:
        raise ContentPackError(
            f"Không hỗ trợ phiên bản cấu trúc quy tắc này ({payload.get('schema')}). "
            f"Nguyên nhân: Phiên bản cấu trúc của rules.json không khớp với phiên bản hệ thống hỗ trợ ({CONTENT_SCHEMA}). "
            "Cách xử lý: Cập nhật tệp rules.json theo đúng phiên bản cấu trúc yêu cầu."
        )
    rules = payload["rules"]
    if not isinstance(rules, list) or not rules:
        raise ContentPackError(
            "Gói quy tắc phải có ít nhất một quy tắc. "
            "Nguyên nhân: Danh sách 'rules' trong tệp rules.json đang rỗng. "
            "Cách xử lý: Thêm ít nhất một quy tắc phân bổ vào tệp rules.json trước khi đóng gói."
        )
    validated: list[dict[str, Any]] = []
    identities: set[tuple[str, str]] = set()
    account_labels = {
        "mfg_account": "tài khoản sản xuất",
        "ga_account": "tài khoản hành chính",
        "sales_account": "tài khoản bán hàng",
    }
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise ContentPackError(
                f"Quy tắc số {index} phải là một đối tượng dữ liệu. "
                "Nguyên nhân: Phần tử trong danh sách quy tắc không phải là một đối tượng JSON (dictionary). "
                "Cách xử lý: Định dạng lại từng phần tử trong danh sách rules thành đối tượng JSON hợp lệ."
            )
        unknown = set(rule) - _RULE_FIELDS
        missing = _REQUIRED_RULE_FIELDS - set(rule)
        if unknown or missing:
            raise ContentPackError(
                f"Các trường của quy tắc số {index} không hợp lệ; "
                f"trường còn thiếu={sorted(missing)}, trường không được hỗ trợ={sorted(unknown)}. "
                "Nguyên nhân: Cấu trúc quy tắc phân bổ không khớp với định nghĩa của hệ thống. "
                f"Cách xử lý: Bổ sung các trường bắt buộc {sorted(missing)} và loại bỏ các trường không được hỗ trợ {sorted(unknown)}."
            )
        source = str(rule["source_dept"]).strip()
        name = str(rule["item_name"]).strip()
        driver = str(rule["driver_type"]).strip()
        if not source or not name:
            raise ContentPackError(
                f"Quy tắc số {index} phải có bộ phận nguồn và tên khoản mục. "
                "Nguyên nhân: Trường 'source_dept' hoặc 'item_name' đang để trống. "
                "Cách xử lý: Nhập đầy đủ thông tin phòng ban nguồn và tên khoản mục cho quy tắc này."
            )
        identity = (source.casefold(), name.casefold())
        if identity in identities:
            raise ContentPackError(
                f"Quy tắc bị trùng: {source}/{name}. "
                "Nguyên nhân: Có hai quy tắc cùng bộ phận nguồn và tên khoản mục trong cùng gói quy tắc. "
                "Cách xử lý: Gộp hoặc đổi tên khoản mục để đảm bảo tính duy nhất của từng quy tắc."
            )
        identities.add(identity)
        if driver not in _ALLOWED_DRIVERS:
            raise ContentPackError(
                f"Quy tắc số {index} dùng cách tính không được hỗ trợ: {driver}. "
                f"Nguyên nhân: Driver phân bổ '{driver}' không nằm trong danh sách driver cho phép. "
                f"Cách xử lý: Sử dụng một trong các driver sau: {', '.join(sorted(_ALLOWED_DRIVERS))}."
            )
        price = rule["unit_price"]
        if isinstance(price, bool) or not isinstance(price, (int, float)) or price < 0:
            raise ContentPackError(
                f"Quy tắc số {index} có đơn giá không hợp lệ ({price}). "
                "Nguyên nhân: Đơn giá (unit_price) phải là giá trị số không âm (>= 0). "
                "Cách xử lý: Nhập lại số tiền hoặc đơn giá hợp lệ cho quy tắc này."
            )
        month = rule.get("posting_month")
        if month not in (None, "") and not re.fullmatch(r"(?:0?[1-9]|1[0-2])", str(month)):
            raise ContentPackError(
                f"Quy tắc số {index} có tháng hạch toán không hợp lệ ({month}). "
                "Nguyên nhân: Tháng hạch toán phải là số từ 1 đến 12 hoặc để trống/null. "
                "Cách xử lý: Nhập tháng từ 1 đến 12 hoặc để trống nếu áp dụng cho tất cả các tháng."
            )
        for field in ("mfg_account", "ga_account", "sales_account"):
            value = rule.get(field)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value <= 0):
                raise ContentPackError(
                    f"Quy tắc số {index} có {account_labels[field]} không hợp lệ ({value}). "
                    "Nguyên nhân: Mã tài khoản kế toán phải là số nguyên dương (> 0). "
                    "Cách xử lý: Nhập lại mã tài khoản hợp lệ trong danh mục tài khoản."
                )
        validated.append(dict(rule))
    return validated


def _read_zip_member(archive: zipfile.ZipFile, name: str, *, max_bytes: int) -> bytes:
    try:
        info = archive.getinfo(name)
    except KeyError as exc:
        raise ContentPackError(
            f"Gói quy tắc thiếu tệp {name}. "
            "Nguyên nhân: Tệp lưu trữ .mpcontent không chứa tệp thành phần bắt buộc. "
            "Cách xử lý: Đóng gói lại tệp .mpcontent bao gồm đầy đủ tệp kê khai và quy tắc."
        ) from exc
    if info.file_size > max_bytes:
        raise ContentPackError(
            f"Tệp trong gói quy tắc vượt quá dung lượng cho phép: {name}. "
            f"Nguyên nhân: Dung lượng tệp ({info.file_size} bytes) vượt quá giới hạn cho phép ({max_bytes} bytes). "
            "Cách xử lý: Giảm dung lượng tệp trước khi đóng gói."
        )
    data = archive.read(info)
    if len(data) != info.file_size:
        raise ContentPackError(
            f"Kích thước tệp trong gói quy tắc không khớp: {name}. "
            "Nguyên nhân: Dữ liệu tệp đọc ra không khớp kích thước ghi nhận trong tiêu đề tệp nén. "
            "Cách xử lý: Đóng gói lại tệp .mpcontent từ nguồn dữ liệu không bị hỏng."
        )
    return data


def inspect_content_pack(
    pack_path: str | os.PathLike[str],
    *,
    current_app_version: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = Path(pack_path)
    try:
        with zipfile.ZipFile(path) as archive:
            names = {info.filename for info in archive.infolist() if not info.is_dir()}
            manifest_bytes = _read_zip_member(archive, "manifest.json", max_bytes=512 * 1024)
            manifest = json.loads(manifest_bytes.decode("utf-8-sig"))
            validate_manifest(manifest, artifact_kind="content")
            if manifest.get("content_schema") != CONTENT_SCHEMA:
                raise ContentPackError(
                    f"Không hỗ trợ phiên bản cấu trúc gói quy tắc này ({manifest.get('content_schema')}). "
                    f"Nguyên nhân: Phiên bản content_schema trong manifest không khớp với hệ thống ({CONTENT_SCHEMA}). "
                    "Cách xử lý: Sử dụng gói quy tắc được tạo cho phiên bản ứng dụng hiện tại."
                )
            if not isinstance(manifest.get("fiscal_year"), int) or manifest["fiscal_year"] < 2027:
                raise ContentPackError(
                    f"Năm tài chính của gói quy tắc không hợp lệ ({manifest.get('fiscal_year')}). "
                    "Nguyên nhân: Trường fiscal_year trong manifest.json phải là số nguyên từ 2027 trở lên. "
                    "Cách xử lý: Kiểm tra và chỉnh sửa lại trường fiscal_year trong manifest.json."
                )
            if _version(current_app_version) < _version(manifest["min_app_version"]):
                raise ContentPackError(
                    f"Gói quy tắc yêu cầu phiên bản ứng dụng mới hơn "
                    f"(yêu cầu v{manifest.get('min_app_version')}, hiện tại v{current_app_version}). "
                    "Nguyên nhân: Gói quy tắc sử dụng định dạng hoặc tính năng chỉ có trên bản phát hành mới hơn. "
                    f"Cách xử lý: Nâng cấp ứng dụng lên phiên bản {manifest.get('min_app_version')} hoặc mới hơn."
                )
            expected = {"manifest.json", *(item["path"] for item in manifest["files"])}
            if names != expected:
                raise ContentPackError(
                    "Gói quy tắc có tệp bị thiếu hoặc không có trong kê khai. "
                    f"Nguyên nhân: Danh sách tệp thực tế ({sorted(names)}) không khớp với kê khai manifest ({sorted(expected)}). "
                    "Cách xử lý: Đồng bộ danh sách tệp trong manifest.json và tệp nén .mpcontent."
                )
            rules_bytes = _read_zip_member(archive, "rules.json", max_bytes=8 * 1024 * 1024)
            rules_payload = json.loads(rules_bytes.decode("utf-8-sig"))
            validate_rules(rules_payload)
    except ContentPackError:
        raise
    except ArtifactVerificationError as exc:
        msg = str(exc)
        if "Cách xử lý:" not in msg:
            msg += (
                " Nguyên nhân: Gói dữ liệu không vượt qua kiểm tra toàn vẹn hoặc cấu trúc manifest. "
                "Cách xử lý: Sử dụng gói quy tắc chính thức từ nguồn tin cậy."
            )
        raise ContentPackError(msg) from exc
    except (zipfile.BadZipFile, UnicodeError, json.JSONDecodeError) as exc:
        raise ContentPackError(
            "Gói quy tắc không hợp lệ hoặc đã bị hỏng. "
            "Nguyên nhân: Tệp .mpcontent không đúng định dạng zip hoặc chứa dữ liệu JSON lỗi. "
            "Cách xử lý: Xuất hoặc tải lại gói quy tắc .mpcontent từ nguồn phát hành tin cậy."
        ) from exc
    return manifest, rules_payload


def install_content_pack(
    pack_path: str | os.PathLike[str],
    content_root: str | os.PathLike[str],
    *,
    current_app_version: str,
    activate: bool = False,
) -> Path:
    manifest, _rules = inspect_content_pack(
        pack_path,
        current_app_version=current_app_version,
    )
    root = Path(content_root).resolve()
    installed = root / "installed"
    destination = installed / manifest["id"] / manifest["version"]
    if destination.exists():
        raise ContentPackError(
            f"Phiên bản gói quy tắc đã được cài đặt: {destination}. "
            "Nguyên nhân: Gói quy tắc với cùng mã ID và phiên bản đã tồn tại trong thư mục cài đặt. "
            "Cách xử lý: Tăng số phiên bản trong manifest.json nếu muốn phát hành bản cập nhật mới."
        )
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
        raise ContentPackError(
            f"Không tìm thấy gói quy tắc đã cài đặt: {pack_id} {version}. "
            "Nguyên nhân: Thư mục hoặc tệp manifest.json của gói quy tắc không tồn tại. "
            "Cách xử lý: Cài đặt lại gói quy tắc trước khi kích hoạt."
        )
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


def install_runtime_content_pack(
    pack_path: str | os.PathLike[str],
    runtime_root: str | os.PathLike[str],
    *,
    fiscal_year: int,
    release_metadata_path: str | os.PathLike[str] | None = None,
) -> Path:
    """Install and activate a hash-checked pack from the controlled source."""
    try:
        metadata_path = Path(release_metadata_path).resolve() if release_metadata_path else bundled_release_metadata_path()
        metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
        app_version = str(metadata.get("version", "")) if isinstance(metadata, dict) else ""
        _version(app_version)
        verified_manifest, _rules = inspect_content_pack(
            pack_path,
            current_app_version=app_version,
        )
        if verified_manifest.get("fiscal_year") != fiscal_year:
            raise ContentPackError(
                f"Gói quy tắc dành cho FY{verified_manifest.get('fiscal_year')}, không phải FY{fiscal_year}. "
                "Nguyên nhân: Năm tài chính trong manifest của gói quy tắc không khớp với năm tài chính đang chạy. "
                f"Cách xử lý: Chọn gói quy tắc tương ứng với năm tài chính FY{fiscal_year}."
            )
    except ContentPackError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        raise ContentPackError(
            "Không xác định được phiên bản ứng dụng cho gói quy tắc. "
            "Nguyên nhân: Tệp siêu dữ liệu phát hành (release metadata) bị thiếu hoặc không đọc được. "
            "Cách xử lý: Kiểm tra lại cài đặt ứng dụng hoặc tệp release.json đi kèm."
        ) from exc
    return install_content_pack(
        pack_path,
        Path(runtime_root).resolve() / "content-packs",
        current_app_version=app_version,
        activate=True,
    )


def load_runtime_content_rules(
    runtime_root: str | os.PathLike[str],
    *,
    fiscal_year: int,
    release_metadata_path: str | os.PathLike[str] | None = None,
) -> list[dict[str, Any]]:
    """Resolve and verify active content rules for one fiscal run."""
    content_root = Path(runtime_root).resolve() / "content-packs"
    active_path = content_root / "active.json"
    if not active_path.exists():
        return []
    try:
        state = json.loads(active_path.read_text(encoding="utf-8-sig"))
        pack_id = state.get("id") if isinstance(state, dict) else None
        pack_version = state.get("version") if isinstance(state, dict) else None
        if not isinstance(pack_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", pack_id):
            raise ContentPackError(
                "Mã gói quy tắc đang dùng không hợp lệ. "
                "Nguyên nhân: Trường 'id' trong active.json không đúng định dạng. "
                "Cách xử lý: Kích hoạt lại gói quy tắc từ giao diện chương trình."
            )
        if not isinstance(pack_version, str):
            raise ContentPackError(
                "Phiên bản gói quy tắc đang dùng không hợp lệ. "
                "Nguyên nhân: Trường 'version' trong active.json không phải dạng chuỗi. "
                "Cách xử lý: Kích hoạt lại gói quy tắc từ giao diện chương trình."
            )
        _version(pack_version)
        manifest_path = content_root / "installed" / pack_id / pack_version / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        metadata_path = Path(release_metadata_path).resolve() if release_metadata_path else bundled_release_metadata_path()
        metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
        app_version = str(metadata.get("version", "")) if isinstance(metadata, dict) else ""
        _version(app_version)
    except ContentPackError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContentPackError(
            "Không xác định được phiên bản ứng dụng cho gói quy tắc đang dùng. "
            "Nguyên nhân: Lỗi khi đọc tệp siêu dữ liệu active.json hoặc release metadata. "
            "Cách xử lý: Kiểm tra tính toàn vẹn của thư mục content-packs."
        ) from exc
    return load_active_content_rules(
        content_root,
        current_app_version=app_version,
        fiscal_year=fiscal_year,
    )


def load_active_content_rules(
    content_root: str | os.PathLike[str],
    *,
    current_app_version: str,
    fiscal_year: int,
) -> list[dict[str, Any]]:
    """Load active rules only after revalidating installed signed content."""
    root = Path(content_root).resolve()
    state_path = root / "active.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContentPackError(
            "Không đọc được trạng thái gói quy tắc đang dùng. "
            "Nguyên nhân: Tệp active.json không tồn tại hoặc bị hỏng định dạng JSON. "
            "Cách xử lý: Kích hoạt lại gói quy tắc."
        ) from exc
    required_state = {"schema", "id", "version", "manifest_sha256"}
    if not isinstance(state, dict) or set(state) != required_state or state.get("schema") != 1:
        raise ContentPackError(
            "Trạng thái gói quy tắc đang dùng không hợp lệ. "
            "Nguyên nhân: Cấu trúc tệp active.json bị thiếu trường bắt buộc hoặc sai schema. "
            "Cách xử lý: Kích hoạt lại gói quy tắc."
        )
    pack_id = state.get("id")
    version = state.get("version")
    if not isinstance(pack_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", pack_id):
        raise ContentPackError(
            "Mã gói quy tắc đang dùng không hợp lệ. "
            "Nguyên nhân: Mã ID gói quy tắc trong active.json chứa ký tự không hợp lệ. "
            "Cách xử lý: Kích hoạt lại gói quy tắc."
        )
    _version(str(version))
    pack_dir = root / "installed" / pack_id / str(version)
    manifest_path = pack_dir / "manifest.json"
    rules_path = pack_dir / "rules.json"
    try:
        if not manifest_path.is_file() or sha256_file(manifest_path) != state.get("manifest_sha256"):
            raise ContentPackError(
                "Tệp kê khai của gói quy tắc đang dùng bị thiếu hoặc đã thay đổi. "
                "Nguyên nhân: Mã băm SHA-256 của manifest.json không khớp với chữ ký trong active.json. "
                "Cách xử lý: Cài đặt và kích hoạt lại gói quy tắc từ nguồn phát hành chính thức."
            )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        validate_manifest(manifest, artifact_kind="content")
        if manifest.get("id") != pack_id or manifest.get("version") != version:
            raise ContentPackError(
                "Thông tin kích hoạt không khớp với tệp kê khai của gói đã cài. "
                "Nguyên nhân: ID hoặc Version trong active.json khác với thông tin trong manifest.json. "
                "Cách xử lý: Kích hoạt lại gói quy tắc."
            )
        if manifest.get("content_schema") != CONTENT_SCHEMA:
            raise ContentPackError(
                f"Không hỗ trợ phiên bản cấu trúc gói quy tắc này ({manifest.get('content_schema')}). "
                f"Nguyên nhân: Phiên bản content_schema trong manifest không khớp với hệ thống ({CONTENT_SCHEMA}). "
                "Cách xử lý: Sử dụng gói quy tắc tương thích với phiên bản phần mềm."
            )
        if manifest.get("fiscal_year") != fiscal_year:
            raise ContentPackError(
                f"Gói quy tắc đang dùng dành cho FY{manifest.get('fiscal_year')}, không phải FY{fiscal_year}. "
                "Nguyên nhân: Gói quy tắc đang kích hoạt được thiết lập cho năm tài chính khác. "
                f"Cách xử lý: Kích hoạt gói quy tắc dành cho FY{fiscal_year}."
            )
        if _version(current_app_version) < _version(manifest["min_app_version"]):
            raise ContentPackError(
                f"Gói quy tắc yêu cầu phiên bản ứng dụng mới hơn "
                f"(yêu cầu v{manifest.get('min_app_version')}, hiện tại v{current_app_version}). "
                "Nguyên nhân: Ứng dụng hiện tại có phiên bản thấp hơn yêu cầu tối thiểu của gói quy tắc. "
                f"Cách xử lý: Cập nhật phần mềm lên phiên bản {manifest.get('min_app_version')} hoặc mới hơn."
            )
        verify_manifest_files(manifest, pack_dir)
        if {item["path"] for item in manifest["files"]} != {"rules.json"}:
            raise ContentPackError(
                "Gói quy tắc đang dùng chứa tệp không được hỗ trợ. "
                "Nguyên nhân: Gói nội dung quy tắc chỉ được phép chứa tệp rules.json. "
                "Cách xử lý: Loại bỏ các tệp không thuộc quy cách khỏi gói quy tắc."
            )
        actual_files: set[str] = set()
        for installed_path in pack_dir.rglob("*"):
            if installed_path.is_symlink():
                raise ContentPackError(
                    "Gói quy tắc đang dùng chứa liên kết tượng trưng. "
                    "Nguyên nhân: Tệp liên kết tượng trưng (symlink) bị cấm vì lý do an toàn. "
                    "Cách xử lý: Đóng gói lại tệp không sử dụng symlink."
                )
            if installed_path.is_file():
                actual_files.add(installed_path.relative_to(pack_dir).as_posix())
        expected_files = {"manifest.json", "rules.json"}
        if actual_files != expected_files:
            raise ContentPackError(
                "Gói quy tắc đang dùng có tệp bị thiếu hoặc không có trong kê khai. "
                f"Nguyên nhân: Danh sách tệp thực tế ({sorted(actual_files)}) không khớp với danh sách ({sorted(expected_files)}). "
                "Cách xử lý: Cài đặt lại gói quy tắc."
            )
        rules_payload = json.loads(rules_path.read_text(encoding="utf-8-sig"))
        return validate_rules(rules_payload)
    except ContentPackError:
        raise
    except ArtifactVerificationError as exc:
        msg = str(exc)
        if "Cách xử lý:" not in msg:
            msg += (
                " Nguyên nhân: Gói dữ liệu không vượt qua kiểm tra toàn vẹn hoặc cấu trúc manifest. "
                "Cách xử lý: Sử dụng gói quy tắc chính thức từ nguồn tin cậy."
            )
        raise ContentPackError(msg) from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContentPackError(
            "Gói quy tắc đã cài đặt không hợp lệ hoặc đã bị hỏng. "
            "Nguyên nhân: Lỗi khi đọc hoặc giải mã tệp quy tắc trong thư mục đã cài đặt. "
            "Cách xử lý: Cài đặt lại gói quy tắc."
        ) from exc
