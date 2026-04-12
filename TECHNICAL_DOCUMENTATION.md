# TECHNICAL DOCUMENTATION - MP2027 Manager

Ngày cập nhật: `2026-04-12`

Tài liệu này mô tả hệ thống ở góc nhìn kỹ thuật và chỉ ra các tài liệu hiện hành cần đọc trước khi bảo trì. Các ghi chú cũ từ tháng `2026-03` đã được rút gọn vì không còn phản ánh đúng trạng thái hiện tại sau các bản sửa MP2027.

## 1. Tài liệu hiện hành

- `QUY_TRINH_NGHIEP_VU_MP2027.md`: quy trình nghiệp vụ và mapping FORM hiện tại.
- `TODO_MP2027_OPEN_ITEMS.md`: các việc còn mở và trạng thái kiểm chứng.
- `MP2027_REQUIREMENTS_AUDIT_CHECKLIST.md`: checklist audit theo từng sheet/dòng trong workbook yêu cầu.
- `OUTPUT_FY2027/MP2027_AUDIT_REPORT.md`: báo cáo audit sinh ra sau lần chạy E2E gần nhất.
- `OUTPUT_FY2027/MP2027_MISSING_INPUTS.csv`: danh sách dữ liệu cần người dùng xem/chốt.

## 2. Kiến trúc tổng quan

Hệ thống gồm các lớp chính:

- GUI: `src/universal_app.py`.
- Orchestration: `scripts/run_e2e.py`.
- Parser nguồn: `src/parsers/`.
- Logic tính và export: `src/engine/allocator.py`, `src/engine/hub_builder.py`.
- Audit report: `src/audit/pipeline_audit.py`.
- SQLite staging: `mp2027.db`.

## 3. Luồng chạy chính

1. Khởi tạo database và tham số năm tài chính.
2. Load master data từ `docs/MP2027/FORM.xlsx`.
3. Parse các nguồn Facility, GA, IT, Fixed Assets, NNN paperwork, Birthday và CSV nhập tay.
4. Chạy allocation engine.
5. Export từng Cost Center vào FORM MP2027.
6. Sinh audit report và missing-input CSV.

## 4. Nguyên tắc kỹ thuật quan trọng

- Runtime FORM là `docs/MP2027/FORM.xlsx`.
- `docs/MP2027/FORM_old.xlsx` chỉ dùng để đối chiếu, không dùng runtime.
- Không copy số FY2026 sang FY2027 nếu không có xác nhận nghiệp vụ.
- Nếu thiếu dữ liệu không thể suy luận, chương trình không tự bịa số; người dùng nhập qua `event_drivers_manual.csv`.
- Output cố gắng giữ công thức để người dùng double-check, ví dụ `=amount`, `=count*unit_price`, hoặc `=ROUND(...*$B$2,0)`.

## 5. Kiểm chứng nên chạy

```powershell
py -m py_compile src\universal_app.py src\audit\pipeline_audit.py scripts\run_e2e.py
py -m unittest tests.test_src_v2_logic tests.test_posting_month_logic tests.test_headcount_and_export
py scripts\run_e2e.py --fy 2027 --template docs\MP2027\FORM.xlsx --source docs\MP2027 --target-cc 1412000006
```

## 6. Khi cập nhật tài liệu

Chỉ đánh dấu một mục là `verified` khi có đủ:

- Command/test đã chạy.
- Workbook hoặc nguồn dữ liệu đã đối chiếu.
- Bằng chứng trong DB, output Excel hoặc audit report.

Nếu thiếu một trong các bằng chứng trên, chỉ nên ghi `implemented`, `partially verified` hoặc `pending validation`.
