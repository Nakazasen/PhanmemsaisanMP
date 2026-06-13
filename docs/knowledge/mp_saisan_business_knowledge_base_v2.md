# Phase 42N3H Source Notice

Current canonical requirement: `raw/requirements/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026.xlsx`.
Current visual support: `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026_ảnh.xlsx`.
Versioned full-coverage duplicate: `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026_ảnh_FULL_COVERAGE.xlsx`, retained only as a byte-identical duplicate and never above the official visual-support path.
Obsolete incomplete visual: `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026_ảnh_LEGACY_INCOMPLETE.xlsx`, retained only for historical comparison and not for active requirement interpretation.
Obsolete old visual requirement: `raw/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026_ảnh.xlsx`; do not use it.
If there is any conflict, the canonical workbook wins over the visual snapshot, Markdown, audit history, and derived descriptions.

Current source hierarchy last verified:

- `LAST_VERIFIED_AT_COMMIT=b9ea4e4bed4e4716aeb9c223ed8b0de56e5e68d8`
- Canonical requirement date: `09.06.2026`
- Implementation status last verified against code/audits at the same commit unless a row says `STATUS_REQUIRES_CURRENT_CODE_AUDIT`.
- Historical content must not override current audits, code, or the canonical 09.06.2026 workbook.

# MP Saisan Business Knowledge Base v2 - Full Business Specification

## 1. Purpose and current truth

MP Saisan là workflow sinh workbook MP FY2027 theo từng cost center/phòng ban. Target hiện tại là CC `1412000040` / `電気製造技術課`. Sheet chi tiết chính là `内訳ﾘｽﾄ(4～3月)`, thường chứa account, mô tả dòng, và month vector F:Q cho tháng 4 đến tháng 3.

Physical row-count gap `136` là counting fact giữa generated v1 và primary reference, không phải bằng chứng rằng công ty thiếu dữ liệu hoặc thiếu source. Previous "missing data/source" conclusion is NOT final. Chỉ được kết luận source-derived gap sau khi phân loại role file và chứng minh provenance từng dòng. Current best path: **HYBRID PATH**.

## 2. Source hierarchy and trust rules

| Source layer | Path | Role | Trust rule |
| ------------ | ---- | ---- | ---------- |
| Excel canonical requirement | `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026.xlsx` | Source of truth requirement | Thắng visual snapshot, Markdown, audit history, và derived descriptions nếu conflict. |
| Official visual support snapshot | `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026_ảnh.xlsx` | Audit visual support only | Dùng để kiểm visual/layout/ảnh; không thay Excel gốc. Each canonical source drawing is fully contained in at least one capture; overall coverage is 159/159. |
| Versioned full-coverage duplicate | `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026_ảnh_FULL_COVERAGE.xlsx` | Duplicate visual support artifact | Byte-identical duplicate of the official visual-support path; không outrank official path. |
| Obsolete incomplete visual | `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026_ảnh_LEGACY_INCOMPLETE.xlsx` | Historical visual reference only | Incomplete 34-image artifact; not for active requirement interpretation. |
| Derived MD | `docs/requirements/cai_tien_nhap_du_lieu_chung.md` | Search/helper | Chỉ là bản dẫn xuất. |
| FORM template | `raw/FORM.xlsx` | Template/output structure | Hướng dẫn target rows/formula style, không tự là amount source. |
| Primary reference | `reference_outputs/primary/16.KDTVN 電気製造技術課_MP FY2027_各予定(Ver01).xlsx` | Output chuẩn tham khảo | Guide skeleton/formula/order, không là raw amount proof nếu chưa proven. |
| Secondary pool | `reference_outputs/secondary/FY2027/` | Generated output/skeleton references | Guide skeleton/formula/order; không claim source-derived amount. |
| Manual CSV | `raw/event_drivers_manual.csv` | Manual input channel | Valid only if rows exist and schema matches. |
| Manual CSV | `raw/special_costs_manual.csv` | Manual input channel | Valid only if rows exist and schema matches. |
| Manual CSV | `raw/headcount_manual.csv` | Manual input channel | Valid only if rows exist and schema matches. |

