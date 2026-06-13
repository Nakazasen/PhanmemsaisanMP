# MP2027 Manager - Quy trình nghiệp vụ, vận hành và handover kỹ thuật

Ngày cập nhật: `2026-06-13`

`LAST_VERIFIED_AT_COMMIT=12d92325a0fffa9b03b6251d27210dbb69e032d0`

Tài liệu này là handover tổng hợp cho dự án MP2027 Manager. Canonical business requirement vẫn là workbook Excel ngày `09.06.2026`; Markdown này không thay thế workbook yêu cầu, ảnh minh họa, audit log, hoặc code/test evidence. Khi có mâu thuẫn, thứ tự ưu tiên là:

1. Workbook canonical ngày `09.06.2026`.
2. Code và test đã commit.
3. Audit report hoặc knowledge doc có timestamp/commit rõ.
4. Markdown handover này.
5. Tài liệu lịch sử hoặc file legacy chưa được gắn nhãn hiện hành.

Thông tin lịch sử không tự động override code hiện tại. Mọi claim về implementation phải có commit/test evidence hoặc được đánh dấu là cần audit lại.

## 1. Mục tiêu chương trình

MP2027 Manager là ứng dụng Windows desktop dùng Python/Tkinter để tổng hợp dữ liệu ngân sách MP FY2027 từ nhiều file Excel nguồn, tính phân bổ chi phí theo rule, rồi xuất FORM theo từng Cost Center.

Nguyên tắc nghiệp vụ: chương trình thay thao tác nhập tay lặp lại nhưng không tự bịa số liệu. Khoản nào không suy luận an toàn từ source workbook hoặc manual CSV đã xác nhận thì phải để trống, ghi missing input, hoặc yêu cầu người dùng nhập/chốt.

## 2. Nguồn yêu cầu và bằng chứng

| Loại | Đường dẫn | Vai trò | Trạng thái |
|---|---|---|---|
| Canonical requirement | `raw/requirements/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026.xlsx` | Nguồn yêu cầu nghiệp vụ cao nhất | CANONICAL |
| Official visual support | `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026_ảnh.xlsx` | Ảnh/annotation hỗ trợ đọc yêu cầu | SUPPORTING |
| Full-coverage duplicate | `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026_ảnh_FULL_COVERAGE.xlsx` | Bản duplicate dùng kiểm tra coverage hình ảnh | SUPPORTING |
| Legacy incomplete visual | `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026_ảnh_LEGACY_INCOMPLETE.xlsx` | Bản cũ thiếu coverage | LEGACY |
| Obsolete visual | `raw/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026_ảnh.xlsx` | Bản 04.06 đã bị supersede | OBSOLETE |
| Handover Markdown | `QUY_TRINH_NGHIEP_VU_MP2027.md` | Tài liệu vận hành/kỹ thuật đã reconcile | DERIVED |

Workbook canonical outranks visual workbook, Markdown, audit-derived descriptions, và mọi suy luận từ tên file.

## 3. Trạng thái module hiện tại

Không dùng phần trăm ước lượng cho readiness. Dùng trạng thái theo module:

| Module/Luồng | Trạng thái | Ghi chú |
|---|---|---|
| Default FORM path | PASS | Runtime ưu tiên `docs/MP2027/FORM.xlsx`. |
| Source workbook manifest | PASS | `docs/MP2027/source_file_order.xlsx` điều khiển thứ tự parser, CSV manifest là fallback kỹ thuật. |
| Facility / fixed assets / IT / GA / birthday / NNN parsers | PASS_WITH_SCOPE | Parser hiện có cho các nguồn chính; output cần audit theo từng CC khi dữ liệu nguồn đổi. |
| Manual headcount channel | PARTIAL | Active path là `raw/headcount_manual.csv`; vẫn thiếu headcount thật cho một số CC. |
| CC `1412000040` headcount | BLOCKED_BY_INPUT | Chưa có chuỗi headcount thật đủ để accept các claim phụ thuộc new-hire delta. |
| Bus passenger drivers | PASS | GUI có input scalar; allocator nhân scalar count với monthly unit price từ GA source. |
| Health-check male/female split | BLOCKED_BY_INPUT | Cần Nam/Nữ tháng 12 thật nếu muốn tính row health-check theo split. |
| Manual event drivers | PARTIAL | Channel có sẵn; event chưa có nguồn máy đọc vẫn cần người dùng nhập/chốt. |
| Legacy headcount source hardening | PASS | Docs legacy đã đổi tên DO_NOT_USE và parser guardrail không silent import. |
| Final six-claim acceptance | PARTIAL | Không được ghi nhận là hoàn tất toàn bộ; xem bảng six-claim bên dưới. |

