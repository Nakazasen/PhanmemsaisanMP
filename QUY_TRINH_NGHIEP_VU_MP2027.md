# MP2027 Manager - Quy trình nghiệp vụ, vận hành và handover kỹ thuật

## Vận hành nhiều năm tài chính

Chương trình dùng chung cho FY2027, FY2028 và các năm sau. Mỗi năm phải có bộ dữ liệu riêng, không được dùng lại dữ liệu năm trước:

| Nội dung | Đường dẫn của FY<YYYY> |
|---|---|
| FORM và file chi phí | `docs/MP<YYYY>` |
| Nhân sự, thời gian, bảng dấu chọn đồng phục/cốc xếp, dữ liệu nhập tay | `raw/FY<YYYY>` |
| File công bố kết quả | `OUTPUT_FY<YYYY>` |
| Lịch sử bất biến | `RUN_HISTORY/FY<YYYY>/<run_id>` |

Khi chọn năm, chương trình tự đề xuất các đường dẫn trên. Người dùng có thể chọn tay một đường dẫn khác, nhưng hệ thống kiểm tra trước phải xác nhận toàn bộ file đúng FY đã chọn. Thiếu file, thiếu sheet FY, có hai file cùng loại, thiếu nhóm tháng hệ thống, dữ liệu nhập tay khác năm hoặc phát hiện file FY khác đều dừng trước khi tính; không tự lấy FORM, đơn giá, nhân sự, bảng đồng phục hoặc số liệu của năm trước.

Mỗi lần chạy chính thức tạo một thư mục lịch sử riêng có `run.db`, `run_manifest.json`, báo cáo JSON/Markdown, checksum nguồn và bản kết quả. Chỉ lần chạy thành công mới được chép nguyên khối sang `OUTPUT_FY<YYYY>`; nếu lỗi khi công bố, kết quả công bố trước đó được khôi phục. Có thể mở nút **Lịch sử lần chạy** để lọc theo năm, ngày, trạng thái, mã phòng hoặc hạng mục, sau đó mở kết quả, báo cáo kiểm tra hoặc CSDL của lần chạy. Lịch sử chỉ đọc, không sửa.

Để chuẩn bị FY mới, người nghiệp vụ tạo đủ `docs/MP<YYYY>`, `raw/FY<YYYY>` và bảng thứ tự nguồn của năm, rồi chọn năm đó trên giao diện. Không sao chép đơn giá hoặc dấu chọn từ FY cũ nếu chưa có file nguồn FY mới được duyệt.

Ngày cập nhật: `2026-07-11`

`IMPLEMENTATION_VERIFIED_AT_COMMIT=12d92325a0fffa9b03b6251d27210dbb69e032d0`
`HANDOVER_CONTENT_BASE_COMMIT=2b87fadbed00b8fe99d371435d8e5bfc43fa9d31`
`HANDOVER_METADATA_REVIEWED_AFTER_COMMIT=13815d9b2267fac97e2a020ef5044c94942521df`
`CANONICAL_SOURCE_USER_CONFIRMED_AT=2026-07-11`

`IMPLEMENTATION_VERIFIED_AT_COMMIT` là trạng thái code/test được handover kiểm chứng. `HANDOVER_CONTENT_BASE_COMMIT` là commit tạo bản reconciliation nội dung handover chính. `HANDOVER_METADATA_REVIEWED_AFTER_COMMIT` là commit gần nhất đã review/chỉnh metadata và thuật ngữ.

Tài liệu này là handover tổng hợp cho dự án MP2027 Manager. Canonical business requirement là workbook Excel ngày `10.07.2026` tại `raw/Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx`; người dùng đã xác nhận đây là bản mới nhất ngày 11.07.2026. Markdown này không thay thế workbook yêu cầu, ảnh minh họa, audit log, hoặc code/test evidence. Khi có mâu thuẫn, thứ tự ưu tiên là:

1. Workbook canonical ngày `10.07.2026`.
2. Code và test đã commit.
3. Audit report hoặc knowledge doc có timestamp/commit rõ.
4. Markdown handover này.
5. Tài liệu lịch sử hoặc file legacy chưa được gắn nhãn hiện hành.

Thông tin lịch sử không tự động override code hiện tại. Mọi claim về implementation phải có commit/test evidence hoặc được đánh dấu là cần audit lại.

