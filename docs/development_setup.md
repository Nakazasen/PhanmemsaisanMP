# Development setup MP2027

> **Document Control**: Owner: MP Engineering | Status: Approved / Production-Ready | Last Updated: 2026-09-01
>
> Xem thêm tài liệu tổng quan tại [README.md](../README.md) và chiến lược test tại [test_strategy_and_profiles.md](handover/test_strategy_and_profiles.md).

## Python khuyến nghị

Dùng Python 3.10+ trên Windows. Nếu lệnh `python` mở Microsoft Store, dùng `py`.

## Fresh clone và tạo môi trường

```powershell
git clone https://github.com/Nakazasen/PhanmemsaisanMP
Set-Location PhanmemsaisanMP
py -m venv .venv
.\.venv\Scripts\activate
py -m pip install -U pip
pip install -r requirements.txt
```

Xác nhận workbook canonical có sẵn sau clone:

```text
raw/Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx
```

## Kiểm tra nhanh

```powershell
py -m compileall src scripts packaging
py -m pytest -m "not requires_raw_excel"
```

GitHub CI chạy nhóm test trên để loại các integration test cần workbook Excel phòng ban trong `raw/`.
Máy có đầy đủ dữ liệu nguồn có thể chạy thêm `py -m pytest`.

## Chạy GUI

```powershell
run_MP2027.bat
```

## Chạy E2E smoke

```powershell
py scripts/run_e2e.py --target-cc 1412000040
```

Nếu thiếu dữ liệu thật, pipeline phải ghi missing input hoặc lỗi rõ; không tạo dữ liệu giả.

Output kiểm tra nằm trong `OUTPUT_FY<năm>\BAO_CAO_KIEM_TRA`:

- `BAO_CAO_LAN_CHAY.xlsx`: tổng hợp lần chạy.
- `DU_LIEU_CON_THIEU.xlsx`: dữ liệu cần bổ sung/xác nhận.
- `KIEM_TRA_TY_GIA.xlsx`: kiểm tra tỷ giá trên các workbook kết quả.

Audit đối chiếu tài sản cố định là luồng riêng, không tự chạy trong E2E smoke:

```powershell
py scripts/audit_fixed_assets_cross_trace.py
py scripts/classify_fixed_assets_mismatches.py
py scripts/build_fixed_assets_business_decision_pack.py
```

Các lần audit được lưu append-only trong `docs/audits/history/fixed_assets` và trong các bảng
`audit_fixed_asset_mismatch_runs`, `audit_fixed_asset_mismatch_history` của `mp2027.db`.

## Build portable

Cài PyInstaller trong venv sạch chỉ có dependency cần thiết, sau đó chạy spec hiện tại.
Spec loại các package ML/CV không được ứng dụng sử dụng để tránh bundle phình lớn do môi trường build bị nhiễm package.
Không commit `build/` hoặc `dist/`.

## Cleanup local an toàn

```powershell
Remove-Item -Recurse -Force build, dist, .tmp_test_artifacts -ErrorAction SilentlyContinue
Remove-Item -Force mp2027.db, mp2027_before_optimization.db -ErrorAction SilentlyContinue
```

Các artifact trên tái tạo được và không cần chuyển sang máy mới.

## Quy tắc dữ liệu

- Canonical requirement: workbook `raw/Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx`.
- Không commit source/output nhạy cảm nếu chưa được xác nhận.
- Không đổi rule tiền/phân bổ nếu chưa có test và bằng chứng từ workbook canonical.
