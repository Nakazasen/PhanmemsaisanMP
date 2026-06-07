# Phase 42N1L - Output Mode Architecture

## Files/reports inspected

- `docs/audits/phase42r0_canonical_requirement_reconciliation.md`
- `docs/audits/phase42n1i_strict_diff_classification.md`
- `docs/audits/phase42n1j_form_template_check_rows_38_42.md`
- `docs/audits/phase42n1k_source_trace_rows_38_40_42.md`
- `docs/requirements/cai_tien_nhap_du_lieu_chung.md`
- `src/engine/hub_builder.py`
- `src/utils/source_manifest.py`
- `src/db/schema.py`
- `src/parsers/facility.py`
- `src/parsers/fixed_assets.py`
- `src/parsers/it_sim.py`
- `src/parsers/ga.py`
- `src/parsers/birthday.py`
- `src/parsers/nnn_paperwork.py`

## Business confirmation used

User/business confirmed:

- `chạy theo thứ tự file là được`
- `không nhất thiết phải vào row nào cả`
- `chạy xong 1 file thì cách 1 dòng ra`

Requirement image context:

- A179: `Điền dữ liệu theo thứ tự dưới đây`
- A180/B180: `Ngoài ra, thứ tự các chi phí của từng file thì ghi trong từng sheet bên cạnh`
- File order:
  1. `施設課　MPFY2027.xlsx`
  2. `固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx`
  3. `システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls`
  4. `総務課 FY2027 MP 振替予定.xlsx`
  5. `Sinh nhật MP FY2027.xlsx`
  6. `FY2027配賦額一覧 (2025.12.29).xlsx`
  7. `Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx`
- Facility has linked note `6 chi phí`.
- System Cost has linked note `gộp thành 1 dòng chi phí`.

## Current implementation findings

### Export/writer architecture

Primary writer is `src/engine/hub_builder.py`.

Current writer flow:

1. Copy template workbook to output.
2. Resolve hub sheet.
3. Write cost center row 5.
4. Call `_write_fixed_rows()`.
5. Clear append area from row 200 onward.
6. Append rows from `_load_append_rows()` in a generic append area.

The implementation is therefore currently **mixed**, but not yet the requested
file-order architecture:

- Fixed FORM rows are heavily managed for rows 38-152.
- Generic dynamic append exists only from row 200 onward.
- Append rows are ordered by account/description/source, not by source-file order.
- Facility, fixed assets, IT simulation, and GA unit price are excluded from generic append.
- No blank-row separator between source-file groups is currently emitted.

### Source manifest architecture

`src/utils/source_manifest.py` already supports:

- `source_file_order.xlsx`
- `source_file_order.csv`
- categories for facility, fixed_assets, it_simulation, ga, birthday,
  allocation_rules, nnn_paperwork
- ordered manifest read and fallback detection

However, `hub_builder.py` does not currently use this manifest to order output
rows in the hub detail sheet.

### Database architecture

`src/db/schema.py` includes `fact_input_data.form_row`.

Current writer uses `form_row` only through explicit fixed-form row handling:

- `_load_explicit_form_rows()` reads rows with `form_row IS NOT NULL`.
- `_write_explicit_form_rows()` writes those rows directly to their form row.
- `_load_append_rows()` only appends rows where `form_row IS NULL`.

There is no canonical `output_mode`, `source_order`, `group_order`, or
`blank_after_group` field yet.

## Hardcoded row findings

