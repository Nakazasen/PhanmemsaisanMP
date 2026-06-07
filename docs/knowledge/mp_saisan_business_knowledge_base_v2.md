# MP Saisan Business Knowledge Base v2 - Full Business Specification

## 1. Purpose and current truth

MP Saisan là workflow sinh workbook MP FY2027 theo từng cost center/phòng ban. Target hiện tại là CC `1412000040` / `電気製造技術課`. Sheet chi tiết chính là `内訳ﾘｽﾄ(4～3月)`, thường chứa account, mô tả dòng, và month vector F:Q cho tháng 4 đến tháng 3.

Physical row-count gap `136` là counting fact giữa generated v1 và primary reference, không phải bằng chứng rằng công ty thiếu dữ liệu hoặc thiếu source. Previous "missing data/source" conclusion is NOT final. Chỉ được kết luận source-derived gap sau khi phân loại role file và chứng minh provenance từng dòng. Current best path: **HYBRID PATH**.

## 2. Source hierarchy and trust rules

| Source layer | Path | Role | Trust rule |
| ------------ | ---- | ---- | ---------- |
| Excel canonical requirement | `raw/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026.xlsx` | Source of truth requirement | Thắng derived MD nếu conflict. |
| Visual/OCR requirement | `raw/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026_ảnh.xlsx` | Audit visual/OCR | Dùng để kiểm visual, không thay Excel gốc. |
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

| Source order | File | Role | Current handling | Status |
| -----------: | ---- | ---- | ---------------- | ------ |
| 1 | `施設課　MPFY2027.xlsx` | Facility utilities/building/land | Facility writer rows 200-205 plus separator | IMPLEMENTED_V1 |
| 2 | `固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx` | Fixed assets master/reference | Evidence exists; no one-to-one monthly mapping yet | NEEDS_MAPPING |
| 3 | `システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls` | System cost Q1 | Combined system cost row | IMPLEMENTED_V1 |
| 4 | `システム課金金額(Simulation)_FY2027 July.2026 ~ Dec.2026(Change AMS & PLM price).xls` | System cost Q2-Q3 | Combined system cost row | IMPLEMENTED_V1 |
| 5 | `システム課金金額(Simulation)_FY2027 Jan.2027 ~ March.2027(Change SAP price).xls` | System cost Q4 | Combined system cost row | IMPLEMENTED_V1 |
| 6 | `総務課 FY2027 MP 振替予定.xlsx` | Admin/GA consumables/allocation | Consumables implemented; allocation needs provenance | PARTIAL |
| 7 | `Sinh nhật MP FY2027.xlsx` | Birthday | Not implemented in v1 | UNHANDLED |
| 8 | `FY2027配賦額一覧 (2025.12.29).xlsx` | Allocation/travel | Needs exact mapping | NEEDS_MAPPING |
| 9 | `Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx` | NNN paperwork | Not implemented in v1 | UNHANDLED |
| 10 | `event_drivers_manual.csv` | Manual event input | Channel exists | MANUAL_INPUT_CHANNEL |
| 11 | `special_costs_manual.csv` | Manual special costs | Channel exists | MANUAL_INPUT_CHANNEL |
| 12 | `headcount_manual.csv` | Manual headcount | Channel exists | MANUAL_INPUT_CHANNEL |

## 4. Module detail matrix

