# Tài liệu yêu cầu: Cải tiến nhập dữ liệu chung vào file MPnew.xlsx

- **Nguồn file**: `raw/Cải tiến nhập dữ liệu chung vào file MPnew.xlsx`
- **Số lượng sheet**: 10
- **Danh sách sheet**: Sheet1, Hạng mục cần cải tiến, Chi phí hệ thống, Chi phí khấu hao, lãi nhà đất, Chi phí tài sản cố định, Chi phí làm giấy tờ cho NNN, Chi phí sinh nhật, Chi phí phân bổ từ hành chính , 勘定科目, 原価センタ

## Sheet: Sheet1
- Kích thước sheet: 55 dòng x 2 cột

**Dòng 1 (Cột 1)**: Cải tiến nhập tự động dữ liệu chung từ các file được cung cấp sẵn vào file Master Plan

### 1. Tổng quan file

### 2. Các file dữ liệu chi phí chung được cung cấp

**Dòng 40 (Cột 2)**: Chi phí hệ thống

**Dòng 42 (Cột 2)**: Chi phí khấu hao, lãi nhà đất, điện nước

**Dòng 44 (Cột 2)**: Chi phí tài sản cố định

**Dòng 46 (Cột 2)**: Chi phí phân bổ từ hành chính

### 3. Nhập dữ liệu lấy từ các file vào ô cần điền trong file MP

**Dòng 52 (Cột 2)**: Hình dung cách làm:

① Filter "code phòng chịu chi phí" trong các file chi phí chung

② Filter "code tài khoản chịu chi phí", "tên tài khoản chịu chi phí", "ghi chú" trong file MP đối tượng

③ Nhập dữ liệu từ mục ① vào ② (theo công thức hoặc paster nguyên số)


---

## Sheet: Hạng mục cần cải tiến
- Kích thước sheet: 186 dòng x 11 cột

**Dòng 1 (Cột 1)**: Những hạng mục cần cải tiến

### 1. Không cần điền 2 dữ liệu dưới vào file

### 2. Đẩy các cột dữ liệu ghi dưới về cột chỉ mũi tên ghi dưới

### 3. Bôi lại đúng màu, đúng định dạng như FORM vốn có

### 4. Để lại tất cả các công thức tính

**Dòng 45 (Cột 1)**: Chi tiết đã ghi ở từng sheet

**Dòng 46 (Cột 1)**: VD:

### 5. Sai code chi phí hệ thống

### 6. Nhập đồng thời số người của 12 tháng, riêng tháng 12 hiển thị nhập số lượng Nam, Nữ (để nhập chi phí khám sức khỏe)

**Dòng 91 (Cột 1)**: Ngoài ra, do phần mềm dùng lâu dài nên ở mục khoanh đỏ ghi dưới, thay vì để 202704, 202705,…, hãy để thành Tháng 4, Tháng 5,…..

### 7.Bổ sung thêm hạng mục ở Sheet Chi phí phân bổ từ hành chính

**Dòng 110 (Cột 2)**: LINK

=> Những dòng, sheet bôi màu xám là đã được thực hiện

**Dòng 113 (Cột 1)**: Sheet không bôi màu là sheet vẫn chưa được thực hiện

**Dòng 114 (Cột 1)**: Sheet màu đỏ là nội dung mới

**Dòng 116 (Cột 1)**: Ngày 9/4:

### 1. Chi phí hệ thống chưa lấy được công thức, vẫn là dạng số

=> Công thức tính bị sai nên tổng tiền không khớp với số tiền đúng như IT liên lạc (số tiền ở bản ghi trên thì đúng)

**Dòng 138 (Cột 2)**: Công thức: = ROUND(công thức của các chi phí + với nhau** tỷ giá $ (ô B2 trong file MP),0)

**Dòng 139 (Cột 2)**: VD: phòng code 1412000006 = ROUND((11*3.19 + 12*11.51+1*153.91+2*2114.25+12*2.25)*26273,0)=120,399,175 (chi phí tổng ở sheet đầu tiên là 120,399,176)

### 2. Sửa lại đối tượng áp dụng và công thức tính tiền phân bổ từ hành chính

**Dòng 144 (Cột 2)**: LINK

**Dòng 146 (Cột 1)**: Ngoài ra, bổ sung thêm những hạng mục ở bên dưới

**Dòng 147 (Cột 2)**: LINK

### 3. Bổ sung thêm 1 loại chi phí mới: Chi phí làm giấy tờ cho người nước ngoài

**Dòng 150 (Cột 2)**: LINK

**Dòng 152 (Cột 1)**: A làm chi phí phân bổ từ hành chính và chi phí làm giấy tờ cho người nước ngoài trước giúp e nhé.

**Dòng 153 (Cột 1)**: Còn chi phí tài sản cố định hơi khó nên để tuần sau a làm cũng được nha.

**Dòng 156 (Cột 1)**: Liên quan đến nhập số người,

**Dòng 157 (Cột 1)**: Thay vì nhập số người của 12 tháng như hiện tại thì sẽ nhập những dữ liệu ghi dưới

- Số người JP (xe bus) (dùng chung cho 12 tháng)

- Số người VN (xe bus) (dùng chung cho 12 tháng)

- Tháng 3 FY cũ (tiền triết lý)

- Tháng 4 (tiệc chúc mừng sau buổi phát biểu phương châm bộ phận)

- Tháng 5 (du lịch)

- Tháng 6 (người ko đi du lịch được quà)

- Tháng 10

・Quà kỉ niệm 10 năm

・Tiệc kỷ niệm 10 năm gắn bó

- Tháng 12: (đã có)

・Nam:

・Nữ:

**Dòng 171 (Cột 1)**: Xóa nội dung dưới đây cho ko cần thiết

**Dòng 179 (Cột 1)**: Điền dữ liệu theo thứ tự dưới đây:

**Dòng 180 (Cột 2)**: Ngoài ra, thứ tự các chi phí của từng file thì ghi trong từng sheet bên cạnh

**Dòng 182 (Cột 8)**: 6 chi phí

**Dòng 186 (Cột 11)**: gộp thành 1 dòng chi phí


---

## Sheet: Chi phí hệ thống
- Kích thước sheet: 97 dòng x 9 cột

**Dòng 1 (Cột 1)**: Chi phí hệ thống

### 1. Tổng quan file: có nhiều sheet

### 2. Các sheet chi tiết

**Dòng 43 (Cột 1)**: Ví dụ: Chi tiết chi phí VPN

**Dòng 44 (Cột 2)**: Các thông tin cần lấy dữ liệu như dưới:

**Dòng 45 (Cột 2)**: Công thức: = số người * Đơn giá

**Dòng 46 (Cột 2)**: VD: Phòng code 141200006 = 11*3.19

**Dòng 47 (Cột 1)**: Các sheet còn lại tương tự công thức như vậy

### 3. Tổng chi phí hệ thống

**Dòng 85 (Cột 1)**: Công thức: = ROUND(công thức của các chi phí + với nhau** tỷ giá $ (ô B2 trong file MP),0)

**Dòng 86 (Cột 1)**: VD: phòng code 1412000006 = ROUND((11*3.19 + 12*11.51+1*153.91+2*2114.25+12*2.25)*26273,0)=120,399,175 (chi phí tổng ở sheet đầu tiên là 120,399,176)

=> Do có chút chênh lệch về tỷ giá sẽ có trường hợp lệch 1 vài đồng so với chi phí ở sheet đầu tiên (sheet tổng các chi phí) như trên

**Dòng 89 (Cột 1)**: Nhập vào 1 dòng duy nhất

### 4. Cách làm

① Filter "code phòng chịu chi phí" của từng sheet

② Nhập công thức sau khi lấy được tất cả các dữ liệu của từng sheet

③ So sánh tổng công hức đã nhập với tổng chi phí của sheet tổng

**Dòng 96 (Cột 2)**: ④ Điều chỉnh cho khớp với tổng chi phí của sheet tổng nếu lệch 1 vài đồng do tỷ giá (ko cần đưa làm lưu trình nếu làm tự động)

**Dòng 97 (Cột 2)**: ⑤ Xác nhận số người cần dự tính của từng tháng để nhập cho các tháng (ví dụ: người nghỉ sinh,…)


---

## Sheet: Chi phí khấu hao, lãi nhà đất
- Kích thước sheet: 131 dòng x 17 cột

**Dòng 1 (Cột 1)**: Chi phí khấu hao, lãi nhà đất, điện nước

### 1. Tổng quan file: gồm 3 loại chi phí: khấu hao nhà đất, lãi nhà đất, điện-nước

### 2. Các sheet chi phí trong file dữ liệu

### 2.1. Sheet chi phí khấu hao nhà, đất

- **Dòng 62**: Cột 1: `Cách làm:`; Cột 2: `① Tìm "code phòng chịu chi phí" để lấy dữ liệu (filter có khả năng mất dòng khấu hao đất nên làm thủ công thì ko filter)`
② Nhập công thức

**Dòng 64 (Cột 2)**: Khấu hao nhà:

- **Dòng 65**: Cột 2: `Công thức = ROUND (chi phí khấu hao nhà * tỷ giá $(ô B2 trong file MP),0)`; Cột 10: `Thứ tự 1`
**Dòng 66 (Cột 2)**: Khấu hao đất:

- **Dòng 67**: Cột 2: `Công thức = ROUND (chi phí khấu hao đất * tỷ giá $(ô B2 trong file MP),0)`; Cột 10: `Thứ tự 2`
③ Phải nhập cho tất cả các tháng

### 2.2. Sheet chi phí lãi nhà, đất

- **Dòng 95**: Cột 1: `Cách làm:`; Cột 2: `① Tìm "code phòng chịu chi phí" để lấy dữ liệu (filter có khả năng mất dòng lãi đất nên làm thủ công thì ko filter)`
② Nhập công thức

**Dòng 97 (Cột 2)**: Lãi nhà:

- **Dòng 98**: Cột 2: `Công thức = ROUND (chi phí lãi nhà * tỷ giá $(ô B2 trong file MP),0)`; Cột 10: `Thứ tự 3`
**Dòng 99 (Cột 2)**: Lãi đất:

- **Dòng 100**: Cột 2: `Công thức = ROUND (chi phí lãi đất * tỷ giá $(ô B2 trong file MP),0)`; Cột 10: `Thứ tự 4`
③ Phải nhập cho tất cả các tháng

### 2.2. Sheet điện-nước

- **Dòng 127**: Cột 1: `Cách làm:`; Cột 2: `① Tìm "code phòng chịu chi phí" để lấy dữ liệu (filter có khả năng mất dòng lãi đất nên làm thủ công thì ko filter)`
② Copy/paste dữ liệu điện+nước

- **Dòng 129**: Cột 2: `Tiền điện`; Cột 3: `Thứ tự 5`
- **Dòng 131**: Cột 2: `Tiền nước`; Cột 3: `Thứ tự 6`

---

## Sheet: Chi phí tài sản cố định
- Kích thước sheet: 66 dòng x 21 cột

**Dòng 1 (Cột 1)**: Chi phí tài sản cố định (TSCĐ)

### 1. Tổng quan file:

### 2. Cách làm

① Filter "code phòng chịu chi phí"

