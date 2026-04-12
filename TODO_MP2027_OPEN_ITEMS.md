# TODO MP2027 Open Items

Ngày cập nhật: `2026-04-12`

Checklist kiểm toán chi tiết theo workbook yêu cầu:
- `MP2027_REQUIREMENTS_AUDIT_CHECKLIST.md`

Quy ước:
- `P1`: ảnh hưởng trực tiếp đến output nghiệp vụ.
- `P2`: xác nhận/mở rộng.
- `P3`: tài liệu, package, bàn giao.

## 1. Đã xong sau audit MP2026/MP2027

- [x] `P1` Dùng `docs/MP2027/FORM.xlsx` làm layout runtime chuẩn. Không copy row number từ `docs/MP2026/FORM.xlsx` vì FORM MP2026 là layout cũ.
- [x] `P1` Sửa fixed-row mapping theo FORM MP2027:
  - `36/37/38` = khấu hao nhà/đất/thiết bị
  - `40/41/42` = lãi nhà/đất/thiết bị
  - `44/45` = điện/nước
  - `46` = gas
  - `48/49/51` = hand wash/toilet paper/cleaning
  - `57/58/59` = health-check yearly / hiring health-check / birthday
  - `75` = IT system cost
  - `97/98` = sổ tay nhân viên/công nhân mới
  - `137` = chi phí giấy tờ người biết phải
- [x] `P1` Output các giá trị ghi ra FORM được giữ ở dạng công thức để người dùng double-check. Nếu không có driver chi tiết thì ghi công thức hằng số dạng `=123` thay vì số chết `123`.
- [x] `P1` Row `75` IT system cost đã ghi công thức tổng hợp từ component, ví dụ `=ROUND((qty*unit+...)*$B$2,0)`.
- [x] `P1` Recurring admin dùng công thức theo headcount tháng trước, riêng tháng 4 dùng tháng 4:
  - `46` Gas
  - `48` Hand wash
  - `49` Toilet paper
  - `51` Cleaning
- [x] `P1` Dùng MP2026 làm reference để bổ sung đơn giá khi rule FY2027 đang `0`:
  - `Moon cake / 月餅` = `56,000` VND/người theo `docs/MP2026/FORM.xlsx` row cũ `71`
  - `Sports day / 運動会` = `107,000` VND/người theo `docs/MP2026/FORM.xlsx` row cũ `67`
  - Lưu ý: chỉ dùng fallback khi rule FY2027 có `unit_price = 0`; nếu FY2027 có đơn giá thật thì ưu tiên FY2027.
- [x] `P1` Đã có parser `special_costs_manual.csv` và cơ chế ghi `form_row` rõ ràng vào FORM.
- [x] `P1` Đã chắn auto-allocation sai cho NNN/VISA/GPLD/Passport theo headcount.
- [x] `P1` Thêm parser trực tiếp cho `docs/MP2027/Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx`.
  - E2E hiện nạp `54` record, `0` error.
  - Row `137` giữ công thức nguồn nếu ô nguồn là công thức, ví dụ `=1820000+130000+50000`.
- [x] `P1` Thêm parser trực tiếp cho `docs/MP2027/Sinh nhật MP FY2027.xlsx`.
  - E2E hiện nạp `556` record, `0` error.
  - Row `59` ghi công thức dạng `=count*152000`.
- [x] `P1` Thêm đường nhập dữ liệu sự kiện không thể suy luận.
  - GUI có nút `Nhập sự kiện thiếu dữ liệu`.
  - CSV runtime: `docs/MP2027/event_drivers_manual.csv`.
  - Pipeline doc `cc_code, period, event_name, count, unit_price, amount_vnd, account_code, form_row, description`.
  - Output giữ công thức dạng `=count*unit_price`; nếu không có `form_row` thì append xuống vùng `200+`.
- [x] `P2` Đã thêm test bảo vệ mapping các row: `36/37/38/40/41/42/44/45/46/48/49/51/57/58/59/75/97/98/137`.

## 2. Bảng đối chiếu MP2026 -> MP2027

MP2026 là dữ liệu người dùng đã làm thật, dùng để đối chiếu nghiệp vụ; MP2027 mới là layout runtime chuẩn.