| Row or range | Location | Meaning / use | Mode implied |
|---|---|---|---|
| `APPEND_TEMPLATE_ROW = 29` | `hub_builder.py` | Style source for append rows | Dynamic append style |
| `APPEND_START_ROW = 200` | `hub_builder.py` | Generic append starts far below FORM rows | Append-only dynamic |
| `MONTHLY_HEADCOUNT_FIXED_ROWS = (46, 48, 49, 51)` | `hub_builder.py` | Headcount-linked admin rows | Fixed row |
| `FIXED_ALLOCATION_ROW_MATCHERS` includes rows 54, 57, 58, 59, 63, 66, 67, 69, 70, 71, 79, 80, 81, 82, 88, 89, 90, 97, 98 | `hub_builder.py` | Allocation descriptions mapped to fixed FORM rows | Fixed row |
| `MANAGED_FIXED_ROWS = 38:90, 93:109, 111:152` | `hub_builder.py` | Clears managed FORM rows | Fixed row |
| `fixed_account_codes` includes 36, 37, 38, 40, 41, 42, 44, 45, 46, 48, 49, 51, 57, 58, 59, 97, 98, 137 | `hub_builder.py` | Hardcoded account codes by row | Fixed row |
| 36/37 | `_write_fixed_rows()` | Facility depreciation building/land | Fixed row |
| 38 | `_write_fixed_rows()` | Fixed assets depreciation | Fixed row |
| 40/41 | `_write_fixed_rows()` | Facility interest building/land | Fixed row |
| 42 | `_write_fixed_rows()` | Fixed assets interest | Fixed row |
| 44/45 | `_write_fixed_rows()` | Facility electric/water | Fixed row |
| 51 | `_write_fixed_rows()` | Cleaning/admin headcount formula | Fixed row |
| 137 | `_write_fixed_rows()` and explicit form row support | NNN compatible row | Fixed row / explicit row |

## Current implementation mode

| Group | Current module/file | Current row behavior | Hardcoded rows found | Style preservation | Blank row support | Risk |
|---|---|---|---|---|---|---|
| Facility | `src/parsers/facility.py`, `hub_builder.py` | Fixed-row | 36, 37, 40, 41, 44, 45 | Fixed rows keep template style; append style not used | No | High: conflicts with file-order 6-cost confirmation; row 40 must not be patched in isolation. |
| Fixed Assets | `src/parsers/fixed_assets.py`, `hub_builder.py` | Fixed-row | 38, 42 | Fixed rows keep template style | No | High: old row 38/42 requirement conflicts with new file-order confirmation. |
| System Cost | `src/parsers/it_sim.py`, `hub_builder.py` | Dynamic locator within template, but fixed single target row | `_find_it_system_total_row()` locates target row by account/text; not source-file append | Existing row style | No | Medium: already single-row concept exists, but not placed by file order. |
| Admin allocation | `src/parsers/ga.py`, `hub_builder.py` | Mixed fixed-row + append | 46, 48, 49, 51 and many allocation matcher rows | Fixed rows preserve template; append rows copy row 29 | No | High: file-order priority not implemented; source-file ordering ignored. |
| Birthday | `src/parsers/birthday.py`, `hub_builder.py` | Fixed-row or append depending description matching | 59 and possible row 63 conflict noted in audits | Fixed rows or append row 29 | No | Medium: file-order can reduce row dependence but compatibility must be preserved. |
| NNN | `src/parsers/nnn_paperwork.py`, `hub_builder.py` | Row 137 compatibility / explicit row capable | 137 | Fixed row or explicit row | No | Medium: F137:Q137 requirement conflicts with file-order list. |
| Generic append | `hub_builder.py` | Dynamic append from row 200 | None per group, but excludes facility/fixed_assets/it_sim/ga_unit_price | `_copy_row_style()` from row 29 | No | Medium: append exists but order is account/description/source, not manifest order. |

## Canonical output mode decision proposal

| Group | Proposed mode | Placement | Notes |
|---|---|---|---|
| Facility | `FILE_ORDER_GROUP` | First source-file group; after group, leave one blank row | Emit `6 chi phí` in source-defined order. Do not patch row 40 directly. |
| Fixed Assets | `MIXED_TRANSITION` / `FILE_ORDER_GROUP_PENDING` | Second source-file group, pending transition decision | Requirement/audits mention row 38/42, but new confirmation says file-order is acceptable. Keep row compatibility until migration is explicit. |
| System Cost | `FILE_ORDER_SINGLE_ROW` | Third source-file group; one row only; blank row after group | Align with `gộp thành 1 dòng chi phí`. Current single-row aggregator can be reused after output placement abstraction. |
| Admin allocation | `FILE_ORDER_GROUP` | Fourth source-file group; blank row after group | High priority; must follow source sheet order rather than fixed row matchers where no fixed-row requirement is confirmed. |
| Birthday | `FILE_ORDER_OR_ROW59_COMPAT` | Fifth source-file group or legacy row 59 compatibility | Keep row 59/63 conflict note. File-order may reduce row dependence but do not remove compatibility yet. |
| Allocation rules | `FILE_ORDER_GROUP` | Sixth source-file group; blank row after group | Existing allocation matcher rows should transition carefully. |
| NNN | `ROW137_COMPAT_OR_FILE_ORDER_PENDING` | Seventh source-file group or row 137 compatibility | Requirement has F137:Q137 but NNN is also in file-order list. Needs explicit compatibility decision. |

