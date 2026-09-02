"""Tests for the curated multilingual business chat knowledge service (v2).

Covers:
- Catalog has all entries with complete VI/EN/JA translations
- v2 schema: status, review_status, source_refs, aliases validated
- Equivalent questions in VI/EN/JA retrieve the same knowledge id
- Japanese fallback is in Japanese
- No technical jargon in catalog content
- Retrieve returns max 3 items
- Missing language falls back to Vietnamese
- Catalog validation catches structural errors
- local_fallback returns correct language when Gemini is offline
- local_fallback directs user to rephrase on no match
- Catalog drift checker finds no drift against review docs
"""

from __future__ import annotations

import json
from pathlib import Path

from src.services.business_chat_knowledge import (
    MIN_MATCH_SCORE,
    SUPPORTED_LANGUAGES,
    _FORBIDDEN_TOKENS,
    _MAX_RESULTS,
    format_curated_context,
    get_catalog,
    local_fallback,
    retrieve,
    retrieve_with_trace,
    validate_catalog,
)


# ---------------------------------------------------------------------------
# Catalog structure tests
# ---------------------------------------------------------------------------

def test_catalog_is_not_empty() -> None:
    catalog = get_catalog()
    assert len(catalog) >= 8, f"Catalog must have at least 8 entries, got {len(catalog)}"


def test_catalog_has_all_three_languages_for_every_entry() -> None:
    catalog = get_catalog()
    for entry in catalog:
        entry_id = entry.get("id", "<no id>")
        for lang in SUPPORTED_LANGUAGES:
            assert lang in entry, f"Entry '{entry_id}' missing language '{lang}'"
            lang_data = entry[lang]
            assert isinstance(lang_data.get("title"), str) and lang_data["title"].strip(), \
                f"Entry '{entry_id}' [{lang}].title is empty"
            assert isinstance(lang_data.get("keywords"), list) and lang_data["keywords"], \
                f"Entry '{entry_id}' [{lang}].keywords is empty"
            assert isinstance(lang_data.get("answer_context"), str) and lang_data["answer_context"].strip(), \
                f"Entry '{entry_id}' [{lang}].answer_context is empty"
            assert isinstance(lang_data.get("safe_steps"), list) and lang_data["safe_steps"], \
                f"Entry '{entry_id}' [{lang}].safe_steps is empty"


def test_catalog_validates_successfully() -> None:
    """validate_catalog() must pass without raising for the shipped catalog."""
    validate_catalog()


def test_catalog_has_no_technical_jargon() -> None:
    """Catalog content must not contain forbidden technical tokens."""
    catalog = get_catalog()
    for entry in catalog:
        entry_id = entry.get("id", "<no id>")
        for lang in SUPPORTED_LANGUAGES:
            lang_data = entry.get(lang, {})
            for field in ("title", "answer_context"):
                text = str(lang_data.get(field, "")).lower()
                for token in _FORBIDDEN_TOKENS:
                    assert token not in text, \
                        f"Entry '{entry_id}' [{lang}].{field} contains forbidden token '{token}'"


# ---------------------------------------------------------------------------
# v2 schema tests
# ---------------------------------------------------------------------------

def test_catalog_schema_version_is_2() -> None:
    """The shipped catalog must be schema_version 2.0."""
    repo_root = Path(__file__).resolve().parents[2]
    catalog_path = repo_root / "docs" / "knowledge" / "business_chat" / "knowledge_catalog.json"
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert data.get("schema_version") == "2.0", \
        f"Expected schema_version '2.0', got '{data.get('schema_version')}'"


