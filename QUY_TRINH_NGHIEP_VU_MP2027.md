# QUY TRÌNH NGHIỆP VỤ MP2027

Ngày cập nhật: `2026-04-12`

Tài liệu này phản ánh trạng thái sau khi đọc lại:
- `docs/MP2027/Cải tiến nhập dữ liệu chung vào file MPnew.xlsx`
- `docs/MP2027/FORM.xlsx`
- bộ đối chiếu người dùng đã làm thật trong `docs/MP2026`

Checklist kiểm toán chi tiết theo từng sheet/dòng yêu cầu:
- `MP2027_REQUIREMENTS_AUDIT_CHECKLIST.md`

## 1. Nguyên tắc nguồn dữ liệu

- `docs/MP2027` là runtime source chuẩn cho FY2027.
- `docs/MP2027/FORM.xlsx` là layout FORM chuẩn để export.
- `docs/MP2026` là bộ đối chiếu nghiệp vụ thật của người dùng. Được phép dùng để đối chiếu mapping, đơn giá tham chiếu, cách tính, nhưng không copy row number hoặc số tiền FY2026 sang FY2027 một cách máy móc.
- Nếu FY2027 đã có đơn giá/dữ liệu thật thì luôn ưu tiên FY2027.

Lý do không copy row number từ MP2026:
- FORM MP2026 là layout cũ, ví dụ điện/nước/gas/cleaning ở các row `40/41/42/44`.
- FORM MP2027 là layout mới, code hiện export theo `44/45/46/51` cho điện/nước/gas/cleaning.

## 2. Luồng xử lý chính

1. Nạp master data từ FORM và allocation rules.
2. Parse các workbook nguồn: facility, fixed assets, IT simulation, GA/tổng vụ, manual CSV.
3. Đưa dữ liệu vào SQLite staging.
4. Allocation engine tính các dòng theo rule và headcount/event driver.
5. Export vào `内訳ﾘｽﾄ(4～3月)` của FORM.
6. Output phải giữ công thức để người dùng double-check. Nếu chỉ có giá trị nguồn cuối cùng, exporter ghi công thức hằng số dạng `=123` thay vì paste số chết.

## 3. Mapping FORM MP2027 hiện tại

| Row | Nội dung MP2027 | Trạng thái |
|---:|---|---|
| `36` | Khấu hao nhà | `=ROUND(usd*$B$2,0)` |
| `37` | Khấu hao đất | `=ROUND(usd*$B$2,0)` |
| `38` | Khấu hao thiết bị | `=ROUND(usd*$B$2,0)` nếu có fixed-assets data |
| `40` | Lãi nhà | `=ROUND(usd*$B$2,0)` |
| `41` | Lãi đất | `=ROUND(usd*$B$2,0)` |
| `42` | Lãi thiết bị | `=ROUND(usd*$B$2,0)` nếu có fixed-assets data |
| `44` | Tiền điện | công thức hằng số `=amount` vì nguồn facility chỉ có tổng tiền tháng |
| `45` | Tiền nước | công thức hằng số `=amount` vì nguồn facility chỉ có tổng tiền tháng |
| `46` | Gas | `=SUM(prev_month_headcount)*unit_price` |
| `48` | Hand wash | `=SUM(prev_month_headcount)*unit_price` |
| `49` | Toilet paper | `=SUM(prev_month_headcount)*unit_price` |
| `51` | Cleaning | `=SUM(prev_month_headcount)*unit_price` |
| `57` | Health check hàng năm | rule/headcount nếu có driver |
| `58` | Health check khi tuyển dụng | rule/event-month driver |
| `59` | Birthday | `headcount * 152000` và cộng thêm người mới nếu có driver |
| `75` | IT system cost | công thức tổng hợp component `qty*unit_usd*$B$2` |
| `97` | Sổ tay nhân viên mới | fixed row theo FORM MP2027 |
| `98` | Sổ tay công nhân mới | fixed row theo FORM MP2027 |
| `137` | Chi phí giấy tờ người biết phải | manual/special cost theo `form_row` |

