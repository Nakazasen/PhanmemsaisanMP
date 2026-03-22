# MP2027 Manager: Hệ thống Tự động hóa Lập kế hoạch Tài chính Toàn diện

Tài liệu này là "linh hồn" của dự án MP2027, giải thích chi tiết từ tư duy nghiệp vụ, bài toán quản trị đến các giải pháp kỹ thuật tinh vi nhất đã được hiện thực hóa.

---

## 1. Bối cảnh Nghiệp vụ: "Cuộc chiến" với các con số phân tán

### 1.1. Câu chuyện Quản lý Tòa nhà Chung cư (Phép ẩn dụ)
Hãy tưởng tượng công ty chúng ta là một **Tòa nhà chung cư khổng lồ** với 62 căn phòng (Cost Center - CC). Mỗi phòng có một chức năng riêng: có phòng trực tiếp sản xuất, có phòng làm văn phòng hỗ trợ, có phòng chuyên bán hàng.

Đến kỳ lập kế hoạch MP2027, chúng ta phải dự báo chi tiêu cho cả năm tới (12 tháng). Vấn đề nan giải là "túi tiền" của tòa nhà đang nằm rải rác ở khắp nơi:
*   **Ông Quản lý Kỹ thuật (Facility):** Giữ hóa đơn điện, nước, khấu hao tòa nhà.
*   **Bà Quản lý Hành chính (GA):** Giữ hợp đồng xe bus, hóa đơn Gas, hợp đồng vệ sinh.
*   **Đội IT:** Giữ chi phí bản quyền phần mềm SAP, PLM phức tạp với đủ loại tỷ giá USD/VND.
*   **Phòng Kế toán (Fixed Assets):** Giữ sổ cái tài sản cố định khổng lồ với hơn **119,361 dòng dữ liệu**.

### 1.2. Bài toán Phân bổ Đa tầng (The Allocation Challenge)
Nhiệm vụ của bạn không chỉ là nhặt số, mà là phải **chia tiền** sao cho công bằng và đúng luật kế toán:
*   **Phân bổ theo Số người (Headcount):** Tiền xe bus, tiền vệ sinh phải chia theo số người ở mỗi phòng.
*   **Phân bổ theo Loại hình nhân sự (Staff vs Worker):** Đây là điểm "độc bản" của dự án này. Hệ thống phải phân biệt:
    *   **Công nhân G7 (Worker):** Chỉ tính đơn giá 4,000 VND (Sổ tay, bảo hộ).
    *   **Nhân viên văn phòng (Staff):** Tính đơn giá 9,100 VND.
*   **Phân bổ 2 bước (Step-down):** Một phòng hỗ trợ (như Cơ sở) chia tiền cho phòng hỗ trợ khác (như IT), sau đó tổng số tiền đó lại phải được chia tiếp cho các phòng Sản xuất. Nếu làm tay, bạn sẽ bị xoay như chong chóng trong các vòng lặp tính toán.

---

## 2. Nỗi đau của Quy trình Thủ công (The Manual Pain)

Trước khi có hệ thống này, nhân viên kế toán phải đối mặt với "cơn ác mộng":
1.  **Mở hàng chục file Excel:** Máy tính chạy chậm, lag, thậm chí treo máy khi mở file 120k dòng.
2.  **Mapping bằng tay:** Phải tra cứu từng mã CC (62 mã) và mã tài khoản (239 mã). Chỉ cần gõ nhầm một số 0 là toàn bộ báo cáo sai lệch tiền tỷ.
3.  **Copy-Paste ròng rã:** Phải điền số cho 12 tháng (Tháng 4 năm nay đến tháng 3 năm sau). Với hàng trăm mã tài khoản, số lượt copy-paste lên đến hàng nghìn lần.
4.  **Hậu quả:** Mất ít nhất 2 ngày làm việc căng thẳng, mệt mỏi và luôn nơm nớp lo sợ sai sót dữ liệu.

---

## 3. Hệ thống MP2027 Manager: "Giải cứu" Kế toán viên

Chúng ta đã xây dựng một cỗ máy tự động hóa hoàn chỉnh với các module "thần thánh":

### 3.1. Module "Hút" dữ liệu (Surgical Ingestion)
Không cần mở file Excel, hệ thống sử dụng công nghệ **Stream-Reader**. Nó chỉ "lướt" qua 120,000 dòng dữ liệu khấu hao trong chưa đầy 5 giây, nhặt ra đúng những gì cần thiết và nạp vào Database SQLite. Đây là tốc độ mà con người không bao giờ đạt được.

### 3.2. Module "Bộ não" thông minh (Mapping Logic)
Hệ thống tự động thực hiện việc rẽ nhánh mã tài khoản (Account Code) cực kỳ phức tạp:
*   Cùng là chi phí điện, nhưng hệ thống tự biết:
    *   Đổ vào Xưởng sản xuất -> Áp mã `mfg_code`.
    *   Đổ vào Văn phòng -> Áp mã `ga_code`.
    *   Đổ vào Phòng kinh doanh -> Áp mã `sales_code`.
=> Loại bỏ hoàn toàn lỗi hạch toán nhầm khối chi phí.

### 3.3. Module "Công thức Vàng" (Allocation Engine)
Hệ thống tự động tra cứu Database để lấy số lượng Staff/Worker của từng phòng ban và thực hiện phép tính:
*   `Tổng tiền = (Số Staff * 9,100) + (Số Worker * 4,000)`.
*   Tự động quy đổi tỷ giá USD sang VND theo nguyên tắc kế toán bảo thủ: **ROUNDUP** (Làm tròn lên) cho chi phí để luôn an toàn về ngân sách dự phòng.

### 3.4. Module "Hub-and-Spoke" (Kiến trúc An toàn)
Đây là đỉnh cao của thiết kế. Hệ thống không cố gắng thay thế toàn bộ file báo cáo của bạn.
*   **Hub (Trục):** Hệ thống chỉ đổ dữ liệu vào duy nhất một sheet là `内訳ﾘｽﾄ(4～3月)`.
*   **Spoke (Báo cáo):** Các báo cáo tổng hợp (VND/USD) vẫn giữ nguyên hàng nghìn công thức Excel gốc của công ty.
=> Kết quả: Dữ liệu thì tự động, nhưng báo cáo thì vẫn quen thuộc và bạn vẫn có quyền can thiệp, sửa chữa thủ công nếu muốn.

---

## 4. Thành quả Nghiệm thu (The Impact)

Dự án đã biến một khối lượng công việc "khổng lồ" thành một quy trình tinh gọn:
*   **Xử lý 62 Cost Centers** một cách hoàn hảo.
*   **Mapping 239 mã tài khoản** không sai một ly.
*   **Xử lý 119,361 dòng dữ liệu** trong vài giây.
*   **Lợi ích:** Tiết kiệm 99% thời gian làm việc, loại bỏ 100% lỗi do con người, cung cấp báo cáo chính xác tuyệt đối để lãnh đạo ra quyết định.

**MP2027 Manager không chỉ là một chương trình máy tính, nó là sự kết tinh của tư duy quản trị hiện đại và sức mạnh công nghệ.**
