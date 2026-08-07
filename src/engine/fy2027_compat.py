"""Siêu dữ liệu tương thích chỉ dành riêng cho FY2027.

Các lần chạy năm tài chính mới nhận thứ tự tệp từ ``FiscalRunContext`` và không
được nhập mô-đun này. Tên tệp chỉ còn để mở các sổ FY2027 lịch sử và kiểm thử bộ
ghi mà không thay đổi bố cục FY2027 đã được chấp nhận.
"""

FY2027_COMPAT_SOURCE_FILE_ORDER = (
    "施設課　MPFY2027.xlsx",
    "固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx",
    "システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls",
    "総務課 FY2027 MP 振替予定.xlsx",
    "Sinh nhật MP FY2027.xlsx",
    "FY2027配賦額一覧 (2025.12.29).xlsx",
    "Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx",
)
