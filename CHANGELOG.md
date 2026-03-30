# Changelog - MP2027 Manager

## [V5.3 - Ultimate Sync] - 2026-03-30
### Added
- **Hệ thống đồng bộ 3 lớp (Ultimate Sync)**: Đảm bảo dữ liệu Master (CC, Account) luôn mới nhất.
  1. **Startup Check**: Tự động so sánh Timestamp của `FORM.xlsx` để nạp lại dữ liệu nếu có thay đổi.
  2. **Manual Refresh**: Thêm nút 🔄 bên cạnh danh sách CC để người dùng chủ động làm mới.
  3. **Pre-Pipeline Sync**: Tự động đồng bộ Master Data ngay trước khi bắt đầu tính toán Pipeline.
- **Tính năng Consistency**: Xóa sạch bảng Master cũ trước khi nạp mới, giúp loại bỏ các mã CC đã bị xóa trong file Excel.

### Changed
- **Packaging V5.3**: Đóng gói lại thành file thực thi duy nhất `dist/MP2027_Manager.exe`.
- Cập nhật GUI: Bốc tách Combobox CC và nút Refresh vào Frame riêng để bố cục chuyên nghiệp.

### Fixed
- Lỗi mã CC bị "rác" (tồn đọng mã cũ) khi đồng bộ nhiều lần từ file Excel khác nhau.
- Sửa lỗi đường dẫn tương đối khi chạy từ file `.exe` bằng `sys.frozen`.

---

## [V3.0.0] - 2026-03-22
### Added
- **Giao diện người dùng (GUI)** chuyên nghiệp bằng `tkinter`.
- Hỗ trợ **Universal Fiscal Year**: Người dùng có thể nhập năm bất kỳ.
- Chế độ chọn đường dẫn file/thư mục thay vì hard-code.
- Hướng dẫn đóng gói thành file `.exe` bằng PyInstaller.
- File `README_Final.md` hướng dẫn sử dụng cho người dùng cuối.

### Changed
- Refactor toàn bộ Parser (`facility`, `ga`, `it_sim`, `fixed_assets`) để nhận tham số năm và thư mục động.
- Nâng cấp `scripts/run_e2e.py` thành Pipeline điều phối trung tâm.
- Cập nhật `run_MP2027.bat` để khởi chạy GUI mặc định.

### Fixed
- Lỗi `ImportError` do thiếu mapping `FY_MONTHS` trong Engine.
- Lỗi null headcount khi nhân với đơn giá.

---

## [V2.0.0] - 2026-03-21
### Added
- Hoàn thành MVP với 6 Phase xử lý.
- Tích hợp 4 nguồn dữ liệu Excel chính.
- Allocation Engine hỗ trợ 4 loại driver.
- Hub Builder xuất dữ liệu bảo toàn công thức Excel.

### Fixed
- Hiệu năng đọc file Fixed Assets (119k dòng) bằng openpyxl streaming.
