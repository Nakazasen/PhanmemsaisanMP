"""Resolve MP2027 source workbooks from a configurable ordered manifest."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

import openpyxl


MANIFEST_FILENAME = "source_file_order.csv"
MANIFEST_XLSX_FILENAME = "source_file_order.xlsx"
MANIFEST_COLUMNS = (
    "order", "category", "filename", "enabled", "description",
    "period_start", "period_end",
)
SUPPORTED_SOURCE_SUFFIXES = {".xls", ".xlsx", ".xlsm"}
SYSTEM_FILENAMES = {"form.xlsx", MANIFEST_FILENAME.lower(), MANIFEST_XLSX_FILENAME.lower()}
SYSTEM_PREFIXES = ("~$", "mp_cc_")
SYSTEM_EXACT_OUTPUTS = {"mp2027_audit_report.md", "mp2027_missing_inputs.csv"}


DEFAULT_DESCRIPTIONS = {
    "facility": "Nguồn cơ sở vật chất",
    "fixed_assets": "Nguồn tài sản cố định",
    "it_simulation": "Nguồn mô phỏng hệ thống",
    "ga": "Nguồn Tổng vụ",
    "birthday": "Nguồn sinh nhật",
    "allocation_rules": "Nguồn quy tắc phân bổ",
    "nnn_paperwork": "Nguồn giấy tờ NNN",
}

CATEGORY_DISPLAY_NAMES = {
    "facility": "Cơ sở vật chất",
    "fixed_assets": "Tài sản cố định",
    "it_simulation": "Mô phỏng hệ thống",
    "ga": "Tổng vụ",
    "birthday": "Sinh nhật",
    "allocation_rules": "Quy tắc phân bổ",
    "nnn_paperwork": "Giấy tờ NNN",
}

CATEGORY_ORDER = {
    "facility": 10,
    "fixed_assets": 20,
    "it_simulation": 30,
    "ga": 40,
    "birthday": 50,
    "allocation_rules": 60,
    "nnn_paperwork": 70,
}


def _source_dir_path(source_dir: str | None) -> Path | None:
    if not source_dir:
        return None
    path = Path(source_dir)
    return path if path.is_dir() else None


def _normalize_row(row: dict[str, object], base_dir: Path) -> dict[str, str] | None:
    enabled = str(row.get("enabled", "1")).strip().lower()
    filename = str(row.get("filename", "")).strip()
    category = str(row.get("category", "")).strip()
    if not filename or not category:
        return None
    normalized = {key: str(row.get(key, "")).strip() for key in MANIFEST_COLUMNS}
    normalized["enabled"] = "0" if enabled in {"0", "false", "no", "n"} else "1"
    normalized["_path"] = str(base_dir / filename)
    return normalized


def _sort_entries(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    def order_key(row: dict[str, str]) -> tuple[int, str]:
        try:
            order = int(str(row.get("order", "")).strip())
        except ValueError:
            order = 9999
        return order, str(row.get("filename", "")).lower()

    return sorted(entries, key=order_key)


def _read_csv_manifest(path: Path, base_dir: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            normalized = _normalize_row(row, base_dir)
            if normalized:
                entries.append(normalized)
    return _sort_entries(entries)


def _read_xlsx_manifest(path: Path, base_dir: Path) -> list[dict[str, str]]:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        worksheet = workbook.active
        headers = [
            str(worksheet.cell(row=1, column=col).value or "").strip()
            for col in range(1, worksheet.max_column + 1)
        ]
        header_index = {name: idx + 1 for idx, name in enumerate(headers)}
        if not all(column in header_index for column in ("order", "category", "filename")):
            return []

        entries: list[dict[str, str]] = []
        for row_index in range(2, worksheet.max_row + 1):
            raw = {
                column: worksheet.cell(row=row_index, column=header_index.get(column, 0)).value
                for column in MANIFEST_COLUMNS
                if header_index.get(column)
            }
            normalized = _normalize_row(raw, base_dir)
            if normalized:
                entries.append(normalized)
        return _sort_entries(entries)
    finally:
        workbook.close()


def _existing_enabled_entries(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        entry
        for entry in entries
        if str(entry.get("enabled", "1")).strip() != "0" and Path(str(entry.get("_path", ""))).is_file()
    ]


def _is_system_or_generated_file(path: Path) -> bool:
    lower = path.name.lower()
    if lower in SYSTEM_FILENAMES or lower in SYSTEM_EXACT_OUTPUTS:
        return True
    if any(lower.startswith(prefix) for prefix in SYSTEM_PREFIXES):
        return True
    if lower.endswith(".tmp_export.xlsx") or lower.endswith(".tmp.xlsx"):
        return True
    return False


def _source_candidates(base_dir: Path) -> list[Path]:
    return [
        path
        for path in base_dir.iterdir()
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_SOURCE_SUFFIXES
        and not _is_system_or_generated_file(path)
    ]


def _classify_source_file(path: Path) -> str | None:
    name = path.name
    lower = name.lower()
    if "fixed_assets_information" in lower or "固定資産情報" in name:
        return "fixed_assets"
    if "simulation" in lower and "fy2027" in lower:
        return "it_simulation"
    if "mpfy2027" in lower and "施設" in name:
        return "facility"
    if "fy2027 mp" in lower and "振替" in name:
        return "ga"
    if "sinh" in lower and "fy2027" in lower:
        return "birthday"
    if "配賦額一覧" in name or ("fy2027" in lower and "2025.12.29" in lower):
        return "allocation_rules"
    if "nnn" in lower or "giấy tờ" in lower or "giay to" in lower:
        return "nnn_paperwork"
    return None


def _it_order(path: Path) -> int:
    lower = path.name.lower()
    if "apr" in lower or "june" in lower:
        return 0
    if "july" in lower or "dec" in lower:
        return 1
    if "jan" in lower or "march" in lower:
        return 2
    return 9


def _detected_sort_key(path: Path) -> tuple[int, int, str]:
    category = _classify_source_file(path) or ""
    return CATEGORY_ORDER.get(category, 999), _it_order(path), path.name.lower()


def detect_source_files(source_dir: str | None) -> list[dict[str, str]]:
    """Auto-detect supported business source files in the selected folder."""
    base_dir = _source_dir_path(source_dir)
    if base_dir is None:
        return []

    entries: list[dict[str, str]] = []
    for index, path in enumerate(sorted(_source_candidates(base_dir), key=_detected_sort_key), start=1):
        category = _classify_source_file(path)
        if not category:
            continue
        entries.append(
            {
                "order": str(index),
                "category": category,
                "filename": path.name,
                "enabled": "1",
                "description": DEFAULT_DESCRIPTIONS.get(category, ""),
                "_path": str(path),
            }
        )
    return entries


def _read_saved_manifest(source_dir: str | None, include_csv: bool = True) -> list[dict[str, str]]:
    base_dir = _source_dir_path(source_dir)
    if base_dir is None:
        return []
    xlsx_path = base_dir / MANIFEST_XLSX_FILENAME
    if xlsx_path.is_file():
        return _read_xlsx_manifest(xlsx_path, base_dir)
    csv_path = base_dir / MANIFEST_FILENAME
    if include_csv and csv_path.is_file():
        return _read_csv_manifest(csv_path, base_dir)
    return []


def merge_manifest_with_detected(
    source_dir: str | None,
    saved_entries: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Merge user overrides with current folder auto-discovery."""
    base_dir = _source_dir_path(source_dir)
    if base_dir is None:
        return []

    saved = saved_entries if saved_entries is not None else _read_saved_manifest(source_dir)
    detected = detect_source_files(source_dir)
    detected_by_name = {entry["filename"].lower(): entry for entry in detected}

    merged: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in _sort_entries(saved):
        filename = str(row.get("filename", "")).strip()
        key = filename.lower()
        if not filename or key in seen or key not in detected_by_name:
            continue
        merged_row = dict(detected_by_name[key])
        merged_row.update(
            {
                "order": row.get("order", merged_row["order"]),
                "category": row.get("category", merged_row["category"]),
                "enabled": row.get("enabled", "1"),
                "description": row.get("description", merged_row.get("description", "")),
                "period_start": row.get("period_start", ""),
                "period_end": row.get("period_end", ""),
                "_path": str(base_dir / filename),
            }
        )
        merged.append(merged_row)
        seen.add(key)

    for row in detected:
        key = row["filename"].lower()
        if key not in seen:
            merged.append(row)
            seen.add(key)

    for index, row in enumerate(_sort_entries(merged), start=1):
        row["order"] = str(index)
    return merged


