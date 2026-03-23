# 📊 MP2027 Manager: Giải pháp Quản trị Tài chính thông minh

**MP2027 Manager** (Phần mềm Saisan MP) là hệ thống tự động hóa cốt lõi dành cho việc lập kế hoạch ngân sách và phân bổ chi phí cho năm tài chính **FY2027**. Hệ thống được thiết kế để chuẩn hóa dữ liệu từ nhiều nguồn khác nhau, thực hiện tính toán vĩ mô và xuất báo cáo chính xác theo tiêu chuẩn nội bộ.

---

## 🚀 Tính năng Cốt lõi (V6.0.0)

### 1. 🇻🇳 Việt hóa Toàn diện
- Toàn bộ tài liệu kỹ thuật (`GEMINI.md`) và hệ thống tri thức (`.brain/`) đã được dịch sang Tiếng Việt chuyên sâu, giúp đội ngũ vận hành dễ dàng tiếp cận.

### 2. 🧩 Khớp mã Trung tâm Chi phí (CC) Linh hoạt
- Thuật toán thông minh tự động ánh xạ các mã CC từ 4 đến 8 chữ số từ nguồn GA vào mã chuẩn 10 chữ số trong Master Data thông qua cơ chế khớp hậu tố (suffix matching).

### 3. ⚙️ Bộ máy Phân bổ Chi phí (Administrative Allocation) đa ngôn ngữ
- Hỗ trợ các quy tắc hạch toán tháng (`posting_month`) bằng cả Tiếng Việt và Tiếng Nhật (ví dụ: "tháng vào làm", "tháng tiếp theo", "入社月", "翌月").
- Đảm bảo tính nhất quán tuyệt đối giữa dữ liệu nhân sự (Headcount) và các driver vận hành (Working Days).

### 4. 📈 Quy trình E2E Siêu tốc
- Pipeline xử lý dữ liệu đầu-cuối: Từ khâu nạp dữ liệu thô (Fixed Assets, IT Sim, Facility) đến khâu xuất hơn 60 file Excel báo cáo chi tiết cho từng bộ phận chỉ trong vài phút.

---

## 💻 Công nghệ Sử dụng
- **Ngôn ngữ**: Python 3.13+
- **Cơ sở dữ liệu**: SQLite 3 (Lưu trữ tập trung, đảm bảo tính nhất quán)
- **Xử lý dữ liệu**: Pandas, Openpyxl, Xlrd
- **Giao diện**: Tkinter (Universal App GUI)

---

## 📁 Cấu trúc Thư mục Chính
- `src/`: Mã nguồn cốt lõi (Allocator, Parsers, DB Loaders).
- `data/`: Lưu trữ Database và các file Driver tham chiếu.
- `docs/`: Tài liệu hướng dẫn chi tiết dành cho người dùng.
- `OUTPUT_FY2027/`: Thư mục lưu trữ kết quả báo cáo sau khi chạy.

---

## 🛠️ Hướng dẫn Cài đặt & Chạy
1. Đảm bảo đã cài đặt Python 3.13.
2. Chạy file khởi động nhanh:
   ```cmd
   run_MP2027.bat
   ```
3. Hoặc chạy trực tiếp giao diện GUI:
   ```bash
   py src/universal_app.py
   ```

---

## 📝 Lưu ý Quan trọng
- Dữ liệu `working_days` giờ đây được quản lý độc lập trong bảng `sys_params` thay vì lấy từ nhân sự.
- Luôn kiểm tra file `FORM.xlsx` (Master Template) trước khi chạy batch export hàng loạt.

---
**Được phát triển bởi Nakazasen - Tự động hóa để dẫn đầu.**
