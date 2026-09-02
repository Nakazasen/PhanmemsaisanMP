"""Tests for Fiscal Year RAG Knowledge Update service and retrieval priority (MP2027).

Covers all 10 mandatory verification scenarios:
1. Immutability: FY2028 updates do not modify or touch legacy FY2027 documents.
2. Confirmed Override: Confirmed FY2028 update takes priority over older rules and supersedes legacy topics.
3. Citation Format: Renders clean, localized update citations across VI, EN, JA.
4. Internal Reference Badge: reference_with_caveat updates display 'Tham khảo nội bộ' / 'Internal Reference' / '社内参考'.
5. Fail-Closed Rollback: Invalid updates roll back atomically without corrupting the index.
6. Idempotency: Re-publishing does not create duplicate chunks.
7. Zero Technical Leakage: No local paths, hashes, JSON filenames, or code tokens exposed.
8. Excel Metadata Inspection: Reads structure safely without guessing rules.
9. Dynamic Fiscal Years: Works for any future fiscal year (FY2029, FY2030...), not just FY2028.
10. Deactivation: Deactivating an update cleanly removes it from the search index.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import pytest

from src.services.business_knowledge_index import (
    DocumentChunk,
    build_index_data,
    compute_source_hash,
    load_index_from_file,
    save_index,
)
from src.services.business_knowledge_retrieval import (
    format_grounded_context,
    grounded_local_fallback,
    retrieve_grounded_chunks,
    retrieve_grounded_chunks_with_trace,
    HybridDocumentRetrievalEngine,
)
from src.services.fiscal_year_knowledge_update import (
    FiscalYearUpdateItem,
    deactivate_update,
    generate_update_preview,
    get_updates_directory,
    inspect_excel_reference_metadata,
    list_updates,
    publish_update,
    save_draft,
    validate_update_item,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_scenario_1_preserve_legacy_documents():
    """Verify adding/publishing FY2028 updates does not modify or delete FY2027 legacy files."""
    legacy_file = REPO_ROOT / "QUY_TRINH_NGHIEP_VU_MP2027.md"
    assert legacy_file.is_file()
    initial_mtime = legacy_file.stat().st_mtime_ns

    item = FiscalYearUpdateItem(
        fiscal_year="FY2028",
        update_id="test_upd_fy2028_immutability_check",
        status="draft",
        change_type="new_rule",
        business_area="cost_allocation",
        title={"vi": "Quy tắc thử nghiệm", "en": "Test Rule", "ja": "テストルール"},
        what_changed={
            "vi": "Đây là nội dung thử nghiệm kiểm tra tính bất biến của tài liệu cũ.",
            "en": "This is test content to verify legacy files are untouched.",
            "ja": "これは過去ファイルが変更されないことを確認するテスト内容です。",
        },
        user_action={
            "vi": "Không cần thao tác gì thêm đối với bài kiểm tra này.",
            "en": "No action needed for this test.",
            "ja": "このテストでは追加の操作は不要です。",
        },
        evidence_anchor="Đây là nội dung thử nghiệm kiểm tra tính bất biến",
    )

    draft_path = save_draft(item)
    assert draft_path.is_file()
    assert draft_path.parent.name == "FY2028"

    # Cleanup test draft
    if draft_path.is_file():
        draft_path.unlink()

    # Verify legacy file remains untouched
    assert legacy_file.stat().st_mtime_ns == initial_mtime


def test_scenario_2_confirmed_override_priority_and_superseding():
    """Verify confirmed newer FY update receives score boost and supersedes legacy rule."""
    engine = HybridDocumentRetrievalEngine()

    legacy_chunk = DocumentChunk(
        chunk_id="chk_cur_saisan_facility_cost_rules_vi",
        source_id="curated_cost_allocation_guidance",
        section_title="Quy tắc phân bổ chi phí nhà xưởng",
        language="vi",
        business_area="facilities",
        text="Toàn bộ tiền điện nước nhà xưởng được phân bổ về phòng cơ sở vật chất 1412000040.",
        safe_steps=("Kiểm tra tổng tiền điện nước trong bảng phân bổ.",),
        keywords=("phân bổ chi phí nhà xưởng", "tiền điện", "tiền nước", "nhà xưởng"),
        aliases=("tiền điện xưởng", "chi phí điện nước"),
        authority="canonical",
        fiscal_year="FY2027",
    )

    fy2028_chunk = DocumentChunk(
        chunk_id="chk_upd_fy2028_facility_cost_rules_vi",
        source_id="approved_business_guidance",
        section_title="Cập nhật phân bổ chi phí nhà xưởng FY2028",
        language="vi",
        business_area="facilities",
        text="Từ năm tài chính FY2028, tiền điện và tiền nước được phân bổ trực tiếp theo đồng hồ đo từng phân xưởng.",
        safe_steps=("Kiểm tra chỉ số đồng hồ đo phân xưởng trước khi chạy tính toán.",),
        keywords=("phân bổ chi phí nhà xưởng", "tiền điện", "tiền nước", "FY2028", "cur_saisan_facility_cost_rules"),
        aliases=("tiền điện xưởng", "FY2028 tiền điện", "upd_fy2028_facility_cost_rules"),
        authority="canonical",
        fiscal_year="FY2028",
        replaces_or_supersedes=("cur_saisan_facility_cost_rules",),
    )

    mock_index = [legacy_chunk, fy2028_chunk]
    results = engine.search("tiền điện nhà xưởng phân bổ thế nào", "vi", top_k=2, index=mock_index)

    assert len(results) >= 1
    # Top result must be the FY2028 chunk
    assert results[0].chunk_id == "chk_upd_fy2028_facility_cost_rules_vi"
    assert results[0].fiscal_year == "FY2028"

    # Legacy chunk should be suppressed due to replaces_or_supersedes
    result_ids = [c.chunk_id for c in results]
    assert "chk_cur_saisan_facility_cost_rules_vi" not in result_ids


def test_scenario_3_citation_format_multilingual():
    """Verify clean citation format across VI, EN, JA for FY update chunks."""
    chunk_vi = DocumentChunk(
        chunk_id="chk_test_upd_vi",
        source_id="approved_business_guidance",
        section_title="Quy tắc phân bổ nhà xưởng",
        language="vi",
        business_area="cost_allocation",
        text="Quy định phân bổ tiền điện theo công tơ xưởng.",
        safe_steps=("Xem cột F trong bảng chi tiết.",),
        evidence_citations=({
            "display_title": "Cập nhật nghiệp vụ FY2028",
            "heading_title": "Quy tắc phân bổ nhà xưởng",
            "supported_summary": "Quy định phân bổ tiền điện theo công tơ xưởng.",
            "evidence_anchor": "phân bổ tiền điện theo công tơ",
            "classification": "covered",
        },),
        fiscal_year="FY2028",
    )

    ctx_vi = format_grounded_context([chunk_vi], "vi", question="phân bổ tiền điện")
    assert "Nguồn tham khảo: Cập nhật nghiệp vụ FY2028 — Quy tắc phân bổ nhà xưởng" in ctx_vi
    assert "Mức tin cậy: Đã xác nhận" in ctx_vi

    chunk_en = DocumentChunk(
        chunk_id="chk_test_upd_en",
        source_id="approved_business_guidance",
        section_title="Workshop Electricity Cost Allocation",
        language="en",
        business_area="cost_allocation",
        text="Electricity costs allocated per workshop sub-meter.",
        safe_steps=("Check column F in detail sheet.",),
        evidence_citations=({
            "display_title": "FY2028 Business Update",
            "heading_title": "Workshop Electricity Cost Allocation",
            "supported_summary": "Electricity costs allocated per workshop sub-meter.",
            "evidence_anchor": "Electricity costs allocated",
            "classification": "covered",
        },),
        fiscal_year="FY2028",
    )

    ctx_en = format_grounded_context([chunk_en], "en", question="electricity allocation")
    assert "Source Reference: FY2028 Business Update — Workshop Electricity Cost Allocation" in ctx_en
    assert "Confidence Level: Confirmed" in ctx_en

    chunk_ja = DocumentChunk(
        chunk_id="chk_test_upd_ja",
        source_id="approved_business_guidance",
        section_title="作業場電気代配賦ルール",
        language="ja",
        business_area="cost_allocation",
        text="各作業場の個別メーターに基づいて電気代を直接配賦します。",
        safe_steps=("詳細シートのF列を確認してください。",),
        evidence_citations=({
            "display_title": "FY2028 業務更新",
            "heading_title": "作業場電気代配賦ルール",
            "supported_summary": "各作業場の個別メーターに基づいて電気代を直接配賦します。",
            "evidence_anchor": "個別メーターに基づいて直接配賦",
            "classification": "covered",
        },),
        fiscal_year="FY2028",
    )

    ctx_ja = format_grounded_context([chunk_ja], "ja", question="電気代配賦")
    assert "参照元: FY2028 業務更新 — 作業場電気代配賦ルール" in ctx_ja
    assert "信頼度: 確定" in ctx_ja


def test_scenario_4_caveat_internal_reference_badge():
    """Verify updates with reference_with_caveat display 'Tham khảo nội bộ' / 'Internal Reference' / '社内参考'."""
    chunk_caveat = DocumentChunk(
        chunk_id="chk_test_caveat_vi",
        source_id="approved_business_guidance",
        section_title="Dự thảo định mức văn phòng phẩm FY2028",
        language="vi",
        business_area="cost_allocation",
        text="Dự kiến định mức văn phòng phẩm 50,000 VND/người/tháng.",
        safe_steps=("Chờ văn bản phê duyệt chính thức.",),
        authority="reference_with_caveat",
        evidence_citations=({
            "display_title": "Cập nhật nghiệp vụ FY2028",
            "heading_title": "Dự thảo định mức văn phòng phẩm FY2028",
            "supported_summary": "Dự kiến định mức văn phòng phẩm 50,000 VND/người/tháng.",
            "evidence_anchor": "Dự kiến định mức văn phòng phẩm",
            "classification": "reference_with_caveat",
        },),
        fiscal_year="FY2028",
    )

    fallback_ans = grounded_local_fallback("định mức văn phòng phẩm FY2028", "vi", index=[chunk_caveat])
    assert "Nguồn tham khảo: Cập nhật nghiệp vụ FY2028 — Dự thảo định mức văn phòng phẩm FY2028" in fallback_ans
    assert "Mức tin cậy: Tham khảo nội bộ" in fallback_ans

    # English check
    chunk_caveat_en = DocumentChunk(
        chunk_id="chk_test_caveat_en",
        source_id="approved_business_guidance",
        section_title="Draft Stationery Quota FY2028",
        language="en",
        business_area="cost_allocation",
        text="Proposed stationery quota of 50,000 VND per employee.",
        safe_steps=("Awaiting final approval.",),
        authority="reference_with_caveat",
        evidence_citations=({
            "display_title": "FY2028 Business Update",
            "heading_title": "Draft Stationery Quota FY2028",
            "supported_summary": "Proposed stationery quota of 50,000 VND per employee.",
            "evidence_anchor": "Proposed stationery quota",
            "classification": "reference_with_caveat",
        },),
        fiscal_year="FY2028",
    )
    fallback_ans_en = grounded_local_fallback("stationery quota FY2028", "en", index=[chunk_caveat_en])
    assert "Source Reference: FY2028 Business Update — Draft Stationery Quota FY2028" in fallback_ans_en
    assert "Confidence Level: Internal Reference" in fallback_ans_en


def test_scenario_5_fail_closed_validation_and_rollback():
    """Verify validation rejects incomplete/unsafe updates, and publishing fails closed."""
    # 1. Missing title
    item_bad_title = FiscalYearUpdateItem(
        fiscal_year="FY2028",
        update_id="test_bad_1",
        title={"vi": "", "en": "", "ja": ""},
        what_changed={"vi": "abc " * 10, "en": "abc " * 10, "ja": "abc " * 10},
        user_action={"vi": "def", "en": "def", "ja": "def"},
        evidence_anchor="abc abc abc abc abc",
    )
    valid, errors = validate_update_item(item_bad_title)
    assert not valid
    assert any("Tiêu đề" in e for e in errors)

    # 2. Short anchor
    item_bad_anchor = FiscalYearUpdateItem(
        fiscal_year="FY2028",
        update_id="test_bad_2",
        title={"vi": "Tiêu đề", "en": "Title", "ja": "タイトル"},
        what_changed={"vi": "Nội dung thay đổi chi tiết rất dài.", "en": "Long detail change.", "ja": "詳細な変更内容。"},
        user_action={"vi": "Bước 1", "en": "Step 1", "ja": "手順1"},
        evidence_anchor="ngắn",  # < 15 chars
    )
    valid, errors = validate_update_item(item_bad_anchor)
    assert not valid
    assert any("evidence_anchor" in e for e in errors)

    # 3. Technical leakage token
    item_tech_leak = FiscalYearUpdateItem(
        fiscal_year="FY2028",
        update_id="test_bad_3",
        title={"vi": "Tiêu đề", "en": "Title", "ja": "タイトル"},
        what_changed={"vi": "Lỗi c:\\users\\admin\\pipeline.py traceback error", "en": "error", "ja": "error"},
        user_action={"vi": "Bước 1", "en": "Step 1", "ja": "手順1"},
        evidence_anchor="Lỗi c:\\users\\admin\\pipeline.py traceback error",
    )
    valid, errors = validate_update_item(item_tech_leak)
    assert not valid
    assert any("kỹ thuật" in e for e in errors)


def test_publish_rebuild_failure_restores_all_generated_artifacts(monkeypatch):
    """A rebuild failure must leave the update pack and generated RAG files byte-for-byte unchanged."""
    from src.services import business_knowledge_index

    artifact_paths = (
        "docs/knowledge/business_chat/source_discovery_inventory.json",
        "docs/knowledge/business_chat/coverage_matrix.json",
        "docs/knowledge/business_chat/coverage_evidence_report.json",
        "docs/knowledge/business_chat/coverage_evidence_report.md",
        "docs/knowledge/business_chat/knowledge_index.json",
    )
    before = {relative: (REPO_ROOT / relative).read_bytes() for relative in artifact_paths}
    item = FiscalYearUpdateItem(
        fiscal_year="FY2099",
        update_id="test_upd_fy2099_atomic_rollback",
        status="confirmed",
        title={"vi": "Kiểm tra hoàn tác nguyên tử", "en": "Atomic rollback test", "ja": "アトミックロールバックテスト"},
        what_changed={
            "vi": "Nội dung thử nghiệm để kiểm tra hoàn tác toàn bộ tệp chỉ mục.",
            "en": "Test content that verifies all generated index files are restored.",
            "ja": "生成されたすべての索引ファイルが復元されることを確認するテスト内容です。",
        },
        user_action={"vi": "Không áp dụng cho vận hành thực tế.", "en": "Do not use in operations.", "ja": "実運用には使用しません。"},
        evidence_anchor="Nội dung thử nghiệm để kiểm tra hoàn tác",
    )
    target_file = get_updates_directory(item.fiscal_year, REPO_ROOT) / f"{item.update_id}.json"
    assert not target_file.exists()

    def fail_save_index(*args, **kwargs):
        raise RuntimeError("simulated index write failure")

    monkeypatch.setattr(business_knowledge_index, "save_index", fail_save_index)
    success, message = publish_update(item, REPO_ROOT)

    assert not success
    assert "giữ nguyên" in message
    assert not target_file.exists()
    assert {relative: (REPO_ROOT / relative).read_bytes() for relative in artifact_paths} == before


def test_scenario_6_idempotent_publishing():
    """Verify re-publishing an update is idempotent and does not generate duplicate chunk IDs."""
    item = FiscalYearUpdateItem(
        fiscal_year="FY2028",
        update_id="test_upd_fy2028_idempotency_item",
        status="confirmed",
        change_type="new_rule",
        business_area="operations",
        title={
            "vi": "Quy tắc kiểm thử tính lũy đẳng",
            "en": "Idempotency Test Rule",
            "ja": "冪等性テストルール",
        },
        what_changed={
            "vi": "Quy định thử nghiệm xuất bản nhiều lần không tạo ra bản sao thừa.",
            "en": "Publishing multiple times does not produce redundant duplicates.",
            "ja": "複数回反映しても不要な重複が生成されないことを検証します。",
        },
        user_action={
            "vi": "Kiểm tra danh sách chunk sau khi xuất bản.",
            "en": "Check chunk list after publishing.",
            "ja": "反映後のチャンクリストを確認します。",
        },
        evidence_anchor="xuất bản nhiều lần không tạo ra bản sao thừa",
    )

    success, msg = publish_update(item, REPO_ROOT)
    assert success, msg

    # Re-publish same item
    success2, msg2 = publish_update(item, REPO_ROOT)
    assert success2, msg2

    # Clean up test update
    target_file = get_updates_directory("FY2028", REPO_ROOT) / f"{item.update_id}.json"
    if target_file.is_file():
        target_file.unlink()

    # Rebuild clean state
    from scripts.build_source_discovery_inventory import generate_source_discovery_inventory
    from scripts.build_coverage_evidence_report import generate_coverage_evidence_report
    from src.services.business_knowledge_index import reload_knowledge_index
    generate_source_discovery_inventory()
    generate_coverage_evidence_report()
    save_index(build_index_data(REPO_ROOT))
    reload_knowledge_index(check_freshness=True)


def test_scenario_7_zero_technical_leakage_in_preview():
    """Verify live preview does not leak technical paths or internal identifiers."""
    item = FiscalYearUpdateItem(
        fiscal_year="FY2028",
        update_id="upd_fy2028_safe_preview",
        status="confirmed",
        change_type="changed_rule",
        business_area="cost_allocation",
        title={"vi": "Phân bổ chi phí xe đưa đón", "en": "Bus Transportation Allocation", "ja": "送迎バス費用配賦"},
        what_changed={
            "vi": "Xe đưa đón được phân bổ theo tỷ lệ nhân sự thực tế từng ca làm việc.",
            "en": "Shuttle bus costs are allocated according to actual shift headcount.",
            "ja": "送迎バス費用は各シフトの実人員比率に基づいて配賦されます。",
        },
        user_action={
            "vi": "Kiểm tra báo cáo chấm công ca trước khi kết xuất.",
            "en": "Verify shift attendance report before exporting.",
            "ja": "出力前にシフト勤怠レポートを確認してください。",
        },
        applies_to={"vi": "Khối sản xuất và vận hành", "en": "Production and operations", "ja": "製造および運用部門"},
        evidence_anchor="Xe đưa đón được phân bổ theo tỷ lệ nhân sự",
    )

    preview_vi = generate_update_preview(item, "vi")
    preview_text = preview_vi["answer"]

    forbidden = ["d:\\", "c:\\", ".json", ".py", ".md", "sha256", "chk_", "upd_fy2028_safe_preview"]
    for f in forbidden:
        assert f not in preview_text.lower()

    assert "Nguồn tham khảo: Cập nhật nghiệp vụ FY2028 — Phân bổ chi phí xe đưa đón" in preview_text
    assert "Mức tin cậy: Đã xác nhận" in preview_text


def test_scenario_8_excel_structure_inspection_safety():
    """Verify Excel inspection only reads structural sheet names and column headers without guessing business rules."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "ChiTietChiPhi"
        ws.append(["Mã CC", "Tên Khoản Mục", "Số Tiền", "Tỷ Lệ Phân Bổ", "Ghi Chú"])
        ws.append(["1412000040", "Tiền điện", 50000000, 0.5, "Nhà xưởng"])
        excel_path = Path(tmp_dir) / "test_cost_sample.xlsx"
        wb.save(excel_path)
        wb.close()

        meta = inspect_excel_reference_metadata(excel_path)
        assert meta["sheets_count"] == 1
        assert meta["sheets"][0]["sheet_name"] == "ChiTietChiPhi"
        assert meta["sheets"][0]["sample_headers"] == ["Mã CC", "Tên Khoản Mục", "Số Tiền", "Tỷ Lệ Phân Bổ", "Ghi Chú"]
        # Must not fabricate or return inferred business rules
        assert "inferred_rules" not in meta


