"""Tests for MP2027 Document-grounded RAG v3 retrieval service."""

from __future__ import annotations

import pytest

from src.services.business_knowledge_index import DocumentChunk, get_knowledge_index
from src.services.business_knowledge_retrieval import (
    HybridDocumentRetrievalEngine,
    RetrievalBackend,
    format_grounded_context,
    grounded_local_fallback,
    retrieve_grounded_chunks,
    retrieve_grounded_chunks_with_trace,
)


def test_retrieval_backend_protocol_compliance():
    engine = HybridDocumentRetrievalEngine()
    assert isinstance(engine, RetrievalBackend)


def test_vietnamese_unaccented_retrieval_matches_correct_topic():
    # User asks without diacritics
    chunks = retrieve_grounded_chunks("file bi khoa", "vi", top_k=1)
    assert len(chunks) == 1
    assert "bck_locked_file" in chunks[0].chunk_id or "blocked_output_file_lock" in chunks[0].chunk_id
    assert chunks[0].language == "vi"


def test_vietnamese_unaccented_baseline_retrieval():
    chunks = retrieve_grounded_chunks("thieu nhan su thang 3", "vi", top_k=1)
    assert len(chunks) == 1
    assert "bck_missing_baseline" in chunks[0].chunk_id or "missing_staffing_baseline" in chunks[0].chunk_id


def test_japanese_query_without_spaces_matches():
    chunks = retrieve_grounded_chunks("出力先Excelファイルがロック", "ja", top_k=1)
    assert len(chunks) == 1
    assert "bck_locked_file" in chunks[0].chunk_id or "blocked_output_file_lock" in chunks[0].chunk_id
    assert chunks[0].language == "ja"


def test_japanese_account_lookup_query():
    chunks = retrieve_grounded_chunks("勘定科目コードの特定", "ja", top_k=1)
    assert len(chunks) == 1
    assert "account_lookup" in chunks[0].chunk_id


def test_english_query_retrieval():
    chunks = retrieve_grounded_chunks("missing March baseline headcount", "en", top_k=1)
    assert len(chunks) == 1
    assert "bck_missing_baseline" in chunks[0].chunk_id or "missing_staffing_baseline" in chunks[0].chunk_id
    assert chunks[0].language == "en"


def test_english_software_update_retrieval():
    chunks = retrieve_grounded_chunks("software update and version rollback", "en", top_k=1)
    assert len(chunks) == 1
    assert "bck_update_rollback_procedure" in chunks[0].chunk_id


def test_curated_cost_allocation_pack_retrieval():
    """Verify retrieval across VI, EN, JA from the curated cost allocation knowledge pack."""
    # VI
    chunks_vi = retrieve_grounded_chunks("quy trinh tinh toan phan bo chi phi mp saisan", "vi", top_k=1)
    assert len(chunks_vi) == 1
    assert "cur_saisan_purpose_and_workflow" in chunks_vi[0].chunk_id
    assert chunks_vi[0].language == "vi"

    # EN
    chunks_en = retrieve_grounded_chunks("facility and utilities cost allocation rules", "en", top_k=1)
    assert len(chunks_en) == 1
    assert "cur_saisan_facility_cost_rules" in chunks_en[0].chunk_id
    assert chunks_en[0].language == "en"

    # JA
    chunks_ja = retrieve_grounded_chunks("イベントおよび特別費用の手動入力", "ja", top_k=1)
    assert len(chunks_ja) == 1
    assert "cur_saisan_manual_input_channels" in chunks_ja[0].chunk_id
    assert chunks_ja[0].language == "ja"


def test_curated_ai_assistant_pack_retrieval():
    """Verify retrieval across VI, EN, JA from the curated AI assistant knowledge pack."""
    # VI: Copy response
    chunks_vi = retrieve_grounded_chunks("sao chep cau tra loi cua ai vao clipboard", "vi", top_k=1)
    assert len(chunks_vi) == 1
    assert "cur_ai_assistant_copy_response" in chunks_vi[0].chunk_id
    assert chunks_vi[0].language == "vi"

    # EN: Paste screenshot
    chunks_en = retrieve_grounded_chunks("paste screenshot error image into chat", "en", top_k=1)
    assert len(chunks_en) == 1
    assert "cur_ai_assistant_image_paste" in chunks_en[0].chunk_id
    assert chunks_en[0].language == "en"

    # JA: Diagnostics
    chunks_ja = retrieve_grounded_chunks("aiオペレーションアシスタントによる障害診断", "ja", top_k=1)
    assert len(chunks_ja) == 1
    assert "cur_ai_assistant_diagnostics" in chunks_ja[0].chunk_id
    assert chunks_ja[0].language == "ja"


def test_canonical_authority_boosts_over_supporting():
    # Construct two artificial chunks: one canonical, one supporting
    c_canonical = DocumentChunk(
        chunk_id="chk_canon",
        source_id="approved_business_guidance",
        section_title="Testing Cost Allocation Canonical Procedure",
        language="en",
        business_area="cost_allocation",
        text="Guidance text about cost distribution calculation.",
        safe_steps=("Do step 1",),
        keywords=("allocation", "procedure"),
        aliases=(),
        authority="canonical",
        external_shareable=True,
    )
    c_supporting = DocumentChunk(
        chunk_id="chk_supp",
        source_id="ai_operations_assistant_guide",
        section_title="Testing Cost Allocation Supporting Procedure",
        language="en",
        business_area="cost_allocation",
        text="Guidance text about cost distribution calculation.",
        safe_steps=("Do step 1",),
        keywords=("allocation", "procedure"),
        aliases=(),
        authority="supporting",
        external_shareable=True,
    )
    engine = HybridDocumentRetrievalEngine()
    score_canon, _ = engine.score_chunk(
        c_canonical, "en", "cost allocation procedure", {"cost", "allocation", "procedure"}, "", set()
    )
    score_supp, _ = engine.score_chunk(
        c_supporting, "en", "cost allocation procedure", {"cost", "allocation", "procedure"}, "", set()
    )
    assert score_canon > score_supp
    assert score_canon == score_supp + 2  # Canonical boost


def test_off_topic_query_returns_empty():
    chunks = retrieve_grounded_chunks("thoi tiet hom nay the nao tai tokyo", "vi")
    assert chunks == []

    chunks_en = retrieve_grounded_chunks("what is the recipe for chocolate cake", "en")
    assert chunks_en == []