## 4. Bảng đối chiếu MP2026 đã áp dụng

| Nghiệp vụ | MP2026 reference | MP2027 cách dùng |
|---|---|---|
| Moon cake / 月餅 | FORM MP2026 row `71`, `56,000/人` | Fallback đơn giá `56,000` nếu rule FY2027 đang `0`. |
| Sports day / 運動会 | FORM MP2026 row `67`, `107,000/人` | Fallback đơn giá `107,000` nếu rule FY2027 đang `0`. |
| Passport | FORM MP2026 row `122/123` | Đối chiếu loại chi phí; FY2027 cần nhập event vào `special_costs_manual.csv`. |
| GPLD health-check / work permit | FORM MP2026 row `116/119/120/121` | Đối chiếu loại chi phí; FY2027 cần nhập event vào `special_costs_manual.csv`. |
| VISA | FORM MP2026 row `137/142/152` | Đối chiếu loại chi phí; FY2027 row có thể là `158` nếu travel/VISA, hoặc `137-147` nếu giấy tờ người biết phải. |
| Gas/Hand wash/Toilet paper/Cleaning | FORM MP2026 row `42/93/94/44` | MP2027 row mới là `46/48/49/51`. |

## 5. Trạng thái hiện tại

Đã xong:
- Dùng `docs/MP2027` làm source mặc định.
- Đọc exchange rate từ FORM `B2`.
- Load được allocation rules, bao gồm unit price dạng `145$`.
- Fallback đơn giá MP2026 cho `Moon cake` và `Sports day` khi FY2027 đang `0`.
- Ghi fixed rows MP2027 đúng layout mới.
- Ghi output ở dạng công thức để double-check.
- Chặn auto-allocation sai cho NNN/VISA/GPLD/Passport.
- Có parser `manual_special_costs.csv` để ghi vào row FORM rõ ràng.
- Có parser `Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx` vào row `137`, giữ công thức nguồn nếu có.
- Có parser `Sinh nhật MP FY2027.xlsx` vào row `59`, ghi công thức `=count*152000`.
- Có panel `Nhập sự kiện thiếu dữ liệu` và CSV `event_drivers_manual.csv` để người dùng cung cấp các count/amount không thể suy luận. Pipeline không tự bịa số; nếu dòng hợp lệ thì ghi công thức `=count*unit_price`.
- Có test bảo vệ mapping fixed rows và công thức output.

Chưa được gọi là 100%:
- Nếu có Passport/VISA/GPLD/NNN phải vào row khác `137`, cần thêm mapping `form_row` riêng hoặc nhập qua `special_costs_manual.csv`.
- Cần xác nhận `Sinh nhật MP FY2027.xlsx` đã bao gồm người mới; nếu người mới nằm ở nguồn khác thì cần thêm driver cộng thêm riêng.
- `docs/MP2027/headcount_manual.csv` chưa có data cho `1412000089`.
- GUI đã có headcount staff/worker 12 tháng, Nam/Nữ tháng 12, và panel manual event driver cho các sự kiện như JP/VN bus, tháng 3 FY cũ, tháng 4/5/6/10. Vẫn cần người dùng nhập/chốt số liệu thật cho các sự kiện này.
- Cần chốt row đích cho `Company anniversary` và `Quà tặng cho CNV không thể tham gia du lịch`.
- Một số nội dung trong `Hạng mục cần cải tiến` chỉ nằm trong ảnh/annotation, cần map thủ công nếu muốn xác nhận 100%.

## 6. File nên đọc khi tiếp tục

1. `TODO_MP2027_OPEN_ITEMS.md`
2. `docs/MP2027/Cải tiến nhập dữ liệu chung vào file MPnew.xlsx`
3. `docs/MP2027/FORM.xlsx`
4. `docs/MP2026/FORM.xlsx`
5. `src/engine/hub_builder.py`
6. `src/db/loader.py`