def test_all_entries_have_v2_metadata() -> None:
    """Every entry must have status, review_status, source_ref_ids."""
    from src.services.business_chat_knowledge import get_source_registry

    catalog = get_catalog()
    registry = get_source_registry()
    valid_sources = set(registry.get("sources", {}).keys())

    for entry in catalog:
        entry_id = entry.get("id", "<no id>")
        assert "status" in entry, f"Entry '{entry_id}' missing 'status'"
        assert "review_status" in entry, f"Entry '{entry_id}' missing 'review_status'"
        assert "source_ref_ids" in entry, f"Entry '{entry_id}' missing 'source_ref_ids'"
        assert entry["status"] in ("active", "deprecated"), \
            f"Entry '{entry_id}' has invalid status '{entry['status']}'"
        assert entry["review_status"] in ("approved", "pending", "draft"), \
            f"Entry '{entry_id}' has invalid review_status '{entry['review_status']}'"
        assert isinstance(entry["source_ref_ids"], list), \
            f"Entry '{entry_id}' source_ref_ids must be a list"
        assert len(entry["source_ref_ids"]) > 0, \
            f"Entry '{entry_id}' source_ref_ids must have at least one ref"
        for s_id in entry["source_ref_ids"]:
            assert s_id in valid_sources, \
                f"Entry '{entry_id}' references unapproved source ID '{s_id}'"


def test_all_entries_have_aliases() -> None:
    """Every entry must have aliases dict."""
    catalog = get_catalog()
    for entry in catalog:
        entry_id = entry.get("id", "<no id>")
        assert "aliases" in entry, f"Entry '{entry_id}' missing 'aliases'"
        assert isinstance(entry["aliases"], dict), \
            f"Entry '{entry_id}' aliases must be a dict"


# ---------------------------------------------------------------------------
# Retrieval tests
# ---------------------------------------------------------------------------

def test_equivalent_questions_in_three_languages_retrieve_same_id() -> None:
    """Questions about the same topic in VI/EN/JA should retrieve the same knowledge id."""
    vi_results = retrieve("file bị khóa không ghi được", "vi")
    en_results = retrieve("file locked cannot save", "en")
    ja_results = retrieve("ファイルロック 保存できない", "ja")

    assert vi_results, "VI query for locked file should return results"
    assert en_results, "EN query for locked file should return results"
    assert ja_results, "JA query for locked file should return results"

    vi_id = vi_results[0]["id"]
    en_id = en_results[0]["id"]
    ja_id = ja_results[0]["id"]

    assert vi_id == en_id == ja_id, \
        f"Same topic should return same id across languages: vi={vi_id}, en={en_id}, ja={ja_id}"


def test_equivalent_questions_baseline_same_id() -> None:
    """Baseline headcount questions in all languages should resolve to the same entry."""
    vi_results = retrieve("thiếu dữ liệu nhân sự mốc tháng 3", "vi")
    en_results = retrieve("missing baseline headcount march", "en")
    ja_results = retrieve("基準 人員 不足", "ja")

    assert vi_results and en_results and ja_results
    assert vi_results[0]["id"] == en_results[0]["id"] == ja_results[0]["id"]


def test_japanese_question_without_spaces_matches_catalog_phrase() -> None:
    """Natural Japanese questions must not require artificial spaces to retrieve guidance."""
    results = retrieve("3月の基準人員データが不足しています", "ja")
    assert results
    assert results[0]["id"] == "bck_missing_baseline"


# ---------------------------------------------------------------------------
# Fallback tests
# ---------------------------------------------------------------------------

def test_japanese_fallback_is_in_japanese() -> None:
    """When Gemini is offline, Japanese users should get a Japanese local fallback."""
    answer = local_fallback("ファイルロック", "ja")
    assert answer, "Japanese fallback should not be empty"
    import re
    assert re.search(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]", answer), \
        f"Japanese fallback must contain Japanese text, got: {answer}"
    assert "承認済みMP2027業務ガイダンス" in answer


def test_vietnamese_fallback_is_in_vietnamese() -> None:
    """Vietnamese offline fallback should be in Vietnamese."""
    answer = local_fallback("file bị khóa", "vi")
    assert answer, "Vietnamese fallback should not be empty"
    assert any(c in answer for c in "ảấáàạẳắăặẵ"), \
        f"Vietnamese fallback must contain Vietnamese text"
    assert "Hướng dẫn nghiệp vụ MP2027 đã duyệt" in answer


def test_english_fallback_is_in_english() -> None:
    """English offline fallback should be in English."""
    answer = local_fallback("locked file", "en")
    assert answer, "English fallback should not be empty"
    assert any(word in answer.lower() for word in ("close", "click", "file", "output")), \
        f"English fallback must contain English guidance"
    assert "Approved MP2027 business guidance" in answer