| Module | Business purpose | Source workbook/sheet | Target/output rows or range | Main account/CC rules | Formula/month rule | Current implementation status | Remaining blocker |
| ------ | ---------------- | --------------------- | --------------------------- | --------------------- | ------------------ | ----------------------------- | ----------------- |
| Facility / 施設課 | Facility cost: building, land, utilities | `raw/施設課　MPFY2027.xlsx`; sheets include depreciation, interest, electric/water | rows 200-205; row 206 blank | Target CC `1412000040`; aliases `電気代`/`水道代` | `ROUND(source_value*$B$2,0)` for 12 months where VND conversion is needed; electricity/water currency handling must preserve source currency/conversion policy | IMPLEMENTED_V1 for 6 rows | Facility details outside rows 200-205 need separate mapping. |
| Admin / GA consumables | Consumables, allocation, event/month, new employee, hiring medical check | `raw/総務課 FY2027 MP 振替予定.xlsx` | rows 207-209 implemented; known FORM targets include row 58, 97, 98 for some admin/new employee items | CC/account per mapped consumable/allocation rows | driver/headcount/unit price/month allocation; 12-month costs and event/month costs require explicit driver | IMPLEMENTED_V1 for 3 consumables; other admin allocation PARTIAL | Other admin/allocation rows need row-level provenance. |
| System Cost | IT/system charge across three simulation periods | Three `システム課金金額(Simulation)_FY2027...xls` files | row 211; row 212 blank | Combined system cost for target CC | Month values come from three source files by period; combined row only under explicit flag | IMPLEMENTED_V1 behind explicit flag | Default unchanged; detail splitting only if requirement proves it. |
| Fixed Assets / 固定資産 | Fixed asset depreciation/interest/detail expense | `raw/固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx` | depreciation row 38 F38:Q38; interest row 42 F42:Q42; no final source-derived target rows yet for detail group | Account `5005026371` has 75 primary rows | Need exact source workbook/sheet/row/cell + Apr-Mar monthly values | NOT_IMPLEMENTED_SOURCE_DERIVED | Master/reference and CC evidence exist, but not enough row/cell/month mapping. Do not code guess. |
| Birthday / Sinh nhật | Birthday benefit/cost | `raw/Sinh nhật MP FY2027.xlsx` | FORM row 59, F59:Q59; row 63 is intermediate/source area, not final target | Target row/account needs confirmation | `number_of_people * unit_price` by month after source row is confirmed | NOT_IMPLEMENTED_V1 | Resolve source row and Apr-Mar values/formula mapping. |
| NNN paperwork | Foreigner paperwork cost estimate | `raw/Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx` | FORM row 137, F137:Q137 | Needs CC/account proof | Need source row/cell/month mapping | NOT_IMPLEMENTED_V1 | Source mapping remains open, but target range is known. |
| Allocation / 配賦 | Allocation/travel/shared costs | `raw/FY2027配賦額一覧 (2025.12.29).xlsx` | no safe final rows yet | Account/CC invariant matching required | Exact F:Q mapping required | PARTIAL / NEEDS_MAPPING | Travel/allocation rows need exact mapping. |
| Manual CSV channels | Structured manual input | `event_drivers_manual.csv`, `special_costs_manual.csv`, `headcount_manual.csv` | generated only from schema-valid rows | Manual rows must include target identity fields | Values from CSV; provenance `MANUAL_INPUT` | HANDLED_MANUAL_CSV channel exists | Header-only/no target rows must not generate guessed rows. |
| Primary/secondary reference | Skeleton/formula/order guide | primary and secondary output references | reference-assisted only | Not source-derived without upstream provenance | Can preserve formulas/order | READY_FOR_MAPPING | Needs explicit provenance label if used. |

### 4.1 Facility / 施設課

Known implemented rows: Facility rows `200-205`, blank row `206`.

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

Status: IMPLEMENTED_V1 for these 6 rows. Remaining Facility details outside this block need separate source mapping.

### 4.2 Admin / GA consumables

Source workbook: `raw/総務課 FY2027 MP 振替予定.xlsx`.

Known generated rows: Admin rows `207-209`, blank row `210`.

Items:

- `toilet_paper`
- `hand_soap`
- `alcohol_disinfectant`

Status: IMPLEMENTED_V1 for 3 rows. If any sample values are `UNKNOWN`, keep that uncertainty visible; do not hide or guess. Remaining admin/allocation rows need row-level provenance.

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

Known generated row: row `211`, item_id `system_cost_combined`, blank row `212`.

Status: IMPLEMENTED_V1 as combined system cost row. It is explicit-flag only; default export remains unchanged.

System Cost formula policy:

- Use the three simulation files by period: Apr-Jun, Jul-Dec, Jan-Mar.
- Month F:Q must be filled from the matching source period only.
- The v1 behavior is a combined `system_cost_combined` row, not a detailed split.
- Do not infer missing months from neighboring months unless source workbook formula proves it.
- Keep behavior behind explicit flag; default export unchanged.

### 4.4 Fixed Assets / 固定資産

Source workbook: `raw/固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx`.

Known account/group: `5005026371` has 75 primary rows in gap matrix. The fixed asset workbook has master/reference and CC evidence, but not enough one-to-one row/cell/month values for source-derived export.

Current status: NOT_IMPLEMENTED_SOURCE_DERIVED.

Remaining blocker: need workbook/sheet/row/cell + account + CC + Apr-Mar monthly values. Do not code guess. Secondary may be used as skeleton/reference guide, not raw amount proof.

Known fixed-asset FORM targets:

- Fixed asset depreciation: row `38`, range `F38:Q38`.
- Fixed asset interest: row `42`, range `F42:Q42`.
- Rows 38/42 are known target ranges, but source-derived generation still requires raw fixed-asset source proof.

### 4.5 Birthday / Sinh nhật

Source workbook: `raw/Sinh nhật MP FY2027.xlsx`.

Requirement status: Birthday/Tiền sinh nhật image indicates FORM target row `59`, F59:Q59. Old note about row `63` is intermediate/source area, not target row.

Current status: UNHANDLED_SOURCE_ORDER_FILE / NOT_IMPLEMENTED_V1. Remaining blocker: source row and Apr-Mar values/formula mapping must be confirmed.

