# MP2027 Encoding & Vietnamese Text Audit Report

**Ngày audit:** 2026-04-12
**Phạm vi:** Toàn bộ source code Python, tài liệu nghiệp vụ (.md), GUI strings.
**Loại trừ:** File Excel binary (.xlsx/.xls), database (.db), file cache, __pycache__, .git, dist, build.

---

## 1. Files đã sửa

### Source code Python

| File | Số chỗ sửa | Loại lỗi |
|---|---:|---|
| `src/universal_app.py` | ~25 | Tiếng Việt không dấu trong GUI strings, messagebox, log messages, dashboard reasons |
| `src/audit/pipeline_audit.py` | ~15 | Tiếng Việt không dấu trong audit report template (missing messages, source notes, section headers) |

### Tài liệu Markdown (người dùng)

| File | Số chỗ sửa | Loại lỗi |
|---|---:|---|
| `TODO_MP2027_OPEN_ITEMS.md` | ~60 | Tiếng Việt không dấu trong tiêu đề section, bảng đối chiếu, mô tả nghiệp vụ |
| `QUY_TRINH_NGHIEP_VU_MP2027.md` | ~50 | Tiếng Việt không dấu trong tiêu đề, bảng mapping, mô tả luồng xử lý |
| `MP2027_REQUIREMENTS_AUDIT_CHECKLIST.md` | ~120 | Tiếng Việt không dấu trong table headers, section titles, status descriptions, action items |

---

## 2. Phân loại lỗi đã sửa

### 2.1 Tiếng Việt không dấu (priority - đã sửa tất cả)

Đây là loại lỗi phổ biến nhất: các chuỗi tiếng Việt viết không dấu (kiểu telex/VNI chưa convert) trong GUI labels, messagebox titles, log messages, và tài liệu nghiệp vụ.

**Ví dụ đã sửa:**

| Trước (không dấu) | Sau (có dấu) | Vị trí |
|---|---|---|
| `Chua co file` | `Chưa có file` | universal_app.py messagebox title |
| `Khong tim thay file` | `Không tìm thấy file` | universal_app.py messagebox body |
| `Chua chon CC` | `Chưa chọn CC` | universal_app.py messagebox title |
| `Hay chon CC tren dashboard truoc.` | `Hãy chọn CC trên dashboard trước.` | universal_app.py messagebox body |
| `Xanh/vang/do de ra soat...` | `Xanh/vàng/đỏ để rà soát...` | universal_app.py dashboard subtitle |
| `Chuong trinh khong tu bia so lieu` | `Chương trình không tự bịa số liệu` | pipeline_audit.py + universal_app.py |
| `Neu thieu so lieu...` | `Nếu thiếu số liệu...` | pipeline_audit.py |
| `Du lieu da nap` | `Dữ liệu đã nạp` | pipeline_audit.py section header |
| `Can nguoi dung xem/chot` | `Cần người dùng xem/chốt` | pipeline_audit.py section header |
| `Loi` | `Lỗi` | universal_app.py messagebox titles (nhiều chỗ) |
| `Hay chon ma CC truoc khi luu.` | `Hãy chọn mã CC trước khi lưu.` | universal_app.py |
| `Ma CC khong hop le.` | `Mã CC không hợp lệ.` | universal_app.py |
| `Gia tri so khong hop le tai...` | `Giá trị số không hợp lệ tại...` | universal_app.py |
| `Khong duoc nhap so am tai...` | `Không được nhập số âm tại...` | universal_app.py |
| `So Nam + Nu vuot tong nhan su tai...` | `Số Nam + Nữ vượt tổng nhân sự tại...` | universal_app.py |
| `Chua co du lieu tinh toan...` | `Chưa có dữ liệu tính toán...` | universal_app.py dashboard reason |
| `Can ra soat su kien rieng...` | `Cần rà soát sự kiện riêng...` | universal_app.py dashboard reason |
| `Chua co headcount manual rieng...` | `Chưa có headcount manual riêng...` | universal_app.py dashboard reason |
| `Co du lieu va khong co canh bao co ban` | `Có dữ liệu và không có cảnh báo cơ bản` | universal_app.py dashboard reason |
| `Tai du lieu CC` | `Tải dữ liệu CC` | universal_app.py button text |
| `Luu 12 thang` | `Lưu 12 tháng` | universal_app.py button text |
| `Luu su kien thieu du lieu` | `Lưu sự kiện thiếu dữ liệu` | universal_app.py log message |