def test_local_fallback_no_match_directs_user_to_rephrase() -> None:
    """When no entry matches, the message should direct user to rephrase in business terms."""
    vi_msg = local_fallback("xyzzyplugh", "vi")
    en_msg = local_fallback("xyzzyplugh", "en")
    ja_msg = local_fallback("xyzzyplugh", "ja")

    assert "thử hỏi lại" in vi_msg.lower() or "nghiệp vụ" in vi_msg.lower(), \
        f"VI no-match should direct user to rephrase: {vi_msg}"
    assert "rephras" in en_msg.lower() or "simpler" in en_msg.lower(), \
        f"EN no-match should direct user to rephrase: {en_msg}"
    assert "質問し直し" in ja_msg or "シンプル" in ja_msg or "質問" in ja_msg, \
        f"JA no-match should direct user to rephrase: {ja_msg}"


def test_local_fallback_respects_explicit_intent() -> None:
    clarify = local_fallback("MP có bao nhiêu chi phí?", "vi", intent="clarify")
    assert "số lượng nhóm chi phí hay số dòng chi phí" in clarify
    assert "lỗi" not in clarify.lower()

    incident = local_fallback("Calculation stopped", "en", intent="incident")
    assert "No matching incident information was found" in incident
    assert "Run History" in incident


def test_local_fallback_does_not_contain_invented_source_names() -> None:
    """Local fallback must never contain fake agent-invented manual titles."""
    for query, lang in [("file bị khóa", "vi"), ("locked file", "en"), ("ファイルロック", "ja")]:
        answer = local_fallback(query, lang)
        for forbidden in ("Operations Manual", "Preflight Check Guide", "Data Entry Handbook", "Staffing Data Entry Handbook"):
            assert forbidden not in answer, f"Found invented manual name '{forbidden}' in fallback: {answer}"


# ---------------------------------------------------------------------------
# Retrieval limits and edge cases
# ---------------------------------------------------------------------------

def test_retrieve_returns_at_most_3_results() -> None:
    results = retrieve("chi phí nhân sự tệp nguồn Excel tính toán phòng ban năm", "vi")
    assert len(results) <= _MAX_RESULTS, \
        f"retrieve() must return at most {_MAX_RESULTS} results, got {len(results)}"


def test_retrieve_returns_empty_for_unrelated_query() -> None:
    results = retrieve("quantum physics black hole entropy", "en")
    assert results == [], "Unrelated query should return empty list"


def test_retrieve_returns_empty_for_empty_query() -> None:
    results = retrieve("", "vi")
    assert results == [], "Empty query should return empty list"


def test_retrieve_falls_back_to_vietnamese_for_unsupported_language() -> None:
    results = retrieve("file bị khóa", "fr")
    assert isinstance(results, list)


# ---------------------------------------------------------------------------
# Context formatting
# ---------------------------------------------------------------------------

def test_format_curated_context_produces_compact_text() -> None:
    results = retrieve("file bị khóa", "vi")
    context = format_curated_context(results, "vi")
    assert isinstance(context, str)
    assert len(context) <= 1000
    assert "khóa" in context.lower() or "kết quả" in context.lower()


def test_format_curated_context_empty_results() -> None:
    context = format_curated_context([], "vi")
    assert context == ""


def test_format_curated_context_includes_localized_source_attribution() -> None:
    """Formatted context must include localized approved source attribution."""
    en_results = retrieve("locked file", "en")
    assert en_results
    en_context = format_curated_context(en_results, "en")
    assert "Source: Approved MP2027 business guidance" in en_context

    vi_results = retrieve("file bị khóa", "vi")
    assert vi_results
    vi_context = format_curated_context(vi_results, "vi")
    assert "Nguồn: Hướng dẫn nghiệp vụ MP2027 đã duyệt" in vi_context

    ja_results = retrieve("ファイルロック", "ja")
    assert ja_results
    ja_context = format_curated_context(ja_results, "ja")
    assert "参照: 承認済みMP2027業務ガイダンス" in ja_context


def test_format_curated_context_never_contains_invented_manual_names() -> None:
    """Formatted context sent to Gemini must not contain old invented names."""
    results = retrieve("locked file", "en")
    context = format_curated_context(results, "en")
    for forbidden in ("Operations Manual", "Preflight Check Guide", "Data Entry Handbook", "Staffing Data Entry Handbook"):
        assert forbidden not in context, f"Found invented manual name in Gemini context: {context}"