def write_source_manifest_xlsx(source_dir: str | None, entries: list[dict[str, str]]) -> str:
    base_dir = _source_dir_path(source_dir)
    if base_dir is None:
        raise FileNotFoundError(f"Không tìm thấy thư mục nguồn: {source_dir}")

    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "source_file_order"
    worksheet.append(list(MANIFEST_COLUMNS))
    for entry in _sort_entries(entries):
        worksheet.append([entry.get(column, "") for column in MANIFEST_COLUMNS])
    worksheet.freeze_panes = "A2"
    for column, width in {
        "A": 10, "B": 18, "C": 90, "D": 10, "E": 44, "F": 14, "G": 14,
    }.items():
        worksheet.column_dimensions[column].width = width
    path = base_dir / MANIFEST_XLSX_FILENAME
    workbook.save(path)
    _cached_manifest_snapshot.cache_clear()
    return str(path)


def ensure_source_manifest(source_dir: str | None, *, refresh: bool = True) -> str:
    base_dir = _source_dir_path(source_dir)
    if base_dir is None:
        raise FileNotFoundError(f"Không tìm thấy thư mục nguồn: {source_dir}")

    entries = merge_manifest_with_detected(source_dir) if refresh else _read_saved_manifest(source_dir)
    if not entries:
        entries = detect_source_files(source_dir)
    write_source_manifest_xlsx(source_dir, entries)
    return str(base_dir / MANIFEST_XLSX_FILENAME)