def test_format_grounded_context_multilingual_attribution():
    chunks_vi = retrieve_grounded_chunks("tệp bị khóa", "vi", top_k=1)
    assert len(chunks_vi) > 0
    ctx_vi = format_grounded_context(chunks_vi, "vi")
    assert "Nguồn tham khảo: " in ctx_vi
    assert "Mức tin cậy: " in ctx_vi
    assert "D:\\" not in ctx_vi
    assert "traceback" not in ctx_vi.lower()

    chunks_en = retrieve_grounded_chunks("locked workbook", "en", top_k=1)
    assert len(chunks_en) > 0
    ctx_en = format_grounded_context(chunks_en, "en")
    assert "Source Reference: " in ctx_en
    assert "Confidence Level: " in ctx_en

    chunks_ja = retrieve_grounded_chunks("ファイルロック", "ja", top_k=1)
    assert len(chunks_ja) > 0
    ctx_ja = format_grounded_context(chunks_ja, "ja")
    assert "参照元: " in ctx_ja
    assert "信頼度: " in ctx_ja


def test_grounded_local_fallback_provides_safe_guidance():
    fallback_vi = grounded_local_fallback("file bi khoa", "vi")
    assert "Nguồn tham khảo: " in fallback_vi
    assert "Mức tin cậy: " in fallback_vi
    assert "1." in fallback_vi

    fallback_offtopic = grounded_local_fallback("nau an mon gi ngon", "vi")
    assert "Chưa tìm thấy hướng dẫn nội bộ phù hợp" in fallback_offtopic


# ---------------------------------------------------------------------------
# Batch 1: Staffing and Headcount Pack — 5 topics × 3 languages
# ---------------------------------------------------------------------------