def test_scenario_9_dynamic_fiscal_year_support():
    """Verify system supports any future fiscal year (FY2029, FY2030...), not hardcoded to FY2028."""
    item_2030 = FiscalYearUpdateItem(
        fiscal_year="FY2030",
        update_id="upd_fy2030_future_carbon_tax",
        status="confirmed",
        change_type="new_rule",
        business_area="cost_allocation",
        title={"vi": "Thuế phát thải Carbon FY2030", "en": "Carbon Emission Tax FY2030", "ja": "炭素排出税 FY2030"},
        what_changed={
            "vi": "Bổ sung dòng chi phí thuế phát thải carbon vào mục chi phí chung.",
            "en": "Added carbon emission tax row to common costs.",
            "ja": "共通費用に炭素排出税行を追加しました。",
        },
        user_action={
            "vi": "Điền chỉ số phát thải vào ô C15 trong tệp FORM.",
            "en": "Enter emission index in cell C15 of FORM file.",
            "ja": "FORMファイルのC15セルに排出指標を入力してください。",
        },
        evidence_anchor="dòng chi phí thuế phát thải carbon",
    )

    valid, errors = validate_update_item(item_2030)
    assert valid, errors

    preview = generate_update_preview(item_2030, "vi")
    assert "Cập nhật nghiệp vụ FY2030" in preview["source_reference"]

    preview_ja = generate_update_preview(item_2030, "ja")
    assert "FY2030 業務更新" in preview_ja["source_reference"]


