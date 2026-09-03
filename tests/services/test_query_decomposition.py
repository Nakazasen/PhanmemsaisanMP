"""Tests for MP2027 Query Decomposition Engine and Multi-Query RAG Retrieval."""

from __future__ import annotations

import pytest

from src.services.business_knowledge_index import DocumentChunk, get_knowledge_index
from src.services.business_knowledge_retrieval import (
    format_grounded_context,
    merge_multi_query_chunks,
    merge_multi_query_traces,
    retrieve_grounded_chunks,
    retrieve_grounded_chunks_with_trace,
)
from src.services.query_decomposition import (
    _normalize_subquery_text,
    decompose_query,
    resolve_multiturn_query,
)
from src.ui.operations_assistant import _business_document_context


# ===========================================================================
# 1. Single Query Tests (Decomposition Accuracy)
# ===========================================================================

class TestSingleQueryDecomposition:
    """Ensure single-intent questions remain single queries without redundant computation."""

    def test_single_vietnamese_query_unchanged(self):
        query = "Lỗi file khóa là gì"
        subqueries = decompose_query(query, "vi")
        assert len(subqueries) == 1
        assert subqueries[0] == "Lỗi file khóa là gì"

    def test_single_query_with_compound_noun_va(self):
        # 'và' connecting two nouns within a single topic must NOT be split
        query = "thứ tự xử lý file nguồn và dòng phân cách"
        subqueries = decompose_query(query, "vi")
        assert len(subqueries) == 1
        assert subqueries[0] == "thứ tự xử lý file nguồn và dòng phân cách"

    def test_single_query_with_chung_va_rieng(self):
        query = "phân bổ chi phí chung và riêng thế nào"
        subqueries = decompose_query(query, "vi")
        assert len(subqueries) == 1
        assert subqueries[0] == "phân bổ chi phí chung và riêng thế nào"

    def test_single_english_query_unchanged(self):
        query = "What is the locked file error?"
        subqueries = decompose_query(query, "en")
        assert len(subqueries) == 1
        assert "locked file error" in subqueries[0].lower()

    def test_single_english_query_with_and(self):
        query = "software update and version rollback"
        subqueries = decompose_query(query, "en")
        assert len(subqueries) == 1
        assert subqueries[0] == "software update and version rollback"

    def test_single_japanese_query_unchanged(self):
        query = "出力先Excelファイルがロックされた場合の対処方法"
        subqueries = decompose_query(query, "ja")
        assert len(subqueries) == 1
        assert subqueries[0] == "出力先Excelファイルがロックされた場合の対処方法"

    def test_single_japanese_query_with_to(self):
        query = "ソースファイルの処理順序と区切り行ルール"
        subqueries = decompose_query(query, "ja")
        assert len(subqueries) == 1
        assert subqueries[0] == "ソースファイルの処理順序と区切り行ルール"

    def test_empty_and_whitespace_query(self):
        assert decompose_query("", "vi") == []
        assert decompose_query("   ", "vi") == []


# ===========================================================================
# 2. Compound Query Tests with Conjunctions (VI, EN, JA)
# ===========================================================================