## Recommended architecture direction

Introduce an output-mode abstraction before changing business calculations.

Suggested concepts:

- `OutputGroup`: category, source filename/order, mode, separator policy.
- `OutputRow`: account, description, monthly series/formulas, source category,
  optional legacy `form_row`.
- `OutputMode` enum:
  - `FIXED_FORM_ROW`
  - `FILE_ORDER_GROUP`
  - `FILE_ORDER_SINGLE_ROW`
  - `MIXED_TRANSITION`
- `StyleSource`: fixed row style vs append template style vs copied group style.
- `BlankSeparatorPolicy`: one blank row after each completed source file group.

The first implementation should be structural only: produce the same data rows
through a planned row-placement layer, without changing parser calculations.

## Migration strategy

### Phase 1 - Output mode abstraction, no business logic change

- Add a row-placement layer that can place rows either by fixed row or file-order group.
- Read file order from `source_manifest` / requirement-derived manifest.
- Add blank-row separator support behind a feature flag or explicit mode.
- Keep existing fixed-row behavior as default.
- Gate with unit tests for row planning only.

### Phase 2 - Facility file-order 6 costs

- Emit Facility as first file-order group.
- Include 6 costs in source-defined order.
- Insert one blank row after Facility group.
- Do not patch row 40 in fixed-row mode; change only file-order placement.

### Phase 3 - System Cost file-order single row

- Reuse current single-row aggregation logic.
- Place the row in the System Cost file-order group.
- Validate `gộp thành 1 dòng chi phí`.

### Phase 4 - Admin allocation file-order

- Convert GA/admin allocation rows to file-order group where no fixed-row lock exists.
- Preserve formula construction and unit-price logic.
- Add blank-row separator after the group.

### Phase 5 - Birthday/NNN compatibility decision

- Decide whether Birthday stays row 59 compatible or moves fully to file-order.
- Decide whether NNN keeps row 137 compatibility or moves to file-order.
- Preserve compatibility until explicitly decided.

### Phase 6 - Fixed Assets transition

- Decide whether rows 38/42 remain fixed rows or become Fixed Assets file-order group.
- If transitioning, preserve old row tests separately from new file-order tests.
- Avoid using primary same-row diffs as acceptance criteria.

## Tests needed

- Test source file order loaded from requirement/manifest.
- Test one blank row after each source-file group.
- Test Facility emits 6 costs in source-defined order.
- Test System Cost emits one combined row.
- Test fixed-row legacy compatibility if fixed rows are kept.
- Test style copied from template row/block for dynamic file-order rows.
- Test fixed rows retain original FORM styles.
- Test no primary same-row/fixed-row assertion for file-order groups.
- Test generated row planner can output both fixed-row and file-order plans.
- Test source groups excluded from append today are handled explicitly by the planner.

## Risks

- Large diff risk if fixed-row writer is replaced without a planner phase.
- Formula/style regression risk when moving rows out of existing FORM positions.
- Primary-reference compare must be adapted to identity/file-order mode, not row parity.
- User-facing layout may change substantially when file-order mode is enabled.
- Existing `form_row` data may conflict with file-order placement if both are active.
- Source manifest order exists but is not currently used for output row order.

## Explicit do not do yet

- Do not patch row 40 directly.
- Do not force all groups to fixed rows.
- Do not remove row 38/42/59/137 compatibility until transition is decided.
- Do not change parser/business calculations in this phase.
- Do not package.
- Do not commit unless report-only commit is requested.
