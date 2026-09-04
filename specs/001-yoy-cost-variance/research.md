# Phase 0: Research & Clarifications

## Q1: Khóa định danh khoản mục chi phí (Matching Key)
- **Decision**: Mã tài khoản (Account Code) + Tên khoản mục (Item Name) kết hợp Số dòng (Row Index) khi cần thiết.
- **Rationale**: Đảm bảo chính xác khi form thay đổi thứ tự dòng hoặc người dùng thêm dòng chi phí riêng.
- **Alternatives considered**: Chỉ sử dụng Row Index (rủi ro sai lệch khi form thay đổi).

## Q2: Ngưỡng cảnh báo biến động (Variance Threshold)
- **Decision**: Biến động $\ge \pm 10\%$ HOẶC chênh lệch tuyệt đối $\ge 50.000.000$ VNĐ. Có ô tùy chỉnh trên giao diện.
- **Rationale**: Bắt các khoản mục trọng yếu cần giải trình, tránh báo động giả cho khoản chi nhỏ.
- **Alternatives considered**: Chỉ cảnh báo tăng chi phí (bỏ qua giảm chi phí - không toàn diện).

## Q3: Vị trí giao diện (UI Placement)
- **Decision**: Thêm 1 Tab riêng "📊 So sánh biến động MP (YoY)" trên thanh điều hướng chính của ứng dụng MP Manager.
- **Rationale**: Cung cấp không gian làm việc rộng rãi cho tính năng phức tạp, tách biệt với luồng xử lý chính.
- **Alternatives considered**: Nút popup ở màn hình chính (thiếu không gian hiển thị bảng dữ liệu chi tiết).

## Audit Findings and Decisions for Correction

### Q4: Column reference contract

- **Decision**: Normalize FORM input to stable internal names and document one
  analyzer reference type.
- **Rationale**: The UI currently passes integer indices while the engine builds
  string-suffixed names, so the comparison action fails before producing output.
- **Verification**: Invoke the analyzer exactly as the UI does in a regression test.

### Q5: Duplicate matching keys

- **Decision**: Aggregate duplicate `(account_code, item_name)` rows with a recorded
  count, or reject them with an actionable diagnostic after checking canonical FORM
  evidence. Never allow many-to-many merging.

### Q6: Batch pairing and errors

- **Decision**: Pair using an explicit Cost Center extraction rule and return
  structured unmatched/invalid/error results.
- **Rationale**: Exact basename matching misses valid year pairs, while swallowed
  exceptions make the financial result unauditable.

### Q7: Packaging dependency

- **Decision**: Before release, either include pandas in the Manager bundle or
  defer-load the optional feature with a clear unavailable-feature message.
- **Rationale**: The application imports the YoY UI at startup while the Manager
  spec excludes pandas. Source tests cannot prove package safety.

### Q8: Export contract

- **Decision**: Align spec, implementation, tests, and walkthrough on formulas or
  value snapshots. Do not describe values as formulas.

## Technical Approach
- **UI Module**: Tạo module UI mới (ví dụ: `src/ui/variance_tab.py` hoặc thêm class `VarianceTab` vào kiến trúc UI hiện tại) và gọi trong `universal_app.py` bằng cách thêm một nút trên thanh công cụ chính để mở cửa sổ so sánh (hoặc thêm Tab thực sự nếu main window dùng Notebook).
- **Data Engine**: Sử dụng `openpyxl` và `pandas` (đã có trong `requirements/runtime.lock`) để load file MP năm ngoái và năm nay. Parse vùng chi phí (từ dòng 38 trở xuống hoặc theo định dạng FORM).
- **Matching Logic**: Pandas `merge` hoặc mapping theo `Account Code` (Cột A/B/C) và `Item Name`.
- **Output**: Dùng thư viện `openpyxl` hoặc `pandas.ExcelWriter` để xuất báo cáo `.xlsx` ra thư mục `OUTPUT_FY2027/BAO_CAO_KIEM_TRA`.