class TestConjunctionDecomposition:
    """Test decomposition of compound questions connected by conjunctions."""

    def test_vietnamese_va_with_action(self):
        query = "Cách xử lý tệp bị khóa và làm sao để tra cứu mã tài khoản phòng ban"
        subqueries = decompose_query(query, "vi")
        assert len(subqueries) == 2
        assert "tệp bị khóa" in subqueries[0].lower() or "cách xử lý" in subqueries[0].lower()
        assert "tra cứu mã tài khoản" in subqueries[1].lower() or "làm sao" in subqueries[1].lower()

    def test_vietnamese_dong_thoi(self):
        query = "Cách khắc phục tệp bị khóa đồng thời cho biết mã tài khoản của phòng ban"
        subqueries = decompose_query(query, "vi")
        assert len(subqueries) == 2
        assert any("khóa" in sq.lower() for sq in subqueries)
        assert any("tài khoản" in sq.lower() for sq in subqueries)

    def test_vietnamese_ngoai_ra(self):
        query = "Hướng dẫn xử lý lỗi tệp bị khóa, ngoài ra cho tôi hỏi quy tắc tra cứu tài khoản"
        subqueries = decompose_query(query, "vi")
        assert len(subqueries) == 2
        assert any("tệp bị khóa" in sq.lower() for sq in subqueries)
        assert any("tra cứu tài khoản" in sq.lower() for sq in subqueries)

    def test_vietnamese_voi_lai(self):
        query = "Lỗi khóa file sửa thế nào, với lại tra cứu mã tài khoản ở đâu"
        subqueries = decompose_query(query, "vi")
        assert len(subqueries) == 2
        assert any("khóa" in sq.lower() for sq in subqueries)
        assert any("tài khoản" in sq.lower() for sq in subqueries)

    def test_vietnamese_tien_the(self):
        query = "Khắc phục lỗi file bị khóa, tiện thể hướng dẫn tra cứu mã tài khoản"
        subqueries = decompose_query(query, "vi")
        assert len(subqueries) == 2
        assert any("khóa" in sq.lower() for sq in subqueries)
        assert any("tài khoản" in sq.lower() for sq in subqueries)

    def test_vietnamese_cung_nhu(self):
        query = "Quy trình xử lý tệp bị khóa cũng như cách tra cứu mã tài khoản"
        subqueries = decompose_query(query, "vi")
        assert len(subqueries) == 2
        assert any("khóa" in sq.lower() for sq in subqueries)
        assert any("tài khoản" in sq.lower() for sq in subqueries)

    def test_vietnamese_con(self):
        query = "Tệp bị khóa xử lý thế nào, còn mã tài khoản tra cứu ra sao"
        subqueries = decompose_query(query, "vi")
        assert len(subqueries) == 2
        assert any("khóa" in sq.lower() for sq in subqueries)
        assert any("tài khoản" in sq.lower() for sq in subqueries)

    def test_vietnamese_lan(self):
        query = "Cách xử lý tệp bị khóa lẫn cách tra cứu mã tài khoản phòng ban"
        subqueries = decompose_query(query, "vi")
        assert len(subqueries) == 2
        assert any("khóa" in sq.lower() for sq in subqueries)
        assert any("tài khoản" in sq.lower() for sq in subqueries)

    def test_vietnamese_compound_lan_lon_not_split(self):
        query = "Dữ liệu bị lẫn lộn giữa các phòng ban thì xử lý thế nào"
        subqueries = decompose_query(query, "vi")
        assert len(subqueries) == 1
        assert "lẫn lộn" in subqueries[0].lower()

    def test_vietnamese_comma_intent_split(self):
        query = "Cách xử lý tệp bị khóa, làm sao để tra cứu mã tài khoản phòng ban"
        subqueries = decompose_query(query, "vi")
        assert len(subqueries) == 2
        assert any("khóa" in sq.lower() for sq in subqueries)
        assert any("tài khoản" in sq.lower() for sq in subqueries)

    def test_english_and_how(self):
        query = "How to resolve locked output file and how do I lookup department account code?"
        subqueries = decompose_query(query, "en")
        assert len(subqueries) == 2
        assert any("locked" in sq.lower() for sq in subqueries)
        assert any("account" in sq.lower() for sq in subqueries)

    def test_english_as_well_as(self):
        query = "How to fix locked files as well as how to lookup account codes"
        subqueries = decompose_query(query, "en")
        assert len(subqueries) == 2
        assert any("locked" in sq.lower() for sq in subqueries)
        assert any("account" in sq.lower() for sq in subqueries)

    def test_english_and_also(self):
        query = "How to troubleshoot locked file errors and also how to map account codes"
        subqueries = decompose_query(query, "en")
        assert len(subqueries) == 2
        assert any("locked" in sq.lower() for sq in subqueries)
        assert any("account" in sq.lower() for sq in subqueries)

    def test_japanese_mata(self):
        query = "出力先Excelファイルがロックされた場合の対処方法、また勘定科目コードの特定ルールについて教えてください"
        subqueries = decompose_query(query, "ja")
        assert len(subqueries) == 2
        assert any("ロック" in sq for sq in subqueries)
        assert any("勘定科目" in sq for sq in subqueries)

    def test_japanese_oyobi(self):
        query = "ファイルロックの解除手順、および勘定科目コードの特定方法について"
        subqueries = decompose_query(query, "ja")
        assert len(subqueries) == 2
        assert any("ロック" in sq for sq in subqueries)
        assert any("勘定科目" in sq for sq in subqueries)

    def test_japanese_to_with_comma(self):
        query = "ファイルロックの対処手順と、勘定科目コードの確認方法"
        subqueries = decompose_query(query, "ja")
        assert len(subqueries) == 2
        assert any("ロック" in sq for sq in subqueries)
        assert any("勘定科目" in sq for sq in subqueries)

    def test_vietnamese_va_interrogative_tail(self):
        query = "Cách xử lý tệp bị khóa và mã tài khoản phòng ban tra cứu ở đâu?"
        subqueries = decompose_query(query, "vi")
        assert len(subqueries) == 2
        assert any("khóa" in sq.lower() for sq in subqueries)
        assert any("tài khoản" in sq.lower() for sq in subqueries)

    def test_vietnamese_lan_interrogative_tail(self):
        query = "Cách khắc phục tệp bị khóa lẫn mã tài khoản tra cứu thế nào?"
        subqueries = decompose_query(query, "vi")
        assert len(subqueries) == 2
        assert any("khóa" in sq.lower() for sq in subqueries)
        assert any("tài khoản" in sq.lower() for sq in subqueries)

    def test_english_and_clause_rules(self):
        query = "How to resolve locked output file and account code lookup rules"
        subqueries = decompose_query(query, "en")
        assert len(subqueries) == 2
        assert any("locked" in sq.lower() for sq in subqueries)
        assert any("account" in sq.lower() for sq in subqueries)