Nguồn trạng thái work hiện hành:

- `docs/handover/HANDOVER_FOR_NEXT_AGENT.md` — handover hiện hành duy nhất.
- `docs/audits/AUDIT_STATUS_INDEX.md` — successor và lifecycle của audit cũ.

Các “recommended next phase” trong audit/knowledge lịch sử không phải work mở nếu không xuất hiện trong current register.


## Reconcile note - workbook canonical updated

Historical reconcile time: `2026-07-07 06:40:00`. Requirement Markdown and machine-readable mapping were refreshed against the 09.06.2026 workbook. From 11.07.2026, the user-confirmed canonical workbook is `raw/Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx`; implementation claims based on the historical reconcile require a current audit against that file. The 10.07 workbook retains 10 sheets and adds/reconfirms bus inputs, fixed-assets coverage, health-check de-duplication, new-hire allocation, and source-order output behavior.

---
## 1. Mục tiêu chương trình

MP2027 Manager là ứng dụng Windows desktop dùng Python/Tkinter để tổng hợp dữ liệu ngân sách MP FY2027 từ nhiều file Excel nguồn, tính phân bổ chi phí theo rule, rồi xuất FORM theo từng Cost Center.

Nguyên tắc nghiệp vụ: chương trình thay thao tác nhập tay lặp lại nhưng không tự bịa số liệu. Khoản nào không suy luận an toàn từ source workbook hoặc manual CSV đã xác nhận thì phải để trống, ghi missing input, hoặc yêu cầu người dùng nhập/chốt.

## 2. Nguồn yêu cầu và bằng chứng

| Loại | Đường dẫn | Vai trò | Trạng thái |
|---|---|---|---|
| Canonical requirement | `raw/Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx` | Nguồn yêu cầu nghiệp vụ cao nhất, do người dùng xác nhận | CANONICAL |
| Historical visual support (09.06) | `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026_ảnh.xlsx` | Ảnh/annotation của requirement 09.06; không xác minh yêu cầu 10.07 | HISTORICAL |
| Historical full-coverage duplicate (09.06) | `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026_ảnh_FULL_COVERAGE.xlsx` | Bản duplicate kiểm tra coverage hình ảnh cho 09.06 | HISTORICAL |
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
| Facility / IT / GA / birthday / NNN parsers | PASS_WITH_SCOPE | Parser hiện có cho các nguồn chính; output cần audit theo từng CC khi dữ liệu nguồn đổi. |
| Fixed assets | IMPLEMENTED_PENDING_BUSINESS_ACCEPTANCE | Parser/writer đã có per-asset rounding, FX theo lần chạy, terminal-month handling, fail-closed Q/cache, zero-vs-blank và provenance. Business snapshot/manual-layer decisions và comparator acceptance vẫn mở. |
| Manual headcount channel | PARTIAL | Active path là `raw/headcount_manual.csv`; vẫn thiếu headcount thật cho một số CC. |
| CC `1412000040` headcount | BLOCKED_BY_INPUT | Chưa có chuỗi headcount thật đủ để accept các claim phụ thuộc new-hire delta. |
| Bus passenger drivers | PASS | GUI có input scalar; allocator nhân scalar count với monthly unit price từ GA source. |
| Health-check male/female split | BLOCKED_BY_INPUT | Cần Nam/Nữ tháng 12 thật nếu muốn tính row health-check theo split. |
| Manual event drivers | PARTIAL | Channel có sẵn; event chưa có nguồn máy đọc vẫn cần người dùng nhập/chốt. |
| GUI pipeline responsiveness | IMPLEMENTED_PENDING_ACCEPTANCE | UI queue/child process đã có; cần một Windows session thật để accept hoặc stack capture nếu còn treo. |
| Legacy headcount source hardening | PASS | Docs legacy đã đổi tên DO_NOT_USE và parser guardrail không silent import. |
| Final six-claim acceptance | PARTIAL | Defect cũ đã có successor evidence; full canonical-10.07/real-data acceptance vẫn chưa hoàn tất. |

## 4. Runtime directory model

Repo dev chuẩn: `D:\Sandbox\MP2027`.