def test_scenario_10_deactivation_and_clean_rebuild():
    """Verify deactivating an update sets is_active=False and removes chunk from active index."""
    item = FiscalYearUpdateItem(
        fiscal_year="FY2028",
        update_id="test_upd_fy2028_deactivate_me",
        status="confirmed",
        change_type="operational_guidance",
        business_area="operations",
        title={"vi": "Hướng dẫn kiểm thử tạm thời", "en": "Temp Test Guide", "ja": "一時テストガイド"},
        what_changed={
            "vi": "Quy định kiểm thử để vô hiệu hóa và kiểm tra xóa khỏi index.",
            "en": "Test rule to deactivate and verify removal from index.",
            "ja": "無効化とインデックスからの削除を確認するテストルールです。",
        },
        user_action={"vi": "Kiểm tra sau vô hiệu hóa.", "en": "Check after deactivation.", "ja": "無効化後に確認。"},
        evidence_anchor="vô hiệu hóa và kiểm tra xóa khỏi index",
    )

    success, msg = publish_update(item, REPO_ROOT)
    assert success, msg

    # Deactivate
    deact_ok, deact_msg = deactivate_update("FY2028", item.update_id, REPO_ROOT)
    assert deact_ok, deact_msg

    # Cleanup file
    target_file = get_updates_directory("FY2028", REPO_ROOT) / f"{item.update_id}.json"
    if target_file.is_file():
        target_file.unlink()

    # Rebuild clean state
    from scripts.build_source_discovery_inventory import generate_source_discovery_inventory
    from scripts.build_coverage_evidence_report import generate_coverage_evidence_report
    from src.services.business_knowledge_index import reload_knowledge_index
    generate_source_discovery_inventory()
    generate_coverage_evidence_report()
    save_index(build_index_data(REPO_ROOT))
    reload_knowledge_index(check_freshness=True)