# ===========================================================================
# 3. Delimiter & List Decomposition Tests
# ===========================================================================

class TestDelimiterDecomposition:
    """Test decomposition with semicolons, multiple question marks, and lists."""

    def test_semicolon_separation(self):
        query = "Cách khắc phục lỗi file khóa; tra cứu mã tài khoản phòng ban"
        subqueries = decompose_query(query, "vi")
        assert len(subqueries) == 2
        assert any("khóa" in sq.lower() for sq in subqueries)
        assert any("tài khoản" in sq.lower() for sq in subqueries)

    def test_multiple_question_marks(self):
        query = "Lỗi file khóa là gì? Tra cứu mã tài khoản ở đâu?"
        subqueries = decompose_query(query, "vi")
        assert len(subqueries) == 2
        assert any("khóa" in sq.lower() for sq in subqueries)
        assert any("tài khoản" in sq.lower() for sq in subqueries)

    def test_bullet_list_multiline(self):
        query = "- Cách xử lý lỗi tệp khóa\n- Tra cứu mã tài khoản phòng ban"
        subqueries = decompose_query(query, "vi")
        assert len(subqueries) == 2
        assert any("khóa" in sq.lower() for sq in subqueries)
        assert any("tài khoản" in sq.lower() for sq in subqueries)

    def test_numbered_list_multiline(self):
        query = "1. Cách xử lý tệp bị khóa\n2. Tra cứu mã tài khoản phòng ban"
        subqueries = decompose_query(query, "vi")
        assert len(subqueries) == 2
        assert any("khóa" in sq.lower() for sq in subqueries)
        assert any("tài khoản" in sq.lower() for sq in subqueries)

    def test_inline_numbered_list(self):
        query = "1. Cách xử lý tệp bị khóa 2. Tra cứu mã tài khoản phòng ban"
        subqueries = decompose_query(query, "vi")
        assert len(subqueries) == 2
        assert any("khóa" in sq.lower() for sq in subqueries)
        assert any("tài khoản" in sq.lower() for sq in subqueries)

    def test_inline_parenthesized_list(self):
        query = "(1) Cách xử lý tệp bị khóa (2) Tra cứu mã tài khoản phòng ban"
        subqueries = decompose_query(query, "vi")
        assert len(subqueries) == 2
        assert any("khóa" in sq.lower() for sq in subqueries)
        assert any("tài khoản" in sq.lower() for sq in subqueries)

    def test_single_line_hyphen_separator(self):
        query = "Cách xử lý tệp bị khóa - Tra cứu mã tài khoản phòng ban"
        subqueries = decompose_query(query, "vi")
        assert len(subqueries) == 2
        assert any("khóa" in sq.lower() for sq in subqueries)
        assert any("tài khoản" in sq.lower() for sq in subqueries)

    def test_japanese_period_sentence_split(self):
        query = "出力先Excelファイルがロックされた場合の対処方法。勘定科目コードの特定ルールについて教えてください。"
        subqueries = decompose_query(query, "ja")
        assert len(subqueries) == 2
        assert any("ロック" in sq for sq in subqueries)
        assert any("勘定科目" in sq for sq in subqueries)

    def test_japanese_conjunction_stripping_with_ideographic_comma(self):
        raw = "また、勘定科目コードの特定ルールについて教えてください"
        normalized = _normalize_subquery_text(raw)
        assert normalized == "勘定科目コードの特定ルールについて教えてください"


