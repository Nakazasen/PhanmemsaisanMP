"""Curated multilingual business chat knowledge service for MP2027 — v2.

Loads a structured knowledge catalog from ``docs/knowledge/business_chat/knowledge_catalog.json``
and provides hybrid lexical retrieval in VI/EN/JA without runtime Markdown scanning.

v2 improvements over v1:
- Hybrid scoring: exact phrase, title, alias, keyword token, Vietnamese unaccented, CJK bigram.
- Minimum score threshold to avoid off-topic results.
- RetrievalTrace for internal debug/test grounding.
- RetrievalBackend protocol for future vector/embedding replacement.
- source_refs attribution in formatted context.
- Fail-closed: invalid catalog → empty → no context sent to Gemini.

Design invariants:
- Every catalog entry must have complete ``vi``, ``en``, ``ja`` translations.
- Retrieval returns at most 3 entries in the requested language.
- No raw technical content (traceback, exception, JSON, SQL, pipeline, function, variable).
- No runtime reads of long Markdown knowledge base files.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence, runtime_checkable

SUPPORTED_LANGUAGES: tuple[str, ...] = ("vi", "en", "ja")
_REQUIRED_ENTRY_FIELDS: tuple[str, ...] = ("title", "keywords", "answer_context", "safe_steps")
_MAX_RESULTS: int = 3
MIN_MATCH_SCORE: int = 3

# Technical tokens that must never appear in catalog content.
_FORBIDDEN_TOKENS: tuple[str, ...] = (
    "traceback", "exception", "json", "sql", "pipeline",
    "function", "variable",
)

# Catalog and registry paths relative to the repository root.
_CATALOG_RELATIVE_PATH: str = "docs/knowledge/business_chat/knowledge_catalog.json"
_SOURCE_REGISTRY_RELATIVE_PATH: str = "docs/knowledge/business_chat/source_registry.json"

# v2 entry status values
_VALID_STATUSES: frozenset[str] = frozenset({"active", "deprecated"})
_VALID_REVIEW_STATUSES: frozenset[str] = frozenset({"approved", "pending", "draft"})

# Scoring weights
_SCORE_EXACT_PHRASE: int = 6
_SCORE_TITLE_MATCH: int = 4
_SCORE_ALIAS_MATCH: int = 3
_SCORE_KEYWORD_TOKEN: int = 2
_SCORE_UNACCENTED_MATCH: int = 2
_SCORE_CJK_BIGRAM: int = 2

# These English words describe how a user asks, not the MP2027 subject they
# need help with.  They must never be enough to ground an answer on their own.
_LOW_SIGNAL_TOKENS: dict[str, frozenset[str]] = {
    "en": frozenset({
        "a", "an", "and", "are", "for", "from", "get", "getting", "guide",
        "help", "how", "start", "the", "to", "use", "what", "with",
    }),
}


# ---------------------------------------------------------------------------
# RetrievalTrace — internal debug/test only
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RetrievalTrace:
    """Internal trace for a single retrieval match. For test/debug only, not shown to users."""

    entry_id: str
    score: int
    match_reasons: tuple[str, ...]
    source_ref_ids: tuple[str, ...]

    @property
    def source_refs(self) -> tuple[str, ...]:
        """Backward-compatible alias for source_ref_ids."""
        return self.source_ref_ids


# ---------------------------------------------------------------------------
# RetrievalBackend protocol — future vector/embedding interface
# ---------------------------------------------------------------------------

@runtime_checkable
class RetrievalBackend(Protocol):
    """Protocol for pluggable retrieval backends.

    The default implementation uses hybrid lexical matching.
    A future vector/embedding backend can implement this protocol
    to replace or augment the lexical engine.
    """

    def search(
        self, query: str, language: str, top_k: int = _MAX_RESULTS,
    ) -> list[dict[str, Any]]:
        """Return up to *top_k* matching entries for *query* in *language*."""
        ...  # pragma: no cover


# ---------------------------------------------------------------------------
# Source Registry loading
# ---------------------------------------------------------------------------

def _repo_root() -> Path:
    """Resolve the repository root (two levels above ``src/services/``)."""
    return Path(__file__).resolve().parents[2]


def validate_source_registry(registry: dict[str, Any]) -> None:
    """Validate source registry schema. Fail closed if invalid."""
    if not isinstance(registry, dict):
        raise ValueError("Source registry must be a dictionary.")
    sources = registry.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise ValueError("Source registry 'sources' must be a non-empty dictionary.")
    for source_id, src_data in sources.items():
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("Source ID must be a non-empty string.")
        if not isinstance(src_data, dict):
            raise ValueError(f"Source '{source_id}' data must be a dictionary.")
        status = src_data.get("status")
        if status != "active":
            raise ValueError(f"Source '{source_id}' status must be 'active'.")
        for lang in SUPPORTED_LANGUAGES:
            lang_entry = src_data.get(lang)
            if not isinstance(lang_entry, dict) or not str(lang_entry.get("label", "")).strip():
                raise ValueError(f"Source '{source_id}' is missing label for language '{lang}'.")


def _load_source_registry_from_path(registry_path: Path) -> dict[str, Any]:
    """Load and parse source registry JSON from *registry_path*."""
    text = registry_path.read_text(encoding="utf-8")
    data = json.loads(text)
    validate_source_registry(data)
    return data


def _load_default_source_registry() -> dict[str, Any]:
    """Load the default source registry shipped with the repository."""
    path = _repo_root() / _SOURCE_REGISTRY_RELATIVE_PATH
    if not path.is_file():
        return {}
    try:
        return _load_source_registry_from_path(path)
    except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError):
        return {}


_SOURCE_REGISTRY: dict[str, Any] = _load_default_source_registry()


def get_source_registry() -> dict[str, Any]:
    """Return the currently loaded source registry (read-only snapshot)."""
    return dict(_SOURCE_REGISTRY)


def get_source_label(source_id: str, language: str, registry: dict[str, Any] | None = None) -> str:
    """Resolve a source ID to its localized display label. Returns empty string if unknown."""
    reg = registry if registry is not None else _SOURCE_REGISTRY
    sources = reg.get("sources", {}) if isinstance(reg, dict) else {}
    src_data = sources.get(source_id, {})
    if not isinstance(src_data, dict):
        return ""
    lang = str(language or "").strip().lower()
    if lang not in SUPPORTED_LANGUAGES:
        lang = "vi"
    lang_data = src_data.get(lang, {})
    if isinstance(lang_data, dict):
        label = lang_data.get("label", "")
        if label:
            return str(label)
    vi_data = src_data.get("vi", {})
    if isinstance(vi_data, dict):
        return str(vi_data.get("label", ""))
    return ""


def reload_source_registry(path: Path | None = None) -> dict[str, Any]:
    """Reload the source registry from *path* (or default) and update the cache."""
    global _SOURCE_REGISTRY
    if path is None:
        _SOURCE_REGISTRY = _load_default_source_registry()
        return dict(_SOURCE_REGISTRY)
    try:
        _SOURCE_REGISTRY = _load_source_registry_from_path(path)
    except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError):
        _SOURCE_REGISTRY = {}
    return dict(_SOURCE_REGISTRY)


# ---------------------------------------------------------------------------
# Catalog loading
# ---------------------------------------------------------------------------

def _load_catalog_from_path(catalog_path: Path) -> list[dict[str, Any]]:
    """Load and parse catalog JSON from *catalog_path*."""
    text = catalog_path.read_text(encoding="utf-8")
    data = json.loads(text)
    return list(data.get("entries", []))


def _load_default_catalog() -> list[dict[str, Any]]:
    """Load the default catalog shipped with the repository."""
    path = _repo_root() / _CATALOG_RELATIVE_PATH
    if not path.is_file():
        return []
    try:
        entries = _load_catalog_from_path(path)
        validate_catalog(entries)
        return entries
    except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError):
        return []


# Module-level cached catalog.
_CATALOG: list[dict[str, Any]] = []


def get_catalog() -> list[dict[str, Any]]:
    """Return the currently loaded catalog entries (read-only snapshot)."""
    return list(_CATALOG)


def reload_catalog(path: Path | None = None) -> list[dict[str, Any]]:
    """Reload the catalog from *path* (or the default path) and update the cache."""
    global _CATALOG
    if path is None:
        _CATALOG = _load_default_catalog()
        return list(_CATALOG)
    try:
        entries = _load_catalog_from_path(path)
        validate_catalog(entries)
        _CATALOG = entries
    except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError):
        _CATALOG = []
    return list(_CATALOG)


# ---------------------------------------------------------------------------
# Text normalization and tokenization
# ---------------------------------------------------------------------------

def _normalize_text(text: str) -> str:
    """Normalize text for matching: NFC, lowercase, strip."""
    return unicodedata.normalize("NFC", text).lower().strip()


def _strip_vietnamese_diacritics(text: str) -> str:
    """Strip Vietnamese diacritical marks for fuzzy matching.

    Converts e.g. 'tệp bị khóa' → 'tep bi khoa'.
    """
    nfkd = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    # Also handle đ/Đ which NFD doesn't decompose
    stripped = stripped.replace("đ", "d").replace("Đ", "D")
    return stripped.strip()


def _cjk_bigrams(text: str) -> set[str]:
    """Generate character bigrams from CJK runs in *text*.

    Useful for matching Japanese compound words without word boundaries.
    E.g. '基準人員' → {'基準', '準人', '人員'}
    """
    cjk_pattern = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff\u3400-\u4dbf]+")
    bigrams: set[str] = set()
    for match in cjk_pattern.finditer(text):
        run = match.group()
        for i in range(len(run) - 1):
            bigrams.add(run[i:i + 2])
    return bigrams


def _tokenize(text: str) -> set[str]:
    """Extract word tokens (≥2 chars) from text for keyword matching."""
    normalized = _normalize_text(text)
    return {t for t in re.findall(r"[\wÀ-ỹぁ-んァ-ヶ一-龯]{2,}", normalized) if t}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_catalog(
    catalog: list[dict[str, Any]] | None = None,
    source_registry: dict[str, Any] | None = None,
) -> None:
    """Validate that every entry has complete VI/EN/JA with all required fields and valid source_ref_ids.

    For schema_version >= "2.0", also validates v2 metadata fields.
    Raises ``ValueError`` on any structural or content issue.
    """
    entries = catalog if catalog is not None else _CATALOG
    if not entries:
        raise ValueError("Catalog is empty — at least one entry is required.")

    registry = source_registry if source_registry is not None else _SOURCE_REGISTRY
    if not registry or not isinstance(registry.get("sources"), dict):
        registry = _load_default_source_registry()
        if not registry or not isinstance(registry.get("sources"), dict):
            raise ValueError("Cannot validate catalog: source registry is missing or invalid.")

    valid_sources = set(registry.get("sources", {}).keys())

    seen_ids: set[str] = set()
    for idx, entry in enumerate(entries):
        entry_id = entry.get("id", "")
        if not isinstance(entry_id, str) or not entry_id.strip():
            raise ValueError(f"Entry #{idx} is missing a valid 'id'.")
        if entry_id in seen_ids:
            raise ValueError(f"Duplicate entry id: '{entry_id}'.")
        seen_ids.add(entry_id)

        # v2 metadata validation (optional for backward compat)
        status = entry.get("status")
        if status is not None:
            if status not in _VALID_STATUSES:
                raise ValueError(
                    f"Entry '{entry_id}' has invalid status '{status}'. "
                    f"Must be one of: {sorted(_VALID_STATUSES)}."
                )

        review_status = entry.get("review_status")
        if review_status is not None:
            if review_status not in _VALID_REVIEW_STATUSES:
                raise ValueError(
                    f"Entry '{entry_id}' has invalid review_status '{review_status}'. "
                    f"Must be one of: {sorted(_VALID_REVIEW_STATUSES)}."
                )

        if "source_refs" in entry:
            raise ValueError(f"Entry '{entry_id}' uses deprecated 'source_refs'; 'source_ref_ids' is required.")

        source_ref_ids = entry.get("source_ref_ids")
        if source_ref_ids is None or not isinstance(source_ref_ids, list) or not source_ref_ids:
            raise ValueError(
                f"Entry '{entry_id}' is missing required 'source_ref_ids' (must be a non-empty list)."
            )
        for ref_id in source_ref_ids:
            if not isinstance(ref_id, str) or not ref_id.strip():
                raise ValueError(f"Entry '{entry_id}' has empty/invalid source_ref_id.")
            if ref_id not in valid_sources:
                raise ValueError(f"Entry '{entry_id}' references unknown source_ref_id '{ref_id}'.")

        aliases = entry.get("aliases")
        if aliases is not None:
            if not isinstance(aliases, dict):
                raise ValueError(f"Entry '{entry_id}' aliases must be a dict.")

        for lang in SUPPORTED_LANGUAGES:
            lang_data = entry.get(lang)
            if not isinstance(lang_data, dict):
                raise ValueError(
                    f"Entry '{entry_id}' is missing language '{lang}'."
                )
            for field_name in _REQUIRED_ENTRY_FIELDS:
                value = lang_data.get(field_name)
                if field_name == "keywords":
                    if (
                        not isinstance(value, list)
                        or not value
                        or any(not isinstance(item, str) or not item.strip() for item in value)
                    ):
                        raise ValueError(
                            f"Entry '{entry_id}' [{lang}].keywords must be a non-empty list."
                        )
                elif field_name == "safe_steps":
                    if (
                        not isinstance(value, list)
                        or not value
                        or any(not isinstance(item, str) or not item.strip() for item in value)
                    ):
                        raise ValueError(
                            f"Entry '{entry_id}' [{lang}].safe_steps must be a non-empty list."
                        )
                else:
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError(
                            f"Entry '{entry_id}' [{lang}].{field_name} must be a non-empty string."
                        )

            # Check for forbidden technical tokens in user-facing fields.
            for field_name in ("title", "answer_context", "safe_steps"):
                value = lang_data.get(field_name, "")
                text = "\n".join(value) if isinstance(value, list) else str(value)
                text = text.lower()
                for token in _FORBIDDEN_TOKENS:
                    if token in text:
                        raise ValueError(
                            f"Entry '{entry_id}' [{lang}].{field_name} contains "
                            f"forbidden technical token '{token}'."
                        )


# Load the shipped catalog only after the validation function is available.
_CATALOG = _load_default_catalog()


# ---------------------------------------------------------------------------
# Hybrid retrieval engine
# ---------------------------------------------------------------------------

def _score_entry(
    entry: dict[str, Any],
    lang: str,
    normalized_question: str,
    question_tokens: set[str],
    question_unaccented: str,
    question_bigrams: set[str],
) -> tuple[int, list[str]]:
    """Score a single catalog entry against the query. Returns (score, match_reasons)."""
    entry_status = entry.get("status", "active")
    if entry_status != "active":
        return 0, []

    lang_data = entry.get(lang)
    if not isinstance(lang_data, dict):
        return 0, []

    score = 0
    reasons: list[str] = []

    keywords = lang_data.get("keywords", [])
    title = str(lang_data.get("title", ""))
    title_normalized = _normalize_text(title)

    # 1. Exact phrase match: keyword phrase found verbatim in question
    all_keywords_lower = [_normalize_text(k) for k in keywords]
    low_signal_tokens = _LOW_SIGNAL_TOKENS.get(lang, frozenset())
    for keyword_phrase in all_keywords_lower:
        keyword_tokens = _tokenize(keyword_phrase)
        meaningful_phrase = bool(keyword_tokens - low_signal_tokens)
        if keyword_phrase and meaningful_phrase and keyword_phrase in normalized_question:
            score += _SCORE_EXACT_PHRASE
            reasons.append(f"exact_phrase:{keyword_phrase}")

    # 2. Title match: title text found in question or vice versa
    if title_normalized and title_normalized in normalized_question:
        score += _SCORE_TITLE_MATCH
        reasons.append(f"title_match:{title_normalized[:30]}")
    elif title_normalized and normalized_question in title_normalized and len(normalized_question) >= 4:
        score += _SCORE_TITLE_MATCH - 1
        reasons.append(f"title_partial:{title_normalized[:30]}")

    # 3. Alias match
    aliases = entry.get("aliases", {})
    lang_aliases = aliases.get(lang, []) if isinstance(aliases, dict) else []
    for alias in lang_aliases:
        alias_normalized = _normalize_text(alias)
        if alias_normalized and alias_normalized in normalized_question:
            score += _SCORE_ALIAS_MATCH
            reasons.append(f"alias:{alias_normalized}")
            break

    # 4. Keyword token overlap
    for keyword_phrase in all_keywords_lower:
        keyword_tokens = _tokenize(keyword_phrase)
        matched = (question_tokens & keyword_tokens) - low_signal_tokens
        if matched:
            score += len(matched) * _SCORE_KEYWORD_TOKEN
            reasons.append(f"token_overlap:{','.join(sorted(matched)[:3])}")

    # 5. Vietnamese unaccented matching (only for VI queries)
    if lang == "vi" and question_unaccented:
        for keyword_phrase in all_keywords_lower:
            keyword_unaccented = _strip_vietnamese_diacritics(keyword_phrase)
            if keyword_unaccented and len(keyword_unaccented) >= 3 and keyword_unaccented in question_unaccented:
                score += _SCORE_UNACCENTED_MATCH
                reasons.append(f"unaccented:{keyword_unaccented}")
                break

    # 6. CJK bigram matching (only for JA queries)
    if lang == "ja" and question_bigrams:
        keyword_text = " ".join(all_keywords_lower) + " " + title_normalized
        entry_bigrams = _cjk_bigrams(keyword_text)
        bigram_overlap = question_bigrams & entry_bigrams
        if bigram_overlap:
            score += len(bigram_overlap) * _SCORE_CJK_BIGRAM
            reasons.append(f"cjk_bigram:{len(bigram_overlap)}hits")

    return score, reasons


def retrieve_with_trace(
    question: str,
    language: str,
    catalog: list[dict[str, Any]] | None = None,
) -> list[tuple[dict[str, Any], RetrievalTrace]]:
    """Retrieve entries with detailed trace information for testing and debugging.

    Returns a list of (result_dict, RetrievalTrace) tuples, sorted by score descending.
    Only entries meeting the minimum score threshold are returned.
    """
    lang = str(language).strip().lower() if language else "vi"
    if lang not in SUPPORTED_LANGUAGES:
        lang = "vi"

    entries = catalog if catalog is not None else _CATALOG
    if not entries:
        return []

    normalized_question = _normalize_text(question)
    question_tokens = _tokenize(normalized_question)
    question_unaccented = _strip_vietnamese_diacritics(question) if lang == "vi" else ""
    question_bigrams = _cjk_bigrams(normalized_question) if lang == "ja" else set()

    if not question_tokens and not question_bigrams:
        return []

    scored: list[tuple[int, dict[str, Any], RetrievalTrace]] = []
    for entry in entries:
        score, reasons = _score_entry(
            entry, lang, normalized_question, question_tokens,
            question_unaccented, question_bigrams,
        )

        if score < MIN_MATCH_SCORE:
            continue

        lang_data = entry.get(lang, {})
        source_ref_ids = tuple(entry.get("source_ref_ids", entry.get("source_refs", [])))
        result_item = {
            "id": entry.get("id", ""),
            "title": lang_data.get("title", ""),
            "answer_context": lang_data.get("answer_context", ""),
            "safe_steps": lang_data.get("safe_steps", []),
            "source_ref_ids": list(source_ref_ids),
            "source_refs": list(source_ref_ids),
        }
        trace = RetrievalTrace(
            entry_id=entry.get("id", ""),
            score=score,
            match_reasons=tuple(reasons),
            source_ref_ids=source_ref_ids,
        )
        scored.append((score, result_item, trace))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    # Deduplication: if two entries share >80% tokens, keep only higher-scoring
    final: list[tuple[dict[str, Any], RetrievalTrace]] = []
    seen_token_sets: list[set[str]] = []
    for _, result_item, trace in scored[:_MAX_RESULTS * 2]:  # Check more than needed for dedup
        item_tokens = _tokenize(result_item.get("title", "") + " " + result_item.get("answer_context", ""))
        is_duplicate = False
        for existing_tokens in seen_token_sets:
            if not item_tokens or not existing_tokens:
                continue
            overlap = len(item_tokens & existing_tokens)
            overlap_ratio = overlap / min(len(item_tokens), len(existing_tokens))
            if overlap_ratio > 0.8:
                is_duplicate = True
                break
        if not is_duplicate:
            final.append((result_item, trace))
            seen_token_sets.append(item_tokens)
        if len(final) >= _MAX_RESULTS:
            break

    return final


def retrieve(
    question: str,
    language: str,
    catalog: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Retrieve up to 3 matching catalog entries for *question* in *language*.

    Returns a list of dicts with keys: ``id``, ``title``, ``answer_context``,
    ``safe_steps``, ``source_ref_ids``, ``source_refs``. Each dict is in the requested language.
    Falls back to ``vi`` if *language* is unsupported.

    Only entries meeting the minimum score threshold (MIN_MATCH_SCORE) are returned
    to avoid off-topic context being sent to Gemini.
    """
    traced = retrieve_with_trace(question, language, catalog)
    return [item for item, _trace in traced]