Primary/secondary references can guide skeleton, formula, row order, and reference-assisted output. They are not raw source amount proof unless upstream source workbook/sheet/row/cell/month values are proven. Manual CSV is valid only when schema-valid rows exist.

### Account Lookup Rule

Khi cần xác định `account_code`, không lookup trực tiếp bằng description. Quy tắc tra account phải đi theo chuỗi nghiệp vụ:

`Cost Center -> 原価センタ -> 原価区分 -> 勘定科目 column 製造/一般/販売 -> account_code`

Ý nghĩa non-tech:

1. Bắt đầu từ cost center/phòng ban, ví dụ `1412000040`.
2. Tra sheet hoặc master `原価センタ` để biết cost category `原価区分`.
3. Dùng `原価区分` để chọn đúng cột trong `勘定科目`.
4. Cột cần chọn là `製造`, `一般`, hoặc `販売` tùy loại cost center/category.
5. Từ dòng/cột đúng đó mới lấy `account_code`.

Nếu bỏ qua `原価区分` hoặc chọn sai cột `製造/一般/販売`, account có thể match sai dù description giống nhau.

## 3. File-order output rule

Requirement states:

- “Điền dữ liệu theo thứ tự dưới đây”.
- “chạy theo thứ tự file là được”.
- “không nhất thiết phải vào row nào cả”.
- “chạy xong 1 file thì cách 1 dòng”.

Therefore, file-order mode may generate rows by source-file order rather than primary row numbers, with blank separator row after a completed source group.

Status freshness: `LAST_VERIFIED_AT_COMMIT=b9ea4e4bed4e4716aeb9c223ed8b0de56e5e68d8`. Recent audits verify Column S normalization, new-hire fail-closed behavior, duplicate new-hire suppression, reference-fill quarantine/scope, and one-blank-row spacing for the source-order blocks that were written. They do not certify every module as complete; rows marked `STATUS_REQUIRES_CURRENT_CODE_AUDIT` need a fresh code/output audit before implementation claims are reused.

| Source order | File | Role | Current handling | Status |
| -----------: | ---- | ---- | ---------------- | ------ |
| 1 | `施設課　MPFY2027.xlsx` | Facility utilities/building/land | Written source-order block observed in 42N3Y acceptance; historical fixed rows 200-205 require fresh row audit | PARTIAL_PASS_FOR_WRITTEN_BLOCKS; `LAST_VERIFIED_AT_COMMIT=b9ea4e4bed4e4716aeb9c223ed8b0de56e5e68d8` |
| 2 | `固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx` | Fixed assets master/reference | Written source-order block observed, but source-derived completeness is not certified | STATUS_REQUIRES_CURRENT_CODE_AUDIT |
| 3 | `システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls` | System cost Q1 | Written source-order block observed, but historical combined-row implementation needs fresh audit | STATUS_REQUIRES_CURRENT_CODE_AUDIT |
| 4 | `システム課金金額(Simulation)_FY2027 July.2026 ~ Dec.2026(Change AMS & PLM price).xls` | System cost Q2-Q3 | Period-specific completeness not certified by the latest acceptance audit | STATUS_REQUIRES_CURRENT_CODE_AUDIT |
| 5 | `システム課金金額(Simulation)_FY2027 Jan.2027 ~ March.2027(Change SAP price).xls` | System cost Q4 | Period-specific completeness not certified by the latest acceptance audit | STATUS_REQUIRES_CURRENT_CODE_AUDIT |
| 6 | `総務課 FY2027 MP 振替予定.xlsx` | Admin/GA consumables/allocation | Written source-order block observed; new-hire allocation is fail-closed because target headcount drivers are missing | PASS_FAIL_CLOSED_FOR_NEW_HIRE; STATUS_REQUIRES_CURRENT_CODE_AUDIT_FOR_REMAINDER |
| 7 | `Sinh nhật MP FY2027.xlsx` | Birthday | Written source-order block observed, but source-derived completeness is not certified | STATUS_REQUIRES_CURRENT_CODE_AUDIT |
| 8 | `FY2027配賦額一覧 (2025.12.29).xlsx` | Allocation/travel | Allocation/headcount block was suppressed by fail-closed missing-driver checks | BLOCKED_BY_MISSING_DRIVER_DATA |
| 9 | `Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx` | NNN paperwork | Written source-order block observed, but source-derived completeness is not certified | STATUS_REQUIRES_CURRENT_CODE_AUDIT |
| 10 | `event_drivers_manual.csv` | Manual event input | Channel exists; target rows require schema-valid data and fresh audit | STATUS_REQUIRES_CURRENT_CODE_AUDIT |
| 11 | `special_costs_manual.csv` | Manual special costs | Channel exists; target rows require schema-valid data and fresh audit | STATUS_REQUIRES_CURRENT_CODE_AUDIT |
| 12 | `headcount_manual.csv` | Manual headcount | Channel exists; target CC still lacks complete monthly headcount driver data | BLOCKED_BY_MISSING_DRIVER_DATA |