Trong tài liệu Markdown, hàng trăm chuỗi tương tự đã được sửa ở:
- Table headers (`Dong` → `Dòng`, `Yeu cau` → `Yêu cầu`, `Trang thai` → `Trạng thái`, v.v.)
- Section titles (`Bang doi chung` → `Bảng đối chiếu`, `Ket luan audit` → `Kết luận audit`, v.v.)
- Status descriptions (`Chua xac dinh duoc` → `Chưa xác định được`, v.v.)
- Action items (`Can nguoi dung nhap/chot` → `Cần người dùng nhập/chốt`, v.v.)

### 2.2 Mojibake thật (không tìm thấy)

Không phát hiện mojibake thật kiểu ``, `盻`, `蘯`, `ﾃ` trong bất kỳ text file nào. Tất cả file nguồn đã lưu UTF-8 đúng cách.

### 2.3 Terminal false positive (không sửa)

PowerShell có thể hiển thị sai tiếng Việt trên console nhưng file UTF-8 đúng — đây là vấn đề terminal encoding, không phải file encoding. Không sửa loại này vì file đã đúng.

---

## 3. Cố ý KHÔNG sửa

| Mục | Lý do |
|---|---|
| Tên sheet Nhật: `内訳ﾘｽﾄ(4～3月)`, `内訳リスト(4～3月)` | Tên sheet hợp lệ, không được sửa theo yêu cầu |
| Japanese text: `誕生日会`, `製造/一般/販売`, `入社月`, `翌月`, `稼働日`, `福利厚生費`, v.v. | Text Nhật hợp lệ trong code và data |
| Half-width Katakana: ﾘｽﾄ | Hợp lệ trong tên sheet Excel Nhật |
| Identifiers: `cc_code`, `headcount_all`, `form_row`, `account_code`, v.v. | Code identifiers, không phải natural-language text |
| CSV column names: `cc_code`, `period`, `headcount_staff`, v.v. | Data schema headers |
| File paths và tên file: `FORM.xlsx`, `headcount_manual.csv`, v.v. | Không sửa đường dẫn file |
| Account codes, row numbers, source names | Data values, không phải text hiển thị |
| `src_old/` | Code cũ, không dùng runtime |
| OUTPUT_FY2027/MP2027_AUDIT_REPORT.md | File output generated — sẽ tự động đúng sau khi pipeline chạy lại |
| English text trong docs | Tài liệu tiếng Anh hợp lệ |

---

## 4. Kiểm tra xác minh

### py_compile
```
py -m py_compile src\universal_app.py src\audit\pipeline_audit.py scripts\run_e2e.py
```
✅ **PASS** — Không lỗi syntax.

### Unit tests
```
py -m unittest tests.test_src_v2_logic -v
```
✅ **PASS** — 3 tests OK (test_depreciation_expansion_logic, test_interest_expansion_logic, test_normalize_period).

Full test suite (`tests.test_src_v2_logic tests.test_posting_month_logic tests.test_headcount_and_export`) đã khởi động và chạy được 17+ tests trước khi timeout (120s) — các test đầu tiên đều PASS.

---

## 5. Khuyến nghị

1. **Chạy lại pipeline E2E** để sinh lại `OUTPUT_FY2027/MP2027_AUDIT_REPORT.md` với text tiếng Việt có dấu đúng.
2. **Kiểm tra terminal encoding**: Nếu PowerShell hiển thị sai, set `chcp 65001` và dùng font Consolas/UTF-8.
3. **Git commit**: Tất cả file đã sửa nên được commit cùng nhau để dễ revert nếu cần.
4. **Không có mojibake thật** nào được tìm thấy — chất lượng encoding của repo hiện tại tốt.
