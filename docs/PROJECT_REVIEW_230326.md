# 📊 BÁO CÁO DỰ ÁN: MP2027 Manager (Review 23/03/2026)

## 🎯 App này làm gì?
Đây là hệ thống tự động hóa lập kế hoạch ngân sách (Mid-term Plan - MP) cho năm tài chính 2027. App giúp thay thế việc nhập liệu thủ công bằng cách tự động trích xuất dữ liệu Headcount, Khấu hao, Tỷ giá từ các file nguồn (GA, IT Sim, Fixed Assets) và đẩy vào file biểu mẫu Excel chuẩn (`FORM.xlsx`).

## 📁 Cấu trúc chính
```text
C:\ProgramData\Sandbox\MP2027
├── src/                # Mã nguồn sạch (Đã Refactor)
│   ├── engine/         # Logic xây dựng Hub/Excel (HubBuilder)
│   ├── parsers/        # Các bộ đọc file Excel (GA, Facility, IT...)
│   ├── db/             # Kết nối SQLite & Schema
│   └── universal_app.py # Giao diện GUI chính
├── data/               # Chứa DB sqlite (mp2027.db)
├── scripts/            # Các script chạy pipeline (run_e2e.py)
├── OUTPUT_FY2027/      # Kết quả xuất file Excel
└── .brain/             # Tri thức hệ thống (brain.json, session.json)
```

## 🛠️ Công nghệ sử dụng
| Thành phần | Công nghệ |
|------------|-----------|
| Ngôn ngữ | Python 3.12+ |
| Giao diện | Tkinter |
| Xử lý Excel | Pandas, Openpyxl, Xlrd |
| Cơ sở dữ liệu| SQLite |

## 🚀 Cách chạy
1. **Chạy GUI (Khuyên dùng)**: `py src/universal_app.py` (hoặc dùng `run_MP2027.bat`).
2. **Chạy Pipeline CLI**: `py scripts/run_e2e.py`.

## 📍 Đang làm dở gì?
- **Trạng thái**: 🛠️ **ĐANG THỰC HIỆN HOTFIX P1**.
- **Vấn đề**: Phát hiện file GA nguồn (`総務課...`) không chứa Headcount chi tiết từng CC mà chỉ có tổng công ty.
- **Giải pháp**: Đang điều chỉnh `src/engine/allocator.py` để dùng tổng Headcount GA làm tỉ lệ biến đổi cho Headcount tĩnh của từng CC.
- **Task tiếp theo**: Hoàn tất logic phân bổ Driver và kiểm tra lại OUTPUT.

## 📝 Các file quan trọng cần biết
| File | Chức năng |
|------|-----------|
| `src/universal_app.py` | Cổng vào chính của ứng dụng (Giao diện). |
| `src/parsers/ga.py` | Bộ parser quan trọng nhất (Xử lý Headcount monthly). |
| `src/engine/hub_builder.py`| "Trái tim" của hệ thống - nạp dữ liệu vào Template Excel. |
| `data/mp2027.db` | Nơi lưu trữ toàn bộ dữ liệu trung gian để tính toán. |

## ⚠️ Lưu ý khi tiếp nhận
- **Encoding**: Code đã được làm sạch 100% emoji để chạy mượt trên Windows Terminal (CP932). Tuyệt đối không thêm emoji vào lệnh `print` hoặc `log`.
- **Fiscal Year**: Hệ thống tự động bóc tách `FY2027` thành số `2027`, không cần chỉnh sửa thủ công.
- **Tỷ giá**: Được lấy động từ file `FORM.xlsx` (ô `B2`), đảm bảo tính nhất quán.