| Nghiệp vụ | MP2026 FORM row tham chiếu | MP2027 FORM row đúng hiện tại | Ghi chú |
|---|---:|---:|---|
| Passport | `122/123` | `137-147` nhóm `5005246286` | Cần dữ liệu FY2027 theo event/người/tháng để nạp vào `special_costs_manual.csv`. |
| GPLD / health-check khi xin GPLD | `116/119` | `137-147` nhóm `5005246286` | Không auto tính theo headcount. |
| VISA expense | `137/142/152` | `158` hoặc row travel tương ứng nếu là đi công tác; `137-147` nếu là giấy tờ người biết phải | Cần người dùng chốt loại chi phí/row đích khi lập FY2027. |
| NNN paperwork tổng hợp | nhóm `113-123`, `137/142/152` | `137-147`, và `158` nếu là VISA travel | Có engine `manual_special_costs` để ghi đúng `form_row`. |
| Moon cake / 月餅 | `71`, đơn giá `56,000` | fixed-row matcher hiện tại theo FORM MP2027 | Đã fallback đơn giá từ MP2026 nếu FY2027 = 0. |
| Sports day / 運動会 | `67`, đơn giá `107,000` | fixed-row matcher hiện tại theo FORM MP2027 | Đã fallback đơn giá từ MP2026 nếu FY2027 = 0. |
| Hand wash / Toilet paper / Cleaning / Gas | `93/94/44/42` trong MP2026 | `48/49/51/46` trong MP2027 | Layout đã đổi, code đã sửa. |

## 3. P1 còn mở thật sự

- [ ] `P1` Nếu có chi phí Passport/VISA/GPLD/NNN phải vào row khác `137`, bổ sung mapping `form_row` riêng.
  - Parser NNN workbook hiện đưa workbook `Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx` vào row `137` theo sheet yêu cầu.
  - `special_costs_manual.csv` vẫn giữ làm đường override thủ công cho các row khác nếu cần.
- [ ] `P1` Xác nhận birthday workbook đã bao gồm người mới theo đúng logic người dùng.
  - Parser birthday hiện đọc count theo workbook và ghi `=count*152000`.
  - Nếu người mới nằm ở nguồn khác, cần cộng thêm driver new-hire riêng.
- [ ] `P1` Bổ sung/cập nhật headcount và event driver FY2027.
  - `docs/MP2027/headcount_manual.csv` hiện có data cho `1412000004`, `1412000006`, `1412000025`, chưa có `1412000089`.
  - Workbook yêu cầu thêm các input riêng: số người JP/VN xe bus, tháng 3 FY cũ, tháng 4/5/6/10 theo sự kiện, tháng 12 Nam/Nữ.
  - GUI đã có panel nhập sự kiện thiếu dữ liệu; cần người dùng nhập count/account/row cho các trường hợp chưa có nguồn máy đọc.
- [ ] `P1` Chốt row đích cho `Company anniversary` trong FORM MP2027.
- [ ] `P1` Chốt row đích cho `Quà tặng cho CNV không thể tham gia du lịch`.
- [ ] `P1` Đọc/đối chiếu thủ công 2 nội dung chỉ nằm trong ảnh ở sheet `Hạng mục cần cải tiến`:
  - `Không cần điền 2 dữ liệu dưới vào file`
  - `Dẫn các cột dữ liệu về đúng cột chỉ mũi tên`

## 4. P2 còn mở

- [ ] `P2` Nếu người dùng muốn IT bung theo từng hệ thống thay vì row tổng `75`, cần cung cấp map row đích rõ ràng trên FORM.
- [ ] `P2` Nếu cần "bôi lại đúng mẫu", cần chỉ rõ những ô/row nào phải repaint; hiện exporter ưu tiên giữ style FORM và chỉ ghi vào row được quản lý.

## 5. Kiểm chứng

- [x] `P2` Unit test mới nhất: `py -m unittest tests.test_src_v2_logic tests.test_posting_month_logic tests.test_headcount_and_export`
- [x] `P2` E2E đã chạy: `py scripts\run_e2e.py --fy 2027 --template docs\MP2027\FORM.xlsx --source docs\MP2027 --target-cc 1412000006`
- [x] `P2` E2E đã chạy: `py scripts\run_e2e.py --fy 2027 --template docs\MP2027\FORM.xlsx --source docs\MP2027 --target-cc 1412000089`

## 6. Lưu ý bàn giao

- Working output/db có thể thay đổi khi chạy E2E:
  - `OUTPUT_FY2027/MP_CC_1412000006.xlsx`
  - `mp2027.db`
- Khi bàn giao, nếu cần file output mới cho tất cả CC thì chạy lại batch sau khi dữ liệu FY2027 được chốt.
