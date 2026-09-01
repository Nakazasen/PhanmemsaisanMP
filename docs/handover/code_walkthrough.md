# MP2027 Manager — hướng dẫn đọc code

Tài liệu này là bản đồ nhanh cho toàn bộ **production code**. Các module, class và function trong code đã có docstring; tài liệu này giải thích cách chúng nối với nhau ở mức chương trình. Thư mục `tests/` chỉ chứa kiểm thử, không phải luồng chạy của người dùng.

## 1. Luồng chạy chính

```text
Windows launcher
  -> packaging/mp2027_portable_entry.py
  -> src/universal_app.py
       -> runtime_health.py: chọn thư mục dữ liệu ổn định
       -> project_config.py: đọc project.json và đường dẫn nguồn
       -> fiscal_run.py: preflight, kiểm tra thiếu/lỗi dữ liệu
       -> db/loader.py + db/schema.py + db/migrations.py
       -> parsers/: đọc từng nhóm nguồn
       -> engine/: tính toán và ghi workbook kết quả
       -> services/run_history.py: lưu lịch sử và evidence
```

Luồng dòng lệnh `scripts/run_e2e.py` dùng cùng parser, service, database và engine như GUI; khác biệt chỉ là giao diện gọi. Vì vậy khi sửa quy tắc nghiệp vụ, ưu tiên sửa `src/`, không nhúng logic mới vào GUI hoặc script.

## 2. Quy tắc đọc code

- `parsers/` chỉ đọc và chuẩn hóa dữ liệu; không tự ghi file kết quả.
- `services/` kiểm tra nguồn, transaction, runtime state và điều phối các bước.
- `db/` là nơi định nghĩa schema, migration và đọc master data.
- `engine/` tính toán/ghi output sau khi dữ liệu đã qua preflight.
- `audit/` chỉ kiểm tra, đối chiếu và tạo evidence; không được âm thầm sửa dữ liệu nguồn.
- `scripts/` là entry point vận hành, build, kiểm thử hoặc audit; không phải lớp nghiệp vụ dùng lại.

## 3. Module gốc và đóng gói

| File | Vai trò |
|---|---|
| `src/__init__.py` | Khai báo package ứng dụng. |
| `src/config.py` | Các cấu hình/giá trị tương thích cũ. |
| `src/universal_app.py` | GUI chính, điều phối thao tác người dùng và pipeline. |
| `packaging/mp2027_portable_entry.py` | Entry point nhẹ cho executable đã đóng gói; xử lý health-check trước khi tải GUI. |

## 4. Database và schema

| File | Vai trò |
|---|---|
| `src/db/__init__.py` | Mô tả package database. |
| `src/db/schema.py` | Tạo bảng SQLite và các ràng buộc dữ liệu. |
| `src/db/migrations.py` | Migration có version, chạy fail-closed khi schema không tương thích. |
| `src/db/loader.py` | Nạp cost center, account, entitlement và allocation rules vào database. |
| `src/db/fy2027_compat.py` | Quy tắc tương thích chỉ dành cho FY2027. |

## 5. Parser — đọc nguồn đầu vào

| File | Vai trò |
|---|---|
| `src/parsers/__init__.py` | Mô tả package parser. |
| `src/parsers/facility.py` | Đọc nguồn Facilities/施設課. |
| `src/parsers/fixed_assets.py` | Đọc fixed assets/khấu hao. |
| `src/parsers/ga.py` | Đọc nguồn GA và chi phí hành chính. |
| `src/parsers/it_sim.py` | Đọc mô phỏng chi phí IT. |
| `src/parsers/birthday.py` | Đọc chi phí sinh nhật. |
| `src/parsers/nnn_paperwork.py` | Đọc chi phí giấy tờ lao động nước ngoài. |
| `src/parsers/headcount_time_plan.py` | Đọc kế hoạch headcount/thời gian theo phòng ban. |
| `src/parsers/extracted_headcount_time_plan.py` | Đọc workbook staffing đã trích xuất từ Master Plan. |
| `src/parsers/manual_headcount.py` | Đọc và kiểm tra headcount nhập thủ công. |
| `src/parsers/manual_event_drivers.py` | Đọc driver sự kiện không thể suy ra tự động. |
| `src/parsers/manual_special_costs.py` | Đọc các khoản chi phí đặc biệt nhập thủ công. |

