"""Fix and synchronize section-level provenance across all MP2027 business knowledge files."""

import hashlib
import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent

# 1. Topic provenance mappings for all 22 curated topics
TOPIC_PROVENANCE = {
    # AI Assistant Pack (3 topics)
    "cur_ai_assistant_diagnostics": {
        "source_path": "docs/operations/ai_operations_assistant.md",
        "source_section": "## 1. Tổng quan & Mục đích (Overview)",
        "source_sha256": "5863da12423d5826c154f6435a0a339434e5f2aed255b168041f8672ac9de7a1",
        "source_classification": "approved_business_source",
        "review_status": "approved",
    },
    "cur_ai_assistant_copy_response": {
        "source_path": "docs/operations/ai_operations_assistant.md",
        "source_section": "## 2. Quy trình thao tác của người dùng (User Workflow)",
        "source_sha256": "5863da12423d5826c154f6435a0a339434e5f2aed255b168041f8672ac9de7a1",
        "source_classification": "approved_business_source",
        "review_status": "approved",
    },
    "cur_ai_assistant_image_paste": {
        "source_path": "docs/operations/ai_operations_assistant.md",
        "source_section": "## 2. Quy trình thao tác của người dùng (User Workflow)",
        "source_sha256": "5863da12423d5826c154f6435a0a339434e5f2aed255b168041f8672ac9de7a1",
        "source_classification": "approved_business_source",
        "review_status": "approved",
    },

    # Cost Allocation Pack (5 topics)
    "cur_saisan_purpose_and_workflow": {
        "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
        "source_section": "## 1. Purpose and current truth",
        "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
        "source_classification": "approved_business_source",
        "review_status": "approved",
    },
    "cur_saisan_cost_center_hierarchy": {
        "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
        "source_section": "## 6. Account code and Cost Center rules",
        "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
        "source_classification": "approved_business_source",
        "review_status": "approved",
    },
    "cur_saisan_account_lookup_chain": {
        "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
        "source_section": "### Account Lookup Rule",
        "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
        "source_classification": "approved_business_source",
        "review_status": "approved",
    },
    "cur_saisan_manual_input_channels": {
        "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
        "source_section": "## 4. Runtime directory model",
        "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
        "source_classification": "approved_business_source",
        "review_status": "approved",
    },
    "cur_saisan_facility_cost_rules": {
        "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
        "source_section": "### 4.1 Facility / 施設課",
        "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
        "source_classification": "approved_business_source",
        "review_status": "approved",
    },

    # Staffing and Headcount Pack (5 topics)
    "cur_admin_consumables_12month": {
        "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
        "source_section": "### 4.2 Admin / GA consumables",
        "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
        "source_classification": "approved_business_source",
        "review_status": "approved",
    },
    "cur_bus_transportation_cost": {
        "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
        "source_section": "## 6. Bus passenger drivers",
        "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
        "source_classification": "approved_business_source",
        "review_status": "approved",
    },
    "cur_new_employee_costs": {
        "source_path": "docs/requirements/cai_tien_nhap_du_lieu_chung.md",
        "source_section": "### 12.7. Nhóm chi phí cho người mới",
        "source_sha256": "44126b748ed747abdd22b69409544d561476c715640078762a82b1135b7a8737",
        "source_classification": "approved_business_source",
        "review_status": "approved",
    },
    "cur_staffing_override_settings": {
        "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
        "source_section": "## 10. Manual input rules",
        "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
        "source_classification": "approved_business_source",
        "review_status": "approved",
    },
    "cur_source_file_order_rule": {
        "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
        "source_section": "## 3. File-order output rule",
        "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
        "source_classification": "approved_business_source",
        "review_status": "approved",
    },

    # Calculation and Output Pack (6 topics)
    "cur_system_cost_combined": {
        "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
        "source_section": "### 4.3 System Cost",
        "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
        "source_classification": "approved_business_source",
        "review_status": "approved",
    },
    "cur_fixed_asset_depreciation": {
        "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
        "source_section": "### 4.4 Fixed Assets / 固定資産",
        "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
        "source_classification": "approved_business_source",
        "review_status": "approved",
    },
    "cur_birthday_cost": {
        "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
        "source_section": "### 4.5 Birthday / Sinh nhật",
        "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
        "source_classification": "approved_business_source",
        "review_status": "approved",
    },
    "cur_nnn_paperwork_cost": {
        "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
        "source_section": "### 4.6 NNN paperwork",
        "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
        "source_classification": "approved_business_source",
        "review_status": "approved",
    },
    "cur_allocation_travel_shared": {
        "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
        "source_section": "### 4.7 Allocation / 配賦",
        "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
        "source_classification": "approved_business_source",
        "review_status": "approved",
    },
    "cur_fiscal_year_calendar": {
        "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
        "source_section": "## Vận hành nhiều năm tài chính",
        "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
        "source_classification": "approved_business_source",
        "review_status": "approved",
    },

    # Common Operational Errors Pack (3 topics)
    "cur_output_format_preservation": {
        "source_path": "docs/requirements/cai_tien_nhap_du_lieu_chung.md",
        "source_section": "### 4.3. Giữ màu và định dạng FORM gốc",
        "source_sha256": "44126b748ed747abdd22b69409544d561476c715640078762a82b1135b7a8737",
        "source_classification": "approved_business_source",
        "review_status": "approved",
    },
    "cur_provenance_labels_operators": {
        "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
        "source_section": "## 8. Row mapping labels",
        "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
        "source_classification": "approved_business_source",
        "review_status": "approved",
    },
    "cur_run_history_statuses": {
        "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
        "source_section": "## 7. Six-claim acceptance status",
        "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
        "source_classification": "approved_business_source",
        "review_status": "approved",
    },
}