## 4. Module detail matrix

| Module | Business purpose | Source workbook/sheet | Target/output rows or range | Main account/CC rules | Formula/month rule | Current implementation status | Remaining blocker |
| ------ | ---------------- | --------------------- | --------------------------- | --------------------- | ------------------ | ----------------------------- | ----------------- |
| Facility / 施設課 | Facility cost: building, land, utilities | `raw/施設課　MPFY2027.xlsx`; sheets include depreciation, interest, electric/water | historical rows 200-205; latest complete-v1 acceptance used source-order block rows, not a universal fixed-row proof | Target CC `1412000040`; aliases `電気代`/`水道代` | `ROUND(source_value*$B$2,0)` for 12 months where VND conversion is needed; electricity/water currency handling must preserve source currency/conversion policy | PARTIAL_PASS_FOR_WRITTEN_BLOCKS; STATUS_REQUIRES_CURRENT_CODE_AUDIT_FOR_FULL_COMPLETENESS | Facility details and fixed row claims need fresh source/output audit. |
| Admin / GA consumables | Consumables, allocation, event/month, new employee, hiring medical check | `raw/総務課 FY2027 MP 振替予定.xlsx` | historical rows 207-209; known FORM targets include row 58, 97, 98 for some admin/new employee items | CC/account per mapped consumable/allocation rows | driver/headcount/unit price/month allocation; 12-month costs and event/month costs require explicit driver | PASS_FAIL_CLOSED_FOR_NEW_HIRE; STATUS_REQUIRES_CURRENT_CODE_AUDIT_FOR_REMAINDER | Target CC lacks complete monthly headcount driver data; other admin/allocation rows need row-level provenance. |
| System Cost | IT/system charge across three simulation periods | Three `システム課金金額(Simulation)_FY2027...xls` files | historical row 211; row 212 blank | Combined system cost for target CC | Month values come from three source files by period; combined row only under explicit flag | STATUS_REQUIRES_CURRENT_CODE_AUDIT | Re-audit combined row behavior against canonical 09.06 before treating it as complete. |
| Fixed Assets / 固定資産 | Fixed asset depreciation/interest/detail expense | `raw/固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx` | depreciation row 38 F38:Q38; interest row 42 F42:Q42; fresh output had a written block but not certified completeness | Account `5005026371` has 75 primary rows | Need exact source workbook/sheet/row/cell + Apr-Mar monthly values | STATUS_REQUIRES_CURRENT_CODE_AUDIT | Master/reference and CC evidence exist, but not enough current proof to claim complete. Do not code guess. |
| Birthday / Sinh nhật | Birthday benefit/cost | `raw/Sinh nhật MP FY2027.xlsx` | FORM row 59, F59:Q59; fresh output had a written block but not certified completeness | Target row/account needs confirmation | `number_of_people * unit_price` by month after source row is confirmed | STATUS_REQUIRES_CURRENT_CODE_AUDIT | Resolve source row and Apr-Mar values/formula mapping before any completion claim. |
| NNN paperwork | Foreigner paperwork cost estimate | `raw/Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx` | FORM row 137, F137:Q137; fresh output had a written block but not certified completeness | Needs CC/account proof | Need source row/cell/month mapping | STATUS_REQUIRES_CURRENT_CODE_AUDIT | Source mapping remains open, but target range is known. |
| Allocation / 配賦 | Allocation/travel/shared costs | `raw/FY2027配賦額一覧 (2025.12.29).xlsx` | no safe final rows yet | Account/CC invariant matching required | Exact F:Q mapping required | BLOCKED_BY_MISSING_DRIVER_DATA / STATUS_REQUIRES_CURRENT_CODE_AUDIT | Travel/allocation rows need exact mapping and complete target headcount drivers. |
| Manual CSV channels | Structured manual input | `event_drivers_manual.csv`, `special_costs_manual.csv`, `headcount_manual.csv` | generated only from schema-valid rows | Manual rows must include target identity fields | Values from CSV; provenance `MANUAL_INPUT` | STATUS_REQUIRES_CURRENT_CODE_AUDIT | Header-only/no target rows must not generate guessed rows. |
| Primary/secondary reference | Skeleton/formula/order guide | primary and secondary output references | reference-assisted only | Not source-derived without upstream provenance | Can preserve formulas/order | PASS_SCOPED_QUARANTINE; `LAST_VERIFIED_AT_COMMIT=b9ea4e4bed4e4716aeb9c223ed8b0de56e5e68d8` | Unscoped primary reference rows are quarantined, not emitted into the workbook. |