## 6. Engine — quy tắc tính và ghi output

| File | Vai trò |
|---|---|
| `src/engine/__init__.py` | Mô tả package engine. |
| `src/engine/allocator.py` | Engine phân bổ chi phí theo driver đã xác thực. |
| `src/engine/account_resolver.py` | Chọn account theo cost center và cost type. |
| `src/engine/hub_builder.py` | Dựng hub/khung workbook kết quả. |
| `src/engine/mp_saisan_complete_export.py` | Điều phối export MP Saisan hoàn chỉnh. |
| `src/engine/cost_center_context.py` | Kiểm tra context cost center trước khi ghi. |
| `src/engine/output_mode.py` | Định nghĩa mode đặt dòng output. |
| `src/engine/output_placement.py` | Lập kế hoạch vị trí dòng thuần (không side effect). |
| `src/engine/source_order_output.py` | Đặt output theo thứ tự file nguồn. |
| `src/engine/complete_v1_source_order_writer.py` | Ghi workbook theo thứ tự nguồn cho complete-v1. |
| `src/engine/facility_file_order_preview.py` | Preview thứ tự file Facilities. |
| `src/engine/facility_file_order_writer.py` | Ghi/export thứ tự file Facilities. |
| `src/engine/admin_consumables_preview.py` | Preview chi phí vật tư hành chính. |
| `src/engine/admin_consumables_writer.py` | Ghi chi phí vật tư hành chính. |
| `src/engine/system_cost_preview.py` | Preview chi phí hệ thống. |
| `src/engine/system_cost_writer.py` | Ghi chi phí hệ thống. |
| `src/engine/fixed_assets_reference_skeleton.py` | Dựng skeleton tham chiếu fixed assets. |
| `src/engine/reference_assisted_fill.py` | Bổ sung output dựa trên reference đã kiểm tra. |
| `src/engine/column_s_normalizer.py` | Chuẩn hóa mô tả cột S trong workbook detail. |
| `src/engine/uniform_cup_rules.py` | Chuẩn hóa entitlement uniform/cup và identity của rule. |
| `src/engine/manual_special_cost_sections.py` | Kế thừa/bảo tồn chi phí riêng nhập tay theo năm tài chính; xóa tiền khi sang FY mới. |
| `src/engine/output_cost_row_ordering.py` | Quản lý thứ tự dòng chi phí kéo-thả, snapshot layout và sheet ẩn `_mp2027_manual_special_meta`. |
| `src/engine/variance_analyzer.py` | Phân tích biến động cùng kỳ (YoY) với bộ giải công thức AST `_MpFormulaResolver`. |
| `src/engine/fy2027_compat.py` | Metadata tương thích engine riêng cho FY2027. |

## 7. Services và UI — điều phối và runtime

| File | Vai trò |
|---|---|
| `src/services/__init__.py` | Mô tả package service. |
| `src/services/fiscal_run.py` | Resolve nguồn theo FY và preflight fail-closed. |
| `src/services/project_config.py` | Đọc/ghi cấu hình project (`manual_special_inheritance_dir`, `manual_special_legacy_starts`). |
| `src/services/headcount_source_policy.py` | Chính sách chọn nguồn staffing theo từng field/tháng. |
| `src/services/headcount_source_importer.py` | Import staffing official/extracted trong transaction. |
| `src/services/manual_staffing_overrides.py` | Lưu override staffing thủ công. |
| `src/services/preflight_cache.py` | Cache metadata của báo cáo preflight. |
| `src/services/reference_staffing_extractor.py` | Trích xuất staffing có trace từ Master Plan. |
| `src/services/reference_staffing_render_worker.py` | Worker COM tách riêng để render Excel reference. |
| `src/services/run_history.py` | Lưu lịch sử chạy, checksum, backup và catalog workspace. |
| `src/services/runtime_health.py` | Health-check release, thư mục ghi được, FORM và SQLite. JSON health-check dùng ASCII để chạy an toàn trên console CP932. |
| `src/services/app_updates.py` | Stage, hash-check, health-check, activate và rollback app onedir. |
| `src/services/update_delivery.py` | Dò nguồn folder/HTTPS, đọc catalog, tải atomic và kiểm tra SHA-256. |
| `src/services/update_security.py` | Hash, manifest validation, safe extraction; không dùng signing key. |
| `src/services/content_packs.py` | Cài và kiểm tra gói rule dữ liệu bằng manifest/hash. |
| `src/services/operations_case_service.py` | Lắp ráp tình huống vận hành (OperationalCase) chỉ đọc từ bằng chứng RUN_HISTORY. |
| `src/services/operations_knowledge.py` | Kho tri thức lỗi chuẩn tắc bất biến, hỗ trợ giải thích đa ngôn ngữ (VI/EN/JA). |
| `src/ui/operations_assistant.py` | Hộp thoại Trợ lý Vận hành & Xử lý Lỗi (presentation-only shell, singleton guard). |
| `src/ui/tabs/variance_tab.py` | Tab giao diện điều phối phân tích so sánh biến động chi phí YoY. |
| `src/ui/variance_chart.py` | Cửa sổ biểu đồ Top 12 biến động Matplotlib, tự tìm font đa ngôn ngữ (NotoSans, Meiryo, YuGothic). |

