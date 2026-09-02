"""Catalog ↔ review document drift checker for MP2027 business chat knowledge.

Pure read-only utility: compares the structured catalog against the admin review
Markdown files (vi.md, en.md, ja.md) and source_registry.json, and reports any drift.

Used by tests and admin tooling. Never auto-overwrites files at runtime.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DriftIssue:
    """A single drift discrepancy between catalog and review doc."""

    language: str
    entry_id: str
    kind: str  # "missing_in_doc", "extra_in_doc", "title_mismatch", "source_mismatch", "invalid_source_id"
    detail: str


def _extract_doc_ids(doc_path: Path) -> set[str]:
    """Extract entry IDs mentioned in a review Markdown document."""
    if not doc_path.is_file():
        return set()
    text = doc_path.read_text(encoding="utf-8")
    return set(re.findall(r"\b(bck_\w+)\b", text))


def _extract_doc_titles(doc_path: Path) -> dict[str, str]:
    """Extract entry ID → title mappings from a review doc (## bck_xxx: title)."""
    if not doc_path.is_file():
        return {}
    titles: dict[str, str] = {}
    text = doc_path.read_text(encoding="utf-8")
    for match in re.finditer(r"^##\s+(bck_\w+)\s*[:\—–-]\s*(.+)$", text, re.MULTILINE):
        titles[match.group(1)] = match.group(2).strip()
    return titles


def _extract_doc_sources(doc_path: Path) -> dict[str, str]:
    """Extract entry ID → Source line mappings from a review doc."""
    if not doc_path.is_file():
        return {}
    sources: dict[str, str] = {}
    text = doc_path.read_text(encoding="utf-8")
    sections = re.split(r"^##\s+(bck_\w+)", text, flags=re.MULTILINE)
    for i in range(1, len(sections), 2):
        entry_id = sections[i]
        body = sections[i + 1] if i + 1 < len(sections) else ""
        match = re.search(r"^\*\*Source\*\*:\s*(.+)$", body, re.MULTILINE)
        if match:
            sources[entry_id] = match.group(1).strip()
    return sources


def check_catalog_review_drift(
    catalog_path: Path | str,
    review_dir: Path | str,
    source_registry_path: Path | str | None = None,
) -> list[DriftIssue]:
    """Compare catalog entries against review docs and source registry, returning drift issues.

    Args:
        catalog_path: Path to knowledge_catalog.json.
        review_dir: Directory containing vi.md, en.md, ja.md.
        source_registry_path: Optional path to source_registry.json (defaults to review_dir/source_registry.json).

    Returns:
        List of DriftIssue objects. Empty list means no drift.
    """
    catalog_path = Path(catalog_path)
    review_dir = Path(review_dir)
    registry_path = Path(source_registry_path) if source_registry_path else review_dir / "source_registry.json"
    issues: list[DriftIssue] = []

    if not catalog_path.is_file():
        issues.append(DriftIssue(
            language="all", entry_id="", kind="missing_catalog",
            detail=f"Catalog file not found: {catalog_path.name}",
        ))
        return issues

    if not registry_path.is_file():
        issues.append(DriftIssue(
            language="all", entry_id="", kind="missing_source_registry",
            detail=f"Source registry file not found: {registry_path.name}",
        ))
        return issues

    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
        entries = data.get("entries", [])
    except (json.JSONDecodeError, OSError) as exc:
        issues.append(DriftIssue(
            language="all", entry_id="", kind="catalog_error",
            detail=f"Cannot parse catalog: {exc}",
        ))
        return issues

    try:
        reg_data = json.loads(registry_path.read_text(encoding="utf-8"))
        valid_sources = reg_data.get("sources", {})
    except (json.JSONDecodeError, OSError) as exc:
        issues.append(DriftIssue(
            language="all", entry_id="", kind="source_registry_error",
            detail=f"Cannot parse source registry: {exc}",
        ))
        return issues

    # Only check active entries
    active_ids: set[str] = set()
    catalog_titles: dict[str, dict[str, str]] = {}  # {entry_id: {lang: title}}
    catalog_sources: dict[str, dict[str, str]] = {}  # {entry_id: {lang: expected_source_label}}

    for entry in entries:
        entry_id = entry.get("id", "")
        status = entry.get("status", "active")
        if status != "active" or not entry_id:
            continue
        active_ids.add(entry_id)

        source_ref_ids = entry.get("source_ref_ids", entry.get("source_refs", []))
        if not source_ref_ids or not isinstance(source_ref_ids, list):
            issues.append(DriftIssue(
                language="all", entry_id=entry_id, kind="missing_source_ref_ids",
                detail=f"Entry '{entry_id}' missing valid source_ref_ids list in catalog",
            ))
        else:
            for s_id in source_ref_ids:
                if s_id not in valid_sources:
                    issues.append(DriftIssue(
                        language="all", entry_id=entry_id, kind="invalid_source_id",
                        detail=f"Entry '{entry_id}' references unknown source ID '{s_id}' not in source_registry.json",
                    ))

        catalog_titles[entry_id] = {}
        catalog_sources[entry_id] = {}
        for lang in ("vi", "en", "ja"):
            lang_data = entry.get(lang, {})
            if isinstance(lang_data, dict):
                catalog_titles[entry_id][lang] = lang_data.get("title", "")

            expected_labels: list[str] = []
            for s_id in source_ref_ids:
                src_entry = valid_sources.get(s_id, {})
                label = src_entry.get(lang, {}).get("label", "")
                if label:
                    expected_labels.append(label)
            catalog_sources[entry_id][lang] = ", ".join(expected_labels)

    # Check each language review doc
    for lang in ("vi", "en", "ja"):
        doc_path = review_dir / f"{lang}.md"
        if not doc_path.is_file():
            issues.append(DriftIssue(
                language=lang, entry_id="", kind="missing_doc",
                detail=f"Review doc not found: {lang}.md",
            ))
            continue

        doc_ids = _extract_doc_ids(doc_path)
        doc_titles = _extract_doc_titles(doc_path)
        doc_sources = _extract_doc_sources(doc_path)

        # Entries in catalog but not in review doc
        for entry_id in sorted(active_ids - doc_ids):
            issues.append(DriftIssue(
                language=lang, entry_id=entry_id, kind="missing_in_doc",
                detail=f"Entry '{entry_id}' is active in catalog but not mentioned in {lang}.md",
            ))

        # Entries in review doc but not active in catalog
        for entry_id in sorted(doc_ids - active_ids):
            issues.append(DriftIssue(
                language=lang, entry_id=entry_id, kind="extra_in_doc",
                detail=f"Entry '{entry_id}' found in {lang}.md but is not active in catalog",
            ))

        # Title mismatches
        for entry_id, doc_title in doc_titles.items():
            if entry_id in catalog_titles:
                catalog_title = catalog_titles[entry_id].get(lang, "")
                if catalog_title and doc_title and catalog_title != doc_title:
                    issues.append(DriftIssue(
                        language=lang, entry_id=entry_id, kind="title_mismatch",
                        detail=f"Title mismatch for '{entry_id}' in {lang}.md: "
                               f"catalog='{catalog_title}', doc='{doc_title}'",
                    ))

        # Source mismatches
        for entry_id in active_ids:
            expected_src = catalog_sources.get(entry_id, {}).get(lang, "")
            doc_src = doc_sources.get(entry_id, "")
            if expected_src and doc_src and expected_src != doc_src:
                issues.append(DriftIssue(
                    language=lang, entry_id=entry_id, kind="source_mismatch",
                    detail=f"Source label mismatch for '{entry_id}' in {lang}.md: "
                           f"registry='{expected_src}', doc='{doc_src}'",
                ))

    return issues


def generate_review_doc(
    catalog_path: Path | str,
    language: str,
    source_registry_path: Path | str | None = None,
) -> str:
    """Generate a review Markdown document for one language from the catalog and source registry.

    This can be used to regenerate vi.md/en.md/ja.md from the catalog.
    Does NOT write to disk — caller decides whether to save.
    """
    catalog_path = Path(catalog_path)
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    schema_version = data.get("schema_version", "2.0")

    reg_path = Path(source_registry_path) if source_registry_path else catalog_path.parent / "source_registry.json"
    valid_sources: dict[str, Any] = {}
    if reg_path.is_file():
        try:
            valid_sources = json.loads(reg_path.read_text(encoding="utf-8")).get("sources", {})
        except Exception:
            valid_sources = {}

    lang_names = {"vi": "Tiếng Việt", "en": "English", "ja": "日本語"}
    lang_name = lang_names.get(language, language.upper())

    note_lines = {
        "vi": (
            "Tài liệu này được tạo tự động từ knowledge_catalog.json và source_registry.json.\n"
            "Đây là curated local retrieval; chưa phải vector/embedding RAG và chưa đọc tài liệu gốc lúc runtime.\n"
            "Gemini là lớp soạn câu trả lời bên ngoài khi khả dụng.\n"
            "Không chỉnh sửa trực tiếp — cập nhật catalog rồi tạo lại tài liệu."
        ),
        "en": (
            "This document is auto-generated from knowledge_catalog.json and source_registry.json.\n"
            "This is curated local retrieval; not vector/embedding RAG and does not read original documents at runtime.\n"
            "Gemini is the external answer-composition layer when available.\n"
            "Do not edit directly — update the catalog and regenerate."
        ),
        "ja": (
            "このドキュメントはknowledge_catalog.jsonおよびsource_registry.jsonから自動生成されました。\n"
            "これはキュレーテッドローカル検索であり、ベクトル/埋め込みRAGではなく、実行時に元のドキュメントを読み込むものではありません。\n"
            "Geminiは利用可能な場合の外部回答作成レイヤーです。\n"
            "直接編集しないでください。カタログを更新してから再生成してください。"
        ),
    }

    lines: list[str] = [
        f"# MP2027 Business Chat Knowledge — {lang_name}",
        "",
        f"Schema version: {schema_version}",
        "",
        note_lines.get(language, note_lines["en"]),
        "",
        "---",
        "",
    ]

    for entry in entries:
        entry_id = entry.get("id", "")
        status = entry.get("status", "active")
        review_status = entry.get("review_status", "approved")
        source_ref_ids = entry.get("source_ref_ids", entry.get("source_refs", []))
        lang_data = entry.get(language, {})

        if not isinstance(lang_data, dict):
            continue

        title = lang_data.get("title", "")
        answer_context = lang_data.get("answer_context", "")
        safe_steps = lang_data.get("safe_steps", [])
        keywords = lang_data.get("keywords", [])

        source_labels: list[str] = []
        for s_id in source_ref_ids:
            label = valid_sources.get(s_id, {}).get(language, {}).get("label", "")
            if label:
                source_labels.append(label)

        lines.append(f"## {entry_id}: {title}")
        lines.append("")
        lines.append(f"**Status**: {status} | **Review**: {review_status}")
        if source_labels:
            lines.append(f"**Source**: {', '.join(source_labels)}")
        lines.append("")
        lines.append(answer_context)
        lines.append("")
        for i, step in enumerate(safe_steps, 1):
            lines.append(f"{i}. {step}")
        lines.append("")
        lines.append(f"Keywords: {', '.join(keywords)}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)
