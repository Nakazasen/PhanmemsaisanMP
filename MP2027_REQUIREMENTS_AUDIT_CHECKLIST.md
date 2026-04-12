# MP2027 Requirements Audit Checklist

Ngày audit: `2026-04-12`

Workbook yêu cầu: `docs/MP2027/Cải tiến nhập dữ liệu chung vào file MPnew.xlsx`

Trạng thái tổng quan:
- Mức đáp ứng kỹ thuật hiện tại: `~85% / 100%`
- Mức sẵn sàng cho người dùng bấm chạy ra đầy đủ số nghiệp vụ: `~78-82% / 100%`
- Lý do không chấm cao hơn: đã có đường nhập manual event driver cho dữ liệu không thể suy luận, nhưng vẫn cần người dùng nhập/chốt các count, row/account cho các sự kiện chưa có nguồn máy đọc, và còn annotation bằng ảnh/chưa có mapping text 1-1.

Quy ước trạng thái:
- `Done`: đã có code/export/test hoặc đã được xác minh trên E2E.
- `Partial`: đã có một phần engine/mapping nhưng chưa đủ hết nghiệp vụ.
- `Missing data`: engine có đường nhập nhưng thiếu dữ liệu FY2027 để ra số.
- `Need manual mapping`: workbook/ảnh/annotation chưa đủ thông tin text để map tự động an toàn.

## 1. Sheet `Sheet1`

| Dòng | Yêu cầu | Trạng thái | Đối ứng hiện tại | Cần làm tiếp |
|---:|---|---|---|---|
| `50-55` | Nhập dữ liệu từ file nguồn vào ô cần điền trong file MP, theo công thức hoặc paste số. | `Partial` | Pipeline đã đọc nhiều nguồn và export vào FORM. Output đã đổi số trực tiếp thành công thức hằng số dạng `=123` để double-check. Đã thêm parser NNN workbook và Birthday workbook. | Cần đóng tiếp một số driver hành chính/sự kiện và annotation bằng ảnh. |

## 2. Sheet `Hạng mục cần cải tiến`

| Dòng | Yêu cầu | Trạng thái | Đối ứng hiện tại | Cần làm tiếp |
|---:|---|---|---|---|
| `2` | Không cần điền 2 dữ liệu dưới vào file. | `Need manual mapping` | Chưa xác định được 2 dữ liệu nào nếu chỉ đọc text cell; khả năng nằm trong ảnh/vị trí trên sheet. | Cần xem workbook bằng Excel/ảnh gốc và đánh dấu cell/row cụ thể cần bỏ qua. |
| `16` | Dời các cột dữ liệu về đúng cột chỉ mũi tên. | `Need manual mapping` | Đã fix nhiều row dịch FORM MP2027, nhưng chưa có audit cell-by-cell cho yêu cầu "mũi tên". | Cần lập bảng source-column -> FORM-column từ ảnh/annotation. |
| `37` | Bôi lại đúng màu, đúng định dạng như FORM vốn có. | `Partial` | Exporter ghi vào template FORM và giữ style sẵn có ở các row template; không có bước repaint riêng. | Cần test/so sánh style nếu người dùng yêu cầu style 100%. |
| `44` | Để lại tất cả công thức tính. | `Partial` | Đã đổi numeric export thành công thức hằng số; IT/FX/headcount là công thức thật. | Cần tiếp tục tránh paste value cho các parser mới; cần reconcile công thức IT nếu lệch với sheet tổng. |
| `70`, `117-139` | Sai code/công thức chi phí hệ thống; cần lấy công thức đúng và nhập row 75. | `Done` | Row `75` dùng account system cost và công thức `=ROUND((component...)*$B$2,0)`. Test bảo vệ row 75. | Nếu cần khớp tuyệt đối với sheet tổng khi lệch vài dòng do tỷ giá thì cần thêm reconcile. |
| `90-91` | Nhập số người 12 tháng; tháng 12 tách Nam/Nữ; label tháng nên hiện Thị "Tháng 4..." thay vì `202704`. | `Partial` | `headcount_manual.csv` hỗ trợ staff/worker theo từng period và male/female. | GUI/input chưa đầy đủ UX theo yêu cầu; label tháng cần audit trong GUI. |
| `109-150` | Bổ sung chi phí phân bổ từ hành chính và chi phí làm giấy tờ NNN. | `Partial` | Đã có nhiều fixed-row mapping, manual special parser, parser NNN workbook, parser Birthday workbook, và fallback unit price MP2026 cho Moon cake/Sports day. | Cần các driver sự kiện riêng và audit account theo 3 nhóm cost center. |
| `156-169` | Thay input số người bằng driver riêng: JP/VN xe bus, tháng 3 FY cũ, tháng 4/5/6/10, tháng 12 Nam/Nữ. | `Partial` | Có staff/worker 12 tháng, Nam/Nữ, và panel `Nhập sự kiện thiếu dữ liệu` ghi `event_drivers_manual.csv` cho driver riêng. | Cần người dùng nhập/chốt count, account, row cho từng sự kiện chưa có nguồn. |
| `171` | Xóa nội dung dưới đây cho không cần thiết. | `Need manual mapping` | Chưa có cell/row dịch cụ thể để xóa/bỏ qua. | Cần xác định vùng "dưới đây" áp dụng cho file nào/sheet nào. |