# ===========================================================================
# 4. Multi-Query Retrieval Coverage & Deduplicated Merge
# ===========================================================================

class TestMultiQueryRetrievalCoverage:
    """Verify that multi-query retrieval covers all topics with zero chunk duplicates."""

    def test_compound_query_retrieves_both_topics_vi(self):
        query = "Cách xử lý tệp bị khóa và làm sao để tra cứu mã tài khoản phòng ban"
        chunks = retrieve_grounded_chunks(query, "vi")
        assert len(chunks) >= 2

        chunk_ids = [c.chunk_id for c in chunks]
        # Check deduplication: all chunk_ids must be unique
        assert len(chunk_ids) == len(set(chunk_ids))

        # Check coverage: both topics represented
        has_locked_file = any("lock" in cid.lower() or "khoa" in cid.lower() or "file" in cid.lower() for cid in chunk_ids)
        has_account_lookup = any("account" in cid.lower() or "tai_khoan" in cid.lower() or "saisan" in cid.lower() for cid in chunk_ids)
        assert has_locked_file, f"Expected locked file topic in retrieved chunks: {chunk_ids}"
        assert has_account_lookup, f"Expected account lookup topic in retrieved chunks: {chunk_ids}"

    def test_compound_query_retrieves_both_topics_en(self):
        query = "How to resolve locked output file and how do I lookup department account code?"
        chunks = retrieve_grounded_chunks(query, "en")
        assert len(chunks) >= 2

        chunk_ids = [c.chunk_id for c in chunks]
        assert len(chunk_ids) == len(set(chunk_ids))

        has_locked_file = any("lock" in cid.lower() for cid in chunk_ids)
        has_account_lookup = any("account" in cid.lower() or "lookup" in cid.lower() for cid in chunk_ids)
        assert has_locked_file, f"Expected locked file in {chunk_ids}"
        assert has_account_lookup, f"Expected account lookup in {chunk_ids}"

    def test_compound_query_retrieves_both_topics_ja(self):
        query = "出力先Excelファイルがロックされた場合の対処方法、また勘定科目コードの特定ルールについて教えてください"
        chunks = retrieve_grounded_chunks(query, "ja")
        assert len(chunks) >= 2

        chunk_ids = [c.chunk_id for c in chunks]
        assert len(chunk_ids) == len(set(chunk_ids))

        has_locked_file = any("lock" in cid.lower() for cid in chunk_ids)
        has_account_lookup = any("account" in cid.lower() or "lookup" in cid.lower() for cid in chunk_ids)
        assert has_locked_file, f"Expected locked file in {chunk_ids}"
        assert has_account_lookup, f"Expected account lookup in {chunk_ids}"

    def test_trace_contains_sub_query_metadata(self):
        query = "Cách xử lý tệp bị khóa và làm sao để tra cứu mã tài khoản phòng ban"
        traced = retrieve_grounded_chunks_with_trace(query, "vi")
        assert len(traced) >= 2

        seen_subqueries = {t.get("sub_query") for _, t in traced if "sub_query" in t}
        assert len(seen_subqueries) >= 2

    def test_merge_multi_query_chunks_deduplication(self):
        c1 = DocumentChunk(
            chunk_id="chunk_1",
            source_id="src1",
            section_title="Title 1",
            language="vi",
            business_area="ops",
            text="Text 1",
        )
        c2 = DocumentChunk(
            chunk_id="chunk_2",
            source_id="src1",
            section_title="Title 2",
            language="vi",
            business_area="ops",
            text="Text 2",
        )
        # Both sub-queries retrieved chunk_1
        res1 = [c1, c2]
        res2 = [c1]
        merged = merge_multi_query_chunks([res1, res2])
        chunk_ids = [c.chunk_id for c in merged]
        assert chunk_ids == ["chunk_1", "chunk_2"]
        assert len(chunk_ids) == len(set(chunk_ids))

    def test_merge_multi_query_chunks_fair_representation(self):
        # Even if query 1 has many chunks and query 2 has only 1, query 2's chunk must be represented
        c1 = DocumentChunk(chunk_id="chk_q1_a", source_id="s1", section_title="T1", language="vi", business_area="ops", text="A")
        c2 = DocumentChunk(chunk_id="chk_q1_b", source_id="s1", section_title="T2", language="vi", business_area="ops", text="B")
        c3 = DocumentChunk(chunk_id="chk_q1_c", source_id="s1", section_title="T3", language="vi", business_area="ops", text="C")
        c_q2 = DocumentChunk(chunk_id="chk_q2_unique", source_id="s2", section_title="T4", language="vi", business_area="ops", text="D")

        merged = merge_multi_query_chunks([[c1, c2, c3], [c_q2]], max_per_query=2, max_total=3)
        chunk_ids = [c.chunk_id for c in merged]
        assert "chk_q2_unique" in chunk_ids
        assert len(chunk_ids) <= 3

    def test_merge_multi_query_chunks_overlap_fairness(self):
        # When subqueries share top chunks, round-robin ensures both queries get distinct chunks
        c1 = DocumentChunk(chunk_id="c1", source_id="s1", section_title="T1", language="vi", business_area="ops", text="1")
        c2 = DocumentChunk(chunk_id="c2", source_id="s1", section_title="T2", language="vi", business_area="ops", text="2")
        c3 = DocumentChunk(chunk_id="c3", source_id="s1", section_title="T3", language="vi", business_area="ops", text="3")
        c4 = DocumentChunk(chunk_id="c4", source_id="s1", section_title="T4", language="vi", business_area="ops", text="4")

        # SQ1: [c1, c2, c3], SQ2: [c1, c2, c4]
        merged = merge_multi_query_chunks([[c1, c2, c3], [c1, c2, c4]], max_per_query=2, max_total=4)
        chunk_ids = [c.chunk_id for c in merged]
        assert "c3" in chunk_ids
        assert "c4" in chunk_ids
        assert len(chunk_ids) == 4
        assert len(chunk_ids) == len(set(chunk_ids))