# ---------------------------------------------------------------------------
# Context formatting
# ---------------------------------------------------------------------------

def format_curated_context(
    results: list[dict[str, Any]],
    language: str,
    registry: dict[str, Any] | None = None,
) -> str:
    """Format retrieved entries into a plain-text context string for the Gemini prompt.

    Includes honest, localized source attribution using the source registry.
    Returns a compact summary suitable for injecting into the LLM prompt.
    """
    if not results:
        return ""

    lang = str(language).strip().lower() if language else "vi"
    if lang not in SUPPORTED_LANGUAGES:
        lang = "vi"

    source_prefix = {
        "vi": "Nguồn",
        "en": "Source",
        "ja": "参照",
    }.get(lang, "Source")

    parts: list[str] = []
    for item in results:
        title = item.get("title", "")
        context = item.get("answer_context", "")
        steps = item.get("safe_steps", [])
        source_ref_ids = item.get("source_ref_ids", item.get("source_refs", []))

        labels: list[str] = []
        for s_id in source_ref_ids:
            lbl = get_source_label(s_id, lang, registry)
            if lbl:
                labels.append(lbl)

        steps_text = " ".join(f"({i + 1}) {s}" for i, s in enumerate(steps))
        source_text = f" ({source_prefix}: {', '.join(labels)})" if labels else ""
        parts.append(f"{title}{source_text}: {context} {steps_text}")

    return "\n".join(parts)[:1000]