# ---------------------------------------------------------------------------
# Source registry and validation edge cases
# ---------------------------------------------------------------------------

def test_source_registry_schema_and_sources() -> None:
    """Source registry must be well-formed and contain approved_business_guidance."""
    from src.services.business_chat_knowledge import get_source_registry

    reg = get_source_registry()
    assert reg.get("schema_version") == "1.0"
    sources = reg.get("sources", {})
    assert "approved_business_guidance" in sources
    abg = sources["approved_business_guidance"]
    assert abg.get("status") == "active"
    assert abg.get("vi", {}).get("label") == "Hướng dẫn nghiệp vụ MP2027 đã duyệt"
    assert abg.get("en", {}).get("label") == "Approved MP2027 business guidance"
    assert abg.get("ja", {}).get("label") == "承認済みMP2027業務ガイダンス"


def test_validate_catalog_rejects_unknown_source_id() -> None:
    """Catalog validation must fail closed when an entry references an unregistered source."""
    bad_catalog = [{
        "id": "test_invalid_source",
        "status": "active",
        "review_status": "approved",
        "source_ref_ids": ["non_existent_source_id"],
        "vi": {"title": "ok", "keywords": ["x"], "answer_context": "ok", "safe_steps": ["ok"]},
        "en": {"title": "ok", "keywords": ["x"], "answer_context": "ok", "safe_steps": ["ok"]},
        "ja": {"title": "ok", "keywords": ["x"], "answer_context": "ok", "safe_steps": ["ok"]},
    }]
    try:
        validate_catalog(bad_catalog)
        assert False, "Should have raised ValueError for unknown source ID"
    except ValueError as exc:
        assert "non_existent_source_id" in str(exc)


def test_validate_catalog_rejects_deprecated_source_refs() -> None:
    """Catalog validation must reject legacy source_refs without source_ref_ids."""
    legacy_catalog = [{
        "id": "test_legacy_source",
        "status": "active",
        "review_status": "approved",
        "source_refs": ["Operations Manual §1"],
        "vi": {"title": "ok", "keywords": ["x"], "answer_context": "ok", "safe_steps": ["ok"]},
        "en": {"title": "ok", "keywords": ["x"], "answer_context": "ok", "safe_steps": ["ok"]},
        "ja": {"title": "ok", "keywords": ["x"], "answer_context": "ok", "safe_steps": ["ok"]},
    }]
    try:
        validate_catalog(legacy_catalog)
        assert False, "Should have raised ValueError for legacy source_refs"
    except ValueError as exc:
        assert "source_ref_ids" in str(exc).lower()


def test_validate_catalog_rejects_entry_missing_source_ref_ids() -> None:
    """Entry with complete 3-language translations but missing source_ref_ids must be rejected."""
    bad_catalog = [{
        "id": "test_missing_source_ref_ids",
        "status": "active",
        "review_status": "approved",
        "vi": {"title": "Tiêu đề", "keywords": ["k"], "answer_context": "Nội dung", "safe_steps": ["Bước 1"]},
        "en": {"title": "Title", "keywords": ["k"], "answer_context": "Context", "safe_steps": ["Step 1"]},
        "ja": {"title": "タイトル", "keywords": ["k"], "answer_context": "コンテキスト", "safe_steps": ["ステップ1"]},
    }]
    try:
        validate_catalog(bad_catalog)
        assert False, "Should have raised ValueError for missing source_ref_ids"
    except ValueError as exc:
        assert "source_ref_ids" in str(exc).lower()


def test_validate_catalog_catches_missing_language() -> None:
    bad_catalog = [{
        "id": "test_bad",
        "source_ref_ids": ["approved_business_guidance"],
        "vi": {"title": "x", "keywords": ["x"], "answer_context": "x", "safe_steps": ["x"]},
    }]
    try:
        validate_catalog(bad_catalog)
        assert False, "Should have raised ValueError for missing en/ja"
    except ValueError as exc:
        assert "missing language" in str(exc).lower() or "en" in str(exc) or "ja" in str(exc)


