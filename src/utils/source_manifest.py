"""Resolve MP2027 source workbooks from a configurable ordered manifest."""

from __future__ import annotations

import csv
from pathlib import Path


MANIFEST_FILENAME = "source_file_order.csv"


def _source_dir_path(source_dir: str | None) -> Path | None:
    if not source_dir:
        return None
    path = Path(source_dir)
    return path if path.is_dir() else None


def read_source_manifest(source_dir: str | None) -> list[dict[str, str]]:
    """Read enabled source file entries sorted by their explicit order."""
    base_dir = _source_dir_path(source_dir)
    if base_dir is None:
        return []

    manifest_path = base_dir / MANIFEST_FILENAME
    if not manifest_path.is_file():
        return []

    entries: list[dict[str, str]] = []
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            enabled = str(row.get("enabled", "1")).strip().lower()
            if enabled in {"0", "false", "no", "n"}:
                continue
            filename = str(row.get("filename", "")).strip()
            category = str(row.get("category", "")).strip()
            if not filename or not category:
                continue
            row["_path"] = str(base_dir / filename)
            entries.append(row)

    def order_key(row: dict[str, str]) -> tuple[int, str]:
        try:
            order = int(str(row.get("order", "")).strip())
        except ValueError:
            order = 9999
        return order, str(row.get("filename", "")).lower()

    entries.sort(key=order_key)
    return entries


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
    for entry in read_source_manifest(source_dir):
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