## 3. Sheet `Chi phí hệ thống`

| Dòng | Yêu cầu | Trạng thái | Đối ứng hiện tại | Cần làm tiếp |
|---:|---|---|---|---|
| `42-47` | Đọc từng sheet chi tiết, công thức `số người * đơn giá`. | `Done` | Parser IT đọc component và exporter tạo công thức component theo tháng. | Cần thêm reconcile nếu muốn ép khớp sheet tổng từng dòng. |
| `83-89` | Tổng chi phí hệ thống: `ROUND(sum component * tỷ giá B2,0)` và nhập row `75`, `F75:Q75`. | `Done` | Row `75` đã ghi công thức tổng hợp, total row R75 = `SUM(F75:Q75)`. | Không còn việc lớn, trừ reconcile lệch 1 vài dòng. |
| `93-97` | Filter từng code phòng, so sánh tổng với sheet tổng, xác nhận số người từng tháng. | `Partial` | Code filter/group theo CC và lấy component; không có bước UI xác nhận số người từng tháng. | Cần thêm audit/reconcile report nếu người dùng cần xác nhận trước export. |

## 4. Sheet `Chi phí khấu hao, lãi nhà đất`

| Dòng | Yêu cầu | Trạng thái | Đối ứng hiện tại | Cần làm tiếp |
|---:|---|---|---|---|
| `62-68` | Khấu hao nhà row `36`, đất row `37`, `F:Q`, công thức `ROUND(usd*B2,0)`. | `Done` | Fixed mapping row `36/37`; exporter ghi công thức FX. | Không. |
| `95-101` | Lãi nhà row `40`, lãi đất row `41`, `F:Q`, công thức `ROUND(usd*B2,0)`. | `Done` | Fixed mapping row `40/41`; exporter ghi công thức FX. | Không. |
| `127-131` | Điền row `44`, nước row `45`, copy/paste dữ liệu `F:Q`. | `Done` | Fixed mapping row `44/45`; ghi công thức hằng số `=amount` từ facility. | Nếu có nguồn sản lượng/đơn giá thì có thể đổi thành công thức driver thật, hiện nguồn chỉ có tổng tiền. |

## 5. Sheet `Chi phí tài sản cố định`

| Dòng | Yêu cầu | Trạng thái | Đối ứng hiện tại | Cần làm tiếp |
|---:|---|---|---|---|
| `41-46` | Fixed assets: row `38` khấu hao, row `42` lãi, công thức `ROUND(usd*B2,0)`. | `Done` | Parser fixed assets có schedule depreciation/interest; fixed mapping row `38/42`; test có bảo vệ. | Không. |
| `47-66` | Logic tháng khấu hao cuối cùng: trước tháng cuối ghi monthly, tháng cuối ghi last-month amount, sau đó không điền; interest tương tự. | `Done` | `expand_depreciation_schedule` và `expand_interest_schedule` đã xử lý last month. | Cần thêm fixture E2E nếu muốn bảo vệ thêm bằng file nguồn thật. |