def test_validate_catalog_catches_empty_title() -> None:
    bad_catalog = [{
        "id": "test_empty_title",
        "source_ref_ids": ["approved_business_guidance"],
        "vi": {"title": "", "keywords": ["x"], "answer_context": "x", "safe_steps": ["x"]},
        "en": {"title": "ok", "keywords": ["x"], "answer_context": "x", "safe_steps": ["x"]},
        "ja": {"title": "ok", "keywords": ["x"], "answer_context": "x", "safe_steps": ["x"]},
    }]
    try:
        validate_catalog(bad_catalog)
        assert False, "Should have raised ValueError for empty title"
    except ValueError as exc:
        assert "title" in str(exc).lower()


def test_validate_catalog_catches_forbidden_token() -> None:
    bad_catalog = [{
        "id": "test_tech",
        "source_ref_ids": ["approved_business_guidance"],
        "vi": {"title": "Traceback error", "keywords": ["x"], "answer_context": "x", "safe_steps": ["x"]},
        "en": {"title": "ok", "keywords": ["x"], "answer_context": "x", "safe_steps": ["x"]},
        "ja": {"title": "ok", "keywords": ["x"], "answer_context": "x", "safe_steps": ["x"]},
    }]
    try:
        validate_catalog(bad_catalog)
        assert False, "Should have raised ValueError for forbidden token"
    except ValueError as exc:
        assert "traceback" in str(exc).lower()


def test_validate_catalog_rejects_technical_jargon_in_a_user_step() -> None:
    bad_catalog = [{
        "id": "test_technical_step",
        "source_ref_ids": ["approved_business_guidance"],
        "vi": {"title": "ok", "keywords": ["x"], "answer_context": "ok", "safe_steps": ["Mở JSON"]},
        "en": {"title": "ok", "keywords": ["x"], "answer_context": "ok", "safe_steps": ["Open the file"]},
        "ja": {"title": "ok", "keywords": ["x"], "answer_context": "ok", "safe_steps": ["ファイルを開く"]},
    }]
    try:
        validate_catalog(bad_catalog)
        assert False, "Should have raised ValueError for jargon in safe_steps"
    except ValueError as exc:
        assert "json" in str(exc).lower()


def test_validate_catalog_catches_invalid_status() -> None:
    """v2: invalid status value should be caught."""
    bad_catalog = [{
        "id": "test_status",
        "status": "deleted",
        "source_ref_ids": ["approved_business_guidance"],
        "vi": {"title": "ok", "keywords": ["x"], "answer_context": "ok", "safe_steps": ["ok"]},
        "en": {"title": "ok", "keywords": ["x"], "answer_context": "ok", "safe_steps": ["ok"]},
        "ja": {"title": "ok", "keywords": ["x"], "answer_context": "ok", "safe_steps": ["ok"]},
    }]
    try:
        validate_catalog(bad_catalog)
        assert False, "Should have raised ValueError for invalid status"
    except ValueError as exc:
        assert "status" in str(exc).lower()


def test_validate_catalog_catches_invalid_review_status() -> None:
    """v2: invalid review_status should be caught."""
    bad_catalog = [{
        "id": "test_review",
        "status": "active",
        "review_status": "rejected",
        "source_ref_ids": ["approved_business_guidance"],
        "vi": {"title": "ok", "keywords": ["x"], "answer_context": "ok", "safe_steps": ["ok"]},
        "en": {"title": "ok", "keywords": ["x"], "answer_context": "ok", "safe_steps": ["ok"]},
        "ja": {"title": "ok", "keywords": ["x"], "answer_context": "ok", "safe_steps": ["ok"]},
    }]
    try:
        validate_catalog(bad_catalog)
        assert False, "Should have raised ValueError for invalid review_status"
    except ValueError as exc:
        assert "review_status" in str(exc).lower()


def test_reload_catalog_fails_closed_when_catalog_is_invalid(tmp_path: Path) -> None:
    """Malformed catalog content must clear the runtime cache instead of being used."""
    from src.services.business_chat_knowledge import reload_catalog

    invalid_catalog = tmp_path / "invalid_catalog.json"
    invalid_catalog.write_text(
        json.dumps({"entries": [{"id": "missing_languages"}]}),
        encoding="utf-8",
    )
    try:
        assert reload_catalog(invalid_catalog) == []
    finally:
        reload_catalog()


