# Data Model & State Transitions: YoY Cost Variance Analysis

## Entities

### `ComparisonContext`
Quản lý trạng thái phiên so sánh của người dùng trên giao diện.
- `fiscal_year_base`: Năm tài chính cơ sở (Năm trước - ví dụ: 2026)
- `fiscal_year_current`: Năm tài chính hiện tại (Năm nay - ví dụ: 2027)
- `cost_center_code`: Mã phòng ban (ví dụ: "1412000040")
- `base_file_path`: Đường dẫn tuyệt đối tới file MP năm trước
- `current_file_path`: Đường dẫn tuyệt đối tới file MP năm nay
- `threshold_percent`: Ngưỡng cảnh báo % (Mặc định: 10.0)
- `threshold_absolute`: Ngưỡng cảnh báo số tiền tuyệt đối (Mặc định: 50000000)

### `CostLineVariance`
Đại diện cho kết quả đối chiếu của một dòng chi phí (một khoản mục).
- `account_code`: Mã tài khoản kế toán (String)
- `item_name`: Tên khoản mục chi phí (String)
- `base_value`: Tổng số tiền năm trước (Float)
- `current_value`: Tổng số tiền năm nay (Float)
- `variance_absolute`: Chênh lệch tuyệt đối (`current_value` - `base_value`) (Float)
- `variance_percent`: Tỷ lệ % biến động (Float hoặc Null nếu base_value = 0)
- `status`: Phân loại biến động (Enum: `INCREASE`, `DECREASE`, `UNCHANGED`, `NEW_ITEM`, `REMOVED`)
- `is_alert`: Cờ (Boolean) báo hiệu dòng này có vượt ngưỡng cảnh báo hay không.

### `VarianceReport`
Kết quả tổng hợp để hiển thị lên UI và xuất ra Excel.
- `context`: Tham chiếu tới `ComparisonContext`
- `lines`: Danh sách các `CostLineVariance`
- `total_base`: Tổng chi phí năm trước
- `total_current`: Tổng chi phí năm nay
- `total_variance_absolute`: Tổng chênh lệch tuyệt đối
- `total_variance_percent`: Tổng tỷ lệ biến động

## Correction Invariants

- `ComparisonInput` carries an explicit source format and column mapping; integer
  FORM indices must not be concatenated with string suffixes.
- Each normalized row has a stable matching key and source-row reference.
- Matching keys are unique after normalization. Duplicate rows are aggregated
  with diagnostics or rejected; they are never joined many-to-many.
- `VarianceReport` retains unmatched keys, duplicate counts, invalid rows, and
  batch skip/error diagnostics.
- Batch results distinguish matched, unmatched-base, unmatched-current, and
  invalid Cost Centers.
- Export metadata states whether calculated columns are formulas or value
  snapshots, and all consumers use the same contract.

## State Transitions
1. **IDLE**: Người dùng mở Tab So sánh. Giao diện trống.
2. **LOADING_FILES**: Người dùng chọn 2 file. Hệ thống validate file có đúng chuẩn MP FORM không.
3. **ANALYZING**: Phân tích data bằng engine (Pandas/Openpyxl). Bóc tách dòng chi phí, so khớp bằng (Account Code + Item Name).
4. **DISPLAY_RESULTS**: Hiển thị lưới dữ liệu (DataGrid/Treeview) có highlight màu sắc dựa trên `is_alert`.
5. **EXPORTING**: Ghi `VarianceReport` ra file Excel (lưu vào `OUTPUT_FY2027/BAO_CAO_KIEM_TRA`).