class TestStaffingHeadcountPackRetrieval:
    """Benchmark queries for curated staffing_and_headcount_pack."""

    def test_vi_admin_consumables_12month(self):
        chunks = retrieve_grounded_chunks("phân bổ vật tư hành chính 12 tháng theo số người", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_admin_consumables_12month" in chunks[0].chunk_id

    def test_en_admin_consumables_12month(self):
        chunks = retrieve_grounded_chunks("admin consumables per person allocation previous month headcount", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_admin_consumables_12month" in chunks[0].chunk_id

    def test_ja_admin_consumables_12month(self):
        chunks = retrieve_grounded_chunks("管理消耗品の12か月配賦ルール前月人員数", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_admin_consumables_12month" in chunks[0].chunk_id

    def test_vi_bus_transportation(self):
        chunks = retrieve_grounded_chunks("chi phí xe bus đưa đón người biệt phái", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_bus_transportation_cost" in chunks[0].chunk_id

    def test_en_bus_transportation(self):
        chunks = retrieve_grounded_chunks("employee bus transportation shuttle cost expat", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_bus_transportation_cost" in chunks[0].chunk_id

    def test_ja_bus_transportation(self):
        chunks = retrieve_grounded_chunks("出向者バス送迎費用の計算", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_bus_transportation_cost" in chunks[0].chunk_id

    def test_vi_new_employee_costs(self):
        chunks = retrieve_grounded_chunks("chi phí nhân viên mới sổ tay khám sức khỏe", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_new_employee_costs" in chunks[0].chunk_id

    def test_en_new_employee_costs(self):
        chunks = retrieve_grounded_chunks("new employee notebook hiring medical check cost", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_new_employee_costs" in chunks[0].chunk_id

    def test_ja_new_employee_costs(self):
        chunks = retrieve_grounded_chunks("新入社員手帳と採用時健康診断の費用", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_new_employee_costs" in chunks[0].chunk_id

    def test_vi_staffing_override(self):
        chunks = retrieve_grounded_chunks("ghi đè mốc nhân sự cơ sở trong cài đặt", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_staffing_override_settings" in chunks[0].chunk_id

    def test_en_staffing_override(self):
        chunks = retrieve_grounded_chunks("staffing baseline override settings headcount", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_staffing_override_settings" in chunks[0].chunk_id

    def test_ja_staffing_override(self):
        chunks = retrieve_grounded_chunks("基準人員オーバーライド設定の変更方法", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_staffing_override_settings" in chunks[0].chunk_id

    def test_vi_source_file_order(self):
        chunks = retrieve_grounded_chunks("thứ tự xử lý file nguồn và dòng phân cách", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_source_file_order_rule" in chunks[0].chunk_id

    def test_en_source_file_order(self):
        chunks = retrieve_grounded_chunks("source file processing order separator row blank row between groups", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_source_file_order_rule" in chunks[0].chunk_id

    def test_ja_source_file_order(self):
        chunks = retrieve_grounded_chunks("ソースファイルの処理順序と区切り行ルール", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_source_file_order_rule" in chunks[0].chunk_id


# ---------------------------------------------------------------------------
# Batch 2: Calculation and Output Pack — 6 topics × 3 languages
# ---------------------------------------------------------------------------

class TestCalculationOutputPackRetrieval:
    """Benchmark queries for curated calculation_and_output_pack."""

    def test_vi_system_cost(self):
        chunks = retrieve_grounded_chunks("chi phí hệ thống 3 kỳ mô phỏng tháng 4 đến tháng 6", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_system_cost_combined" in chunks[0].chunk_id

    def test_en_system_cost(self):
        chunks = retrieve_grounded_chunks("system IT cost three simulation periods April June", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_system_cost_combined" in chunks[0].chunk_id

    def test_en_production_system_cost_account_mapping(self):
        chunks = retrieve_grounded_chunks(
            "Which account code should be used for production system costs?",
            "en",
            top_k=1,
        )
        assert len(chunks) == 1
        assert "cur_system_cost_account_mapping" in chunks[0].chunk_id

    def test_ja_system_cost(self):
        chunks = retrieve_grounded_chunks("システム費用3期間シミュレーション計算", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_system_cost_combined" in chunks[0].chunk_id

    def test_vi_fixed_asset(self):
        chunks = retrieve_grounded_chunks("khấu hao lãi tài sản cố định theo tháng", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_fixed_asset_depreciation" in chunks[0].chunk_id

    def test_en_fixed_asset(self):
        chunks = retrieve_grounded_chunks("fixed asset depreciation and interest rules monthly", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_fixed_asset_depreciation" in chunks[0].chunk_id

    def test_ja_fixed_asset(self):
        chunks = retrieve_grounded_chunks("固定資産の減価償却と利息ルール", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_fixed_asset_depreciation" in chunks[0].chunk_id

    def test_vi_birthday_cost(self):
        chunks = retrieve_grounded_chunks("chi phí sinh nhật nhân viên số người nhân đơn giá", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_birthday_cost" in chunks[0].chunk_id

    def test_en_birthday_cost(self):
        chunks = retrieve_grounded_chunks("employee birthday cost calculation headcount unit price", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_birthday_cost" in chunks[0].chunk_id

    def test_ja_birthday_cost(self):
        chunks = retrieve_grounded_chunks("従業員誕生日費用の計算ルール", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_birthday_cost" in chunks[0].chunk_id

    def test_vi_nnn_paperwork(self):
        chunks = retrieve_grounded_chunks("chi phí giấy tờ cho người nước ngoài NNN visa", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_nnn_paperwork_cost" in chunks[0].chunk_id

    def test_en_nnn_paperwork(self):
        chunks = retrieve_grounded_chunks("NNN foreigner paperwork visa work permit cost", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_nnn_paperwork_cost" in chunks[0].chunk_id

    def test_ja_nnn_paperwork(self):
        chunks = retrieve_grounded_chunks("外国人書類作成費用NNNビザ労働許可", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_nnn_paperwork_cost" in chunks[0].chunk_id

    def test_vi_allocation_travel(self):
        chunks = retrieve_grounded_chunks("chi phí phân bổ chung đi lại công tác giữa phòng ban", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_allocation_travel_shared" in chunks[0].chunk_id

    def test_en_allocation_travel(self):
        chunks = retrieve_grounded_chunks("shared allocation travel cross-department cost", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_allocation_travel_shared" in chunks[0].chunk_id

    def test_ja_allocation_travel(self):
        chunks = retrieve_grounded_chunks("共有配賦費用と出張費部門間", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_allocation_travel_shared" in chunks[0].chunk_id

    def test_vi_fiscal_year(self):
        chunks = retrieve_grounded_chunks("năm tài chính tháng 4 đến tháng 3 lịch FY2027", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_fiscal_year_calendar" in chunks[0].chunk_id

    def test_en_fiscal_year(self):
        chunks = retrieve_grounded_chunks("fiscal year calendar April to March FY2027 12 months", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_fiscal_year_calendar" in chunks[0].chunk_id

    def test_ja_fiscal_year(self):
        chunks = retrieve_grounded_chunks("会計年度カレンダー4月から3月FY2027", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_fiscal_year_calendar" in chunks[0].chunk_id


# ---------------------------------------------------------------------------
# Batch 3: Common Operational Errors Pack — 3 topics × 3 languages
# ---------------------------------------------------------------------------

class TestOperationalErrorsPackRetrieval:
    """Benchmark queries for curated common_operational_errors_pack."""

    def test_vi_output_format(self):
        chunks = retrieve_grounded_chunks("bảo toàn định dạng màu sắc công thức bảng tính", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_output_format_preservation" in chunks[0].chunk_id

    def test_en_output_format(self):
        chunks = retrieve_grounded_chunks("output workbook format preservation colors formulas FORM", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_output_format_preservation" in chunks[0].chunk_id

    def test_ja_output_format(self):
        chunks = retrieve_grounded_chunks("出力ワークブック書式保持色数式テンプレート", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_output_format_preservation" in chunks[0].chunk_id

    def test_vi_provenance_labels(self):
        chunks = retrieve_grounded_chunks("nhãn nguồn gốc dữ liệu trên kết quả gốc tham khảo nhập tay", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_provenance_labels_operators" in chunks[0].chunk_id

    def test_en_provenance_labels(self):
        chunks = retrieve_grounded_chunks("data provenance labels source derived reference manual input", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_provenance_labels_operators" in chunks[0].chunk_id

    def test_ja_provenance_labels(self):
        chunks = retrieve_grounded_chunks("データ出所ラベル ソース由来 参照 手動入力", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_provenance_labels_operators" in chunks[0].chunk_id

    def test_vi_run_history(self):
        chunks = retrieve_grounded_chunks("trạng thái lần chạy FAILED SUCCEEDED lịch sử", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_run_history_statuses" in chunks[0].chunk_id

    def test_en_run_history(self):
        chunks = retrieve_grounded_chunks("run history status SUCCEEDED FAILED PRECHECK_FAILED", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_run_history_statuses" in chunks[0].chunk_id

    def test_ja_run_history(self):
        chunks = retrieve_grounded_chunks("実行履歴ステータスの読み方 SUCCEEDED FAILED", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_run_history_statuses" in chunks[0].chunk_id


# ---------------------------------------------------------------------------
# Batch 4: Expanded Business Topics Retrieval Tests
# ---------------------------------------------------------------------------

class TestExpandedBusinessTopicsRetrieval:
    """Benchmark tests for newly curated business operational topics."""

    def test_vi_special_cost_inheritance(self):
        chunks = retrieve_grounded_chunks("kế thừa bảo tồn chi phí riêng theo năm tài chính mới", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_manual_special_cost_inheritance" in chunks[0].chunk_id

    def test_en_special_cost_inheritance(self):
        chunks = retrieve_grounded_chunks("manual special cost inheritance across fiscal years rollover", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_manual_special_cost_inheritance" in chunks[0].chunk_id

    def test_ja_special_cost_inheritance(self):
        chunks = retrieve_grounded_chunks("年度間における個別手動費用の継承と保持 金額クリア", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_manual_special_cost_inheritance" in chunks[0].chunk_id

    def test_vi_cost_row_reordering(self):
        chunks = retrieve_grounded_chunks("tùy biến sắp xếp thứ tự dòng chi phí kéo thả", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_output_cost_row_reordering" in chunks[0].chunk_id

    def test_en_cost_row_reordering(self):
        chunks = retrieve_grounded_chunks("custom drag and drop cost row reordering dialog", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_output_cost_row_reordering" in chunks[0].chunk_id

    def test_ja_cost_row_reordering(self):
        chunks = retrieve_grounded_chunks("ドラッグ＆ドロップによる費用行順序の並び替え", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_output_cost_row_reordering" in chunks[0].chunk_id

    def test_vi_quick_search_departments(self):
        chunks = retrieve_grounded_chunks("tìm kiếm nhanh phòng ban trên màn hình chính", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_quick_search_departments" in chunks[0].chunk_id

    def test_en_quick_search_departments(self):
        chunks = retrieve_grounded_chunks("quick department search on main screen cost center filter", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_quick_search_departments" in chunks[0].chunk_id

    def test_ja_quick_search_departments(self):
        chunks = retrieve_grounded_chunks("メイン画面での部門クイック検索機能 リアルタイム", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_quick_search_departments" in chunks[0].chunk_id

    def test_vi_budget_variance_yoy(self):
        chunks = retrieve_grounded_chunks("so sánh biến động ngân sách cùng kỳ YoY biểu đồ", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_budget_variance_yoy_analysis" in chunks[0].chunk_id

    def test_en_budget_variance_yoy(self):
        chunks = retrieve_grounded_chunks("year over year YoY budget variance analysis and charts", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_budget_variance_yoy_analysis" in chunks[0].chunk_id

    def test_ja_budget_variance_yoy(self):
        chunks = retrieve_grounded_chunks("前年同期比 YoY 予算変動分析と視覚的グラフ", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_budget_variance_yoy_analysis" in chunks[0].chunk_id

    def test_vi_uniform_and_cups(self):
        chunks = retrieve_grounded_chunks("quy tắc cấp phát đồng phục và cốc xếp định kỳ", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_uniform_and_folding_cups" in chunks[0].chunk_id

    def test_en_uniform_and_cups(self):
        chunks = retrieve_grounded_chunks("uniform allocation and periodic folding cup rules", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_uniform_and_folding_cups" in chunks[0].chunk_id

    def test_ja_uniform_and_cups(self):
        chunks = retrieve_grounded_chunks("制服および折りたたみコップの支給ルール 半袖長袖", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_uniform_and_folding_cups" in chunks[0].chunk_id

    def test_vi_legacy_staffing_exclusion(self):
        chunks = retrieve_grounded_chunks("không cần điền 2 dữ liệu nhân sự cũ biệt phái local", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_legacy_staffing_exclusion" in chunks[0].chunk_id

    def test_en_legacy_staffing_exclusion(self):
        chunks = retrieve_grounded_chunks("exclusion rule for 2 legacy staffing rows expat local", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_legacy_staffing_exclusion" in chunks[0].chunk_id

    def test_ja_legacy_staffing_exclusion(self):
        chunks = retrieve_grounded_chunks("旧人員2行 出向社員 ローカル社員 入力不要ルール", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_legacy_staffing_exclusion" in chunks[0].chunk_id

    def test_vi_claim_col_e(self):
        chunks = retrieve_grounded_chunks("cột E không được phép tồn tại mô tả giải thích claim 12", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_claim_col_e_no_description" in chunks[0].chunk_id

    def test_en_claim_col_e(self):
        chunks = retrieve_grounded_chunks("column E must not contain custom explanations Claim 12", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_claim_col_e_no_description" in chunks[0].chunk_id

    def test_ja_claim_col_e(self):
        chunks = retrieve_grounded_chunks("E列に自由記述の説明解説を配置しない Claim 12", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_claim_col_e_no_description" in chunks[0].chunk_id

    def test_vi_actual_distribution_count(self):
        chunks = retrieve_grounded_chunks("23 chi phí cấp phát thực tế 配布数 nhập số lượng phát thật", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_claim_actual_distribution_count_rule" in chunks[0].chunk_id

    def test_en_actual_distribution_count(self):
        chunks = retrieve_grounded_chunks("rule for 23 actual distribution cost items requiring real counts", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_claim_actual_distribution_count_rule" in chunks[0].chunk_id

    def test_ja_actual_distribution_count(self):
        chunks = retrieve_grounded_chunks("実際の配布数を必要とする23の配布数費用項目ルール", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_claim_actual_distribution_count_rule" in chunks[0].chunk_id


# ---------------------------------------------------------------------------
# Batch 5: Reference with Caveat Topics Retrieval Tests (Owner Decision)
# ---------------------------------------------------------------------------

class TestReferenceWithCaveatTopicsRetrieval:
    """Benchmark tests for 12 newly promoted reference_with_caveat operational topics."""

    def test_vi_custom_headcount(self):
        chunks = retrieve_grounded_chunks("khoản chi có số người riêng đặc thù custom headcount", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_special_cost_custom_headcount" in chunks[0].chunk_id
        assert chunks[0].authority in ("caveat", "reference_with_caveat")

    def test_en_custom_headcount(self):
        chunks = retrieve_grounded_chunks("special cost allocation custom headcount participant rule", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_special_cost_custom_headcount" in chunks[0].chunk_id

    def test_ja_custom_headcount(self):
        chunks = retrieve_grounded_chunks("個別人員数を指定する特別費用の配賦ルール", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_special_cost_custom_headcount" in chunks[0].chunk_id

    def test_vi_birthday_row_conflict(self):
        chunks = retrieve_grounded_chunks("xung đột dòng FORM sinh nhật dòng 63 hay dòng 59", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_birthday_form_row_conflict" in chunks[0].chunk_id

    def test_en_birthday_row_conflict(self):
        chunks = retrieve_grounded_chunks("birthday cost form row reconciliation row 63 vs row 59", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_birthday_form_row_conflict" in chunks[0].chunk_id

    def test_ja_birthday_row_conflict(self):
        chunks = retrieve_grounded_chunks("誕生日費用 FORM行番号照合 63行目 59行目", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_birthday_form_row_conflict" in chunks[0].chunk_id

    def test_vi_claim_pen_stationery(self):
        chunks = retrieve_grounded_chunks("dòng pen bút thiếu dữ liệu cột C D điền mã tài khoản", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_claim_pen_stationery_account_fill" in chunks[0].chunk_id

    def test_en_claim_pen_stationery(self):
        chunks = retrieve_grounded_chunks("stationery pen line account code resolution missing columns c d", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_claim_pen_stationery_account_fill" in chunks[0].chunk_id

    def test_ja_claim_pen_stationery(self):
        chunks = retrieve_grounded_chunks("ペン 行の勘定科目コード補完対応 CD列不足", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_claim_pen_stationery_account_fill" in chunks[0].chunk_id

    def test_vi_claim_system_q1(self):
        chunks = retrieve_grounded_chunks("claim 14 code 5005246282 chỉ chạy tháng 4 đến tháng 6 quý 1", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_claim_system_cost_q1_simulation" in chunks[0].chunk_id

    def test_en_claim_system_q1(self):
        chunks = retrieve_grounded_chunks("system cost code 5005246282 q1 simulation april june claim 14", "en", top_k=1)
        assert len(chunks) == 1
        assert "cur_claim_system_cost_q1_simulation" in chunks[0].chunk_id

    def test_ja_claim_system_q1(self):
        chunks = retrieve_grounded_chunks("システム費コード5005246282 第1四半期シミュレーション 4月から6月", "ja", top_k=1)
        assert len(chunks) == 1
        assert "cur_claim_system_cost_q1_simulation" in chunks[0].chunk_id

    def test_vi_claim_duplicate_cost_rows(self):
        chunks = retrieve_grounded_chunks("chuẩn hóa dòng chi phí trùng lặp 64 69 và 30 35 claim 18", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_claim_duplicate_cost_row_standardization" in chunks[0].chunk_id

    def test_vi_claim_blank_rows(self):
        chunks = retrieve_grounded_chunks("dòng chi phí trống 73 74 75 biểu mẫu form claim 19", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_claim_blank_cost_rows_73_75" in chunks[0].chunk_id

    def test_vi_target_cell_ranges(self):
        chunks = retrieve_grounded_chunks("vùng ô và dòng kết quả FORM target rows cell ranges", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_target_output_cell_ranges" in chunks[0].chunk_id

    def test_vi_event_driver_standards(self):
        chunks = retrieve_grounded_chunks("định mức và động lực phân bổ sự kiện event drivers theo tháng", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_event_driver_standards" in chunks[0].chunk_id

    def test_vi_fixed_assets_audit(self):
        chunks = retrieve_grounded_chunks("lịch sử đối soát và kiểm toán tài sản cố định khấu hao", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_fixed_assets_audit_history" in chunks[0].chunk_id

    def test_vi_module_implementation_status(self):
        chunks = retrieve_grounded_chunks("bảng theo dõi trạng thái các module phân bổ chi phí tiến độ", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_module_implementation_status" in chunks[0].chunk_id

    def test_vi_roadmap_operational_priorities(self):
        chunks = retrieve_grounded_chunks("danh mục ưu tiên hoàn thiện nghiệp vụ vận hành lộ trình", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_roadmap_operational_priorities" in chunks[0].chunk_id

    def test_vi_saisan_dashboard(self):
        chunks = retrieve_grounded_chunks("bảng trạng thái hoàn thiện tổng thể MP Saisan dashboard", "vi", top_k=1)
        assert len(chunks) == 1
        assert "cur_saisan_implementation_dashboard" in chunks[0].chunk_id

    def test_local_fallback_formats_attribution_and_confidence(self):
        from src.services.business_knowledge_retrieval import grounded_local_fallback

        # Test caveat topic produces "Tham khảo nội bộ"
        ans_caveat = grounded_local_fallback("khoản chi có số người riêng", "vi")
        assert "Nguồn tham khảo:" in ans_caveat
        assert "Mức tin cậy: Tham khảo nội bộ" in ans_caveat
        assert "D:\\" not in ans_caveat
        assert ".json" not in ans_caveat

        # Test canonical topic produces "Đã xác nhận"
        ans_canonical = grounded_local_fallback("quy trình tính toán phân bổ chi phí mp saisan", "vi")
        assert "Nguồn tham khảo:" in ans_canonical
        assert "Mức tin cậy: Đã xác nhận" in ans_canonical
        assert "D:\\" not in ans_canonical
        assert ".json" not in ans_canonical


class TestEndToEndPackAcceptanceScenarios:
    """Acceptance scenarios verifying that answers across all packs and languages
    contain direct business explanations, clean citations, confidence levels, and zero technical leakage."""

    @pytest.mark.parametrize(
        "query,lang,expected_topic,expected_kw,citation_prefix,expected_conf",
        [
            # Pack 1: Cost Allocation (VI, EN, JA)
            (
                "quy trình tính toán phân bổ chi phí mp saisan",
                "vi",
                "cur_saisan_purpose_and_workflow",
                "MP Saisan",
                "Nguồn tham khảo:",
                "Mức tin cậy: Đã xác nhận",
            ),
            (
                "facility utilities cost allocation 6 items",
                "en",
                "cur_saisan_facility_cost_rules",
                "facility",
                "Source Reference:",
                "Confidence Level: Confirmed",
            ),
            (
                "コストセンターと部門の階層構造 1412000040",
                "ja",
                "cur_saisan_cost_center_hierarchy",
                "コストセンター",
                "参照元:",
                "信頼度: 確定",
            ),
            # Pack 2: Staffing & Headcount (VI, EN, JA)
            (
                "định mức cấp phát đồng phục và cốc gấp định kỳ",
                "vi",
                "cur_uniform_and_folding_cups",
                "đồng phục",
                "Nguồn tham khảo:",
                "Mức tin cậy: Đã xác nhận",
            ),
            (
                "exclusion rule for 2 legacy staffing rows expat local",
                "en",
                "cur_legacy_staffing_exclusion",
                "staffing",
                "Source Reference:",
                "Confidence Level: Confirmed",
            ),
            (
                "新入社員の社員手帳と採用時健康診断費用",
                "ja",
                "cur_new_employee_costs",
                "新入社員",
                "参照元:",
                "信頼度: 確定",
            ),
            # Pack 3: Calculation & Output (VI, EN, JA)
            (
                "kế thừa bảo tồn chi phí riêng theo từng phòng ban",
                "vi",
                "cur_manual_special_cost_inheritance",
                "kế thừa",
                "Nguồn tham khảo:",
                "Mức tin cậy: Đã xác nhận",
            ),
            (
                "fixed assets depreciation allocation logic",
                "en",
                "cur_fixed_asset_depreciation",
                "depreciation",
                "Source Reference:",
                "Confidence Level: Confirmed",
            ),
            (
                "システム費用の結合および配賦ロジック",
                "ja",
                "cur_system_cost_combined",
                "システム",
                "参照元:",
                "信頼度: 確定",
            ),
            # Pack 4: Common Operational Errors & User Claims (VI, EN, JA)
            (
                "cột E không được phép tồn tại mô tả giải thích claim 12",
                "vi",
                "cur_claim_col_e_no_description",
                "cột E",
                "Nguồn tham khảo:",
                "Mức tin cậy: Đã xác nhận",
            ),
            (
                "rule for 23 actual distribution cost items requiring real counts",
                "en",
                "cur_claim_actual_distribution_count_rule",
                "distribution",
                "Source Reference:",
                "Confidence Level: Confirmed",
            ),
            (
                "健康診断費用の2回重複バグ防止ルール",
                "ja",
                "cur_claim_medical_check_dedup",
                "健康診断",
                "参照元:",
                "信頼度: 確定",
            ),
            # Pack 5: Reference with Caveat Topics (VI, EN, JA)
            (
                "khoản chi có số người riêng đặc thù custom headcount",
                "vi",
                "cur_special_cost_custom_headcount",
                "số người",
                "Nguồn tham khảo:",
                "Mức tin cậy: Tham khảo nội bộ",
            ),
            (
                "birthday cost form row reconciliation row 63 vs row 59",
                "en",
                "cur_birthday_form_row_conflict",
                "birthday",
                "Source Reference:",
                "Confidence Level: Internal Reference",
            ),
            (
                "システム費コード5005246282 第1四半期シミュレーション",
                "ja",
                "cur_claim_system_cost_q1_simulation",
                "シミュレーション",
                "参照元:",
                "信頼度: 社内参考",
            ),
            # Operational Error Models (VI, EN, JA)
            (
                "lỗi file bị khóa không ghi được kết quả",
                "vi",
                "bck_locked_file",
                "kết quả",
                "Nguồn tham khảo:",
                "Mức tin cậy: Đã xác nhận",
            ),
            (
                "how to fix missing March baseline headcount",
                "en",
                "bck_missing_baseline",
                "baseline",
                "Source Reference:",
                "Confidence Level: Confirmed",
            ),
            (
                "ai制限事項 禁止事項 外部通信禁止",
                "ja",
                "cur_ai_assistant_explicit_boundaries",
                "安全境界",
                "参照元:",
                "信頼度: 確定",
            ),
        ],
    )
    def test_acceptance_scenario_response_quality_and_clean_citation(
        self, query, lang, expected_topic, expected_kw, citation_prefix, expected_conf
    ):
        from src.services.business_knowledge_retrieval import (
            grounded_local_fallback,
            retrieve_grounded_chunks,
        )

        chunks = retrieve_grounded_chunks(query, lang, top_k=1)
        assert len(chunks) == 1
        assert expected_topic in chunks[0].chunk_id or expected_topic == chunks[0].source_id

        answer = grounded_local_fallback(query, lang)
        lower_ans = answer.lower()

        # 1. Answer has direct business content
        assert expected_kw.lower() in lower_ans

        # 2. Citation format and confidence level
        assert citation_prefix in answer
        assert expected_conf in answer

        # 3. Invariant: Absolute zero technical leakage
        forbidden = ("d:\\", "c:\\", ".json", ".md", "traceback", "cagent", "c-agent", "function", "def ")
        for token in forbidden:
            assert token not in lower_ans


    def test_dynamic_citation_selection_for_different_queries_in_same_topic(self):
        """Verify that distinct questions targeting different facets of the same topic
        dynamically select the specific matching heading citation."""
        from src.services.business_knowledge_retrieval import (
            format_grounded_context,
            select_relevant_citations,
        )
        from src.services.business_knowledge_index import DocumentChunk

        # 1. Direct unit test of select_relevant_citations on multiple citations
        citations = (
            {
                "display_title": "Quy trình nghiệp vụ MP2027",
                "heading_title": "Mô hình thư mục và đường dẫn nhập thủ công",
                "supported_summary": "Mô tả cấu trúc thư mục làm việc và kênh nhập dữ liệu qua CSV/Excel.",
                "classification": "covered",
            },
            {
                "display_title": "Quy trình nghiệp vụ MP2027",
                "heading_title": "Quy tắc nhập dữ liệu thủ công an toàn",
                "supported_summary": "Hướng dẫn người dùng nhập số liệu nhân sự qua giao diện với cơ chế kiểm tra tính hợp lệ.",
                "classification": "covered",
            },
        )

        selected_q1 = select_relevant_citations(citations, question="cấu trúc thư mục runtime layout và đường dẫn", language="vi")
        assert len(selected_q1) >= 1
        assert selected_q1[0]["heading_title"] == "Mô hình thư mục và đường dẫn nhập thủ công"

        selected_q2 = select_relevant_citations(citations, question="quy tắc kiểm tra hợp lệ khi nhập số liệu an toàn", language="vi")
        assert len(selected_q2) >= 1
        assert selected_q2[0]["heading_title"] == "Quy tắc nhập dữ liệu thủ công an toàn"

        # 2. Integration test via format_grounded_context with question parameter
        chunk = DocumentChunk(
            chunk_id="chk_test_multiple_citations_vi",
            source_id="curated_cost_allocation_guidance",
            section_title="Kênh nhập dữ liệu thủ công",
            language="vi",
            business_area="operations",
            text="Nội dung hướng dẫn nhập liệu.",
            safe_steps=(),
            keywords=(),
            aliases=(),
            authority="canonical",
            external_shareable=True,
            evidence_citations=citations,
        )

        ctx_q1 = format_grounded_context([chunk], language="vi", question="cấu trúc thư mục layout")
        assert "Mô hình thư mục và đường dẫn nhập thủ công" in ctx_q1

        ctx_q2 = format_grounded_context([chunk], language="vi", question="quy tắc kiểm tra an toàn")
        assert "Quy tắc nhập dữ liệu thủ công an toàn" in ctx_q2


    def test_dynamic_citation_selection_on_actual_curated_pack_multi_refs(self):
        """Verify dynamic citation selection on REAL curated packs loaded from disk (non-synthetic)."""
        from src.services.business_knowledge_retrieval import (
            format_grounded_context,
            select_relevant_citations,
        )
        from src.services.business_knowledge_index import get_knowledge_index

        chunks = get_knowledge_index()
        # Find real chunk with multiple citations
        multi_ref_chunks = [c for c in chunks if len(c.evidence_citations) >= 2]
        assert len(multi_ref_chunks) > 0, "Expected at least one real chunk with multiple evidence citations"

        target_chunk = next(c for c in multi_ref_chunks if "cur_saisan_manual_input_channels" in c.chunk_id and c.language == "vi")
        assert len(target_chunk.evidence_citations) >= 2

        # Query 1 focuses on runtime directory and CSV layout
        q1 = "cấu trúc thư mục runtime layout và đường dẫn file CSV"
        sel1 = select_relevant_citations(target_chunk.evidence_citations, question=q1, language="vi")
        ctx1 = format_grounded_context([target_chunk], language="vi", question=q1)
        assert len(sel1) >= 1
        assert "Mô hình thư mục và đường dẫn nhập thủ công" in sel1[0]["heading_title"]
        assert "Mô hình thư mục và đường dẫn nhập thủ công" in ctx1

        # Query 2 focuses on safe manual entry rules and pre-save validation
        q2 = "quy tắc nhập dữ liệu thủ công an toàn kiểm tra hợp lệ"
        sel2 = select_relevant_citations(target_chunk.evidence_citations, question=q2, language="vi")
        ctx2 = format_grounded_context([target_chunk], language="vi", question=q2)
        assert len(sel2) >= 1
        assert "Quy tắc nhập dữ liệu thủ công an toàn" in sel2[0]["heading_title"]
        assert "Quy tắc nhập dữ liệu thủ công an toàn" in ctx2

        # Distinct headings chosen from the same real pack chunk
        assert sel1[0]["heading_title"] != sel2[0]["heading_title"]


    def test_all_evidence_refs_section_scoped_body_anchors(self):
        """Verify that EVERY evidence reference across all real curated packs and knowledge catalog
        has an anchor (15-50 chars) located strictly within its section body slice on disk."""
        import json
        from pathlib import Path
        from scripts.generate_evidence_ref_semantics import (
            REPO_ROOT,
            clean_heading_text,
            extract_section_body_slice,
        )

        all_refs = []
        curated_dir = REPO_ROOT / "docs" / "knowledge" / "business_chat" / "curated"
        for pf in sorted(curated_dir.glob("*.json")):
            pdata = json.loads(pf.read_text(encoding="utf-8"))
            for entry in pdata.get("entries", []):
                all_refs.extend(entry.get("evidence_refs", []))

        cat_path = REPO_ROOT / "docs" / "knowledge" / "business_chat" / "knowledge_catalog.json"
        cat_data = json.loads(cat_path.read_text(encoding="utf-8"))
        for entry in cat_data.get("entries", []):
            all_refs.extend(entry.get("evidence_refs", []))

        assert len(all_refs) > 0

        anchor_failures = []
        for ref in all_refs:
            sp = ref.get("source_path", "")
            sec = ref.get("source_section", "")
            anchor = ref.get("evidence_anchor", "")
            clean_h = clean_heading_text(sec).lower()

            if not anchor or not isinstance(anchor, str):
                anchor_failures.append((sp, sec, "Missing anchor"))
                continue

            if len(anchor) < 15 or len(anchor) > 50:
                anchor_failures.append((sp, sec, f"Invalid anchor length {len(anchor)}: '{anchor}'"))
                continue

            if anchor == sec or anchor.lower() == clean_h:
                anchor_failures.append((sp, sec, f"Anchor equals heading: '{anchor}'"))
                continue

            body_slice = extract_section_body_slice(sp, sec)
            if anchor not in body_slice:
                anchor_failures.append((sp, sec, f"Anchor not found in section body slice: '{anchor}'"))

        assert anchor_failures == [], f"Found {len(anchor_failures)} anchor failures:\n" + "\n".join(str(f) for f in anchor_failures[:10])


    def test_zero_forbidden_template_summaries_in_all_packs(self):
        """Verify that zero evidence references contain generic forbidden template phrases in VI, EN, or JA."""
        import json
        from pathlib import Path
        from scripts.generate_evidence_ref_semantics import (
            EXPANDED_FORBIDDEN_TEMPLATES,
            REPO_ROOT,
            SUPPORTED_LANGUAGES,
        )

        all_refs = []
        curated_dir = REPO_ROOT / "docs" / "knowledge" / "business_chat" / "curated"
        for pf in sorted(curated_dir.glob("*.json")):
            pdata = json.loads(pf.read_text(encoding="utf-8"))
            for entry in pdata.get("entries", []):
                all_refs.extend(entry.get("evidence_refs", []))

        cat_path = REPO_ROOT / "docs" / "knowledge" / "business_chat" / "knowledge_catalog.json"
        cat_data = json.loads(cat_path.read_text(encoding="utf-8"))
        for entry in cat_data.get("entries", []):
            all_refs.extend(entry.get("evidence_refs", []))

        template_matches = []
        for ref in all_refs:
            ss = ref.get("supported_summary", {})
            sp = ref.get("source_path", "")
            sec = ref.get("source_section", "")
            for l in SUPPORTED_LANGUAGES:
                val = ss.get(l, "")
                for ft in EXPANDED_FORBIDDEN_TEMPLATES:
                    if ft.lower() in val.lower():
                        template_matches.append((sp, sec, l, ft, val))

        assert template_matches == [], f"Found {len(template_matches)} forbidden template matches:\n" + "\n".join(str(m) for m in template_matches[:10])


    def test_all_evidence_refs_natural_heading_translations(self):
        """Verify that EN and JA heading translations are natural and not raw copy-pastes of VI headings."""
        import json
        from pathlib import Path
        from scripts.generate_evidence_ref_semantics import REPO_ROOT

        all_refs = []
        curated_dir = REPO_ROOT / "docs" / "knowledge" / "business_chat" / "curated"
        for pf in sorted(curated_dir.glob("*.json")):
            pdata = json.loads(pf.read_text(encoding="utf-8"))
            for entry in pdata.get("entries", []):
                all_refs.extend(entry.get("evidence_refs", []))

        cat_path = REPO_ROOT / "docs" / "knowledge" / "business_chat" / "knowledge_catalog.json"
        cat_data = json.loads(cat_path.read_text(encoding="utf-8"))
        for entry in cat_data.get("entries", []):
            all_refs.extend(entry.get("evidence_refs", []))

        copy_paste_headings = []
        for ref in all_refs:
            ht = ref.get("heading_title", {})
            sp = ref.get("source_path", "")
            sec = ref.get("source_section", "")
            vi_h = ht.get("vi", "").strip()
            en_h = ht.get("en", "").strip()
            ja_h = ht.get("ja", "").strip()

            if vi_h and en_h and vi_h == en_h:
                copy_paste_headings.append((sp, sec, "EN equals VI", vi_h, en_h))
            if vi_h and ja_h and vi_h == ja_h:
                copy_paste_headings.append((sp, sec, "JA equals VI", vi_h, ja_h))

        assert copy_paste_headings == [], f"Found {len(copy_paste_headings)} copy-pasted heading translations:\n" + "\n".join(str(c) for c in copy_paste_headings[:10])


    def test_multiple_real_curated_packs_dynamic_citation_selection(self):
        """Verify dynamic citation selection on additional real multi-ref curated packs."""
        from src.services.business_knowledge_index import get_knowledge_index
        from src.services.business_knowledge_retrieval import (
            format_grounded_context,
            select_relevant_citations,
        )

        chunks = get_knowledge_index()

        # 1. Test on cur_saisan_facility_cost_rules
        fac_chunk = next((c for c in chunks if "cur_saisan_facility_cost_rules" in c.chunk_id and c.language == "vi"), None)
        assert fac_chunk is not None
        assert len(fac_chunk.evidence_citations) >= 2

        # Query A focuses on factory depreciation and land lease
        q_depr = "khấu hao nhà đất và tiền thuê đất công xưởng"
        sel_depr = select_relevant_citations(fac_chunk.evidence_citations, question=q_depr, language="vi")
        ctx_depr = format_grounded_context([fac_chunk], language="vi", question=q_depr)
        assert len(sel_depr) >= 1

        # Query B focuses on utilities electricity and water bills
        q_util = "chi phí tiền điện tiền nước và tiện ích"
        sel_util = select_relevant_citations(fac_chunk.evidence_citations, question=q_util, language="vi")
        ctx_util = format_grounded_context([fac_chunk], language="vi", question=q_util)
        assert len(sel_util) >= 1

        # Check citations are distinct and present in context
        assert "Nguồn tham khảo:" in ctx_depr
        assert "Nguồn tham khảo:" in ctx_util

        # 2. Test on cur_claim_col_e_no_description
        col_e_chunk = next((c for c in chunks if "cur_claim_col_e_no_description" in c.chunk_id and c.language == "vi"), None)
        assert col_e_chunk is not None
        assert len(col_e_chunk.evidence_citations) >= 2

        q_claim12 = "nghiệm thu claim 12 loại bỏ mô tả giải thích tại cột E"
        sel_c12 = select_relevant_citations(col_e_chunk.evidence_citations, question=q_claim12, language="vi")
        assert len(sel_c12) >= 1
        assert "Claim 12" in sel_c12[0]["heading_title"]


class TestIntentClassificationAndFallback:
    """Regression tests for question intent routing (incident / clarify / business) across VI, EN, JA."""

    def test_intent_classification_vietnamese(self):
        from src.services.business_knowledge_retrieval import classify_question_intent

        # 1. Business queries
        assert classify_question_intent("cách sử dụng phần mềm này", "vi") == "business"
        assert classify_question_intent("Tại sao chi phí này được phân bổ như vậy?", "vi") == "business"
        assert classify_question_intent("Thiếu dữ liệu nhân sự tháng 3 thì nhập ở đâu?", "vi") == "business"
        assert classify_question_intent("Khóa sổ kế toán là gì?", "vi") == "business"
        assert classify_question_intent("Quy trình kiểm tra tính hợp lệ của dữ liệu nguồn đầu vào?", "vi") == "business"
        assert classify_question_intent("Phân bổ chi phí chung và riêng thế nào?", "vi") == "business"

        # 2. Clarification queries
        assert classify_question_intent("MP có bao nhiêu chi phí?", "vi") == "clarify"
        assert classify_question_intent("Phần mềm có bao nhiêu chi phí?", "vi") == "clarify"
        assert classify_question_intent("Có bao nhiêu nhóm chi phí?", "vi") == "clarify"
        assert classify_question_intent("Tổng chi phí là bao nhiêu?", "vi") == "clarify"

        # 3. Incident queries
        assert classify_question_intent("Chạy tính toán bị dừng khi xuất Excel", "vi") == "incident"
        assert classify_question_intent("Lỗi này là gì?", "vi") == "incident"
        assert classify_question_intent("Lỗi file kết quả bị khóa xử lý thế nào?", "vi") == "incident"
        assert classify_question_intent("Ứng dụng bị dừng khi đang tính toán", "vi") == "incident"
        assert classify_question_intent("Tại sao xuất file thất bại?", "vi") == "incident"
        assert classify_question_intent("Cách khắc phục file bị khóa", "vi") == "incident"

    def test_intent_classification_english(self):
        from src.services.business_knowledge_retrieval import classify_question_intent

        # 1. Business queries
        assert classify_question_intent("How to use this software?", "en") == "business"
        assert classify_question_intent("Why is this cost allocated this way?", "en") == "business"
        assert classify_question_intent("Where do I enter missing March staffing data?", "en") == "business"
        assert classify_question_intent("What is accounting closing procedure?", "en") == "business"
        assert classify_question_intent("How are common and specific costs allocated?", "en") == "business"

        # 2. Clarification queries
        assert classify_question_intent("How many expenses are in MP?", "en") == "clarify"
        assert classify_question_intent("How many cost categories?", "en") == "clarify"
        assert classify_question_intent("What is the total cost?", "en") == "clarify"

        # 3. Incident queries
        assert classify_question_intent("Calculation stopped when exporting to Excel", "en") == "incident"
        assert classify_question_intent("What does this error mean?", "en") == "incident"
        assert classify_question_intent("Why did the calculation fail?", "en") == "incident"
        assert classify_question_intent("Troubleshoot missing staffing baseline", "en") == "incident"
        assert classify_question_intent("How to resolve locked output Excel file issue?", "en") == "incident"

    def test_intent_classification_japanese(self):
        from src.services.business_knowledge_retrieval import classify_question_intent

        # 1. Business queries
        assert classify_question_intent("このソフトウェアの使い方は？", "ja") == "business"
        assert classify_question_intent("なぜこの費用はこのように配賦されるのですか？", "ja") == "business"
        assert classify_question_intent("3月の人員データが不足している場合、どこに入力しますか？", "ja") == "business"
        assert classify_question_intent("共通費と個別費はどう配賦しますか？", "ja") == "business"

        # 2. Clarification queries
        assert classify_question_intent("MPには費用がいくつありますか？", "ja") == "clarify"
        assert classify_question_intent("費用項目はいくつありますか？", "ja") == "clarify"
        assert classify_question_intent("総費用はいくらですか？", "ja") == "clarify"

        # 3. Incident queries
        assert classify_question_intent("Excel出力時に計算が停止した", "ja") == "incident"
        assert classify_question_intent("このエラーは何ですか？", "ja") == "incident"
        assert classify_question_intent("処理が失敗した原因は？", "ja") == "incident"
        assert classify_question_intent("出力先Excelファイルがロックされた場合の対処方法は？", "ja") == "incident"
        assert classify_question_intent("どうすれば対処できますか", "ja") == "incident"

    def test_grounded_local_fallback_by_intent(self):
        from src.services.business_knowledge_retrieval import grounded_local_fallback

        # VI Fallbacks
        fb_clarify_vi = grounded_local_fallback("MP có bao nhiêu chi phí?", "vi", intent="clarify")
        assert "Bạn đang cần hỏi về số lượng nhóm chi phí hay số dòng chi phí" in fb_clarify_vi
        assert "năm tài chính" in fb_clarify_vi

        fb_inc_vi = grounded_local_fallback("su co runtime khong ton tai zz99", "vi", index=[], intent="incident")
        assert "Chưa tìm thấy thông tin sự cố phù hợp" in fb_inc_vi
        assert "Lịch sử lần chạy" in fb_inc_vi
        assert "hệ thống bình thường" not in fb_inc_vi

        fb_biz_vi = grounded_local_fallback("cau hoi nghiep vu khong ton tai zz99", "vi", index=[], intent="business")
        assert "Chưa tìm thấy hướng dẫn nội bộ phù hợp" in fb_biz_vi
        assert "phân bổ chi phí chung và riêng" in fb_biz_vi
        assert "không có lỗi" not in fb_biz_vi

        # EN Fallbacks
        fb_clarify_en = grounded_local_fallback("How many expenses in MP?", "en", intent="clarify")
        assert "Are you asking about the number of cost categories" in fb_clarify_en

        fb_inc_en = grounded_local_fallback("unknown crash issue zz99", "en", index=[], intent="incident")
        assert "No matching incident information was found" in fb_inc_en
        assert "Run History" in fb_inc_en

        fb_biz_en = grounded_local_fallback("unknown business topic zz99", "en", index=[], intent="business")
        assert "No matching internal guidance was found" in fb_biz_en

        # JA Fallbacks
        fb_clarify_ja = grounded_local_fallback("MPには費用がいくつありますか？", "ja", intent="clarify")
        assert "費用の分類項目数ですか、それとも具体的な明細行数ですか？" in fb_clarify_ja

        fb_inc_ja = grounded_local_fallback("mishiranu eror zz99", "ja", index=[], intent="incident")
        assert "該当する障害情報が見つかりませんでした" in fb_inc_ja
        assert "実行履歴" in fb_inc_ja

        fb_biz_ja = grounded_local_fallback("mishiranu gyomu zz99", "ja", index=[], intent="business")
        assert "該当する社内ガイダンスが見つかりませんでした" in fb_biz_ja
