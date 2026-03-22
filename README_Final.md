# MP2027 Manager - Hướng dẫn sử dụng (V3.0 Standalone)

Hệ thống tự động hóa lập ngân sách (MP) theo mô hình Hub-centric, hỗ trợ giao diện đồ họa (GUI) và có tính vạn năng (Universal) cho các năm tài chính tiếp theo.

## 1. Chuẩn bị
*   **File nguồn**: Đảm bảo các file Excel của phòng ban (Facility, GA, IT Sim, Fixed Assets) nằm trong một thư mục (Mặc định là thư mục chứa phần mềm).
*   **File Template**: File `FORM.xlsx` (file đích cần đổ dữ liệu).

## 2. Cách khởi động
1.  Double-click vào file `run_MP2027.bat`.
2.  Cửa sổ Giao diện sẽ hiện ra.

## 3. Các bước thực hiện trên Giao diện
*   **Năm tài chính**: Nhập năm bạn muốn lập kế hoạch (Ví dụ: `2027`, `2028`).
*   **File Template**: Nhấn "Duyệt..." và chọn file `FORM.xlsx`.
*   **Thư mục nguồn**: Nhấn "Duyệt..." và chọn thư mục chứa các file dữ liệu đầu vào.
*   **Chạy**: Nhấn nút **BẮT ĐẦU CHẠY PIPELINE**.

## 4. Kết quả
*   File báo cáo mới sẽ được sinh ra với tên: `FORM_GENERATED_FY[Năm].xlsx`.
*   Tất cả công thức trong file đều được bảo toàn 100%.

---
**Lưu ý**: Nếu bạn muốn đóng gói thành file `.exe` duy nhất để gửi cho người khác, hãy đọc hướng dẫn chi tiết trong file `walkthrough.md`.
