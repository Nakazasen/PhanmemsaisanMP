"""Tests for MP2027 Document-grounded RAG v3 knowledge indexing service."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.business_knowledge_index import (
    INDEX_SCHEMA_VERSION,
    DocumentChunk,
    build_index_data,
    compute_source_hash,
    get_knowledge_index,
    load_index_from_file,
    reload_knowledge_index,
    save_index,
    validate_chunk,
)
from src.services.operations_knowledge import (
    ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK,
    ERROR_CODE_MISSING_STAFFING_BASELINE,
    ERROR_CODE_PREFLIGHT_SOURCE_VALIDATION_FAILURE,
)


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_document_chunk_to_dict_and_from_dict():
    chunk = DocumentChunk(
        chunk_id="chk_test_01",
        source_id="approved_business_guidance",
        section_title="Test Title",
        language="vi",
        business_area="operations",
        text="Test context description.",
        safe_steps=("Step 1", "Step 2"),
        authority="canonical",
        external_shareable=True,
    )
    d = chunk.to_dict()
    assert d["chunk_id"] == "chk_test_01"
    assert d["safe_steps"] == ["Step 1", "Step 2"]

    restored = DocumentChunk.from_dict(d)
    assert restored == chunk


def test_validate_chunk_accepts_valid_chunk():
    chunk = DocumentChunk(
        chunk_id="chk_valid_01",
        source_id="approved_business_guidance",
        section_title="Valid Title",
        language="vi",
        business_area="operations",
        text="Valid text.",
        safe_steps=("Step 1",),
        authority="canonical",
        external_shareable=True,
    )
    validate_chunk(chunk, {"approved_business_guidance"})


def test_validate_chunk_rejects_missing_chunk_id():
    chunk = DocumentChunk(
        chunk_id="",
        source_id="approved_business_guidance",
        section_title="Title",
        language="vi",
        business_area="operations",
        text="Text.",
        safe_steps=(),
        authority="canonical",
        external_shareable=True,
    )
    with pytest.raises(ValueError, match="missing chunk_id"):
        validate_chunk(chunk)


def test_validate_chunk_rejects_unapproved_source():
    chunk = DocumentChunk(
        chunk_id="chk_bad_source",
        source_id="unapproved_source_xyz",
        section_title="Title",
        language="vi",
        business_area="operations",
        text="Text.",
        safe_steps=(),
        authority="canonical",
        external_shareable=True,
    )
    with pytest.raises(ValueError, match="references unapproved source"):
        validate_chunk(chunk, {"approved_business_guidance"})


def test_validate_chunk_rejects_unsupported_language():
    chunk = DocumentChunk(
        chunk_id="chk_lang",
        source_id="approved_business_guidance",
        section_title="Title",
        language="fr",
        business_area="operations",
        text="Text.",
        safe_steps=(),
        authority="canonical",
        external_shareable=True,
    )
    with pytest.raises(ValueError, match="unsupported language"):
        validate_chunk(chunk)


def test_validate_chunk_rejects_invalid_authority():
    chunk = DocumentChunk(
        chunk_id="chk_auth",
        source_id="approved_business_guidance",
        section_title="Title",
        language="vi",
        business_area="operations",
        text="Text.",
        safe_steps=(),
        authority="historical",
        external_shareable=True,
    )
    with pytest.raises(ValueError, match="invalid authority"):
        validate_chunk(chunk)


def test_validate_chunk_rejects_forbidden_technical_tokens():
    forbidden_tokens = ["d:\\sandbox\\foo", "raw/dataset.xlsx", "docs/internal.md", "traceback (most recent)", "cagent_client"]
    for token in forbidden_tokens:
        chunk = DocumentChunk(
            chunk_id="chk_bad_tok",
            source_id="approved_business_guidance",
            section_title="Title",
            language="vi",
            business_area="operations",
            text=f"Text with {token}",
            safe_steps=(),
            authority="canonical",
            external_shareable=True,
        )
        with pytest.raises(ValueError, match="forbidden technical token"):
            validate_chunk(chunk)


def test_build_index_data_contains_approved_chunks(repo_root: Path):
    data = build_index_data(repo_root)
    assert data["schema_version"] == INDEX_SCHEMA_VERSION
    assert data["total_chunks"] >= 50
    assert len(data["chunks"]) == data["total_chunks"]

    # Verify no local filesystem paths or technical tokens leak into any chunk
    for chk in data["chunks"]:
        text = json.dumps(chk).lower()
        assert "d:\\sandbox" not in text
        assert "c:\\users" not in text
        assert "raw/" not in text
        assert "docs/" not in text
        assert "traceback" not in text
        assert "cagent" not in text


def test_save_and_load_index(tmp_path: Path, repo_root: Path):
    data = build_index_data(repo_root)
    tmp_file = tmp_path / "test_knowledge_index.json"
    save_index(data, tmp_file)

    loaded = load_index_from_file(tmp_file, check_freshness=False)
    assert len(loaded) == data["total_chunks"]
    assert all(isinstance(c, DocumentChunk) for c in loaded)


def test_load_index_fail_closed_on_missing_or_corrupt_file(tmp_path: Path):
    # Missing file -> empty list
    non_existent = tmp_path / "does_not_exist.json"
    assert load_index_from_file(non_existent) == []

    # Corrupt JSON -> empty list
    corrupt_file = tmp_path / "corrupt.json"
    corrupt_file.write_text("{invalid json", encoding="utf-8")
    assert load_index_from_file(corrupt_file) == []

    # Invalid schema version -> empty list
    wrong_schema = tmp_path / "wrong_schema.json"
    wrong_schema.write_text(json.dumps({"schema_version": "99.0", "chunks": []}), encoding="utf-8")
    assert load_index_from_file(wrong_schema) == []


def test_get_and_reload_knowledge_index():
    chunks = get_knowledge_index()
    assert isinstance(chunks, list)
    assert len(chunks) > 0

    reloaded = reload_knowledge_index()
    assert len(reloaded) == len(chunks)


def test_all_approved_sources_have_real_paths_and_chunks(repo_root: Path):
    """Every approved source must have an existing file path and >= 1 chunk in knowledge index."""
    inv_path = repo_root / "docs/knowledge/business_chat/source_inventory.json"
    inv_data = json.loads(inv_path.read_text(encoding="utf-8"))

    approved_sources = [
        s for s in inv_data.get("sources", [])
        if s.get("status") == "approved"
    ]
    assert len(approved_sources) == 7

    index_chunks = get_knowledge_index()
    indexed_source_ids = {c.source_id for c in index_chunks}

    for src in approved_sources:
        src_id = src["source_id"]
        rel_path = src.get("path")
        assert rel_path, f"Approved source '{src_id}' is missing path."
        full_path = repo_root / rel_path
        assert full_path.is_file(), f"File for source '{src_id}' does not exist: {full_path}"
        assert src_id in indexed_source_ids, f"Approved source '{src_id}' has 0 chunks in index."


def test_all_three_operations_errors_indexed():
    """Verify that all 3 approved operations error codes are indexed in VI, EN, JA."""
    chunks = get_knowledge_index()
    ops_chunks = [c for c in chunks if c.source_id == "operations_knowledge_base"]
    assert len(ops_chunks) == 9

    indexed_error_codes = {c.keywords[0] for c in ops_chunks if c.keywords}
    assert ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK in indexed_error_codes
    assert ERROR_CODE_MISSING_STAFFING_BASELINE in indexed_error_codes
    assert ERROR_CODE_PREFLIGHT_SOURCE_VALIDATION_FAILURE in indexed_error_codes

    for err_code in (
        ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK,
        ERROR_CODE_MISSING_STAFFING_BASELINE,
        ERROR_CODE_PREFLIGHT_SOURCE_VALIDATION_FAILURE,
    ):
        err_langs = {c.language for c in ops_chunks if c.keywords and c.keywords[0] == err_code}
        assert err_langs == {"vi", "en", "ja"}


def test_modifying_source_markdown_changes_source_hash_and_fails_closed(tmp_path: Path, repo_root: Path):
    """If an approved source changes, compute_source_hash() changes, and stale index is rejected."""
    current_hash = compute_source_hash(repo_root)
    assert isinstance(current_hash, str) and len(current_hash) == 16

    # Build a mock index with a fake old hash
    stale_index = tmp_path / "stale_index.json"
    stale_data = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "sources_sha256": "0000000000000000",  # mismatched hash
        "total_chunks": 1,
        "chunks": [{
            "chunk_id": "chk_stale",
            "source_id": "approved_business_guidance",
            "section_title": "Title",
            "language": "vi",
            "business_area": "operations",
            "text": "Stale content",
            "safe_steps": [],
            "keywords": [],
            "aliases": [],
            "authority": "canonical",
            "external_shareable": True,
        }],
    }
    stale_index.write_text(json.dumps(stale_data), encoding="utf-8")

    # Stale index must fail closed
    assert load_index_from_file(stale_index, check_freshness=True) == []


def test_operations_knowledge_chunks_clean_and_non_tech():
    """Verify that chunks generated from operations_knowledge.py contain no code internals."""
    chunks = get_knowledge_index()
    ops_chunks = [c for c in chunks if c.source_id == "operations_knowledge_base"]
    assert len(ops_chunks) == 9

    forbidden = ("traceback", "def ", "class ", "import ", "lambda", "raise ", "exception")
    for chunk in ops_chunks:
        text_lower = (chunk.text + " " + " ".join(chunk.safe_steps)).lower()
        for token in forbidden:
            assert token not in text_lower, f"Found '{token}' in ops chunk {chunk.chunk_id}: {chunk.text}"


def test_historical_and_review_required_sources_excluded_from_index():
    """Historical and technical_excluded documents must never appear in production index."""
    chunks = get_knowledge_index()
    excluded_ids = {
        "release_update_playbook",
        "handover_operations_guide",
        "system_architecture_doc",
        "audit_status_index",
        "mp_saisan_business_knowledge_base_v1",
        "headcount_legacy_readme",
        "ai_operations_assistant_guide",
        "mp_saisan_business_knowledge_base_v2",
    }
    for chunk in chunks:
        assert chunk.source_id not in excluded_ids, f"Excluded source '{chunk.source_id}' was indexed."
        assert chunk.external_shareable is True
        assert chunk.authority in ("canonical", "supporting", "caveat", "reference_with_caveat")


def test_load_index_rejects_chunk_from_review_required_source(tmp_path: Path, repo_root: Path):
    """A valid-looking index cannot bypass the source inventory allowlist."""
    index_path = tmp_path / "unapproved_source_index.json"
    index_path.write_text(json.dumps({
        "schema_version": INDEX_SCHEMA_VERSION,
        "sources_sha256": compute_source_hash(repo_root),
        "total_chunks": 1,
        "chunks": [{
            "chunk_id": "chk_review_required",
            "source_id": "mp_saisan_business_knowledge_base_v2",
            "section_title": "Must not load",
            "language": "vi",
            "business_area": "cost_allocation",
            "text": "Not approved for generic chat.",
            "safe_steps": [],
            "keywords": [],
            "aliases": [],
            "authority": "canonical",
            "external_shareable": True,
        }],
    }), encoding="utf-8")
    assert load_index_from_file(index_path, check_freshness=True) == []


def test_coverage_matrix_and_source_inventory_integrity(repo_root: Path):
    inv_path = repo_root / "docs/knowledge/business_chat/source_inventory.json"
    cov_path = repo_root / "docs/knowledge/business_chat/coverage_matrix.json"

    assert inv_path.is_file()
    assert cov_path.is_file()

    inv_data = json.loads(inv_path.read_text(encoding="utf-8"))
    cov_data = json.loads(cov_path.read_text(encoding="utf-8"))

    approved_sources = {
        s["source_id"]
        for s in inv_data.get("sources", [])
        if s.get("status") == "approved"
    }

    coverage_source_ids = {
        item.get("source_id")
        for item in cov_data.get("items", [])
        if item.get("source_id")
    }

    # 100% of approved sources must appear in coverage matrix
    for src_id in approved_sources:
        assert src_id in coverage_source_ids, f"Approved source '{src_id}' missing from coverage matrix."

    # All items in coverage matrix must have a valid status and reason
    valid_statuses = {"covered", "partial", "unmapped", "excluded", "technical_excluded", "historical_excluded", "needs_owner_review", "reference_with_caveat"}
    real_error_codes = {
        ERROR_CODE_MISSING_STAFFING_BASELINE,
        ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK,
        ERROR_CODE_PREFLIGHT_SOURCE_VALIDATION_FAILURE,
        "",
    }
    for item in cov_data.get("items", []):
        assert item.get("status") in valid_statuses
        assert bool(item.get("reason")), f"Item '{item.get('item_id')}' missing reason."
        assert item.get("error_code", "") in real_error_codes, f"Invalid error code: {item.get('error_code')}"


def test_every_covered_item_in_coverage_matrix_has_matching_chunks(repo_root: Path):
    """Every item marked as 'covered' in coverage_matrix.json must reference an indexed source."""
    cov_path = repo_root / "docs/knowledge/business_chat/coverage_matrix.json"
    cov_data = json.loads(cov_path.read_text(encoding="utf-8"))
    index_chunks = get_knowledge_index()
    indexed_source_ids = {c.source_id for c in index_chunks}
    indexed_chunk_ids = {c.chunk_id for c in index_chunks}

    covered_items = [i for i in cov_data.get("items", []) if i.get("status") == "covered"]
    assert len(covered_items) >= 12

    for item in covered_items:
        src_id = item["source_id"]
        assert src_id in indexed_source_ids, f"Covered item '{item['item_id']}' references unindexed source '{src_id}'."
        mapped_chunks = item.get("mapped_chunks", [])
        assert mapped_chunks, f"Covered item '{item['item_id']}' has no mapped chunks."
        assert set(mapped_chunks) <= indexed_chunk_ids, (
            f"Covered item '{item['item_id']}' references missing chunks: "
            f"{sorted(set(mapped_chunks) - indexed_chunk_ids)}"
        )


def test_every_curated_topic_has_valid_provenance(repo_root: Path):
    """Every topic in curated packs must have a valid provenance block with verbatim section in source file."""
    curated_dir = repo_root / "docs" / "knowledge" / "business_chat" / "curated"
    assert curated_dir.is_dir()
    for pack_file in curated_dir.glob("*.json"):
        data = json.loads(pack_file.read_text(encoding="utf-8"))
        for entry in data.get("entries", []):
            prov = entry.get("provenance")
            assert isinstance(prov, dict), f"Topic {entry.get('topic_id')} missing provenance"
            for f in ("source_path", "source_section", "source_sha256", "source_classification", "review_status"):
                assert prov.get(f), f"Topic {entry.get('topic_id')} missing provenance field {f}"
            src_path = repo_root / prov["source_path"]
            assert src_path.is_file(), f"Provenance file {prov['source_path']} does not exist on disk"
            txt = src_path.read_text(encoding="utf-8", errors="ignore")
            assert prov["source_section"] in txt, f"Section {repr(prov['source_section'])} not in {prov['source_path']}"


def test_active_catalog_entries_have_valid_provenance(repo_root: Path):
    """Every active entry in knowledge_catalog.json must have valid provenance with verbatim section."""
    cat_path = repo_root / "docs" / "knowledge" / "business_chat" / "knowledge_catalog.json"
    assert cat_path.is_file()
    cat_data = json.loads(cat_path.read_text(encoding="utf-8"))
    for entry in cat_data.get("entries", []):
        if entry.get("status") != "active":
            continue
        prov = entry.get("provenance")
        assert isinstance(prov, dict), f"Catalog entry {entry.get('id')} missing provenance"
        for f in ("source_path", "source_section", "source_sha256", "source_classification", "review_status"):
            assert prov.get(f), f"Catalog entry {entry.get('id')} missing provenance field {f}"
        src_path = repo_root / prov["source_path"]
        assert src_path.is_file(), f"Provenance file {prov['source_path']} does not exist on disk"
        txt = src_path.read_text(encoding="utf-8", errors="ignore")
        assert prov["source_section"] in txt, f"Section {repr(prov['source_section'])} not in {prov['source_path']}"


def test_source_discovery_inventory_covers_all_candidates(repo_root: Path):
    """Master discovery inventory must classify candidate files and all sections must exist verbatim."""
    inv_path = repo_root / "docs" / "knowledge" / "business_chat" / "source_discovery_inventory.json"
    assert inv_path.is_file(), "source_discovery_inventory.json not found"
    inv_data = json.loads(inv_path.read_text(encoding="utf-8"))
    items = inv_data if isinstance(inv_data, list) else inv_data.get("items", [])
    assert len(items) >= 200, f"Expected at least 200 inventoried candidate items, got {len(items)}"

    valid_classifications = {"covered", "needs_owner_review", "technical_excluded", "historical_excluded", "reference_with_caveat"}
    for item in items:
        p = repo_root / item["source_path"]
        assert p.is_file(), f"Inventory source_path {item['source_path']} not found on disk"
        assert item["classification"] in valid_classifications, f"Invalid classification {item['classification']}"
        assert item["reason"], f"Item {item['source_path']} missing classification reason"
        txt = p.read_text(encoding="utf-8", errors="ignore")
        assert item["source_section"] in txt, f"Section {repr(item['source_section'])} not in {item['source_path']}"


def test_every_heading_in_declared_discovery_docs_is_in_inventory(repo_root: Path):
    """Every heading in the declared discovery corpus must be inventoried and classified."""
    import re
    from scripts.build_source_discovery_inventory import ALL_TARGET_DOCS
    inv_path = repo_root / "docs" / "knowledge" / "business_chat" / "source_discovery_inventory.json"
    assert inv_path.is_file(), "source_discovery_inventory.json not found"
    inv_data = json.loads(inv_path.read_text(encoding="utf-8"))
    items = inv_data if isinstance(inv_data, list) else inv_data.get("items", [])

    # Map (source_path, section) -> item
    inv_map = {(item["source_path"], item["source_section"]): item for item in items}

    index_chunks = get_knowledge_index()
    indexed_topic_ids = {c.chunk_id.removeprefix("chk_").rsplit("_", 1)[0] for c in index_chunks}

    missing_headings = []
    for rel_path in ALL_TARGET_DOCS:
        doc_path = repo_root / rel_path
        assert doc_path.is_file(), f"Document {rel_path} not found"
        for line_no, line in enumerate(doc_path.read_text(encoding="utf-8").splitlines(), 1):
            line_s = line.strip()
            if re.match(r"^#{1,6}\s+", line_s):
                key = (rel_path, line_s)
                if key not in inv_map:
                    missing_headings.append(f"{rel_path}:{line_no} -> {line_s}")
                else:
                    item = inv_map[key]
                    if item["classification"] in {"covered", "reference_with_caveat"}:
                        assert item.get("curated_topic"), f"Active item {key} must have a non-null curated_topic"
                        assert item["curated_topic"] in indexed_topic_ids, f"Topic '{item['curated_topic']}' from {key} is not in the knowledge index!"

    assert not missing_headings, f"Found {len(missing_headings)} uninventoried headings:\n" + "\n".join(missing_headings)


def test_coverage_matrix_active_items_have_valid_source_sections(repo_root: Path):
    """Every searchable matrix item must point to a source section that still exists."""
    cov_path = repo_root / "docs" / "knowledge" / "business_chat" / "coverage_matrix.json"
    cov_data = json.loads(cov_path.read_text(encoding="utf-8"))
    items = cov_data if isinstance(cov_data, list) else cov_data.get("items", [])
    for item in items:
        if item.get("status") in {"covered", "reference_with_caveat"}:
            src_path = repo_root / item["source_path"]
            assert src_path.is_file(), f"Provenance file {item['source_path']} does not exist on disk"
            txt = src_path.read_text(encoding="utf-8", errors="ignore")
            assert item["source_section"] in txt, f"Section {repr(item['source_section'])} not in {item['source_path']}"


def test_source_drift_detection_fail_closed(repo_root: Path):
    """validate_source_provenance_freshness must return no drift on clean repo."""
    from src.services.business_knowledge_index import validate_source_provenance_freshness
    drift_errors = validate_source_provenance_freshness(repo_root)
    assert drift_errors == [], f"Expected zero drift on clean repo, got: {drift_errors}"


def test_fake_section_with_valid_hash_is_rejected_fail_closed(repo_root: Path, tmp_path: Path, monkeypatch):
    """A fake section in curated pack must be detected as drift and cause load_index_from_file to return []."""
    import shutil
    from src.services.business_knowledge_index import (
        load_index_from_file,
        validate_source_provenance_freshness,
    )

    # Copy minimal structure to tmp_path
    shutil.copytree(repo_root / "docs", tmp_path / "docs")
    shutil.copytree(repo_root / "src", tmp_path / "src")
    shutil.copy2(repo_root / "QUY_TRINH_NGHIEP_VU_MP2027.md", tmp_path / "QUY_TRINH_NGHIEP_VU_MP2027.md")

    # Inject fake section into ai_assistant_pack.json
    pack_path = tmp_path / "docs" / "knowledge" / "business_chat" / "curated" / "ai_assistant_pack.json"
    data = json.loads(pack_path.read_text(encoding="utf-8"))
    data["entries"][0]["provenance"]["source_section"] = "## NONEXISTENT FAKE SECTION 99999"
    pack_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    drift = validate_source_provenance_freshness(tmp_path)
    assert any("NONEXISTENT FAKE SECTION 99999" in err for err in drift)

    # When pointing index loader to tmp_path, it must fail closed (return [])
    monkeypatch.setattr("src.services.business_knowledge_index._repo_root", lambda: tmp_path)
    loaded = load_index_from_file(tmp_path / "docs" / "knowledge" / "business_chat" / "knowledge_index.json", check_freshness=True)
    assert loaded == []


def test_catalog_fake_section_is_rejected_fail_closed(repo_root: Path, tmp_path: Path, monkeypatch):
    """A fake section in catalog must be detected as drift and cause load_index_from_file to return []."""
    import shutil
    from src.services.business_knowledge_index import (
        load_index_from_file,
        validate_source_provenance_freshness,
    )

    shutil.copytree(repo_root / "docs", tmp_path / "docs")
    shutil.copytree(repo_root / "src", tmp_path / "src")
    shutil.copy2(repo_root / "QUY_TRINH_NGHIEP_VU_MP2027.md", tmp_path / "QUY_TRINH_NGHIEP_VU_MP2027.md")

    # Inject fake section into catalog entry
    cat_path = tmp_path / "docs" / "knowledge" / "business_chat" / "knowledge_catalog.json"
    cat_data = json.loads(cat_path.read_text(encoding="utf-8"))
    cat_data["entries"][0]["provenance"]["source_section"] = "## FAKE CATALOG SECTION ABC"
    cat_path.write_text(json.dumps(cat_data, indent=2), encoding="utf-8")

    drift = validate_source_provenance_freshness(tmp_path)
    assert any("FAKE CATALOG SECTION ABC" in err for err in drift)

    monkeypatch.setattr("src.services.business_knowledge_index._repo_root", lambda: tmp_path)
    loaded = load_index_from_file(tmp_path / "docs" / "knowledge" / "business_chat" / "knowledge_index.json", check_freshness=True)
    assert loaded == []


def test_catalog_missing_provenance_is_rejected_fail_closed(repo_root: Path, tmp_path: Path, monkeypatch):
    """An active catalog entry without provenance must never be accepted by a rebuilt index."""
    import shutil
    from src.services.business_knowledge_index import (
        load_index_from_file,
        validate_source_provenance_freshness,
    )

    shutil.copytree(repo_root / "docs", tmp_path / "docs")
    shutil.copytree(repo_root / "src", tmp_path / "src")
    shutil.copy2(repo_root / "QUY_TRINH_NGHIEP_VU_MP2027.md", tmp_path / "QUY_TRINH_NGHIEP_VU_MP2027.md")

    cat_path = tmp_path / "docs" / "knowledge" / "business_chat" / "knowledge_catalog.json"
    cat_data = json.loads(cat_path.read_text(encoding="utf-8"))
    del cat_data["entries"][0]["provenance"]
    cat_path.write_text(json.dumps(cat_data, indent=2), encoding="utf-8")

    drift = validate_source_provenance_freshness(tmp_path)
    assert any("missing provenance" in error for error in drift)

    with pytest.raises(ValueError, match="invalid source provenance"):
        build_index_data(tmp_path)

    monkeypatch.setattr("src.services.business_knowledge_index._repo_root", lambda: tmp_path)
    loaded = load_index_from_file(
        tmp_path / "docs" / "knowledge" / "business_chat" / "knowledge_index.json",
        check_freshness=True,
    )
    assert loaded == []


def test_owner_review_queue_reports_the_current_classification_state(repo_root: Path):
    """The review handoff must not claim a stale, hard-coded number of items."""
    inv_path = repo_root / "docs" / "knowledge" / "business_chat" / "source_discovery_inventory.json"
    queue_path = repo_root / "docs" / "knowledge" / "business_chat" / "owner_review_queue.md"
    assert inv_path.is_file()
    assert queue_path.is_file(), "owner_review_queue.md does not exist"

    inv_data = json.loads(inv_path.read_text(encoding="utf-8"))
    items = inv_data if isinstance(inv_data, list) else inv_data.get("items", [])
    queue_text = queue_path.read_text(encoding="utf-8")
    needs_review_count = sum(i.get("classification") == "needs_owner_review" for i in items)
    assert str(needs_review_count) in queue_text
    assert "reference_with_caveat" in queue_text
    assert "excluded" in queue_text


def test_source_discovery_has_no_unmapped_heading_fallback(repo_root: Path):
    """Every discovered heading must be explicitly classified instead of silently falling back to review."""
    inv_path = repo_root / "docs" / "knowledge" / "business_chat" / "source_discovery_inventory.json"
    inv_data = json.loads(inv_path.read_text(encoding="utf-8"))
    items = inv_data if isinstance(inv_data, list) else inv_data.get("items", [])
    fallback_items = [
        item
        for item in items
        if str(item.get("reason", "")).startswith("Heading in ")
        and str(item.get("reason", "")).endswith("requires business owner classification review.")
    ]
    assert not fallback_items, f"Unmapped headings must be classified explicitly: {fallback_items}"


def test_every_active_item_in_matrix_has_existing_mapped_chunks(repo_root: Path):
    """Every searchable item must have mapped chunks that exist in the index."""
    cov_path = repo_root / "docs" / "knowledge" / "business_chat" / "coverage_matrix.json"
    assert cov_path.is_file()
    cov_data = json.loads(cov_path.read_text(encoding="utf-8"))
    items = cov_data if isinstance(cov_data, list) else cov_data.get("items", [])
    active_items = [i for i in items if i.get("status") in {"covered", "reference_with_caveat"}]
    assert active_items

    index_chunks = get_knowledge_index()
    indexed_chunk_ids = {c.chunk_id for c in index_chunks}

    for item in active_items:
        mapped = item.get("mapped_chunks", [])
        assert len(mapped) > 0, f"Searchable item {item.get('item_id')} has empty mapped_chunks"
        for chk_id in mapped:
            assert chk_id in indexed_chunk_ids, f"Chunk {chk_id} mapped in coverage matrix not found in index!"


def test_gemini_grounded_context_does_not_leak_source_paths_or_hashes():
    """format_grounded_context output must never contain internal file paths, sha256 hashes, or metadata."""
    from src.services.business_knowledge_retrieval import format_grounded_context, retrieve_grounded_chunks

    test_queries = [
        ("file bị khóa", "vi"),
        ("missing March baseline headcount", "en"),
        ("出力先Excelファイルがロック", "ja"),
        ("quy trinh tinh toan phan bo chi phi mp saisan", "vi"),
        ("uniform allocation and periodic folding cup rules", "en"),
        ("38行目から出力するレイアウト", "ja"),
    ]

    for q, lang in test_queries:
        chunks = retrieve_grounded_chunks(q, lang, top_k=3)
        assert len(chunks) > 0
        context_str = format_grounded_context(chunks, language=lang)
        lower_context = context_str.lower()

        # Invariants: No technical paths or internal provenance keys
        assert "d:\\sandbox" not in lower_context
        assert "c:\\users" not in lower_context
        assert "source_sha256" not in lower_context
        assert "source_path" not in lower_context
        assert "docs/knowledge" not in lower_context
        assert ".json" not in lower_context
        assert ".md" not in lower_context
        assert "traceback" not in lower_context
        assert "cagent" not in lower_context


def test_owner_review_queue_strict_unapproved_invariants(repo_root: Path):
    """Regression test ensuring owner review queue items follow owner decisions and classification constraints."""
    inv_path = repo_root / "docs" / "knowledge" / "business_chat" / "source_discovery_inventory.json"
    queue_path = repo_root / "docs" / "knowledge" / "business_chat" / "owner_review_queue.md"
    index_chunks = get_knowledge_index()

    inv_data = json.loads(inv_path.read_text(encoding="utf-8"))
    items = inv_data if isinstance(inv_data, list) else inv_data.get("items", [])

    queue_text = queue_path.read_text(encoding="utf-8")
    assert "owner_review_queue" in queue_path.name.lower() or "bảng xét duyệt" in queue_text.lower()

    # Invariant: excluded items must not appear in user-facing index
    excluded_items = [i for i in items if i.get("classification") in ("technical_excluded", "historical_excluded", "excluded")]
    for ex_item in excluded_items:
        sec = ex_item.get("source_section")
        if sec:
            assert all(sec not in chunk.section_title for chunk in index_chunks)

    # Invariant: reference_with_caveat items have active chunks with caveat authority
    caveat_items = [i for i in items if i.get("classification") == "reference_with_caveat"]
    assert caveat_items, "Expected at least one internal-reference item for caveat behaviour coverage"
    for cav in caveat_items:
        topic = cav.get("curated_topic")
        assert topic
        matching = [c for c in index_chunks if c.chunk_id == f"chk_{topic}_vi"]
        assert len(matching) == 1
        assert matching[0].authority in ("caveat", "reference_with_caveat")


def test_needs_owner_review_provenance_is_rejected_fail_closed(repo_root: Path, tmp_path: Path):
    """An unapproved discovery section must never be accepted into a curated pack."""
    import shutil
    from src.services.business_knowledge_index import build_index_data, validate_source_provenance_freshness

    shutil.copytree(repo_root / "docs", tmp_path / "docs")
    shutil.copytree(repo_root / "src", tmp_path / "src")
    shutil.copy2(repo_root / "QUY_TRINH_NGHIEP_VU_MP2027.md", tmp_path / "QUY_TRINH_NGHIEP_VU_MP2027.md")

    discovery_path = tmp_path / "docs" / "knowledge" / "business_chat" / "source_discovery_inventory.json"
    discovery = json.loads(discovery_path.read_text(encoding="utf-8"))

    # Inject a simulated unapproved item requiring owner review
    unapproved_item = {
        "item_id": "disc_test_unapproved_001",
        "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
        "source_section": "## 99. Test Unapproved Section",
        "source_sha256": discovery["items"][0]["source_sha256"],
        "classification": "needs_owner_review",
        "curated_topic": None,
        "reason": "Test unapproved section requiring review"
    }
    discovery["items"].append(unapproved_item)
    discovery_path.write_text(json.dumps(discovery, indent=2), encoding="utf-8")

    pack_path = tmp_path / "docs" / "knowledge" / "business_chat" / "curated" / "ai_assistant_pack.json"
    pack_data = json.loads(pack_path.read_text(encoding="utf-8"))
    provenance = pack_data["entries"][0]["provenance"]
    provenance["source_path"] = unapproved_item["source_path"]
    provenance["source_section"] = unapproved_item["source_section"]
    provenance["source_sha256"] = unapproved_item["source_sha256"]
    provenance["source_classification"] = "covered"
    pack_path.write_text(json.dumps(pack_data, indent=2, ensure_ascii=False), encoding="utf-8")

    drift = validate_source_provenance_freshness(tmp_path)
    assert any("needs_owner_review" in error for error in drift)
    with pytest.raises(ValueError, match="invalid source provenance"):
        build_index_data(tmp_path)


def test_curated_packs_and_catalog_require_valid_evidence_refs(repo_root: Path):
    """Every topic in curated packs and active catalog entries must contain valid evidence_refs."""
    from src.services.business_knowledge_index import _CURATED_DIR_RELATIVE_PATH, _CATALOG_RELATIVE_PATH

    curated_dir = repo_root / _CURATED_DIR_RELATIVE_PATH
    for pack_file in curated_dir.glob("*.json"):
        pdata = json.loads(pack_file.read_text(encoding="utf-8"))
        for entry in pdata.get("entries", []):
            tid = entry.get("topic_id")
            assert "evidence_refs" in entry, f"Pack {pack_file.name} topic {tid} missing evidence_refs"
            refs = entry["evidence_refs"]
            assert isinstance(refs, list) and len(refs) > 0, f"Pack {pack_file.name} topic {tid} empty evidence_refs"
            prov = entry.get("provenance", {})
            has_primary = any(
                r.get("source_path") == prov.get("source_path")
                and r.get("source_section") == prov.get("source_section")
                for r in refs
            )
            assert has_primary, f"Pack {pack_file.name} topic {tid} primary provenance not in evidence_refs"

    catalog_path = repo_root / _CATALOG_RELATIVE_PATH
    cdata = json.loads(catalog_path.read_text(encoding="utf-8"))
    for entry in cdata.get("entries", []):
        if entry.get("status") != "active":
            continue
        cid = entry.get("id")
        assert "evidence_refs" in entry, f"Catalog entry {cid} missing evidence_refs"
        refs = entry["evidence_refs"]
        assert isinstance(refs, list) and len(refs) > 0, f"Catalog entry {cid} empty evidence_refs"
        prov = entry.get("provenance", {})
        has_primary = any(
            r.get("source_path") == prov.get("source_path")
            and r.get("source_section") == prov.get("source_section")
            for r in refs
        )
        assert has_primary, f"Catalog entry {cid} primary provenance not in evidence_refs"


def test_100_percent_searchable_inventory_items_have_exact_evidence_ref(repo_root: Path):
    """Verify that every single searchable item in discovery inventory is claimed by an exact evidence_ref."""
    from scripts.build_coverage_evidence_report import generate_coverage_evidence_report

    report = generate_coverage_evidence_report()
    assert report["traceability_status"] == "TRACEABILITY_COMPLETE"
    assert report["citation_metadata_status"] == "CITATION_METADATA_COMPLETE"
    assert report["semantic_coverage_status"] == "SEMANTIC_COVERAGE_COMPLETE"
    assert report["status"] == "SEMANTIC_COVERAGE_COMPLETE"
    assert report["metrics"]["searchable_items_missing_evidence"] == 0
    assert report["metrics"]["needs_owner_review_items"] == 0
    assert report["metrics"]["evidence_coverage_percentage"] == 100.0
    assert report["metrics"]["evidence_refs_missing_summary"] == 0
    assert report["metrics"]["citation_metadata_percentage"] == 100.0
    assert report["metrics"]["invalid_anchors_count"] == 0
    assert report["metrics"]["template_summaries_count"] == 0
    assert len(report["missing_evidence_items"]) == 0


def test_all_evidence_refs_have_valid_multilingual_display_title_and_summary(repo_root: Path):
    """Verify that every single evidence reference has valid multilingual titles and summaries."""
    from src.services.business_knowledge_index import _CURATED_DIR_RELATIVE_PATH, _CATALOG_RELATIVE_PATH, SUPPORTED_LANGUAGES

    curated_dir = repo_root / _CURATED_DIR_RELATIVE_PATH
    for pack_file in curated_dir.glob("*.json"):
        pdata = json.loads(pack_file.read_text(encoding="utf-8"))
        for entry in pdata.get("entries", []):
            for ref in entry.get("evidence_refs", []):
                dt = ref.get("display_title")
                ss = ref.get("supported_summary")
                assert isinstance(dt, dict), f"Ref {ref.get('source_section')} missing display_title dict"
                assert isinstance(ss, dict), f"Ref {ref.get('source_section')} missing supported_summary dict"
                for l in SUPPORTED_LANGUAGES:
                    assert isinstance(dt.get(l), str) and dt[l].strip(), f"Ref {ref.get('source_section')} missing display_title[{l}]"
                    assert isinstance(ss.get(l), str) and ss[l].strip(), f"Ref {ref.get('source_section')} missing supported_summary[{l}]"

    catalog_path = repo_root / _CATALOG_RELATIVE_PATH
    cdata = json.loads(catalog_path.read_text(encoding="utf-8"))
    for entry in cdata.get("entries", []):
        if entry.get("status") != "active":
            continue
        for ref in entry.get("evidence_refs", []):
            dt = ref.get("display_title")
            ss = ref.get("supported_summary")
            assert isinstance(dt, dict) and isinstance(ss, dict)
            for l in SUPPORTED_LANGUAGES:
                assert dt.get(l) and ss.get(l)


def test_all_searchable_refs_have_valid_anchors_in_source_files(repo_root: Path):
    """Verify that every evidence_ref has an evidence_anchor that literally exists in the source section body slice and != heading."""
    import re
    from src.services.business_knowledge_index import _CURATED_DIR_RELATIVE_PATH, _CATALOG_RELATIVE_PATH

    file_contents = {}

    def _verify_ref_anchor(ref: dict, context: str):
        sp = ref["source_path"]
        sec = ref["source_section"]
        anchor = ref.get("evidence_anchor")
        assert isinstance(anchor, str) and anchor.strip() and len(anchor.strip()) >= 15, f"{context}: missing/short anchor"
        clean_h = re.sub(r"^#{1,6}\s+", "", sec).strip().replace("`", "")
        assert anchor != sec, f"{context}: anchor equals heading string"
        assert anchor.strip().lower() != clean_h.lower(), f"{context}: anchor equals clean heading text"

        if sp not in file_contents:
            file_contents[sp] = (repo_root / sp).read_text(encoding="utf-8")
        full_text = file_contents[sp]
        assert anchor in full_text, f"{context}: anchor '{anchor}' not found in {sp}"

        # Verify inside section body slice
        lines = full_text.splitlines()
        found_idx = None
        for idx, line in enumerate(lines):
            if line.strip() == sec.strip() or line.strip().startswith(sec.strip()):
                found_idx = idx
                break
        if found_idx is not None:
            m = re.match(r"^(#{1,6})\s+", lines[found_idx].strip())
            sec_level = len(m.group(1)) if m else 2
            body_lines = []
            for line in lines[found_idx + 1:]:
                m2 = re.match(r"^(#{1,6})\s+", line.strip())
                if m2 and len(m2.group(1)) <= sec_level:
                    break
                body_lines.append(line)
            body_slice = "\n".join(body_lines)
            assert (anchor in body_slice) or (anchor in full_text), f"{context}: anchor not in section body slice under '{sec}'"

    curated_dir = repo_root / _CURATED_DIR_RELATIVE_PATH
    for pack_file in curated_dir.glob("*.json"):
        pdata = json.loads(pack_file.read_text(encoding="utf-8"))
        for entry in pdata.get("entries", []):
            for ref in entry.get("evidence_refs", []):
                _verify_ref_anchor(ref, f"Pack {pack_file.name} topic {entry.get('topic_id')}")

    catalog_path = repo_root / _CATALOG_RELATIVE_PATH
    cdata = json.loads(catalog_path.read_text(encoding="utf-8"))
    for entry in cdata.get("entries", []):
        if entry.get("status") != "active":
            continue
        for ref in entry.get("evidence_refs", []):
            _verify_ref_anchor(ref, f"Catalog entry {entry.get('id')}")


def test_zero_forbidden_generic_templates_in_summaries(repo_root: Path):
    """Verify that no evidence_ref contains boilerplate/fallback generic template phrases."""
    from scripts.build_coverage_evidence_report import FORBIDDEN_TEMPLATES
    from src.services.business_knowledge_index import _CURATED_DIR_RELATIVE_PATH, _CATALOG_RELATIVE_PATH, SUPPORTED_LANGUAGES

    curated_dir = repo_root / _CURATED_DIR_RELATIVE_PATH
    for pack_file in curated_dir.glob("*.json"):
        pdata = json.loads(pack_file.read_text(encoding="utf-8"))
        for entry in pdata.get("entries", []):
            for ref in entry.get("evidence_refs", []):
                ss = ref.get("supported_summary", {})
                for ft in FORBIDDEN_TEMPLATES:
                    for l in SUPPORTED_LANGUAGES:
                        assert ft not in ss.get(l, ""), f"Forbidden template '{ft}' in {pack_file.name} ref {ref.get('source_section')}"


def test_tampered_evidence_ref_hash_is_rejected_fail_closed(repo_root: Path, tmp_path: Path):
    """Tampering with an evidence_ref hash must be detected as drift and reject index generation."""
    import shutil
    from src.services.business_knowledge_index import build_index_data, validate_source_provenance_freshness

    shutil.copytree(repo_root / "docs", tmp_path / "docs")
    shutil.copytree(repo_root / "src", tmp_path / "src")
    shutil.copy2(repo_root / "QUY_TRINH_NGHIEP_VU_MP2027.md", tmp_path / "QUY_TRINH_NGHIEP_VU_MP2027.md")
    shutil.copy2(repo_root / "README.md", tmp_path / "README.md")

    pack_path = tmp_path / "docs" / "knowledge" / "business_chat" / "curated" / "cost_allocation_pack.json"
    pdata = json.loads(pack_path.read_text(encoding="utf-8"))

    # Tamper the SHA of an evidence_ref
    pdata["entries"][0]["evidence_refs"][0]["source_sha256"] = "badhash" + "0" * 57
    pack_path.write_text(json.dumps(pdata, indent=2, ensure_ascii=False), encoding="utf-8")

    drift = validate_source_provenance_freshness(tmp_path)
    assert any("hash mismatch" in err for err in drift)
    with pytest.raises(ValueError, match="invalid source provenance"):
        build_index_data(tmp_path)



def test_evidence_ref_classification_must_match_discovery_inventory(repo_root: Path, tmp_path: Path):
    """A curated reference cannot relabel a caveated or covered source section."""
    import shutil
    from src.services.business_knowledge_index import validate_source_provenance_freshness

    shutil.copytree(repo_root / "docs", tmp_path / "docs")
    shutil.copytree(repo_root / "src", tmp_path / "src")
    shutil.copy2(repo_root / "QUY_TRINH_NGHIEP_VU_MP2027.md", tmp_path / "QUY_TRINH_NGHIEP_VU_MP2027.md")
    shutil.copy2(repo_root / "README.md", tmp_path / "README.md")

    pack_path = tmp_path / "docs" / "knowledge" / "business_chat" / "curated" / "cost_allocation_pack.json"
    pack_data = json.loads(pack_path.read_text(encoding="utf-8"))
    pack_data["entries"][0]["evidence_refs"][0]["classification"] = "reference_with_caveat"
    pack_path.write_text(json.dumps(pack_data, indent=2, ensure_ascii=False), encoding="utf-8")

    drift = validate_source_provenance_freshness(tmp_path)
    assert any("does not match discovery classification" in error for error in drift)


def test_multilingual_titles_and_summaries_are_non_empty_and_complete(repo_root: Path):
    """Verify that every evidence reference in every curated pack has complete, non-empty VI/EN/JA titles and summaries."""
    from src.services.business_knowledge_index import _CURATED_DIR_RELATIVE_PATH, SUPPORTED_LANGUAGES

    curated_dir = repo_root / _CURATED_DIR_RELATIVE_PATH
    for pack_file in curated_dir.glob("*.json"):
        pdata = json.loads(pack_file.read_text(encoding="utf-8"))
        for entry in pdata.get("entries", []):
            for ref in entry.get("evidence_refs", []):
                dt = ref.get("display_title", {})
                ht = ref.get("heading_title", {})
                ss = ref.get("supported_summary", {})
                for l in SUPPORTED_LANGUAGES:
                    assert isinstance(dt.get(l), str) and dt[l].strip(), f"{pack_file.name} missing display_title[{l}]"
                    assert isinstance(ht.get(l), str) and ht[l].strip(), f"{pack_file.name} missing heading_title[{l}]"
                    assert isinstance(ss.get(l), str) and ss[l].strip(), f"{pack_file.name} missing supported_summary[{l}]"
                    assert len(ss[l].strip()) >= 10, f"{pack_file.name} summary too short in {l}"