# 2. Knowledge catalog provenance mappings (13 entries)
CATALOG_PROVENANCE = {
    "bck_locked_file": {
        "source_path": "src/services/operations_knowledge.py",
        "source_section": "ENTRY_BLOCKED_OUTPUT_FILE_LOCK",
        "source_sha256": "0d4dfcb2332fdb8b58f6829930804edd7fad3b8c5916e854c2ac36aa20ca6a18",
        "source_classification": "canonical_error_model",
        "review_status": "approved",
    },
    "bck_missing_baseline": {
        "source_path": "src/services/operations_knowledge.py",
        "source_section": "ENTRY_MISSING_STAFFING_BASELINE",
        "source_sha256": "0d4dfcb2332fdb8b58f6829930804edd7fad3b8c5916e854c2ac36aa20ca6a18",
        "source_classification": "canonical_error_model",
        "review_status": "approved",
    },
    "bck_source_validation": {
        "source_path": "src/services/operations_knowledge.py",
        "source_section": "ENTRY_PREFLIGHT_SOURCE_VALIDATION_FAILURE",
        "source_sha256": "0d4dfcb2332fdb8b58f6829930804edd7fad3b8c5916e854c2ac36aa20ca6a18",
        "source_classification": "canonical_error_model",
        "review_status": "approved",
    },
    "bck_fiscal_year_mismatch": {
        "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
        "source_section": "## Vận hành nhiều năm tài chính",
        "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
        "source_classification": "approved_business_guidance",
        "review_status": "approved",
    },
    "bck_cost_center_selection": {
        "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
        "source_section": "## 1. Mục tiêu chương trình",
        "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
        "source_classification": "approved_business_guidance",
        "review_status": "approved",
    },
    "bck_data_entry_manual": {
        "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
        "source_section": "## 4. Runtime directory model",
        "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
        "source_classification": "approved_business_guidance",
        "review_status": "approved",
    },
    "bck_rerun_calculation": {
        "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
        "source_section": "## Vận hành nhiều năm tài chính",
        "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
        "source_classification": "approved_business_guidance",
        "review_status": "approved",
    },
    "bck_excel_format_error": {
        "source_path": "docs/requirements/cai_tien_nhap_du_lieu_chung.md",
        "source_section": "### 4.3. Giữ màu và định dạng FORM gốc",
        "source_sha256": "44126b748ed747abdd22b69409544d561476c715640078762a82b1135b7a8737",
        "source_classification": "approved_business_guidance",
        "review_status": "approved",
    },
    "bck_headcount_input": {
        "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
        "source_section": "## 4. Runtime directory model",
        "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
        "source_classification": "approved_business_guidance",
        "review_status": "approved",
    },
    "bck_workflow_overview": {
        "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
        "source_section": "## 1. Mục tiêu chương trình",
        "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
        "source_classification": "approved_business_guidance",
        "review_status": "approved",
    },
    "bck_account_lookup_rules": {
        "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
        "source_section": "### Account Lookup Rule",
        "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
        "source_classification": "approved_business_guidance",
        "review_status": "approved",
    },
    "bck_special_cost_manual": {
        "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
        "source_section": "## 4. Runtime directory model",
        "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
        "source_classification": "approved_business_guidance",
        "review_status": "approved",
    },
    "bck_update_rollback_procedure": {
        "source_path": "docs/handover/release_update_playbook.md",
        "source_section": "## Rollback",
        "source_sha256": "23c11941f65f462d18044462f9e96a9df25292a73c8c78a61dce5ac6d6ab3f45",
        "source_classification": "technical_excluded",
        "review_status": "approved",
    },
}


