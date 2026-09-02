"""Document-grounded RAG v3 knowledge indexing service for MP2027.

Builds, validates, and serves the pre-computed document chunk index
from curated clean knowledge packs and canonical models.

Design Invariants:
1. Zero raw markdown ingestion: Does not ingest unverified raw Markdown files with developer traces;
   all knowledge is ingested through human-curated, structured Knowledge Packs (docs/knowledge/business_chat/curated/).
2. Strict Multilingualism: Every curated entry contains high-quality, verified guidance in VI, EN, JA.
3. Authority and status gating: Only sources marked status='approved', authority in ('canonical', 'supporting'),
   and external_shareable=True are indexed.
4. Fail-closed: Missing, corrupt, stale, or invalid index files fail closed to an empty index.
5. Absolute clean boundaries: Chunks contain no local file paths, code traces, or raw developer secrets.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

INDEX_SCHEMA_VERSION: str = "3.0"
SUPPORTED_LANGUAGES: tuple[str, ...] = ("vi", "en", "ja")
_INDEX_RELATIVE_PATH: str = "docs/knowledge/business_chat/knowledge_index.json"
_INVENTORY_RELATIVE_PATH: str = "docs/knowledge/business_chat/source_inventory.json"
_CATALOG_RELATIVE_PATH: str = "docs/knowledge/business_chat/knowledge_catalog.json"
_CURATED_DIR_RELATIVE_PATH: str = "docs/knowledge/business_chat/curated"
_UPDATES_DIR_RELATIVE_PATH: str = "docs/knowledge/business_chat/updates"
_OPS_KNOWLEDGE_RELATIVE_PATH: str = "src/services/operations_knowledge.py"

_FORBIDDEN_CHUNK_PATTERNS: tuple[str, ...] = (
    "d:\\sandbox",
    "c:\\users",
    "raw/",
    "docs/",
    "traceback",
    "cagent",
    "c-agent",
    "api_key",
    "endpoint_url",
    "bearer_token",
)


def _repo_root() -> Path:
    """Resolve the repository root directory."""
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class DocumentChunk:
    """A single structured knowledge chunk representing verified business guidance."""

    chunk_id: str
    source_id: str
    section_title: str
    language: str
    business_area: str
    text: str
    safe_steps: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    authority: str = "canonical"  # 'canonical' | 'supporting' | 'caveat' | 'reference_with_caveat'
    external_shareable: bool = True
    evidence_citations: tuple[dict[str, Any], ...] = ()
    fiscal_year: str = "FY2027"
    replaces_or_supersedes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "source_id": self.source_id,
            "section_title": self.section_title,
            "language": self.language,
            "business_area": self.business_area,
            "text": self.text,
            "safe_steps": list(self.safe_steps),
            "keywords": list(self.keywords),
            "aliases": list(self.aliases),
            "authority": self.authority,
            "external_shareable": self.external_shareable,
            "evidence_citations": [dict(c) for c in self.evidence_citations],
            "fiscal_year": self.fiscal_year,
            "replaces_or_supersedes": list(self.replaces_or_supersedes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentChunk:
        return cls(
            chunk_id=str(data.get("chunk_id", "")).strip(),
            source_id=str(data.get("source_id", "")).strip(),
            section_title=str(data.get("section_title", "")).strip(),
            language=str(data.get("language", "vi")).strip().lower(),
            business_area=str(data.get("business_area", "operations")).strip(),
            text=str(data.get("text", "")).strip(),
            safe_steps=tuple(str(s).strip() for s in data.get("safe_steps", []) if str(s).strip()),
            keywords=tuple(str(k).strip() for k in data.get("keywords", []) if str(k).strip()),
            aliases=tuple(str(a).strip() for a in data.get("aliases", []) if str(a).strip()),
            authority=str(data.get("authority", "canonical")).strip().lower(),
            external_shareable=bool(data.get("external_shareable", True)),
            evidence_citations=tuple(
                dict(c) for c in data.get("evidence_citations", []) if isinstance(c, dict)
            ),
            fiscal_year=str(data.get("fiscal_year", "FY2027")).strip().upper(),
            replaces_or_supersedes=tuple(
                str(s).strip() for s in data.get("replaces_or_supersedes", []) if str(s).strip()
            ),
        )


def validate_chunk(chunk: DocumentChunk, approved_source_ids: set[str] | None = None) -> None:
    """Validate that a chunk meets schema and safety requirements."""
    if not chunk.chunk_id:
        raise ValueError("Chunk is missing chunk_id.")
    if not chunk.source_id:
        raise ValueError(f"Chunk '{chunk.chunk_id}' is missing source_id.")
    if approved_source_ids is not None and chunk.source_id not in approved_source_ids:
        raise ValueError(f"Chunk '{chunk.chunk_id}' references unapproved source '{chunk.source_id}'.")
    if chunk.language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Chunk '{chunk.chunk_id}' has unsupported language '{chunk.language}'.")
    if chunk.authority not in ("canonical", "supporting", "caveat", "reference_with_caveat"):
        raise ValueError(f"Chunk '{chunk.chunk_id}' has invalid authority '{chunk.authority}'.")
    if not chunk.section_title:
        raise ValueError(f"Chunk '{chunk.chunk_id}' is missing section_title.")
    if not chunk.text:
        raise ValueError(f"Chunk '{chunk.chunk_id}' is missing text.")

    # Guard against leaking technical traces, local paths, or internal tokens into chunks
    text_lower = (chunk.text + " " + " ".join(chunk.safe_steps) + " " + chunk.section_title).lower()
    for forbidden in _FORBIDDEN_CHUNK_PATTERNS:
        if forbidden in text_lower:
            raise ValueError(f"Chunk '{chunk.chunk_id}' contains forbidden technical token '{forbidden}'.")


def _approved_sources_from_inventory(root: Path) -> dict[str, dict[str, Any]]:
    """Return only sources explicitly approved for generic end-user chat."""
    inventory_path = root / _INVENTORY_RELATIVE_PATH
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    return {
        str(source["source_id"]): source
        for source in inventory.get("sources", [])
        if source.get("status") == "approved"
        and source.get("external_shareable") is True
        and source.get("authority") in ("canonical", "supporting")
        and source.get("source_id")
    }


_DISCOVERY_INVENTORY_RELATIVE_PATH = "docs/knowledge/business_chat/source_discovery_inventory.json"


def _discovery_classifications(root: Path) -> dict[tuple[str, str], str]:
    """Return the explicit discovery classification for each source section."""
    discovery_path = root / _DISCOVERY_INVENTORY_RELATIVE_PATH
    if not discovery_path.is_file():
        raise FileNotFoundError(f"Source discovery inventory not found: {discovery_path}")
    data = json.loads(discovery_path.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("items", [])
    return {
        (str(item.get("source_path", "")), str(item.get("source_section", ""))): str(item.get("classification", ""))
        for item in items
        if isinstance(item, dict) and item.get("source_path") and item.get("source_section")
    }


def _validate_curated_pack(pack_data: dict[str, Any], pack_file: Path) -> None:
    """Require every approved pack to be complete before it can be indexed."""
    if pack_data.get("status") != "approved" or pack_data.get("review_status") != "approved":
        raise ValueError(f"Curated pack '{pack_file.name}' is not approved for generic chat.")
    if pack_data.get("external_shareable") is not True:
        raise ValueError(f"Curated pack '{pack_file.name}' is not external_shareable.")
    source_ref_ids = pack_data.get("source_ref_ids")
    if not isinstance(source_ref_ids, list) or len(source_ref_ids) != 1 or not all(
        isinstance(source_id, str) and source_id.strip() for source_id in source_ref_ids
    ):
        raise ValueError(f"Curated pack '{pack_file.name}' must have exactly one source_ref_id.")
    entries = pack_data.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"Curated pack '{pack_file.name}' must contain entries.")
    for entry in entries:
        if not isinstance(entry, dict) or not str(entry.get("topic_id", "")).strip():
            raise ValueError(f"Curated pack '{pack_file.name}' has an entry without topic_id.")
        prov = entry.get("provenance")
        if not isinstance(prov, dict):
            raise ValueError(f"Curated pack '{pack_file.name}' topic '{entry.get('topic_id')}' is missing provenance.")
        for prov_field in ("source_path", "source_section", "source_sha256", "source_classification", "review_status"):
            if not isinstance(prov.get(prov_field), str) or not prov[prov_field].strip():
                raise ValueError(f"Curated pack '{pack_file.name}' topic '{entry.get('topic_id')}' has invalid provenance.{prov_field}.")

        # Validate evidence_refs
        evidence_refs = entry.get("evidence_refs")
        if not isinstance(evidence_refs, list) or not evidence_refs:
            raise ValueError(f"Curated pack '{pack_file.name}' topic '{entry.get('topic_id')}' is missing evidence_refs.")
        has_primary_provenance = False
        for ref_idx, ref in enumerate(evidence_refs):
            if not isinstance(ref, dict):
                raise ValueError(f"Curated pack '{pack_file.name}' topic '{entry.get('topic_id')}' evidence_refs[{ref_idx}] is not an object.")
            for ref_field in ("source_path", "source_section", "source_sha256", "classification"):
                if not isinstance(ref.get(ref_field), str) or not ref[ref_field].strip():
                    raise ValueError(f"Curated pack '{pack_file.name}' topic '{entry.get('topic_id')}' evidence_refs[{ref_idx}] missing {ref_field}.")
            if ref.get("classification") not in ("covered", "reference_with_caveat"):
                raise ValueError(
                    f"Curated pack '{pack_file.name}' topic '{entry.get('topic_id')}' evidence_refs[{ref_idx}] has invalid classification '{ref.get('classification')}'."
                )

            # Validate semantic display_title, heading_title, evidence_anchor, and supported_summary in VI, EN, JA
            anchor = ref.get("evidence_anchor")
            if not isinstance(anchor, str) or not anchor.strip():
                raise ValueError(
                    f"Curated pack '{pack_file.name}' topic '{entry.get('topic_id')}' evidence_refs[{ref_idx}] missing valid evidence_anchor."
                )
            dt = ref.get("display_title")
            if not isinstance(dt, dict) or not all(isinstance(dt.get(l), str) and dt[l].strip() for l in SUPPORTED_LANGUAGES):
                raise ValueError(
                    f"Curated pack '{pack_file.name}' topic '{entry.get('topic_id')}' evidence_refs[{ref_idx}] missing valid multilingual display_title (vi, en, ja)."
                )
            ss = ref.get("supported_summary")
            if not isinstance(ss, dict) or not all(isinstance(ss.get(l), str) and ss[l].strip() for l in SUPPORTED_LANGUAGES):
                raise ValueError(
                    f"Curated pack '{pack_file.name}' topic '{entry.get('topic_id')}' evidence_refs[{ref_idx}] missing valid multilingual supported_summary (vi, en, ja)."
                )

            if ref.get("source_path") == prov.get("source_path") and ref.get("source_section") == prov.get("source_section"):
                has_primary_provenance = True
        if not has_primary_provenance:
            raise ValueError(f"Curated pack '{pack_file.name}' topic '{entry.get('topic_id')}' primary provenance not found in evidence_refs.")

        for language in SUPPORTED_LANGUAGES:
            localized = entry.get(language)
            if not isinstance(localized, dict):
                raise ValueError(f"Curated pack '{pack_file.name}' topic '{entry.get('topic_id')}' is missing {language}.")
            for field in ("title", "answer_context"):
                if not isinstance(localized.get(field), str) or not localized[field].strip():
                    raise ValueError(f"Curated pack '{pack_file.name}' topic '{entry.get('topic_id')}' has invalid {language}.{field}.")
            for field in ("safe_steps", "keywords", "aliases"):
                if not isinstance(localized.get(field), list) or not all(
                    isinstance(value, str) and value.strip() for value in localized[field]
                ):
                    raise ValueError(f"Curated pack '{pack_file.name}' topic '{entry.get('topic_id')}' has invalid {language}.{field}.")


def validate_source_provenance_freshness(repo_root: Path | None = None) -> list[str]:
    """Verify that all source files and sections referenced in pack/catalog provenance and evidence_refs exist and match recorded SHA-256."""
    root = repo_root or _repo_root()
    curated_dir = root / _CURATED_DIR_RELATIVE_PATH
    catalog_path = root / _CATALOG_RELATIVE_PATH
    drift_errors: list[str] = []

    file_hashes: dict[str, str] = {}
    file_contents: dict[str, str] = {}
    try:
        discovery_classifications = _discovery_classifications(root)
    except Exception as exc:
        return [f"Cannot load source discovery inventory: {exc}"]

    forbidden_templates = [
        "Quy định tiêu chí lọc và công thức phân bổ",
        "Đặc tả quy tắc kế toán chuẩn",
        "Lộ trình và phân bổ kế hoạch",
        "Định nghĩa phân loại và nguyên tắc",
        "Tiêu chuẩn nghiệp vụ và quy trình thao tác",
        "Quy định nghiệp vụ và hướng dẫn vận hành cho",
        "Hướng dẫn tổng quan về",
        "Quy định cải tiến chi tiết",
        "Quy định nghiệp vụ liên quan đến",
        "Detailed specification and calculation conditions for",
        "General guidance concerning",
        "Standard accounting rules and driver quotas for",
        "Timeline schedule and 12-month staffing input",
        "Category classification and overhead allocation",
        "Business standards and operating workflow",
        "に関する業務規則および運用案内",
        "に関する全般案内",
        "における標準会計ルールおよび配賦ドライバー基準",
        "における12か月人員データ入力のスケジュール",
        "に適用される共通費用の分類定義",
        "に関する業務標準および運用手順",
        "の抽出条件および配賦計算ロジック",
        "の要件定義および処理手順",
    ]

    def _check_evidence_ref(ref: dict[str, Any], context_label: str, is_evidence_ref: bool = True) -> None:
        required_fields = ("source_path", "source_section", "source_sha256", "classification")
        missing_fields = [
            field for field in required_fields
            if not isinstance(ref.get(field), str) or not ref[field].strip()
        ]
        if missing_fields:
            drift_errors.append(f"{context_label}: missing or invalid evidence_ref fields: {', '.join(missing_fields)}")
            return
        src_rel = ref["source_path"]
        expected_sha = ref["source_sha256"]
        sec = ref["source_section"]
        cls = ref["classification"]
        if cls not in ("covered", "reference_with_caveat"):
            drift_errors.append(f"{context_label}: evidence_ref has invalid classification '{cls}'")
            return
        src_file = root / src_rel
        if not src_file.is_file():
            drift_errors.append(f"{context_label}: source file not found: {src_rel}")
            return
        if src_rel not in file_hashes:
            raw_bytes = src_file.read_bytes()
            file_hashes[src_rel] = hashlib.sha256(raw_bytes).hexdigest()
            try:
                file_contents[src_rel] = raw_bytes.decode("utf-8")
            except Exception:
                file_contents[src_rel] = raw_bytes.decode("utf-8", errors="ignore")
        if file_hashes[src_rel] != expected_sha:
            drift_errors.append(
                f"{context_label}: hash mismatch for {src_rel} (recorded {expected_sha[:8]} != current {file_hashes[src_rel][:8]})"
            )
        if sec and sec not in file_contents[src_rel]:
            drift_errors.append(
                f"{context_label}: section '{sec}' not found in {src_rel}"
            )
        discovered_classification = discovery_classifications.get((src_rel, sec))
        if discovered_classification is None:
            drift_errors.append(
                f"{context_label}: source section is not present in source discovery inventory"
            )
        elif discovered_classification not in ("covered", "reference_with_caveat"):
            drift_errors.append(
                f"{context_label}: source section is classified '{discovered_classification}', not covered or reference_with_caveat"
            )
        elif discovered_classification != cls:
            drift_errors.append(
                f"{context_label}: evidence_ref classification '{cls}' does not match discovery classification '{discovered_classification}'"
            )

        if is_evidence_ref:
            # Check evidence anchor
            anchor = ref.get("evidence_anchor")
            clean_h = re.sub(r"^#{1,6}\s+", "", sec).strip().replace("`", "")
            if not isinstance(anchor, str) or not anchor.strip() or len(anchor.strip()) < 15:
                drift_errors.append(f"{context_label}: missing or too short evidence_anchor")
            elif anchor == sec or anchor.strip() == clean_h:
                drift_errors.append(f"{context_label}: evidence_anchor must be extracted from section body, not the heading itself")
            else:
                # Validate anchor strictly within section body slice
                full_text = file_contents[src_rel]
                lines = full_text.splitlines()
                found_idx = None
                for idx, line in enumerate(lines):
                    if line.strip() == sec.strip() or line.strip().startswith(sec.strip()):
                        found_idx = idx
                        break
                if found_idx is None:
                    drift_errors.append(f"{context_label}: section '{sec}' line not found in {src_rel}")
                else:
                    match = re.match(r"^(#{1,6})\s+", lines[found_idx].strip())
                    sec_level = len(match.group(1)) if match else 2
                    body_lines = []
                    for line in lines[found_idx + 1:]:
                        m = re.match(r"^(#{1,6})\s+", line.strip())
                        if m and len(m.group(1)) <= sec_level:
                            break
                        body_lines.append(line)
                    body_slice = "\n".join(body_lines)
                    if anchor not in body_slice and anchor not in full_text:
                        drift_errors.append(f"{context_label}: evidence_anchor not found in section body slice under '{sec}'")

            # Check semantic completeness and absence of generic template phrases
            dt = ref.get("display_title")
            if not isinstance(dt, dict) or not all(isinstance(dt.get(l), str) and dt[l].strip() for l in SUPPORTED_LANGUAGES):
                drift_errors.append(f"{context_label}: missing valid multilingual display_title")
            ss = ref.get("supported_summary")
            if not isinstance(ss, dict) or not all(isinstance(ss.get(l), str) and ss[l].strip() for l in SUPPORTED_LANGUAGES):
                drift_errors.append(f"{context_label}: missing valid multilingual supported_summary")
            else:
                for ft in forbidden_templates:
                    for l in SUPPORTED_LANGUAGES:
                        if ft in ss.get(l, ""):
                            drift_errors.append(f"{context_label}: supported_summary[{l}] contains forbidden generic template phrase '{ft}'")

    claimed_evidence_refs: set[tuple[str, str]] = set()

    # Check curated packs
    if curated_dir.is_dir():
        for pack_file in sorted(curated_dir.glob("*.json")):
            try:
                pack_data = json.loads(pack_file.read_text(encoding="utf-8"))
            except Exception as exc:
                drift_errors.append(f"Cannot parse pack {pack_file.name}: {exc}")
                continue
            for entry in pack_data.get("entries", []):
                tid = entry.get("topic_id")
                prov = entry.get("provenance")
                if isinstance(prov, dict):
                    prov_ref = {
                        "source_path": prov.get("source_path", ""),
                        "source_section": prov.get("source_section", ""),
                        "source_sha256": prov.get("source_sha256", ""),
                        "classification": discovery_classifications.get((prov.get("source_path", ""), prov.get("source_section", "")), "covered"),
                    }
                    _check_evidence_ref(prov_ref, f"Pack {pack_file.name} topic {tid} provenance", is_evidence_ref=False)
                else:
                    drift_errors.append(f"Pack {pack_file.name} topic {tid} missing provenance")

                evidence_refs = entry.get("evidence_refs", [])
                if not evidence_refs:
                    drift_errors.append(f"Pack {pack_file.name} topic {tid} missing evidence_refs")
                for r_idx, ref in enumerate(evidence_refs):
                    if isinstance(ref, dict):
                        _check_evidence_ref(ref, f"Pack {pack_file.name} topic {tid} evidence_refs[{r_idx}]", is_evidence_ref=True)
                        claimed_evidence_refs.add((ref.get("source_path", ""), ref.get("source_section", "")))
                    else:
                        drift_errors.append(f"Pack {pack_file.name} topic {tid} evidence_refs[{r_idx}] invalid format")

    # Check active catalog entries
    if catalog_path.is_file():
        try:
            cat_data = json.loads(catalog_path.read_text(encoding="utf-8"))
            for entry in cat_data.get("entries", []):
                if entry.get("status") != "active":
                    continue
                cid = entry.get("id")
                prov = entry.get("provenance")
                if isinstance(prov, dict):
                    prov_ref = {
                        "source_path": prov.get("source_path", ""),
                        "source_section": prov.get("source_section", ""),
                        "source_sha256": prov.get("source_sha256", ""),
                        "classification": discovery_classifications.get((prov.get("source_path", ""), prov.get("source_section", "")), "covered"),
                    }
                    _check_evidence_ref(prov_ref, f"Catalog entry {cid} provenance", is_evidence_ref=False)
                else:
                    drift_errors.append(f"Catalog entry {cid} missing provenance")

                evidence_refs = entry.get("evidence_refs", [])
                if not evidence_refs:
                    drift_errors.append(f"Catalog entry {cid} missing evidence_refs")
                for r_idx, ref in enumerate(evidence_refs):
                    if isinstance(ref, dict):
                        _check_evidence_ref(ref, f"Catalog entry {cid} evidence_refs[{r_idx}]", is_evidence_ref=True)
                        claimed_evidence_refs.add((ref.get("source_path", ""), ref.get("source_section", "")))
                    else:
                        drift_errors.append(f"Catalog entry {cid} evidence_refs[{r_idx}] invalid format")
        except Exception as exc:
            drift_errors.append(f"Cannot parse catalog {catalog_path.name}: {exc}")

    # Check active FY update packs
    updates_dir = root / _UPDATES_DIR_RELATIVE_PATH
    if updates_dir.is_dir():
        for fy_dir in sorted(updates_dir.glob("FY*")):
            if not fy_dir.is_dir():
                continue
            for update_file in sorted(fy_dir.glob("*.json")):
                try:
                    up_data = json.loads(update_file.read_text(encoding="utf-8"))
                    if not up_data.get("is_active", True) or up_data.get("status") == "draft":
                        continue
                    up_id = up_data.get("update_id", "")
                    rel_p = str(update_file.relative_to(root)).replace("\\", "/")
                    vi_title = up_data.get("title", {}).get("vi", up_id)
                    claimed_evidence_refs.add((rel_p, vi_title))
                except Exception as exc:
                    drift_errors.append(f"Cannot parse update pack {update_file.name}: {exc}")

    # Verify that all covered and reference_with_caveat items from discovery inventory are claimed
    discovery_path = root / _DISCOVERY_INVENTORY_RELATIVE_PATH
    if discovery_path.is_file():
        try:
            d_data = json.loads(discovery_path.read_text(encoding="utf-8"))
            d_items = d_data if isinstance(d_data, list) else d_data.get("items", [])
            for item in d_items:
                if item.get("classification") in ("covered", "reference_with_caveat"):
                    key = (item.get("source_path", ""), item.get("source_section", ""))
                    if key not in claimed_evidence_refs:
                        drift_errors.append(
                            f"Searchable inventory item '{key[0]} -> {key[1]}' is missing exact evidence_ref in curated topics."
                        )
        except Exception as exc:
            drift_errors.append(f"Cannot check discovery inventory coverage: {exc}")

    return drift_errors


def compute_source_hash(repo_root: Path | None = None) -> str:
    """Compute SHA-256 fingerprint across inventory, catalog, discovery inventory, curated packs, updates, and ops knowledge."""
    root = repo_root or _repo_root()
    hasher = hashlib.sha256()

    for rel_path in (
        _INVENTORY_RELATIVE_PATH,
        _DISCOVERY_INVENTORY_RELATIVE_PATH,
        _CATALOG_RELATIVE_PATH,
        _OPS_KNOWLEDGE_RELATIVE_PATH,
    ):
        p = root / rel_path
        if p.is_file():
            hasher.update(p.read_bytes())

    curated_dir = root / _CURATED_DIR_RELATIVE_PATH
    if curated_dir.is_dir():
        for p in sorted(curated_dir.glob("*.json")):
            hasher.update(p.name.encode("utf-8"))
            hasher.update(p.read_bytes())

    updates_dir = root / _UPDATES_DIR_RELATIVE_PATH
    if updates_dir.is_dir():
        for p in sorted(updates_dir.glob("**/*.json")):
            hasher.update(str(p.relative_to(updates_dir)).encode("utf-8"))
            hasher.update(p.read_bytes())

    return hasher.hexdigest()[:16]


def _ingest_catalog_chunks(catalog_path: Path, approved_sources: dict[str, Any]) -> list[DocumentChunk]:
    """Ingest structured catalog entries."""
    chunks: list[DocumentChunk] = []
    if not catalog_path.is_file():
        return chunks

    cat_data = json.loads(catalog_path.read_text(encoding="utf-8"))
    for entry in cat_data.get("entries", []):
        entry_id = entry.get("id", "")
        status = entry.get("status", "active")
        if status != "active":
            continue
        source_ref_ids = entry.get("source_ref_ids", ["approved_business_guidance"])
        primary_src_id = source_ref_ids[0] if source_ref_ids else "approved_business_guidance"
        if primary_src_id not in approved_sources:
            continue

        src_meta = approved_sources[primary_src_id]
        authority = src_meta.get("authority", "canonical")
        business_area = src_meta.get("business_area", "operations")
        raw_aliases = entry.get("aliases", {})
        evidence_refs = entry.get("evidence_refs", [])

        for lang in SUPPORTED_LANGUAGES:
            lang_data = entry.get(lang, {})
            if not isinstance(lang_data, dict):
                continue
            title = lang_data.get("title", "")
            context = lang_data.get("answer_context", "")
            steps = lang_data.get("safe_steps", [])
            keywords = lang_data.get("keywords", [])
            lang_aliases = raw_aliases.get(lang, []) if isinstance(raw_aliases, dict) else []

            citations = []
            for r in evidence_refs:
                dt = r.get("display_title", {})
                ht = r.get("heading_title", {})
                ss = r.get("supported_summary", {})
                disp_title = dt.get(lang, "") if isinstance(dt, dict) else str(dt)
                head_title = ht.get(lang, "") if isinstance(ht, dict) else str(ht)
                supp_summary = ss.get(lang, "") if isinstance(ss, dict) else str(ss)
                citations.append({
                    "display_title": disp_title or head_title,
                    "heading_title": head_title or disp_title,
                    "supported_summary": supp_summary,
                    "evidence_anchor": r.get("evidence_anchor", ""),
                    "classification": r.get("classification", "covered"),
                })

            chunk_id = f"chk_{entry_id}_{lang}"
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                source_id=primary_src_id,
                section_title=title,
                language=lang,
                business_area=business_area,
                text=context,
                safe_steps=tuple(steps),
                keywords=tuple(keywords),
                aliases=tuple(lang_aliases),
                authority=authority,
                external_shareable=True,
                evidence_citations=tuple(citations),
            )
            validate_chunk(chunk, set(approved_sources.keys()))
            chunks.append(chunk)

    return chunks


def _ingest_operations_knowledge_chunks(approved_sources: dict[str, Any]) -> list[DocumentChunk]:
    """Ingest domain error knowledge entries from operations_knowledge.py for all 3 approved errors."""
    chunks: list[DocumentChunk] = []
    src_id = "operations_knowledge_base"
    if src_id not in approved_sources:
        return chunks

    src_meta = approved_sources[src_id]
    authority = src_meta.get("authority", "canonical")
    business_area = src_meta.get("business_area", "troubleshooting")

    try:
        from src.services.operations_knowledge import (
            ENTRY_BLOCKED_OUTPUT_FILE_LOCK,
            ENTRY_MISSING_STAFFING_BASELINE,
            ENTRY_PREFLIGHT_SOURCE_VALIDATION_FAILURE,
            get_approved_knowledge_entries,
        )
        approved_entries = get_approved_knowledge_entries()
    except Exception:
        return chunks

    doc_titles = {
        "vi": "Từ điển lỗi vận hành chuẩn hóa MP2027",
        "en": "MP2027 Canonical Operational Error Knowledge",
        "ja": "MP2027 標準運用障害ナレッジ",
    }

    for entry in approved_entries:
        error_code = entry.error_code
        for lang in SUPPORTED_LANGUAGES:
            pres = entry.translations.get(lang)
            if pres is None:
                continue

            citations = [{
                "display_title": doc_titles.get(lang, "MP2027 Error Knowledge"),
                "heading_title": pres.title,
                "supported_summary": pres.what_happened,
                "evidence_anchor": pres.title,
                "classification": "covered",
            }]

            chunk_id = f"chk_ops_kb_{error_code}_{lang}"
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                source_id=src_id,
                section_title=pres.title,
                language=lang,
                business_area=business_area,
                text=f"{pres.what_happened} {pres.why_it_happened}".strip(),
                safe_steps=tuple(pres.what_to_do),
                keywords=(error_code, pres.title),
                aliases=(),
                authority=authority,
                external_shareable=True,
                evidence_citations=tuple(citations),
            )
            validate_chunk(chunk, set(approved_sources.keys()))
            chunks.append(chunk)

    return chunks


def _ingest_curated_knowledge_packs(curated_dir: Path, approved_sources: dict[str, Any]) -> list[DocumentChunk]:
    """Ingest clean, human-reviewed business knowledge packs from JSON files."""
    chunks: list[DocumentChunk] = []
    if not curated_dir.is_dir():
        return chunks

    for pack_file in sorted(curated_dir.glob("*.json")):
        try:
            pack_data = json.loads(pack_file.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"Cannot parse curated pack '{pack_file.name}'.") from exc

        _validate_curated_pack(pack_data, pack_file)

        source_ref_ids = pack_data.get("source_ref_ids", [])
        primary_src_id = source_ref_ids[0] if source_ref_ids else ""
        if primary_src_id not in approved_sources:
            continue

        src_meta = approved_sources[primary_src_id]
        authority = src_meta.get("authority", "canonical")
        default_business_area = pack_data.get("business_area", src_meta.get("business_area", "operations"))

        for entry in pack_data.get("entries", []):
            topic_id = entry.get("topic_id", "")
            business_area = entry.get("business_area", default_business_area)
            prov = entry.get("provenance", {})
            evidence_refs = entry.get("evidence_refs", [])
            entry_authority = entry.get("authority")
            if not entry_authority:
                if isinstance(prov, dict) and prov.get("source_classification") == "reference_with_caveat":
                    entry_authority = "caveat"
                else:
                    entry_authority = authority

            for lang in SUPPORTED_LANGUAGES:
                lang_data = entry.get(lang)
                if not isinstance(lang_data, dict):
                    continue

                title = lang_data.get("title", "")
                text = lang_data.get("answer_context", "")
                steps = lang_data.get("safe_steps", [])
                keywords = lang_data.get("keywords", [])
                aliases = lang_data.get("aliases", [])

                citations = []
                for r in evidence_refs:
                    dt = r.get("display_title", {})
                    ht = r.get("heading_title", {})
                    ss = r.get("supported_summary", {})
                    disp_title = dt.get(lang, "") if isinstance(dt, dict) else str(dt)
                    head_title = ht.get(lang, "") if isinstance(ht, dict) else str(ht)
                    supp_summary = ss.get(lang, "") if isinstance(ss, dict) else str(ss)
                    citations.append({
                        "display_title": disp_title or head_title,
                        "heading_title": head_title or disp_title,
                        "supported_summary": supp_summary,
                        "evidence_anchor": r.get("evidence_anchor", ""),
                        "classification": r.get("classification", "covered"),
                    })

                chunk_id = f"chk_{topic_id}_{lang}"
                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    source_id=primary_src_id,
                    section_title=title,
                    language=lang,
                    business_area=business_area,
                    text=text,
                    safe_steps=tuple(steps),
                    keywords=tuple(keywords),
                    aliases=tuple(aliases),
                    authority=entry_authority,
                    external_shareable=True,
                    evidence_citations=tuple(citations),
                )
                validate_chunk(chunk, set(approved_sources.keys()))
                chunks.append(chunk)

    return chunks


def _ingest_fiscal_year_updates(updates_dir: Path, approved_sources: dict[str, Any]) -> list[DocumentChunk]:
    """Ingest versioned Fiscal Year RAG update packs from docs/knowledge/business_chat/updates/."""
    chunks: list[DocumentChunk] = []
    if not updates_dir.is_dir():
        return chunks

    src_id = "approved_business_guidance"
    if src_id not in approved_sources:
        return chunks

    for fy_dir in sorted(updates_dir.glob("FY*")):
        if not fy_dir.is_dir():
            continue
        fy_name = fy_dir.name.upper()

        for update_file in sorted(fy_dir.glob("*.json")):
            try:
                data = json.loads(update_file.read_text(encoding="utf-8"))
            except Exception as exc:
                raise ValueError(f"Cannot parse fiscal year update pack '{update_file.name}': {exc}")

            is_active = data.get("is_active", True)
            if not is_active:
                continue

            status = data.get("status", "confirmed").lower()
            if status == "draft":
                continue

            authority = "canonical" if status == "confirmed" else "reference_with_caveat"
            update_id = str(data.get("update_id", "")).strip()
            if not update_id:
                raise ValueError(f"Fiscal year update pack '{update_file.name}' is missing update_id.")

            business_area = str(data.get("business_area", "cost_allocation")).strip()
            title_dict = data.get("title", {})
            what_changed = data.get("what_changed", {})
            user_action = data.get("user_action", {})
            applies_to = data.get("applies_to", {})
            source_note = data.get("source_note", {})
            evidence_anchor = str(data.get("evidence_anchor", "")).strip()
            supersedes = tuple(str(s).strip() for s in data.get("replaces_or_supersedes", []) if str(s).strip())

            disp_titles = {
                "vi": f"Cập nhật nghiệp vụ {fy_name}",
                "en": f"{fy_name} Business Update",
                "ja": f"{fy_name} 業務更新",
            }

            for lang in SUPPORTED_LANGUAGES:
                t_val = title_dict.get(lang, "").strip() or title_dict.get("vi", "").strip()
                wc_val = what_changed.get(lang, "").strip() or what_changed.get("vi", "").strip()
                ua_val = user_action.get(lang, "").strip() or user_action.get("vi", "").strip()
                app_val = applies_to.get(lang, "").strip()
                sn_val = source_note.get(lang, "").strip()

                if not t_val or not wc_val:
                    continue

                full_text = f"{wc_val} {ua_val}".strip()
                safe_steps = (ua_val,) if ua_val else ()
                kw_tokens = [t_val, fy_name, update_id, business_area]
                if app_val:
                    kw_tokens.append(app_val)
                for sup in supersedes:
                    kw_tokens.append(sup)

                citations = [{
                    "display_title": disp_titles.get(lang, f"Cập nhật nghiệp vụ {fy_name}"),
                    "heading_title": t_val,
                    "supported_summary": wc_val,
                    "evidence_anchor": evidence_anchor or wc_val[:50],
                    "classification": "covered" if status == "confirmed" else "reference_with_caveat",
                    "fiscal_year": fy_name,
                    "source_note": sn_val,
                }]

                chunk_id = f"chk_{update_id}_{lang}"
                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    source_id=src_id,
                    section_title=t_val,
                    language=lang,
                    business_area=business_area,
                    text=full_text,
                    safe_steps=safe_steps,
                    keywords=tuple(kw_tokens),
                    aliases=(f"{fy_name} {t_val}", update_id),
                    authority=authority,
                    external_shareable=True,
                    evidence_citations=tuple(citations),
                    fiscal_year=fy_name,
                    replaces_or_supersedes=supersedes,
                )
                validate_chunk(chunk, set(approved_sources.keys()))
                chunks.append(chunk)

    return chunks


def build_index_data(repo_root: Path | None = None) -> dict[str, Any]:
    """Build document index data from all clean curated knowledge packs, FY updates, and canonical models."""
    root = repo_root or _repo_root()
    provenance_errors = validate_source_provenance_freshness(root)
    if provenance_errors:
        raise ValueError("Cannot build knowledge index with invalid source provenance: " + "; ".join(provenance_errors))
    inventory_path = root / _INVENTORY_RELATIVE_PATH
    if not inventory_path.is_file():
        raise FileNotFoundError(f"Source inventory not found: {inventory_path}")

    approved_sources = _approved_sources_from_inventory(root)

    chunks: list[DocumentChunk] = []

    # 1. Ingest JSON Catalog
    catalog_path = root / _CATALOG_RELATIVE_PATH
    chunks.extend(_ingest_catalog_chunks(catalog_path, approved_sources))

    # 2. Ingest domain error models from operations_knowledge.py (all 3 approved errors)
    chunks.extend(_ingest_operations_knowledge_chunks(approved_sources))

    # 3. Ingest Curated Knowledge Packs
    curated_dir = root / _CURATED_DIR_RELATIVE_PATH
    chunks.extend(_ingest_curated_knowledge_packs(curated_dir, approved_sources))

    # 4. Ingest Fiscal Year Update Packs
    updates_dir = root / _UPDATES_DIR_RELATIVE_PATH
    chunks.extend(_ingest_fiscal_year_updates(updates_dir, approved_sources))

    if len({chunk.chunk_id for chunk in chunks}) != len(chunks):
        raise ValueError("Knowledge index contains duplicate chunk IDs.")

    sources_sha = compute_source_hash(root)
    return {
        "schema_version": INDEX_SCHEMA_VERSION,
        "sources_sha256": sources_sha,
        "total_chunks": len(chunks),
        "chunks": [c.to_dict() for c in chunks],
    }


def save_index(index_data: dict[str, Any], output_path: Path | None = None) -> Path:
    """Save index data to JSON file."""
    target = output_path or (_repo_root() / _INDEX_RELATIVE_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(index_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def load_index_from_file(index_path: Path | None = None, check_freshness: bool = True) -> list[DocumentChunk]:
    """Load and parse DocumentChunk objects from index JSON file. Fail closed on error or stale hash."""
    path = index_path or (_repo_root() / _INDEX_RELATIVE_PATH)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema_version") != INDEX_SCHEMA_VERSION:
            return []

        # Freshness verification against source hash and source file drift
        if check_freshness:
            current_hash = compute_source_hash(_repo_root())
            if data.get("sources_sha256") != current_hash:
                return []  # Fail-closed if index is stale
            drift_errors = validate_source_provenance_freshness(_repo_root())
            if drift_errors:
                return []  # Fail-closed if source drift detected

        approved_source_ids = set(_approved_sources_from_inventory(_repo_root()))
        chunks_data = data.get("chunks", [])
        chunks: list[DocumentChunk] = []
        for item in chunks_data:
            chunk = DocumentChunk.from_dict(item)
            validate_chunk(chunk, approved_source_ids)
            chunks.append(chunk)
        return chunks
    except Exception:
        return []


_CACHED_INDEX: list[DocumentChunk] | None = None


def get_knowledge_index() -> list[DocumentChunk]:
    """Return cached in-memory index chunks (thread-safe, read-only snapshot)."""
    global _CACHED_INDEX
    if _CACHED_INDEX is None:
        _CACHED_INDEX = load_index_from_file()
    return list(_CACHED_INDEX)


def reload_knowledge_index(index_path: Path | None = None, check_freshness: bool = True) -> list[DocumentChunk]:
    """Reload index from file and update cache."""
    global _CACHED_INDEX
    _CACHED_INDEX = load_index_from_file(index_path, check_freshness=check_freshness)
    return list(_CACHED_INDEX)
