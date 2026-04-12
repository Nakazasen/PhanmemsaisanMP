# MP2027 Manager

MP2027 Manager là chương trình hỗ trợ lập ngân sách MP FY2027 theo từng CC. Chương trình nạp dữ liệu từ bộ tệp trong `docs/MP2027`, tính toán, xuất tệp Excel theo FORM mới và tạo báo cáo kiểm toán để người dùng biết phần nào đã đủ dữ liệu, phần nào còn cần nhập/chốt.

Nguyên tắc quan trọng nhất: chương trình không tự bịa số. Những khoản không thể suy luận từ tệp nguồn, ví dụ xe bus JP/VN, quà không đi du lịch, My Episode, kỷ niệm 10 năm, kỷ niệm công ty, hoặc VISA/Passport/GPLD/NNN cần dòng FORM khác, phải được người dùng nhập/chốt trước khi tin kết quả.

## Cách chạy bằng giao diện

1. Chạy `run_MP2027.bat` hoặc `py src/universal_app.py`.
2. Kiểm tra `Tệp mẫu FORM` đang trỏ tới `docs/MP2027/FORM.xlsx`.
3. Kiểm tra `Thư mục nguồn` đang trỏ tới `docs/MP2027`.
4. Nếu cần, bấm `Nhập nhân sự thủ công` để nhập staff/worker 12 tháng và Nam/Nữ tháng 12.
5. Nếu Dashboard hoặc nghiệp vụ báo thiếu dữ liệu sự kiện, bấm `Nhập sự kiện thiếu dữ liệu`.
6. Bấm `CHẠY TÍNH TOÁN`.
7. Mở `Dashboard kiểm toán` để kiểm tra đèn XANH/VÀNG/ĐỎ, danh sách việc cần chốt và công thức trong tệp kết quả.

## Cách đọc Dashboard

- XANH: CC đã có dữ liệu nền tảng và chưa có cảnh báo cơ bản.
- VÀNG: CC có dữ liệu nhưng còn việc cần người dùng xem/chốt.
- ĐỎ: CC chưa có dữ liệu tính toán sau lần chạy gần nhất.

Nếu thấy VÀNG hoặc ĐỎ, hãy chọn dòng CC đó, đọc cột `Lý do`, xem bảng `Việc cần người dùng chốt`, rồi nhập bổ sung nếu cần.

## File đầu vào quan trọng

- `docs/MP2027/FORM.xlsx`: FORM runtime hiện tại.
- `docs/MP2027/headcount_manual.csv`: nhân sự nhập tay theo CC/tháng.
- `docs/MP2027/event_drivers_manual.csv`: sự kiện hoặc khoản tiền không thể tự suy luận.
- `docs/MP2027/special_costs_manual.csv`: chi phí đặc biệt cần nhập trực tiếp theo dòng FORM.

`docs/MP2027/FORM_old.xlsx` chỉ dùng để đối chiếu, không dùng để chạy.

## File kết quả

Sau khi chạy, kiểm tra trong `OUTPUT_FY2027`:

- `MP_CC_<mã CC>.xlsx`: tệp kết quả theo CC.
- `MP2027_AUDIT_REPORT.md`: báo cáo kiểm toán.
- `MP2027_MISSING_INPUTS.csv`: danh sách dữ liệu cần người dùng xem/chốt.

## Lệnh kiểm chứng cho người bảo trì

```powershell
py -m py_compile src\universal_app.py src\audit\pipeline_audit.py scripts\run_e2e.py
py -m unittest tests.test_src_v2_logic tests.test_posting_month_logic tests.test_headcount_and_export
py scripts\run_e2e.py --fy 2027 --template docs\MP2027\FORM.xlsx --source docs\MP2027 --target-cc 1412000006
```