### 4.1 Facility / 施設課

Historical fixed-row note: Facility rows `200-205`, blank row `206`. Latest complete-v1 acceptance used source-order rows and does not make these row numbers universal completion proof.

Items:

- `building_depreciation` / `Khấu hao nhà`
- `land_depreciation` / `Khấu hao đất`
- `building_interest` / `Lãi nhà`
- `land_interest` / `Lãi đất`
- `electricity` / `Điện`
- `water` / `Nước`

Aliases:

- `電気代` maps to generated `electricity`.
- `水道代` maps to generated `water`.

Status: PARTIAL_PASS_FOR_WRITTEN_BLOCKS with `LAST_VERIFIED_AT_COMMIT=b9ea4e4bed4e4716aeb9c223ed8b0de56e5e68d8`. This confirms the written block participated in the latest spacing acceptance, not that every Facility amount or historical fixed row is complete. Remaining Facility details outside this block require `STATUS_REQUIRES_CURRENT_CODE_AUDIT`.

### 4.2 Admin / GA consumables

Source workbook: `raw/総務課 FY2027 MP 振替予定.xlsx`.

Historical fixed-row note: Admin rows `207-209`, blank row `210`. Treat these as historical implementation references until a fresh code/output audit confirms them.

Items:

- `toilet_paper`
- `hand_soap`
- `alcohol_disinfectant`

Status: PASS_FAIL_CLOSED_FOR_NEW_HIRE with `LAST_VERIFIED_AT_COMMIT=b9ea4e4bed4e4716aeb9c223ed8b0de56e5e68d8`; target CC `1412000040` still lacks complete monthly headcount driver data, so real new-hire monthly amounts are not certified. Remaining admin/allocation rows require `STATUS_REQUIRES_CURRENT_CODE_AUDIT` and row-level provenance.

Expanded admin allocation rules:

- **12-month costs**: allocate across F:Q only when source gives monthly amount or a proven monthly driver.
- **event/month costs**: only fill event months where event timing and driver are known.
- **new employee costs**: use hiring/new employee driver by month; known FORM targets include new employee notebook staff row `97` and worker row `98`.
- **hiring medical check**: known FORM target row `58`; needs source driver/headcount and unit price.
- **unit price / driver / headcount**: formula should be `driver_or_headcount * unit_price`, optionally allocated by month, and must cite the source row/cell.

