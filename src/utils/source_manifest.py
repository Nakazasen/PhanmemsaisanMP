"""Resolve MP2027 source workbooks from a configurable ordered manifest."""

from __future__ import annotations

import csv
from pathlib import Path

import openpyxl


MANIFEST_FILENAME = "source_file_order.csv"
MANIFEST_XLSX_FILENAME = "source_file_order.xlsx"
MANIFEST_COLUMNS = ("order", "category", "filename", "enabled", "description")


DEFAULT_DESCRIPTIONS = {
    "facility": "Facility depreciation, interest, electric and water source",
    "fixed_assets": "Fixed assets source",
    "it_simulation": "IT simulation source",
    "ga": "General affairs source",
    "birthday": "Birthday source",
    "allocation_rules": "Allocation rules source",
    "nnn_paperwork": "NNN paperwork source",
}


def _source_dir_path(source_dir: str | None) -> Path | None:
    if not source_dir:
        return None
    path = Path(source_dir)
    return path if path.is_dir() else None


def _normalize_row(row: dict[str, object], base_dir: Path) -> dict[str, str] | None:
    enabled = str(row.get("enabled", "1")).strip().lower()
    if enabled in {"0", "false", "no", "n"}:
        return None
    filename = str(row.get("filename", "")).strip()
    category = str(row.get("category", "")).strip()
    if not filename or not category:
        return None
    normalized = {key: str(row.get(key, "")).strip() for key in MANIFEST_COLUMNS}
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


def _existing_entries(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    return [entry for entry in entries if Path(str(entry.get("_path", ""))).is_file()]


def _detect_source_files(base_dir: Path) -> list[dict[str, str]]:
    paths = [path for path in base_dir.iterdir() if path.is_file() and not path.name.startswith("~$")]

    def first(predicate) -> Path | None:
        return next((path for path in paths if predicate(path.name)), None)

    def all_matching(predicate) -> list[Path]:
        return sorted((path for path in paths if predicate(path.name)), key=lambda item: item.name.lower())

    rows: list[tuple[str, Path]] = []
    facility = first(lambda name: name.endswith(".xlsx") and "MPFY2027" in name and name != "FORM.xlsx")
    fixed_assets = first(lambda name: name.endswith(".xlsx") and "Fixed_Assets_Information" in name)
    ga = first(lambda name: name.endswith(".xlsx") and "FY2027 MP" in name and "振替" in name)
    birthday = first(lambda name: name.endswith(".xlsx") and "Sinh" in name and "FY2027" in name)
    allocation = first(lambda name: name.endswith(".xlsx") and "FY2027" in name and "2025.12.29" in name)
    nnn = first(lambda name: name.endswith(".xlsx") and "NNN" in name)

    for category, path in (
        ("facility", facility),
        ("fixed_assets", fixed_assets),
        ("ga", ga),
        ("birthday", birthday),
        ("allocation_rules", allocation),
        ("nnn_paperwork", nnn),
    ):
        if path:
            rows.append((category, path))

    it_files = all_matching(lambda name: name.endswith(".xls") and "Simulation" in name and "FY2027" in name)
    if it_files:
        def it_order(path: Path) -> int:
            lower = path.name.lower()
            if "apr" in lower or "june" in lower:
                return 0
            if "july" in lower or "dec" in lower:
                return 1
            if "jan" in lower or "march" in lower:
                return 2
            return 9

        insert_after = 2 if len(rows) >= 2 else len(rows)
        for offset, path in enumerate(sorted(it_files, key=it_order)):
            rows.insert(insert_after + offset, ("it_simulation", path))

    entries: list[dict[str, str]] = []
    for index, (category, path) in enumerate(rows, start=1):
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


def write_source_manifest_xlsx(source_dir: str | None, entries: list[dict[str, str]]) -> str:
    base_dir = _source_dir_path(source_dir)
    if base_dir is None:
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "source_file_order"
    worksheet.append(list(MANIFEST_COLUMNS))
    for entry in _sort_entries(entries):
        worksheet.append([entry.get(column, "") for column in MANIFEST_COLUMNS])
    worksheet.freeze_panes = "A2"
    for column, width in {"A": 10, "B": 18, "C": 90, "D": 10, "E": 44}.items():
        worksheet.column_dimensions[column].width = width
    path = base_dir / MANIFEST_XLSX_FILENAME
    workbook.save(path)
    return str(path)


def ensure_source_manifest(source_dir: str | None) -> str:
    base_dir = _source_dir_path(source_dir)
    if base_dir is None:
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    xlsx_path = base_dir / MANIFEST_XLSX_FILENAME
    if xlsx_path.is_file():
        return str(xlsx_path)

    entries = read_source_manifest(source_dir, include_missing=True)
    if not _existing_entries(entries):
        entries = _detect_source_files(base_dir)
    write_source_manifest_xlsx(source_dir, entries)
    return str(xlsx_path)


def read_source_manifest(source_dir: str | None, include_missing: bool = False) -> list[dict[str, str]]:
    """Read enabled source file entries sorted by their explicit order."""
    base_dir = _source_dir_path(source_dir)
    if base_dir is None:
        return []

    xlsx_path = base_dir / MANIFEST_XLSX_FILENAME
    if xlsx_path.is_file():
        entries = _read_xlsx_manifest(xlsx_path, base_dir)
        return entries if include_missing else _existing_entries(entries)

    manifest_path = base_dir / MANIFEST_FILENAME
    if not manifest_path.is_file():
        return []

    entries = _read_csv_manifest(manifest_path, base_dir)
    return entries if include_missing else _existing_entries(entries)


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
        status = "OK" if path.is_file() else "MISSING"
        lines.append(
            "{order}. {category}: {filename} [{status}]".format(
                order=str(entry.get("order", "")).strip() or "?",
                category=str(entry.get("category", "")).strip(),
                filename=str(entry.get("filename", "")).strip(),
                status=status,
            )
        )
    return lines