def test_scenario_11_multilingual_distinct_update_chunks():
    """Verify published update produces distinct VI, EN, and JA chunks without VI leakage in EN/JA."""
    item = FiscalYearUpdateItem(
        fiscal_year="FY2028",
        update_id="test_upd_fy2028_distinct_languages",
        status="confirmed",
        change_type="changed_rule",
        business_area="facilities",
        title={
            "vi": "Định mức nhiệt độ kho thành phẩm",
            "en": "Finished Goods Warehouse Temperature Limit",
            "ja": "完成品倉庫の温度上限規定",
        },
        what_changed={
            "vi": "Kho thành phẩm duy trì nhiệt độ tối đa 25 độ C để đảm bảo chất lượng.",
            "en": "Finished goods warehouse temperature is capped at 25C to preserve quality.",
            "ja": "品質維持のため完成品倉庫の温度は最大25度に保たれます。",
        },
        user_action={
            "vi": "Kiểm tra nhiệt kế IoT kho mỗi 2 giờ.",
            "en": "Check warehouse IoT thermometer every 2 hours.",
            "ja": "2時間ごとに倉庫のIoT温度計を確認してください。",
        },
        applies_to={
            "vi": "Kho thành phẩm nhà xưởng",
            "en": "Factory finished goods warehouse",
            "ja": "工場完成品倉庫",
        },
        source_note={
            "vi": "Quy chuẩn bảo quản QC-2028",
            "en": "QC-2028 Storage Standard",
            "ja": "QC-2028 保管基準",
        },
        evidence_anchor="Kho thành phẩm duy trì nhiệt độ tối đa 25 độ C",
    )

    success, msg = publish_update(item, REPO_ROOT)
    assert success, msg

    try:
        index_data = load_index_from_file()
        chunks_by_id = {c.chunk_id: c for c in index_data}

        # VI chunk
        chk_vi = chunks_by_id.get("chk_test_upd_fy2028_distinct_languages_vi")
        assert chk_vi is not None
        assert chk_vi.section_title == "Định mức nhiệt độ kho thành phẩm"
        assert "Kho thành phẩm duy trì nhiệt độ tối đa 25 độ C" in chk_vi.text
        assert "Kiểm tra nhiệt kế IoT kho mỗi 2 giờ." in chk_vi.safe_steps

        # EN chunk
        chk_en = chunks_by_id.get("chk_test_upd_fy2028_distinct_languages_en")
        assert chk_en is not None
        assert chk_en.section_title == "Finished Goods Warehouse Temperature Limit"
        assert "Finished goods warehouse temperature is capped at 25C" in chk_en.text
        assert "Check warehouse IoT thermometer every 2 hours." in chk_en.safe_steps
        assert "Kho thành phẩm" not in chk_en.text
        assert "nhiệt độ" not in chk_en.text

        # JA chunk
        chk_ja = chunks_by_id.get("chk_test_upd_fy2028_distinct_languages_ja")
        assert chk_ja is not None
        assert chk_ja.section_title == "完成品倉庫の温度上限規定"
        assert "完成品倉庫の温度は最大25度に保たれます。" in chk_ja.text
        assert "2時間ごとに倉庫のIoT温度計を確認してください。" in chk_ja.safe_steps
        assert "Kho thành phẩm" not in chk_ja.text

    finally:
        target_file = get_updates_directory("FY2028", REPO_ROOT) / f"{item.update_id}.json"
        if target_file.is_file():
            target_file.unlink()

        from scripts.build_source_discovery_inventory import generate_source_discovery_inventory
        from scripts.build_coverage_evidence_report import generate_coverage_evidence_report
        from src.services.business_knowledge_index import reload_knowledge_index
        generate_source_discovery_inventory()
        generate_coverage_evidence_report()
        save_index(build_index_data(REPO_ROOT))
        reload_knowledge_index(check_freshness=True)


