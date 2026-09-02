"""Script to build and validate the complete repository-wide source discovery inventory and coverage matrix.

Discovers and classifies every single heading from all business, operational, requirement,
and engineering documentation files across the entire MP2027 project:
- Core business processes & rules
- User requirements & claims
- Operational assistant guides & error models
- Wiki concepts & timelines
- Superpowers feature specifications
- Architecture, database, development, handover, and test playbooks (technical/historical exclusions)

Classifies each heading into one of:
- covered: canonical confirmed business rules mapped to curated RAG topics
- reference_with_caveat: internal reference knowledge requiring operator verification
- technical_excluded: dev setup, code walkthrough, schemas, scripts, tests, release keys
- historical_excluded: obsolete versions, legacy files, superseded specs

Outputs:
- docs/knowledge/business_chat/source_discovery_inventory.json
- docs/knowledge/business_chat/coverage_matrix.json
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]

# All documentation files across the project
ALL_TARGET_DOCS: List[str] = [
    "QUY_TRINH_NGHIEP_VU_MP2027.md",
    "README.md",
    "AGENTS.md",
    "docs/requirements/cai_tien_nhap_du_lieu_chung.md",
    "docs/operations/ai_operations_assistant.md",
    "docs/operations/ai_operations_assistant_scope.md",
    "docs/knowledge/mp_saisan_business_knowledge_base_v2.md",
    "docs/knowledge/mp_saisan_business_knowledge_base.md",
    "docs/MP2027/README_HEADCOUNT_LEGACY.md",
    "wiki/concepts/cai-tien-nhap-lieu-chi-phi-chung.md",
    "wiki/timelines/nhap-lieu-nhan-su-master-plan.md",
    "wiki/index.md",
    "docs/superpowers/specs/2026-08-31-g6-to-g5-transition-new-hire.md",
    "docs/superpowers/specs/2026-08-31-uniform-cup-improvement-807-814.md",
    "docs/superpowers/specs/2026-09-01-manual-special-cost-inheritance.md",
    "docs/superpowers/specs/2026-09-01-output-cost-row-ordering-design.md",
    "docs/superpowers/plans/2026-08-31-facility-summary-rows-cc-1412000086.md",
    "docs/superpowers/plans/2026-08-31-g6-to-g5-transition-new-hire.md",
    "docs/superpowers/plans/2026-08-31-sales-account-resolution-release.md",
    "docs/superpowers/plans/2026-08-31-uniform-cup-improvement-807-814.md",
    "docs/superpowers/plans/2026-09-01-manual-special-cost-inheritance.md",
    "docs/superpowers/plans/2026-09-01-output-cost-row-ordering.md",
    "docs/architecture/feature_registry.md",
    "docs/architecture/system_architecture.md",
    "docs/database/data_dictionary.md",
    "docs/development_setup.md",
    "docs/handover/HANDOVER_FOR_NEXT_AGENT.md",
    "docs/handover/code_walkthrough.md",
    "docs/handover/release_update_playbook.md",
    "docs/handover/test_strategy_and_profiles.md",
    "docs/handover/releases/0.1.1.md",
    "docs/handover/releases/0.1.2.md",
    "docs/handover/releases/0.1.3.md",
    "docs/handover/releases/0.1.4.md",
    "docs/handover/releases/0.1.5.md",
    "docs/handover/releases/0.1.6.md",
    "installer/languages/README.md",
    "reference_outputs/README.md",
]

OTHER_DOCS_INVENTORY: List[Dict[str, Any]] = [
    {
        "source_path": "src/services/operations_knowledge.py",
        "source_section": "ENTRY_BLOCKED_OUTPUT_FILE_LOCK",
        "classification": "covered",
        "curated_topic": "bck_locked_file",
        "reason": "Mô hình lỗi chuẩn hóa khi tệp đầu ra đang bị khóa."
    },
    {
        "source_path": "src/services/operations_knowledge.py",
        "source_section": "ENTRY_MISSING_STAFFING_BASELINE",
        "classification": "covered",
        "curated_topic": "bck_missing_baseline",
        "reason": "Mô hình lỗi chuẩn hóa khi thiếu nhân sự mốc ban đầu."
    },
    {
        "source_path": "src/services/operations_knowledge.py",
        "source_section": "ENTRY_PREFLIGHT_SOURCE_VALIDATION_FAILURE",
        "classification": "covered",
        "curated_topic": "bck_source_validation",
        "reason": "Mô hình lỗi chuẩn hóa khi xác thực nguồn đầu vào thất bại."
    },
]

# Default policies for purely technical/historical documents
DEFAULT_DOC_POLICIES: Dict[str, Tuple[str, Optional[str], str]] = {
    "docs/knowledge/mp_saisan_business_knowledge_base.md": ("historical_excluded", None, "Tài liệu V1 lịch sử đã được thay thế bởi V2."),
    "docs/database/data_dictionary.md": ("technical_excluded", None, "Từ điển dữ liệu và lược đồ cơ sở dữ liệu nội bộ."),
    "docs/development_setup.md": ("technical_excluded", None, "Hướng dẫn thiết lập môi trường phát triển và kiểm thử."),
    "docs/architecture/feature_registry.md": ("technical_excluded", None, "Danh mục tính năng kỹ thuật dành cho nhà phát triển."),
    "docs/architecture/system_architecture.md": ("technical_excluded", None, "Bản đồ kiến trúc hệ thống kỹ thuật."),
    "docs/handover/HANDOVER_FOR_NEXT_AGENT.md": ("technical_excluded", None, "Tài liệu bàn giao kỹ thuật giữa các kỹ sư."),
    "docs/handover/code_walkthrough.md": ("technical_excluded", None, "Hướng dẫn cấu trúc mã nguồn cho lập trình viên."),
    "docs/handover/release_update_playbook.md": ("technical_excluded", None, "Sổ tay quy trình đóng gói và phát hành phần mềm."),
    "docs/handover/test_strategy_and_profiles.md": ("technical_excluded", None, "Chiến lược và hồ sơ kiểm thử tự động."),
    "docs/handover/releases/0.1.1.md": ("technical_excluded", None, "Ghi chú phát hành phiên bản 0.1.1."),
    "docs/handover/releases/0.1.2.md": ("technical_excluded", None, "Ghi chú phát hành phiên bản 0.1.2."),
    "docs/handover/releases/0.1.3.md": ("technical_excluded", None, "Ghi chú phát hành phiên bản 0.1.3."),
    "docs/handover/releases/0.1.4.md": ("technical_excluded", None, "Ghi chú phát hành phiên bản 0.1.4."),
    "docs/handover/releases/0.1.5.md": ("technical_excluded", None, "Ghi chú phát hành phiên bản 0.1.5."),
    "docs/handover/releases/0.1.6.md": ("technical_excluded", None, "Ghi chú phát hành phiên bản 0.1.6."),
    "docs/superpowers/plans/2026-08-31-facility-summary-rows-cc-1412000086.md": ("technical_excluded", None, "Kế hoạch thực thi kỹ thuật Facility summary rows."),
    "docs/superpowers/plans/2026-08-31-g6-to-g5-transition-new-hire.md": ("technical_excluded", None, "Kế hoạch thực thi kỹ thuật G6-to-G5 transition."),
    "docs/superpowers/plans/2026-08-31-sales-account-resolution-release.md": ("technical_excluded", None, "Kế hoạch thực thi kỹ thuật Sales account resolution."),
    "docs/superpowers/plans/2026-08-31-uniform-cup-improvement-807-814.md": ("technical_excluded", None, "Kế hoạch thực thi kỹ thuật Uniform and cup improvement."),
    "docs/superpowers/plans/2026-09-01-manual-special-cost-inheritance.md": ("technical_excluded", None, "Kế hoạch thực thi kỹ thuật Manual special cost inheritance."),
    "docs/superpowers/plans/2026-09-01-output-cost-row-ordering.md": ("technical_excluded", None, "Kế hoạch thực thi kỹ thuật Output cost row ordering."),
    "wiki/index.md": ("technical_excluded", None, "Chỉ mục điều hướng hệ thống tri thức wiki nội bộ."),
    "installer/languages/README.md": ("technical_excluded", None, "Tệp bản dịch ngôn ngữ cho trình cài đặt Inno Setup."),
    "reference_outputs/README.md": ("technical_excluded", None, "Quy định đối chiếu thư mục tệp mẫu kết quả tham chiếu."),
}

# Specific heading classification rules for business, requirements, operations, and wiki documents
HEADING_RULES: Dict[str, Dict[str, Tuple[str, Optional[str], str]]] = {
    "QUY_TRINH_NGHIEP_VU_MP2027.md": {
        "# MP2027 Manager - Quy trình nghiệp vụ, vận hành và handover kỹ thuật": ("technical_excluded", None, "Tài liệu kỹ thuật tổng hợp kiêm handover"),
        "## Vận hành nhiều năm tài chính": ("covered", "cur_fiscal_year_calendar", "Quy tắc chu kỳ 12 tháng từ tháng 4 đến tháng 3"),
        "## Reconcile note - workbook canonical updated": ("historical_excluded", None, "Ghi chú đối soát lịch sử cập nhật file Excel gốc"),
        "## 1. Mục tiêu chương trình": ("covered", "cur_saisan_purpose_and_workflow", "Mục đích tự động hóa tính toán phân bổ chi phí MP Saisan"),
        "## 2. Nguồn yêu cầu và bằng chứng": ("covered", "bck_source_validation", "Quy tắc kiểm tra tính hợp lệ dữ liệu nguồn"),
        "## 3. Trạng thái module hiện tại": ("reference_with_caveat", "cur_module_implementation_status", "Theo dõi trạng thái hoàn thiện các module phân bổ chi phí (tham khảo nội bộ)"),
        "## 4. Runtime directory model": ("covered", "cur_saisan_manual_input_channels", "Mô hình thư mục và các kênh nhập liệu thủ công"),
        "## 5. Active và legacy headcount": ("covered", "bck_headcount_input", "Quy tắc nhập số lượng nhân sự active và loại bỏ legacy"),
        "## 6. Bus passenger drivers": ("covered", "cur_bus_transportation_cost", "Chi phí xe bus đưa đón người biệt phái và nhân viên Việt"),
        "## 7. Six-claim acceptance status": ("covered", "cur_claim_medical_check_dedup", "Nghiệm thu 6 phản hồi lỗi người dùng"),
        "## 8. Row mapping labels": ("covered", "cur_provenance_labels_operators", "Nhãn định danh dòng chi phí và đối chiếu nguồn gốc"),
        "## 9. Source workbook workflow": ("covered", "cur_source_file_order_rule", "Quy trình đọc và xử lý tệp nguồn theo thứ tự"),
        "### Audit tài sản cố định và lịch sử giải thích": ("reference_with_caveat", "cur_fixed_assets_audit_history", "Lịch sử kiểm toán và đối soát khấu hao tài sản cố định (tham khảo nội bộ)"),
        "## 10. Manual input rules": ("covered", "cur_saisan_manual_input_channels", "Quy tắc các kênh nhập liệu thủ công"),
        "### Headcount": ("covered", "bck_headcount_input", "Quy tắc nhập số lượng nhân sự thủ công"),
        "### Event drivers": ("reference_with_caveat", "cur_event_driver_standards", "Định mức phân bổ các sự kiện hành chính theo tháng (tham khảo nội bộ)"),
        "### Special costs": ("covered", "cur_manual_special_cost_inheritance", "Quy tắc nhập và kế thừa chi phí riêng theo Cost Center"),
        "## 11. Database": ("technical_excluded", None, "Lược đồ cơ sở dữ liệu SQLite"),
        "## 12. Công thức output": ("covered", "cur_output_format_preservation", "Quy tắc bảo toàn công thức trên file kết quả"),
        "## 13. Dashboard và audit": ("covered", "cur_dashboard_audit_status", "Bảng điều khiển và quy trình kiểm toán dữ liệu"),
        "## 14. Commit trail gần nhất": ("technical_excluded", None, "Lịch sử commit kỹ thuật"),
        "## 15. Checks nên chạy": ("technical_excluded", None, "Lệnh kiểm tra mã nguồn cho lập trình viên"),
        "## 16. Quy tắc an toàn khi tiếp tục": ("technical_excluded", None, "Quy tắc an toàn mã nguồn"),
        "## 17. Việc ưu tiên tiếp theo": ("reference_with_caveat", "cur_roadmap_operational_priorities", "Lộ trình và danh mục ưu tiên hoàn thiện nghiệp vụ vận hành (tham khảo nội bộ)"),
        "## 18. Tóm tắt cho agent tiếp theo": ("technical_excluded", None, "Tóm tắt bàn giao kỹ thuật cho agent"),
        "## 19. Đồng phục và cốc xếp": ("covered", "cur_uniform_and_folding_cups", "Quy tắc định mức cấp phát đồng phục và cốc gấp"),
        "## 20. Kế thừa và bảo tồn chi phí riêng theo năm tài chính": ("covered", "cur_manual_special_cost_inheritance", "Bảo toàn chi phí riêng theo từng Cost Center qua các năm tài chính"),
        "## 21. Tùy biến sắp xếp thứ tự dòng chi phí kéo-thả": ("covered", "cur_output_cost_row_reordering", "Chức năng sắp xếp thứ tự hiển thị dòng chi phí"),
        "## 22. Tìm kiếm nhanh phòng ban trên màn hình chính": ("covered", "cur_quick_search_departments", "Tìm kiếm nhanh mã Cost Center và phòng ban"),
        "## 23. So sánh biến động ngân sách cùng kỳ (YoY) và biểu đồ trực quan": ("covered", "cur_budget_variance_yoy_analysis", "Báo cáo phân tích so sánh ngân sách qua các năm"),
    },
    "README.md": {
        "# MP2027 Manager": ("covered", "cur_saisan_purpose_and_workflow", "Tổng quan ứng dụng MP2027"),
        "## Ai dùng chương trình này": ("covered", "cur_saisan_purpose_and_workflow", "Đối tượng người dùng MP2027"),
        "## Luồng sử dụng chính": ("covered", "cur_saisan_purpose_and_workflow", "Luồng sử dụng chính MP2027"),
        "## Input chính": ("covered", "cur_saisan_purpose_and_workflow", "Các tệp dữ liệu đầu vào chính"),
        "## Output chính": ("covered", "cur_saisan_purpose_and_workflow", "Các tệp dữ liệu kết quả đầu ra chính"),
        "## Tính năng nâng cao nổi bật": ("covered", "cur_saisan_purpose_and_workflow", "Tính năng nâng cao nổi bật"),
        "## Nguyên tắc nghiệp vụ an toàn": ("covered", "cur_saisan_purpose_and_workflow", "Nguyên tắc nghiệp vụ an toàn"),
        "## Cài môi trường Windows sau khi clone": ("technical_excluded", None, "Hướng dẫn cài đặt môi trường kỹ thuật"),
        "## Cách chạy": ("technical_excluded", None, "Lệnh chạy ứng dụng kỹ thuật"),
        "### Bản đóng gói Windows cho người dùng": ("technical_excluded", None, "Hướng dẫn chạy bản đóng gói"),
        "### GUI/launcher chính": ("technical_excluded", None, "Lệnh chạy GUI"),
        "### CLI engine": ("technical_excluded", None, "Lệnh chạy CLI"),
        "### Pipeline E2E cho developer": ("technical_excluded", None, "Lệnh chạy pipeline E2E"),
        "### CLI test runner": ("technical_excluded", None, "Lệnh chạy test runner"),
        "### Kiểm chứng output sau refactor": ("technical_excluded", None, "Lệnh kiểm chứng kết quả"),
        "## Cách test": ("technical_excluded", None, "Lệnh kiểm thử kỹ thuật"),
        "## Cấu trúc thư mục quan trọng": ("technical_excluded", None, "Cấu trúc thư mục mã nguồn"),
        "## Không được commit": ("technical_excluded", None, "Quy định bảo vệ dữ liệu nội bộ"),
        "## Dọn artifact local an toàn": ("technical_excluded", None, "Lệnh dọn dẹp thư mục tạm"),
        "## Tài liệu bàn giao cần đọc trước": ("technical_excluded", None, "Danh mục tài liệu kỹ thuật bàn giao"),
        "## Troubleshooting": ("technical_excluded", None, "Xử lý sự cố kỹ thuật môi trường"),
    },
    "AGENTS.md": {
        "# MP2027 instructions for AI agents": ("technical_excluded", None, "Chỉ dẫn lập trình cho AI agent"),
        "## Release and update work": ("technical_excluded", None, "Chỉ dẫn phát hành và cập nhật cho AI agent"),
    },
    "docs/operations/ai_operations_assistant_scope.md": {
        "# Phạm vi tính năng: Trợ lý Vận hành & Xử lý Lỗi (AI Operations Assistant - MVP Read-only)": ("covered", "cur_ai_assistant_diagnostics", "Phạm vi tính năng trợ lý vận hành AI"),
        "## 1. Tôn chỉ cốt lõi & Ranh giới an toàn (Safety Boundary)": ("covered", "cur_ai_assistant_explicit_boundaries", "Ranh giới an toàn cho trợ lý AI"),
        "## 2. Các chức năng trong phạm vi (In-Scope for MVP)": ("covered", "cur_ai_assistant_diagnostics", "Chức năng chẩn đoán trong phạm vi"),
        "## 3. Các hạng mục ngoài phạm vi & Hoãn lại (Explicitly Out-of-Scope & Deferred)": ("technical_excluded", None, "Hạng mục kỹ thuật ngoài phạm vi"),
        "## 4. Tiêu chí nghiệm thu & Kiểm chứng (Verification & Acceptance Criteria)": ("technical_excluded", None, "Tiêu chí nghiệm thu kỹ thuật"),
    },
    "docs/MP2027/README_HEADCOUNT_LEGACY.md": {
        "# Manual Headcount Legacy File": ("covered", "cur_legacy_staffing_exclusion", "Hướng dẫn loại trừ tệp nhân sự cũ legacy"),
    },
    "wiki/concepts/cai-tien-nhap-lieu-chi-phi-chung.md": {
        "## Summary": ("covered", "cur_saisan_purpose_and_workflow", "Tổng quan cải tiến nhập liệu chi phí chung"),
        "## Details": ("covered", "cur_saisan_purpose_and_workflow", "Chi tiết các nhóm chi phí chung"),
        "### 1. Chi phí hệ thống (System Cost)": ("covered", "cur_system_cost_combined", "Khái niệm chi phí hệ thống"),
        "### 2. Chi phí khấu hao và lãi nhà đất (Depreciation & Land Interest)": ("covered", "cur_saisan_facility_cost_rules", "Khái niệm chi phí khấu hao lãi nhà đất"),
        "### 3. Chi phí tài sản cố định (Fixed Assets)": ("covered", "cur_fixed_asset_depreciation", "Khái niệm chi phí tài sản cố định"),
        "### 4. Chi phí làm giấy tờ cho người nước ngoài (Foreigners Paperwork Costs)": ("covered", "cur_nnn_paperwork_cost", "Khái niệm chi phí làm giấy tờ NNN"),
        "### 5. Chi phí sinh nhật (Birthday Costs)": ("covered", "cur_birthday_cost", "Khái niệm chi phí sinh nhật"),
        "### 6. Chi phí phân bổ từ hành chính (Administrative Allocation Costs)": ("covered", "cur_admin_consumables_12month", "Khái niệm chi phí phân bổ hành chính"),
        "## Evidence": ("technical_excluded", None, "Bằng chứng wiki nội bộ"),
        "## Related": ("technical_excluded", None, "Liên kết wiki"),
        "## Change Log": ("technical_excluded", None, "Nhật ký thay đổi wiki"),
    },
    "wiki/timelines/nhap-lieu-nhan-su-master-plan.md": {
        "## Summary": ("covered", "cur_admin_consumables_12month", "Tổng quan lộ trình nhập liệu nhân sự"),
        "## Details": ("covered", "cur_admin_consumables_12month", "Chi tiết các nhóm dữ liệu nhân sự"),
        "### 1. Dữ liệu nhân sự dùng chung cho cả 12 tháng": ("covered", "cur_bus_transportation_cost", "Nhân sự xe bus 12 tháng"),
        "### 2. Dữ liệu nhân sự đặc thù theo từng tháng": ("covered", "cur_admin_monthly_events", "Nhân sự sự kiện đặc thù theo từng tháng"),
        "### 3. Hạng mục cần xóa bỏ": ("covered", "cur_legacy_staffing_exclusion", "Hạng mục nhân sự cũ cần loại bỏ"),
        "## Evidence": ("technical_excluded", None, "Bằng chứng wiki"),
        "## Related": ("technical_excluded", None, "Liên kết wiki"),
        "## Change Log": ("technical_excluded", None, "Nhật ký wiki"),
    },
    "docs/superpowers/specs/2026-08-31-g6-to-g5-transition-new-hire.md": {
        "# G6 to G5 transition handling — specification": ("covered", "cur_new_employee_costs", "Đặc tả chuyển đổi G6 sang G5 cho người mới"),
        "## Source request": ("covered", "cur_new_employee_costs", "Yêu cầu nguồn người mới"),
        "## Root cause": ("technical_excluded", None, "Nguyên nhân kỹ thuật"),
        "## Functional requirements": ("covered", "cur_new_employee_costs", "Yêu cầu chức năng người mới"),
        "## Acceptance examples": ("covered", "cur_new_employee_costs", "Ví dụ nghiệm thu người mới"),
        "## Safety boundaries": ("covered", "cur_new_employee_costs", "Ranh giới an toàn người mới"),
    },
    "docs/superpowers/specs/2026-08-31-uniform-cup-improvement-807-814.md": {
        "# Uniform and Cup Improvement 807-814 Specification": ("covered", "cur_uniform_and_folding_cups", "Đặc tả cấp phát đồng phục và cốc gấp"),
        "## Scope": ("covered", "cur_uniform_and_folding_cups", "Phạm vi cấp phát đồng phục"),
        "## Business rules": ("covered", "cur_uniform_and_folding_cups", "Quy tắc nghiệp vụ đồng phục và cốc"),
        "## Acceptance criteria": ("covered", "cur_uniform_and_folding_cups", "Tiêu chuẩn nghiệm thu đồng phục"),
        "## Out of scope": ("technical_excluded", None, "Ngoài phạm vi kỹ thuật"),
    },
    "docs/superpowers/specs/2026-09-01-manual-special-cost-inheritance.md": {
        "# Kế thừa chi phí riêng theo CC": ("covered", "cur_manual_special_cost_inheritance", "Đặc tả kế thừa chi phí riêng theo Cost Center"),
        "## Mục tiêu": ("covered", "cur_manual_special_cost_inheritance", "Mục tiêu kế thừa chi phí riêng"),
        "## Quy tắc đã chốt": ("covered", "cur_manual_special_cost_inheritance", "Quy tắc kế thừa chi phí riêng đã duyệt"),
        "## Thiết kế": ("technical_excluded", None, "Thiết kế kỹ thuật kế thừa"),
        "## Không thuộc phạm vi": ("technical_excluded", None, "Ngoài phạm vi kế thừa"),
    },
    "docs/superpowers/specs/2026-09-01-output-cost-row-ordering-design.md": {
        "# Sắp xếp dòng chi phí trên file MP — Thiết kế": ("covered", "cur_output_cost_row_reordering", "Đặc tả sắp xếp thứ tự dòng chi phí MP"),
        "## Mục tiêu": ("covered", "cur_output_cost_row_reordering", "Mục tiêu sắp xếp thứ tự dòng"),
        "## Quy tắc nghiệp vụ đã chốt": ("covered", "cur_output_cost_row_reordering", "Quy tắc sắp xếp dòng chi phí đã duyệt"),
        "## Phạm vi giao diện": ("covered", "cur_output_cost_row_reordering", "Giao diện sắp xếp dòng chi phí"),
        "## Nhận dạng và metadata ẩn": ("technical_excluded", None, "Metadata ẩn kỹ thuật"),
        "## Luồng lưu thứ tự": ("covered", "cur_output_cost_row_reordering", "Luồng lưu thứ tự dòng"),
        "## Luồng chạy lại và tạo FY mới": ("covered", "cur_output_cost_row_reordering", "Quy tắc áp dụng khi chạy lại hoặc tạo FY mới"),
        "## Kiểm thử và nghiệm thu": ("technical_excluded", None, "Kiểm thử kỹ thuật sắp xếp"),
    },
    "docs/operations/ai_operations_assistant.md": {
        "# Hướng dẫn Vận hành: Trợ lý Vận hành & Xử lý Lỗi (AI Operations Assistant)": ("technical_excluded", None, "Tài liệu kỹ thuật trợ lý vận hành"),
        "## 1. Tổng quan & Mục đích (Overview)": ("covered", "cur_ai_assistant_diagnostics", "Mục tiêu và ranh giới an toàn của trợ lý AI"),
        "## 2. Quy trình thao tác của người dùng (User Workflow)": ("covered", "cur_ai_assistant_diagnostics", "Quy trình thao tác chẩn đoán sự cố"),
        "## 3. Chính sách đa ngôn ngữ (Language Policy)": ("covered", "cur_ai_assistant_language_policy", "Chính sách hỗ trợ 3 ngôn ngữ bắt buộc"),
        "## 4. Phân định Ngôn ngữ Nghiệp vụ & Chi tiết Kỹ thuật (Separation of Concerns)": ("covered", "cur_ai_assistant_separation_of_concerns", "Phân tách giải thích nghiệp vụ và chi tiết kỹ thuật"),
        "## 5. Ranh giới & Giới hạn Bằng chứng (Evidence Limits)": ("covered", "cur_ai_assistant_evidence_limits", "Giới hạn trích xuất bằng chứng an toàn"),
        "## 6. Mức độ chắc chắn (Confidence Levels)": ("covered", "cur_ai_assistant_confidence_levels", "Quy tắc hiển thị mức tin cậy"),
        "## 7. Ba lớp lỗi đã được phê duyệt (Supported Error Classes)": ("covered", "cur_operations_error_taxonomy", "Danh mục 3 lớp lỗi vận hành chuẩn hóa"),
        "### 1. `missing_staffing_baseline` (Thiếu dữ liệu nhân sự mốc ban đầu)": ("covered", "cur_operations_error_taxonomy", "Chi tiết lỗi thiếu nhân sự mốc ban đầu"),
        "### 2. `blocked_output_file_lock` (Tệp kết quả đầu ra đang bị khóa)": ("covered", "cur_operations_error_taxonomy", "Chi tiết lỗi tệp kết quả đang bị khóa"),
        "### 3. `preflight_source_validation_failure` (Kiểm tra dữ liệu nguồn thất bại)": ("covered", "cur_operations_error_taxonomy", "Chi tiết lỗi kiểm tra dữ liệu nguồn thất bại"),
        "### 3. `preflight_source_validation_failure` (Kiểm tra dữ liệu nguồn trước khi chạy thất bại)": ("covered", "cur_operations_error_taxonomy", "Chi tiết lỗi xác thực nguồn đầu vào"),
        "## 8. Xử lý Lỗi Chưa Xác Định (Unknown Error Fallback)": ("covered", "cur_ai_assistant_unknown_error_handling", "Xử lý sự cố không xác định"),
        "## 8. Luồng xử lý khi Lỗi chưa xác nhận (`unknown`)": ("covered", "cur_ai_assistant_unknown_error_handling", "Luồng xử lý sự cố chưa xác nhận"),
        "## 9. Ranh giới Cấm & Hành vi Không Được Phép (Explicit Boundaries)": ("covered", "cur_ai_assistant_explicit_boundaries", "Ranh giới những việc trợ lý AI không làm"),
        "## 9. Giới hạn & Các điều cấm tuyệt đối (Explicit Non-Capabilities)": ("covered", "cur_ai_assistant_explicit_boundaries", "Giới hạn và các điều cấm của trợ lý AI"),
        "## 10. Nghiệm thu thủ công (T027 — chưa thực hiện)": ("technical_excluded", None, "Kế hoạch nghiệm thu thủ công kỹ thuật"),
        "## 11. Tư vấn AI nội bộ C-AGENT (Phase 6)": ("technical_excluded", None, "Tài liệu kỹ thuật định hướng tích hợp AI C-AGENT"),
        "### Nguyên tắc vận hành": ("covered", "cur_ai_assistant_explicit_boundaries", "Nguyên tắc vận hành an toàn của AI"),
        "## 11. Bảng trạng thái đối soát & Audit Dashboard": ("covered", "cur_dashboard_audit_status", "Theo dõi đối soát audit trên Dashboard"),
        "## 12. Danh mục thuật ngữ (Glossary)": ("covered", "cur_provenance_labels_operators", "Danh mục thuật ngữ vận hành"),
    },
    "docs/knowledge/mp_saisan_business_knowledge_base_v2.md": {
        "# Current Source Authority Notice": ("historical_excluded", None, "Ghi chú phân cấp thẩm quyền tài liệu"),
        "## Historical reconcile note - 09.06 workbook": ("historical_excluded", None, "Ghi chú đối soát lịch sử cập nhật file Excel gốc"),
        "# MP Saisan Business Knowledge Base v2 - Full Business Specification": ("covered", "cur_saisan_purpose_and_workflow", "Tổng quan cơ sở tri thức nghiệp vụ MP Saisan v2"),
        "## 1. Purpose and current truth": ("covered", "cur_saisan_purpose_and_workflow", "Mục đích và hiện trạng ứng dụng"),
        "## 2. Source hierarchy and trust rules": ("covered", "bck_source_validation", "Phân cấp nguồn và quy tắc tin cậy"),
        "### Account Lookup Rule": ("covered", "cur_saisan_account_lookup_chain", "Quy tắc tra cứu mã tài khoản"),
        "## 3. File-order output rule": ("covered", "cur_source_file_order_rule", "Quy tắc xuất file theo đúng thứ tự"),
        "## 4. Module detail matrix": ("covered", "cur_saisan_purpose_and_workflow", "Ma trận chi tiết từng module"),
        "### 4.1 Facility / 施設課": ("covered", "cur_saisan_facility_cost_rules", "Quy tắc module cơ sở vật chất"),
        "### 4.2 Admin / GA consumables": ("covered", "cur_admin_consumables_12month", "Quy tắc module vật tư hành chính tiêu hao"),
        "### 4.3 Admin / GA monthly events": ("covered", "cur_admin_monthly_events", "Quy tắc module sự kiện hành chính theo tháng"),
        "### 4.3 System Cost": ("covered", "cur_system_cost_combined", "Quy tắc module chi phí hệ thống"),
        "### 4.4 System / KDC system": ("covered", "cur_system_cost_combined", "Quy tắc module chi phí hệ thống KDC"),
        "### 4.4 Fixed Assets / 固定資産": ("covered", "cur_fixed_asset_depreciation", "Quy tắc module tài sản cố định"),
        "### 4.5 Fixed assets / 固定資産": ("covered", "cur_fixed_asset_depreciation", "Quy tắc module tài sản cố định"),
        "### 4.5 Birthday / Sinh nhật": ("covered", "cur_birthday_cost", "Quy tắc module sinh nhật"),
        "### 4.6 Birthday / 誕生日": ("covered", "cur_birthday_cost", "Quy tắc module sinh nhật"),
        "### 4.6 NNN paperwork": ("covered", "cur_nnn_paperwork_cost", "Quy tắc module giấy tờ người nước ngoài"),
        "### 4.7 NNN paperwork / 外国人": ("covered", "cur_nnn_paperwork_cost", "Quy tắc module giấy tờ người nước ngoài"),
        "### 4.7 Allocation / 配賦": ("covered", "cur_allocation_travel_shared", "Quy tắc module công tác phí và phân bổ chung"),
        "### 4.8 Travel & shared GA / 配賦額一覧": ("covered", "cur_allocation_travel_shared", "Quy tắc module công tác phí và phân bổ chung"),
        "### 4.8 Manual CSV channels": ("covered", "cur_saisan_manual_input_channels", "Quy tắc các kênh nhập dữ liệu thủ công CSV"),
        "## 5. Target rows / cell ranges known so far": ("reference_with_caveat", "cur_target_output_cell_ranges", "Vùng ô và dòng kết quả FORM (tham khảo nội bộ)"),
        "## 6. Account code and Cost Center rules": ("covered", "cur_saisan_account_lookup_chain", "Quy tắc mã tài khoản và Cost Center"),
        "## 7. Primary and secondary reference pool": ("covered", "cur_saisan_purpose_and_workflow", "Quy định nguồn tham chiếu chính và phụ"),
        "## 8. Gap accounting and what not to say": ("covered", "cur_ai_assistant_explicit_boundaries", "Ranh giới những điều AI không được khẳng định bừa"),
        "## 9. Provenance policy": ("covered", "cur_provenance_labels_operators", "Chính sách dẫn nguồn minh bạch"),
        "## 10. Implementation status dashboard": ("reference_with_caveat", "cur_saisan_implementation_dashboard", "Bảng trạng thái hoàn thiện tổng thể MP Saisan (tham khảo nội bộ)"),
        "## 11. Current continuation route": ("covered", "cur_roadmap_operational_priorities", "Lộ trình phát triển tiếp theo"),
        "## 12. Glossary": ("covered", "cur_provenance_labels_operators", "Danh mục thuật ngữ"),
        "## 13. Source documents used": ("covered", "cur_provenance_labels_operators", "Danh sách tài liệu nguồn đã dùng"),
    },
    "docs/requirements/cai_tien_nhap_du_lieu_chung.md": {
        "# Current Source Authority Notice": ("historical_excluded", None, "Ghi chú phân cấp thẩm quyền tài liệu"),
        "# Cải tiến nhập dữ liệu chung vào file MPnew.xlsx — bản kế hoạch đã kiểm tra, sửa và bổ sung": ("covered", "cur_saisan_purpose_and_workflow", "Mục tiêu tổng quát cải tiến nhập liệu"),
        "## 0.0. Historical reconcile of the 09.06 workbook": ("historical_excluded", None, "Ghi chú đối soát lịch sử cập nhật file Excel 09.06"),
        "### 0.0.1. Inventory workbook hiện tại": ("historical_excluded", None, "Kiểm kê workbook hiện tại 09.06"),
        "### 0.0.2. Nội dung bổ sung/nhấn mạnh cần phản ánh khi code hoặc audit": ("historical_excluded", None, "Nội dung bổ sung lịch sử 09.06"),
        "## 0. Kết luận rà soát bản Gemini cào dữ liệu": ("historical_excluded", None, "Kết luận rà soát kỹ thuật"),
        "### 0.1. Phần Gemini đã làm đúng và được giữ": ("historical_excluded", None, "Phần cào dữ liệu đã giữ"),
        "### 0.2. Những điểm Gemini cào chưa đủ hoặc dễ gây sai khi code": ("historical_excluded", None, "Cảnh báo kỹ thuật khi lập trình"),
        "## 0.3. HISTORICAL_04_06_CONTEXT — lineage từ MPnew 04.06.2026, chỉ giữ nơi không mâu thuẫn với canonical 10.07.2026": ("historical_excluded", None, "Bối cảnh lịch sử phiên bản 04.06"),
        "## 1. Mục tiêu tổng thể của yêu cầu": ("covered", "cur_saisan_purpose_and_workflow", "Mục tiêu tổng thể của yêu cầu"),
        "### 1.1. Mục tiêu không phải chỉ là copy/paste": ("covered", "cur_saisan_purpose_and_workflow", "Mục đích tự động hóa và bảo toàn công thức"),
        "## 2. Danh sách sheet trong file yêu cầu gốc": ("covered", "cur_source_file_order_rule", "Danh sách sheet trong file yêu cầu gốc"),
        "## 3. Thuật ngữ bắt buộc dùng đúng khi viết code": ("covered", "cur_saisan_account_lookup_chain", "Thuật ngữ nghiệp vụ kế toán"),
        "### 3.1. Cost Center / 原価センタ / code phòng chịu chi phí": ("covered", "cur_saisan_cost_center_hierarchy", "Định nghĩa Cost Center và mã phòng"),
        "### 3.2. Account Code / 勘定科目": ("covered", "cur_saisan_account_lookup_chain", "Định nghĩa mã tài khoản"),
        "### 3.3. `採算区分` và `原価区分`": ("covered", "cur_saisan_account_lookup_chain", "Phân loại chi phí và phân bổ"),
        "## 4. Yêu cầu chung trên toàn bộ output FORM": ("covered", "cur_output_format_preservation", "Yêu cầu chung trên biểu mẫu FORM"),
        "### 4.1. Không cần điền 2 dữ liệu nhân sự cũ": ("covered", "cur_legacy_staffing_exclusion", "Bỏ qua 2 dòng nhân sự cũ"),
        "### 4.2. Đẩy dữ liệu về đúng cột theo FORM": ("covered", "cur_form_column_alignment", "Đẩy dữ liệu đúng cột tháng theo FORM"),
        "### 4.3. Giữ màu và định dạng FORM gốc": ("covered", "cur_output_format_preservation", "Giữ màu sắc và định dạng gốc"),
        "### 4.4. Để lại tất cả công thức tính": ("covered", "cur_output_format_preservation", "Bảo toàn tất cả công thức tính"),
        "### 4.5. Audit bắt buộc": ("technical_excluded", None, "Kiểm thử kỹ thuật bắt buộc"),
        "## 5. Sheet `Sheet1` — tổng quan yêu cầu": ("covered", "cur_saisan_purpose_and_workflow", "Tổng quan yêu cầu nhập liệu"),
        "### 5.1. Nội dung Gemini cào đúng": ("historical_excluded", None, "Nội dung lịch sử cào dữ liệu"),
        "### 5.2. Cách làm tổng quát": ("covered", "cur_saisan_purpose_and_workflow", "Cách làm tổng quát phân bổ chi phí"),
        "## 6. Sheet `Hạng mục cần cải tiến` — danh sách cải tiến chung": ("covered", "cur_saisan_purpose_and_workflow", "Danh sách cải tiến chung"),
        "### 6.1. Các mục cải tiến ban đầu": ("covered", "cur_saisan_purpose_and_workflow", "Các hạng mục cải tiến ban đầu"),
        "### 6.2. Ghi chú màu trong file yêu cầu": ("covered", "cur_output_format_preservation", "Quy định màu sắc ô trên biểu mẫu"),
        "### 6.3. Ghi chú ngày 9/4 — ưu tiên mới": ("historical_excluded", None, "Ghi chú lịch sử ngày 9/4"),
        "### 6.4. Input số người mới thay thế logic hiện tại": ("covered", "cur_new_employee_costs", "Nhập số người mới thay thế"),
        "### 6.5. “Xóa nội dung dưới đây cho không cần thiết”": ("historical_excluded", None, "Ghi chú loại bỏ nội dung không cần thiết"),
        "### 6.6. HISTORICAL_04_06_CONTEXT — lineage 04.06 cho thứ tự file và dòng trống giữa các nhóm file": ("historical_excluded", None, "Bối cảnh lịch sử thứ tự file 04.06"),
        "### 6.7. HISTORICAL_04_06_CONTEXT — “6 chi phí / gộp thành 1 dòng chi phí”": ("historical_excluded", None, "Bối cảnh lịch sử gộp chi phí 04.06"),
        "## 7. Sheet `Chi phí hệ thống`": ("covered", "cur_system_cost_combined", "Quy tắc chi phí hệ thống KDC"),
        "### 7.1. Mục tiêu": ("covered", "cur_system_cost_combined", "Mục tiêu chi phí hệ thống"),
        "### 7.2. File nguồn hệ thống": ("covered", "cur_system_cost_combined", "Tệp nguồn hệ thống IT"),
        "### 7.3. Công thức chi tiết": ("covered", "cur_system_cost_combined", "Công thức chi tiết chi phí hệ thống"),
        "### 7.4. Công thức tổng hệ thống": ("covered", "cur_system_cost_combined", "Công thức tổng hợp chi phí hệ thống"),
        "### 7.5. Rule đối chiếu và điều chỉnh": ("covered", "cur_system_cost_combined", "Quy tắc đối chiếu chi phí hệ thống"),
        "### 7.6. Nhập vào FORM": ("covered", "cur_system_cost_combined", "Điền chi phí hệ thống vào biểu mẫu FORM"),
        "### 7.7. Account code đúng cho chi phí hệ thống": ("covered", "cur_system_cost_account_mapping", "Mã tài khoản chuẩn KDC System theo nguyên giá"),
        "### 7.8. Tháng áp dụng": ("covered", "cur_system_cost_combined", "Tháng áp dụng chi phí hệ thống"),
        "### 7.9. Test bắt buộc": ("technical_excluded", None, "Kiểm thử kỹ thuật chi phí hệ thống"),
        "## 8. Sheet `Chi phí khấu hao, lãi nhà đất`": ("covered", "cur_saisan_facility_cost_rules", "Chi phí cơ sở vật chất và tiện ích"),
        "### 8.1. Mục tiêu": ("covered", "cur_saisan_facility_cost_rules", "Mục tiêu chi phí khấu hao lãi nhà đất"),
        "### 8.2. Thứ tự chi phí": ("covered", "cur_facility_cost_breakdown", "Thứ tự 6 khoản chi phí cơ sở vật chất"),
        "### 8.3. Quy tắc filter": ("covered", "cur_saisan_facility_cost_rules", "Quy tắc lọc dữ liệu cơ sở vật chất"),
        "### 8.4. Tháng áp dụng": ("covered", "cur_saisan_facility_cost_rules", "Tháng áp dụng chi phí cơ sở vật chất"),
        "### 8.5. Công thức phải để lại": ("covered", "cur_output_format_preservation", "Công thức tính tổng cơ sở vật chất"),
        "### 8.6. HISTORICAL_04_06_CONTEXT — kết luận audit 04.06 cho Facility": ("historical_excluded", None, "Kết luận audit 04.06 cơ sở vật chất"),
        "### 8.7. Test bắt buộc": ("technical_excluded", None, "Kiểm thử kỹ thuật cơ sở vật chất"),
        "## 9. Sheet `Chi phí tài sản cố định`": ("covered", "cur_fixed_asset_depreciation", "Chi phí tài sản cố định"),
        "### 9.1. Mục tiêu": ("covered", "cur_fixed_asset_depreciation", "Mục tiêu tính chi phí tài sản cố định"),
        "### 9.2. Cột nguồn quan trọng": ("covered", "cur_fixed_asset_depreciation", "Cột nguồn dữ liệu tài sản cố định"),
        "### 9.3. Vùng FORM đích": ("covered", "cur_fixed_asset_depreciation", "Vùng FORM ghi nhận tài sản cố định"),
        "### 9.4. Rule tổng quát": ("covered", "cur_fixed_asset_depreciation", "Quy tắc tổng quát tài sản cố định"),
        "### 9.5. Nếu tháng khấu hao cuối cùng KHÔNG nằm trong FY2027": ("covered", "cur_fixed_asset_depreciation", "Khấu hao ngoài năm tài chính"),
        "### 9.6. Nếu tháng khấu hao cuối cùng nằm trong FY2027": ("covered", "cur_fixed_asset_depreciation", "Khấu hao trong năm tài chính"),
        "### 9.7. Aggregation": ("covered", "cur_fixed_asset_depreciation", "Tổng hợp số liệu tài sản cố định"),
        "### 9.8. Ưu tiên triển khai": ("technical_excluded", None, "Thứ tự triển khai kỹ thuật"),
        "### 9.9. Test bắt buộc": ("technical_excluded", None, "Kiểm thử kỹ thuật tài sản cố định"),
        "## 10. Sheet `Chi phí làm giấy tờ cho NNN`": ("covered", "cur_nnn_paperwork_cost", "Chi phí làm giấy tờ người nước ngoài"),
        "### 10.1. Mục tiêu": ("covered", "cur_nnn_paperwork_cost", "Mục tiêu chi phí giấy tờ NNN"),
        "### 10.2. Vùng FORM đích": ("covered", "cur_nnn_paperwork_cost", "Vùng FORM ghi nhận chi phí NNN dòng 137"),
        "### 10.3. Cách filter đúng": ("covered", "cur_nnn_paperwork_cost", "Cách lọc đúng chi phí NNN"),
        "### 10.4. Cách cộng dữ liệu": ("covered", "cur_nnn_paperwork_cost", "Cách cộng dồn dữ liệu NNN"),
        "### 10.5. Công thức hay giá trị?": ("covered", "cur_nnn_paperwork_cost", "Quy ước ghi giá trị chi phí NNN"),
        "### 10.6. Test bắt buộc": ("technical_excluded", None, "Kiểm thử kỹ thuật chi phí NNN"),
        "## 11. Sheet `Chi phí sinh nhật`": ("covered", "cur_birthday_cost", "Chi phí sinh nhật nhân viên"),
        "### 11.1. Mục tiêu": ("covered", "cur_birthday_cost", "Mục tiêu tính chi phí sinh nhật"),
        "### 11.2. Cách làm": ("covered", "cur_birthday_cost", "Cách tính chi phí sinh nhật"),
        "### 11.3. Rule cộng người mới": ("covered", "cur_birthday_cost", "Quy tắc cộng thêm người mới vào chi phí sinh nhật"),
        "### 11.4. Đơn giá": ("covered", "cur_birthday_cost", "Đơn giá tiền sinh nhật nhân viên"),
        "### 11.5. Xung đột dòng FORM: dòng 63 hay dòng 59": ("reference_with_caveat", "cur_birthday_form_row_conflict", "Đối soát vị trí dòng sinh nhật 63 hay 59 trên các mẫu biểu (tham khảo nội bộ)"),
        "### 11.6. Test bắt buộc": ("technical_excluded", None, "Kiểm thử kỹ thuật sinh nhật"),
        "## 12. Sheet `Chi phí phân bổ từ hành chính`": ("covered", "cur_admin_consumables_12month", "Chi phí phân bổ hành chính"),
        "### 12.1. Nhóm 1 — chi phí phân bổ cho cả 12 tháng": ("covered", "cur_admin_consumables_12month", "Vật tư hành chính tiêu hao 12 tháng"),
        "### 12.2. Nhóm 2 — chi phí đặc thù theo từng tháng": ("covered", "cur_admin_monthly_events", "Chi phí sự kiện đặc thù theo từng tháng"),
        "### 12.3. Lưu ý filter nội dung": ("covered", "cur_admin_monthly_events", "Lưu ý lọc nội dung sự kiện hành chính"),
        "### 12.4. Ví dụ `社員旅行 / Du lịch công ty`": ("covered", "cur_admin_monthly_events", "Quy tắc phân bổ du lịch công ty tháng 5"),
        "### 12.5. Danh sách event/hạng mục đặc thù theo tháng": ("covered", "cur_admin_monthly_events", "Danh mục sự kiện đặc thù theo tháng"),
        "### 12.5.1. HISTORICAL_04_06_CONTEXT — kết luận 04.06 cho event quà không đi du lịch": ("historical_excluded", None, "Kết luận lịch sử 04.06 quà không đi du lịch"),
        "### 12.6. Khám sức khỏe định kỳ nam/nữ": ("covered", "cur_admin_monthly_events", "Khám sức khỏe định kỳ nam/nữ tháng 12"),
        "### 12.7. Nhóm chi phí cho người mới": ("covered", "cur_new_employee_costs", "Chi phí cho nhân sự mới"),
        "### 12.8. Bổ sung hạng mục `Sổ` phân tách nhân viên/công nhân": ("covered", "cur_new_employee_costs", "Sổ nhân viên và sổ công nhân cho người mới"),
        "### 12.9. Chú ý filter `入社月`": ("covered", "cur_new_employee_costs", "Lọc dữ liệu theo tháng nhập việc"),
        "### 12.10. Khám sức khỏe khi tuyển dụng": ("covered", "cur_new_employee_costs", "Khám sức khỏe tuyển dụng tháng sau khi vào"),
        "### 12.11. Test bắt buộc cho administrative allocation": ("technical_excluded", None, "Kiểm thử kỹ thuật phân bổ hành chính"),
        "## 13. Sheet `勘定科目` — account master": ("covered", "cur_saisan_account_lookup_chain", "Danh mục tài khoản kế toán"),
        "### 13.1. Vai trò": ("covered", "cur_saisan_account_lookup_chain", "Vai trò của bảng tra cứu tài khoản"),
        "### 13.2. Rule tra account": ("covered", "cur_saisan_account_lookup_chain", "Quy tắc tra cứu mã tài khoản kế toán"),
        "### 13.3. Không dùng sai cột": ("covered", "cur_saisan_account_lookup_chain", "Không dùng sai cột mã tài khoản"),
        "### 13.4. Nếu account trống": ("covered", "cur_saisan_account_lookup_chain", "Xử lý khi mã tài khoản để trống"),
        "## 14. Sheet `原価センタ` — Cost Center master": ("covered", "cur_saisan_cost_center_hierarchy", "Danh mục Cost Center và phòng ban"),
        "### 14.1. Vai trò": ("covered", "cur_saisan_cost_center_hierarchy", "Vai trò bảng Cost Center"),
        "### 14.2. Rule chính": ("covered", "cur_saisan_cost_center_hierarchy", "Quy tắc chính xác định Cost Center"),
        "### 14.3. Test bắt buộc": ("technical_excluded", None, "Kiểm thử kỹ thuật Cost Center"),
        "## 15. Thứ tự ưu tiên triển khai theo file yêu cầu": ("technical_excluded", None, "Kế hoạch phân kỳ triển khai kỹ thuật"),
        "### Phase 1 — Chuẩn hóa nền tảng mapping": ("technical_excluded", None, "Phase 1 kỹ thuật"),
        "### Phase 2 — NNN paperwork": ("technical_excluded", None, "Phase 2 kỹ thuật"),
        "### Phase 3 — Administrative allocation": ("technical_excluded", None, "Phase 3 kỹ thuật"),
        "### Phase 4 — System cost": ("technical_excluded", None, "Phase 4 kỹ thuật"),
        "### Phase 5 — FORM style/formula preservation": ("technical_excluded", None, "Phase 5 kỹ thuật"),
        "### Phase 6 — Birthday": ("technical_excluded", None, "Phase 6 kỹ thuật"),
        "### Phase 7 — Facility": ("technical_excluded", None, "Phase 7 kỹ thuật"),
        "### Phase 8 — Fixed assets": ("technical_excluded", None, "Phase 8 kỹ thuật"),
        "## 16. GAP cần agent kiểm tra trong repo hiện tại": ("technical_excluded", None, "Danh sách GAP kiểm tra kỹ thuật của lập trình viên"),
        "## 17. Các test tối thiểu cần viết": ("technical_excluded", None, "Danh sách test cases cho lập trình viên"),
        "### 17.1. Master resolver tests": ("technical_excluded", None, "Test kỹ thuật master resolver"),
        "### 17.2. NNN tests": ("technical_excluded", None, "Test kỹ thuật NNN"),
        "### 17.3. Administrative allocation tests": ("technical_excluded", None, "Test kỹ thuật phân bổ"),
        "### 17.4. System cost tests": ("technical_excluded", None, "Test kỹ thuật system"),
        "### 17.5. Birthday tests": ("technical_excluded", None, "Test kỹ thuật sinh nhật"),
        "### 17.6. Facility tests": ("technical_excluded", None, "Test kỹ thuật facility"),
        "### 17.7. Fixed assets tests": ("technical_excluded", None, "Test kỹ thuật fixed assets"),
        "### 17.8. FORM output tests": ("technical_excluded", None, "Test kỹ thuật FORM output"),
        "## 18. Các điểm cần xác nhận trước khi code mạnh": ("technical_excluded", None, "Các điểm mâu thuẫn kỹ thuật dành cho lập trình viên"),
        "## 19. Checklist agent trước khi sửa code": ("technical_excluded", None, "Checklist thao tác của lập trình viên"),
        "## 20. Prompt đề xuất để giao cho agent code": ("technical_excluded", None, "Mẫu prompt giao việc kỹ thuật"),
        "## 21. Tóm tắt ngắn cho người không chuyên": ("covered", "cur_saisan_purpose_and_workflow", "Tóm tắt ngắn quy trình cho người vận hành"),
        "## 22. Historical layout output evidence from the 09.06.2026 file": ("historical_excluded", None, "Bằng chứng layout lịch sử từ file 09.06"),
        "### 22.1. Dữ liệu output bắt đầu từ dòng 38": ("covered", "cur_output_layout_row38_preservation", "Bố cục dữ liệu kết quả bắt đầu từ dòng 38"),
        "### 22.2. Cột A đến D từ dòng 38 trở đi phải màu trắng": ("covered", "cur_output_format_preservation", "Định dạng màu trắng cột A-D"),
        "### 22.3. Cột E từ dòng 38 trở xuống không được có giải thích": ("covered", "cur_claim_col_e_no_description", "Cột E không được chứa câu giải thích tự thêm"),
        "### 22.4. Giải thích/diễn giải phải lấy từ cột B của sheet `*配賦額一覧`": ("covered", "cur_claim_col_e_no_description", "Lấy tên hạng mục chuẩn từ cột B sheet phân bổ"),
        "### 22.5. Workbook Excel gốc thắng markdown khi mâu thuẫn": ("covered", "cur_saisan_purpose_and_workflow", "Nguyên tắc workbook gốc có thẩm quyền cao nhất"),
        "### 22.6. Không quay lại cách xuất cố định theo từng dòng": ("covered", "cur_source_file_order_rule", "Xuất động theo thứ tự tệp nguồn"),
        "### 22.7. Không hardcode Cost Center `1412000040`": ("technical_excluded", None, "Chỉ dẫn lập trình không hardcode mã phòng"),
        "### 22.8. Không hardcode/map riêng file `16.KDTVN 電気製造技術課_MP FY2027_各予定(Ver01)`": ("technical_excluded", None, "Chỉ dẫn lập trình xử lý file tổng quát"),
        "### 22.9. Xóa nội dung cũ trước khi xuất output mới": ("covered", "cur_output_format_preservation", "Quy tắc xóa sạch dữ liệu cũ dòng 38 trước khi ghi mới"),
        "## 23. Trạng thái hoàn thiện theo Excel gốc 09.06.2026": ("historical_excluded", None, "Trạng thái lịch sử đối soát 09.06"),
        "## 24. Regression guard — các bug đã biết từ Excel gốc": ("covered", "cur_claim_medical_check_dedup", "Chống lỗi lặp 2 lần chi phí y tế và dồn tháng 12"),
        "### 24.1. Khám sức khỏe định kỳ bị lặp 2 lần": ("covered", "cur_claim_medical_check_dedup", "Quy tắc chống lặp 2 lần chi phí khám sức khỏe"),
        "### 24.2. Chi phí người mới bị gom hết vào tháng 12": ("covered", "cur_claim_new_hire_month_allocation", "Quy tắc phân bổ người mới theo đúng tháng vào"),
        "## 25. Yêu cầu bổ sung mô tả": ("technical_excluded", None, "Yêu cầu bổ sung mô tả kỹ thuật nội bộ"),
        "## 26. User claims — lỗi người dùng phát hiện khi sử dụng chương trình": ("covered", "cur_claim_col_e_no_description", "Tổng hợp và phân loại phản hồi lỗi từ người dùng"),
        "### 26.1. Claim 12: Cột E không được phép tồn tại mô tả": ("covered", "cur_claim_col_e_no_description", "Claim 12: Cột E không chứa mô tả"),
        "### 26.2. Claim 13: Chưa có tiền du lịch của tháng 5": ("covered", "cur_admin_monthly_events", "Claim 13: Tiền du lịch tháng 5"),
        "### 26.3. Claim 14: Code 5005246282 chỉ chạy được từ tháng 4 đến tháng 6": ("reference_with_caveat", "cur_claim_system_cost_q1_simulation", "Claim 14: Mã hệ thống 5005246282 mô phỏng 3 tháng đầu quý 1 (tham khảo nội bộ)"),
        "### 26.4. Claim 15: Tháng 12 đang mặc định nhân chi phí người mới với tổng số người": ("covered", "cur_claim_new_hire_month_allocation", "Claim 15: Phân bổ người mới đúng tháng"),
        "### 26.5. Claim 16: Chi phí `社員証用写真のみ` không cần cho người mới": ("covered", "cur_claim_photo_not_for_new_hire", "Claim 16: Ảnh thẻ không tính cho người mới"),
        "### 26.6. Claim 17: Dòng `ペン Bút` thiếu dữ liệu cột C, D": ("reference_with_caveat", "cur_claim_pen_stationery_account_fill", "Claim 17: Điền mã tài khoản văn phòng phẩm cho dòng Bút (tham khảo nội bộ)"),
        "### 26.7. Claim 18: Dòng 64-69 trùng với dòng 30-35 nhưng code chi phí sai": ("reference_with_caveat", "cur_claim_duplicate_cost_row_standardization", "Claim 18: Chuẩn hóa trùng lặp dòng chi phí 64-69 và 30-35 (tham khảo nội bộ)"),
        "### 26.8. Claim 19: Không có chi phí ở dòng 73, 74, 75": ("reference_with_caveat", "cur_claim_blank_cost_rows_73_75", "Claim 19: Dòng trống 73-75 là dòng dự phòng không có số tiền (tham khảo nội bộ)"),
        "### 26.9. Tổng hợp claims và phân loại": ("technical_excluded", None, "Bảng phân loại claim kỹ thuật"),
        "## 27. Yêu cầu bổ sung — item 20: Chi phí event theo tháng chưa chạy được": ("covered", "cur_admin_monthly_events", "Phân bổ sự kiện theo tháng"),
        "### 27.1. Nội dung yêu cầu": ("covered", "cur_admin_monthly_events", "Chi tiết yêu cầu phân bổ sự kiện đúng tháng"),
        "### 27.2. Ngoại lệ: chi phí có \"số người riêng\"": ("reference_with_caveat", "cur_special_cost_custom_headcount", "Quy tắc áp dụng số người tham gia riêng cho khoản chi đặc thù (tham khảo nội bộ)"),
        "### 27.3. Ưu tiên giữa yêu cầu 7 và yêu cầu 20": ("covered", "cur_admin_monthly_events", "Ưu tiên giữa các yêu cầu phân bổ sự kiện"),
        "## 28. Cập nhật master `原価センタ` — 5 Cost Center mới": ("covered", "cur_saisan_cost_center_hierarchy", "5 Cost Center mới được bổ sung vào hệ thống"),
        "## 21. BUG: Chi phí phát thực tế (配布数) bị tính sai bằng headcount delta": ("covered", "cur_claim_actual_distribution_count_rule", "23 rules cấp phát thực tế phải nhập số lượng phát thật"),
        "### Mô tả vấn đề": ("covered", "cur_claim_actual_distribution_count_rule", "Mô tả lỗi tính sai bằng headcount delta"),
        "### 23 Rules bị ảnh hưởng": ("covered", "cur_claim_actual_distribution_count_rule", "Danh sách 23 quy tắc chi phí có từ khóa 配布数"),
        "### Cách fix": ("covered", "cur_claim_actual_distribution_count_rule", "Cách nhập số lượng phát thực tế qua hộp thoại sự kiện"),
    }
}


def compute_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_headings(file_path: Path) -> List[str]:
    headings = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        line_s = line.strip()
        if re.match(r"^#{1,6}\s+", line_s):
            headings.append(line_s)
    return headings


def normalize_heading_for_rule_match(heading: str) -> str:
    return heading.replace("`", "")


def build_inventory() -> List[Dict[str, Any]]:
    inventory: List[Dict[str, Any]] = []

    for rel_path in ALL_TARGET_DOCS:
        full_path = REPO_ROOT / rel_path
        if not full_path.is_file():
            raise FileNotFoundError(f"Target document file declared in ALL_TARGET_DOCS does not exist: {rel_path}")
        sha256 = compute_sha256(full_path)
        headings = extract_headings(full_path)
        rules = HEADING_RULES.get(rel_path, {})
        default_policy = DEFAULT_DOC_POLICIES.get(rel_path)

        for heading in headings:
            rule = rules.get(heading) or rules.get(normalize_heading_for_rule_match(heading))
            if rule:
                classification, topic, reason = rule
            elif default_policy:
                classification, topic, reason = default_policy
            else:
                classification = "needs_owner_review"
                topic = None
                reason = f"Heading in {rel_path} requires business owner classification review."

            inventory.append({
                "source_path": rel_path,
                "source_section": heading,
                "source_sha256": sha256,
                "classification": classification,
                "curated_topic": topic,
                "reason": reason
            })

    for entry in OTHER_DOCS_INVENTORY:
        path = REPO_ROOT / entry["source_path"]
        if not path.is_file():
            raise FileNotFoundError(f"Required source file not found: {entry['source_path']}")
        sha256 = compute_sha256(path)
        inventory.append({
            "source_path": entry["source_path"],
            "source_section": entry["source_section"],
            "source_sha256": sha256,
            "classification": entry["classification"],
            "curated_topic": entry["curated_topic"],
            "reason": entry["reason"]
        })

    # Auto-discover versioned Fiscal Year update packs
    updates_dir = REPO_ROOT / "docs" / "knowledge" / "business_chat" / "updates"
    if updates_dir.is_dir():
        for update_file in sorted(updates_dir.glob("FY*/*.json")):
            try:
                up_data = json.loads(update_file.read_text(encoding="utf-8"))
                if not up_data.get("is_active", True) or up_data.get("status") == "draft":
                    continue
                up_id = str(up_data.get("update_id", update_file.stem)).strip()
                rel_p = str(update_file.relative_to(REPO_ROOT)).replace("\\", "/")
                cls = str(up_data.get("status", "confirmed")).strip().lower()
                classification = "covered" if cls == "confirmed" else "reference_with_caveat"
                vi_title = up_data.get("title", {}).get("vi", up_id)
                sha256 = compute_sha256(update_file)
                inventory.append({
                    "source_path": rel_p,
                    "source_section": vi_title,
                    "source_sha256": sha256,
                    "classification": classification,
                    "curated_topic": up_id,
                    "reason": f"Bản cập nhật kiến thức {up_data.get('fiscal_year', 'FY2028')}."
                })
            except Exception:
                continue

    return inventory


PACK_SOURCE_MAP = {
    "cur_saisan_purpose_and_workflow": "curated_cost_allocation_guidance",
    "cur_saisan_cost_center_hierarchy": "curated_cost_allocation_guidance",
    "cur_saisan_account_lookup_chain": "curated_cost_allocation_guidance",
    "cur_saisan_manual_input_channels": "curated_cost_allocation_guidance",
    "cur_saisan_facility_cost_rules": "curated_cost_allocation_guidance",
    "cur_manual_special_cost_inheritance": "curated_cost_allocation_guidance",
    "cur_output_cost_row_reordering": "curated_cost_allocation_guidance",
    "cur_quick_search_departments": "curated_cost_allocation_guidance",
    "cur_budget_variance_yoy_analysis": "curated_cost_allocation_guidance",
    "cur_module_implementation_status": "curated_cost_allocation_guidance",
    "cur_roadmap_operational_priorities": "curated_cost_allocation_guidance",
    "cur_target_output_cell_ranges": "curated_cost_allocation_guidance",
    "cur_saisan_implementation_dashboard": "curated_cost_allocation_guidance",
    "cur_admin_consumables_12month": "curated_staffing_headcount_guidance",
    "cur_bus_transportation_cost": "curated_staffing_headcount_guidance",
    "cur_new_employee_costs": "curated_staffing_headcount_guidance",
    "cur_staffing_override_settings": "curated_staffing_headcount_guidance",
    "cur_source_file_order_rule": "curated_staffing_headcount_guidance",
    "cur_uniform_and_folding_cups": "curated_staffing_headcount_guidance",
    "cur_legacy_staffing_exclusion": "curated_staffing_headcount_guidance",
    "cur_event_driver_standards": "curated_staffing_headcount_guidance",
    "cur_special_cost_custom_headcount": "curated_staffing_headcount_guidance",
    "cur_system_cost_combined": "curated_calculation_output_guidance",
    "cur_fixed_asset_depreciation": "curated_calculation_output_guidance",
    "cur_birthday_cost": "curated_calculation_output_guidance",
    "cur_nnn_paperwork_cost": "curated_calculation_output_guidance",
    "cur_allocation_travel_shared": "curated_calculation_output_guidance",
    "cur_fiscal_year_calendar": "curated_calculation_output_guidance",
    "cur_system_cost_account_mapping": "curated_calculation_output_guidance",
    "cur_facility_cost_breakdown": "curated_calculation_output_guidance",
    "cur_admin_monthly_events": "curated_calculation_output_guidance",
    "cur_form_column_alignment": "curated_calculation_output_guidance",
    "cur_fixed_assets_audit_history": "curated_calculation_output_guidance",
    "cur_birthday_form_row_conflict": "curated_calculation_output_guidance",
    "cur_output_format_preservation": "curated_operational_errors_guidance",
    "cur_provenance_labels_operators": "curated_operational_errors_guidance",
    "cur_run_history_statuses": "curated_operational_errors_guidance",
    "cur_output_layout_row38_preservation": "curated_operational_errors_guidance",
    "cur_claim_col_e_no_description": "curated_operational_errors_guidance",
    "cur_claim_medical_check_dedup": "curated_operational_errors_guidance",
    "cur_claim_new_hire_month_allocation": "curated_operational_errors_guidance",
    "cur_claim_photo_not_for_new_hire": "curated_operational_errors_guidance",
    "cur_claim_actual_distribution_count_rule": "curated_operational_errors_guidance",
    "cur_claim_system_cost_q1_simulation": "curated_operational_errors_guidance",
    "cur_claim_pen_stationery_account_fill": "curated_operational_errors_guidance",
    "cur_claim_duplicate_cost_row_standardization": "curated_operational_errors_guidance",
    "cur_claim_blank_cost_rows_73_75": "curated_operational_errors_guidance",
    "cur_ai_assistant_diagnostics": "curated_ai_operations_assistant_guidance",
    "cur_ai_assistant_copy_response": "curated_ai_operations_assistant_guidance",
    "cur_ai_assistant_image_paste": "curated_ai_operations_assistant_guidance",
    "cur_ai_assistant_language_policy": "curated_ai_operations_assistant_guidance",
    "cur_ai_assistant_separation_of_concerns": "curated_ai_operations_assistant_guidance",
    "cur_ai_assistant_evidence_limits": "curated_ai_operations_assistant_guidance",
    "cur_ai_assistant_confidence_levels": "curated_ai_operations_assistant_guidance",
    "cur_operations_error_taxonomy": "curated_ai_operations_assistant_guidance",
    "cur_ai_assistant_unknown_error_handling": "curated_ai_operations_assistant_guidance",
    "cur_ai_assistant_explicit_boundaries": "curated_ai_operations_assistant_guidance",
    "cur_dashboard_audit_status": "curated_ai_operations_assistant_guidance",
    "bck_locked_file": "operations_knowledge_base",
    "bck_missing_baseline": "operations_knowledge_base",
    "bck_source_validation": "operations_knowledge_base",
    "bck_headcount_input": "approved_business_guidance",
}


def build_coverage_matrix(inventory: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    matrix: List[Dict[str, Any]] = []

    for idx, item in enumerate(inventory, 1):
        topic_id = item.get("curated_topic")
        classification = item.get("classification")
        source_id = PACK_SOURCE_MAP.get(topic_id, "approved_business_guidance" if classification == "covered" else "")

        error_code = ""
        if topic_id == "bck_locked_file" or "file_lock" in str(topic_id):
            error_code = "blocked_output_file_lock"
        elif topic_id == "bck_missing_baseline" or "baseline" in str(topic_id):
            error_code = "missing_staffing_baseline"
        elif topic_id == "bck_source_validation" or "validation" in str(topic_id):
            error_code = "preflight_source_validation_failure"

        entry = {
            "item_id": f"cov_item_{idx:03d}",
            "business_item": item["source_section"],
            "source_id": source_id,
            "source_path": item["source_path"],
            "source_section": item["source_section"],
            "source_sha256": item["source_sha256"],
            "status": "covered" if classification == "covered" else classification,
            "curated_topic_id": topic_id,
            "mapped_chunks": [f"chk_{topic_id}_vi", f"chk_{topic_id}_en", f"chk_{topic_id}_ja"] if topic_id else [],
            "test_cases": [f"test_retrieval_{topic_id}"] if topic_id else [],
            "error_code": error_code,
            "reason": item["reason"]
        }
        matrix.append(entry)

    return matrix


def generate_source_discovery_inventory() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Programmatically generate source discovery inventory and coverage matrix."""
    inventory = build_inventory()
    matrix = build_coverage_matrix(inventory)

    out_inv = REPO_ROOT / "docs" / "knowledge" / "business_chat" / "source_discovery_inventory.json"
    out_mat = REPO_ROOT / "docs" / "knowledge" / "business_chat" / "coverage_matrix.json"

    out_inv_data = {"schema_version": "2.0", "items": inventory}
    out_mat_data = {"schema_version": "2.0", "items": matrix}

    out_inv.write_text(json.dumps(out_inv_data, indent=2, ensure_ascii=False), encoding="utf-8")
    out_mat.write_text(json.dumps(out_mat_data, indent=2, ensure_ascii=False), encoding="utf-8")
    return inventory, matrix


def main() -> None:
    inventory, matrix = generate_source_discovery_inventory()

    print(f"Successfully generated inventory with {len(inventory)} items.")
    print(f"Successfully generated coverage matrix with {len(matrix)} items.")

    # Counts by classification
    counts: Dict[str, int] = {}
    for item in inventory:
        c = item["classification"]
        counts[c] = counts.get(c, 0) + 1
    print("Classification summary:", counts)


if __name__ == "__main__":
    main()