### 4.3 System Cost

Source files:

- `raw/システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls`
- `raw/システム課金金額(Simulation)_FY2027 July.2026 ~ Dec.2026(Change AMS & PLM price).xls`
- `raw/システム課金金額(Simulation)_FY2027 Jan.2027 ~ March.2027(Change SAP price).xls`

Historical fixed-row note: row `211`, item_id `system_cost_combined`, blank row `212`. Treat this as historical implementation context until a fresh code/output audit confirms it.

Status: STATUS_REQUIRES_CURRENT_CODE_AUDIT. Historical notes describe a combined system cost row, but current docs must not treat it as complete until a fresh code/output audit verifies it against canonical 09.06.2026.

System Cost formula policy:

- Use the three simulation files by period: Apr-Jun, Jul-Dec, Jan-Mar.
- Month F:Q must be filled from the matching source period only.
- The v1 behavior is a combined `system_cost_combined` row, not a detailed split.
- Do not infer missing months from neighboring months unless source workbook formula proves it.
- Keep behavior behind explicit flag; default export unchanged.

### 4.4 Fixed Assets / 固定資産

Source workbook: `raw/固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx`.

Known account/group: `5005026371` has 75 primary rows in gap matrix. The fixed asset workbook has master/reference and CC evidence, but not enough one-to-one row/cell/month values for source-derived export.

Current status: STATUS_REQUIRES_CURRENT_CODE_AUDIT.

Remaining blocker: need workbook/sheet/row/cell + account + CC + Apr-Mar monthly values. Do not code guess. Secondary may be used as skeleton/reference guide, not raw amount proof.

Known fixed-asset FORM targets:

- Fixed asset depreciation: row `38`, range `F38:Q38`.
- Fixed asset interest: row `42`, range `F42:Q42`.
- Rows 38/42 are known target ranges, but source-derived generation still requires raw fixed-asset source proof.

### 4.5 Birthday / Sinh nhật

Source workbook: `raw/Sinh nhật MP FY2027.xlsx`.

Requirement status: Birthday/Tiền sinh nhật image indicates FORM target row `59`, F59:Q59. Old note about row `63` is intermediate/source area, not target row.

Current status: STATUS_REQUIRES_CURRENT_CODE_AUDIT. Remaining blocker: source row and Apr-Mar values/formula mapping must be confirmed before any completion claim.

Birthday formula policy:

- Known target: FORM row `59`, range `F59:Q59`.
- Row `63` is intermediate/source area, not the final target row.
- Formula concept: `number_of_people * unit_price` by month.
- Need proof for monthly number of people and unit price before generating.

### 4.6 NNN paperwork

Source workbook: `raw/Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx`.

Current status: STATUS_REQUIRES_CURRENT_CODE_AUDIT. Target range is known: FORM row `137`, range `F137:Q137`. Remaining blocker: source row/cell/month mapping and output order.

### 4.7 Allocation / 配賦

Source workbook: `raw/FY2027配賦額一覧 (2025.12.29).xlsx`.

Current status: BLOCKED_BY_MISSING_DRIVER_DATA / STATUS_REQUIRES_CURRENT_CODE_AUDIT. Remaining blocker: travel/allocation rows need exact mapping and complete target headcount drivers before output generation.

### 4.8 Manual CSV channels

Manual input files:

- `event_drivers_manual.csv`
- `special_costs_manual.csv`
- `headcount_manual.csv`

Current status: STATUS_REQUIRES_CURRENT_CODE_AUDIT. If header-only/no target rows, no rows should be generated. Manual rows must be schema-valid and provenance `MANUAL_INPUT`.

## 5. Target rows / cell ranges known so far

Rows `200-212` below are historical file-order-v1 target references. The latest complete-v1 acceptance for CC `1412000040` used source-order output rows `168-186`; do not treat those row numbers as completion proof without a fresh output audit.