② Xác nhận"tháng khấu hao cuối cùng" có trong kỳ FY đó ko, nếu ko thì nhập theo bước ③,④ dưới đây, nếu có thì thực hiện từ bước ⑤ trở đi

- **Dòng 44**: Cột 2: `③ Lấy dữ liệu chi phí khấu hao rồi nhập theo công thức = ROUND(chi phí khấu hao * tỷ giá $ (ô B2 trong file MP),0)`; Cột 14: `Nhập vào dòng 38, từ F38 => Q38 vào file FORM`
- **Dòng 45**: Cột 2: `④ Lấy dữ liệu chi phí lãi rồi nhập theo công thức =ROUND(chi phí lãi * tỷ giá $ (ô B2 trong file MP),0)`; Cột 14: `Nhập vào dòng 42, từ F42 => Q42 vào file FORM`
**Dòng 46 (Cột 2)**: (Cột chi phí lãi có 2 loại: tháng 4 và từ tháng 5 trở đi=> lấy dữ liệu của từng ô để nhập tương ứng cho từng tháng)

- **Dòng 47**: Cột 2: `VD:`; Cột 3: `No.1: Tháng khấu hao cuối cùng No.3 là 11/2027 thì nhập theo công thức trên cho tất cả các tháng`
**Dòng 48 (Cột 2)**: ⑤ Các tháng trước tháng cuối cùng thì điền chi phí khấu hao, lãi giống như bước ③ và ④

**Dòng 49 (Cột 2)**: ⑥ Vào tháng khấu hao cuối cùng, lấy giá trị của trong cột "tháng khấu hao cuối cùng"

- **Dòng 50**: Cột 2: `VD:`; Cột 3: `No.3: Tháng khấu hao cuối cùng là 5/2026`
**Dòng 51 (Cột 4)**: Đối với chi phí khấu hao

**Dòng 52 (Cột 5)**: Tháng 4 làm theo bước ③

**Dòng 53 (Cột 5)**: Tháng 5 = ROUND( "chi phí khấu hao của tháng cuối cùng" * tỷ giá $ (ô B2 trong file MP),0)

**Dòng 54 (Cột 5)**: Từ tháng 6 đến hết: không phải điền

**Dòng 55 (Cột 4)**: Đối với chi phí lãi

**Dòng 56 (Cột 5)**: Tháng 4~5: Làm theo bước ④

**Dòng 57 (Cột 5)**: Từ tháng 6 đến hết: không phải điền

**Dòng 59 (Cột 3)**: No.23: Tháng khấu hao cuối cùng là 11/2026

**Dòng 60 (Cột 4)**: Đối với chi phí khấu hao

**Dòng 61 (Cột 5)**: Tháng 4~10 làm theo bước ③

**Dòng 62 (Cột 5)**: Tháng 11 = ROUND( "chi phí khấu hao của tháng cuối cùng" * tỷ giá $ (ô B2 trong file MP),0)

**Dòng 63 (Cột 5)**: Từ tháng 12 đến hết: không phải điền

**Dòng 64 (Cột 4)**: Đối với chi phí lãi

**Dòng 65 (Cột 5)**: Tháng 4~11: Làm theo bước ④

**Dòng 66 (Cột 5)**: Từ tháng 12 đến hết: không phải điền


---

## Sheet: Chi phí làm giấy tờ cho NNN
- Kích thước sheet: 24 dòng x 17 cột

**Dòng 1 (Cột 1)**: Chi phí làm giấy tờ cho NNN

- **Dòng 18**: Cột 1: `Cách làm:`; Cột 2: `① Filter code tài khoản mong muốn tại cột "Code tài khoản chịu chi phí"`
- **Dòng 19**: Cột 2: `② Nhập số tiền của các tháng hiện ra ở file trên vào các cột tháng tương ứng ở file FORM`; Cột 11: `Nhập vào dòng 137, từ F137 => Q137 vào file FORM`
**Dòng 21 (Cột 2)**: VD:

- Lọc code 1412000018 ghi dưới

- Có 2 người cùng ở code đó, và các mỗi người thì chi phí thì phân bổ rải rác vào nhiều tháng như dưới

- Lấy tất cảt các chi phí đó nhập vào FORM


---

## Sheet: Chi phí sinh nhật
- Kích thước sheet: 48 dòng x 16 cột

**Dòng 1 (Cột 1)**: Chi phí sinh nhật

- **Dòng 20**: Cột 1: `Cách làm:`; Cột 2: `① Filter code tài khoản mong muốn tại cột "Code tài khoản chịu chi phí"`
② Lấy số người tương ứng với cột tháng

③ Filter cột nội dung của file "FY2027配賦額一覧" với nội dung: 誕生日会 Tiệc sinh nhật

- **Dòng 23**: Cột 2: `cách lấy mã code giống như ở đây →`; Cột 6: `LINK`
- **Dòng 24**: Cột 2: `④ Nhập vào dòng 63 (từ G63=>  Q63)`; Cột 9: `Nhập vào dòng 59, từ F59 => Q59 vào file FORM`
**Dòng 25 (Cột 2)**: Công thức = số người * đơn giá

**Dòng 46 (Cột 2)**: ※ Ngoài ra, trong trường hợp tháng đó có người mới thì sẽ cộng luôn số người mới đó vào luôn

**Dòng 47 (Cột 2)**: VD: Tháng 6 phòng 1412000006 có 2 người sinh nhật, trong tháng đó có 1 người mới thì tổng số người sinh nhật trong tháng 6 sẽ là 3 người

**Dòng 48 (Cột 2)**: Công thức = (2 người(trong file ở đầu) + 1 người mới )* 152,000VND


---

## Sheet: Chi phí phân bổ từ hành chính 
- Kích thước sheet: 210 dòng x 19 cột

**Dòng 1 (Cột 1)**: Chi phí phân bổ từ hành chính

### 1. Chi phí phân bổ cho cả 12 tháng

- **Dòng 31**: Cột 1: `Cách làm:`; Cột 2: `① Điền các dữ liệu chi phí tương ứng vào ô chi phí trong file MP (áp dụng cho tiền gas, nước rửa tay, giấy vệ sinh, chi phí làm sạch)`
**Dòng 32 (Cột 2)**: Công thức = số người * chi phí tương ứng

**Dòng 33 (Cột 3)**: Số người: Tổng số người của tháng trước (Cũ: công thức = số người của tháng đó * chi phí tương ứng)

**Dòng 34 (Cột 3)**: Do ko có dữ liệu tháng 3 của kỳ trước nên số người của tháng 4 sẽ vẫn lấy tổng số người của tháng 4

### 2. Chi phí phân bổ đặc thù cho từng tháng

**Dòng 65 (Cột 1)**: ※Cách lấy mã đúng cho từng code phòng chịu chi phí

- **Dòng 66**: Cột 2: `Trong công ty chia ra 3 nhóm:`; Cột 4: `製造`
**Dòng 67 (Cột 4)**: 一般

**Dòng 68 (Cột 4)**: 販売

**Dòng 69 (Cột 2)**: Dựa vào 2 sheet dưới đây để lấy mã tài khoản cho đúng

- **Dòng 70**: Cột 3: `原価センタ`; Cột 10: `勘定科目`
**Dòng 92 (Cột 1)**: 社員旅行 Du lịch công ty: Tháng 5

① Xác nhận code phòng chi phí

**Dòng 94 (Cột 3)**: Được chọn ngay từ lúc nhập mã phòng trên phần mềm

**Dòng 95 (Cột 3)**: VD: Code 1412000089