| Thành phần | Active path | Ghi chú |
|---|---|---|
| FORM template/runtime | `docs/MP2027/FORM.xlsx` | Dùng load master và làm template. Mỗi lần chạy lấy tỷ giá từ GUI/CLI (hoặc `B2` nếu CLI không truyền giá trị), rồi ghi cùng giá trị vào `B2` của mọi file output. |
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
- Business item/content: `通勤送迎費`.
- Account JP name: `福利厚生費`.
- Account code resolution: Cost Center -> `原価センタ` -> `原価区分` -> `勘定科目` (`製造`/`一般`/`販売`) -> `account_code`.
- Monthly unit price lấy từ GA workbook `docs/MP2027/総務課 FY2027 MP 振替予定.xlsx`.
- Sheet nguồn: `FY2027予定`.
- Expat/Japanese bus unit price: `B9:M9`.
- Vietnamese bus unit price: `B10:M10`.
- Formula: scalar count x monthly unit price.
- Nếu thiếu price nguồn, logic fail-closed và ghi missing input; không tự tạo số.

Hai field bus độc lập với staff/worker/male/female headcount. Chỉnh headcount không được làm mất bus drivers và ngược lại.

## 7. Six-claim acceptance status

Bảng này là successor evidence cho các defect N3Q/N3S và dùng run historical 09.06; không phải full acceptance của workbook canonical 10.07. Không tự biến kết luận lịch sử thành backlog hiện hành; mục tiêu hiện tại chỉ lấy từ `docs/handover/HANDOVER_FOR_NEXT_AGENT.md`.

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
| 38 | Khấu hao thiết bị | LEGACY_STAGING_ONLY; SOURCE_ORDER_DYNAMIC | Có thể là vùng staging legacy; complete-v1 không coi đây là fixed output row. Vị trí hiện hành phụ thuộc source manifest/order. |
| 40 | Lãi nhà | CURRENT_CODE_VERIFIED | Facility. |
| 41 | Lãi đất | CURRENT_CODE_VERIFIED | Facility. |
| 42 | Lãi thiết bị | LEGACY_STAGING_ONLY; SOURCE_ORDER_DYNAMIC | Có thể là vùng staging legacy; complete-v1 không coi đây là fixed output row. Vị trí hiện hành phụ thuộc source manifest/order. |
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

1. Chốt một tỷ giá USD/VND cho lần chạy: GUI/CLI có giá trị thì dùng giá trị đó; CLI không có giá trị thì đọc `B2` của FORM. Ghi tỷ giá hiệu lực vào `sys_params` và `B2` của mọi file output.
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
8. Audit pipeline sinh `OUTPUT_FY2027/BAO_CAO_KIEM_TRA/BAO_CAO_LAN_CHAY.xlsx`,
   `DU_LIEU_CON_THIEU.xlsx` và `KIEM_TRA_TY_GIA.xlsx`.

### Audit tài sản cố định và lịch sử giải thích

Luồng tính tài sản cố định trong pipeline chính đọc source workbook theo manifest và xuất theo
source-order động của complete-v1; không được giả định dòng FORM cố định 38/42. Code làm tròn từng
tài sản trước khi cộng, dừng sau tháng hết khấu hao, giữ phân biệt ô trống/số 0 và ghi provenance
source file/sheet/row vào CSDL.

Để đối chiếu với file phòng ban và lưu lịch sử từng lần phân loại, chạy:

```powershell
py scripts/audit_fixed_assets_cross_trace.py
py scripts/classify_fixed_assets_mismatches.py
py scripts/build_fixed_assets_business_decision_pack.py
```

Mỗi lần chạy classifier tạo một thư mục mới trong
`docs/audits/history/fixed_assets`, không ghi đè lịch sử cũ; đồng thời lưu các ô, bằng chứng và
phân loại vào hai bảng `audit_fixed_asset_mismatch_runs` và
`audit_fixed_asset_mismatch_history` trong `mp2027.db`. Đây là luồng audit bổ sung, không tự chạy
khi người dùng chỉ bấm `CHẠY TÍNH TOÁN` trên GUI.

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
| `d65d07b` | Kế thừa & bảo tồn chi phí riêng theo năm tài chính (`manual_special_cost_sections.py`). |
| `c3b8575` | Sắp xếp thứ tự dòng chi phí kéo thả chuột trên sheet Chi tiết MP (`output_cost_row_ordering.py`). |
| `697e285` | Tìm kiếm nhanh phòng ban trực tiếp trên giao diện chính. |
| `cd1c725` | Khắc phục an toàn giới hạn 31 ký tự tên sheet ngầm `_mp2027_manual_special_meta` và dọn dòng IT trống. |
| `3c8d4fc` | So sánh biến động cùng kỳ YoY với bộ giải công thức AST, biểu đồ Top 12 Matplotlib & native Excel chart. |
| `e6dfcf9` | Singleton editor window manager & khóa an toàn khi Pipeline đang xuất dữ liệu. |
| `514a179` | Đồng bộ kiến trúc và feature registry theo chuẩn phát hành `HASH_ONLY_LAN`. |
| `6d13aa5` | Bổ sung tài liệu vận hành cho 5 tính năng mới và cập nhật trace code/test. |
| `051e480` | Gắn nhãn superseded/archive cho knowledge base v1, experimental wiki và 44 audit Phase 42. |

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

