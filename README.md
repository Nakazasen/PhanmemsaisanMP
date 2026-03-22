# 🚀 MP2027 Manager: Hệ thống Tự động hóa Lập kế hoạch Tài chính

**MP2027 Manager** là một giải pháp tự động hóa toàn diện, giúp các phòng ban (Kỹ thuật, Hành chính, IT, Kế toán) dễ dàng lập kế hoạch tài chính (Master Plan) cho năm tài chính FY2027 (4/2026 - 3/2027). Hệ thống thay thế quy trình nhập liệu thủ công chậm chạp và dễ sai sót bằng một quy trình \"siêu tốc\" và chính xác tuyệt đối.

---

## ✨ Tính năng Nổi bật (V3.5 - Bản cập nhật Mới nhất)

### 1. 💹 Tỷ giá USD/VND Linh hoạt
- Người dùng có thể **tự nhập tỷ giá** ngay trên giao diện chính (Mặc định: 25,450).
- Hệ thống tự động quy đổi chính xác các khoản chi phí ngoại tệ (Khấu hao, Lãi vay, Phí SAP/PLM/AMS) sang VND trước khi đổ vào báo cáo.

### 2. 📦 Chế độ Xuất Báo cáo \"Siêu cấp\" (Flexible Export)
Hệ thống hỗ trợ 2 chế độ xử lý linh hoạt:
- **Chế độ Đơn lẻ (Single Export):** Nhập mã Cost Center cụ thể (ví dụ: 1412000089) để xuất nhanh 1 file báo cáo duy nhất. Cực kỳ hữu ích để kiểm tra sai lệch cho một phòng ban.
- **Chế độ Hàng loạt (Batch Export):** Để trống ô mã phòng, chương trình sẽ tự động quét toàn bộ 62 phòng ban và tạo ra **62 file Excel riêng biệt** chỉ trong vài phút. Kết quả được lưu gọn gàng trong thư mục OUTPUT_FY2027.

### 3. 🛠️ Sửa lỗi Triệt để & Tối ưu hóa Excel
- **Fix lỗi #N/A:** Đồng bộ hóa tiêu đề tháng (Tháng 4 -> Tháng 3) vào đúng các cột F đến Q.
- **Fix lỗi Số thập phân:** Tự động làm tròn toàn bộ số tiền về số nguyên (int) để vượt qua dòng kiểm tra CHECK (経費→小数点) của file mẫu Excel.
- **Bảo vệ Công thức:** Dữ liệu được đổ từ Dòng 29 trở đi, bảo vệ các hàng tiêu đề và công thức tổng hợp ở phía trên.

---

## 🏗️ Kiến trúc Hệ thống (Hub-centric Design)
Hệ thống hoạt động theo mô hình **Hub-and-Spoke**:
- **Hub (Trục):** Chương trình đổ dữ liệu vào duy nhất sheet 内訳ﾘｽﾄ(4～3月).
- **Spoke (Báo cáo):** Các sheet báo cáo (採算表 VND/USD) tự động tính toán dựa trên công thức Excel gốc, đảm bảo tính nhất quán và quen thuộc cho người dùng.

---

## 📂 Cấu trúc Dự án
`	ext
C:\ProgramData\Sandbox\MP2027\
├── src\
│   ├── universal_app.py      # Giao diện đồ họa (GUI)
│   ├── engine\
│   │   ├── hub_builder.py    # Bộ não xuất file Excel & Sửa lỗi hiển thị
│   │   └── allocator.py      # Bộ máy phân bổ chi phí đa tầng
│   └── parsers\              # Các module đọc dữ liệu (Facility, GA, IT, Fixed Assets)
├── scripts\
│   └── run_e2e.py            # Luồng xử lý dữ liệu (Pipeline)
├── data\
│   └── mp2027.db             # Cơ sở dữ liệu SQLite (Lưu trữ tập trung)
└── run_MP2027.bat            # File chạy ứng dụng duy nhất cho người dùng
`

---

## 🚀 Hướng dẫn Sử dụng
1.  Chạy file un_MP2027.bat.
2.  Chọn **Năm tài chính** (2027).
3.  Nhập **Tỷ giá USD/VND** hiện tại.
4.  Nhập **Mã Cost Center** (nếu muốn làm 1 phòng) hoặc **để trống** (để làm cho cả công ty).
5.  Chọn đường dẫn file FORM.xlsx và thư mục chứa dữ liệu nguồn.
6.  Nhấn **BẮT ĐẦU CHẠY PIPELINE** và đợi thành quả trong thư mục đầu ra.

---
**Được phát triển bởi Nakazasen - Giải pháp Tự động hóa Tài chính Chuyên nghiệp.**