| Area | Target row/range | Columns | Meaning | Status | Evidence/source |
| ---- | ---------------- | ------- | ------- | ------ | --------------- |
| Facility | rows 200-205 | F:Q months, identity columns | 6 Facility rows | STATUS_REQUIRES_CURRENT_CODE_AUDIT | historical RC/release readiness docs |
| Facility separator | row 206 | all blank | blank separator row | STATUS_REQUIRES_CURRENT_CODE_AUDIT | file-order requirement |
| Admin | rows 207-209 | F:Q months | 3 consumables | STATUS_REQUIRES_CURRENT_CODE_AUDIT | historical RC/release readiness docs |
| Admin separator | row 210 | all blank | blank separator row | STATUS_REQUIRES_CURRENT_CODE_AUDIT | file-order requirement |
| System Cost | row 211 | F:Q months | combined system cost | STATUS_REQUIRES_CURRENT_CODE_AUDIT | historical RC/release readiness docs |
| System separator | row 212 | all blank | blank separator row | STATUS_REQUIRES_CURRENT_CODE_AUDIT | file-order requirement |
| Hiring medical check | row 58 | F58:Q58 | hiring medical check target | BLOCKED_BY_MISSING_DRIVER_DATA | admin allocation/user rule |
| Birthday | row 59 | F59:Q59 | Birthday target row | STATUS_REQUIRES_CURRENT_CODE_AUDIT | visual requirement; row 63 is not final target |
| New employee notebook staff | row 97 | F97:Q97 | new employee notebook/staff | BLOCKED_BY_MISSING_DRIVER_DATA | admin allocation/user rule |
| New employee notebook worker | row 98 | F98:Q98 | new employee notebook/worker | BLOCKED_BY_MISSING_DRIVER_DATA | admin allocation/user rule |
| NNN paperwork | row 137 | F137:Q137 | NNN paperwork target | STATUS_REQUIRES_CURRENT_CODE_AUDIT | user rule; source mapping still open |
| Fixed asset depreciation | row 38 | F38:Q38 | fixed asset depreciation target | STATUS_REQUIRES_CURRENT_CODE_AUDIT | FORM/source trace docs |
| Fixed asset interest | row 42 | F42:Q42 | fixed asset interest target | STATUS_REQUIRES_CURRENT_CODE_AUDIT | FORM/source trace docs |
| Rows 38/40/42 caution | rows 38/40/42 | output-mode dependent | do not patch row 40 directly | NEEDS_OUTPUT_MODE_DECISION | source trace architecture docs |
| Fixed assets detail | no final target yet | F:Q unknown | account `5005026371` details | STATUS_REQUIRES_CURRENT_CODE_AUDIT / BLOCKED_NEEDS_PROVENANCE | historical 42N2C blocker |

## 6. Account code and Cost Center rules

CC means cost center. Current target is `1412000040`.

Account code is an invariant identity key and stronger than description text. Important account codes:

- `5005026371`
- `5005066281`
- `5005066282`
- `5005056281`
- `5005046281`
- `5005116291`
- `5005116292`

Matching priority:

1. cost center
2. `原価センタ`
3. `原価区分`
4. `勘定科目` column `製造` / `一般` / `販売`
5. account code
6. source family
7. month vector F:Q
8. formula/value pattern
9. known aliases
10. description text only as weak helper

Practical account lookup rule:

`Cost Center -> 原価センタ -> 原価区分 -> 勘定科目 column 製造/一般/販売 -> account_code`

False-gap aliases:

- `電気代` = `electricity` = `Điện`
- `水道代` = `water` = `Nước`

## 7. Primary and secondary reference pool

42N2D inventory summary:

| Metric | Count |
|---|---:|
| total files inventoried | 119 |
| secondary files | 82 |
| secondary root | 65 |
| secondary subfolder | 17 |
| files with sheet `内訳ﾘｽﾄ(4～3月)` | 71 |
| secondary containing account `5005026371` | 71 |
| secondary containing CC `1412000040` | 76 |
| read errors | 0 |

Secondary is mostly `generated_output_reference` / `skeleton_reference`. It can unlock skeleton/formula/order. It cannot be called raw source amount proof unless upstream raw provenance is proven.

