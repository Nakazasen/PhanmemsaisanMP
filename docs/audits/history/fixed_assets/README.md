# Lịch sử audit chi phí tài sản cố định

Mỗi lần chạy `py scripts/classify_fixed_assets_mismatches.py`, hệ thống tạo một thư mục mới theo mã lần chạy (`fa-...`). Không được sửa hoặc ghi đè các thư mục đã tạo.

Mỗi lần chạy lưu:

- `fixed_assets_true_mismatch_decision_matrix_...csv`: từng ô chênh lệch, số theo sổ nguồn, số file phòng ban, nguyên nhân phân loại và hành động được phép.
- `fixed_assets_true_mismatch_decision_matrix_...md`: tổng hợp dễ đọc.
- `manifest.json`: thời điểm chạy và mã kiểm tra nội dung.
- `run_index.csv`: danh sách các lần chạy, có thể mở và lọc bằng Excel.

Phần mềm cũng lưu cùng dữ liệu vào database `mp2027.db`, trong hai bảng `audit_fixed_asset_mismatch_runs` và `audit_fixed_asset_mismatch_history`. Có thể lọc theo năm tài chính, cost center, tài khoản và tháng khi cần giải thích lại.

Lần đầu được lưu ở thư mục `fa-20260716T064652Z-50dd017d9ade`; đây là ảnh chụp 638 ô chênh lệch đã phân loại ngày 16/07/2026.
