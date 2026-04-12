# MP2027 Manager - Walkthrough và trạng thái hiện tại

Ngày cập nhật: `2026-04-12`

Tài liệu này tóm tắt cách đọc hệ thống ở trạng thái hiện tại sau khi đã đối chiếu FORM MP2027, dữ liệu tham chiếu MP2026, parser mới và dashboard audit. Đây không phải tài liệu marketing; mục tiêu là giúp người đọc biết chương trình đang làm được gì, còn thiếu dữ liệu gì và cần kiểm chứng ở đâu.

## 1. Luồng sử dụng chính

1. Người dùng mở GUI trong `src/universal_app.py`.
2. Chương trình đọc FORM runtime tại `docs/MP2027/FORM.xlsx`.
3. Pipeline nạp dữ liệu nguồn trong `docs/MP2027`, bao gồm Facility, Fixed Assets, IT simulation, GA unit price, NNN paperwork, Birthday và CSV nhập tay.
4. Allocation engine tạo dữ liệu tính toán vào `mp2027.db`.
5. Export ghi ra workbook theo từng Cost Center trong `OUTPUT_FY2027`.
6. Audit dashboard và audit report hiển thị trạng thái xanh/vàng/đỏ, dữ liệu thiếu và preview công thức.

## 2. FORM runtime

- FORM mới là `docs/MP2027/FORM.xlsx`.
- `docs/MP2027/FORM_old.xlsx` chỉ dùng để đối chiếu, không dùng runtime.
- Output ghi vào hub sheet `内訳ﾘｽﾄ(4～3月)` hoặc sheet tương đương do helper tìm được.

## 3. Những phần đã có cơ chế tự động

- Mapping fixed rows theo FORM MP2027 cho các dòng quan trọng như `36/37/38`, `40/41/42`, `44/45`, `57/58/59`, `75`, `97/98`, `137`.
- Parser NNN paperwork ghi vào row `137` và giữ công thức breakdown nếu file nguồn có công thức.
- Parser Birthday ghi row `59` với công thức dạng `=count*152000`.
- Manual event driver cho phép người dùng nhập sự kiện không thể suy luận qua `docs/MP2027/event_drivers_manual.csv` hoặc panel GUI.
- MP2026 chỉ được dùng làm đơn giá tham chiếu cho Moon cake và Sports day khi FY2027 đang trống hoặc bằng `0`.
- Output ưu tiên giữ công thức để người dùng có thể double-check sau khi export.

## 4. Những phần không được tự đoán

Chương trình không tự bịa số cho các dữ liệu không thể suy luận từ workbook nguồn, ví dụ:

- Số người bus JP/VN theo từng sự kiện.
- Quà không đi du lịch.
- My Episode.
- Quà kỷ niệm 10 năm hoặc tiệc kỷ niệm 10 năm.
- Company anniversary.
- VISA/Passport/GPLD/NNN nếu nghiệp vụ yêu cầu row khác mapping hiện tại.

Các dữ liệu này phải được người dùng nhập/chốt trước khi coi output là hoàn chỉnh.

## 5. Audit dashboard

Dashboard dùng ba trạng thái:

- `GREEN`: có dữ liệu cơ bản và không có cảnh báo nền tảng.
- `YELLOW`: thiếu dữ liệu cần người dùng xem/chốt, ví dụ thiếu manual headcount hoặc thiếu manual event driver theo Cost Center.
- `RED`: không có dữ liệu tính toán cho Cost Center đó.

Dashboard chỉ xác nhận mức độ sẵn sàng của dữ liệu, không thay thế việc người dùng nghiệp vụ kiểm tra lại workbook output.

## 6. Kiểm chứng nên chạy

```powershell
py -m py_compile src\universal_app.py src\audit\pipeline_audit.py scripts\run_e2e.py
py -m unittest tests.test_src_v2_logic tests.test_posting_month_logic tests.test_headcount_and_export
py scripts\run_e2e.py --fy 2027 --template docs\MP2027\FORM.xlsx --source docs\MP2027 --target-cc 1412000006
```

Sau khi chạy E2E, kiểm tra các file:

- `OUTPUT_FY2027/MP_CC_1412000006.xlsx`
- `OUTPUT_FY2027/MP2027_AUDIT_REPORT.md`
- `OUTPUT_FY2027/MP2027_MISSING_INPUTS.csv`

## 7. Trạng thái trung thực hiện tại

Trạng thái nên mô tả là:

- Pipeline E2E đã chạy được.
- Fixed-row mapping và parser mới đã có test bảo vệ.
- Dashboard audit đã có nền tảng xanh/vàng/đỏ và preview công thức.
- Các dữ liệu sự kiện không thể suy luận vẫn cần người dùng nhập/chốt.
- Báo cáo audit cần được dùng như bước kiểm soát bắt buộc trước khi bàn giao output.