## 8. Gap accounting and what not to say

- Generated v1 = 141 business rows.
- Primary = 277 business rows.
- Physical row-count gap = 136.
- False gap at least 2: `電気代` and `水道代`.
- Real source-derived gap is not final.
- Never say “company lacks data/source” based only on current gap.
- Current blocker may be parser coverage/file-role/reference-role handling.

## 9. Provenance policy

| Provenance | Meaning | Allowed to output? | How to label |
| ---------- | ------- | ------------------ | ------------ |
| SOURCE_DERIVED | Proven raw workbook/sheet/row/cell/month values | Yes | `SOURCE_DERIVED:<workbook>:<sheet>:<row/cell>` |
| REFERENCE_ASSISTED | Generated from primary/secondary skeleton/formula guide | Yes, with explicit flag and label | `REFERENCE_FILLED_FROM_PRIMARY` or `REFERENCE_ASSISTED_SECONDARY` |
| SKELETON_REFERENCE | Reference-only row/formula/order pattern | No as amount proof; yes as guide | `SKELETON_REFERENCE` |
| MANUAL_INPUT | Schema-valid user/manual CSV row | Yes | `MANUAL_INPUT:<csv>` |
| UNKNOWN_NEEDS_MAPPING | Insufficient evidence | No | `UNKNOWN_NEEDS_MAPPING` |

Reference-assisted output must carry label like `REFERENCE_FILLED_FROM_PRIMARY` or equivalent. Source-derived output must have workbook/sheet/row/cell/month proof. Unknown rows must not be guessed.

## 10. Implementation status dashboard

| Capability | Flag / module | Status | Rows affected | Notes |
| ---------- | ------------- | ------ | ------------- | ----- |
| default export unchanged | default mode | STATUS_REQUIRES_CURRENT_CODE_AUDIT | all default outputs | Re-audit before using as a current completion claim. |
| file-order / complete-v1 spacing | `--mp-saisan-complete-v1` | PARTIAL_PASS_FOR_WRITTEN_BLOCKS; `LAST_VERIFIED_AT_COMMIT=b9ea4e4bed4e4716aeb9c223ed8b0de56e5e68d8` | 6 written source-order blocks in latest target output | All written block gaps had exactly one blank row; seven-block acceptance remains blocked by missing driver data. |
| Facility writer | Facility module | STATUS_REQUIRES_CURRENT_CODE_AUDIT | historical rows 200-205 + 206 blank | Latest audit verified block presence/spacing, not full amount completeness. |
| Admin consumables/new-hire writer | Admin/GA module | PASS_FAIL_CLOSED_FOR_NEW_HIRE; STATUS_REQUIRES_CURRENT_CODE_AUDIT_FOR_REMAINDER | rows 58/97/98 and admin source-order rows | Target CC lacks complete monthly headcount driver data; real new-hire monthly amounts are not certified. |
| System cost writer | System Cost module | STATUS_REQUIRES_CURRENT_CODE_AUDIT | historical row 211 + 212 blank | Combined system cost behavior needs fresh audit against canonical 09.06. |
| Fixed assets detail writer | Fixed Assets module | STATUS_REQUIRES_CURRENT_CODE_AUDIT / BLOCKED_NEEDS_PROVENANCE | account `5005026371` 75 primary rows | Need source row/cell/month mapping before completion claim. |
| Birthday writer | Birthday module | STATUS_REQUIRES_CURRENT_CODE_AUDIT | FORM row 59 target | Needs source mapping and current output proof. |
| NNN writer | NNN paperwork module | STATUS_REQUIRES_CURRENT_CODE_AUDIT | FORM row 137 target | Needs source mapping and current output proof. |
| Allocation writer | Allocation module | BLOCKED_BY_MISSING_DRIVER_DATA / STATUS_REQUIRES_CURRENT_CODE_AUDIT | allocation/travel rows | Needs exact mapping and complete headcount drivers. |
| Column S cost-row rule | output normalizer | PASS; `LAST_VERIFIED_AT_COMMIT=b9ea4e4bed4e4716aeb9c223ed8b0de56e5e68d8` | month-cost rows from row 30 onward | Latest audit found cost+blank S = 0 and no-cost+nonblank S = 0. |
| reference-assisted fill scope | complete-v1/reference assist | PASS_SCOPED_QUARANTINE; `LAST_VERIFIED_AT_COMMIT=b9ea4e4bed4e4716aeb9c223ed8b0de56e5e68d8` | primary reference candidates | Latest audit found 0 reference-filled workbook rows and 130 quarantined unscoped rows. |
| secondary skeleton extraction | analysis workflow | STATUS_REQUIRES_CURRENT_CODE_AUDIT | account `5005026371` candidates | Use as guide only; not raw amount proof. |

