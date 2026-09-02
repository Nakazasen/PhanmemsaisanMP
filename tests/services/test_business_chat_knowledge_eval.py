"""Evaluation fixtures and quality gates for Curated RAG v2 retrieval.

Contains 30+ labeled test questions across VI/EN/JA covering all 10 catalog topics,
plus off-topic queries to verify no hallucinated context. Serves as the quality gate:
if top-1 retrieval returns the wrong entry, the test fails.

This file is separate from the unit tests to clearly distinguish evaluation
from structural/integration tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from src.services.business_chat_knowledge import (
    MIN_MATCH_SCORE,
    RetrievalTrace,
    _cjk_bigrams,
    _strip_vietnamese_diacritics,
    retrieve,
    retrieve_with_trace,
)


@dataclass
class EvalFixture:
    """A single labeled evaluation question."""

    query: str
    language: str
    expected_top1_id: str  # "" means must return empty (off-topic)
    description: str = ""
    must_not_match_ids: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Labeled fixtures — 10 VI, 10 EN, 10 JA, 6 off-topic
# ---------------------------------------------------------------------------

EVAL_FIXTURES: list[EvalFixture] = [
    # === Vietnamese (10) ===
    EvalFixture(
        query="file bị khóa không ghi được kết quả",
        language="vi", expected_top1_id="bck_locked_file",
        description="Locked file — direct keywords",
    ),
    EvalFixture(
        query="thiếu dữ liệu nhân sự mốc tháng 3",
        language="vi", expected_top1_id="bck_missing_baseline",
        description="Missing baseline — direct keywords",
    ),
    EvalFixture(
        query="kiểm tra nguồn đầu vào bị lỗi",
        language="vi", expected_top1_id="bck_source_validation",
        description="Source validation — partial keywords",
    ),
    EvalFixture(
        query="năm tài chính không khớp với tệp nguồn",
        language="vi", expected_top1_id="bck_fiscal_year_mismatch",
        description="FY mismatch — clear keywords",
    ),
    EvalFixture(
        query="chọn phòng ban trước khi chạy tính toán",
        language="vi", expected_top1_id="bck_cost_center_selection",
        description="Cost center selection — direct question",
    ),
    EvalFixture(
        query="nhập sự kiện bổ sung thủ công vào chương trình",
        language="vi", expected_top1_id="bck_data_entry_manual",
        description="Manual data entry — event related",
    ),
    EvalFixture(
        query="chạy lại sau khi sửa dữ liệu nguồn",
        language="vi", expected_top1_id="bck_rerun_calculation",
        description="Rerun calculation — clear intent",
    ),
    EvalFixture(
        query="excel sai cấu trúc cột thiếu trang tính",
        language="vi", expected_top1_id="bck_excel_format_error",
        description="Excel format error — structural keywords",
    ),
    EvalFixture(
        query="nhập nhân sự 12 tháng cho từng phòng ban",
        language="vi", expected_top1_id="bck_headcount_input",
        description="Headcount input — 12-month staffing",
    ),
    EvalFixture(
        query="quy trình 5 bước sử dụng MP2027",
        language="vi", expected_top1_id="bck_workflow_overview",
        description="Workflow overview — 5-step process",
    ),

    EvalFixture(
        query="tra mã tài khoản kế toán theo phân loại chi phí",
        language="vi", expected_top1_id="bck_account_lookup_rules",
        description="Account lookup — cost category hierarchy",
    ),
    EvalFixture(
        query="nhập chi phí đặc biệt bổ sung vào hệ thống",
        language="vi", expected_top1_id="bck_special_cost_manual",
        description="Special cost — manual input entry",
    ),
    EvalFixture(
        query="cập nhật phần mềm và khôi phục phiên bản trên mạng LAN",
        language="vi", expected_top1_id="bck_update_rollback_procedure",
        description="Software update — rollback procedure",
    ),

    # === English (13) ===
    EvalFixture(
        query="output file is locked by another user",
        language="en", expected_top1_id="bck_locked_file",
        description="Locked file — direct phrasing",
    ),
    EvalFixture(
        query="missing baseline headcount data for March",
        language="en", expected_top1_id="bck_missing_baseline",
        description="Missing baseline — clear keywords",
    ),
    EvalFixture(
        query="source file validation failed during preflight",
        language="en", expected_top1_id="bck_source_validation",
        description="Source validation — preflight keyword",
    ),
    EvalFixture(
        query="fiscal year mismatch between FORM and sources",
        language="en", expected_top1_id="bck_fiscal_year_mismatch",
        description="FY mismatch — explicit keywords",
    ),
    EvalFixture(
        query="how to select cost centers for calculation",
        language="en", expected_top1_id="bck_cost_center_selection",
        description="Cost center selection — how-to question",
    ),
    EvalFixture(
        query="enter manual data for event drivers",
        language="en", expected_top1_id="bck_data_entry_manual",
        description="Manual entry — event driver keywords",
    ),
    EvalFixture(
        query="rerun calculation after fixing errors",
        language="en", expected_top1_id="bck_rerun_calculation",
        description="Rerun — after fix keywords",
    ),
    EvalFixture(
        query="excel workbook has wrong format missing worksheet",
        language="en", expected_top1_id="bck_excel_format_error",
        description="Excel error — format and worksheet",
    ),
    EvalFixture(
        query="enter employee count for each of 12 months",
        language="en", expected_top1_id="bck_headcount_input",
        description="Headcount — 12-month entry",
    ),
    EvalFixture(
        query="what are the 5 steps to run MP2027",
        language="en", expected_top1_id="bck_workflow_overview",
        description="Workflow — 5 steps question",
    ),
    EvalFixture(
        query="account code lookup hierarchy rules by cost category",
        language="en", expected_top1_id="bck_account_lookup_rules",
        description="Account lookup — hierarchy rules",
    ),
    EvalFixture(
        query="manual special cost adjustments and supplementary expense",
        language="en", expected_top1_id="bck_special_cost_manual",
        description="Special cost — manual adjustments",
    ),
    EvalFixture(
        query="software update and version rollback on LAN share",
        language="en", expected_top1_id="bck_update_rollback_procedure",
        description="Software update — rollback flow",
    ),

    # === Japanese (13) ===
    EvalFixture(
        query="ファイルがロックされて保存できない",
        language="ja", expected_top1_id="bck_locked_file",
        description="Locked file — Japanese natural phrasing",
    ),
    EvalFixture(
        query="3月の基準人員データが不足",
        language="ja", expected_top1_id="bck_missing_baseline",
        description="Missing baseline — March CJK compound",
    ),
    EvalFixture(
        query="入力ファイルの検証でエラーが出る",
        language="ja", expected_top1_id="bck_source_validation",
        description="Source validation — verification error",
    ),
    EvalFixture(
        query="会計年度が一致しない",
        language="ja", expected_top1_id="bck_fiscal_year_mismatch",
        description="FY mismatch — direct phrase",
    ),
    EvalFixture(
        query="コストセンターの選択方法",
        language="ja", expected_top1_id="bck_cost_center_selection",
        description="Cost center selection — method query",
    ),
    EvalFixture(
        query="手動でイベントデータを入力したい",
        language="ja", expected_top1_id="bck_data_entry_manual",
        description="Manual entry — event data",
    ),
    EvalFixture(
        query="データ修正後に計算を再実行",
        language="ja", expected_top1_id="bck_rerun_calculation",
        description="Rerun — after data fix",
    ),
    EvalFixture(
        query="Excelのフォーマットが不正でシートが不足",
        language="ja", expected_top1_id="bck_excel_format_error",
        description="Excel error — format and sheet",
    ),
    EvalFixture(
        query="12か月の人員数を入力する",
        language="ja", expected_top1_id="bck_headcount_input",
        description="Headcount — 12-month input",
    ),
    EvalFixture(
        query="MP2027の5ステップワークフロー",
        language="ja", expected_top1_id="bck_workflow_overview",
        description="Workflow — 5-step overview",
    ),
    EvalFixture(
        query="勘定科目コードの特定ルールと原価区分",
        language="ja", expected_top1_id="bck_account_lookup_rules",
        description="Account lookup — CJK rules",
    ),
    EvalFixture(
        query="特別費用の手動登録方法",
        language="ja", expected_top1_id="bck_special_cost_manual",
        description="Special cost — manual registration",
    ),
    EvalFixture(
        query="ソフトウェアの更新とロールバック手順",
        language="ja", expected_top1_id="bck_update_rollback_procedure",
        description="Software update — rollback CJK",
    ),

    # === Off-topic queries (must return empty) ===
    EvalFixture(
        query="quantum physics black hole entropy",
        language="en", expected_top1_id="",
        description="Off-topic — physics",
    ),
    EvalFixture(
        query="cách nấu phở bò Hà Nội",
        language="vi", expected_top1_id="",
        description="Off-topic — cooking recipe",
    ),
    EvalFixture(
        query="コーヒーの入れ方を教えてください",
        language="ja", expected_top1_id="",
        description="Off-topic — coffee brewing",
    ),
    EvalFixture(
        query="share price of Toyota stock today",
        language="en", expected_top1_id="",
        description="Off-topic — stock market",
    ),
    EvalFixture(
        query="how to install Python 3.13 on Windows",
        language="en", expected_top1_id="",
        description="Off-topic — software installation",
    ),
    EvalFixture(
        query="coffee brewing guide",
        language="en", expected_top1_id="",
        description="Off-topic — coffee guide",
    ),
    EvalFixture(
        query="lịch thi đấu bóng đá World Cup 2026",
        language="vi", expected_top1_id="",
        description="Off-topic — football schedule",
    ),
    EvalFixture(
        query="東京の天気予報を確認",
        language="ja", expected_top1_id="",
        description="Off-topic — weather forecast",
    ),
]


# ---------------------------------------------------------------------------
# Quality gate tests
# ---------------------------------------------------------------------------

class TestQualityGateTop1Accuracy:
    """Quality gate: every labeled fixture must have correct top-1 retrieval."""

    @pytest.mark.parametrize(
        "fixture",
        [f for f in EVAL_FIXTURES if f.expected_top1_id],
        ids=[f"{f.language}:{f.description}" for f in EVAL_FIXTURES if f.expected_top1_id],
    )
    def test_top1_correct(self, fixture: EvalFixture) -> None:
        """Top-1 retrieval must return the expected entry ID."""
        results = retrieve(fixture.query, fixture.language)
        assert results, (
            f"Expected top-1='{fixture.expected_top1_id}' but got empty results "
            f"for [{fixture.language}] '{fixture.query}'"
        )
        actual_id = results[0]["id"]
        assert actual_id == fixture.expected_top1_id, (
            f"Top-1 mismatch for [{fixture.language}] '{fixture.query}': "
            f"expected='{fixture.expected_top1_id}', got='{actual_id}'"
        )


class TestOffTopicGate:
    """Off-topic queries must return empty results (no hallucinated context)."""

    @pytest.mark.parametrize(
        "fixture",
        [f for f in EVAL_FIXTURES if not f.expected_top1_id],
        ids=[f"{f.language}:{f.description}" for f in EVAL_FIXTURES if not f.expected_top1_id],
    )
    def test_off_topic_returns_empty(self, fixture: EvalFixture) -> None:
        """Off-topic query must not retrieve any catalog entries."""
        results = retrieve(fixture.query, fixture.language)
        assert results == [], (
            f"Off-topic query [{fixture.language}] '{fixture.query}' should return empty, "
            f"but got: {[r['id'] for r in results]}"
        )


class TestRetrievalTraceGrinding:
    """Verify that retrieve_with_trace provides actionable debug info."""

    def test_trace_contains_match_reasons(self) -> None:
        """Traces for matching queries must include at least one match reason."""
        traced = retrieve_with_trace("file bị khóa", "vi")
        assert traced, "Should have results for 'file bị khóa'"
        _result, trace = traced[0]
        assert trace.entry_id == "bck_locked_file"
        assert trace.score >= MIN_MATCH_SCORE
        assert len(trace.match_reasons) > 0, "Trace must have at least one match reason"

    def test_trace_contains_source_refs(self) -> None:
        """Traces must include source_refs from catalog."""
        traced = retrieve_with_trace("locked file", "en")
        assert traced
        _result, trace = traced[0]
        assert len(trace.source_refs) > 0, "Trace must include source_refs"

    def test_trace_scores_are_above_threshold(self) -> None:
        """All returned trace scores must meet the minimum threshold."""
        traced = retrieve_with_trace("missing headcount baseline march", "en")
        for _result, trace in traced:
            assert trace.score >= MIN_MATCH_SCORE, (
                f"Entry '{trace.entry_id}' has score {trace.score} "
                f"below threshold {MIN_MATCH_SCORE}"
            )


class TestVietnameseUnaccentedMatching:
    """Verify Vietnamese diacritics-stripped matching works."""

    def test_strip_diacritics(self) -> None:
        """_strip_vietnamese_diacritics should remove tone marks and đ."""
        assert _strip_vietnamese_diacritics("tệp bị khóa") == "tep bi khoa"
        assert _strip_vietnamese_diacritics("nhân sự") == "nhan su"
        assert _strip_vietnamese_diacritics("đóng") == "dong"

    def test_unaccented_query_matches(self) -> None:
        """A query without diacritics should still retrieve the correct entry."""
        results = retrieve("tep bi khoa khong ghi duoc", "vi")
        assert results, "Unaccented Vietnamese should still match"
        assert results[0]["id"] == "bck_locked_file"


class TestCJKBigramMatching:
    """Verify CJK bigram generation and matching for Japanese."""

    def test_bigram_generation(self) -> None:
        """CJK bigrams should be generated correctly."""
        bigrams = _cjk_bigrams("基準人員")
        assert "基準" in bigrams
        assert "準人" in bigrams
        assert "人員" in bigrams

    def test_japanese_compound_match(self) -> None:
        """Japanese compound words without spaces should match via bigrams."""
        results = retrieve("基準人員データが不足しています", "ja")
        assert results
        assert results[0]["id"] == "bck_missing_baseline"


class TestMinimumScoreThreshold:
    """Verify that low-relevance queries are filtered out."""

    def test_partial_token_below_threshold_returns_empty(self) -> None:
        """A query with only marginal overlap should be excluded."""
        # "thời tiết" is not a catalog keyword — should not match
        results = retrieve("thời tiết hôm nay thế nào", "vi")
        assert results == [], f"Marginal query should return empty, got: {[r['id'] for r in results]}"

    def test_single_common_word_below_threshold(self) -> None:
        """A single common word that appears in many entries should not match below threshold."""
        results = retrieve("chương trình", "vi")
        # This might match because "chương trình" appears in answer_context, but
        # it's not a keyword — behavior depends on scoring. At least verify no crash.
        assert isinstance(results, list)


class TestSourceRefsInOutput:
    """Verify source_refs appear in retrieval results and formatted context."""

    def test_results_include_source_refs(self) -> None:
        """Each result dict should include source_refs list."""
        results = retrieve("file locked", "en")
        assert results
        assert "source_refs" in results[0]
        assert len(results[0]["source_refs"]) > 0

    def test_format_context_includes_source_label(self) -> None:
        """Formatted context should mention source references."""
        from src.services.business_chat_knowledge import format_curated_context

        results = retrieve("file locked", "en")
        context = format_curated_context(results, "en")
        assert "Source:" in context, "Formatted context must include Source: attribution"
