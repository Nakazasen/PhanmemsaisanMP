<!-- converted from Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026.xlsx -->

## Sheet: Sheet1
| Cải tiến nhập tự động dữ liệu chung từ các file được cung cấp sẵn vào file Master Plan |  |
| --- | --- |
| 1. Tổng quan file |  |
| 2. Các file dữ liệu chi phí chung được cung cấp |  |
|  | Chi phí hệ thống |
|  | Chi phí khấu hao, lãi nhà đất, điện nước |
|  | Chi phí tài sản cố định |
|  | Chi phí phân bổ từ hành chính  |
| 3. Nhập dữ liệu lấy từ các file vào ô cần điền trong file MP |  |
|  | Hình dung cách làm: |
|  | ① Filter "code phòng chịu chi phí" trong các file chi phí chung  |
|  | ② Filter "code tài khoản chịu chi phí", "tên tài khoản chịu chi phí", "ghi chú" trong file MP đối tượng |
|  | ③ Nhập dữ liệu từ mục ① vào ② (theo công thức hoặc paster nguyên số) |
## Sheet: Hạng mục cần cải tiến
| Những hạng mục cần cải tiến |  |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1. Không cần điền 2 dữ liệu dưới vào file |  |  |  |  |  |  |  |  |  |  |
| 2. Đẩy các cột dữ liệu ghi dưới về cột chỉ mũi tên ghi dưới |  |  |  |  |  |  |  |  |  |  |
| 3. Bôi lại đúng màu, đúng định dạng như FORM vốn có  |  |  |  |  |  |  |  |  |  |  |
| 4. Để lại tất cả các công thức tính |  |  |  |  |  |  |  |  |  |  |
| Chi tiết đã ghi ở từng sheet |  |  |  |  |  |  |  |  |  |  |
| VD:  |  |  |  |  |  |  |  |  |  |  |
| 5. Sai code chi phí hệ thống |  |  |  |  |  |  |  |  |  |  |
| 6. Nhập đồng thời số người của 12 tháng, riêng tháng 12 hiển thị nhập số lượng Nam, Nữ (để nhập chi phí khám sức khỏe) |  |  |  |  |  |  |  |  |  |  |
| Ngoài ra, do phần mềm dùng lâu dài nên ở mục khoanh đỏ ghi dưới, thay vì để 202704, 202705,…, hãy để thành Tháng 4, Tháng 5,….. |  |  |  |  |  |  |  |  |  |  |
| 7.Bổ sung thêm hạng mục ở Sheet Chi phí phân bổ từ hành chính |  |  |  |  |  |  |  |  |  |  |
|  | LINK |  |  |  |  |  |  |  |  |  |
| => Những dòng, sheet bôi màu xám là đã được thực hiện |  |  |  |  |  |  |  |  |  |  |
| Sheet không bôi màu là sheet vẫn chưa được thực hiện |  |  |  |  |  |  |  |  |  |  |
| Sheet màu đỏ là nội dung mới |  |  |  |  |  |  |  |  |  |  |
| Ngày 9/4: |  |  |  |  |  |  |  |  |  |  |
| 1. Chi phí hệ thống chưa lấy được công thức, vẫn là dạng số |  |  |  |  |  |  |  |  |  |  |
|  | => Công thức tính bị sai nên tổng tiền không khớp với số tiền đúng như IT liên lạc (số tiền ở bản ghi trên thì đúng) |  |  |  |  |  |  |  |  |  |
|  | Công thức: = ROUND(công thức của các chi phí + với nhau** tỷ giá $ (ô B2 trong file MP),0) |  |  |  |  |  |  |  |  |  |
|  | VD: phòng code 1412000006 = ROUND((11*3.19 + 12*11.51+1*153.91+2*2114.25+12*2.25)*26273,0)=120,399,175 (chi phí tổng ở sheet đầu tiên là 120,399,176) |  |  |  |  |  |  |  |  |  |
| 2. Sửa lại đối tượng áp dụng và công thức tính tiền phân bổ từ hành chính |  |  |  |  |  |  |  |  |  |  |
|  | LINK |  |  |  |  |  |  |  |  |  |
| Ngoài ra, bổ sung thêm những hạng mục ở bên dưới  |  |  |  |  |  |  |  |  |  |  |
|  | LINK |  |  |  |  |  |  |  |  |  |
| 3. Bổ sung thêm 1 loại chi phí mới: Chi phí làm giấy tờ cho người nước ngoài |  |  |  |  |  |  |  |  |  |  |
|  | LINK |  |  |  |  |  |  |  |  |  |
| A làm chi phí phân bổ từ hành chính và chi phí làm giấy tờ cho người nước ngoài trước giúp e nhé. |  |  |  |  |  |  |  |  |  |  |
| Còn chi phí tài sản cố định hơi khó nên để tuần sau a làm cũng được nha. |  |  |  |  |  |  |  |  |  |  |
| Liên quan đến nhập số người, |  |  |  |  |  |  |  |  |  |  |
| Thay vì nhập số người của 12 tháng như hiện tại thì sẽ nhập những dữ liệu ghi dưới  |  |  |  |  |  |  |  |  |  |  |
| - Số người JP (xe bus) (dùng chung cho 12 tháng) |  |  |  |  |  |  |  |  |  |  |
| - Số người VN (xe bus) (dùng chung cho 12 tháng) |  |  |  |  |  |  |  |  |  |  |
| - Tháng 3 FY cũ (tiền triết lý) |  |  |  |  |  |  |  |  |  |  |
| - Tháng 4 (tiệc chúc mừng sau buổi phát biểu phương châm bộ phận) |  |  |  |  |  |  |  |  |  |  |
| - Tháng 5 (du lịch) |  |  |  |  |  |  |  |  |  |  |
| - Tháng 6 (người ko đi du lịch được quà) |  |  |  |  |  |  |  |  |  |  |
| - Tháng 10 |  |  |  |  |  |  |  |  |  |  |
|      ・Quà kỉ niệm 10 năm |  |  |  |  |  |  |  |  |  |  |
|      ・Tiệc kỷ niệm 10 năm gắn bó |  |  |  |  |  |  |  |  |  |  |
| - Tháng 12: (đã có) |  |  |  |  |  |  |  |  |  |  |
|      ・Nam: |  |  |  |  |  |  |  |  |  |  |
|      ・Nữ: |  |  |  |  |  |  |  |  |  |  |
| Xóa nội dung dưới đây cho ko cần thiết |  |  |  |  |  |  |  |  |  |  |
| Điền dữ liệu theo thứ tự dưới đây: |  |  |  |  |  |  |  |  |  |  |
|  | Ngoài ra, thứ tự các chi phí của từng file thì ghi trong từng sheet bên cạnh |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  | 6 chi phí |  |  |  |
|  |  |  |  |  |  |  |  |  |  | gộp thành 1 dòng chi phí |
| 2026-09-06 00:00:00 |  |  |  |  |  |  |  |  |  |  |
| 1 | Xóa nội dung dưới đây |  |  |  |  |  |  |  |  |  |
| 2 | Bổ sung thêm nhập số người |  |  |  |  |  |  |  |  |  |
|  | - Người biệt phái đi xe bus |  |  |  |  |  |  |  |  |  |
|  | - Người VN đi xe bus |  |  |  |  |  |  |  |  |  |
|  | Cách điền theo công thức |  |  | LINK |  |  |  |  |  |  |
| 3 | Chi phí tài sản cố định |  |  |  |  |  |  |  |  |  |
|  | - Chưa chạy được hết tất cả các dữ liệu của CC |  |  |  |  | LINK |  |  |  |  |
| 4 | Chi phí khám sức khỏe |  |  |  |  |  |  |  |  |  |
|  | - Đang bị lặp 2 lần |  |  |  |  |  |  |  |  |  |
| 5 | Chi phí văn phòng phẩm của người mới đang bị sai |  |  |  |  |  |  |  |  |  |
|  | - Tất cả các chi phí người mới đang bị nhập vào tháng 12 và nhân với tổng số người |  |  |  |  |  |  |  | LINK  |  |
| 6 | Chưa chạy xong các chi phí phân bổ từ hành chính |  |  |  |  |  |  |  |  |  |
|  | - Dữ liệu từ A144~A169 |  |  | LINK |  |  |  |  |  |  |
|  | - Chi phí khám sức khỏe cho người mới |  |  |  | LINK |  |  |  |  |  |
| 7 | Bổ sung thêm mô tả  |  |  |  |  |  |  |  |  |  |
| 8 | Nhập xong dữ liệu của từng file thì sẽ cách 1 dòng, không nhập theo dòng như trước nữa |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  | ->đã làm xong |  |  |  |
|  |  |  |  |  |  |  |  |  |  | chưa xong |
|  |  |  |  |  |  |  |  |  |  | ->đã làm xong |
|  |  |  |  |  |  | chưa xong |  |  |  |  |
|  |  |  |  |  |  | ->đã làm xong |  |  |  |  |
|  |  |  |  |  |  |  | chưa xong |  |  |  |
|  |  |  |  |  |  |  |  | ->đã làm xong |  |  |
## Sheet: Chi phí hệ thống
| Chi phí hệ thống |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1. Tổng quan file: có nhiều sheet |  |  |  |  |  |  |  |  |
| 2. Các sheet chi tiết |  |  |  |  |  |  |  |  |
| Ví dụ: Chi tiết chi phí VPN |  |  |  |  |  |  |  |  |
|  | Các thông tin cần lấy dữ liệu như dưới: |  |  |  |  |  |  |  |
|  | Công thức: = số người * Đơn giá  |  |  |  |  |  |  |  |
|  | VD: Phòng code 141200006 = 11*3.19 |  |  |  |  |  |  |  |
| Các sheet còn lại tương tự công thức như vậy |  |  |  |  |  |  |  |  |
| 3. Tổng chi phí hệ thống |  |  |  |  |  |  |  |  |
| Công thức: = ROUND(công thức của các chi phí + với nhau** tỷ giá $ (ô B2 trong file MP),0) |  |  |  |  |  |  |  |  |
| VD: phòng code 1412000006 = ROUND((11*3.19 + 12*11.51+1*153.91+2*2114.25+12*2.25)*26273,0)=120,399,175 (chi phí tổng ở sheet đầu tiên là 120,399,176) |  |  |  |  |  |  |  |  |
| => Do có chút chênh lệch về tỷ giá sẽ có trường hợp lệch 1 vài đồng so với chi phí ở sheet đầu tiên (sheet tổng các chi phí) như trên |  |  |  |  |  |  |  |  |
| Nhập vào 1 dòng duy nhất |  |  |  |  |  |  |  |  |
| 4. Cách làm |  |  |  |  |  |  |  |  |
|  | ① Filter "code phòng chịu chi phí" của từng sheet |  |  |  |  |  |  |  |
|  | ② Nhập công thức sau khi lấy được tất cả các dữ liệu của từng sheet |  |  |  |  |  |  |  |
|  | ③ So sánh tổng công hức đã nhập với tổng chi phí của sheet tổng |  |  |  |  |  |  |  |
|  | ④ Điều chỉnh cho khớp với tổng chi phí của sheet tổng nếu lệch 1 vài đồng do tỷ giá (ko cần đưa làm lưu trình nếu làm tự động) |  |  |  |  |  |  |  |
|  | ⑤ Xác nhận số người cần dự tính của từng tháng để nhập cho các tháng (ví dụ: người nghỉ sinh,…) |  |  |  |  |  |  |  |
## Sheet: Chi phí khấu hao, lãi nhà đất
| Chi phí khấu hao, lãi nhà đất, điện nước |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1. Tổng quan file: gồm 3 loại chi phí: khấu hao nhà đất, lãi nhà đất, điện-nước |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 2. Các sheet chi phí trong file dữ liệu |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 2.1. Sheet chi phí khấu hao nhà, đất |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Cách làm: | ① Tìm "code phòng chịu chi phí" để lấy dữ liệu (filter có khả năng mất dòng khấu hao đất nên làm thủ công thì ko filter) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ② Nhập công thức |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Khấu hao nhà: |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Công thức = ROUND (chi phí khấu hao nhà * tỷ giá $(ô B2 trong file MP),0) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Khấu hao đất: |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Công thức = ROUND (chi phí khấu hao đất * tỷ giá $(ô B2 trong file MP),0) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ③ Phải nhập cho tất cả các tháng |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 2.2. Sheet chi phí lãi nhà, đất |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Cách làm: | ① Tìm "code phòng chịu chi phí" để lấy dữ liệu (filter có khả năng mất dòng lãi đất nên làm thủ công thì ko filter) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ② Nhập công thức |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Lãi nhà: |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Công thức = ROUND (chi phí lãi nhà * tỷ giá $(ô B2 trong file MP),0) |  |  |  |  |  |  |  | Thứ tự 3 |  |  |  |  |  |  |  |
|  | Lãi đất: |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Công thức = ROUND (chi phí lãi đất * tỷ giá $(ô B2 trong file MP),0) |  |  |  |  |  |  |  | Thứ tự 4 |  |  |  |  |  |  |  |
|  | ③ Phải nhập cho tất cả các tháng |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 2.2. Sheet điện-nước |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Cách làm: | ① Tìm "code phòng chịu chi phí" để lấy dữ liệu (filter có khả năng mất dòng lãi đất nên làm thủ công thì ko filter) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ② Copy/paste dữ liệu điện+nước |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Tiền điện | Thứ tự 5 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Tiền nước | Thứ tự 6 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
## Sheet: Chi phí tài sản cố định
| Chi phí tài sản cố định (TSCĐ) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1. Tổng quan file:  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 2. Cách làm |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ① Filter "code phòng chịu chi phí" |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ② Xác nhận"tháng khấu hao cuối cùng" có trong kỳ FY đó ko, nếu ko thì nhập theo bước ③,④ dưới đây, nếu có thì thực hiện từ bước ⑤ trở đi |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ③ Lấy dữ liệu chi phí khấu hao rồi nhập theo công thức = ROUND(chi phí khấu hao * tỷ giá $ (ô B2 trong file MP),0) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ④ Lấy dữ liệu chi phí lãi rồi nhập theo công thức =ROUND(chi phí lãi * tỷ giá $ (ô B2 trong file MP),0) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |     (Cột chi phí lãi có 2 loại: tháng 4 và từ tháng 5 trở đi=> lấy dữ liệu của từng ô để nhập tương ứng cho từng tháng) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |             VD: | No.1: Tháng khấu hao cuối cùng No.3 là 11/2027 thì nhập theo công thức trên cho tất cả các tháng |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ⑤ Các tháng trước tháng cuối cùng thì điền chi phí khấu hao, lãi giống như bước ③ và ④ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ⑥ Vào tháng khấu hao cuối cùng, lấy giá trị của trong cột "tháng khấu hao cuối cùng" |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |            VD:  | No.3: Tháng khấu hao cuối cùng là 5/2026 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  Đối với chi phí khấu hao |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  | Tháng 4 làm theo bước ③ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  | Tháng 5 = ROUND( "chi phí khấu hao của tháng cuối cùng" * tỷ giá $ (ô B2 trong file MP),0) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  | Từ tháng 6 đến hết: không phải điền |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  | Đối với chi phí lãi |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  | Tháng 4~5: Làm theo bước ④  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  | Từ tháng 6 đến hết: không phải điền |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | No.23: Tháng khấu hao cuối cùng là 11/2026 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  Đối với chi phí khấu hao |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  | Tháng 4~10 làm theo bước ③ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  | Tháng 11 = ROUND( "chi phí khấu hao của tháng cuối cùng" * tỷ giá $ (ô B2 trong file MP),0) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  | Từ tháng 12 đến hết: không phải điền |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  | Đối với chi phí lãi |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  | Tháng 4~11: Làm theo bước ④ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  | Từ tháng 12 đến hết: không phải điền |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
## Sheet: Chi phí làm giấy tờ cho NNN
| Chi phí làm giấy tờ cho NNN |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cách làm: | ① Filter code tài khoản mong muốn tại cột "Code tài khoản chịu chi phí" |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ② Nhập số tiền của các tháng hiện ra ở file trên vào các cột tháng tương ứng ở file FORM |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | VD: |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | - Lọc code 1412000018 ghi dưới |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | - Có 2 người cùng ở code đó, và các mỗi người thì chi phí thì phân bổ rải rác vào nhiều tháng như dưới |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | - Lấy tất cảt các chi phí đó nhập vào FORM |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
## Sheet: Chi phí sinh nhật
| Chi phí sinh nhật |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cách làm: | ① Filter code tài khoản mong muốn tại cột "Code tài khoản chịu chi phí" |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ② Lấy số người tương ứng với cột tháng  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ③ Filter cột nội dung của file "FY2027配賦額一覧" với nội dung: 誕生日会 Tiệc sinh nhật |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | cách lấy mã code giống như ở đây → |  |  |  | LINK |  |  |  |  |  |  |  |  |  |  |
|  | ④ Nhập vào dòng 63 (từ G63=>  Q63) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Công thức = số người * đơn giá |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ※ Ngoài ra, trong trường hợp tháng đó có người mới thì sẽ cộng luôn số người mới đó vào luôn |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | VD: Tháng 6 phòng 1412000006 có 2 người sinh nhật, trong tháng đó có 1 người mới thì tổng số người sinh nhật trong tháng 6 sẽ là 3 người |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Công thức = (2 người(trong file ở đầu) + 1 người mới )* 152,000VND |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
## Sheet: Chi phí phân bổ từ hành chính 
| Chi phí phân bổ từ hành chính  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1. Chi phí phân bổ cho cả 12 tháng |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Cách làm: | ① Điền các dữ liệu chi phí tương ứng vào ô chi phí trong file MP (áp dụng cho tiền gas, nước rửa tay, giấy vệ sinh, chi phí làm sạch) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |      Công thức = số người * chi phí tương ứng |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | Số người: Tổng số người của tháng trước (Cũ: công thức = số người của tháng đó * chi phí tương ứng) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | Do ko có dữ liệu tháng 3 của kỳ trước nên số người của tháng 4 sẽ vẫn lấy tổng số người của tháng 4 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ② Điền các dữ liệu chi phí tương ứng vào ô chi phí trong file MP (áp dụng cho tiền xe bus đưa đón người Nhật, người Việt) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |      Công thức = số người (nhập ở đầu phần mềm) * chi phí tương ứng |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 2. Chi phí phân bổ đặc thù cho từng tháng |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ※Cách lấy mã đúng cho từng code phòng chịu chi phí |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Trong công ty chia ra 3 nhóm: |  | 製造 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  | 一般 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  | 販売 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Dựa vào 2 sheet dưới đây để lấy mã tài khoản cho đúng  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | 原価センタ |  |  |  |  |  |  | 勘定科目 |  |  |  |  |  |  |  |  |  |  |
| 社員旅行 Du lịch công ty: Tháng 5 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ① Xác nhận code phòng chi phí  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | Được chọn ngay từ lúc nhập mã phòng trên phần mềm |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | VD: Code 1412000089 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ② Xác nhận code phòng chi phí thuộc nhóm nào (製造、一般、販売） |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | - Mở sheet này | 原価センタ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | - Filter cột A1 như dưới |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | - Biết được thuộc nhóm 製造 như ô khoanh đỏ trên |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ③ Xác nhận nhóm đó thì sẽ là mã tài khoản nào |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | - Mở file "FY2027配賦額一覧" như dưới |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | - Filter "社員旅行 Du lịch công ty" tại cột B "Nội dung 内容"  |  |  |  |  | (Chú ý: Filter giống như đầu mục trước dấu 2 chấm) |  |  |  |  |  | ☚ Bấm vô |  |  |  |  |  |  |
|  |  | - Xác định tháng phân bổ: cột G màu xanh lá như dưới |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | - Lấy tên tài khoản ở khung đỏ xanh dương như dưới |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | - Mở sheet này | 勘定科目 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | - Filter tên tài khoản "福利厚生費" (khung xanh dương ở trên) ở cột D "JP_Name" khung đỏ ở dưới |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | - Cột F, H, H tương ứng với 3 nhóm sẽ hiện ra các mã tài khoản tương ứng |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | - Ở mục ② ghi trên đã xác nhận được code chi phí phòng hiện tại đang làm là nhóm 製造, do đó sẽ lấy mã code theo cột F "製造", là khung tím ở dưới |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ④ Nhập mã tài khoản vào FORM tương ứng với tháng phân bổ đã xác định ở trên (tháng 5) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ⑤ Nhập công thức= Số người * Đơn giá |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | Số người: Số người nhập ban đầu khi mở phần mềm |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | Đơn giá: Cột H của file "FY2027配賦額一覧" (màu hồng ở ảnh trên) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Áp dụng cùng cách làm ghi trên cho các chi phí ghi dưới |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| FY2027部門方針発表会後の決起コンパ  Tiệc chúc mừng sau buổi phát biểu phương châm bộ phận KDTVN FY2027: Tháng 4  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| (có số người riêng) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Tiệc khuấy động năm tài chính決起コンパ: Tháng 5 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  社員旅行不参加対象者へのギフト贈呈 Quà tặng cho CNV không thể tham gia du lịch: Tháng 6 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| (có số người riêng) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| マイエピソード ～フィロソフィの実践～参加賞
Giải tham gia "Cảm nghĩ về triết lý kinh doanh": Tháng 7 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| (có số người riêng) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 京セラフェスティバルLễ hội Kyocera: Tháng 9 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 月餅 Bánh Trung Thu: Tháng 9 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 10年勤続記念コンパ Tiệc kỷ niệm 10 năm gắn bó: Tháng 10 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| (có số người riêng) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 10年勤続記念品 Quà kỷ niệm cho CNV 10 năm gắn bó: Tháng 10 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| (có số người riêng) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 会社設立記念 感謝イベント Sự kiện tri ân ngày thành lập công ty : Tháng 10 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ポケットカレンダー Lịch bỏ túi: Tháng 11 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 運動会 Đại hội thể thao: Tháng 11 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 忘年会補助金 Hỗ trợ tiệc tất niên: Tháng 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| お年玉 Tiền lì xì: Tháng 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Khám sức khỏe (cho CNV nam): |  |  |  | => bị lặp |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Khám sức khỏe (cho CNV nữ): |  |  |  | => bị lặp |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ① → ④: Giống ghi trên |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ⑤ Nhập công thức= Số người * Đơn giá |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | Số người: Số người nhập ban đầu khi mở phần mềm_chỗ tháng 12 đã chia rõ số người nam, nữ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | Đơn giá: Cột H của file "FY2027配賦額一覧" (đơn giá của nam, nữ tương ứng như dưới) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | => Để lại công thức cho e nhé |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Tiền chi phí cho người mới: |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Sẽ có tất cả những chi phí ở bảng dưới. |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Công thức và cách điền tháng như hiện tại đã đúng. |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Tuy nhiên, cần bổ sung thêm hạng mục bôi màu ghi dưới  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Số người mới = số người tháng sau - số người tháng trước (VD: Tháng 5: 22 người, tháng 6: 26 người => số người mới = 26 - 22 =4 người) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | ・Sổ: chi phí của nhân viên và công nhân khác nhau |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  | => trường hợp có người mới là nhân viên thì sẽ nhập vào ô công nhân ở chỗ nhập nhân sự thủ công |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  | Công thức = số người nhân viên mới * đơn giá (9100VND) |  |  |  |  |  |  | VD: Trong 4 người ở VD trên có 1 người nhân viên thì công thức sẽ là 1 * 9100 = 9100 |  |  |  |  |  |  |  |
|  |  |  |  |  | => trường hợp có người mới là công nhân thì sẽ nhập vào ô công nhân ở chỗ nhập nhân sự thủ công |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  | Công thức = số người công nhân mới * đơn giá (4000VND) |  |  |  |  |  |  | VD: Trong 4 người ở VD trên có 3 người công nhân thì công thức sẽ là 3 * 4000 = 12000 |  |  |  |  |  |  |  |
|  | ※Chú ý: Điểm chung của các chi phí dưới đây là ở cột Tháng phân bổ "入社月", tuy nhiên nếu filter thì sẽ bị mất dòng chi phí sổ của nhân viên nên a làm thế nào để lấy được đủ tiền cho e nhé |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | ・Khám sức khỏe khi tuyển dụng |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | Người mớ vào tháng này thì chi phí khám sưc khỏe tuyển dụng sẽ phân bổ vào tháng sau |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | VD: Tháng 6 người mới vào thì chi phí khám sức khỏe sẽ phân bổ vào tháng 7 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  | Công thức = số người * đơn giá |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | ※Chú ý: Chi phí khám sức khỏe khi tuyển dụng khác với chi phí khám sức khỏe định kỳ của công ty, do đó a đừng lấy nhầm chi phí nhé |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
## Sheet: 勘定科目
| Account_Code | JPN (50cha) | Tiếng Việt_Tên tài khoản kế toán | JP_Name | Tiếng Việt_Hạng mục lợi nhuận | 製造 | 一般 | 販売 | REMARK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  | 6 | 7 | 8 |  |
| 7001065118 | 雑収入 | Doanh thu khác | 雑収入 | Thu nhập khác | 7001065118 | 7001065118 | 7001065118 |  |
| 7001075118 | 雑収入（関係会社） | Doanh thu khác | 雑収入 | Thu nhập khác | 7001075118 | 7001075118 | 7001075118 |  |
| 7001065119 | 固定資産売却勘定 | Doanh thu khác | 雑収入 | Thu nhập khác |  |  |  |  |
| 5001016131 | 材料仕入割戻高 | Chi phí nguyên liệu, vật liệu trực tiếp | 材料費 | Chi phí nguyên vật liệu | 5001016131 |  |  | 2016年4月から追加する。 |
| 5001016134 | リーフレット用材料 | Chi phí nguyên liệu, vật liệu trực tiếp | 材料費 | Chi phí nguyên vật liệu | 5001016134 | 5001016134 | 5001016134 | 2017年1月変更。 |
| 5001016135 | 不良部品材料費 | Chi phí nguyên liệu, vật liệu trực tiếp | 材料費 | Chi phí nguyên vật liệu | 5001016135 | 5001016135 | 5001016135 |  |
| 5001016136 | 追加指図部品費 | Chi phí nguyên liệu, vật liệu trực tiếp | 材料費 | Chi phí nguyên vật liệu | 5001016136 | 5001016136 | 5001016136 |  |
| 5001016142 | 加工中不良廃棄損 | Chi phí nguyên liệu, vật liệu trực tiếp | 仕掛仕損 | Sản phẩm chưa hoàn thiện,hỏng | 5001016142 | 5001016142 | 5001016142 |  |
| 5001016149 | 金型材料仕入 | Chi phí nguyên liệu, vật liệu trực tiếp | 材料費 | Chi phí nguyên vật liệu | 5001016149 | 5001016149 | 5001016149 | 2月から追加する。 |
| 5001016151 | 生産用副資材 | Chi phí nguyên liệu, vật liệu trực tiếp | 材料費 | Chi phí nguyên vật liệu | 5001016151 |  |  | 2017年1月追加。 |
| 5004046221 | 雑給（直製） | Chi phí nhân công trực tiếp | 雑給 | Chi phí nhân công trực tiếp | 5004046221 |  |  |  |
| 5004046371 | 雑給（間製） | Chi phí nhân viên phân xưởng | 雑給 | Chi phí nhân công trực tiếp | 5004046371 |  |  |  |
| 5005016371 | 生産用消耗品費（製） | Chi phí dụng cụ sản xuất | 消耗品費 | Chi phí hàng hóa tiêu hao | 5005016371 |  |  |  |
| 5005016372 | その他消耗品（製） | Chi phí dụng cụ sản xuất | 消耗品費 | Chi phí hàng hóa tiêu hao | 5005016372 |  |  |  |
| 5005016373 | 生産用文房具（製造） | Chi phí dụng cụ sản xuất | 消耗品費 | Chi phí hàng hóa tiêu hao | 5005016373 |  |  | 2017年1月追加。 |
| 5005026371 | 消耗工具器具備品費（製） | Chi phí dụng cụ sản xuất | 消耗工具器具備品費 | Chi phí sử dụng công cụ,đồ đạc | 5005026371 |  |  |  |
| 5005026372 | 消耗金型代（製） | Chi phí dụng cụ sản xuất | 消耗金型費 | Chi phí tiêu hao khuôn | 5005026372 |  |  |  |
| 5006016241 | 減価償却費（製）　建物 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao | 5006016241 |  |  |  |
| 5006016242 | 減価償却費（製）　機械装置 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao | 5006016242 |  |  |  |
| 5006016243 | 減価償却費（製）　車輌運搬具 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao | 5006016243 |  |  |  |
| 5006016244 | 減価償却費（製）　工具器具備品 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao | 5006016244 |  |  |  |
| 5006016245 | 減価償却費（製）　構築物 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao | 5006016245 |  |  |  |
| 5005036246 | 減価償却費（製）　金型 | Chi phí khấu hao TSCĐ | 金型償却費 | Chi phí khấu hao khuôn | 5005036246 |  |  |  |
| 5006016247 | 減価償却費（製）　その他有形固定資産 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao | 5006016247 |  |  |  |
| 5006016248 | 減価償却費（製）　リース建物 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao | 5006016248 |  |  |  |
| 5006016249 | 減価償却費（製）　リース機械装置 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao | 5006016249 |  |  |  |
| 5006016250 | 減価償却費（製）　リース車輌運搬具 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao | 5006016250 |  |  |  |
| 5006016251 | 減価償却費（製）　リース工具器具備品 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao | 5006016251 |  |  |  |
| 5006016252 | 減価償却費（製）　リース構築物 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao | 5006016252 |  |  |  |
| 5006016253 | 減価償却費（製）　土地使用権 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao | 5006016253 |  |  |  |
| 5006016254 | 減価償却費（製）　出版著作権 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao | 5006016254 |  |  |  |
| 5006016255 | 減価償却費（製）　特許権 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao | 5006016255 |  |  |  |
| 5006016256 | 減価償却費（製）　商標権 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao | 5006016256 |  |  |  |
| 5006016257 | 減価償却費（製）　ソフトウェア | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao | 5006016257 |  |  |  |
| 5006016258 | 減価償却費（製）　営業権 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao | 5006016258 |  |  |  |
| 5006016259 | 減価償却費（製）　その他無形固定資産 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao | 5006016259 |  |  |  |
| 5006016260 | 減価償却費配賦（製）　建物 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao | 5006016260 |  |  |  |
| 5006016261 | 減価償却費配賦（製）　土地使用権 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao | 5006016261 |  |  |  |
| 5004096281 | 求人費（製） | Chi phi dịch vụ mua ngoài | 募集教育費 | Chi phí tuyển dụng,đào tạo | 5004096281 |  |  |  |
| 5005046281 | 機械設備修繕費（製） | Chi phi dịch vụ mua ngoài | 修繕費 | Chi phí sửa chữa | 5005046281 |  |  |  |
| 5005046282 | その他修繕費（製） | Chi phi dịch vụ mua ngoài | 修繕費 | Chi phí sửa chữa | 5005046282 |  |  |  |
| 5005046283 | 年間保守料（製） | Chi phi dịch vụ mua ngoài | 修繕費 | Chi phí sửa chữa | 5005046283 |  |  |  |
| 5005046284 | 金型修繕費（製造） | Chi phi dịch vụ mua ngoài | 修繕費 | Chi phí sửa chữa | 5005046284 |  |  | 2017年1月追加。 |
| 5005066281 | 電気代（製） | Chi phi dịch vụ mua ngoài | 水道光熱費 | Chi phí Utilities(điện,nước..) | 5005066281 |  |  |  |
| 5005066282 | 水道代（製） | Chi phi dịch vụ mua ngoài | 水道光熱費 | Chi phí Utilities(điện,nước..) | 5005066282 |  |  |  |
| 5005056281 | ガス代（製） | Chi phi dịch vụ mua ngoài | 水道光熱費 | Chi phí Utilities(điện,nước..) | 5005056281 |  |  |  |
| 5005076281 | 通関申告費用（製） | Chi phi dịch vụ mua ngoài | 荷造運賃 | Chi phí vận chuyển hàng hóa | 5005076281 |  |  |  |
| 5005076282 | 設備輸送費（製） | Chi phi dịch vụ mua ngoài | 荷造運賃 | Chi phí vận chuyển hàng hóa | 5005076282 |  |  |  |
| 5005076283 | 輸入航空運賃（製） | Chi phi dịch vụ mua ngoài | 荷造運賃 | Chi phí vận chuyển hàng hóa | 5005076283 |  |  |  |
| 5005076284 | 輸入海上運賃（製） | Chi phi dịch vụ mua ngoài | 荷造運賃 | Chi phí vận chuyển hàng hóa | 5005076284 |  |  |  |
| 5005076285 | 空箱返却費用 | Chi phi dịch vụ mua ngoài | 荷造運賃 | Chi phí vận chuyển hàng hóa | 5005076285 |  |  |  |
| 5005076286 | 部品集荷トラック代 | Chi phi dịch vụ mua ngoài | 荷造運賃 | Chi phí vận chuyển hàng hóa | 5005076286 |  |  |  |
| 5005076287 | 物流保険料（製） | Chi phi dịch vụ mua ngoài | 荷造運賃 | Chi phí vận chuyển hàng hóa | 5005076287 |  |  |  |
| 5005076288 | 梱包材料費（製） | Chi phi dịch vụ mua ngoài | 荷造用品費 | Chi phí NVL dùng đóng gói hàng | 5005076288 |  |  |  |
| 5005076289 | クーリエ費用（製） | Chi phi dịch vụ mua ngoài | 荷造運賃 | Chi phí vận chuyển hàng hóa | 5005076289 |  |  |  |
| 5005076291 | 外部倉庫　取扱手数料（製造） | Chi phi dịch vụ mua ngoài | 荷造運賃 | Chi phí vận chuyển hàng hóa | 5005076291 |  |  | 2017年1月追加。 |
| 5005076292 | 外部倉庫　保管料（製造） | Chi phi dịch vụ mua ngoài | 荷造運賃 | Chi phí vận chuyển hàng hóa | 5005076292 |  |  | 2017年1月追加。 |
| 5005076293 | 外部倉庫　輸送料（製造） | Chi phi dịch vụ mua ngoài | 荷造運賃 | Chi phí vận chuyển hàng hóa | 5005076293 |  |  | 2017年1月追加。 |
| 5005076294 | 外部物流業者　取扱手数料（製造） | Chi phi dịch vụ mua ngoài | 荷造運賃 | Chi phí vận chuyển hàng hóa | 5005076294 |  |  | 2017年1月追加。 |
| 5005086281 | 技術料（製） | Chi phi dịch vụ mua ngoài | 技術料 | Phí kỹ thuật | 5005086281 |  |  |  |
| 5005136281 | 通信費（製） | Chi phi dịch vụ mua ngoài | 通信費 | Chi phí điện thoại | 5005136281 |  |  |  |
| 5005246281 | 図書印刷費（製） | Chi phi dịch vụ mua ngoài | 図書及び事務費 | Chi phí văn phòng | 5005246281 |  |  |  |
| 5005246282 | ＫＤＣシステム使用料（製） | Chi phi dịch vụ mua ngoài | 図書及び事務費 | Chi phí văn phòng | 5005246282 |  |  |  |
| 5005246283 | ライセンス料（製） | Chi phi dịch vụ mua ngoài | 図書及び事務費 | Chi phí văn phòng | 5005246283 |  |  |  |
| 5005246284 | 会費（製） | Chi phi dịch vụ mua ngoài | 会費及び会議費 | Chi phí cuộc họp | 5005246284 |  |  |  |
| 5005216281 | 委嘱報酬・設計委託費（製） | Chi phi dịch vụ mua ngoài | 委嘱報酬 | Thù lao ủy thác,phí hoa hồng | 5005216281 |  |  |  |
| 5005226281 | 保険料（製） | Chi phi dịch vụ mua ngoài | 保険料 | Chi phí bảo hiểm | 5005226281 |  |  |  |
| 5005236281 | 事務所賃借料（製） | Chi phi dịch vụ mua ngoài | 賃借料 | Chi phí thuê | 5005236281 |  |  |  |
| 5005236282 | 倉庫賃借料（製） | Chi phi dịch vụ mua ngoài | 賃借料 | Chi phí thuê | 5005236282 |  |  |  |
| 5005246285 | 取扱手数料（製） | Chi phi dịch vụ mua ngoài | 手数料 | Tiền dịch vụ,tiền lệ phí | 5005246285 |  |  |  |
| 5005246286 | その他手数料（製） | Chi phi dịch vụ mua ngoài | 手数料 | Tiền dịch vụ,tiền lệ phí | 5005246286 |  |  |  |
| 5005246287 | ＫＤＣ手数料（製） | Chi phi dịch vụ mua ngoài | 手数料 | Tiền dịch vụ,tiền lệ phí | 5005246287 |  |  |  |
| 5005246288 | 事務用品費（製） | Chi phi dịch vụ mua ngoài | 図書及び事務費 | Chi phí văn phòng | 5005246288 |  |  |  |
| 5004086291 | 福利厚生費（製） | Chi phí bằng tiền khác | 福利厚生費 | Chi phí phúc lợi | 5004086291 |  |  |  |
| 5004086293 | 教育訓練費（製） | Chi phí bằng tiền khác | 募集教育費 | Chi phí tuyển dụng,đào tạo | 5004086293 |  |  |  |
| 5005116291 | ベトナム国内交通費（製） | Chi phí bằng tiền khác | 旅費交通費 | Chi phí di chuyển | 5005116291 |  |  |  |
| 5005116292 | 海外渡航費（製） | Chi phí bằng tiền khác | 渡航費 | Chi phí di chuyển(nước ngoài) | 5005116292 |  |  |  |
| 5005136291 | 郵送代（製） | Chi phí bằng tiền khác | 通信費 | Chi phí điện thoại | 5005136291 |  |  |  |
| 5005166291 | 接待交際費（製） | Chi phí bằng tiền khác | 接待交際費 | Chi phí tiếp khách | 5005166291 |  |  |  |
| 5005186292 | その他税金（製） | Chi phí bằng tiền khác | 公租公課 | Thuế,phí công cộng | 5005186292 |  |  |  |
| 5005196373 | 試験研究用材料費 | Chi phí dụng cụ sản xuất | 試験研究費 | Chi phí thử nghiệm,nghiên cứu | 5005196373 | 5005196373 | 5005196373 | 2月から追加する。 |
| 5005196277 | 試験研究用役務費 | Chi phi dịch vụ mua ngoài | 試験研究費 | Chi phí thử nghiệm,nghiên cứu | 5005196277 | 5005196277 | 5005196277 | 2月から追加する。 |
| 5005246291 | 会議費（製） | Chi phí bằng tiền khác | 会費及び会議費 | Chi phí cuộc họp | 5005246291 |  |  |  |
| 5005246292 | 雑費（製） | Chi phí bằng tiền khác | 雑費 | Các loại chi phí bằng tiền khác | 5005246292 |  |  |  |
| 5005246294 | 開発費振替勘定（製） | Chi phí bằng tiền khác | 雑費 | Các loại chi phí bằng tiền khác | 5005246294 |  |  | 2月から追加する→9/2015からｘから雑費になった |
| 5005256291 | 棚卸減耗費（製） | Chi phí bằng tiền khác | 棚卸減耗費 | Chi phí hao hụt sau kiểm kê | 5005256291 |  |  |  |
| 5101016174 | 製商品仕入諸掛 | Giá vốn hàng bán | 仕入製商品費 | Chi phí bán hàng | 5101016174 |  |  |  |
| 5101016179 | 製品品目外注加工費 | Giá vốn hàng bán | 外注加工費 | Chi phí gia công ngoài | 5101016179 |  |  |  |
| 5101016187 | 製商品在庫廃棄損 | Giá vốn hàng bán | 雑損失 | Tổn thất,lỗ khác | 5101016187 |  |  |  |
| 5101016189 | 金型製作収入 | Doanh thu bán thành phẩm | 雑収入 | Thu nhập khác | 5101016189 |  |  | 2月から追加する。 |
| 6004046511 | 雑給（販売） | Chi phí nhân viên | 雑給 | Chi phí nhân công trực tiếp |  |  | 6004046511 |  |
| 6003036412 | 梱包材料費（販売） | Chi phí vật liệu bao bì | 荷造用品費 | Chi phí NVL dùng đóng gói hàng |  |  | 6003036412 |  |
| 6005016413 | 消耗品費（販売） | Chi phí dụng cụ đồ dùng | 消耗品費 | Chi phí hàng hóa tiêu hao |  |  | 6005016413 |  |
| 6005016414 | 消耗備品費（販売） | Chi phí dụng cụ đồ dùng | 消耗工具器具備品費 | Chi phí sử dụng công cụ,đồ đạc |  | 6005016414 | 6005016414 | 2017年1月追加。 |
| 6006016521 | 減価償却費（販）　建物 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  |  | 6006016521 |  |
| 6006016522 | 減価償却費（販）　機械装置 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  |  | 6006016522 |  |
| 6006016523 | 減価償却費（販）　車輌運搬具 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  |  | 6006016523 |  |
| 6006016524 | 減価償却費（販）　工具器具備品 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  |  | 6006016524 |  |
| 6006016525 | 減価償却費（販）　構築物 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  |  | 6006016525 |  |
| 6006016526 | 減価償却費（販）　その他有形固定資産 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  |  | 6006016526 |  |
| 6006016527 | 減価償却費（販）　リース建物 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  |  | 6006016527 |  |
| 6006016528 | 減価償却費（販）　リース機械装置 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  |  | 6006016528 |  |
| 6006016529 | 減価償却費（販）　リース車輌運搬具 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  |  | 6006016529 |  |
| 6006016530 | 減価償却費（販）　リース工具器具備品 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  |  | 6006016530 |  |
| 6006016531 | 減価償却費（販）　リース構築物 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  |  | 6006016531 |  |
| 6006016532 | 減価償却費（販）　土地使用権 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  |  | 6006016532 |  |
| 6006016533 | 減価償却費（販）　出版著作権 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  |  | 6006016533 |  |
| 6006016534 | 減価償却費（販）　特許権 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  |  | 6006016534 |  |
| 6006016535 | 減価償却費（販）　商標権 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  |  | 6006016535 |  |
| 6006016536 | 減価償却費（販）　ソフトウェア | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  |  | 6006016536 |  |
| 6006016537 | 減価償却費（販）　営業権 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  |  | 6006016537 |  |
| 6006016538 | 減価償却費（販）　その他無形固定資産 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  |  | 6006016538 |  |
| 6006016539 | 減価償却費配賦（販）　建物 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  |  | 6006016539 |  |
| 6006016540 | 減価償却費配賦（販）　土地使用権 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  |  | 6006016540 |  |
| 6005046541 | その他修繕費（販売） | Chi phí bảo hành | 修繕費 | Chi phí sửa chữa |  |  | 6005046541 |  |
| 6005046542 | 年間保守料（販売） | Chi phí bảo hành | 修繕費 | Chi phí sửa chữa |  |  | 6005046542 |  |
| 6003016541 | 販売手数料（販売） | Chi phí dịch vụ mua ngòai | 手数料 | Tiền dịch vụ,tiền lệ phí |  |  | 6003016541 |  |
| 6003026541 | 販売促進費（販売） | Chi phí dịch vụ mua ngòai | 雑費 | Các loại chi phí bằng tiền khác |  |  | 6003026541 |  |
| 6003036541 | 通関申告料（販売） | Chi phí dịch vụ mua ngòai | 荷造運賃 | Chi phí vận chuyển hàng hóa |  |  | 6003036541 |  |
| 6003036542 | クーリエ費用（販売） | Chi phí dịch vụ mua ngòai | 荷造運賃 | Chi phí vận chuyển hàng hóa |  |  | 6003036542 |  |
| 6003036543 | 輸出航空運賃（販売） | Chi phí dịch vụ mua ngòai | 荷造運賃 | Chi phí vận chuyển hàng hóa | 6003036543 |  | 6003036543 |  |
| 6003036544 | 輸出海上運賃（販売） | Chi phí dịch vụ mua ngòai | 荷造運賃 | Chi phí vận chuyển hàng hóa | 6003036544 | 6003036544 | 6003036544 |  |
| 6003036545 | 保管延長費（販売） | Chi phí dịch vụ mua ngòai | 荷造運賃 | Chi phí vận chuyển hàng hóa |  |  | 6003036545 |  |
| 6003036546 | 物流保険料（販売） | Chi phí dịch vụ mua ngòai | 荷造運賃 | Chi phí vận chuyển hàng hóa |  |  | 6003036546 |  |
| 6003036547 | 梱包費用（販売） | Chi phí dịch vụ mua ngòai | 荷造運賃 | Chi phí vận chuyển hàng hóa |  |  | 6003036547 |  |
| 6003036548 | 返品手数料（販売） | Chi phí dịch vụ mua ngòai | 荷造運賃 | Chi phí vận chuyển hàng hóa |  |  | 6003036548 |  |
| 6003036549 | 保管料（販売） | Chi phí dịch vụ mua ngòai | 荷造運賃 | Chi phí vận chuyển hàng hóa |  |  | 6003036549 |  |
| 6003036550 | オーバーナイト費（販売） | Chi phí dịch vụ mua ngòai | 荷造運賃 | Chi phí vận chuyển hàng hóa |  |  | 6003036550 |  |
| 6003036551 | バンニング費（販売） | Chi phí dịch vụ mua ngòai | 荷造運賃 | Chi phí vận chuyển hàng hóa |  |  | 6003036551 |  |
| 6003036552 | その他物流費（販売） | Chi phí dịch vụ mua ngòai | 荷造運賃 | Chi phí vận chuyển hàng hóa | 6003036552 |  | 6003036552 |  |
| 6003036554 | 外部倉庫　取扱手数料（販売） | Chi phí dịch vụ mua ngòai | 荷造運賃 | Chi phí vận chuyển hàng hóa | 6003036554 | 6003036554 | 6003036554 | 2017年1月追加。 |
| 6003036555 | 外部倉庫　保管料（販売） | Chi phí dịch vụ mua ngòai | 荷造運賃 | Chi phí vận chuyển hàng hóa | 6003036555 | 6003036555 | 6003036555 | 2017年1月追加。 |
| 6003036556 | 外部倉庫　輸送料（販売） | Chi phí dịch vụ mua ngòai | 荷造運賃 | Chi phí vận chuyển hàng hóa | 6003036556 | 6003036556 | 6003036556 | 2017年1月追加。 |
| 6003036557 | 外部物流業者　取扱手数料（販売） | Chi phí dịch vụ mua ngòai | 荷造運賃 | Chi phí vận chuyển hàng hóa | 6003036557 | 6003036557 | 6003036557 | 2017年1月追加。 |
| 6004096541 | 求人費（販売） | Chi phí dịch vụ mua ngòai | 募集教育費 | Chi phí tuyển dụng,đào tạo |  |  | 6004096541 |  |
| 6005056541 | 電気代（販売） | Chi phí dịch vụ mua ngòai | 水道光熱費 | Chi phí Utilities(điện,nước..) |  |  | 6005056541 |  |
| 6005056542 | 水道代（販売） | Chi phí dịch vụ mua ngòai | 水道光熱費 | Chi phí Utilities(điện,nước..) |  |  | 6005056542 |  |
| 6005056543 | ガス代（販売） | Chi phí dịch vụ mua ngòai | 水道光熱費 | Chi phí Utilities(điện,nước..) |  |  | 6005056543 |  |
| 6005136541 | 通信費（販売） | Chi phí dịch vụ mua ngòai | 通信費 | Chi phí điện thoại |  |  | 6005136541 |  |
| 6005146541 | 図書印刷費（販売） | Chi phí dịch vụ mua ngòai | 図書及び事務費 | Chi phí văn phòng |  |  | 6005146541 |  |
| 6005146542 | ＫＤＣシステム使用料（販売） | Chi phí dịch vụ mua ngòai | 図書及び事務費 | Chi phí văn phòng |  |  | 6005146542 |  |
| 6005146543 | ライセンス料（販売） | Chi phí dịch vụ mua ngòai | 図書及び事務費 | Chi phí văn phòng |  |  | 6005146543 |  |
| 6005156541 | 広告宣伝費（販売） | Chi phí dịch vụ mua ngòai | 雑費 | Các loại chi phí bằng tiền khác |  |  | 6005156541 |  |
| 6005206541 | 会費（販売） | Chi phí dịch vụ mua ngòai | 会費及び会議費 | Chi phí cuộc họp |  |  | 6005206541 |  |
| 6005216541 | 委嘱報酬・設計委託費（販売） | Chi phí dịch vụ mua ngòai | 委嘱報酬 | Thù lao ủy thác,phí hoa hồng |  |  | 6005216541 |  |
| 6005226541 | 保険料（販売） | Chi phí dịch vụ mua ngòai | 保険料 | Chi phí bảo hiểm |  |  | 6005226541 |  |
| 6005236541 | 事務所賃借料（販売） | Chi phí dịch vụ mua ngòai | 賃借料 | Chi phí thuê |  |  | 6005236541 |  |
| 6005246541 | 取扱手数料（販売） | Chi phí dịch vụ mua ngòai | 手数料 | Tiền dịch vụ,tiền lệ phí |  |  | 6005246541 |  |
| 6005246542 | その他手数料 | Chi phí dịch vụ mua ngòai | 手数料 | Tiền dịch vụ,tiền lệ phí | 6005246542 | 6005246542 | 6005246542 |  |
| 6005246543 | ＫＤＣ手数料 | Chi phí dịch vụ mua ngòai | 手数料 | Tiền dịch vụ,tiền lệ phí | 6005246543 | 6005246543 | 6005246543 |  |
| 6005246544 | 事務用品費（販売） | Chi phí dịch vụ mua ngòai | 図書及び事務費 | Chi phí văn phòng |  |  | 6005246544 |  |
| 6004086551 | 福利厚生費（販売） | Chi phí bằng tiền khác | 福利厚生費 | Chi phí phúc lợi |  |  | 6004086551 |  |
| 6004086553 | 教育訓練費（販売） | Chi phí bằng tiền khác | 募集教育費 | Chi phí tuyển dụng,đào tạo |  |  | 6004086553 |  |
| 6005116551 | ベトナム国内交通費（販売） | Chi phí bằng tiền khác | 旅費交通費 | Chi phí di chuyển |  |  | 6005116551 |  |
| 6005116552 | 海外渡航費（販売） | Chi phí bằng tiền khác | 渡航費 | Chi phí di chuyển(nước ngoài) |  |  | 6005116552 |  |
| 6005136551 | 郵送代（販売） | Chi phí bằng tiền khác | 通信費 | Chi phí điện thoại |  |  | 6005136551 |  |
| 6005166551 | 接待交際費（販売） | Chi phí bằng tiền khác | 接待交際費 | Chi phí tiếp khách |  |  | 6005166551 |  |
| 6005186552 | その他税金（販売） | Chi phí bằng tiền khác | 公租公課 | Thuế,phí công cộng |  |  | 6005186552 |  |
| 6005246551 | 会議費（販売） | Chi phí bằng tiền khác | 会費及び会議費 | Chi phí cuộc họp |  |  | 6005246551 |  |
| 6005246552 | 雑費（販売） | Chi phí bằng tiền khác | 雑費 | Các loại chi phí bằng tiền khác |  |  | 6005246552 |  |
| 6005246553 | 棚卸減耗費（販売） | Chi phí bằng tiền khác | 棚卸減耗費 | Chi phí hao hụt sau kiểm kê |  |  | 6005246553 |  |
| 6004046421 | 雑給（一般） | Chi phí nhân viên quản lý | 雑給 | Chi phí nhân công trực tiếp |  | 6004046421 |  |  |
| 6005016422 | 消耗品費（一般） | Chi phí vật liệu quản lý | 消耗品費 | Chi phí hàng hóa tiêu hao |  | 6005016422 |  | 2017年1月変更。 |
| 6005016423 | 消耗備品費（一般） | Chi phí vật liệu quản lý | 消耗工具器具備品費 | Chi phí sử dụng công cụ,đồ đạc |  | 6005016423 | 6005016423 | 2017年1月追加。 |
| 6005126423 | 事務用品費（一般） | Chi phí đồ dùng văn phòng | 図書及び事務費 | Chi phí văn phòng |  | 6005126423 |  |  |
| 6006016611 | 減価償却費（一般）　建物 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  | 6006016611 |  |  |
| 6006016612 | 減価償却費（一般）　車輌運搬具 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  | 6006016612 |  |  |
| 6006016613 | 減価償却費（一般）　工具器具備品 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  | 6006016613 |  |  |
| 6006016614 | 減価償却費（一般）　構築物 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  | 6006016614 |  |  |
| 6006016615 | 減価償却費（一般）　その他有形固定資産 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  | 6006016615 |  |  |
| 6006016616 | 減価償却費（一般）　リース建物 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  | 6006016616 |  |  |
| 6006016617 | 減価償却費（一般）　リース車輌運搬具 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  | 6006016617 |  |  |
| 6006016618 | 減価償却費（一般）　リース工具器具備品 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  | 6006016618 |  |  |
| 6006016619 | 減価償却費（一般）　リース構築物 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  | 6006016619 |  |  |
| 6006016620 | 減価償却費（一般）　土地使用権 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  | 6006016620 |  |  |
| 6006016621 | 減価償却費（一般）　出版著作権 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  | 6006016621 |  |  |
| 6006016622 | 減価償却費（一般）　特許権 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  | 6006016622 |  |  |
| 6006016623 | 減価償却費（一般）　商標権 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  | 6006016623 |  |  |
| 6006016624 | 減価償却費（一般）　ソフトウェア | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  | 6006016624 |  |  |
| 6006016625 | 減価償却費（一般）　営業権 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  | 6006016625 |  |  |
| 6006016626 | 減価償却費（一般）　その他無形固定資産 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  | 6006016626 |  |  |
| 6006016627 | 減価償却費（一般）　差異調整 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  | 6006016627 |  |  |
| 6006016628 | 減価償却費配賦（一般）　建物 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  | 6006016628 |  |  |
| 6006016629 | 減価償却費配賦（一般）　土地使用権 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  | 6006016629 |  |  |
| 6006016630 | 減価償却費（一般）機器装置 | Chi phí khấu hao TSCĐ | 減価償却費 | Chi phí khấu hao |  | 6006016630 |  | Thêm từ tháng 12/2024 |
| 6005186425 | 外国契約者税（一般） | Thuế phí và lệ phí | 公租公課 | Thuế,phí công cộng |  | 6005186425 |  |  |
| 6005186429 | その他税金（一般） | Thuế phí và lệ phí | 公租公課 | Thuế,phí công cộng |  | 6005186429 |  |  |
| 6005266426 | 貸倒引当金繰入（一般） | Chi phí dự phòng | 雑費 | Các loại chi phí bằng tiền khác |  | 6005266426 |  |  |
| 6004096621 | 求人費（一般） | Chi phí dịch vụ mua ngoài | 募集教育費 | Chi phí tuyển dụng,đào tạo |  | 6004096621 |  |  |
| 6005046622 | 修繕費（一般） | Chi phí dịch vụ mua ngoài | 修繕費 | Chi phí sửa chữa |  | 6005046622 |  |  |
| 6005046635 | 保守料（一般） | Chi phí dịch vụ mua ngoài | 修繕費 | Chi phí sửa chữa |  | 6005046635 |  |  |
| 6005056623 | 電気代（一般） | Chi phí dịch vụ mua ngoài | 水道光熱費 | Chi phí Utilities(điện,nước..) |  | 6005056623 |  |  |
| 6005056624 | 水道代（一般） | Chi phí dịch vụ mua ngoài | 水道光熱費 | Chi phí Utilities(điện,nước..) |  | 6005056624 |  |  |
| 6005056625 | ガス代（一般） | Chi phí dịch vụ mua ngoài | 水道光熱費 | Chi phí Utilities(điện,nước..) |  | 6005056625 |  |  |
| 6005136626 | 通信費（一般） | Chi phí dịch vụ mua ngoài | 通信費 | Chi phí điện thoại |  | 6005136626 |  |  |
| 6005146627 | 図書印刷費（一般） | Chi phí dịch vụ mua ngoài | 図書及び事務費 | Chi phí văn phòng |  | 6005146627 |  |  |
| 6005146628 | ＫＤＣシステム使用料（一般） | Chi phí dịch vụ mua ngoài | 図書及び事務費 | Chi phí văn phòng |  | 6005146628 |  |  |
| 6005146629 | ライセンス料（一般） | Chi phí dịch vụ mua ngoài | 図書及び事務費 | Chi phí văn phòng |  | 6005146629 |  |  |
| 6005156630 | 広告宣伝費（一般） | Chi phí dịch vụ mua ngoài | 雑費 | Các loại chi phí bằng tiền khác |  | 6005156630 |  |  |
| 6005206631 | 会費（一般） | Chi phí dịch vụ mua ngoài | 会費及び会議費 | Chi phí cuộc họp |  | 6005206631 |  |  |
| 6005216632 | 委嘱報酬・設計委託費（一般） | Chi phí dịch vụ mua ngoài | 委嘱報酬 | Thù lao ủy thác,phí hoa hồng |  | 6005216632 |  |  |
| 6005226633 | 保険料（一般） | Chi phí dịch vụ mua ngoài | 保険料 | Chi phí bảo hiểm |  | 6005226633 |  |  |
| 6005236634 | 事務所賃借料（一般） | Chi phí dịch vụ mua ngoài | 賃借料 | Chi phí thuê |  | 6005236634 |  |  |
| 6005246636 | 取扱手数料（一般） | Chi phí dịch vụ mua ngoài | 手数料 | Tiền dịch vụ,tiền lệ phí |  | 6005246636 |  |  |
| 6005246672 | 銀行手数料（一般） | Chi phí dịch vụ mua ngoài | 手数料 | Tiền dịch vụ,tiền lệ phí |  | 6005246672 |  |  |
| 6005246673 | その他手数料（一般） | Chi phí dịch vụ mua ngoài | 手数料 | Tiền dịch vụ,tiền lệ phí |  | 6005246673 |  |  |
| 6005246674 | ＫＤＣ手数料（一般） | Chi phí dịch vụ mua ngoài | 手数料 | Tiền dịch vụ,tiền lệ phí |  | 6005246674 |  |  |
| 6004086651 | 福利厚生費（一般） | Chi phí bằng tiền khác | 福利厚生費 | Chi phí phúc lợi |  | 6004086651 |  |  |
| 6004086653 | 教育訓練費（一般） | Chi phí bằng tiền khác | 募集教育費 | Chi phí tuyển dụng,đào tạo |  | 6004086653 |  |  |
| 6005116654 | ベトナム国内交通費（一般） | Chi phí bằng tiền khác | 旅費交通費 | Chi phí di chuyển |  | 6005116654 |  |  |
| 6005116655 | 海外渡航費（一般） | Chi phí bằng tiền khác | 渡航費 | Chi phí di chuyển(nước ngoài) |  | 6005116655 |  |  |
| 6005136657 | 郵送代（一般） | Chi phí bằng tiền khác | 通信費 | Chi phí điện thoại |  | 6005136657 |  |  |
| 6005166658 | 接待交際費（一般） | Chi phí bằng tiền khác | 接待交際費 | Chi phí tiếp khách |  | 6005166658 |  |  |
| 6005176659 | 寄付金（一般） | Chi phí bằng tiền khác | 雑費 | Các loại chi phí bằng tiền khác |  | 6005176659 |  |  |
| 6005246671 | 雑費（一般） | Chi phí bằng tiền khác | 雑費 | Các loại chi phí bằng tiền khác |  | 6005246671 |  |  |
| 6005246675 | 会議費（一般） | Chi phí bằng tiền khác | 会費及び会議費 | Chi phí cuộc họp |  | 6005246675 |  |  |
| 6005246676 | 開発費振替勘定（一般） | Chi phí bằng tiền khác | 雑費 | Các loại chi phí bằng tiền khác |  | 6005246676 |  | 2月から追加する→9/2015からｘから雑費になった |
| 8001017111 | 固定資産売却益 | Thu nhập khác | 特別利益 | Lợi nhuận đặc biệt | 8001017111 | 8001017111 | 8001017111 |  |
| 8001027111 | 前期損益修正益 | Thu nhập khác | 特別利益 | Lợi nhuận đặc biệt | 8001027111 | 8001027111 | 8001027111 |  |
| 8001037111 | その他特別利益 | Thu nhập khác | 特別利益 | Lợi nhuận đặc biệt | 8001037111 | 8001037111 | 8001037111 |  |
| 7002048111 | 雑損失 | Chi phí khác | 雑損失 | Tổn thất,lỗ khác | 7002048111 | 7002048111 | 7002048111 |  |
| 7002048112 | 棚卸資産廃棄損 | Chi phí khác | 棚卸資産廃棄損 | Tổn thất tài sản hư hỏng sau kiểm kê | 7002048112 | 7002048112 | 7002048112 |  |
| 8002018111 | 固定資産売却損・除却損 | Chi phí khác | 特別損失 | Lỗ đặc biệt | 8002018111 | 8002018111 | 8002018111 |  |
| 8002028111 | 前期損益修正損 | Chi phí khác | 特別損失 | Lỗ đặc biệt | 8002028111 | 8002028111 | 8002028111 |  |
| 8002038111 | その他特別損失 | Chi phí khác | 特別損失 | Lỗ đặc biệt | 8002038111 | 8002038111 | 8002038111 |  |
| 9114120002 | 社外出荷 |  | 社外出荷 | Xuất hàng ra ngoài | 9114120002 | 9114120002 | 9114120002 |  |
| 9114120004 | 社内売 |  | 社内売 | Bán hàng nội bộ | 9114120004 | 9114120004 | 9114120004 |  |
| 9114120005 | 支払営業口銭 |  | 営業経費 | Chi phí hoạt động | 9114120005 | 9114120005 | 9114120005 |  |
| 9114120006 | 材料費(指図出庫） |  | 材料費 | Chi phí nguyên vật liệu | 9114120006 | 9114120006 | 9114120006 |  |
| 9114120007 | 社内金利（固定資産） |  | 固定資産金利 | Lãi suất tài sản cố định | 9114120007 | 9114120007 | 9114120007 |  |
| 9114120008 | 仕入製商品費 |  | 仕入製商品費 | Chi phí bán hàng | 9114120008 |  |  |  |
| 9114120009 | 社内金利（在庫） |  | 在庫金利 | Lãi suất tồn kho | 9114120009 | 9114120009 | 9114120009 |  |
| 9114120011 | 内部諸経費 |  | 内部諸経費 | Chi phí nội bộ | 9114120011 | 9114120011 | 9114120011 |  |
| 9114120014 | 社内買 |  | 社内買 | Mua hàng nội bộ | 9114120014 | 9114120014 | 9114120014 |  |
| 9114120018 | 部内間接経費 |  | 部内間接経費 | Chi phí trong bộ phận(gián tiếp) | 9114120018 | 9114120018 | 9114120018 |  |
| 9114120021 | 工場間接経費 |  | 工場間接経費 | Chi phí nhà máy(gián tiếp)  | 9114120021 | 9114120021 | 9114120021 |  |
| 9114120028 | 社内システム使用料 |  | 社内システム使用料 | Phí sử dụng phần mềm nội bộ | 9114120028 | 9114120028 | 9114120028 |  |
| 9114120029 | 部外間接経費1 |  | 部外間接経費1 | Chi phí ngoài bộ phận(gián tiếp 1) | 9114120029 | 9114120029 | 9114120029 |  |
| 9114120030 | 部外間接経費2 |  | 部外間接経費2 | Chi phí ngoài bộ phận(gián tiếp 2) | 9114120030 | 9114120030 | 9114120030 |  |
## Sheet: 原価センタ
| 原価センタ | テキスト | No. | 採算区分 | 原価区分 |
| --- | --- | --- | --- | --- |
| 1412000004 | 機器製造1課 | 1. | 製造 | 製造 |
| 1412000005 | 機器製造2課 | 2. | 製造 | 製造 |
| 1412000081 | 機器製造3課 | 52. | 製造 | 製造 |
| 1412000066 | RPS製造課 | 39. | 製造 | 製造 |
| 1412000034 | トナー製造課 | 4. | 製造 | 製造 |
| 1412000056 | 部品製造課 | 23. | 製造 | 製造 |
| 1412000050 | MD1課 | 7. | 製造 | 製造 |
| 1412000077 | MD2課 | 8. | 製造 | 製造 |
| 1412000083 | MD3課 | 53. | 製造 | 製造 |
| 1412000057 | EI1課 | 49. | 製造 | 製造 |
| 1412000078 | ESD1課 | 50. | 製造 | 製造 |
| 1412000062 | 機器製造管理課 | 3. | 部内間接 | 製造 |
| 1412000036 | 部品管理1課 | 13. | 部内間接 | 製造 |
| 1412000103 | 部品管理2課 | 69. | 部内間接 | 製造 |
| 1412000063 | トナー製造管理課 | 38. | 部内間接 | 製造 |
| 1412000048 | トナー生産技術課 | 5. | 部内間接 | 製造 |
| 1412000055 | トナー品質管理課 | 6. | 部内間接 | 製造 |
| 1412000073 | 物流管理課 | 46. | 部内間接 | 製造 |
| 1412000008 | 生産管理課 | 10. | 部内間接 | 製造 |
| 1412000094 | 部品在庫管理課 | 61. | 部内間接 | 製造 |
| 1412000080 | 部品技術課 | 20. | 部内間接 | 製造 |
| 1412000087 | 部品製造管理課 | 55. | 部内間接 | 製造 |
| 1412000088 | 品質管理課 | 56. | 部内間接 | 製造 |
| 1412000072 | 製品管理課 | 45. | 部内間接 | 販売 |
| 1412000053 | 工程品質管理1課 | 9. | 部内間接 | 製造 |
| 1412000104 | 工程品質管理2課 | 47. | 部内間接 | 製造 |
| 1412000105 | 工程品質管理3課 | 70. | 部内間接 | 製造 |
| 1412000075 | 工程品質管理4課 | 71. | 部内間接 | 製造 |
| 1412000044 | 金型技術課 | 22. | 部内間接 | 製造 |
| 1412000054 | マスター管理課 | 12. | 部外間接1 | 製造 |
| 1412000010 | 採算管理課 | 11. | 部外間接1 | 製造 |
| 1412000013 | 部品検査1課 | 18. | 部外間接1 | 製造 |
| 1412000092 | 部品検査2課 | 59. | 部外間接1 | 製造 |
| 1412000035 | 部品品質管理1課 | 40. | 部内間接 | 製造 |
| 1412000108 | 部品品質管理2課 | 74. | 部内間接 | 製造 |
| 1412000006 | メカ製造技術1課 | 14. | 部外間接1 | 製造 |
| 1412000089 | メカ製造技術2課 | 15. | 部外間接1 | 製造 |
| 1412000040 | 電気製造技術課 | 16. | 部外間接1 | 製造 |
| 1412000106 | 製造システム開発課 | 72. | 部外間接1 | 製造 |
| 1412000039 | 製造技術管理課 | 73. | 部外間接1 | 製造 |
| 1412000016 | 生産技術1課 | 42. | 部外間接1 | 製造 |
| 1412000069 | 生産技術2課 | 43. | 部外間接1 | 製造 |
| 1412000084 | 生産技術3課 | 54. | 部外間接1 | 製造 |
| 1412000018 | 品質保証課 | 24. | 部外間接2 | 製造 |
| 1412000019 | 製品保証課 | 25. | 部外間接2 | 製造 |
| 1412000058 | 第1資材課 | 26. | 部外間接2 | 製造 |
| 1412000042 | 第2資材課 | 27. | 部外間接2 | 製造 |
| 1412000021 | 第3資材課 | 28. | 部外間接2 | 製造 |
| 1412000070 | 第4資材課 | 44. | 部外間接2 | 製造 |
| 1412000022 | 資材管理課 | 29. | 部外間接2 | 製造 |
| 1412000024 | 総務課 | 30. | 工場間接 | 一般 |
| 1412000025 | 人事課 | 31. | 工場間接 | 一般 |
| 1412000026 | 施設課 | 32. | 工場間接 | 一般 |
| 1412000093 | リスクマネジメント課 | 60. | 工場間接 | 一般 |
| 1412000028 | 会計課 | 33. | 工場間接 | 一般 |
| 1412000029 | 経営管理課 | 34. | 工場間接 | 一般 |
| 1412000091 | 保安課 | 58. | 工場間接 | 一般 |
| 1412000086 | 情報システム課 | 36. | 工場間接 | 一般 |
| 1412C00001 | 労働組合 | 51. |  |  |
| 1412000030 | 貿易管理課 | 35. | 工場間接 | 販売 |
| 1412000098 | 電工製造課 | 64. | 製造 | 製造 |
| 1412000096 | ESD2課 | 63. | 製造 | 製造 |
| 1412000099 | MD4課 | 65. | 製造 | 製造 |
| 1412000100 | MD5課 | 68. | 製造 | 製造 |
| 1412000101 | EI2課 | 66. | 製造 | 製造 |