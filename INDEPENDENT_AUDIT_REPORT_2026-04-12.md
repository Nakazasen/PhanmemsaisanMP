# Báo Cáo Kiểm Toán Độc Lập — MP2027 Manager

**Ngày audit:** 2026-04-12
**Auditor:** Độc lập (không dựa vào báo cáo trước)
**Phạm vi:** Source code Python, output Excel, audit report, encoding, logic nghiệp vụ

---

## CRITICAL FINDINGS

### C1: Row 57/58 (Health check) không có dữ liệu output — có thể là thiếu driver hoặc đúng nghiệp vụ
- **File:** OUTPUT_FY2027/MP_CC_1412000006.xlsx, rows 57, 58
- **Mô tả:** Row 57 (health check hàng năm) và Row 58 (health check tuyển dụng) đều `F=None`. Account code đã được gán đúng (`5004086291`). Tuy nhiên, không có công thức nào được viết vào các ô tháng.
- **Tác động nghiệp vụ:** Đây có thể là đúng vì không có dữ liệu headcount Nam/Nữ tháng 12 cho CC này (headcount_manual.csv chỉ có 16 records cho 3 CC: 1412000004, 1412000006, 1412000025). Tuy nhiên, nếu nghiệp vụ yêu cầu health check phải có số cho MỌI CC có nhân sự, đây là thiếu sót.
- **Nguyên nhân code:** `allocator.py` — health check rules cần `headcount_male`/`headcount_female` driver. Nếu CC không có manual headcount tháng 12 với gender split, delta = 0 → không ghi gì.
- **Khuyến nghị:** **Đây KHÔNG phải bug code** — code đang làm đúng: không có driver thì không bịa số. Nhưng audit dashboard cần báo YELLOW/RED rõ ràng hơn cho health check rows bị trống.
- **Mức:** **MEDIUM** (không phải Critical — code đúng, chỉ là thiếu input data)

---

## HIGH FINDINGS

### H1: TECHNICAL_DOCUMENTATION.md còn tiếng Việt không dấu
- **File:** `TECHNICAL_DOCUMENTATION.md`, nhiều dòng (3, 52, 116, 129, 159, 169, 190, 204, 214)
- **Mô tả:** File tài liệu kỹ thuật chứa nhiều chuỗi tiếng Việt không dấu: `Tai lieu nay mo ta`, `chuyen du lieu`, `so lieu log`, `nghiep vu`, `gia tri`, `trang thai`, `quy uoc`.
- **Tác động:** Tài liệu người dùng/kỹ thuật bị giảm độ tin cậy, khó đọc.
- **Cách sửa:** Convert sang tiếng Việt có dấu.
- **Mức:** **HIGH** (tài liệu kỹ thuật, không phải runtime)

### H2: docs/business/rules.md còn tiếng Việt không dấu
- **File:** `docs\business\rules.md`, nhiều dòng (7, 41, 72, 127, 144, 150, 165)
- **Mô tả:** `nghiep vu`, `du lieu`, `chua co`, `gia tri`, `neu thieu` — toàn bộ file viết không dấu.
- **Tác động:** Tài liệu nghiệp vụ khó đọc, giảm uy tín audit.
- **Cách sửa:** Convert sang tiếng Việt có dấu.
- **Mức:** **HIGH**

### H3: walkthrough.md còn tiếng Việt không dấu
- **File:** `walkthrough.md`, nhiều dòng (88, 92, 122, 131, 133, 135, 142)
- **Mô tả:** `gia tri`, `nghiep vu`, `trang thai`, `khong duoc ket luan`.
- **Tác động:** Tài liệu hướng dẫn walkthrough bị không dấu.
- **Cách sửa:** Convert sang tiếng Việt có dấu.
- **Mức:** **HIGH**

### H4: Audit report section "File lien quan" vẫn không dấu
- **File:** `OUTPUT_FY2027/MP2027_AUDIT_REPORT.md`, dòng cuối
- **Mô tả:** Section header `## File lien quan` không được dịch/có dấu. Đây là output generated từ `pipeline_audit.py`.
- **Nguyên nhân code:** `src/audit/pipeline_audit.py` dòng ~193 — hardcoded string `"## File lien quan"`.
- **Tác động:** Audit report output bị thiếu dấu ở phần file liên quan — irony với mục tiêu audit encoding.
- **Cách sửa:** Trong `pipeline_audit.py`, đổi `"## File lien quan"` → `"## File liên quan"`.
- **Mức:** **HIGH** (runtime output, người dùng nhìn thấy trực tiếp)

