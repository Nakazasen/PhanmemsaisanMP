# 📋 TÀI LIỆU ĐẶC TẢ KỸ THUẬT CHI TIẾT (REF_SPEC V4.4.0)
## DỰ ÁN: REFACTOR MP2027 MANAGER - "FIXING THE BROKEN LOGIC"

> **DÀNH CHO AGENT TIẾP THEO:** Đây là dự án đang trong quá trình Refactor khẩn cấp vì code cũ (v4.0.2) đang sai logic nghiệp vụ nghiêm trọng. Đừng vội viết code, hãy đọc kỹ chỉ dẫn dưới đây.

---

## 1. 🔍 KIỂM TOÁN CÁC SAI LẦM CŨ (THE AUDIT)
- **Lỗi Tỷ giá:** Đang hardcode 25450. **Sửa:** Phải lấy từ ô **`B2`** của file `FORM.xlsx` (SSOT).
- **Lỗi Khấu hao:** Đang điền 12 tháng giống nhau. **Sửa:** Phải so sánh với `Last Depreciation Month` (Cột 15) để dừng tính tiền đúng lúc (Case No.3, No.23).
- **Lỗi GA Driver (QUAN TRỌNG):** Đang dùng nhân sự tĩnh. **Sửa:** Bắt buộc dùng **Lựa chọn 2 (HR file biến động hàng tháng)**. Phải tìm bảng "Nhân sự 12 tháng" trong sheet `稼働日` (FORM.xlsx) hoặc file GA.

---

## 2. 📑 TOẠ ĐỘ DỮ LIỆU (MAPPING BIBLE)

### A. File "固定資産情報...xlsx" (Khấu hao)
- **Dòng tiêu đề:** Dòng 3 (Index 3).
- **Cột 7 (Col H):** Mã Cost Center.
- **Cột 11 (Col L):** Số tiền khấu hao hàng tháng.
- **Cột 15 (Col P):** `Last Depreciation Month` (Tháng kết thúc khấu hao - Datetime).
- **Cột 16 (Col Q):** `Last Month Depr` (Giá trị tháng cuối).
- **Cột 21, 22:** Lãi tháng 4 và Lãi từ tháng 5.

### B. File "FORM.xlsx" (Hub)
- **Ô B2:** Tỷ giá USD/VND (Phải đọc ô này ĐẦU TIÊN).
- **Sheet `内訳ﾘｽﾄ(4～3月)`:** Nơi đổ dữ liệu kết quả (Cột B: Mã TK, Cột C: Mã CC, Cột F-Q: 12 tháng).
- **Sheet `稼働日`:** Tìm bảng nhân sự biến động 12 tháng tại đây để làm Driver cho GA.

---

## 3. 🧠 THUẬT TOÁN ENGINE (LOGIC FLOW)

### Bước 1: Khởi tạo (MANDATORY)
1. Đọc ô **`B2`** lấy `EXCHANGE_RATE`.
2. Tìm bảng nhân sự 12 tháng để nạp vào bộ nhớ (Monthly Headcount Cache).

### Bước 2: Xử lý Khấu hao (Dành cho mỗi dòng FA)
Duyệt qua 12 tháng (`curr_month`):
- **Nếu `curr_month < Last_Depreciation_Month`**: `VND = Depreciation_Amount * EXCHANGE_RATE`.
- **Nếu `curr_month == Last_Depreciation_Month`**: `VND = Last_Month_Depr * EXCHANGE_RATE`.
- **Nếu `curr_month > Last_Depreciation_Month`**: `VND = 0`.

### Bước 3: Xử lý GA (Số người biến động)
1. Lookup số người của CC ban tại tháng đó: `HC_current = get_hc(cc_code, month)`.
2. Tính toán: `VND = HC_current * Unit_Price`.
   - Gas: `39,309`.
   - VPN: `3.19 * EXCHANGE_RATE`.
   - Sổ tay (Staff/G7): `9,100 / 4,000`.

---

## 4. 🛠️ CHỈ THỊ THỰC THI (STEP-BY-STEP)
1. Sửa `src/parsers/fixed_assets.py` để lấy đủ các cột nghiệp vụ (15, 16, 21, 22).
2. Sửa `src/engine/allocator.py`: Implement logic so sánh tháng và lookup driver biến động.
3. Chạy Unit Test Case No.23: Tháng 11/2026 có số, tháng 12/2026 phải bằng 0 VND.
4. Kiểm tra tỷ giá: Đổi ô B2 và xem kết kết quả có tự cập nhật không.

---
**NGHIÊM CẤM:** Không được sử dụng bất kỳ con số hardcode nào hoặc driver tĩnh từ Database cho GA.