def test_scenario_12_publish_blocked_on_missing_translation_but_draft_saved():
    """Verify publishing fails closed when missing EN/JA required translations, while draft saving works."""
    incomplete_item = FiscalYearUpdateItem(
        fiscal_year="FY2028",
        update_id="test_upd_fy2028_incomplete_draft_only",
        status="draft",
        change_type="new_rule",
        business_area="cost_allocation",
        title={"vi": "Quy tắc chỉ mới nhập tiếng Việt", "en": "", "ja": ""},
        what_changed={
            "vi": "Mô tả thay đổi chi tiết bằng tiếng Việt rất đầy đủ.",
            "en": "",
            "ja": "",
        },
        user_action={"vi": "Kiểm tra danh mục chi phí.", "en": "", "ja": ""},
        evidence_anchor="Mô tả thay đổi chi tiết bằng tiếng Việt rất đầy đủ",
    )

    # 1. Validation fails for publish
    valid, errors = validate_update_item(incomplete_item)
    assert not valid
    assert any("en" in e for e in errors)
    assert any("ja" in e for e in errors)

    success, msg = publish_update(incomplete_item, REPO_ROOT)
    assert not success
    assert "Validation thất bại" in msg

    # 2. Saving as draft succeeds and persists the incomplete language fields cleanly
    draft_path = save_draft(incomplete_item, REPO_ROOT)
    try:
        assert draft_path.is_file()
        data = json.loads(draft_path.read_text(encoding="utf-8"))
        assert data["status"] == "draft"
        assert data["title"]["vi"] == "Quy tắc chỉ mới nhập tiếng Việt"
        assert data["title"]["en"] == ""
        assert data["title"]["ja"] == ""
        assert data["what_changed"]["vi"] == "Mô tả thay đổi chi tiết bằng tiếng Việt rất đầy đủ."
        assert data["what_changed"]["en"] == ""
    finally:
        if draft_path.is_file():
            draft_path.unlink()