## 4. Runtime directory model

Repo dev chuẩn: `D:\Sandbox\MP2027`.

| Thành phần | Active path | Ghi chú |
|---|---|---|
| FORM template/runtime | `docs/MP2027/FORM.xlsx` | Dùng load master, tỷ giá `B2`, copy/export FORM. |
| Source workbook dir | `docs/MP2027` | Facility, fixed assets, IT simulation, GA, birthday, allocation rule, NNN paperwork. |
| Source order manifest | `docs/MP2027/source_file_order.xlsx` | Người dùng chỉnh bằng Excel hoặc GUI `Thứ tự file nguồn`. |
| Manual headcount | `raw/headcount_manual.csv` | Active canonical manual headcount input. |
| Manual bus passenger driver | `raw/bus_headcount_manual.csv` | Tạo bởi GUI/parser khi cần; scalar theo CC, không theo tháng. |
| Manual event driver | `docs/MP2027/event_drivers_manual.csv` | Dùng cho event không suy luận được. |
| Manual special cost | `docs/MP2027/special_costs_manual.csv` | Dùng khi có amount/row FORM chính xác. |
| Legacy headcount artifact | `docs/MP2027/headcount_manual_LEGACY_DO_NOT_USE.csv` | Không phải active input; không import. |
| SQLite DB | `mp2027.db` | Runtime database, không commit. |
| Output | `OUTPUT_FY2027/` | Output/audit/temp/quarantine, không commit nếu là runtime data. |

Khi đóng gói OneDir/OneFile, dữ liệu người dùng phải nằm ngoài bundled resource. Thư mục bàn giao nên có `docs\MP2027` cạnh `.exe` cho source workbooks và `raw` cạnh `.exe` cho manual headcount/bus CSV. Bundle chỉ là fallback kỹ thuật, không phải nơi người dùng chỉnh dữ liệu vận hành.

Nếu GUI source dir trỏ tới `docs/MP2027`, manual headcount resolver vẫn đọc/ghi `raw/`. Nếu người dùng truyền custom source folder ngoài project, parser tôn trọng custom folder đó.

## 5. Active và legacy headcount

Active headcount input:

`raw/headcount_manual.csv`

Schema hiện hành:

```text
cc_code,period,headcount_staff,headcount_worker,headcount_male,headcount_female,description
```

Yêu cầu kỳ:

- Baseline previous March: `202603`.
- FY2027 months: `202604` đến `202703`.
- `headcount_staff` và `headcount_worker` tách riêng.
- `headcount_male` và `headcount_female` chỉ dùng cho tháng 12 khi cần health-check split.
- Field trống phải giữ là trống, không tự biến thành zero.
- Không fallback từ `dim_cost_centers`.
- Không fallback từ CC khác.

Legacy artifact:

`docs/MP2027/headcount_manual_LEGACY_DO_NOT_USE.csv`

File này chỉ giữ bằng chứng lịch sử. README đi kèm là `docs/MP2027/README_HEADCOUNT_LEGACY.md`. Parser có guardrail `LEGACY_HEADCOUNT_SOURCE_IGNORED`: explicit docs legacy path không được silent import; project default chuyển về `raw/`.

Phase 42N46 đã quarantine và xóa khỏi active data sáu logical values của CC `1412000006` cho `202701`, `202702`, `202703` staff/worker. Bằng chứng quarantine nằm dưới `OUTPUT_FY2027/tmp_phase42n46_headcount_confirmation/` và không được commit.

## 6. Bus passenger drivers

Bus không còn là pending manual event chung. Trạng thái hiện tại: PASS.

Luồng hiện hành:

- GUI headcount panel có hai field scalar theo CC:
  - `bus_expat_count`
  - `bus_vietnamese_count`
- Parser ghi vào `fact_bus_headcount_drivers`.
- Allocator dùng account/item `通勤送迎費`.
- Monthly unit price lấy từ GA workbook `docs/MP2027/総務課 FY2027 MP 振替予定.xlsx`.
- Sheet nguồn: `FY2027予定`.
- Expat/Japanese bus unit price: `B9:M9`.
- Vietnamese bus unit price: `B10:M10`.
- Formula: scalar count x monthly unit price.
- Nếu thiếu price nguồn, logic fail-closed và ghi missing input; không tự tạo số.