# ---------------------------------------------------------------------------
# On-disk catalog tests
# ---------------------------------------------------------------------------

def test_catalog_json_is_valid_utf8() -> None:
    """The on-disk catalog file must be valid UTF-8 JSON."""
    repo_root = Path(__file__).resolve().parents[2]
    catalog_path = repo_root / "docs" / "knowledge" / "business_chat" / "knowledge_catalog.json"
    assert catalog_path.is_file(), f"Catalog file not found: {catalog_path}"
    text = catalog_path.read_text(encoding="utf-8")
    data = json.loads(text)
    assert "entries" in data
    assert len(data["entries"]) >= 8


def test_catalog_entry_ids_are_stable_and_unique() -> None:
    catalog = get_catalog()
    ids = [e["id"] for e in catalog]
    assert len(ids) == len(set(ids)), "Entry ids must be unique"
    for entry_id in ids:
        assert entry_id.startswith("bck_"), f"Entry id '{entry_id}' should start with 'bck_'"


# ---------------------------------------------------------------------------
# Drift checker tests
# ---------------------------------------------------------------------------

def test_catalog_review_docs_have_no_drift() -> None:
    """Review docs (vi.md, en.md, ja.md) must be consistent with the catalog."""
    from src.services.catalog_review_sync import check_catalog_review_drift

    repo_root = Path(__file__).resolve().parents[2]
    catalog_path = repo_root / "docs" / "knowledge" / "business_chat" / "knowledge_catalog.json"
    review_dir = repo_root / "docs" / "knowledge" / "business_chat"

    issues = check_catalog_review_drift(catalog_path, review_dir)
    if issues:
        detail = "\n".join(f"  [{i.language}] {i.kind}: {i.detail}" for i in issues)
        assert False, f"Catalog ↔ review doc drift detected:\n{detail}"


def test_drift_checker_detects_invalid_source_id(tmp_path: Path) -> None:
    """Drift checker must flag unknown source IDs in catalog."""
    from src.services.catalog_review_sync import check_catalog_review_drift

    reg_file = tmp_path / "source_registry.json"
    reg_file.write_text(json.dumps({
        "schema_version": "1.0",
        "sources": {"approved_business_guidance": {"status": "active", "vi": {"label": "L"}, "en": {"label": "L"}, "ja": {"label": "L"}}}
    }), encoding="utf-8")

    cat_file = tmp_path / "knowledge_catalog.json"
    cat_file.write_text(json.dumps({
        "schema_version": "2.0",
        "entries": [{
            "id": "bck_test",
            "status": "active",
            "source_ref_ids": ["bogus_source_id"],
            "vi": {"title": "T"}, "en": {"title": "T"}, "ja": {"title": "T"}
        }]
    }), encoding="utf-8")

    issues = check_catalog_review_drift(cat_file, tmp_path, reg_file)
    assert any(i.kind == "invalid_source_id" for i in issues)


def test_rag_v3_boundary_isolation_and_security():
    """Verify that generic chat context never leaks paths, packets, or developer traces."""
    from src.services.business_knowledge_retrieval import format_grounded_context, retrieve_grounded_chunks

    chunks = retrieve_grounded_chunks("file bị khóa", "vi", top_k=3)
    assert len(chunks) > 0
    formatted = format_grounded_context(chunks, "vi")

    forbidden_signals = ["d:\\", "c:\\", "traceback", "selected_run", "case_packet", "token", "password", "pipeline_stage"]
    for sig in forbidden_signals:
        assert sig not in formatted.lower(), f"Context leaked forbidden signal '{sig}': {formatted}"


def test_rag_v3_unapproved_sources_rejected_from_context():
    """Chunks from review_required or unshareable sources must not be in production index."""
    from src.services.business_knowledge_index import get_knowledge_index

    chunks = get_knowledge_index()
    for chunk in chunks:
        assert chunk.external_shareable is True, f"Chunk {chunk.chunk_id} has external_shareable=False"
        assert chunk.authority in ("canonical", "supporting", "caveat", "reference_with_caveat"), f"Chunk {chunk.chunk_id} has invalid authority"