Fixed-assets deep audit:

- Lifecycle và bằng chứng fixed-assets lịch sử: `docs/audits/AUDIT_STATUS_INDEX.md`; không có handover fixed-assets hiện hành riêng.
- Audit GAP 15.07 là provenance; không dùng bảng “Chưa chốt” làm lý do hỏi Accounting trước khi đọc đủ evidence.
- Cross-trace canonical → source/calculation MP2026/MP2027 → reference outputs FY2026/FY2027 → code/tests; tạo asset ledger và decision matrix có file/sheet/cell/row evidence.
- Chỉ chuyển phần còn mâu thuẫn/thiếu sau cross-trace sang Accounting/MP review.
- Không hardcode FY, period, FX, filename/sheet, row identity, category/account theo một FY hoặc xóa history FY khác.
- Không final acceptance fixed-assets cho đến khi comparator kiểm tra theo CC × asset × month × cost type và true mismatch đã được xử lý/chấp thuận.

P1 chung:

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

Trạng thái implementation verified tới commit `12d92325a0fffa9b03b6251d27210dbb69e032d0`; nội dung handover chính dựa trên commit `2b87fadbed00b8fe99d371435d8e5bfc43fa9d31`; metadata và thuật ngữ đã được review sau commit `13815d9b2267fac97e2a020ef5044c94942521df`:

- Canonical requirement: `raw/Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx`.
- Active source workbook dir: `docs/MP2027`.
- Active FORM: `docs/MP2027/FORM.xlsx`.
- Active manual headcount: `raw/headcount_manual.csv`.
- Active bus passenger driver template: `raw/bus_headcount_manual.csv`.
- Legacy headcount artifact: `docs/MP2027/headcount_manual_LEGACY_DO_NOT_USE.csv`, not active input.
- Bus passenger flow is implemented and not pending as JP/VN manual event.
- Six-claim final acceptance remains partial because real headcount input for CC `1412000040` is still missing.

Không bắt đầu bằng refactor lớn. Việc có giá trị nhất là bổ sung/chốt dữ liệu thật còn thiếu, chạy targeted audit, rồi chỉ sửa code khi audit chỉ ra lỗi cụ thể.

## 19. Đồng phục và cốc xếp

- Chương trình đọc dấu `〇` tại cột F:U của trang `原価センタ`; không phân loại áo theo nhân viên/công nhân và không tự ưu tiên áo polo.
- Nếu phòng được chọn áo ngắn tay hoặc áo polo thì toàn bộ người mới của phòng dùng đúng loại đó. Phòng an ninh dùng hạng mục riêng. Nếu chọn trùng nhiều loại áo ngắn tay, chi phí áo bằng 0 và chương trình yêu cầu sửa nguồn.
- Người mới mỗi tháng là phần tăng không âm so với tháng trước. Quần, áo, giày, mũ dùng tổng nhân viên mới và công nhân mới; cốc người mới chỉ dùng công nhân mới.
- Áo cấp theo mùa: tháng 2 cấp bù áo ngắn tay/polo cho người vào tháng 1; tháng 10 cấp bù áo dài tay cho người vào tháng 5–9.
- Cốc định kỳ chỉ nhập ở tháng 2 hoặc tháng 8 trong cửa sổ `Nhập sự kiện thiếu dữ liệu` → `Cốc xếp định kỳ`. Phải nhập số nguyên từ 0 trở lên; số 0 là đã xác nhận không phát, còn để trống thì chi phí bằng 0 và có cảnh báo.
- Chi phí cấp đổi do hỏng hoặc mất vẫn phải lấy số phát thực tế, chương trình không suy ra từ số người mới.
- Nhật ký `audit_uniform_cup_calculation` lưu dấu chọn nguồn, số người mới, tháng nguồn, số lượng, đơn giá, công thức, tài khoản và loại phát để giải thích lại cho người dùng.