② Xác nhận code phòng chi phí thuộc nhóm nào (製造、一般、販売）

- **Dòng 97**: Cột 3: `- Mở sheet này`; Cột 4: `原価センタ`
- Filter cột A1 như dưới

- Biết được thuộc nhóm 製造 như ô khoanh đỏ trên

③ Xác nhận nhóm đó thì sẽ là mã tài khoản nào

- Mở file "FY2027配賦額一覧" như dưới

- **Dòng 106**: Cột 3: `- Filter "社員旅行 Du lịch công ty" tại cột B "Nội dung 内容"`; Cột 8: `(Chú ý: Filter giống như đầu mục trước dấu 2 chấm)`; Cột 14: `☚ Bấm vô`
- Xác định tháng phân bổ: cột G màu xanh lá như dưới

- Lấy tên tài khoản ở khung đỏ xanh dương như dưới

- **Dòng 121**: Cột 3: `- Mở sheet này`; Cột 4: `勘定科目`
- Filter tên tài khoản "福利厚生費" (khung xanh dương ở trên) ở cột D "JP_Name" khung đỏ ở dưới

- Cột F, H, H tương ứng với 3 nhóm sẽ hiện ra các mã tài khoản tương ứng

- Ở mục ② ghi trên đã xác nhận được code chi phí phòng hiện tại đang làm là nhóm 製造, do đó sẽ lấy mã code theo cột F "製造", là khung tím ở dưới

**Dòng 133 (Cột 2)**: ④ Nhập mã tài khoản vào FORM tương ứng với tháng phân bổ đã xác định ở trên (tháng 5)

**Dòng 134 (Cột 2)**: ⑤ Nhập công thức= Số người * Đơn giá

**Dòng 135 (Cột 3)**: Số người: Số người nhập ban đầu khi mở phần mềm

**Dòng 136 (Cột 3)**: Đơn giá: Cột H của file "FY2027配賦額一覧" (màu hồng ở ảnh trên)

**Dòng 138 (Cột 1)**: Áp dụng cùng cách làm ghi trên cho các chi phí ghi dưới

**Dòng 141 (Cột 1)**: FY2027部門方針発表会後の決起コンパ  Tiệc chúc mừng sau buổi phát biểu phương châm bộ phận KDTVN FY2027: Tháng 4

**Dòng 142 (Cột 1)**: (có số người riêng)

**Dòng 143 (Cột 1)**: Tiệc khuấy động năm tài chính決起コンパ: Tháng 5

**Dòng 145 (Cột 1)**: 社員旅行不参加対象者へのギフト贈呈 Quà tặng cho CNV không thể tham gia du lịch: Tháng 6

**Dòng 146 (Cột 1)**: (có số người riêng)

**Dòng 147 (Cột 1)**: マイエピソード ～フィロソフィの実践～参加賞
Giải tham gia "Cảm nghĩ về triết lý kinh doanh": Tháng 7

**Dòng 148 (Cột 1)**: (có số người riêng)

**Dòng 149 (Cột 1)**: 京セラフェスティバルLễ hội Kyocera: Tháng 9

**Dòng 151 (Cột 1)**: 月餅 Bánh Trung Thu: Tháng 9

**Dòng 153 (Cột 1)**: 10年勤続記念コンパ Tiệc kỷ niệm 10 năm gắn bó: Tháng 10

**Dòng 154 (Cột 1)**: (có số người riêng)

**Dòng 155 (Cột 1)**: 10年勤続記念品 Quà kỷ niệm cho CNV 10 năm gắn bó: Tháng 10

**Dòng 156 (Cột 1)**: (có số người riêng)

**Dòng 158 (Cột 1)**: 会社設立記念 感謝イベント Sự kiện tri ân ngày thành lập công ty : Tháng 10

**Dòng 160 (Cột 1)**: ポケットカレンダー Lịch bỏ túi: Tháng 11

**Dòng 162 (Cột 1)**: 運動会 Đại hội thể thao: Tháng 11

**Dòng 164 (Cột 1)**: 忘年会補助金 Hỗ trợ tiệc tất niên: Tháng 2

**Dòng 166 (Cột 1)**: お年玉 Tiền lì xì: Tháng 2

**Dòng 170 (Cột 1)**: Khám sức khỏe (cho CNV nam):

**Dòng 171 (Cột 1)**: Khám sức khỏe (cho CNV nữ):

① → ④: Giống ghi trên

**Dòng 174 (Cột 2)**: ⑤ Nhập công thức= Số người * Đơn giá

**Dòng 175 (Cột 3)**: Số người: Số người nhập ban đầu khi mở phần mềm_chỗ tháng 12 đã chia rõ số người nam, nữ

**Dòng 176 (Cột 3)**: Đơn giá: Cột H của file "FY2027配賦額一覧" (đơn giá của nam, nữ tương ứng như dưới)

=> Để lại công thức cho e nhé

**Dòng 191 (Cột 1)**: Tiền chi phí cho người mới:

**Dòng 192 (Cột 2)**: Sẽ có tất cả những chi phí ở bảng dưới.

**Dòng 193 (Cột 2)**: Công thức và cách điền tháng như hiện tại đã đúng.

**Dòng 194 (Cột 2)**: Tuy nhiên, cần bổ sung thêm hạng mục bôi màu ghi dưới

・Sổ: chi phí của nhân biên và công nhân khác nhau

=> trường hợp có người mới là nhân viên thì sẽ nhập vào ô công nhân ở chỗ nhập nhân sự thủ công

- **Dòng 198**: Cột 6: `Công thức = số người nhân viên mới * đơn giá (9100VND)`; Cột 14: `Nhập vào dòng 97 vào file FORM`
=> trường hợp có người mới là công nhân thì sẽ nhập vào ô công nhân ở chỗ nhập nhân sự thủ công

- **Dòng 200**: Cột 6: `Công thức = số người công nhân mới * đơn giá (4000VND)`; Cột 14: `Nhập vào dòng 98 vào file FORM`
**Dòng 204 (Cột 2)**: ※Chú ý: Điểm chung của các chi phí dưới đây là ở cột Tháng phân bổ "入社月", tuy nhiên nếu filter thì sẽ bị mất dòng chi phí sổ của nhân viên nên a làm thế nào để lấy được đủ tiến cho e nhé

・Khám sức khỏe khi tuyển dụng

**Dòng 207 (Cột 3)**: Người mớ vào tháng này thì chi phí khám sưc khỏe tuyển dụng sẽ phân bổ vào tháng sau

- **Dòng 208**: Cột 3: `VD: Tháng 6 người mới vào thì chi phí khám sức khỏe sẽ phân bổ vào tháng 7`; Cột 11: `Nhập vào dòng 58 vào file FORM`
**Dòng 209 (Cột 3)**: Công thức = số người * đơn giá

**Dòng 210 (Cột 2)**: ※Chú ý: Chi phí khám sức khỏe khi tuyển dụng khác với chi phí khám sức khỏe định kỳ của công ty, do đó a đừng lấy nhầm chi phí nhé


---

## Sheet: 勘定科目
- Kích thước sheet: 244 dòng x 9 cột

- **Dòng 1**: Cột 1: `Account_Code`; Cột 2: `JPN (50cha)`; Cột 3: `Tiếng Việt_Tên tài khoản kế toán`; Cột 4: `JP_Name`; Cột 5: `Tiếng Việt_Hạng mục lợi nhuận`; Cột 6: `製造`; Cột 7: `一般`; Cột 8: `販売`; Cột 9: `REMARK`
- **Dòng 2**: Cột 6: `6`; Cột 7: `7`; Cột 8: `8`
- **Dòng 3**: Cột 1: `7001065118`; Cột 2: `雑収入`; Cột 3: `Doanh thu khác`; Cột 4: `雑収入`; Cột 5: `Thu nhập khác`; Cột 6: `7001065118`; Cột 7: `7001065118`; Cột 8: `7001065118`
- **Dòng 4**: Cột 1: `7001075118`; Cột 2: `雑収入（関係会社）`; Cột 3: `Doanh thu khác`; Cột 4: `雑収入`; Cột 5: `Thu nhập khác`; Cột 6: `7001075118`; Cột 7: `7001075118`; Cột 8: `7001075118`
- **Dòng 5**: Cột 1: `7001065119`; Cột 2: `固定資産売却勘定`; Cột 3: `Doanh thu khác`; Cột 4: `雑収入`; Cột 5: `Thu nhập khác`
- **Dòng 6**: Cột 1: `5001016131`; Cột 2: `材料仕入割戻高`; Cột 3: `Chi phí nguyên liệu, vật liệu trực tiếp`; Cột 4: `材料費`; Cột 5: `Chi phí nguyên vật liệu`; Cột 6: `5001016131`; Cột 9: `2016年4月から追加する。`
- **Dòng 7**: Cột 1: `5001016134`; Cột 2: `リーフレット用材料`; Cột 3: `Chi phí nguyên liệu, vật liệu trực tiếp`; Cột 4: `材料費`; Cột 5: `Chi phí nguyên vật liệu`; Cột 6: `5001016134`; Cột 7: `5001016134`; Cột 8: `5001016134`; Cột 9: `2017年1月変更。`
- **Dòng 8**: Cột 1: `5001016135`; Cột 2: `不良部品材料費`; Cột 3: `Chi phí nguyên liệu, vật liệu trực tiếp`; Cột 4: `材料費`; Cột 5: `Chi phí nguyên vật liệu`; Cột 6: `5001016135`; Cột 7: `5001016135`; Cột 8: `5001016135`
- **Dòng 9**: Cột 1: `5001016136`; Cột 2: `追加指図部品費`; Cột 3: `Chi phí nguyên liệu, vật liệu trực tiếp`; Cột 4: `材料費`; Cột 5: `Chi phí nguyên vật liệu`; Cột 6: `5001016136`; Cột 7: `5001016136`; Cột 8: `5001016136`
- **Dòng 10**: Cột 1: `5001016142`; Cột 2: `加工中不良廃棄損`; Cột 3: `Chi phí nguyên liệu, vật liệu trực tiếp`; Cột 4: `仕掛仕損`; Cột 5: `Sản phẩm chưa hoàn thiện,hỏng`; Cột 6: `5001016142`; Cột 7: `5001016142`; Cột 8: `5001016142`
- **Dòng 11**: Cột 1: `5001016149`; Cột 2: `金型材料仕入`; Cột 3: `Chi phí nguyên liệu, vật liệu trực tiếp`; Cột 4: `材料費`; Cột 5: `Chi phí nguyên vật liệu`; Cột 6: `5001016149`; Cột 7: `5001016149`; Cột 8: `5001016149`; Cột 9: `2月から追加する。`
- **Dòng 12**: Cột 1: `5001016151`; Cột 2: `生産用副資材`; Cột 3: `Chi phí nguyên liệu, vật liệu trực tiếp`; Cột 4: `材料費`; Cột 5: `Chi phí nguyên vật liệu`; Cột 6: `5001016151`; Cột 9: `2017年1月追加。`
- **Dòng 13**: Cột 1: `5004046221`; Cột 2: `雑給（直製）`; Cột 3: `Chi phí nhân công trực tiếp`; Cột 4: `雑給`; Cột 5: `Chi phí nhân công trực tiếp`; Cột 6: `5004046221`
- **Dòng 14**: Cột 1: `5004046371`; Cột 2: `雑給（間製）`; Cột 3: `Chi phí nhân viên phân xưởng`; Cột 4: `雑給`; Cột 5: `Chi phí nhân công trực tiếp`; Cột 6: `5004046371`
- **Dòng 15**: Cột 1: `5005016371`; Cột 2: `生産用消耗品費（製）`; Cột 3: `Chi phí dụng cụ sản xuất`; Cột 4: `消耗品費`; Cột 5: `Chi phí hàng hóa tiêu hao`; Cột 6: `5005016371`
- **Dòng 16**: Cột 1: `5005016372`; Cột 2: `その他消耗品（製）`; Cột 3: `Chi phí dụng cụ sản xuất`; Cột 4: `消耗品費`; Cột 5: `Chi phí hàng hóa tiêu hao`; Cột 6: `5005016372`
- **Dòng 17**: Cột 1: `5005016373`; Cột 2: `生産用文房具（製造）`; Cột 3: `Chi phí dụng cụ sản xuất`; Cột 4: `消耗品費`; Cột 5: `Chi phí hàng hóa tiêu hao`; Cột 6: `5005016373`; Cột 9: `2017年1月追加。`
- **Dòng 18**: Cột 1: `5005026371`; Cột 2: `消耗工具器具備品費（製）`; Cột 3: `Chi phí dụng cụ sản xuất`; Cột 4: `消耗工具器具備品費`; Cột 5: `Chi phí sử dụng công cụ,đồ đạc`; Cột 6: `5005026371`
- **Dòng 19**: Cột 1: `5005026372`; Cột 2: `消耗金型代（製）`; Cột 3: `Chi phí dụng cụ sản xuất`; Cột 4: `消耗金型費`; Cột 5: `Chi phí tiêu hao khuôn`; Cột 6: `5005026372`
- **Dòng 20**: Cột 1: `5006016241`; Cột 2: `減価償却費（製）　建物`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 6: `5006016241`
- **Dòng 21**: Cột 1: `5006016242`; Cột 2: `減価償却費（製）　機械装置`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 6: `5006016242`
- **Dòng 22**: Cột 1: `5006016243`; Cột 2: `減価償却費（製）　車輌運搬具`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 6: `5006016243`
- **Dòng 23**: Cột 1: `5006016244`; Cột 2: `減価償却費（製）　工具器具備品`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 6: `5006016244`
- **Dòng 24**: Cột 1: `5006016245`; Cột 2: `減価償却費（製）　構築物`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 6: `5006016245`
- **Dòng 25**: Cột 1: `5005036246`; Cột 2: `減価償却費（製）　金型`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `金型償却費`; Cột 5: `Chi phí khấu hao khuôn`; Cột 6: `5005036246`
- **Dòng 26**: Cột 1: `5006016247`; Cột 2: `減価償却費（製）　その他有形固定資産`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 6: `5006016247`
- **Dòng 27**: Cột 1: `5006016248`; Cột 2: `減価償却費（製）　リース建物`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 6: `5006016248`
- **Dòng 28**: Cột 1: `5006016249`; Cột 2: `減価償却費（製）　リース機械装置`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 6: `5006016249`
- **Dòng 29**: Cột 1: `5006016250`; Cột 2: `減価償却費（製）　リース車輌運搬具`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 6: `5006016250`
- **Dòng 30**: Cột 1: `5006016251`; Cột 2: `減価償却費（製）　リース工具器具備品`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 6: `5006016251`
- **Dòng 31**: Cột 1: `5006016252`; Cột 2: `減価償却費（製）　リース構築物`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 6: `5006016252`
- **Dòng 32**: Cột 1: `5006016253`; Cột 2: `減価償却費（製）　土地使用権`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 6: `5006016253`
- **Dòng 33**: Cột 1: `5006016254`; Cột 2: `減価償却費（製）　出版著作権`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 6: `5006016254`
- **Dòng 34**: Cột 1: `5006016255`; Cột 2: `減価償却費（製）　特許権`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 6: `5006016255`
- **Dòng 35**: Cột 1: `5006016256`; Cột 2: `減価償却費（製）　商標権`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 6: `5006016256`
- **Dòng 36**: Cột 1: `5006016257`; Cột 2: `減価償却費（製）　ソフトウェア`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 6: `5006016257`
- **Dòng 37**: Cột 1: `5006016258`; Cột 2: `減価償却費（製）　営業権`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 6: `5006016258`
- **Dòng 38**: Cột 1: `5006016259`; Cột 2: `減価償却費（製）　その他無形固定資産`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 6: `5006016259`
- **Dòng 39**: Cột 1: `5006016260`; Cột 2: `減価償却費配賦（製）　建物`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 6: `5006016260`
- **Dòng 40**: Cột 1: `5006016261`; Cột 2: `減価償却費配賦（製）　土地使用権`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 6: `5006016261`
- **Dòng 41**: Cột 1: `5004096281`; Cột 2: `求人費（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `募集教育費`; Cột 5: `Chi phí tuyển dụng,đào tạo`; Cột 6: `5004096281`
- **Dòng 42**: Cột 1: `5005046281`; Cột 2: `機械設備修繕費（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `修繕費`; Cột 5: `Chi phí sửa chữa`; Cột 6: `5005046281`
- **Dòng 43**: Cột 1: `5005046282`; Cột 2: `その他修繕費（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `修繕費`; Cột 5: `Chi phí sửa chữa`; Cột 6: `5005046282`
- **Dòng 44**: Cột 1: `5005046283`; Cột 2: `年間保守料（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `修繕費`; Cột 5: `Chi phí sửa chữa`; Cột 6: `5005046283`
- **Dòng 45**: Cột 1: `5005046284`; Cột 2: `金型修繕費（製造）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `修繕費`; Cột 5: `Chi phí sửa chữa`; Cột 6: `5005046284`; Cột 9: `2017年1月追加。`
- **Dòng 46**: Cột 1: `5005066281`; Cột 2: `電気代（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `水道光熱費`; Cột 5: `Chi phí Utilities(điện,nước..)`; Cột 6: `5005066281`
- **Dòng 47**: Cột 1: `5005066282`; Cột 2: `水道代（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `水道光熱費`; Cột 5: `Chi phí Utilities(điện,nước..)`; Cột 6: `5005066282`
- **Dòng 48**: Cột 1: `5005056281`; Cột 2: `ガス代（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `水道光熱費`; Cột 5: `Chi phí Utilities(điện,nước..)`; Cột 6: `5005056281`
- **Dòng 49**: Cột 1: `5005076281`; Cột 2: `通関申告費用（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 6: `5005076281`
- **Dòng 50**: Cột 1: `5005076282`; Cột 2: `設備輸送費（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 6: `5005076282`
- **Dòng 51**: Cột 1: `5005076283`; Cột 2: `輸入航空運賃（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 6: `5005076283`
- **Dòng 52**: Cột 1: `5005076284`; Cột 2: `輸入海上運賃（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 6: `5005076284`
- **Dòng 53**: Cột 1: `5005076285`; Cột 2: `空箱返却費用`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 6: `5005076285`
- **Dòng 54**: Cột 1: `5005076286`; Cột 2: `部品集荷トラック代`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 6: `5005076286`
- **Dòng 55**: Cột 1: `5005076287`; Cột 2: `物流保険料（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 6: `5005076287`
- **Dòng 56**: Cột 1: `5005076288`; Cột 2: `梱包材料費（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `荷造用品費`; Cột 5: `Chi phí NVL dùng đóng gói hàng`; Cột 6: `5005076288`
- **Dòng 57**: Cột 1: `5005076289`; Cột 2: `クーリエ費用（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 6: `5005076289`
- **Dòng 58**: Cột 1: `5005076291`; Cột 2: `外部倉庫　取扱手数料（製造）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 6: `5005076291`; Cột 9: `2017年1月追加。`
- **Dòng 59**: Cột 1: `5005076292`; Cột 2: `外部倉庫　保管料（製造）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 6: `5005076292`; Cột 9: `2017年1月追加。`
- **Dòng 60**: Cột 1: `5005076293`; Cột 2: `外部倉庫　輸送料（製造）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 6: `5005076293`; Cột 9: `2017年1月追加。`
- **Dòng 61**: Cột 1: `5005076294`; Cột 2: `外部物流業者　取扱手数料（製造）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 6: `5005076294`; Cột 9: `2017年1月追加。`
- **Dòng 62**: Cột 1: `5005086281`; Cột 2: `技術料（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `技術料`; Cột 5: `Phí kỹ thuật`; Cột 6: `5005086281`
- **Dòng 63**: Cột 1: `5005136281`; Cột 2: `通信費（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `通信費`; Cột 5: `Chi phí điện thoại`; Cột 6: `5005136281`
- **Dòng 64**: Cột 1: `5005246281`; Cột 2: `図書印刷費（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `図書及び事務費`; Cột 5: `Chi phí văn phòng`; Cột 6: `5005246281`
- **Dòng 65**: Cột 1: `5005246282`; Cột 2: `ＫＤＣシステム使用料（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `図書及び事務費`; Cột 5: `Chi phí văn phòng`; Cột 6: `5005246282`
- **Dòng 66**: Cột 1: `5005246283`; Cột 2: `ライセンス料（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `図書及び事務費`; Cột 5: `Chi phí văn phòng`; Cột 6: `5005246283`
- **Dòng 67**: Cột 1: `5005246284`; Cột 2: `会費（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `会費及び会議費`; Cột 5: `Chi phí cuộc họp`; Cột 6: `5005246284`
- **Dòng 68**: Cột 1: `5005216281`; Cột 2: `委嘱報酬・設計委託費（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `委嘱報酬`; Cột 5: `Thù lao ủy thác,phí hoa hồng`; Cột 6: `5005216281`
- **Dòng 69**: Cột 1: `5005226281`; Cột 2: `保険料（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `保険料`; Cột 5: `Chi phí bảo hiểm`; Cột 6: `5005226281`
- **Dòng 70**: Cột 1: `5005236281`; Cột 2: `事務所賃借料（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `賃借料`; Cột 5: `Chi phí thuê`; Cột 6: `5005236281`
- **Dòng 71**: Cột 1: `5005236282`; Cột 2: `倉庫賃借料（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `賃借料`; Cột 5: `Chi phí thuê`; Cột 6: `5005236282`
- **Dòng 72**: Cột 1: `5005246285`; Cột 2: `取扱手数料（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `手数料`; Cột 5: `Tiền dịch vụ,tiền lệ phí`; Cột 6: `5005246285`
- **Dòng 73**: Cột 1: `5005246286`; Cột 2: `その他手数料（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `手数料`; Cột 5: `Tiền dịch vụ,tiền lệ phí`; Cột 6: `5005246286`
- **Dòng 74**: Cột 1: `5005246287`; Cột 2: `ＫＤＣ手数料（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `手数料`; Cột 5: `Tiền dịch vụ,tiền lệ phí`; Cột 6: `5005246287`
- **Dòng 75**: Cột 1: `5005246288`; Cột 2: `事務用品費（製）`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `図書及び事務費`; Cột 5: `Chi phí văn phòng`; Cột 6: `5005246288`
- **Dòng 76**: Cột 1: `5004086291`; Cột 2: `福利厚生費（製）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `福利厚生費`; Cột 5: `Chi phí phúc lợi`; Cột 6: `5004086291`
- **Dòng 77**: Cột 1: `5004086293`; Cột 2: `教育訓練費（製）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `募集教育費`; Cột 5: `Chi phí tuyển dụng,đào tạo`; Cột 6: `5004086293`
- **Dòng 78**: Cột 1: `5005116291`; Cột 2: `ベトナム国内交通費（製）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `旅費交通費`; Cột 5: `Chi phí di chuyển`; Cột 6: `5005116291`
- **Dòng 79**: Cột 1: `5005116292`; Cột 2: `海外渡航費（製）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `渡航費`; Cột 5: `Chi phí di chuyển(nước ngoài)`; Cột 6: `5005116292`
- **Dòng 80**: Cột 1: `5005136291`; Cột 2: `郵送代（製）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `通信費`; Cột 5: `Chi phí điện thoại`; Cột 6: `5005136291`
- **Dòng 81**: Cột 1: `5005166291`; Cột 2: `接待交際費（製）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `接待交際費`; Cột 5: `Chi phí tiếp khách`; Cột 6: `5005166291`
- **Dòng 82**: Cột 1: `5005186292`; Cột 2: `その他税金（製）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `公租公課`; Cột 5: `Thuế,phí công cộng`; Cột 6: `5005186292`
- **Dòng 83**: Cột 1: `5005196373`; Cột 2: `試験研究用材料費`; Cột 3: `Chi phí dụng cụ sản xuất`; Cột 4: `試験研究費`; Cột 5: `Chi phí thử nghiệm,nghiên cứu`; Cột 6: `5005196373`; Cột 7: `5005196373`; Cột 8: `5005196373`; Cột 9: `2月から追加する。`
- **Dòng 84**: Cột 1: `5005196277`; Cột 2: `試験研究用役務費`; Cột 3: `Chi phi dịch vụ mua ngoài`; Cột 4: `試験研究費`; Cột 5: `Chi phí thử nghiệm,nghiên cứu`; Cột 6: `5005196277`; Cột 7: `5005196277`; Cột 8: `5005196277`; Cột 9: `2月から追加する。`
- **Dòng 85**: Cột 1: `5005246291`; Cột 2: `会議費（製）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `会費及び会議費`; Cột 5: `Chi phí cuộc họp`; Cột 6: `5005246291`
- **Dòng 86**: Cột 1: `5005246292`; Cột 2: `雑費（製）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `雑費`; Cột 5: `Các loại chi phí bằng tiền khác`; Cột 6: `5005246292`
- **Dòng 87**: Cột 1: `5005246294`; Cột 2: `開発費振替勘定（製）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `雑費`; Cột 5: `Các loại chi phí bằng tiền khác`; Cột 6: `5005246294`; Cột 9: `2月から追加する→9/2015からｘから雑費になった`
- **Dòng 88**: Cột 1: `5005256291`; Cột 2: `棚卸減耗費（製）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `棚卸減耗費`; Cột 5: `Chi phí hao hụt sau kiểm kê`; Cột 6: `5005256291`
- **Dòng 89**: Cột 1: `5101016174`; Cột 2: `製商品仕入諸掛`; Cột 3: `Giá vốn hàng bán`; Cột 4: `仕入製商品費`; Cột 5: `Chi phí bán hàng`; Cột 6: `5101016174`
- **Dòng 90**: Cột 1: `5101016179`; Cột 2: `製品品目外注加工費`; Cột 3: `Giá vốn hàng bán`; Cột 4: `外注加工費`; Cột 5: `Chi phí gia công ngoài`; Cột 6: `5101016179`
- **Dòng 91**: Cột 1: `5101016187`; Cột 2: `製商品在庫廃棄損`; Cột 3: `Giá vốn hàng bán`; Cột 4: `雑損失`; Cột 5: `Tổn thất,lỗ khác`; Cột 6: `5101016187`
- **Dòng 92**: Cột 1: `5101016189`; Cột 2: `金型製作収入`; Cột 3: `Doanh thu bán thành phẩm`; Cột 4: `雑収入`; Cột 5: `Thu nhập khác`; Cột 6: `5101016189`; Cột 9: `2月から追加する。`
- **Dòng 93**: Cột 1: `6004046511`; Cột 2: `雑給（販売）`; Cột 3: `Chi phí nhân viên`; Cột 4: `雑給`; Cột 5: `Chi phí nhân công trực tiếp`; Cột 8: `6004046511`
- **Dòng 94**: Cột 1: `6003036412`; Cột 2: `梱包材料費（販売）`; Cột 3: `Chi phí vật liệu bao bì`; Cột 4: `荷造用品費`; Cột 5: `Chi phí NVL dùng đóng gói hàng`; Cột 8: `6003036412`
- **Dòng 95**: Cột 1: `6005016413`; Cột 2: `消耗品費（販売）`; Cột 3: `Chi phí dụng cụ đồ dùng`; Cột 4: `消耗品費`; Cột 5: `Chi phí hàng hóa tiêu hao`; Cột 8: `6005016413`
- **Dòng 96**: Cột 1: `6005016414`; Cột 2: `消耗備品費（販売）`; Cột 3: `Chi phí dụng cụ đồ dùng`; Cột 4: `消耗工具器具備品費`; Cột 5: `Chi phí sử dụng công cụ,đồ đạc`; Cột 7: `6005016414`; Cột 8: `6005016414`; Cột 9: `2017年1月追加。`
- **Dòng 97**: Cột 1: `6006016521`; Cột 2: `減価償却費（販）　建物`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 8: `6006016521`
- **Dòng 98**: Cột 1: `6006016522`; Cột 2: `減価償却費（販）　機械装置`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 8: `6006016522`
- **Dòng 99**: Cột 1: `6006016523`; Cột 2: `減価償却費（販）　車輌運搬具`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 8: `6006016523`
- **Dòng 100**: Cột 1: `6006016524`; Cột 2: `減価償却費（販）　工具器具備品`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 8: `6006016524`
- **Dòng 101**: Cột 1: `6006016525`; Cột 2: `減価償却費（販）　構築物`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 8: `6006016525`
- **Dòng 102**: Cột 1: `6006016526`; Cột 2: `減価償却費（販）　その他有形固定資産`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 8: `6006016526`
- **Dòng 103**: Cột 1: `6006016527`; Cột 2: `減価償却費（販）　リース建物`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 8: `6006016527`
- **Dòng 104**: Cột 1: `6006016528`; Cột 2: `減価償却費（販）　リース機械装置`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 8: `6006016528`
- **Dòng 105**: Cột 1: `6006016529`; Cột 2: `減価償却費（販）　リース車輌運搬具`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 8: `6006016529`
- **Dòng 106**: Cột 1: `6006016530`; Cột 2: `減価償却費（販）　リース工具器具備品`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 8: `6006016530`
- **Dòng 107**: Cột 1: `6006016531`; Cột 2: `減価償却費（販）　リース構築物`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 8: `6006016531`
- **Dòng 108**: Cột 1: `6006016532`; Cột 2: `減価償却費（販）　土地使用権`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 8: `6006016532`
- **Dòng 109**: Cột 1: `6006016533`; Cột 2: `減価償却費（販）　出版著作権`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 8: `6006016533`
- **Dòng 110**: Cột 1: `6006016534`; Cột 2: `減価償却費（販）　特許権`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 8: `6006016534`
- **Dòng 111**: Cột 1: `6006016535`; Cột 2: `減価償却費（販）　商標権`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 8: `6006016535`
- **Dòng 112**: Cột 1: `6006016536`; Cột 2: `減価償却費（販）　ソフトウェア`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 8: `6006016536`
- **Dòng 113**: Cột 1: `6006016537`; Cột 2: `減価償却費（販）　営業権`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 8: `6006016537`
- **Dòng 114**: Cột 1: `6006016538`; Cột 2: `減価償却費（販）　その他無形固定資産`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 8: `6006016538`
- **Dòng 115**: Cột 1: `6006016539`; Cột 2: `減価償却費配賦（販）　建物`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 8: `6006016539`
- **Dòng 116**: Cột 1: `6006016540`; Cột 2: `減価償却費配賦（販）　土地使用権`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 8: `6006016540`
- **Dòng 117**: Cột 1: `6005046541`; Cột 2: `その他修繕費（販売）`; Cột 3: `Chi phí bảo hành`; Cột 4: `修繕費`; Cột 5: `Chi phí sửa chữa`; Cột 8: `6005046541`
- **Dòng 118**: Cột 1: `6005046542`; Cột 2: `年間保守料（販売）`; Cột 3: `Chi phí bảo hành`; Cột 4: `修繕費`; Cột 5: `Chi phí sửa chữa`; Cột 8: `6005046542`
- **Dòng 119**: Cột 1: `6003016541`; Cột 2: `販売手数料（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `手数料`; Cột 5: `Tiền dịch vụ,tiền lệ phí`; Cột 8: `6003016541`
- **Dòng 120**: Cột 1: `6003026541`; Cột 2: `販売促進費（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `雑費`; Cột 5: `Các loại chi phí bằng tiền khác`; Cột 8: `6003026541`
- **Dòng 121**: Cột 1: `6003036541`; Cột 2: `通関申告料（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 8: `6003036541`
- **Dòng 122**: Cột 1: `6003036542`; Cột 2: `クーリエ費用（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 8: `6003036542`
- **Dòng 123**: Cột 1: `6003036543`; Cột 2: `輸出航空運賃（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 6: `6003036543`; Cột 8: `6003036543`
- **Dòng 124**: Cột 1: `6003036544`; Cột 2: `輸出海上運賃（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 6: `6003036544`; Cột 7: `6003036544`; Cột 8: `6003036544`
- **Dòng 125**: Cột 1: `6003036545`; Cột 2: `保管延長費（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 8: `6003036545`
- **Dòng 126**: Cột 1: `6003036546`; Cột 2: `物流保険料（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 8: `6003036546`
- **Dòng 127**: Cột 1: `6003036547`; Cột 2: `梱包費用（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 8: `6003036547`
- **Dòng 128**: Cột 1: `6003036548`; Cột 2: `返品手数料（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 8: `6003036548`
- **Dòng 129**: Cột 1: `6003036549`; Cột 2: `保管料（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 8: `6003036549`
- **Dòng 130**: Cột 1: `6003036550`; Cột 2: `オーバーナイト費（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 8: `6003036550`
- **Dòng 131**: Cột 1: `6003036551`; Cột 2: `バンニング費（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 8: `6003036551`
- **Dòng 132**: Cột 1: `6003036552`; Cột 2: `その他物流費（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 6: `6003036552`; Cột 8: `6003036552`
- **Dòng 133**: Cột 1: `6003036554`; Cột 2: `外部倉庫　取扱手数料（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 6: `6003036554`; Cột 7: `6003036554`; Cột 8: `6003036554`; Cột 9: `2017年1月追加。`
- **Dòng 134**: Cột 1: `6003036555`; Cột 2: `外部倉庫　保管料（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 6: `6003036555`; Cột 7: `6003036555`; Cột 8: `6003036555`; Cột 9: `2017年1月追加。`
- **Dòng 135**: Cột 1: `6003036556`; Cột 2: `外部倉庫　輸送料（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 6: `6003036556`; Cột 7: `6003036556`; Cột 8: `6003036556`; Cột 9: `2017年1月追加。`
- **Dòng 136**: Cột 1: `6003036557`; Cột 2: `外部物流業者　取扱手数料（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `荷造運賃`; Cột 5: `Chi phí vận chuyển hàng hóa`; Cột 6: `6003036557`; Cột 7: `6003036557`; Cột 8: `6003036557`; Cột 9: `2017年1月追加。`
- **Dòng 137**: Cột 1: `6004096541`; Cột 2: `求人費（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `募集教育費`; Cột 5: `Chi phí tuyển dụng,đào tạo`; Cột 8: `6004096541`
- **Dòng 138**: Cột 1: `6005056541`; Cột 2: `電気代（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `水道光熱費`; Cột 5: `Chi phí Utilities(điện,nước..)`; Cột 8: `6005056541`
- **Dòng 139**: Cột 1: `6005056542`; Cột 2: `水道代（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `水道光熱費`; Cột 5: `Chi phí Utilities(điện,nước..)`; Cột 8: `6005056542`
- **Dòng 140**: Cột 1: `6005056543`; Cột 2: `ガス代（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `水道光熱費`; Cột 5: `Chi phí Utilities(điện,nước..)`; Cột 8: `6005056543`
- **Dòng 141**: Cột 1: `6005136541`; Cột 2: `通信費（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `通信費`; Cột 5: `Chi phí điện thoại`; Cột 8: `6005136541`
- **Dòng 142**: Cột 1: `6005146541`; Cột 2: `図書印刷費（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `図書及び事務費`; Cột 5: `Chi phí văn phòng`; Cột 8: `6005146541`
- **Dòng 143**: Cột 1: `6005146542`; Cột 2: `ＫＤＣシステム使用料（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `図書及び事務費`; Cột 5: `Chi phí văn phòng`; Cột 8: `6005146542`
- **Dòng 144**: Cột 1: `6005146543`; Cột 2: `ライセンス料（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `図書及び事務費`; Cột 5: `Chi phí văn phòng`; Cột 8: `6005146543`
- **Dòng 145**: Cột 1: `6005156541`; Cột 2: `広告宣伝費（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `雑費`; Cột 5: `Các loại chi phí bằng tiền khác`; Cột 8: `6005156541`
- **Dòng 146**: Cột 1: `6005206541`; Cột 2: `会費（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `会費及び会議費`; Cột 5: `Chi phí cuộc họp`; Cột 8: `6005206541`
- **Dòng 147**: Cột 1: `6005216541`; Cột 2: `委嘱報酬・設計委託費（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `委嘱報酬`; Cột 5: `Thù lao ủy thác,phí hoa hồng`; Cột 8: `6005216541`
- **Dòng 148**: Cột 1: `6005226541`; Cột 2: `保険料（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `保険料`; Cột 5: `Chi phí bảo hiểm`; Cột 8: `6005226541`
- **Dòng 149**: Cột 1: `6005236541`; Cột 2: `事務所賃借料（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `賃借料`; Cột 5: `Chi phí thuê`; Cột 8: `6005236541`
- **Dòng 150**: Cột 1: `6005246541`; Cột 2: `取扱手数料（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `手数料`; Cột 5: `Tiền dịch vụ,tiền lệ phí`; Cột 8: `6005246541`
- **Dòng 151**: Cột 1: `6005246542`; Cột 2: `その他手数料`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `手数料`; Cột 5: `Tiền dịch vụ,tiền lệ phí`; Cột 6: `6005246542`; Cột 7: `6005246542`; Cột 8: `6005246542`
- **Dòng 152**: Cột 1: `6005246543`; Cột 2: `ＫＤＣ手数料`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `手数料`; Cột 5: `Tiền dịch vụ,tiền lệ phí`; Cột 6: `6005246543`; Cột 7: `6005246543`; Cột 8: `6005246543`
- **Dòng 153**: Cột 1: `6005246544`; Cột 2: `事務用品費（販売）`; Cột 3: `Chi phí dịch vụ mua ngòai`; Cột 4: `図書及び事務費`; Cột 5: `Chi phí văn phòng`; Cột 8: `6005246544`
- **Dòng 154**: Cột 1: `6004086551`; Cột 2: `福利厚生費（販売）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `福利厚生費`; Cột 5: `Chi phí phúc lợi`; Cột 8: `6004086551`
- **Dòng 155**: Cột 1: `6004086553`; Cột 2: `教育訓練費（販売）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `募集教育費`; Cột 5: `Chi phí tuyển dụng,đào tạo`; Cột 8: `6004086553`
- **Dòng 156**: Cột 1: `6005116551`; Cột 2: `ベトナム国内交通費（販売）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `旅費交通費`; Cột 5: `Chi phí di chuyển`; Cột 8: `6005116551`
- **Dòng 157**: Cột 1: `6005116552`; Cột 2: `海外渡航費（販売）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `渡航費`; Cột 5: `Chi phí di chuyển(nước ngoài)`; Cột 8: `6005116552`
- **Dòng 158**: Cột 1: `6005136551`; Cột 2: `郵送代（販売）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `通信費`; Cột 5: `Chi phí điện thoại`; Cột 8: `6005136551`
- **Dòng 159**: Cột 1: `6005166551`; Cột 2: `接待交際費（販売）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `接待交際費`; Cột 5: `Chi phí tiếp khách`; Cột 8: `6005166551`
- **Dòng 160**: Cột 1: `6005186552`; Cột 2: `その他税金（販売）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `公租公課`; Cột 5: `Thuế,phí công cộng`; Cột 8: `6005186552`
- **Dòng 161**: Cột 1: `6005246551`; Cột 2: `会議費（販売）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `会費及び会議費`; Cột 5: `Chi phí cuộc họp`; Cột 8: `6005246551`
- **Dòng 162**: Cột 1: `6005246552`; Cột 2: `雑費（販売）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `雑費`; Cột 5: `Các loại chi phí bằng tiền khác`; Cột 8: `6005246552`
- **Dòng 163**: Cột 1: `6005246553`; Cột 2: `棚卸減耗費（販売）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `棚卸減耗費`; Cột 5: `Chi phí hao hụt sau kiểm kê`; Cột 8: `6005246553`
- **Dòng 164**: Cột 1: `6004046421`; Cột 2: `雑給（一般）`; Cột 3: `Chi phí nhân viên quản lý`; Cột 4: `雑給`; Cột 5: `Chi phí nhân công trực tiếp`; Cột 7: `6004046421`
- **Dòng 165**: Cột 1: `6005016422`; Cột 2: `消耗品費（一般）`; Cột 3: `Chi phí vật liệu quản lý`; Cột 4: `消耗品費`; Cột 5: `Chi phí hàng hóa tiêu hao`; Cột 7: `6005016422`; Cột 9: `2017年1月変更。`
- **Dòng 166**: Cột 1: `6005016423`; Cột 2: `消耗備品費（一般）`; Cột 3: `Chi phí vật liệu quản lý`; Cột 4: `消耗工具器具備品費`; Cột 5: `Chi phí sử dụng công cụ,đồ đạc`; Cột 7: `6005016423`; Cột 8: `6005016423`; Cột 9: `2017年1月追加。`
- **Dòng 167**: Cột 1: `6005126423`; Cột 2: `事務用品費（一般）`; Cột 3: `Chi phí đồ dùng văn phòng`; Cột 4: `図書及び事務費`; Cột 5: `Chi phí văn phòng`; Cột 7: `6005126423`
- **Dòng 168**: Cột 1: `6006016611`; Cột 2: `減価償却費（一般）　建物`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 7: `6006016611`
- **Dòng 169**: Cột 1: `6006016612`; Cột 2: `減価償却費（一般）　車輌運搬具`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 7: `6006016612`
- **Dòng 170**: Cột 1: `6006016613`; Cột 2: `減価償却費（一般）　工具器具備品`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 7: `6006016613`
- **Dòng 171**: Cột 1: `6006016614`; Cột 2: `減価償却費（一般）　構築物`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 7: `6006016614`
- **Dòng 172**: Cột 1: `6006016615`; Cột 2: `減価償却費（一般）　その他有形固定資産`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 7: `6006016615`
- **Dòng 173**: Cột 1: `6006016616`; Cột 2: `減価償却費（一般）　リース建物`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 7: `6006016616`
- **Dòng 174**: Cột 1: `6006016617`; Cột 2: `減価償却費（一般）　リース車輌運搬具`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 7: `6006016617`
- **Dòng 175**: Cột 1: `6006016618`; Cột 2: `減価償却費（一般）　リース工具器具備品`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 7: `6006016618`
- **Dòng 176**: Cột 1: `6006016619`; Cột 2: `減価償却費（一般）　リース構築物`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 7: `6006016619`
- **Dòng 177**: Cột 1: `6006016620`; Cột 2: `減価償却費（一般）　土地使用権`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 7: `6006016620`
- **Dòng 178**: Cột 1: `6006016621`; Cột 2: `減価償却費（一般）　出版著作権`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 7: `6006016621`
- **Dòng 179**: Cột 1: `6006016622`; Cột 2: `減価償却費（一般）　特許権`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 7: `6006016622`
- **Dòng 180**: Cột 1: `6006016623`; Cột 2: `減価償却費（一般）　商標権`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 7: `6006016623`
- **Dòng 181**: Cột 1: `6006016624`; Cột 2: `減価償却費（一般）　ソフトウェア`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 7: `6006016624`
- **Dòng 182**: Cột 1: `6006016625`; Cột 2: `減価償却費（一般）　営業権`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 7: `6006016625`
- **Dòng 183**: Cột 1: `6006016626`; Cột 2: `減価償却費（一般）　その他無形固定資産`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 7: `6006016626`
- **Dòng 184**: Cột 1: `6006016627`; Cột 2: `減価償却費（一般）　差異調整`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 7: `6006016627`
- **Dòng 185**: Cột 1: `6006016628`; Cột 2: `減価償却費配賦（一般）　建物`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 7: `6006016628`
- **Dòng 186**: Cột 1: `6006016629`; Cột 2: `減価償却費配賦（一般）　土地使用権`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 7: `6006016629`
- **Dòng 187**: Cột 1: `6006016630`; Cột 2: `減価償却費（一般）機器装置`; Cột 3: `Chi phí khấu hao TSCĐ`; Cột 4: `減価償却費`; Cột 5: `Chi phí khấu hao`; Cột 7: `6006016630`; Cột 9: `Thêm từ tháng 12/2024`
- **Dòng 188**: Cột 1: `6005186425`; Cột 2: `外国契約者税（一般）`; Cột 3: `Thuế phí và lệ phí`; Cột 4: `公租公課`; Cột 5: `Thuế,phí công cộng`; Cột 7: `6005186425`
- **Dòng 189**: Cột 1: `6005186429`; Cột 2: `その他税金（一般）`; Cột 3: `Thuế phí và lệ phí`; Cột 4: `公租公課`; Cột 5: `Thuế,phí công cộng`; Cột 7: `6005186429`
- **Dòng 190**: Cột 1: `6005266426`; Cột 2: `貸倒引当金繰入（一般）`; Cột 3: `Chi phí dự phòng`; Cột 4: `雑費`; Cột 5: `Các loại chi phí bằng tiền khác`; Cột 7: `6005266426`
- **Dòng 191**: Cột 1: `6004096621`; Cột 2: `求人費（一般）`; Cột 3: `Chi phí dịch vụ mua ngoài`; Cột 4: `募集教育費`; Cột 5: `Chi phí tuyển dụng,đào tạo`; Cột 7: `6004096621`
- **Dòng 192**: Cột 1: `6005046622`; Cột 2: `修繕費（一般）`; Cột 3: `Chi phí dịch vụ mua ngoài`; Cột 4: `修繕費`; Cột 5: `Chi phí sửa chữa`; Cột 7: `6005046622`
- **Dòng 193**: Cột 1: `6005046635`; Cột 2: `保守料（一般）`; Cột 3: `Chi phí dịch vụ mua ngoài`; Cột 4: `修繕費`; Cột 5: `Chi phí sửa chữa`; Cột 7: `6005046635`
- **Dòng 194**: Cột 1: `6005056623`; Cột 2: `電気代（一般）`; Cột 3: `Chi phí dịch vụ mua ngoài`; Cột 4: `水道光熱費`; Cột 5: `Chi phí Utilities(điện,nước..)`; Cột 7: `6005056623`
- **Dòng 195**: Cột 1: `6005056624`; Cột 2: `水道代（一般）`; Cột 3: `Chi phí dịch vụ mua ngoài`; Cột 4: `水道光熱費`; Cột 5: `Chi phí Utilities(điện,nước..)`; Cột 7: `6005056624`
- **Dòng 196**: Cột 1: `6005056625`; Cột 2: `ガス代（一般）`; Cột 3: `Chi phí dịch vụ mua ngoài`; Cột 4: `水道光熱費`; Cột 5: `Chi phí Utilities(điện,nước..)`; Cột 7: `6005056625`
- **Dòng 197**: Cột 1: `6005136626`; Cột 2: `通信費（一般）`; Cột 3: `Chi phí dịch vụ mua ngoài`; Cột 4: `通信費`; Cột 5: `Chi phí điện thoại`; Cột 7: `6005136626`
- **Dòng 198**: Cột 1: `6005146627`; Cột 2: `図書印刷費（一般）`; Cột 3: `Chi phí dịch vụ mua ngoài`; Cột 4: `図書及び事務費`; Cột 5: `Chi phí văn phòng`; Cột 7: `6005146627`
- **Dòng 199**: Cột 1: `6005146628`; Cột 2: `ＫＤＣシステム使用料（一般）`; Cột 3: `Chi phí dịch vụ mua ngoài`; Cột 4: `図書及び事務費`; Cột 5: `Chi phí văn phòng`; Cột 7: `6005146628`
- **Dòng 200**: Cột 1: `6005146629`; Cột 2: `ライセンス料（一般）`; Cột 3: `Chi phí dịch vụ mua ngoài`; Cột 4: `図書及び事務費`; Cột 5: `Chi phí văn phòng`; Cột 7: `6005146629`
- **Dòng 201**: Cột 1: `6005156630`; Cột 2: `広告宣伝費（一般）`; Cột 3: `Chi phí dịch vụ mua ngoài`; Cột 4: `雑費`; Cột 5: `Các loại chi phí bằng tiền khác`; Cột 7: `6005156630`
- **Dòng 202**: Cột 1: `6005206631`; Cột 2: `会費（一般）`; Cột 3: `Chi phí dịch vụ mua ngoài`; Cột 4: `会費及び会議費`; Cột 5: `Chi phí cuộc họp`; Cột 7: `6005206631`
- **Dòng 203**: Cột 1: `6005216632`; Cột 2: `委嘱報酬・設計委託費（一般）`; Cột 3: `Chi phí dịch vụ mua ngoài`; Cột 4: `委嘱報酬`; Cột 5: `Thù lao ủy thác,phí hoa hồng`; Cột 7: `6005216632`
- **Dòng 204**: Cột 1: `6005226633`; Cột 2: `保険料（一般）`; Cột 3: `Chi phí dịch vụ mua ngoài`; Cột 4: `保険料`; Cột 5: `Chi phí bảo hiểm`; Cột 7: `6005226633`
- **Dòng 205**: Cột 1: `6005236634`; Cột 2: `事務所賃借料（一般）`; Cột 3: `Chi phí dịch vụ mua ngoài`; Cột 4: `賃借料`; Cột 5: `Chi phí thuê`; Cột 7: `6005236634`
- **Dòng 206**: Cột 1: `6005246636`; Cột 2: `取扱手数料（一般）`; Cột 3: `Chi phí dịch vụ mua ngoài`; Cột 4: `手数料`; Cột 5: `Tiền dịch vụ,tiền lệ phí`; Cột 7: `6005246636`
- **Dòng 207**: Cột 1: `6005246672`; Cột 2: `銀行手数料（一般）`; Cột 3: `Chi phí dịch vụ mua ngoài`; Cột 4: `手数料`; Cột 5: `Tiền dịch vụ,tiền lệ phí`; Cột 7: `6005246672`
- **Dòng 208**: Cột 1: `6005246673`; Cột 2: `その他手数料（一般）`; Cột 3: `Chi phí dịch vụ mua ngoài`; Cột 4: `手数料`; Cột 5: `Tiền dịch vụ,tiền lệ phí`; Cột 7: `6005246673`
- **Dòng 209**: Cột 1: `6005246674`; Cột 2: `ＫＤＣ手数料（一般）`; Cột 3: `Chi phí dịch vụ mua ngoài`; Cột 4: `手数料`; Cột 5: `Tiền dịch vụ,tiền lệ phí`; Cột 7: `6005246674`
- **Dòng 210**: Cột 1: `6004086651`; Cột 2: `福利厚生費（一般）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `福利厚生費`; Cột 5: `Chi phí phúc lợi`; Cột 7: `6004086651`
- **Dòng 211**: Cột 1: `6004086653`; Cột 2: `教育訓練費（一般）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `募集教育費`; Cột 5: `Chi phí tuyển dụng,đào tạo`; Cột 7: `6004086653`
- **Dòng 212**: Cột 1: `6005116654`; Cột 2: `ベトナム国内交通費（一般）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `旅費交通費`; Cột 5: `Chi phí di chuyển`; Cột 7: `6005116654`
- **Dòng 213**: Cột 1: `6005116655`; Cột 2: `海外渡航費（一般）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `渡航費`; Cột 5: `Chi phí di chuyển(nước ngoài)`; Cột 7: `6005116655`
- **Dòng 214**: Cột 1: `6005136657`; Cột 2: `郵送代（一般）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `通信費`; Cột 5: `Chi phí điện thoại`; Cột 7: `6005136657`
- **Dòng 215**: Cột 1: `6005166658`; Cột 2: `接待交際費（一般）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `接待交際費`; Cột 5: `Chi phí tiếp khách`; Cột 7: `6005166658`
- **Dòng 216**: Cột 1: `6005176659`; Cột 2: `寄付金（一般）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `雑費`; Cột 5: `Các loại chi phí bằng tiền khác`; Cột 7: `6005176659`
- **Dòng 217**: Cột 1: `6005246671`; Cột 2: `雑費（一般）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `雑費`; Cột 5: `Các loại chi phí bằng tiền khác`; Cột 7: `6005246671`
- **Dòng 218**: Cột 1: `6005246675`; Cột 2: `会議費（一般）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `会費及び会議費`; Cột 5: `Chi phí cuộc họp`; Cột 7: `6005246675`
- **Dòng 219**: Cột 1: `6005246676`; Cột 2: `開発費振替勘定（一般）`; Cột 3: `Chi phí bằng tiền khác`; Cột 4: `雑費`; Cột 5: `Các loại chi phí bằng tiền khác`; Cột 7: `6005246676`; Cột 9: `2月から追加する→9/2015からｘから雑費になった`
- **Dòng 220**: Cột 1: `8001017111`; Cột 2: `固定資産売却益`; Cột 3: `Thu nhập khác`; Cột 4: `特別利益`; Cột 5: `Lợi nhuận đặc biệt`; Cột 6: `8001017111`; Cột 7: `8001017111`; Cột 8: `8001017111`
- **Dòng 221**: Cột 1: `8001027111`; Cột 2: `前期損益修正益`; Cột 3: `Thu nhập khác`; Cột 4: `特別利益`; Cột 5: `Lợi nhuận đặc biệt`; Cột 6: `8001027111`; Cột 7: `8001027111`; Cột 8: `8001027111`
- **Dòng 222**: Cột 1: `8001037111`; Cột 2: `その他特別利益`; Cột 3: `Thu nhập khác`; Cột 4: `特別利益`; Cột 5: `Lợi nhuận đặc biệt`; Cột 6: `8001037111`; Cột 7: `8001037111`; Cột 8: `8001037111`
- **Dòng 223**: Cột 1: `7002048111`; Cột 2: `雑損失`; Cột 3: `Chi phí khác`; Cột 4: `雑損失`; Cột 5: `Tổn thất,lỗ khác`; Cột 6: `7002048111`; Cột 7: `7002048111`; Cột 8: `7002048111`
- **Dòng 224**: Cột 1: `7002048112`; Cột 2: `棚卸資産廃棄損`; Cột 3: `Chi phí khác`; Cột 4: `棚卸資産廃棄損`; Cột 5: `Tổn thất tài sản hư hỏng sau kiểm kê`; Cột 6: `7002048112`; Cột 7: `7002048112`; Cột 8: `7002048112`
- **Dòng 225**: Cột 1: `8002018111`; Cột 2: `固定資産売却損・除却損`; Cột 3: `Chi phí khác`; Cột 4: `特別損失`; Cột 5: `Lỗ đặc biệt`; Cột 6: `8002018111`; Cột 7: `8002018111`; Cột 8: `8002018111`
- **Dòng 226**: Cột 1: `8002028111`; Cột 2: `前期損益修正損`; Cột 3: `Chi phí khác`; Cột 4: `特別損失`; Cột 5: `Lỗ đặc biệt`; Cột 6: `8002028111`; Cột 7: `8002028111`; Cột 8: `8002028111`
- **Dòng 227**: Cột 1: `8002038111`; Cột 2: `その他特別損失`; Cột 3: `Chi phí khác`; Cột 4: `特別損失`; Cột 5: `Lỗ đặc biệt`; Cột 6: `8002038111`; Cột 7: `8002038111`; Cột 8: `8002038111`
- **Dòng 228**: Cột 1: `9114120002`; Cột 2: `社外出荷`; Cột 4: `社外出荷`; Cột 5: `Xuất hàng ra ngoài`; Cột 6: `9114120002`; Cột 7: `9114120002`; Cột 8: `9114120002`
- **Dòng 229**: Cột 1: `9114120004`; Cột 2: `社内売`; Cột 4: `社内売`; Cột 5: `Bán hàng nội bộ`; Cột 6: `9114120004`; Cột 7: `9114120004`; Cột 8: `9114120004`
- **Dòng 230**: Cột 1: `9114120005`; Cột 2: `支払営業口銭`; Cột 4: `営業経費`; Cột 5: `Chi phí hoạt động`; Cột 6: `9114120005`; Cột 7: `9114120005`; Cột 8: `9114120005`
- **Dòng 231**: Cột 1: `9114120006`; Cột 2: `材料費(指図出庫）`; Cột 4: `材料費`; Cột 5: `Chi phí nguyên vật liệu`; Cột 6: `9114120006`; Cột 7: `9114120006`; Cột 8: `9114120006`
- **Dòng 232**: Cột 1: `9114120007`; Cột 2: `社内金利（固定資産）`; Cột 4: `固定資産金利`; Cột 5: `Lãi suất tài sản cố định`; Cột 6: `9114120007`; Cột 7: `9114120007`; Cột 8: `9114120007`
- **Dòng 233**: Cột 1: `9114120008`; Cột 2: `仕入製商品費`; Cột 4: `仕入製商品費`; Cột 5: `Chi phí bán hàng`; Cột 6: `9114120008`
- **Dòng 234**: Cột 1: `9114120009`; Cột 2: `社内金利（在庫）`; Cột 4: `在庫金利`; Cột 5: `Lãi suất tồn kho`; Cột 6: `9114120009`; Cột 7: `9114120009`; Cột 8: `9114120009`
- **Dòng 235**: Cột 1: `9114120011`; Cột 2: `内部諸経費`; Cột 4: `内部諸経費`; Cột 5: `Chi phí nội bộ`; Cột 6: `9114120011`; Cột 7: `9114120011`; Cột 8: `9114120011`
- **Dòng 236**: Cột 1: `9114120014`; Cột 2: `社内買`; Cột 4: `社内買`; Cột 5: `Mua hàng nội bộ`; Cột 6: `9114120014`; Cột 7: `9114120014`; Cột 8: `9114120014`
- **Dòng 237**: Cột 1: `9114120018`; Cột 2: `部内間接経費`; Cột 4: `部内間接経費`; Cột 5: `Chi phí trong bộ phận(gián tiếp)`; Cột 6: `9114120018`; Cột 7: `9114120018`; Cột 8: `9114120018`
- **Dòng 238**: Cột 1: `9114120021`; Cột 2: `工場間接経費`; Cột 4: `工場間接経費`; Cột 5: `Chi phí nhà máy(gián tiếp)`; Cột 6: `9114120021`; Cột 7: `9114120021`; Cột 8: `9114120021`
- **Dòng 239**: Cột 1: `9114120028`; Cột 2: `社内システム使用料`; Cột 4: `社内システム使用料`; Cột 5: `Phí sử dụng phần mềm nội bộ`; Cột 6: `9114120028`; Cột 7: `9114120028`; Cột 8: `9114120028`
- **Dòng 240**: Cột 1: `9114120029`; Cột 2: `部外間接経費1`; Cột 4: `部外間接経費1`; Cột 5: `Chi phí ngoài bộ phận(gián tiếp 1)`; Cột 6: `9114120029`; Cột 7: `9114120029`; Cột 8: `9114120029`
- **Dòng 241**: Cột 1: `9114120030`; Cột 2: `部外間接経費2`; Cột 4: `部外間接経費2`; Cột 5: `Chi phí ngoài bộ phận(gián tiếp 2)`; Cột 6: `9114120030`; Cột 7: `9114120030`; Cột 8: `9114120030`

---

## Sheet: 原価センタ
- Kích thước sheet: 66 dòng x 5 cột

- **Dòng 1**: Cột 1: `原価センタ`; Cột 2: `テキスト`; Cột 3: `No.`; Cột 4: `採算区分`; Cột 5: `原価区分`
- **Dòng 2**: Cột 1: `1412000004`; Cột 2: `機器製造1課`; Cột 3: `1.`; Cột 4: `製造`; Cột 5: `製造`
- **Dòng 3**: Cột 1: `1412000005`; Cột 2: `機器製造2課`; Cột 3: `2.`; Cột 4: `製造`; Cột 5: `製造`
- **Dòng 4**: Cột 1: `1412000081`; Cột 2: `機器製造3課`; Cột 3: `52.`; Cột 4: `製造`; Cột 5: `製造`
- **Dòng 5**: Cột 1: `1412000066`; Cột 2: `RPS製造課`; Cột 3: `39.`; Cột 4: `製造`; Cột 5: `製造`
- **Dòng 6**: Cột 1: `1412000034`; Cột 2: `トナー製造課`; Cột 3: `4.`; Cột 4: `製造`; Cột 5: `製造`
- **Dòng 7**: Cột 1: `1412000056`; Cột 2: `部品製造課`; Cột 3: `23.`; Cột 4: `製造`; Cột 5: `製造`
- **Dòng 8**: Cột 1: `1412000050`; Cột 2: `MD1課`; Cột 3: `7.`; Cột 4: `製造`; Cột 5: `製造`
- **Dòng 9**: Cột 1: `1412000077`; Cột 2: `MD2課`; Cột 3: `8.`; Cột 4: `製造`; Cột 5: `製造`
- **Dòng 10**: Cột 1: `1412000083`; Cột 2: `MD3課`; Cột 3: `53.`; Cột 4: `製造`; Cột 5: `製造`
- **Dòng 11**: Cột 1: `1412000057`; Cột 2: `EI1課`; Cột 3: `49.`; Cột 4: `製造`; Cột 5: `製造`
- **Dòng 12**: Cột 1: `1412000078`; Cột 2: `ESD1課`; Cột 3: `50.`; Cột 4: `製造`; Cột 5: `製造`
- **Dòng 13**: Cột 1: `1412000062`; Cột 2: `機器製造管理課`; Cột 3: `3.`; Cột 4: `部内間接`; Cột 5: `製造`
- **Dòng 14**: Cột 1: `1412000036`; Cột 2: `部品管理1課`; Cột 3: `13.`; Cột 4: `部内間接`; Cột 5: `製造`
- **Dòng 15**: Cột 1: `1412000103`; Cột 2: `部品管理2課`; Cột 3: `69.`; Cột 4: `部内間接`; Cột 5: `製造`
- **Dòng 16**: Cột 1: `1412000063`; Cột 2: `トナー製造管理課`; Cột 3: `38.`; Cột 4: `部内間接`; Cột 5: `製造`
- **Dòng 17**: Cột 1: `1412000048`; Cột 2: `トナー生産技術課`; Cột 3: `5.`; Cột 4: `部内間接`; Cột 5: `製造`
- **Dòng 18**: Cột 1: `1412000055`; Cột 2: `トナー品質管理課`; Cột 3: `6.`; Cột 4: `部内間接`; Cột 5: `製造`
- **Dòng 19**: Cột 1: `1412000073`; Cột 2: `物流管理課`; Cột 3: `46.`; Cột 4: `部内間接`; Cột 5: `製造`
- **Dòng 20**: Cột 1: `1412000008`; Cột 2: `生産管理課`; Cột 3: `10.`; Cột 4: `部内間接`; Cột 5: `製造`
- **Dòng 21**: Cột 1: `1412000094`; Cột 2: `部品在庫管理課`; Cột 3: `61.`; Cột 4: `部内間接`; Cột 5: `製造`
- **Dòng 22**: Cột 1: `1412000080`; Cột 2: `部品技術課`; Cột 3: `20.`; Cột 4: `部内間接`; Cột 5: `製造`
- **Dòng 23**: Cột 1: `1412000087`; Cột 2: `部品製造管理課`; Cột 3: `55.`; Cột 4: `部内間接`; Cột 5: `製造`
- **Dòng 24**: Cột 1: `1412000088`; Cột 2: `品質管理課`; Cột 3: `56.`; Cột 4: `部内間接`; Cột 5: `製造`
- **Dòng 25**: Cột 1: `1412000072`; Cột 2: `製品管理課`; Cột 3: `45.`; Cột 4: `部内間接`; Cột 5: `販売`
- **Dòng 26**: Cột 1: `1412000053`; Cột 2: `工程品質管理1課`; Cột 3: `9.`; Cột 4: `部内間接`; Cột 5: `製造`
- **Dòng 27**: Cột 1: `1412000104`; Cột 2: `工程品質管理2課`; Cột 3: `47.`; Cột 4: `部内間接`; Cột 5: `製造`
- **Dòng 28**: Cột 1: `1412000105`; Cột 2: `工程品質管理3課`; Cột 3: `70.`; Cột 4: `部内間接`; Cột 5: `製造`
- **Dòng 29**: Cột 1: `1412000075`; Cột 2: `工程品質管理4課`; Cột 3: `71.`; Cột 4: `部内間接`; Cột 5: `製造`
- **Dòng 30**: Cột 1: `1412000044`; Cột 2: `金型技術課`; Cột 3: `22.`; Cột 4: `部内間接`; Cột 5: `製造`
- **Dòng 31**: Cột 1: `1412000054`; Cột 2: `マスター管理課`; Cột 3: `12.`; Cột 4: `部外間接1`; Cột 5: `製造`
- **Dòng 32**: Cột 1: `1412000010`; Cột 2: `採算管理課`; Cột 3: `11.`; Cột 4: `部外間接1`; Cột 5: `製造`
- **Dòng 33**: Cột 1: `1412000013`; Cột 2: `部品検査1課`; Cột 3: `18.`; Cột 4: `部外間接1`; Cột 5: `製造`
- **Dòng 34**: Cột 1: `1412000092`; Cột 2: `部品検査2課`; Cột 3: `59.`; Cột 4: `部外間接1`; Cột 5: `製造`
- **Dòng 35**: Cột 1: `1412000035`; Cột 2: `部品品質管理1課`; Cột 3: `40.`; Cột 4: `部内間接`; Cột 5: `製造`
- **Dòng 36**: Cột 1: `1412000108`; Cột 2: `部品品質管理2課`; Cột 3: `74.`; Cột 4: `部内間接`; Cột 5: `製造`
- **Dòng 37**: Cột 1: `1412000006`; Cột 2: `メカ製造技術1課`; Cột 3: `14.`; Cột 4: `部外間接1`; Cột 5: `製造`
- **Dòng 38**: Cột 1: `1412000089`; Cột 2: `メカ製造技術2課`; Cột 3: `15.`; Cột 4: `部外間接1`; Cột 5: `製造`
- **Dòng 39**: Cột 1: `1412000040`; Cột 2: `電気製造技術課`; Cột 3: `16.`; Cột 4: `部外間接1`; Cột 5: `製造`
- **Dòng 40**: Cột 1: `1412000106`; Cột 2: `製造システム開発課`; Cột 3: `72.`; Cột 4: `部外間接1`; Cột 5: `製造`
- **Dòng 41**: Cột 1: `1412000039`; Cột 2: `製造技術管理課`; Cột 3: `73.`; Cột 4: `部外間接1`; Cột 5: `製造`
- **Dòng 42**: Cột 1: `1412000016`; Cột 2: `生産技術1課`; Cột 3: `42.`; Cột 4: `部外間接1`; Cột 5: `製造`
- **Dòng 43**: Cột 1: `1412000069`; Cột 2: `生産技術2課`; Cột 3: `43.`; Cột 4: `部外間接1`; Cột 5: `製造`
- **Dòng 44**: Cột 1: `1412000084`; Cột 2: `生産技術3課`; Cột 3: `54.`; Cột 4: `部外間接1`; Cột 5: `製造`
- **Dòng 45**: Cột 1: `1412000018`; Cột 2: `品質保証課`; Cột 3: `24.`; Cột 4: `部外間接2`; Cột 5: `製造`
- **Dòng 46**: Cột 1: `1412000019`; Cột 2: `製品保証課`; Cột 3: `25.`; Cột 4: `部外間接2`; Cột 5: `製造`
- **Dòng 47**: Cột 1: `1412000058`; Cột 2: `第1資材課`; Cột 3: `26.`; Cột 4: `部外間接2`; Cột 5: `製造`
- **Dòng 48**: Cột 1: `1412000042`; Cột 2: `第2資材課`; Cột 3: `27.`; Cột 4: `部外間接2`; Cột 5: `製造`
- **Dòng 49**: Cột 1: `1412000021`; Cột 2: `第3資材課`; Cột 3: `28.`; Cột 4: `部外間接2`; Cột 5: `製造`
- **Dòng 50**: Cột 1: `1412000070`; Cột 2: `第4資材課`; Cột 3: `44.`; Cột 4: `部外間接2`; Cột 5: `製造`
- **Dòng 51**: Cột 1: `1412000022`; Cột 2: `資材管理課`; Cột 3: `29.`; Cột 4: `部外間接2`; Cột 5: `製造`
- **Dòng 52**: Cột 1: `1412000024`; Cột 2: `総務課`; Cột 3: `30.`; Cột 4: `工場間接`; Cột 5: `一般`
- **Dòng 53**: Cột 1: `1412000025`; Cột 2: `人事課`; Cột 3: `31.`; Cột 4: `工場間接`; Cột 5: `一般`
- **Dòng 54**: Cột 1: `1412000026`; Cột 2: `施設課`; Cột 3: `32.`; Cột 4: `工場間接`; Cột 5: `一般`
- **Dòng 55**: Cột 1: `1412000093`; Cột 2: `リスクマネジメント課`; Cột 3: `60.`; Cột 4: `工場間接`; Cột 5: `一般`
- **Dòng 56**: Cột 1: `1412000028`; Cột 2: `会計課`; Cột 3: `33.`; Cột 4: `工場間接`; Cột 5: `一般`
- **Dòng 57**: Cột 1: `1412000029`; Cột 2: `経営管理課`; Cột 3: `34.`; Cột 4: `工場間接`; Cột 5: `一般`
- **Dòng 58**: Cột 1: `1412000091`; Cột 2: `保安課`; Cột 3: `58.`; Cột 4: `工場間接`; Cột 5: `一般`
- **Dòng 59**: Cột 1: `1412000086`; Cột 2: `情報システム課`; Cột 3: `36.`; Cột 4: `工場間接`; Cột 5: `一般`
- **Dòng 60**: Cột 1: `1412C00001`; Cột 2: `労働組合`; Cột 3: `51.`
- **Dòng 61**: Cột 1: `1412000030`; Cột 2: `貿易管理課`; Cột 3: `35.`; Cột 4: `工場間接`; Cột 5: `販売`
- **Dòng 62**: Cột 1: `1412000098`; Cột 2: `電工製造課`; Cột 3: `64.`; Cột 4: `製造`; Cột 5: `製造`
- **Dòng 63**: Cột 1: `1412000096`; Cột 2: `ESD2課`; Cột 3: `63.`; Cột 4: `製造`; Cột 5: `製造`
- **Dòng 64**: Cột 1: `1412000099`; Cột 2: `MD4課`; Cột 3: `65.`; Cột 4: `製造`; Cột 5: `製造`
- **Dòng 65**: Cột 1: `1412000100`; Cột 2: `MD5課`; Cột 3: `68.`; Cột 4: `製造`; Cột 5: `製造`
- **Dòng 66**: Cột 1: `1412000101`; Cột 2: `EI2課`; Cột 3: `66.`; Cột 4: `製造`; Cột 5: `製造`

---