# ===========================================================================
# 5. UI & Business Document Context Integration Tests
# ===========================================================================

class TestBusinessDocumentContextMultiQuery:
    """Verify _business_document_context formats comprehensive multi-query context."""

    def test_business_document_context_covers_both_topics(self):
        query = "Cách xử lý tệp bị khóa và làm sao để tra cứu mã tài khoản phòng ban"
        ctx = _business_document_context(query, "vi")
        assert "Nguồn tham khảo:" in ctx
        assert "Mức tin cậy:" in ctx

        # Context must contain information for both topics
        ctx_lower = ctx.lower()
        has_file_guidance = "khóa" in ctx_lower or "tệp" in ctx_lower or "excel" in ctx_lower
        has_account_guidance = "tài khoản" in ctx_lower or "nguyên giá" in ctx_lower or "mã" in ctx_lower
        assert has_file_guidance, f"Context should mention file lock guidance:\n{ctx}"
        assert has_account_guidance, f"Context should mention account lookup guidance:\n{ctx}"

    def test_business_document_context_no_internal_path_leak(self):
        query = "Cách xử lý tệp bị khóa và tra cứu mã tài khoản phòng ban"
        ctx = _business_document_context(query, "vi")
        assert "d:\\sandbox" not in ctx.lower()
        assert "traceback" not in ctx.lower()