## 20. Kế thừa và bảo tồn chi phí riêng theo năm tài chính

- **Mục đích**: Bảo toàn các dòng chi phí riêng nhập tay của từng phòng ban khi tính toán lại hoặc chuyển tiếp sang năm tài chính kế tiếp (`src/engine/manual_special_cost_sections.py`).
- **Nguyên tắc bảo tồn**:
  - Dòng chi phí riêng tự động xếp dưới nhóm chi phí chung và giữ nguyên liên kết công thức/mô tả.
  - Khi chạy lại trong cùng năm tài chính: Giữ nguyên số tiền và công thức đã nhập.
  - Khi tạo/kế thừa sang năm tài chính mới (`is_new_fiscal_year=True`): Giữ nguyên cấu trúc dòng, tên hạng mục và công thức, nhưng tự động **xóa trắng các ô số tiền** để người dùng nhập dự toán mới.
- **Cấu hình**: Cấu hình thư mục kế thừa `manual_special_inheritance_dir` trong `project.json`.

## 21. Tùy biến sắp xếp thứ tự dòng chi phí kéo-thả

- **Mục đích**: Cho phép người dùng tùy ý điều chỉnh thứ tự hiển thị các dòng chi phí trên sheet `Chi tiết MP` (`内訳ﾘｽﾄ(4～3月)`) trực tiếp qua giao diện GUI (`src/engine/output_cost_row_ordering.py`).
- **Thao tác**:
  - Mở hộp thoại `Sắp xếp thứ tự dòng chi phí...` từ menu giao diện chính.
  - Chọn dòng chi phí và kéo thả (hoặc dùng nút Lên/Xuống) để thay đổi vị trí.
  - Bấm `Lưu thứ tự`. Hệ thống sẽ ghi nhận thứ tự vào sheet ẩn `_mp2027_manual_special_meta` trong file Excel xuất ra.
- **Bảo toàn an toàn**: Khi pipeline chạy lại, thứ tự đã lưu được ưu tiên áp dụng tự động mà không làm sai lệch logic tính toán hoặc mất dòng.

## 22. Tìm kiếm nhanh phòng ban trên màn hình chính

- **Mục đích**: Tìm kiếm tức thì trung tâm chi phí trong danh sách hàng trăm phòng ban (`src/universal_app.py`).
- **Thao tác**: Nhập mã số (ví dụ `1412000040`) hoặc tên phòng ban (tiếng Nhật/tiếng Việt) vào ô tìm kiếm nhanh phía trên danh sách phòng ban. Danh sách sẽ tự động lọc realtime theo từ khóa gõ vào.

## 23. So sánh biến động ngân sách cùng kỳ (YoY) và biểu đồ trực quan

- **Mục đích**: Tự động so sánh chênh lệch dự toán ngân sách giữa các lần chạy hoặc giữa hai năm tài chính (`src/engine/variance_analyzer.py`, `src/ui/variance_chart.py`).
- **Tính năng nổi bật**:
  - **Bộ giải công thức AST độc lập (`_MpFormulaResolver`)**: Tự động tính toán các ô công thức Excel mà không phụ thuộc vào Excel application.
  - **Cửa sổ Biểu đồ Tương tác**: Nhấn nút `Xem biểu đồ biến động` trên tab So sánh biến động để mở biểu đồ Top 12 hạng mục tăng/giảm mạnh nhất với font chữ đa ngôn ngữ (NotoSans, Meiryo, YuGothic).
  - **Nhúng biểu đồ Native vào Excel**: Khi xuất file so sánh biến động, hệ thống tự động nhúng đối tượng `BarChart` chuẩn của Excel vào sheet kết quả (`src/utils/excel_variance_writer.py`).
- **An toàn giao diện**: Áp dụng cơ chế khóa nút bấm khi pipeline đang xử lý (`_set_pipeline_ui_busy`) và quản lý chống mở trùng lặp cửa sổ (`_register_singleton_editor`).