# ---------------------------------------------------------------------------
# Local fallback
# ---------------------------------------------------------------------------

def local_fallback(
    question: str,
    language: str,
    registry: dict[str, Any] | None = None,
    *,
    intent: str | None = None,
) -> str:
    """Return a local fallback answer from the curated catalog when Gemini is offline.

    Retrieves the best-matching entry and formats it as a user-friendly answer
    in the requested language. When no result meets the score threshold, returns
    a message directing the user to rephrase in simpler business language.
    """
    lang = str(language).strip().lower() if language else "vi"
    if lang not in SUPPORTED_LANGUAGES:
        lang = "vi"

    if intent == "clarify":
        clarify_msg = {
            "vi": "Bạn đang cần hỏi về số lượng nhóm chi phí hay số dòng chi phí cụ thể, cho năm tài chính (FY) và trung tâm chi phí (cost center) nào?",
            "en": "Are you asking about the number of cost categories or specific cost line items, and for which fiscal year (FY) and cost center?",
            "ja": "費用の分類項目数ですか、それとも具体的な明細行数ですか？対象の会計年度（FY）とコストセンターをお知らせください。",
        }
        return clarify_msg.get(lang, clarify_msg["vi"])

    if intent == "incident":
        incident_no_match = {
            "vi": (
                "Chưa tìm thấy thông tin sự cố phù hợp với mô tả này.\n"
                "Vui lòng kiểm tra lại thông báo lỗi cụ thể trên màn hình, xem chi tiết trong \"Lịch sử lần chạy\", "
                "hoặc chọn lần chạy bị lỗi để được phân tích."
            ),
            "en": (
                "No matching incident information was found for this description.\n"
                "Please check the specific on-screen error message, inspect \"Run History\", "
                "or select the failed run for diagnosis."
            ),
            "ja": (
                "この内容に該当する障害情報が見つかりませんでした。\n"
                "画面上に表示されたエラーメッセージを確認するか、「実行履歴」で対象のエラー実行を選択して診断してください。"
            ),
        }
        return incident_no_match.get(lang, incident_no_match["vi"])

    results = retrieve(question, lang)
    if not results:
        # Return a clear "no match" message directing user to rephrase
        no_match = {
            "vi": (
                "Chưa tìm thấy hướng dẫn nội bộ phù hợp với câu hỏi này.\n"
                "Vui lòng thử hỏi lại bằng từ ngữ nghiệp vụ đơn giản hơn, "
                "ví dụ: \"phân bổ chi phí chung và riêng thế nào\", \"nhập dữ liệu nhân sự ở đâu\", "
                "hoặc nêu rõ năm tài chính và trung tâm chi phí cần hỏi."
            ),
            "en": (
                "No matching internal guidance was found for this question.\n"
                "Please try rephrasing using simpler business terms, "
                "e.g. \"how are common and special costs allocated?\", \"where do I enter staffing data?\", "
                "or specify the fiscal year and cost center."
            ),
            "ja": (
                "この質問に該当する社内ガイダンスが見つかりませんでした。\n"
                "よりシンプルな業務用語で質問し直してください。"
                "例：「共通費と個別費はどう配賦しますか」「人員データはどこに入力しますか」、"
                "または対象の年度とコストセンターを指定してください。"
            ),
        }
        return no_match.get(lang, no_match["vi"])

    best = results[0]
    title = best.get("title", "")
    context = best.get("answer_context", "")
    steps = best.get("safe_steps", [])
    source_ref_ids = best.get("source_ref_ids", best.get("source_refs", []))

    header = {
        "vi": "Hướng dẫn nội bộ",
        "en": "Internal Guidance",
        "ja": "社内ガイダンス",
    }.get(lang, "Hướng dẫn nội bộ")

    labels: list[str] = []
    for s_id in source_ref_ids:
        lbl = get_source_label(s_id, lang, registry)
        if lbl:
            labels.append(lbl)

    source_label = ""
    if labels:
        source_label = {
            "vi": f" (Nguồn: {', '.join(labels)})",
            "en": f" (Source: {', '.join(labels)})",
            "ja": f" (参照: {', '.join(labels)})",
        }.get(lang, f" ({', '.join(labels)})")

    lines: list[str] = [f"📋 {header}: {title}{source_label}", "", context, ""]
    for i, step in enumerate(steps, 1):
        lines.append(f"{i}. {step}")

    return "\n".join(lines)
