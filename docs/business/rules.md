# Business Rules - MP2027 Manager

Ngày cập nhật: `2026-04-12`

Tài liệu này tách bạch giữa quy tắc nghiệp vụ cần tôn trọng và trạng thái implementation hiện tại. Nếu cần checklist chi tiết theo workbook yêu cầu, đọc `MP2027_REQUIREMENTS_AUDIT_CHECKLIST.md`.

## 1. Năm tài chính

- Kỳ tài chính bắt đầu từ tháng `4` và kết thúc vào tháng `3` năm sau.
- Mọi dữ liệu theo tháng phải được quy về period `YYYYMM`.
- Runtime FY2027 dùng chuỗi tháng từ `202704` đến `202803`.

## 2. FORM runtime

- FORM runtime là `docs/MP2027/FORM.xlsx`.
- `docs/MP2027/FORM_old.xlsx` chỉ dùng để đối chiếu, không dùng khi chạy pipeline.
- Chương trình chỉ ghi vào hub sheet `内訳ﾘｽﾄ(4～3月)` hoặc sheet tương đương do helper tìm được.

## 3. Mapping Cost Center và account

- Account đích phải được chọn theo nhóm Cost Center nếu rule có mã cho `製造/一般/販売`.
- Không được tự đổi account code nếu workbook rule hoặc FORM chưa xác nhận.
- Các trường `cc_code`, `account_code`, `form_row` là dữ liệu kỹ thuật, không được Việt hóa.

## 4. Fixed rows quan trọng

- `36/37/38`: khấu hao nhà/đất/thiết bị.
- `40/41/42`: lãi nhà/đất/thiết bị.
- `44/45`: điện/nước.
- `46/48/49/51`: gas, hand wash, toilet paper, cleaning.
- `57/58/59`: health-check hàng năm, health-check tuyển dụng, birthday.
- `75`: IT system cost.
- `97/98`: sổ tay nhân viên/công nhân mới.
- `137`: chi phí giấy tờ NNN theo workbook yêu cầu hiện tại.

## 5. Công thức trong output

- Không paste số chết nếu có thể để công thức.
- Dữ liệu nguồn chỉ có tổng tiền sẽ ghi dạng `=amount`.
- Birthday ghi dạng `=count*152000`.
- IT system cost ghi dạng `=ROUND((...)*$B$2,0)`.
- Manual event driver ghi dạng `=count*unit_price` hoặc `=amount_vnd`.

## 6. Dữ liệu không thể suy luận

Những dữ liệu như số người đi bus JP/VN, quà không đi du lịch, My Episode, kỷ niệm 10 năm, company anniversary hoặc VISA/Passport cần row khác `137` không được tự đoán.

Người dùng nhập các dữ liệu này qua:

- `docs/MP2027/event_drivers_manual.csv`
- Panel GUI `Nhập sự kiện thiếu dữ liệu`

## 7. Audit và missing inputs

Sau mỗi lần E2E, pipeline sinh:

- `OUTPUT_FY2027/MP2027_AUDIT_REPORT.md`
- `OUTPUT_FY2027/MP2027_MISSING_INPUTS.csv`

Hai file này là nơi người dùng nghiệp vụ xem phần nào đã được nạp, phần nào còn cần chốt, và phần nào chương trình không tự suy luận.
