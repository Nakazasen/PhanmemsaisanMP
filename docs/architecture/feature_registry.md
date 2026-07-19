# Danh mục tính năng MP2027

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
| F-011 | Gói nội dung có chữ ký | `src/services/content_packs.py` | Test gói nội dung/an toàn | Cao |
| F-012 | Cập nhật ứng dụng có chữ ký | `src/services/app_updates.py` | Test cập nhật/an toàn | Nghiêm trọng |
| F-013 | Gói portable onedir | `MP2027_Portable.spec`, `scripts/package_app.py` | Test đóng gói + sức khỏe EXE | Nghiêm trọng |
| F-014 | Trình khởi chạy ổn định/bộ cài ban đầu | `MP2027_Manager.spec`, `scripts/update_launcher.py`, `installer/` | Hợp đồng đóng gói + diễn tập Windows sạch | Nghiêm trọng |

## Quy tắc cho các thay đổi sau này

1. Thay đổi công thức hoặc driver phải cập nhật test đặc trưng hóa liên quan và bằng chứng quy tắc nghiệp vụ, không chỉ test giao diện.
2. Thay đổi schema phải bổ sung migration và sinh lại `docs/database/schema_catalog.json` cùng `docs/database/data_dictionary.md`.
3. Thay đổi đường dẫn hoặc đóng gói phải chạy kiểm tra sức khỏe source và EXE đã đóng gói.
4. Bản cập nhật phát hành phải dùng `.mpupdate` có chữ ký; không phân phối các mô-đun Python rời cho người dùng.
5. Thay đổi giá/ánh xạ riêng của bộ phận chỉ được đưa vào gói nội dung có chữ ký sau khi xác minh driver và hợp đồng tài khoản mà bộ máy hỗ trợ.

## Danh mục máy đọc được

Danh mục sinh tự động ở cấp mô-đun là `reports/quality_baseline.json`. Sinh lại bằng:

```powershell
py scripts/generate_quality_baseline.py
```