## 11. Recommended next phases

1. Extract secondary skeleton patterns for account `5005026371`.
2. Build reference-assisted fill with provenance if skeleton is stable.
3. Implement source parsers only for modules with exact source row/cell/month evidence.
4. Keep default export unchanged and use explicit flags only.

Recommended route remains **HYBRID PATH**: secondary skeleton/formula/order guide + reference-assisted fill with provenance + source parsers only when proven.

## 12. Glossary

- **MP Saisan**: Workflow sinh workbook MP FY2027 per cost center/department.
- **CC**: Cost center, e.g. `1412000040`.
- **account code**: Mã tài khoản kế toán, invariant identity key.
- **原価区分**: Cost category/classification used in MP/accounting context.
- **内訳ﾘｽﾄ(4～3月)**: Sheet detail Apr-Mar, usually with month vector F:Q.
- **FORM**: Template workbook/sheet logic for target rows/cells.
- **source-derived**: Proven from raw source workbook/sheet/row/cell/month values.
- **reference-assisted**: Generated using reference skeleton/formula/order with explicit label.
- **skeleton reference**: Reference structure, not amount proof.
- **primary reference**: Target department expected output workbook.
- **secondary reference**: FY2027 pool from other departments, useful for patterns.
- **file-order mode**: Output follows source-file order, not fixed primary row numbers.
- **blank separator row**: Blank row inserted after one source file/group.
- **provenance**: Evidence label explaining where each row came from.
- **month vector F:Q**: 12 monthly columns from Apr to Mar.
- **製造/一般/販売**: columns in `勘定科目` selected via `原価区分` to determine the correct account code.
- **driver/headcount/unit price**: allocation formula inputs for admin/new employee/event costs.

## 13. Source documents used

Source docs read/checked:

- `docs/knowledge/mp_saisan_business_knowledge_base.md` - USED
- `docs/requirements/cai_tien_nhap_du_lieu_chung.md` - USED
- `docs/audits/phase42n2d_all_saisan_file_role_inventory.md` - USED
- `docs/audits/phase42n2d_all_saisan_file_role_inventory.csv` - USED
- `docs/audits/phase42n2b_invariant_gap_accounting.md` - USED
- `docs/audits/phase42n2b_invariant_gap_accounting.csv` - USED
- `docs/audits/phase42n2a_exact_source_rows_verification.md` - USED
- `docs/audits/phase42n2c_fixed_assets_detail_5005026371_mapping.md` - USED
- `docs/audits/phase42n2c_fixed_assets_detail_5005026371_mapping.csv` - USED
- `docs/audits/phase42n1w_auto_file_order_v1_rc_check.md` - USED
- `docs/audits/phase42n1x_a_file_order_v1_release_readiness.md` - USED
- `docs/audits/phase42n1v_a_file_order_v1_acceptance.md` - MISSING
- `docs/audits/phase42n1t_b_facility_admin_row_count.md` - USED
- `docs/audits/phase42n1p_b_output_row_count_vs_primary.md` - USED
- `docs/audits/phase42n1l_output_mode_architecture.md` - USED
- `docs/audits/phase42n1k_source_trace_rows_38_40_42.md` - USED

Missing source docs were not used; no claims depend uniquely on them.