Birthday formula policy:

- Known target: FORM row `59`, range `F59:Q59`.
- Row `63` is intermediate/source area, not the final target row.
- Formula concept: `number_of_people * unit_price` by month.
- Need proof for monthly number of people and unit price before generating.

### 4.6 NNN paperwork

Source workbook: `raw/Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx`.

Current status: UNHANDLED_SOURCE_ORDER_FILE / NOT_IMPLEMENTED_V1. Target range is known: FORM row `137`, range `F137:Q137`. Remaining blocker: source row/cell/month mapping and output order.

### 4.7 Allocation / 配賦

Source workbook: `raw/FY2027配賦額一覧 (2025.12.29).xlsx`.

Current status: PARTIAL / NEEDS_MAPPING. Remaining blocker: travel/allocation rows need exact mapping before output generation.

### 4.8 Manual CSV channels

Manual input files:

- `event_drivers_manual.csv`
- `special_costs_manual.csv`
- `headcount_manual.csv`

Current status: HANDLED_MANUAL_CSV channel exists. If header-only/no target rows, no rows should be generated. Manual rows must be schema-valid and provenance `MANUAL_INPUT`.

## 5. Target rows / cell ranges known so far

| Area | Target row/range | Columns | Meaning | Status | Evidence/source |
| ---- | ---------------- | ------- | ------- | ------ | --------------- |
| Facility | rows 200-205 | F:Q months, identity columns | 6 Facility rows | IMPLEMENTED_V1 | RC/release readiness docs |
| Facility separator | row 206 | all blank | blank separator row | IMPLEMENTED_V1 | file-order requirement |
| Admin | rows 207-209 | F:Q months | 3 consumables | IMPLEMENTED_V1 | RC/release readiness docs |
| Admin separator | row 210 | all blank | blank separator row | IMPLEMENTED_V1 | file-order requirement |
| System Cost | row 211 | F:Q months | combined system cost | IMPLEMENTED_V1 | RC/release readiness docs |
| System separator | row 212 | all blank | blank separator row | IMPLEMENTED_V1 | file-order requirement |
| Hiring medical check | row 58 | F58:Q58 | hiring medical check target | NEEDS_MAPPING | admin allocation/user rule |
| Birthday | row 59 | F59:Q59 | Birthday target row | NEEDS_MAPPING | visual requirement; row 63 is not final target |
| New employee notebook staff | row 97 | F97:Q97 | new employee notebook/staff | NEEDS_MAPPING | admin allocation/user rule |
| New employee notebook worker | row 98 | F98:Q98 | new employee notebook/worker | NEEDS_MAPPING | admin allocation/user rule |
| NNN paperwork | row 137 | F137:Q137 | NNN paperwork target | NEEDS_MAPPING | user rule; source mapping still open |
| Fixed asset depreciation | row 38 | F38:Q38 | fixed asset depreciation target | NEEDS_MAPPING | FORM/source trace docs |
| Fixed asset interest | row 42 | F42:Q42 | fixed asset interest target | NEEDS_MAPPING | FORM/source trace docs |
| Rows 38/40/42 caution | rows 38/40/42 | output-mode dependent | do not patch row 40 directly | NEEDS_OUTPUT_MODE_DECISION | source trace architecture docs |
| Fixed assets detail | no final target yet | F:Q unknown | account `5005026371` details | BLOCKED_NEEDS_PROVENANCE | 42N2C blocker |

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
| default export unchanged | default mode | DONE_V1 | all default outputs | No new rows without explicit flag. |
| file-order export v1 | `--file-order-export-v1` | DONE_V1 | Facility/Admin/System v1 rows | Master flag. |
| Facility writer | Facility module | DONE_V1 | rows 200-205 + 206 blank | Handles six Facility rows. |
| Admin consumables writer | Admin/GA module | DONE_V1 | rows 207-209 + 210 blank | Three consumables. |
| System cost writer | System Cost module | DONE_V1 | row 211 + 212 blank | Combined system cost. |
| Fixed assets detail writer | Fixed Assets module | BLOCKED_NEEDS_PROVENANCE | account `5005026371` 75 primary rows | Need source row/cell/month mapping. |
| Birthday writer | Birthday module | NOT_STARTED | FORM row 59 target | Needs source mapping. |
| NNN writer | NNN paperwork module | NOT_STARTED | unknown target | Needs source mapping. |
| Allocation writer | Allocation module | READY_FOR_MAPPING | allocation/travel rows | Needs exact mapping. |
| reference-assisted fill v2 | explicit future flag | RECOMMENDED_NEXT | physical gap candidates | Must label provenance. |
| secondary skeleton extraction | analysis workflow | READY_FOR_MAPPING | account `5005026371` candidates | Use as guide only. |

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
