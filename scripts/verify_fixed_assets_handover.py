#!/usr/bin/env python3
"""Xác minh và tùy chọn khởi tạo bộ dữ liệu kiểm toán tài sản cố định có thể bàn giao."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.cli import VietnameseArgumentParser


REQUIRED_HASHES = {
    "raw/Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx": (
        "426207927e42b19c113f26f9d63ec564a434b5758a43ac71ac52803badbae661"
    ),
    "docs/MP2026/固定資産情報_Fixed_Assets_Information_2024.12 - December.xlsx": (
        "cb5e01bc631002408b6756449b114bfd30bfea932648e2a28e7f500426e7b028"
    ),
    "docs/MP2027/固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx": (
        "5c82bca709499f69248cf5994a209514e8b5a9b9888ea684fadbaa12a54dbaa8"
    ),
    "reference_outputs/secondary/FY2027.zip": (
        "fb0f2f637395e8c45373041013685829889ddda30824457eee546c165024d12b"
    ),
}
FY2026_DIR = ROOT / "reference_outputs" / "secondary" / "FY2026"
FY2027_ZIP = ROOT / "reference_outputs" / "secondary" / "FY2027.zip"
FY2027_DIR = ROOT / "reference_outputs" / "secondary" / "FY2027"
EXPECTED_FY2026_XLSX = 64
EXPECTED_FY2027_XLSX = 82
EXPECTED_ZIP_ROOT = "FY2027"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_zip_members(archive: ZipFile) -> list[str]:
    files: list[str] = []
    for name in archive.namelist():
        member = PurePosixPath(name)
        if member.is_absolute() or ".." in member.parts:
            raise ValueError(f"Thành phần ZIP không an toàn: {name}")
        if not name.endswith("/"):
            files.append(name)
    return files


def verify(extract_reference: bool) -> int:
    errors: list[str] = []

    for relative, expected in REQUIRED_HASHES.items():
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"Thiếu tệp bắt buộc: {relative}")
            continue
        actual = sha256(path)
        if actual != expected:
            errors.append(
                f"SHA-256 không khớp: {relative}\n"
                f"  giá trị cần có: {expected}\n"
                f"  giá trị thực tế: {actual}"
            )
        else:
            print(f"HASH_OK Đã xác minh: {relative}")

    fy2026_count = len(list(FY2026_DIR.glob("*.xlsx"))) if FY2026_DIR.is_dir() else 0
    if fy2026_count != EXPECTED_FY2026_XLSX:
        errors.append(
            f"Số tệp tham khảo FY2026 không khớp: cần {EXPECTED_FY2026_XLSX}, "
            f"tìm thấy {fy2026_count}"
        )
    else:
        print(f"FY2026_OK Đã xác minh số tệp Excel: {fy2026_count}")

    zip_ready = FY2027_ZIP.is_file() and not any(
        error.startswith("Thiếu tệp bắt buộc: reference_outputs/secondary/FY2027.zip")
        or error.startswith("SHA-256 không khớp: reference_outputs/secondary/FY2027.zip")
        for error in errors
    )
    if zip_ready:
        try:
            with ZipFile(FY2027_ZIP) as archive:
                corrupt = archive.testzip()
                if corrupt is not None:
                    errors.append(f"Tệp ZIP FY2027 có thành phần bị hỏng: {corrupt}")
                members = safe_zip_members(archive)
                xlsx_members = [
                    name for name in members if name.lower().endswith(".xlsx")
                ]
                roots = {PurePosixPath(name).parts[0] for name in members}
                if len(xlsx_members) != EXPECTED_FY2027_XLSX:
                    errors.append(
                        "Số tệp Excel trong ZIP FY2027 không khớp: "
                        f"cần {EXPECTED_FY2027_XLSX}, tìm thấy {len(xlsx_members)}"
                    )
                if roots != {EXPECTED_ZIP_ROOT}:
                    errors.append(
                        f"Thư mục gốc trong ZIP FY2027 không khớp: cần {EXPECTED_ZIP_ROOT}, "
                        f"tìm thấy {sorted(roots)}"
                    )
                if corrupt is None and len(xlsx_members) == EXPECTED_FY2027_XLSX and roots == {EXPECTED_ZIP_ROOT}:
                    print(
                        f"FY2027_ZIP_OK Đã xác minh {len(xlsx_members)} tệp Excel; "
                        f"thư mục gốc={EXPECTED_ZIP_ROOT}"
                    )
                if extract_reference and not errors:
                    archive.extractall(FY2027_ZIP.parent)
        except (BadZipFile, ValueError):
            errors.append("Tệp ZIP FY2027 không hợp lệ hoặc chứa thành phần không an toàn.")

    if extract_reference and not errors:
        extracted_count = (
            len(list(FY2027_DIR.rglob("*.xlsx"))) if FY2027_DIR.is_dir() else 0
        )
        if extracted_count != EXPECTED_FY2027_XLSX:
            errors.append(
                "Số tệp Excel FY2027 sau giải nén không khớp: "
                f"cần {EXPECTED_FY2027_XLSX}, tìm thấy {extracted_count}"
            )
        else:
            print(f"FY2027_EXTRACT_OK Đã giải nén {extracted_count} tệp Excel tại {FY2027_DIR}")

    if errors:
        print("HANDOVER_CORPUS_INVALID Bộ dữ liệu bàn giao không hợp lệ", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("HANDOVER_CORPUS_OK Bộ dữ liệu bàn giao hợp lệ")
    return 0


def main() -> int:
    parser = VietnameseArgumentParser(
        description="Xác minh bộ dữ liệu bàn giao tài sản cố định có thể sử dụng độc lập."
    )
    parser.add_argument(
        "--extract-reference",
        action="store_true",
        help="Giải nén FY2027.zip sau khi toàn bộ bước kiểm tra dữ liệu đạt yêu cầu",
    )
    args = parser.parse_args()
    return verify(args.extract_reference)


if __name__ == "__main__":
    raise SystemExit(main())