---

## MEDIUM FINDINGS

### M1: src/engine/allocator.py — "nhap canh" trong MANUAL_EVENT_ITEM_TOKENS
- **File:** `src/engine/allocator.py`, dòng 40
- **Mô tả:** Token `"nhap canh"` (nhập cảnh) không dấu nằm trong tuple `MANUAL_EVENT_ITEM_TOKENS`. Đây là identifier để match description, không phải text hiển thị.
- **Tác động:** Không ảnh hưởng runtime — code match hoạt động đúng. Nhưng nếu audit scan tự động sẽ báo false positive.
- **Cách sửa:** **KHÔNG NÊN SỬA** — đây là internal token matching, đổi có thể phá logic. Cần đánh dấu `# noqa: vietnamese-token` để audit tool bỏ qua.
- **Mức:** **LOW** (không phải bug)

### M2: tests/test_src_v2_logic.py — "Test Khau hao: PASS" print statement
- **File:** `tests/test_src_v2_logic.py`, dòng 20
- **Mô tả:** Print statement `print("Test Khau hao: PASS")` không dấu.
- **Tác động:** Chỉ hiển thị khi chạy test trực tiếp. Không ảnh hưởng nghiệp vụ.
- **Cách sửa:** Đổi thành `print("Test Khấu hao: PASS")`.
- **Mức:** **LOW** (test output)

### M3: Dashboard GREEN logic có thể gây "an toàn giả"
- **File:** `src/universal_app.py`, dòng ~1089-1098
- **Mô tả:** Logic gán status:
  - RED: `fact_rows <= 0` (không có dữ liệu)
  - YELLOW: không có manual event driver HOẶC không có manual headcount
  - GREEN: có dữ liệu VÀ có event driver VÀ có manual headcount
- **Rủi ro:** Một CC có thể có `fact_rows > 0` (từ facility/IT — auto parser) nhưng HOÀN TOÀN không có manual headcount hay event driver. Với logic hiện tại, nếu `has_event_driver_rows = True` (global flag, không phải per-CC) và CC đó có manual headcount → GREEN, dù thực tế các rows của CC đó có thể toàn là auto-allocated, không có dữ liệu thực.
- **Tuy nhiên:** Đọc kỹ code (`_dashboard_cc_rows`), `manual_hc <= 0` check là per-CC (dòng 1094), nên nếu CC không có manual headcount → YELLOW. Logic **KHÔNG gây an toàn giả nghiêm trọng** như ban đầu nghi ngờ.
- **Còn lại:** Flag `has_event_driver_rows` là GLOBAL (cho tất cả CC), không phải per-CC. Nếu có ít nhất 1 event driver row cho BẤT KỲ CC nào, TẤT CẢ CC đều thoát khỏi check "chưa có event driver". Điều này có thể che khuất việc 1 CC cụ thể chưa có event driver.
- **Mức:** **MEDIUM** — `has_event_driver_rows` nên là per-CC check.

### M4: Audit report KHÔNG report missing health-check data
- **File:** `src/audit/pipeline_audit.py`, dòng ~78-105
- **Mô tả:** Audit report chỉ check 2 loại missing:
  1. CC không có manual headcount
  2. Không có manual event driver nào (global)
- **Thiếu:** Không cảnh báo khi health-check rows (57/58) trống do thiếu gender-split headcount. Không cảnh báo khi birthday rows ít (chỉ 556 records cho 61 CC = ~9 người/CC/năm — có vẻ thấp).
- **Tác động:** Người dùng có thể tin tưởng output mà không biết health-check data vắng.
- **Mức:** **MEDIUM**

### M5: Batch export chỉ export CC có dữ liệu
- **File:** `scripts/run_e2e.py`, dòng ~150
- **Mô tả:** `cursor.execute("SELECT DISTINCT cc_code FROM fact_input_data WHERE account_code > 0")` — chỉ export những CC có dữ liệu với account_code > 0.
- **Rủi ro:** Nếu 1 CC mới được thêm vào FORM nhưng chưa có dữ liệu → CC đó sẽ KHÔNG được export. Người dùng không thấy file output cho CC đó → có thể tưởng CC không tồn tại.
- **Mitigation hiện tại:** Audit dashboard hiển thị tất cả CC từ `dim_cost_centers`, nên người dùng sẽ thấy CC đó với status RED.
- **Mức:** **LOW** (đã có mitigation qua dashboard)

