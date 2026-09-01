# Danh mục tính năng MP2027

> **Document Control**: Owner: MP Engineering | Status: Approved / Production-Ready for accepted entries; F-020 is pending manual acceptance | Last Updated: 2026-09-01 | Active Features: F-001..F-020

Danh mục này được viết theo hướng thận trọng: chỉ ghi nhận các bề mặt đã triển khai và kỳ vọng xác minh, không đưa ra cam kết kế toán chưa được tài liệu hóa.

| Mã tính năng | Bề mặt | Ranh giới nguồn | Bằng chứng chính | Rủi ro phát hành |
|---|---|---|---|---|
| F-001 | Xác định dự án/đường dẫn | `src/services/project_config.py` | `test_project_config*.py`, kiểm tra sức khỏe bản đóng gói | Cao |
| F-002 | Kiểm tra trước nguồn năm tài chính | `src/services/fiscal_run.py` | Test chính sách năm tài chính/nguồn | Cao |
| F-003 | Bộ đọc workbook | `src/parsers/` | Test hồi quy bộ đọc | Cao |
| F-004 | Schema/migration SQLite | `src/db/schema.py`, `src/db/migrations.py` | Test migration và tài liệu schema | Cao |
| F-005 | Bộ máy phân bổ | `src/engine/allocator.py` | Test phân bổ và driver | Nghiêm trọng |
| F-006 | Xuất theo trung tâm chi phí/thứ tự nguồn | `src/engine/*writer.py`, `src/engine/source_order_output.py` | Test xuất/thứ tự nguồn | Nghiêm trọng |
| F-007 | Truy vết/kiểm toán tài sản cố định | `src/audit/`, các script tài sản cố định | Test/báo cáo kiểm toán tài sản cố định | Cao |
| F-008 | Lịch sử chạy và kết quả kiểm toán | `src/services/run_history.py` | Test lịch sử/runtime | Trung bình |
| F-009 | Điều phối giao diện | `src/universal_app.py` | Test nhanh giao diện/đường dẫn | Cao |
| F-010 | Sức khỏe runtime | `src/services/runtime_health.py`, `scripts/run_e2e.py` | Test sức khỏe runtime | Cao |
| F-011 | Gói nội dung kiểm tra toàn vẹn | `src/services/content_packs.py` | Test gói nội dung/an toàn SHA-256 | Cao |
| F-012 | Cập nhật ứng dụng qua LAN | `src/services/app_updates.py` | Test cập nhật/an toàn HASH_ONLY_LAN | Nghiêm trọng |
| F-013 | Gói portable onedir | `MP2027_Portable.spec`, `scripts/package_app.py` | Test đóng gói + sức khỏe EXE | Nghiêm trọng |
| F-014 | Trình khởi chạy ổn định/bộ cài ban đầu | `MP2027_Manager.spec`, `scripts/update_launcher.py`, `installer/` | Hợp đồng đóng gói + diễn tập Windows sạch | Nghiêm trọng |
| F-015 | Kế thừa & bảo tồn chi phí riêng liên năm | `src/engine/manual_special_cost_sections.py`, `src/services/project_config.py` | `tests/test_manual_special_cost_sections.py` | Cao |
| F-016 | Sắp xếp thứ tự dòng chi phí kéo-thả | `src/engine/output_cost_row_ordering.py`, `src/universal_app.py` | `tests/test_output_cost_row_ordering.py`, `test_gui_cost_center_and_output_actions.py` | Cao |
| F-017 | Tìm kiếm nhanh phòng ban màn hình chính | `src/universal_app.py` | `tests/test_gui_cost_center_and_output_actions.py` | Trung bình |
| F-018 | So sánh biến động cùng kỳ (YoY) & Biểu đồ | `src/engine/variance_analyzer.py`, `src/ui/variance_chart.py`, `src/ui/tabs/variance_tab.py`, `src/utils/excel_variance_writer.py` | `tests/engine/test_variance_analyzer.py`, `tests/ui/test_variance_chart.py` | Cao |
| F-019 | An toàn giao diện & Khóa chống xung đột | `src/universal_app.py` | `tests/test_singleton_editor_windows.py`, `tests/test_variance_window_layering.py` | Cao |
| F-020 | Trợ lý Vận hành & Xử lý Lỗi (MVP Read-only, chờ nghiệm thu thủ công) | `src/services/operations_case_service.py`, `src/services/operations_knowledge.py`, `src/ui/operations_assistant.py` | `tests/services/test_operations_case_service.py`, `tests/services/test_operations_knowledge.py`, `tests/ui/test_operations_assistant.py` | Trung bình |

## Quy tắc cho các thay đổi sau này

1. Thay đổi công thức hoặc driver phải cập nhật test đặc trưng hóa liên quan và bằng chứng quy tắc nghiệp vụ, không chỉ test giao diện.
2. Thay đổi schema phải bổ sung migration và sinh lại `docs/database/schema_catalog.json` cùng `docs/database/data_dictionary.md`.
3. Thay đổi đường dẫn hoặc đóng gói phải chạy kiểm tra sức khỏe source và EXE đã đóng gói.
4. Bản cập nhật phát hành phải dùng gói `.mpupdate` kèm mã băm SHA-256 trên thư mục LAN đã duyệt (`HASH_ONLY_LAN`); không phân phối các mô-đun Python rời cho người dùng.
5. Thay đổi giá/ánh xạ riêng của bộ phận chỉ được đưa vào gói nội dung sau khi xác minh driver và hợp đồng tài khoản mà bộ máy hỗ trợ.

## Danh mục máy đọc được

Danh mục sinh tự động ở cấp mô-đun là `reports/quality_baseline.json`. Sinh lại bằng:

```powershell
py scripts/generate_quality_baseline.py
```