## 6. Sheet `Chi phí làm giấy tờ cho NNN`

| Dòng | Yêu cầu | Trạng thái | Đối ứng hiện tại | Cần làm tiếp |
|---:|---|---|---|---|
| `18-24` | Filter code tài khoản/cost center, lấy số tiền theo tháng, nhập row `137`, `F137:Q137`. | `Done` | Parser `nnn_paperwork` đã đọc `docs/MP2027/Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx` và ghi row `137`. Nếu ô nguồn là công thức, output giữ breakdown công thức, ví dụ `=1820000+130000+50000`. | Nếu có loại VISA/Passport cần row khác row `137`, cần thêm mapping `form_row` riêng. |

## 7. Sheet `Chi phí sinh nhật`

| Dòng | Yêu cầu | Trạng thái | Đối ứng hiện tại | Cần làm tiếp |
|---:|---|---|---|---|
| `20-25` | Lấy số người theo tháng, filter rule `誕生日会`, nhập row `59`, `F59:Q59`, công thức `số người * đơn giá`. | `Done` | Parser `birthday_workbook` đã đọc `docs/MP2027/Sinh nhật MP FY2027.xlsx`, nhận đơn giá `152000`, và output row `59` dạng `=count*152000`. | Cần xác nhận workbook birthday đã bao gồm người mới theo đúng logic người dùng. |
| `46-48` | Nếu tháng đó có người mới thì cộng thêm số người mới vào birthday count. | `Partial` | Event delta logic tồn tại trong allocator cho rule event-month/next-month, nhưng chưa được nối trực tiếp với birthday workbook và driver người mới. | Cần thêm driver birthday_count + new_hire_count theo CC/tháng, hoặc parser workbook birthday nếu file đã có đủ. |

## 8. Sheet `Chi phí phân bổ từ hành chính`

| Dòng | Yêu cầu | Trạng thái | Đối ứng hiện tại | Cần làm tiếp |
|---:|---|---|---|---|
| `31-34` | Gas/handwash/toilet/cleaning = số người tháng trước * chi phí; riêng tháng 4 lấy tháng 4. | `Done` | Rows `46/48/49/51` dùng formula theo headcount tháng trước; tháng 4 fallback dùng tháng 4. | Không. |
| `65-136` | Cách lấy account theo nhóm cost center `製造/一般/販売`, rule workbook và tháng phân bổ. | `Partial` | Allocation engine có map account theo cost type và posting month override cho nhiều item. | Cần audit từng item xem account code đã đúng theo 3 nhóm; cần test bằng 3 CC đại diện. |
| `141-143` | Kickoff/party tháng 4/5, có số người riêng. | `Partial` | Có posting month override/fixed matcher cho một số item; panel manual event driver cho phép nhập count/unit/account/row khi nguồn không có. | Cần người dùng nhập count sự kiện nếu file nguồn không có. |
| `145-148` | Quà tặng người không đi du lịch và My Episode, có số người riêng. | `Partial` | Có panel manual event driver để nhập count/unit/account/row; không tự đoán. | Cần row mapping và driver riêng từ người dùng. |
| `149-151` | Kyocera Festival tháng 9, Moon cake tháng 9. | `Done` | Có posting month override; Moon cake fallback unit price `56,000` từ MP2026 khi FY2027 = 0. | Cần dữ liệu headcount/driver đúng cho CC thực tế. |
| `153-158` | Tiệc/quà kỷ niệm 10 năm và sự kiện tri ân thành lập công ty, tháng 10, có số người riêng. | `Partial` | Có override cho company anniversary tháng 10 và panel manual event driver cho dữ liệu/chốt row thiếu. | Cần map row dịch và input driver riêng. |
| `160-166` | Pocket calendar tháng 11, Sports day tháng 11, year-end/new-year tháng 2. | `Partial` | Pocket/Sports/Year-end/New-year có override; Sports day fallback unit price `107,000` từ MP2026 khi FY2027 = 0. | Cần audit account code và driver từng sự kiện. |
| `170-176` | Health check Nam/Nữ row `57`, dùng số Nam/Nữ tháng 12 và đơn giá nam/nữ. | `Partial` | Driver male/female có hỗ trợ; row `57` đã map. | Dữ liệu Nam/Nữ hiện chỉ có nếu manual headcount cung cấp; chưa có UI/nguồn đầy đủ cho mọi CC. |
| `189` | Để lại công thức. | `Done` | Exporter giữ công thức; numeric raw output ghi `=amount`. | Cần duy trì khi thêm parser mới. |
| `191-200` | Chi phí người mới; số staff row `97` đơn giá `9100`, worker row `98` đơn giá `4000`. | `Partial` | Row `97/98` đã map; matcher tách staff/worker. | Cần driver người mới staff/worker theo tháng; hiện đang suy từ delta headcount nếu rule là event month, có thể không khớp file người dùng. |
| `204-210` | Các chi phí `入社月`; riêng khám sức khỏe tuyển dụng phân bổ tháng sau, row `58`, không nhầm với khám sức khỏe định kỳ. | `Partial` | Row `58` đã map; allocator có logic next event month. | Cần test với rule/source thực tế và driver người mới; cần bảo đảm không filter mất row sổ tay staff. |