Hai field bus độc lập với staff/worker/male/female headcount. Chỉnh headcount không được làm mất bus drivers và ngược lại.

## 7. Six-claim acceptance status

Không ghi nhận toàn bộ sáu claim là hoàn tất. Trạng thái hiện hành:

| Claim | Trạng thái | Ghi chú |
|---|---|---|
| 1. Duplicate new-hire stationery | PASS_FAIL_CLOSED | Logic fail-closed; vẫn cần acceptance bằng dữ liệu delta dương thật. |
| 2. Total-headcount multiplier | PASS_FAIL_CLOSED | Không tự nhân nếu thiếu driver/headcount thật; cần real-data acceptance. |
| 3. Monthly new-hire delta | BLOCKED_BY_REAL_HEADCOUNT_INPUT | CC `1412000040` chưa có chuỗi headcount thật. |
| 4. Column S handling | PASS | Đã xử lý theo evidence hiện tại. |
| 5. One blank row between blocks | PARTIAL_PASS_FOR_WRITTEN_BLOCKS | Đúng với block đã được ghi; strict seven-block acceptance chờ đủ true drivers. |
| 6. Row 168/reference garbage | PASS | Reference garbage đã được xử lý/quarantine theo scope đã audit. |

## 8. Row mapping labels

Các nhãn dùng trong tài liệu/audit:

- `CANONICAL_TARGET`: row đích đến từ requirement/workbook canonical.
- `CURRENT_CODE_VERIFIED`: code/test hiện tại đã chứng minh đang ghi hoặc tính theo row này.
- `HISTORICAL_MAPPING`: mapping lịch sử, không được dùng như sự thật hiện hành nếu chưa audit lại.
- `SOURCE_ORDER_DYNAMIC`: vị trí phụ thuộc manifest/source order, không phải fixed row output.
- `REQUIRES_CURRENT_OUTPUT_AUDIT`: cần mở output/current run để xác nhận lại trước khi claim pass.

| Row/Range | Nội dung | Classification | Ghi chú |
|---:|---|---|---|
| 36 | Khấu hao nhà | CURRENT_CODE_VERIFIED | Facility, công thức quy đổi USD/VND nếu nguồn USD. |
| 37 | Khấu hao đất | CURRENT_CODE_VERIFIED | Facility. |
| 38 | Khấu hao thiết bị | CURRENT_CODE_VERIFIED | Fixed assets nếu có dữ liệu. |
| 40 | Lãi nhà | CURRENT_CODE_VERIFIED | Facility. |
| 41 | Lãi đất | CURRENT_CODE_VERIFIED | Facility. |
| 42 | Lãi thiết bị | CURRENT_CODE_VERIFIED | Fixed assets nếu có dữ liệu. |
| 44 | Điện | CURRENT_CODE_VERIFIED | Facility amount. |
| 45 | Nước | CURRENT_CODE_VERIFIED | Facility amount. |
| 46 | Gas | CURRENT_CODE_VERIFIED | Headcount-based admin allocation. |
| 48 | Hand wash | CURRENT_CODE_VERIFIED | Admin consumables. |
| 49 | Toilet paper | CURRENT_CODE_VERIFIED | Admin consumables. |
| 51 | Cleaning | CURRENT_CODE_VERIFIED | Admin allocation. |
| 53/54 | Bus passenger cost | CANONICAL_TARGET; CURRENT_CODE_VERIFIED | Scalar bus drivers x monthly unit price from GA. |
| 57 | Annual health check | CANONICAL_TARGET; REQUIRES_CURRENT_OUTPUT_AUDIT | Cần male/female December input thật khi áp dụng split. |
| 58 | Recruitment health check | CANONICAL_TARGET; REQUIRES_CURRENT_OUTPUT_AUDIT | Cần event/new-hire driver thật. |
| 59 | Birthday | CURRENT_CODE_VERIFIED | Birthday workbook count x unit price. |
| 75 | IT system cost | CURRENT_CODE_VERIFIED | IT Simulation, formula giữ breakdown và quy đổi tỷ giá. |
| 97/98 | New-hire stationery | CURRENT_CODE_VERIFIED | Fail-closed nếu thiếu monthly delta/headcount thật. |
| 137 | NNN paperwork | CURRENT_CODE_VERIFIED | Parser NNN hiện map row này; row khác cần user confirmation. |
| 200-212 | Source-order v1 area | HISTORICAL_MAPPING; SOURCE_ORDER_DYNAMIC | Không coi là fixed FORM mapping hiện hành nếu chưa output-audit lại. |

