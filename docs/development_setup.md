# Development setup MP2027

## Python khuyến nghị

Dùng Python 3.10+ trên Windows. Nếu lệnh `python` mở Microsoft Store, dùng `py`.

## Tạo môi trường

```powershell
py -m venv .venv
.\.venv\Scripts\activate
py -m pip install -U pip
pip install -r requirements.txt
```

## Kiểm tra nhanh

```powershell
py -m compileall src scripts packaging
py -m pytest -m "not requires_raw_excel"
py -m pytest
```

GitHub CI chạy `py -m pytest -m "not requires_raw_excel"` để loại các integration test cần workbook Excel thật trong `raw/`. Local máy có đủ dữ liệu raw vẫn chạy `py -m pytest` để kiểm tra toàn bộ. Test có marker `requires_raw_excel` không được skip âm thầm nếu raw workbook tồn tại.

## Chạy GUI

```powershell
run_MP2027.bat
```

## Chạy E2E smoke an toàn

```powershell
py scripts/run_e2e.py --target-cc 1412000040
```

Chỉ chạy khi có `docs/MP2027/FORM.xlsx` và source workbook hợp lệ. Nếu thiếu dữ liệu thật, ghi nhận missing input hoặc lỗi rõ; không tạo dữ liệu giả.

## Build portable

Repo có `packaging/mp2027_portable_entry.py` và spec PyInstaller. Nếu cần build, kiểm tra spec hiện tại rồi chạy PyInstaller trong venv đã cài requirements. Không commit `build/`, `dist/`, DB runtime hoặc output Excel sinh ra.

## Quy tắc dữ liệu

- Canonical requirement: workbook `raw/requirements/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026.xlsx`.
- Không commit source/output nhạy cảm nếu chưa được xác nhận.
- Không đổi rule tiền/phân bổ nếu chưa có test và bằng chứng từ workbook canonical.