## 9. Sheet `勘定科目`

| Dòng | Yêu cầu | Trạng thái | Đối ứng hiện tại | Cần làm tiếp |
|---:|---|---|---|---|
| all | Master account mapping theo nhóm cost center. | `Partial` | Loader nạp account, allocation engine chọn account theo `mfg/ga/sales`. | Cần audit từng rule hành chính với 3 CC đại diện để đảm bảo mã account đúng trong FORM. |

## 10. Sheet `原価センタ`

| Dòng | Yêu cầu | Trạng thái | Đối ứng hiện tại | Cần làm tiếp |
|---:|---|---|---|---|
| all | Master cost center, có dòng mới/được highlight. | `Done` | Loader nạp 65 cost centers từ FORM/source và hỗ trợ code dạng chữ-số. | Nếu FORM thay đổi thêm CC mới thì chạy lại loader/E2E. |

## 11. Các khoảng trống nên đóng tiếp theo thứ tự ưu tiên

| Ưu tiên | Khoảng trống | Lý do | Hướng đóng |
|---:|---|---|---|
| `1` | Chốt/nhập dữ liệu manual event driver | Đã có panel và CSV `event_drivers_manual.csv`, nhưng cần số liệu nghiệp vụ thật cho các sự kiện không suy luận được. | Người dùng nhập `cc_code, period, event_name, count, unit_price/amount, account_code, form_row`. |
| `2` | Audit account code cho 3 nhóm `製造/一般/販売` | Nếu sai account thì số tiền đúng vẫn vào sai mã. | Thêm test 3 CC đại diện cho các item hành chính. |
| `3` | Birthday new-hire addition | Parser birthday đã đọc workbook, nhưng cần xác nhận người mới đã nằm trong workbook hay cần cộng thêm từ nguồn khác. | Đối chiếu workbook birthday với source tuyển dụng/người mới. |
| `4` | Manual mapping cho annotation bằng ảnh | Openpyxl không đọc ý nghĩa mũi tên/ảnh. | Dùng Excel/ảnh chụp để lập bảng source -> target cell. |

## 12. Kết luận audit

Kết luận trung thực: chưa đạt `100%`.

Đã đạt khá tốt ở nhóm fixed-row export, công thức output, IT, facility, fixed assets, recurring admin, NNN workbook, Birthday workbook, và đã có panel nhập dữ liệu cho phần không thể suy luận. Chưa đạt 100% vì vẫn cần người dùng cung cấp/chốt số liệu sự kiện thật, account/row cho các trường hợp chưa rõ, và annotation bằng ảnh.