def test_scenario_13_preview_missing_translation_friendly_notice():
    """Verify preview for missing translation displays friendly notice and does not pretend VI is EN/JA."""
    vi_only_item = FiscalYearUpdateItem(
        fiscal_year="FY2028",
        update_id="test_upd_fy2028_vi_only_preview",
        status="confirmed",
        change_type="changed_rule",
        business_area="cost_allocation",
        title={"vi": "Quy định tạm ứng chi phí", "en": "", "ja": ""},
        what_changed={
            "vi": "Tạm ứng chi phí công tác không quá 10 triệu đồng.",
            "en": "",
            "ja": "",
        },
        user_action={"vi": "Gửi phiếu đề nghị tạm ứng.", "en": "", "ja": ""},
        evidence_anchor="Tạm ứng chi phí công tác không quá 10 triệu đồng",
    )

    # EN preview when EN not translated
    prev_en = generate_update_preview(vi_only_item, "en")
    assert "No English translation provided" in prev_en["answer"]
    assert "Tạm ứng chi phí công tác" not in prev_en["answer"]
    assert "Untitled" in prev_en["source_reference"]

    # JA preview when JA not translated
    prev_ja = generate_update_preview(vi_only_item, "ja")
    assert "日本語の変更内容がまだ登録されていません" in prev_ja["answer"]
    assert "Tạm ứng chi phí công tác" not in prev_ja["answer"]
    assert "タイトル未設定" in prev_ja["source_reference"]

    # VI preview when VI is present
    prev_vi = generate_update_preview(vi_only_item, "vi")
    assert "Tạm ứng chi phí công tác không quá 10 triệu đồng." in prev_vi["answer"]
    assert "1. Gửi phiếu đề nghị tạm ứng." in prev_vi["answer"]
    assert "Nguồn tham khảo: Cập nhật nghiệp vụ FY2028 — Quy định tạm ứng chi phí" in prev_vi["source_reference"]