## 9. Source workbook workflow

Người dùng đặt source workbooks trong `docs/MP2027` và kiểm tra `source_file_order.xlsx`.

Pipeline cơ bản:

1. Load `docs/MP2027/FORM.xlsx` để lấy tỷ giá, master Cost Center, account.
2. Load allocation rules từ workbook FY2027.
3. Parse source theo manifest:
   - Facility.
   - Fixed assets.
   - IT Simulation.
   - GA/Admin.
   - Birthday.
   - NNN paperwork.
4. Parse manual inputs:
   - `raw/headcount_manual.csv`.
   - `raw/bus_headcount_manual.csv`.
   - `docs/MP2027/event_drivers_manual.csv`.
   - `docs/MP2027/special_costs_manual.csv`.
5. Ghi SQLite `mp2027.db`.
6. Allocation engine tính fact output và missing inputs.
7. HubBuilder export `OUTPUT_FY2027/MP_CC_<cc>.xlsx`.
8. Audit pipeline sinh `OUTPUT_FY2027/MP2027_AUDIT_REPORT.md` và `MP2027_MISSING_INPUTS.csv`.

## 10. Manual input rules

### Headcount

Nhập qua GUI `Nhập liệu nhân sự 12 tháng` hoặc chỉnh `raw/headcount_manual.csv`. Baseline `202603` chỉ phục vụ tính delta từ tháng 4 nếu cần; không tự điền Apr-Mar từ baseline.

CC switching trong GUI phải clear giá trị stale. Nếu chọn CC không có dòng active, staff/worker/male/female hiển thị blank, bus fields load độc lập.

### Event drivers

File:

`docs/MP2027/event_drivers_manual.csv`

Schema chính:

```text
cc_code,period,event_name,count,unit_price,amount_vnd,account_code,form_row,description
```

Chỉ nhập khi có dữ liệu thật hoặc user confirmation. Các event vẫn cần người dùng chốt gồm quà không đi du lịch, My Episode, sự kiện 10 năm, kỷ niệm thành lập công ty, và các khoản chưa có source parser ổn định.

### Special costs

File:

`docs/MP2027/special_costs_manual.csv`

Dùng khi có amount và row FORM chính xác. Nếu chưa rõ row/account, không nhập bừa.

## 11. Database

SQLite runtime:

`mp2027.db`

Các bảng chính:

| Bảng | Vai trò |
|---|---|
| `dim_cost_centers` | Master Cost Center từ FORM. |
| `dim_accounts` | Master Account từ FORM. |
| `map_allocation_rules` | Allocation rules. |
| `fact_input_data` | Staging dữ liệu chi phí đầu vào. |
| `fact_monthly_headcount` | Manual monthly headcount theo CC/period. |
| `fact_bus_headcount_drivers` | Scalar bus passenger drivers theo CC. |
| `fact_allocation_log` | Trace allocation. |
| `fact_missing_inputs` | Missing input/fail-closed evidence. |
| `sys_params` | Tỷ giá, fiscal year, working days. |

Manual headcount import hiện reconcile source `manual`: DB không được giữ stale rows sau khi canonical CSV đã xóa. Exact-key quarantine helper chỉ xóa đúng key được chỉ định và không xóa CC khác.

## 12. Công thức output

Người dùng cần công thức để kiểm tra lại:

- Amount VND nguồn trực tiếp: `=amount`.
- Amount USD: `=ROUND(usd*$B$2,0)`.
- Driver count/unit price: `=count*unit_price`.
- Bus: `=bus_count*monthly_unit_price`.
- Birthday: `=count*152000` nếu unit price theo rule hiện hành.
- IT: `=ROUND((component sum)*$B$2,0)`.

Không paste số chết nếu có thể giữ công thức kiểm chứng. Nếu source thiếu driver/price bắt buộc, fail-closed thay vì tự bịa.

## 13. Dashboard và audit

Dashboard là lớp kiểm toán cho người dùng tài chính:

| Trạng thái | Ý nghĩa |
|---|---|
| XANH | Chưa thấy missing input cơ bản trong phạm vi audit hiện tại. |
| VÀNG | Còn dữ liệu cần nhập/chốt hoặc cảnh báo cần xem. |
| ĐỎ | Không có dữ liệu tính toán đủ cho CC sau lần chạy gần nhất. |

XANH không có nghĩa số liệu đúng 100%. Người dùng vẫn cần kiểm tra FORM output, công thức, source workbook, và audit report.

## 14. Commit trail gần nhất