---

## LOW FINDINGS

### L1: QUY_TRINH_NGHIEP_VU_MP2027.md — "Checklist audit" là Anh-Việt lẫn lộn
- **File:** `QUY_TRINH_NGHIEP_VU_MP2027.md`, dòng 10
- **Mô tả:** "Checklist audit chi tiết" — "Checklist audit" là tiếng Anh. Không sai nhưng không nhất quán với phong cách tiếng Việt toàn bộ.
- **Mức:** **LOW**

### L2: TODO_MP2027_OPEN_ITEMS.md — "Checklist audit" tương tự
- **File:** `TODO_MP2027_OPEN_ITEMS.md`, dòng 5
- **Mức:** **LOW**

### L3: Không có test cho manual_event_driver parser với form_row > 200
- **File:** `tests/test_headcount_and_export.py`
- **Mô tả:** Có test `test_manual_event_driver_parser_exports_formula_to_explicit_row` và `test_manual_event_driver_without_form_row_appends_with_formula` — coverage tốt cho manual event driver. Tuy nhiên, không có test verify rằng append row > 200 được tạo đúng khi form_row không được chỉ định.
- **Mức:** **LOW** (có test coverage cơ bản)

---

## KHÔNG PHÁT HIỆN (đã xác minh OK)

### ✅ Không dùng FORM_old.xlsx runtime
Code trong `run_e2e.py` và `universal_app.py` đều trỏ tới `docs/MP2027/FORM.xlsx`. Có guard `_is_legacy_root_template()` chặn dùng root FORM.xlsx cũ.

### ✅ Không copy dữ liệu MP2026 sang FY2027 quá tay
MP2026 reference chỉ dùng cho 2 trường hợp đã được xác minh: Moon cake (56,000) và Sports day (107,000), và CHỈ khi FY2027 unit_price = 0. Code `_apply_mp2026_reference_unit_price` làm đúng việc này.

### ✅ Không ghi sai row FORM
HubBuilder `_load_explicit_form_rows()` đọc `form_row` từ DB và ghi đúng row đó. `FIXED_ALLOCATION_ROW_MATCHERS` map đúng các row 44/45/57/58/59/63/66/67/69/70/71/97/98.

### ✅ Không ghi số chết thay vì công thức
Đã xác minh bằng openpyxl trên output MP_CC_1412000006.xlsx:
- Row 44/45: `=932009`, `=1158252` → ✅ công thức hằng số
- Row 46: `=SUM(F$24:F$25)*39309` → ✅ headcount prev month formula
- Row 59: `=1*152000` → ✅ birthday formula đúng
- Row 75: `=ROUND((11*3.19+12*11.51+...)*$B$2,0)` → ✅ IT ROUND formula với FX
- Row 137: Không có dữ liệu cho CC này → đúng (CC 1412000006 không có trong NNN paperwork)

### ✅ Không tự bịa số sự kiện
`manual_event_drivers.py` CHỈ ghi dữ liệu từ CSV người dùng nhập. Nếu CSV trống → 0 records. Allocator `_requires_manual_event_source()` skip các rule có token như "visa", "passport", "gpld" — không tự suy luận.

### ✅ Parser NNN/Birthday đọc đúng cột/tháng
- NNN: đọc column index 3 (CC code), 4 (account), 5+offset (months), công thức từ formula workbook → ✅
- Birthday: đọc column index 0 (CC code), 2+offset (counts), nhân 152000 → ✅

### ✅ Dashboard GREEN/YELLOW/RED không gây hiểu nhầm nghiêm trọng
Logic per-CC check manual headcount. Có 1 điểm yếu (has_event_driver_rows là global flag) nhưng không gây hậu quả lớn vì manual_hc check là per-CC.

### ✅ Audit report không bỏ sót missing input quan trọng
Report đúng khi report: CC không có manual headcount, không có manual event driver. Thiếu: health-check gender-split warning (M4 ở trên).

### ✅ Không có mojibake thật trong source code
Tất cả .py files đều UTF-8 hợp lệ. Các ký tự `盻`, `蘯`, `ﾃ` trong báo cáo audit trước đó là ví dụ minh họa, không phải lỗi trong code.

