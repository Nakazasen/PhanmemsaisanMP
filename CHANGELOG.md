# Changelog - MP2027 Manager

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