@lru_cache(maxsize=16)
def _cached_manifest_snapshot(source_dir: str) -> tuple[tuple[tuple[str, str], ...], ...]:
    # A saved manifest is authoritative: changing a configured filename or
    # directory must not depend on filename classification heuristics.
    entries = _read_saved_manifest(source_dir)
    if not entries:
        entries = detect_source_files(source_dir)
    return tuple(tuple(sorted((str(key), str(value)) for key, value in entry.items())) for entry in entries)


def read_source_manifest(source_dir: str | None, include_missing: bool = False) -> list[dict[str, str]]:
    """Read source file entries without rewriting the manifest on disk."""
    base_dir = _source_dir_path(source_dir)
    if base_dir is None:
        return []

    snapshot = _cached_manifest_snapshot(str(base_dir.resolve()))
    entries = [dict(items) for items in snapshot]
    if include_missing:
        return entries
    return _existing_enabled_entries(entries)


def validate_cost_source_manifest(source_dir: str | None) -> list[dict[str, str]]:
    """Validate the explicit cost-source manifest before a production run.

    Auto-detection remains available to the manifest editor, but calculation must
    use an explicit manifest so a staffing-only folder cannot silently be treated
    as the cost-source folder.
    """
    base_dir = _source_dir_path(source_dir)
    if base_dir is None:
        raise FileNotFoundError(f"Không tìm thấy thư mục nguồn chi phí: {source_dir}")

    manifest_paths = (
        base_dir / MANIFEST_XLSX_FILENAME,
        base_dir / MANIFEST_FILENAME,
    )
    if not any(path.is_file() for path in manifest_paths):
        raise ValueError(
            "Thư mục nguồn chi phí không có source_file_order.xlsx hoặc "
            f"source_file_order.csv: {base_dir}. Hãy chọn thư mục nguồn chi phí "
            "đã cấu hình manifest; không chọn thư mục chỉ chứa dữ liệu nhân sự."
        )

    entries = _read_saved_manifest(str(base_dir))
    if not entries:
        raise ValueError(f"Manifest nguồn chi phí không có dòng cấu hình hợp lệ: {base_dir}.")

    enabled = [
        entry
        for entry in entries
        if str(entry.get("enabled", "1")).strip() != "0"
    ]
    if not enabled:
        raise ValueError(f"Manifest nguồn chi phí không có nguồn nào được bật: {base_dir}.")

    missing = [
        str(entry.get("filename", "")).strip()
        for entry in enabled
        if not Path(str(entry.get("_path", ""))).is_file()
    ]
    if missing:
        preview = ", ".join(missing[:5])
        suffix = f" (và {len(missing) - 5} file khác)" if len(missing) > 5 else ""
        raise FileNotFoundError(
            f"Manifest nguồn chi phí tham chiếu file không tồn tại: {preview}{suffix}."
        )

    return enabled


def resolve_manifest_file(source_dir: str | None, category: str) -> str | None:
    """Return the first existing enabled file for a category."""
    for entry in read_source_manifest(source_dir):
        if entry.get("category") != category:
            continue
        path = Path(str(entry.get("_path", "")))
        if path.is_file():
            return str(path)
    return None


def resolve_manifest_files(source_dir: str | None, category: str) -> list[str]:
    """Return existing enabled files for a category in configured order."""
    paths: list[str] = []
    for entry in read_source_manifest(source_dir):
        if entry.get("category") != category:
            continue
        path = Path(str(entry.get("_path", "")))
        if path.is_file():
            paths.append(str(path))
    return paths


def describe_manifest(source_dir: str | None) -> list[str]:
    lines: list[str] = []
    for entry in read_source_manifest(source_dir, include_missing=True):
        path = Path(str(entry.get("_path", "")))
        status = "ĐỦ" if path.is_file() else "THIẾU"
        enabled = "BẬT" if str(entry.get("enabled", "1")).strip() != "0" else "TẮT"
        category_key = str(entry.get("category", "")).strip()
        category = CATEGORY_DISPLAY_NAMES.get(category_key, category_key)
        lines.append(
            "{order}. {category}: {filename} [{status}; {enabled}]".format(
                order=str(entry.get("order", "")).strip() or "?",
                category=category,
                filename=str(entry.get("filename", "")).strip(),
                status=status,
                enabled=enabled,
            )
        )
    return lines