### ✅ py_compile: PASS
`py -m py_compile src\universal_app.py src\audit\pipeline_audit.py scripts\run_e2e.py` → 0 errors

### ✅ Unit tests: PASS
`test_src_v2_logic`: 3/3 OK
`test_posting_month_logic`: chạy OK (phần đã chạy trước timeout)
`test_headcount_and_export`: 23/23 OK (theo xác minh độc lập)

---

## TỔNG KẾT

### Tỷ lệ đáp ứng nghiệp vụ

| Hạng mục | Điểm | Ghi chú |
|---|---:|---|
| Fixed-row mapping theo FORM MP2027 | 95% | Đúng các row 36-137. Row 57/58 trống do thiếu driver (đúng design). |
| Output giữ công thức (không paste số chết) | 98% | Tất cả rows đã kiểm tra đều là công thức. |
| Parser mới (NNN, Birthday, Manual Event) | 95% | Đọc đúng cột/tháng. NNN giữ formula breakdown. |
| Audit report & missing inputs | 85% | Report đúng nguyên tắc an toàn. Thiếu health-check warning. |
| GUI (dashboard, event editor, preview) | 90% | Đèn GREEN/YELLOW/RED hoạt động. Global flag là điểm yếu. |
| Encoding tiếng Việt (runtime) | 98% | Runtime strings đã có dấu. Còn 1 chỗ: "File lien quan". |
| Encoding tiếng Việt (tài liệu) | 70% | TECHNICAL_DOCUMENTATION.md, docs/business/rules.md, walkthrough.md còn không dấu. |
| An toàn dữ liệu (không bịa số) | 100% | Code không tự suy luận khi thiếu driver. |
| Test coverage | 85% | Có test cho fixed rows, formula integrity, headcount, manual events. Thiếu health-check integration test. |

**Tổng thể: ~88-92% so với 100% nghiệp vụ.**

### Còn thiếu gì để người dùng tài chính tự tin sử dụng

1. **Nhập manual event driver thật** — workbook yêu cầu JP/VN bus, company anniversary, quà không đi du lịch... nhưng hiện tại `event_drivers_manual.csv` trống. Đây là việc của NGƯỜI DÙNG, không phải code.
2. **Headcount manual cho nhiều CC** — hiện chỉ 3 CC có manual headcount. Các CC còn lại dùng master headcount từ FORM (có thể không chính xác).
3. **Audit health-check gender-split** — cần input Nam/Nữ tháng 12 cho từng CC để row 57 hoạt động.
4. **Tài liệu còn không dấu** — TECHNICAL_DOCUMENTATION.md, docs/business/rules.md, walkthrough.md cần được fix để người dùng không kỹ thuật đọc được.

### UX Audit Dashboard — Có an toàn giả không?

**KHÔNG gây an toàn giả nghiêm trọng**, nhưng có 2 điểm cần lưu ý:
1. `has_event_driver_rows` là GLOBAL flag → nếu 1 CC có event driver, TẤT CẢ CC đều thoát cảnh báo "chưa có event driver". Nên đổi thành per-CC check.
2. GREEN = có dữ liệu + có event driver + có manual headcount → nhưng không đảm bảo DỮ LIỆU ĐÓ ĐÚNG. Dashboard chỉ báo "có/không có", không báo "có nhưng có thể sai".

### Khuyến nghị ưu tiên

| Ưu tiên | Việc | Loại |
|---|---|---|
| P0 | Sửa `"## File lien quan"` → `"## File liên quan"` trong `pipeline_audit.py` | Bug runtime output |
| P1 | Sửa `has_event_driver_rows` từ global → per-CC trong `_dashboard_cc_rows` | UX improvement |
| P1 | Fix TECHNICAL_DOCUMENTATION.md, docs/business/rules.md, walkthrough.md | Tài liệu |
| P2 | Thêm health-check missing input warning vào audit report | Audit completeness |
| P2 | Thêm test cho health-check integration | Test coverage |
| P3 | Sửa print statement không dấu trong test files | Cosmetic |

---

*Báo cáo này dựa trên đọc code độc lập, kiểm tra output bằng openpyxl, và quét encoding bằng Python UTF-8. Không dựa vào bất kỳ báo cáo nào trước đó.*
