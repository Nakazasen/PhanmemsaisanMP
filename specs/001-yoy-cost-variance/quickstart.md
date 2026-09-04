# Quickstart & Validation Guide: YoY Cost Variance Analysis

## Correction Validation Gates

Run these before acceptance:

```powershell
py -m pytest tests/engine/test_variance_analyzer.py -q
py -m pytest tests/test_text_encoding_integrity.py tests/test_packaging_entrypoint.py -q
py -m compileall src scripts packaging
py -m pytest -m "not requires_raw_excel and not real_pipeline_acceptance and not performance" -q
```

Required regression cases:

1. UI-equivalent integer column references complete successfully.
2. Repeated account/name rows do not inflate totals.
3. Different year-specific filenames pair by Cost Center code.
4. Unmatched and malformed batch files appear in diagnostics, not silent drops.
5. `.xls` behavior matches the declared supported format.
6. Exported formulas or value snapshots match the documented contract.
7. The packaged Manager starts and the existing main workflow remains usable.

The release/update flow is intentionally excluded. Do not build or publish until
the owner explicitly requests release work.

## Prerequisites
- Môi trường Python với các thư viện: `openpyxl`, `pandas`, `tkinter` (đã có sẵn trong `requirements/runtime.lock`).
- Dữ liệu test:
  1. `D:/test_data/MP_CC_1412000040_FY2026.xlsx` (File năm ngoái)
  2. `D:/test_data/MP_CC_1412000040_FY2027.xlsx` (File năm nay - có một số dòng thay đổi/tăng/giảm)

## Validation Workflow 1: Mở Giao Diện So Sánh
1. Khởi chạy ứng dụng: `py src/universal_app.py`
2. Tại màn hình chính, kiểm tra trên giao diện hoặc menu có nút/Tab "📊 So sánh biến động MP (YoY)".
3. Nhấp vào nút/Tab đó, giao diện "So sánh biến động chi phí" xuất hiện.

## Validation Workflow 2: Chọn File & Hiển Thị Bảng Đối Chiếu
1. Trên giao diện So sánh, chọn `File MP Năm Trước` và `File MP Năm Nay`.
2. Đặt ngưỡng cảnh báo (ví dụ: `10%` và `50,000,000 VND`).
3. Nhấn nút **"Thực hiện So sánh"**.
4. **Kết quả kỳ vọng**:
   - Bảng dữ liệu (Treeview/Grid) hiện ra trong vòng dưới 3 giây.
   - Các dòng có chênh lệch $\ge 10\%$ hoặc $\ge 50$ triệu VNĐ được tô màu đỏ (Tăng) hoặc vàng (Giảm).
   - Dòng mới phát sinh ghi rõ `Mới phát sinh (+100%)`.
   - Dòng bị cắt giảm ghi rõ `Đã cắt giảm (-100%)`.

## Validation Workflow 3: Xuất Báo Cáo Excel
1. Nhấn nút **"Xuất Excel giải trình"** trên giao diện so sánh.
2. Chọn thư mục lưu (mặc định là `OUTPUT_FY2027/BAO_CAO_KIEM_TRA/BAO_CAO_BIEN_DONG_CHI_PHI_1412000040.xlsx`).
3. Mở file Excel vừa xuất ra.
4. **Kết quả kỳ vọng**:
   - File có các cột: Mã tài khoản, Tên khoản mục, Năm trước, Năm nay, Chênh lệch, % Biến động, Ghi chú.
   - Số liệu khớp 100% với giao diện UI.
   - Cột "% Biến động" sử dụng định dạng phần trăm (`0.00%`) của Excel, có màu sắc đánh dấu các khoản mục trọng yếu.