## 8. Utility và audit

| File | Vai trò |
|---|---|
| `src/utils/__init__.py` | Mô tả package utility. |
| `src/utils/cli.py` | Parser/console helper tương thích Windows code page. |
| `src/utils/excel_helpers.py` | Hàm đọc, chuẩn hóa và kiểm tra Excel. |
| `src/utils/excel_variance_writer.py` | Xuất workbook so sánh biến động và nhúng biểu đồ BarChart native. |
| `src/utils/fiscal_periods.py` | Mapping tháng tài chính và file nguồn; phát hiện gap/overlap. |
| `src/utils/source_manifest.py` | Detect, lưu và resolve manifest file nguồn. |
| `src/audit/exchange_rate_audit.py` | Kiểm tra tỷ giá USD/VND trong workbook. |
| `src/audit/fixed_assets_coverage.py` | Đánh giá độ phủ fixed-assets source/reference. |
| `src/audit/pipeline_audit.py` | Tạo báo cáo audit pipeline và missing-input. |
| `src/audit/real_pipeline_validator.py` | Acceptance check read-only cho một run thực. |

## 9. Scripts vận hành

| File | Vai trò |
|---|---|
| `scripts/run_e2e.py` | Chạy pipeline từ command line. |
| `scripts/run_real_pipeline_acceptance.py` | Chạy acceptance trên dữ liệu thật theo profile. |
| `scripts/package_app.py` | Build app/launcher, bundle, health-check và publish artifact. |
| `scripts/update_launcher.py` | Launcher ổn định, resolve `current.json` và khởi chạy version active. |
| `scripts/convert_icon.py` | Chuyển icon sang định dạng dùng khi đóng gói Windows. |
| `scripts/extract_reference_staffing_sources.py` | Trích xuất staffing reference. |
| `scripts/export_schema_documentation.py` | Xuất tài liệu schema. |
| `scripts/generate_quality_baseline.py` | Tạo quality baseline machine-readable. |
| `scripts/audit_fixed_assets_cross_trace.py` | Audit chéo fixed-assets source/reference/output. |
| `scripts/build_fixed_assets_business_decision_pack.py` | Dựng gói quyết định nghiệp vụ fixed-assets. |
| `scripts/classify_fixed_assets_mismatches.py` | Phân loại mismatch fixed-assets có evidence. |
| `scripts/verify_fixed_assets_handover.py` | Kiểm tra artifact handover fixed-assets. |
| `scripts/verify_fixed_assets_policy_output.py` | Kiểm tra output theo policy fixed-assets. |

## 10. Khi cần sửa một lỗi

1. Xác định lỗi nằm ở đọc nguồn (`parsers`), kiểm tra/điều phối (`services`), schema (`db`) hay tính/ghi (`engine`).
2. Đọc docstring của module và function liên quan trước khi sửa.
3. Kiểm tra call site từ `src/universal_app.py` và `scripts/run_e2e.py` để không tạo hai luồng logic khác nhau.
4. Bổ sung test gần module bị sửa; chạy test mục tiêu rồi mới chạy profile rộng.
5. Nếu liên quan phát hành/update, đọc `docs/handover/release_update_playbook.md` trước khi build hoặc publish.
