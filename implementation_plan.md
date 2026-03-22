# MP2027 Manager — Implementation Plan (V4.1.0)

## Goal
Xây dựng công cụ Python tự động hóa lập kế hoạch tài chính FY2027, theo mô hình **Hub-centric**. 
Đặc biệt tập trung vào việc xử lý chính xác thời điểm dừng khấu hao và biến động nhân sự.

## Core Mandates
1. **Dừng khấu hao đúng lúc**: Dựa vào cột 'Last Depreciation Month' trong file nguồn.
2. **Tỷ giá động**: Lấy từ ô B2 của file FORM.xlsx.
3. **Phân loại CC chuẩn**: Chỉ dùng 製造, 一般, 販売.
4. **Bảo toàn công thức**: Dùng openpyxl để ghi dữ liệu mà không hỏng công thức Excel.

## Refactor Path
Agent tiếp theo cần sửa đổi:
- src/parsers/fixed_assets.py: Để đọc thêm cột 15 (tháng cuối), cột 16 (giá trị tháng cuối), cột 21, 22 (lãi).
- src/engine/allocator.py: Để áp dụng logic so sánh tháng.

Xem chi tiết tọa độ cột và logic tại: REFACTORING_SPEC_V4.md.