def apply_and_verify():
    # 1. Update Curated Packs
    curated_dir = repo_root / "docs/knowledge/business_chat/curated"
    for pack_file in sorted(curated_dir.glob("*.json")):
        data = json.loads(pack_file.read_text(encoding="utf-8"))
        for entry in data.get("entries", []):
            tid = entry["topic_id"]
            if tid in TOPIC_PROVENANCE:
                entry["provenance"] = TOPIC_PROVENANCE[tid]
        pack_file.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Updated {pack_file.name}")

    # 2. Update Knowledge Catalog
    cat_path = repo_root / "docs/knowledge/business_chat/knowledge_catalog.json"
    cat_data = json.loads(cat_path.read_text(encoding="utf-8"))
    for entry in cat_data.get("entries", []):
        eid = entry.get("id")
        if eid in CATALOG_PROVENANCE:
            entry["provenance"] = CATALOG_PROVENANCE[eid]
    cat_path.write_text(json.dumps(cat_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Updated {cat_path.name}")

    # 3. Update Coverage Matrix
    cov_path = repo_root / "docs/knowledge/business_chat/coverage_matrix.json"
    cov_data = json.loads(cov_path.read_text(encoding="utf-8"))
    for item in cov_data.get("items", []):
        if item.get("status") == "covered":
            eid = item.get("entry_id")
            if eid and eid in TOPIC_PROVENANCE:
                item["provenance"] = TOPIC_PROVENANCE[eid]
            elif eid and eid in CATALOG_PROVENANCE:
                item["provenance"] = CATALOG_PROVENANCE[eid]
            elif item.get("error_code") == "blocked_output_file_lock":
                item["provenance"] = CATALOG_PROVENANCE["bck_locked_file"]
            elif item.get("error_code") == "missing_staffing_baseline":
                item["provenance"] = CATALOG_PROVENANCE["bck_missing_baseline"]
            elif item.get("error_code") == "preflight_source_validation_failure":
                item["provenance"] = CATALOG_PROVENANCE["bck_source_validation"]
    cov_path.write_text(json.dumps(cov_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Updated {cov_path.name}")

    # 4. Master Source Discovery Inventory
    inventory_items = [
        # QUY_TRINH_NGHIEP_VU_MP2027.md
        {
            "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
            "source_section": "## Vận hành nhiều năm tài chính",
            "classification": "covered",
            "reason": "Canonical multi-year fiscal calendar, directory layout, and run history rules covered in curated guidance.",
            "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
            "curated_topic": "cur_fiscal_year_calendar",
        },
        {
            "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
            "source_section": "## 1. Mục tiêu chương trình",
            "classification": "covered",
            "reason": "Desktop application workflow, cost center selection, and non-destructive calculation principles.",
            "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
            "curated_topic": "bck_cost_center_selection",
        },
        {
            "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
            "source_section": "## 2. Nguồn yêu cầu và bằng chứng",
            "classification": "covered",
            "reason": "Canonical requirement workbook priority and preflight source validation rules.",
            "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
            "curated_topic": "bck_source_validation",
        },
        {
            "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
            "source_section": "## 3. Trạng thái module hiện tại",
            "classification": "needs_owner_review",
            "reason": "Module readiness claims and historical transition pending business owner sign-off on new-hire delta and health check split.",
            "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
            "curated_topic": None,
        },
        {
            "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
            "source_section": "## 4. Runtime directory model",
            "classification": "covered",
            "reason": "Active file paths, manual event drivers, and headcount file conventions covered in curated packs.",
            "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
            "curated_topic": "cur_saisan_manual_input_channels",
        },
        {
            "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
            "source_section": "## 5. Active và legacy headcount",
            "classification": "covered",
            "reason": "Active headcount ingestion and legacy headcount transition rules.",
            "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
            "curated_topic": "bck_headcount_input",
        },
        {
            "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
            "source_section": "## 6. Bus passenger drivers",
            "classification": "covered",
            "reason": "Bus transportation passenger calculation and headcount driver rules.",
            "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
            "curated_topic": "cur_bus_transportation_cost",
        },
        {
            "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
            "source_section": "## 7. Six-claim acceptance status",
            "classification": "covered",
            "reason": "Six-claim business rules, run history status interpretations, and immutable run archives.",
            "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
            "curated_topic": "cur_run_history_statuses",
        },
        {
            "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
            "source_section": "## 8. Row mapping labels",
            "classification": "covered",
            "reason": "Provenance and row mapping conventions for operator calculation output.",
            "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
            "curated_topic": "cur_provenance_labels_operators",
        },
        {
            "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
            "source_section": "## 10. Manual input rules",
            "classification": "covered",
            "reason": "Manual headcount and special expense override input conventions.",
            "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
            "curated_topic": "cur_staffing_override_settings",
        },
        {
            "source_path": "QUY_TRINH_NGHIEP_VU_MP2027.md",
            "source_section": "## 14. Commit trail gần nhất",
            "classification": "technical_excluded",
            "reason": "Developer commit history and technical maintainer notes excluded from business chat.",
            "source_sha256": "354fcf616c302ba6726f992526ca9e5fe0284e1d8f5e4ddcff3805392c013ebc",
            "curated_topic": None,
        },

        # docs/requirements/cai_tien_nhap_du_lieu_chung.md
        {
            "source_path": "docs/requirements/cai_tien_nhap_du_lieu_chung.md",
            "source_section": "## 1. Mục tiêu tổng thể của yêu cầu",
            "classification": "covered",
            "reason": "Core requirements specification for MP Saisan automated cost allocation.",
            "source_sha256": "44126b748ed747abdd22b69409544d561476c715640078762a82b1135b7a8737",
            "curated_topic": "cur_saisan_purpose_and_workflow",
        },
        {
            "source_path": "docs/requirements/cai_tien_nhap_du_lieu_chung.md",
            "source_section": "### 4.3. Giữ màu và định dạng FORM gốc",
            "classification": "covered",
            "reason": "Preservation of colors, border styles, and formatting in the target workbook.",
            "source_sha256": "44126b748ed747abdd22b69409544d561476c715640078762a82b1135b7a8737",
            "curated_topic": "cur_output_format_preservation",
        },
        {
            "source_path": "docs/requirements/cai_tien_nhap_du_lieu_chung.md",
            "source_section": "### 4.4. Để lại tất cả công thức tính",
            "classification": "covered",
            "reason": "Preservation of calculation formulas and non-destructive excel output.",
            "source_sha256": "44126b748ed747abdd22b69409544d561476c715640078762a82b1135b7a8737",
            "curated_topic": "cur_output_format_preservation",
        },
        {
            "source_path": "docs/requirements/cai_tien_nhap_du_lieu_chung.md",
            "source_section": "## 7. Sheet `Chi phí hệ thống`",
            "classification": "covered",
            "reason": "IT system cost consolidation from 3 simulation workbooks.",
            "source_sha256": "44126b748ed747abdd22b69409544d561476c715640078762a82b1135b7a8737",
            "curated_topic": "cur_system_cost_combined",
        },
        {
            "source_path": "docs/requirements/cai_tien_nhap_du_lieu_chung.md",
            "source_section": "## 8. Sheet `Chi phí khấu hao, lãi nhà đất`",
            "classification": "covered",
            "reason": "Facility rent and interest cost calculation rules.",
            "source_sha256": "44126b748ed747abdd22b69409544d561476c715640078762a82b1135b7a8737",
            "curated_topic": "cur_saisan_facility_cost_rules",
        },
        {
            "source_path": "docs/requirements/cai_tien_nhap_du_lieu_chung.md",
            "source_section": "## 9. Sheet `Chi phí tài sản cố định`",
            "classification": "covered",
            "reason": "Fixed asset depreciation and interest calculation per cost center.",
            "source_sha256": "44126b748ed747abdd22b69409544d561476c715640078762a82b1135b7a8737",
            "curated_topic": "cur_fixed_asset_depreciation",
        },
        {
            "source_path": "docs/requirements/cai_tien_nhap_du_lieu_chung.md",
            "source_section": "## 10. Sheet `Chi phí làm giấy tờ cho NNN`",
            "classification": "covered",
            "reason": "Expat paperwork and visa fee allocation rules.",
            "source_sha256": "44126b748ed747abdd22b69409544d561476c715640078762a82b1135b7a8737",
            "curated_topic": "cur_nnn_paperwork_cost",
        },
        {
            "source_path": "docs/requirements/cai_tien_nhap_du_lieu_chung.md",
            "source_section": "## 11. Sheet `Chi phí sinh nhật`",
            "classification": "covered",
            "reason": "Birthday cost allocation rules (headcount × unit price).",
            "source_sha256": "44126b748ed747abdd22b69409544d561476c715640078762a82b1135b7a8737",
            "curated_topic": "cur_birthday_cost",
        },
        {
            "source_path": "docs/requirements/cai_tien_nhap_du_lieu_chung.md",
            "source_section": "## 12. Sheet `Chi phí phân bổ từ hành chính`",
            "classification": "covered",
            "reason": "12-month admin consumable allocation and event expense rules.",
            "source_sha256": "44126b748ed747abdd22b69409544d561476c715640078762a82b1135b7a8737",
            "curated_topic": "cur_admin_consumables_12month",
        },
        {
            "source_path": "docs/requirements/cai_tien_nhap_du_lieu_chung.md",
            "source_section": "### 12.7. Nhóm chi phí cho người mới",
            "classification": "covered",
            "reason": "New employee equipment, uniform, and onboarding cost allocation.",
            "source_sha256": "44126b748ed747abdd22b69409544d561476c715640078762a82b1135b7a8737",
            "curated_topic": "cur_new_employee_costs",
        },
        {
            "source_path": "docs/requirements/cai_tien_nhap_du_lieu_chung.md",
            "source_section": "## 13. Sheet `勘定科目` — account master",
            "classification": "covered",
            "reason": "Account code lookup rules and mapping validation.",
            "source_sha256": "44126b748ed747abdd22b69409544d561476c715640078762a82b1135b7a8737",
            "curated_topic": "cur_saisan_account_lookup_chain",
        },
        {
            "source_path": "docs/requirements/cai_tien_nhap_du_lieu_chung.md",
            "source_section": "## 14. Sheet `原価センタ` — Cost Center master",
            "classification": "covered",
            "reason": "Cost center hierarchy and department mapping rules.",
            "source_sha256": "44126b748ed747abdd22b69409544d561476c715640078762a82b1135b7a8737",
            "curated_topic": "cur_saisan_cost_center_hierarchy",
        },
        {
            "source_path": "docs/requirements/cai_tien_nhap_du_lieu_chung.md",
            "source_section": "## 16. GAP cần agent kiểm tra trong repo hiện tại",
            "classification": "needs_owner_review",
            "reason": "Row-level edge-case verification checklist requires business-owner sign-off.",
            "source_sha256": "44126b748ed747abdd22b69409544d561476c715640078762a82b1135b7a8737",
            "curated_topic": None,
        },

        # docs/knowledge/mp_saisan_business_knowledge_base_v2.md
        {
            "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
            "source_section": "## 1. Purpose and current truth",
            "classification": "covered",
            "reason": "High-level business purpose and calculation principles.",
            "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
            "curated_topic": "cur_saisan_purpose_and_workflow",
        },
        {
            "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
            "source_section": "### Account Lookup Rule",
            "classification": "covered",
            "reason": "Canonical account lookup chain and fallback order.",
            "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
            "curated_topic": "cur_saisan_account_lookup_chain",
        },
        {
            "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
            "source_section": "## 3. File-order output rule",
            "classification": "covered",
            "reason": "File-order ingestion rule and row spacing rules.",
            "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
            "curated_topic": "cur_source_file_order_rule",
        },
        {
            "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
            "source_section": "### 4.1 Facility / 施設課",
            "classification": "covered",
            "reason": "Facility rent and interest cost allocation.",
            "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
            "curated_topic": "cur_saisan_facility_cost_rules",
        },
        {
            "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
            "source_section": "### 4.2 Admin / GA consumables",
            "classification": "covered",
            "reason": "Admin consumable items and previous-month headcount rules.",
            "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
            "curated_topic": "cur_admin_consumables_12month",
        },
        {
            "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
            "source_section": "### 4.3 System Cost",
            "classification": "covered",
            "reason": "IT system cost calculation and 3 workbook simulation rules.",
            "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
            "curated_topic": "cur_system_cost_combined",
        },
        {
            "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
            "source_section": "### 4.4 Fixed Assets / 固定資産",
            "classification": "covered",
            "reason": "Fixed asset depreciation formula and monthly rate.",
            "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
            "curated_topic": "cur_fixed_asset_depreciation",
        },
        {
            "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
            "source_section": "### 4.5 Birthday / Sinh nhật",
            "classification": "covered",
            "reason": "Birthday cost allocation calculation.",
            "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
            "curated_topic": "cur_birthday_cost",
        },
        {
            "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
            "source_section": "### 4.6 NNN paperwork",
            "classification": "covered",
            "reason": "Expat paperwork fee calculation.",
            "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
            "curated_topic": "cur_nnn_paperwork_cost",
        },
        {
            "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
            "source_section": "### 4.7 Allocation / 配賦",
            "classification": "covered",
            "reason": "Shared travel expense allocation rules.",
            "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
            "curated_topic": "cur_allocation_travel_shared",
        },
        {
            "source_path": "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
            "source_section": "## 6. Account code and Cost Center rules",
            "classification": "covered",
            "reason": "Cost center hierarchy and department codes.",
            "source_sha256": "2ee52552f186a02609c4e7534e68ef68442970ddb5b2b81dcb912d282e2d15f1",
            "curated_topic": "cur_saisan_cost_center_hierarchy",
        },

        # docs/operations/ai_operations_assistant.md
        {
            "source_path": "docs/operations/ai_operations_assistant.md",
            "source_section": "## 1. Tổng quan & Mục đích (Overview)",
            "classification": "covered",
            "reason": "End-user overview and diagnostic capability of local AI assistant.",
            "source_sha256": "5863da12423d5826c154f6435a0a339434e5f2aed255b168041f8672ac9de7a1",
            "curated_topic": "cur_ai_assistant_diagnostics",
        },
        {
            "source_path": "docs/operations/ai_operations_assistant.md",
            "source_section": "## 2. Quy trình thao tác của người dùng (User Workflow)",
            "classification": "covered",
            "reason": "User guide for copying AI guidance and pasting screenshots.",
            "source_sha256": "5863da12423d5826c154f6435a0a339434e5f2aed255b168041f8672ac9de7a1",
            "curated_topic": "cur_ai_assistant_copy_response",
        },
        {
            "source_path": "docs/operations/ai_operations_assistant.md",
            "source_section": "## 11. Tư vấn AI nội bộ C-AGENT (Phase 6)",
            "classification": "technical_excluded",
            "reason": "Internal networking, API providers, C-AGENT proxy and bearer token specifications.",
            "source_sha256": "5863da12423d5826c154f6435a0a339434e5f2aed255b168041f8672ac9de7a1",
            "curated_topic": None,
        },

        # src/services/operations_knowledge.py
        {
            "source_path": "src/services/operations_knowledge.py",
            "source_section": "ENTRY_BLOCKED_OUTPUT_FILE_LOCK",
            "classification": "covered",
            "reason": "Canonical domain error model for blocked output file locks.",
            "source_sha256": "0d4dfcb2332fdb8b58f6829930804edd7fad3b8c5916e854c2ac36aa20ca6a18",
            "curated_topic": "bck_locked_file",
        },
        {
            "source_path": "src/services/operations_knowledge.py",
            "source_section": "ENTRY_MISSING_STAFFING_BASELINE",
            "classification": "covered",
            "reason": "Canonical domain error model for missing March staffing baseline.",
            "source_sha256": "0d4dfcb2332fdb8b58f6829930804edd7fad3b8c5916e854c2ac36aa20ca6a18",
            "curated_topic": "bck_missing_baseline",
        },
        {
            "source_path": "src/services/operations_knowledge.py",
            "source_section": "ENTRY_PREFLIGHT_SOURCE_VALIDATION_FAILURE",
            "classification": "covered",
            "reason": "Canonical domain error model for preflight source workbook validation failures.",
            "source_sha256": "0d4dfcb2332fdb8b58f6829930804edd7fad3b8c5916e854c2ac36aa20ca6a18",
            "curated_topic": "bck_source_validation",
        },

        # Historical and Technical documents
        {
            "source_path": "docs/knowledge/mp_saisan_business_knowledge_base.md",
            "source_section": "# Current Source Authority Notice",
            "classification": "historical_excluded",
            "reason": "Superseded by v2 specification on 2026-07-11; retained for historical audit trace only.",
            "source_sha256": "2fc1435ffcc808ceab4bfee72d4789633a90a30a377a58fe28d7930ec0ae398f",
            "curated_topic": None,
        },
        {
            "source_path": "docs/MP2027/README_HEADCOUNT_LEGACY.md",
            "source_section": "# Manual Headcount Legacy File",
            "classification": "historical_excluded",
            "reason": "Legacy manual input instructions superseded by unified dialog.",
            "source_sha256": "82ef9b3c61f30c6fb61a99f5fb725e37469ad95348acec79d647dc1839a085b9",
            "curated_topic": None,
        },
        {
            "source_path": "docs/architecture/feature_registry.md",
            "source_section": "# Danh mục tính năng MP2027",
            "classification": "technical_excluded",
            "reason": "Internal feature status tracking and code module registry.",
            "source_sha256": "33dce33ab2e44f3e6638a28ce41366108fbbda73f6bdde957685e10e6ff000ea",
            "curated_topic": None,
        },
        {
            "source_path": "docs/architecture/system_architecture.md",
            "source_section": "# MP2027 Manager — Bản đồ kiến trúc kỹ thuật",
            "classification": "technical_excluded",
            "reason": "Technical architectural overview and internal subsystem designs.",
            "source_sha256": "c39547f11af377f9783fca619404e61e3487ce204f99fda772d0017bd40ea70d",
            "curated_topic": None,
        },
        {
            "source_path": "docs/database/data_dictionary.md",
            "source_section": "# Từ điển dữ liệu SQLite MP2027",
            "classification": "technical_excluded",
            "reason": "Internal SQLite database schema and column definitions.",
            "source_sha256": "bdf9923a63b04a8a1cd0f3bdd153375285e51c016f30ef6031a60b2bf79e7ff7",
            "curated_topic": None,
        },
        {
            "source_path": "docs/development_setup.md",
            "source_section": "# Development setup MP2027",
            "classification": "technical_excluded",
            "reason": "Developer environment setup and Python tooling instructions.",
            "source_sha256": "0dcacd3291f14cb39bcdd7792a8314cf2d382335942717ec1269b2f188901cf6",
            "curated_topic": None,
        },
        {
            "source_path": "docs/handover/HANDOVER_FOR_NEXT_AGENT.md",
            "source_section": "# Bàn giao hiện hành — MP2027 Manager",
            "classification": "technical_excluded",
            "reason": "Technical developer handover instructions.",
            "source_sha256": "12a671b68f017962ef27bdcbcb6ba541c54804a5a77ebaf1097633bdcc4853cf",
            "curated_topic": None,
        },
        {
            "source_path": "docs/handover/release_update_playbook.md",
            "source_section": "# Phát hành và cập nhật MP2027 Manager",
            "classification": "technical_excluded",
            "reason": "Technical release packaging and LAN update handbook.",
            "source_sha256": "23c11941f65f462d18044462f9e96a9df25292a73c8c78a61dce5ac6d6ab3f45",
            "curated_topic": None,
        },
        {
            "source_path": "docs/handover/test_strategy_and_profiles.md",
            "source_section": "# Chiến lược test và các profile phát hành MP2027",
            "classification": "technical_excluded",
            "reason": "Automated test suite profiles and developer test strategy.",
            "source_sha256": "90e511315f5cd079b18dd549dbbef3a8d40189c1da6e5185c1dc93e5505e3e31",
            "curated_topic": None,
        },
        {
            "source_path": "docs/handover/code_walkthrough.md",
            "source_section": "# MP2027 Manager — hướng dẫn đọc code",
            "classification": "technical_excluded",
            "reason": "Code walkthrough and technical module structure documentation.",
            "source_sha256": "77ebf570dba960a1c6f032e2d93750092f6fa9bc18d60f9d553cd6e889936a0e",
            "curated_topic": None,
        },
        {
            "source_path": "README.md",
            "source_section": "# MP2027 Manager",
            "classification": "technical_excluded",
            "reason": "Project repository README for developers.",
            "source_sha256": "ed0db11de7e6bbe9f9d3435285b9bfd66ebacd577986d625a863fa81ef0f6eeb",
            "curated_topic": None,
        },
        {
            "source_path": "AGENTS.md",
            "source_section": "# MP2027 instructions for AI agents",
            "classification": "technical_excluded",
            "reason": "AI agent instructions and update protocols.",
            "source_sha256": "a150445e19e416be0bcd21e25db4eb492c2e34830924a7753b4ca0edbda959ce",
            "curated_topic": None,
        },
        {
            "source_path": "docs/operations/ai_operations_assistant_scope.md",
            "source_section": "# Phạm vi tính năng: Trợ lý Vận hành & Xử lý Lỗi (AI Operations Assistant - MVP Read-only)",
            "classification": "technical_excluded",
            "reason": "Developer scope definition and boundary documentation for the AI Assistant component.",
            "source_sha256": "fd73341eb0739a2447c081b308db35c5536303e49b3923b37651b1350ca211df",
            "curated_topic": None,
        },
    ]

    # Verification loop
    for it in inventory_items:
        p = repo_root / it["source_path"]
        assert p.is_file(), f"Missing file {it['source_path']}"
        raw = p.read_bytes()
        curr_sha = hashlib.sha256(raw).hexdigest()
        assert curr_sha == it["source_sha256"], f"SHA mismatch for {it['source_path']}"
        txt = raw.decode("utf-8", errors="ignore")
        assert it["source_section"] in txt, f"Section {repr(it['source_section'])} not in {it['source_path']}"

    inv_path = repo_root / "docs/knowledge/business_chat/source_discovery_inventory.json"
    inv_data = {
        "schema_version": "1.0",
        "description": "Master source discovery inventory and section-level provenance catalog for MP2027 business chat knowledge.",
        "items": inventory_items,
    }
    inv_path.write_text(json.dumps(inv_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Verified & wrote {len(inventory_items)} items to {inv_path.name}")


if __name__ == "__main__":
    apply_and_verify()