| Commit | Nội dung |
|---|---|
| `33cbcd6` | Reconcile canonical 09.06 requirement wording. |
| `0a873ca` | Persist baseline manual headcount series. |
| `93231e7` | Add recurring bus passenger inputs. |
| `dde3fd4` | Map monthly bus prices from GA source. |
| `5383f75` | Canonical headcount path and CC-switch clearing. |
| `a2f0759` | Quarantine unconfirmed manual headcount keys. |
| `12d9232` | Mark legacy headcount source inactive. |

Các commit trên là mốc evidence hiện hành cho tài liệu này. File user/runtime data như CSV thật, DB, output, screenshot, workbook raw/reference không được commit nếu không có yêu cầu bàn giao rõ.

## 15. Checks nên chạy

Docs-only handover reconciliation:

```powershell
rg -n "<stale wording patterns from the phase note>" QUY_TRINH_NGHIEP_VU_MP2027.md
git diff --check
git diff --name-only
git diff
```

Import sanity:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONIOENCODING='utf-8'
py -B -c "import src.universal_app, scripts.run_e2e, src.utils.source_manifest"
```

Targeted tests khi sửa code:

```powershell
$env:PYTHONIOENCODING='utf-8'
py -m unittest tests.test_headcount_and_export tests.test_gui_bus_passenger_inputs tests.test_posting_month_logic
```

E2E một CC:

```powershell
$env:PYTHONIOENCODING='utf-8'
py scripts\run_e2e.py --fy 2027 --template docs\MP2027\FORM.xlsx --source docs\MP2027 --target-cc 1412000040
```

Nếu `OUTPUT_FY2027` bị Windows lock, chạy từ thư mục temp và dùng absolute paths.

## 16. Quy tắc an toàn khi tiếp tục

- Không dùng root `FORM.xlsx` làm runtime nếu khác chuẩn.
- Không dùng `FORM_old.xlsx` làm runtime.
- Không copy số liệu MP2026 sang FY2027 nếu chưa có confirmation.
- Không dùng legacy headcount artifact làm active input.
- Không tự điền headcount, event drivers, bus passengers, hoặc health-check split.
- Không dùng `dim_cost_centers` làm fallback headcount.
- Không biến empty field thành zero.
- Không xóa rộng bảng DB hoặc dữ liệu CC khác khi quarantine exact key.
- Không commit `raw/headcount_manual.csv`, `raw/bus_headcount_manual.csv`, `mp2027.db`, `OUTPUT_FY2027`, screenshots, backup, raw workbook, reference outputs, hoặc quarantine CSV.

## 17. Việc ưu tiên tiếp theo

P1:

- Thu thập/chốt headcount thật cho CC `1412000040`, gồm baseline `202603` và FY periods `202604..202703`.
- Chốt Nam/Nữ tháng 12 thật nếu health-check row 57 cần split.
- Chốt event drivers còn thiếu: quà không đi du lịch, My Episode, sự kiện 10 năm, kỷ niệm thành lập công ty.
- Chốt row/account cho Passport/VISA/GPLD/NNN nếu yêu cầu khác row 137.
- Audit output hiện hành theo từng CC trước khi final acceptance sáu claim.

P2:

- Nâng Dashboard event-driver check từ global sang theo CC nếu còn chỗ mơ hồ.
- Thêm audit riêng cho missing male/female December split.
- Kiểm tra GUI thực tế trên Windows sau mỗi thay đổi về input panel.

## 18. Tóm tắt cho agent tiếp theo

Bạn đang làm trong `D:\Sandbox\MP2027`.

Trạng thái verified tới commit `12d92325a0fffa9b03b6251d27210dbb69e032d0`:

- Canonical requirement: `raw/requirements/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026.xlsx`.
- Active source workbook dir: `docs/MP2027`.
- Active FORM: `docs/MP2027/FORM.xlsx`.
- Active manual headcount: `raw/headcount_manual.csv`.
- Active bus passenger driver template: `raw/bus_headcount_manual.csv`.
- Legacy headcount artifact: `docs/MP2027/headcount_manual_LEGACY_DO_NOT_USE.csv`, not active input.
- Bus passenger flow is implemented and not pending as JP/VN manual event.
- Six-claim final acceptance remains partial because real headcount input for CC `1412000040` is still missing.

Không bắt đầu bằng refactor lớn. Việc có giá trị nhất là bổ sung/chốt dữ liệu thật còn thiếu, chạy targeted audit, rồi chỉ sửa code khi audit chỉ ra lỗi cụ thể.