# ===========================================================================
# 6. Multi-turn Resolution Tests
# ===========================================================================

class TestMultiTurnResolution:
    """Verify anaphoric pronoun resolution and follow-up contextualization."""

    def test_short_continuation_inherited(self):
        history = [
            {"role": "user", "content": "Lỗi file bị khóa là gì"},
            {"role": "assistant", "content": "Tệp Excel đang bị mở..."},
        ]
        resolved = resolve_multiturn_query("Nó là gì?", history, "vi")
        assert "Lỗi file bị khóa là gì" in resolved
        assert "Nó là gì?" in resolved

    def test_pronoun_in_longer_sentence_vietnamese(self):
        history = [
            {"role": "user", "content": "Quy trình xử lý tệp Excel bị khóa"},
            {"role": "assistant", "content": "Các bước xử lý..."},
        ]
        question = "Lỗi đó có làm gián đoạn quá trình phân bổ chi phí không?"
        resolved = resolve_multiturn_query(question, history, "vi")
        assert "Quy trình xử lý tệp Excel bị khóa" in resolved
        assert "Lỗi đó" in resolved

    def test_pronoun_in_english(self):
        history = [
            {"role": "user", "content": "How to resolve locked workbook errors"},
            {"role": "assistant", "content": "Please close Excel..."},
        ]
        question = "How long does it take to fix this issue?"
        resolved = resolve_multiturn_query(question, history, "en")
        assert "How to resolve locked workbook errors" in resolved

    def test_pronoun_in_japanese(self):
        history = [
            {"role": "user", "content": "出力先Excelファイルがロックされた場合の対処方法"},
            {"role": "assistant", "content": "Excelを閉じてください..."},
        ]
        question = "そのエラーの原因は何ですか？"
        resolved = resolve_multiturn_query(question, history, "ja")
        assert "出力先Excelファイルがロックされた場合の対処方法" in resolved

    def test_standalone_query_not_contaminated_vietnamese(self):
        history = [{"role": "user", "content": "Lỗi file bị khóa là gì"}]
        question = "Tra cứu mã tài khoản phòng ban"
        resolved = resolve_multiturn_query(question, history, "vi")
        assert resolved == "Tra cứu mã tài khoản phòng ban"

    def test_standalone_query_not_contaminated_japanese(self):
        history = [{"role": "user", "content": "出力先Excelファイルがロックされた場合の対処方法"}]
        question = "勘定科目コードの特定ルールについて教えてください"
        resolved = resolve_multiturn_query(question, history, "ja")
        assert resolved == "勘定科目コードの特定ルールについて教えてください"

    def test_standalone_query_not_contaminated_english(self):
        history = [{"role": "user", "content": "What is the locked file error?"}]
        question = "Department account code lookup rules"
        resolved = resolve_multiturn_query(question, history, "en")
        assert resolved == "Department account code lookup rules"

    def test_resolve_multiturn_query_idempotent(self):
        history = [{"role": "user", "content": "Lỗi file bị khóa là gì"}]
        question = "Nó là gì?"
        res1 = resolve_multiturn_query(question, history, "vi")
        res2 = resolve_multiturn_query(res1, history, "vi")
        assert res1 == res2
        assert res1.count("Lỗi file bị khóa là gì") == 1

    def test_long_prior_user_query_multiturn(self):
        long_query = (
            "Tôi đang thực hiện chạy phân bổ chi phí tháng 12 năm 2027 cho các phòng ban quản lý chung "
            "và phòng ban sản xuất nhưng gặp lỗi tệp kết quả đầu ra bị khóa khi ghi dữ liệu ra đĩa. "
            "Hệ thống báo rằng không thể truy cập vào file Excel được chỉ định trong cấu hình đường dẫn "
            "vì tệp đó đang được sử dụng bởi một ứng dụng khác."
        )
        assert len(long_query.split()) > 50
        history = [{"role": "user", "content": long_query}]
        question = "Lỗi đó xử lý thế nào?"
        resolved = resolve_multiturn_query(question, history, "vi")
        assert long_query in resolved
        assert "Lỗi đó" in resolved

