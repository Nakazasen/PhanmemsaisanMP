# Phase 42N3K Fixed Asset CC Full Data Audit

Classification: `PASS_PHASE_42N3K_FIXED_ASSET_CC_FULL_DATA_AUDIT`

## Scope

Read-only audit for the 09.06.2026 requirement update. This audit did not use the legacy `04.06.2026_ảnh.xlsx` workbook as source of truth.

Current requirement source:

- `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026.xlsx`
- `raw/requirements/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026.xlsx`

Fixed-asset source inspected:

- `raw/固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx`
- Sheet: `2025.11`

## Requirement Interpretation

The 09.06.2026 image requirement for `Chi phí tài sản cố định` means:

- Filter by the Cost Center that bears the fixed-asset cost.
- Process each asset identity before aggregation.
- Use Asset No / asset text where available for traceability.
- Use `Last Depreciation Month` to decide when depreciation and interest stop.
- Depreciation:
  - before last depreciation month: normal monthly depreciation.
  - at last depreciation month: use `Last Month Depr` if available.
  - after last depreciation month: no depreciation.
- Interest:
  - April uses April interest.
  - May onward uses May-onward interest.
  - after last depreciation month: no interest.
- Output should convert USD source values with FORM `$B$2`, e.g. `ROUND(source_usd*$B$2,0)`.
- Audit and comparison must be identity-aligned by Cost Center, asset identity, last depreciation month, and cost type; not by fixed physical row alone.

## Code Paths Inspected

- `src/parsers/fixed_assets.py`
- `src/engine/hub_builder.py`
- `src/engine/output_mode.py`
- `src/engine/complete_v1_source_order_writer.py`
- `src/engine/source_order_output.py`
- `scripts/run_e2e.py`
- `src/db/loader.py`
- `src/utils/excel_helpers.py`
- `src/db/schema.py`

## Current Implementation Summary

`scripts/run_e2e.py` calls `parse_fixed_assets(conn, source_dir=source_dir)` during the normal pipeline.

`src/parsers/fixed_assets.py` resolves the fixed-asset workbook through manifest category `fixed_assets` or by filename containing `Fixed_Assets_Information`.

The parser reads sheet `2025.11` and currently uses fixed column positions:

- H / index 7: `管理責任原価センタ / Control Cost Center`
- L / index 11: `November 2025 Depreciation`
- P / index 15: `Last Depreciation Month`
- Q / index 16: `Last Month Depr`
- V / index 21: `Interest in April 2026`
- W / index 22: `Interest from May 2026`

For each asset row, it inserts:

- `fixed_assets_depr|{asset_no}|{asset_text}`
- `fixed_assets_interest|{asset_no}|{asset_text}`

The parser stores both `amount_usd` and `amount_vnd`, but inserts `account_code=0` and no `form_row`.

## Source Workbook Evidence

Read-only inspection of `raw/固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx` showed:

- Sheet `2025.11`
- Header row 4 contains both:
  - H: `Control Cost Center`
  - J: `Depreciation Cost Center`
- 1266 source rows have a Control Cost Center.
- 1266 source rows have a Depreciation Cost Center.
- Control Cost Center has 30 distinct CCs.
- Depreciation Cost Center has 27 distinct CCs.
- At least 417 asset rows have `Last Depreciation Month` inside FY2027.

Important mismatch:

- Current parser uses H / Control Cost Center.
- The requirement wording says `code phòng chịu chi phí` / Cost Center bearing the cost.
- In this workbook, the stronger business match for cost-bearing CC appears to be J / Depreciation Cost Center.

Audit-only comparison found large H-to-J movement risk:

- If using J instead of H, about 10,108 generated asset-period records would move to a different CC.
- Examples:
  - `1412000022 -> 1412000004`: 2,314 records
  - `1412000084 -> 1412000103`: 1,376 records
  - `1412000022 -> 1412000005`: 1,070 records
  - `1412000016 -> 1412000005`: 944 records

This is the highest-probability reason users see fixed-asset data not running correctly for all expected CCs.

## Current CC Filtering Behavior

Parser-level:

- Uses `helpers.extract_cc_code(row[7])`, i.e. source column H / Control Cost Center.
- Does not validate the selected CC against `dim_cost_centers`.
- Does not preserve both control CC and depreciation CC as separate identity fields.

Export-level:

- `HubBuilder.export_to_template()` refuses to export a CC if it has no `fact_input_data` rows at all.
- Batch export in `scripts/run_e2e.py` selects CCs with:
  - `SELECT DISTINCT cc_code FROM fact_input_data WHERE account_code > 0`
- Fixed-asset facts are inserted with `account_code=0`.
- Therefore fixed-asset facts alone cannot make a CC appear in batch export.

## Missing CC/Data Risk

There are two separate risks:

1. Wrong CC identity:
   - Current code filters by Control Cost Center H.
   - Requirement likely wants Depreciation Cost Center J.
   - Assets can have H != J, causing data to appear under the managing CC instead of the cost-bearing CC.

2. Batch export discovery excludes fixed-asset-only CCs:
   - Current fixed-asset facts have `account_code=0`.
   - Batch export discovers only CCs with `account_code > 0`.
   - A CC with only fixed-asset rows can be parsed but not exported in batch mode.

The current local `mp2027.db` dirty runtime file showed zero `fixed_assets` rows, but an in-memory read-only parse against `raw` produced 16,448 fixed-asset facts across 29 CCs. Treat the local DB as stale/runtime state, not source truth.

## Last Depreciation Month Support

Supported in code:

- `expand_depreciation_schedule(monthly_depr, last_month, last_month_depr, fy_months)`
- `expand_interest_schedule(apr_interest, may_interest, last_month, fy_months)`

Current behavior:

- Depreciation before last month uses monthly depreciation.
- Depreciation at last month uses `Last Month Depr` if positive, else monthly depreciation.
- Depreciation after last month is zero.
- Interest after last month is zero.
- April interest uses column V.
- May onward interest uses column W.

This matches the requirement shape, but the parser does not yet expose a structured audit trail for `last_month` or asset identity beyond the description string.

## Depreciation Cost Handling

Supported.

Parser emits per-asset monthly USD and VND records with description prefix `fixed_assets_depr|`.

Writer behavior:

- Legacy staging writes fixed-asset depreciation to row 38 using `amount_usd`.
- The visible formula is written as `=ROUND(<usd>*$B$2,0)`.
- Complete-v1 source-order writer then treats row 38 as staging evidence and moves it into the fixed-assets source block, clearing legacy fixed placement rows.

## Interest Cost Handling

Supported.

Parser emits per-asset monthly USD and VND records with description prefix `fixed_assets_interest|`.

Writer behavior:

- Legacy staging writes fixed-asset interest to row 42 using `amount_usd`.
- The visible formula is written as `=ROUND(<usd>*$B$2,0)`.
- Complete-v1 source-order writer then moves it into the fixed-assets source block.

## Exchange Rate Source

FORM `$B$2` is supported at output formula level.

Evidence:

- `src/utils/excel_helpers.py` reads FORM hub sheet `B2`.
- `src/db/loader.py` stores `exchange_rate_usd_vnd` from FORM B2 into `sys_params`.
- `src/parsers/fixed_assets.py` also uses `sys_params` to precompute `amount_vnd`.
- `src/engine/hub_builder.py` writes formulas with `$B$2` through `_write_fx_formula_series`.

The final workbook formula is the stronger requirement match because it preserves the FORM-rate reference.

## Output Target/Range

Current legacy staging:

- Depreciation: row 38
- Interest: row 42
- Month columns: F:Q

Current complete-v1 visible placement:

- `complete_v1_source_order_writer.py` collects staged rows 38 and 42 for source file `固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx`.
- It clears legacy rows 38 and 42.
- It writes fixed-asset rows into the source-file-order block after Facility and before System Cost.
- It inserts blank separator rows between source file blocks.

So the final complete-v1 path is source-order visible placement, but still depends on legacy rows 38 and 42 as staging rows.

## Fixed-Row vs Identity-Aligned Assessment

Partially identity-aligned, but not sufficient.

Identity-aligned parts:

- Per-asset source rows are parsed before aggregation.
- Asset No and asset text are included in the description.
- Last depreciation month affects per-asset schedules before monthly aggregation.
- Depreciation and interest are separated by description prefix.

Fixed-row/weak parts:

- Output still stages fixed-assets on rows 38 and 42 before source-order rewrite.
- There are no structured columns for asset number, source row, control CC, depreciation CC, last depreciation month, or cost type.
- The parser currently uses Control Cost Center H, not Depreciation Cost Center J.
- Batch export CC discovery ignores fixed-asset-only CCs because `account_code=0`.

## Proposed Implementation Plan

1. Update fixed-asset parser CC identity:
   - Read both H `control_cost_center` and J `depreciation_cost_center`.
   - Use J as `cc_code` for cost-bearing output if confirmed by requirement.
   - Preserve H in description/audit metadata, e.g. `control_cc=...`.

2. Add explicit asset metadata:
   - Include `asset_no`, `asset_text`, `source_row`, `last_depreciation_month`, `cost_type=depreciation|interest`.
   - Keep existing description prefix compatibility for writer matching.

3. Fix batch export CC discovery:
   - Include CCs with `source='fixed_assets'` even when `account_code=0`, or assign resolved fixed-asset account codes during parsing.
   - Safer first change: in batch export, use all distinct `fact_input_data.cc_code`, not only `account_code > 0`, then rely on `HubBuilder` to skip empty workbooks.

4. Preserve formula policy:
   - Continue writing `=ROUND(<usd>*$B$2,0)` in output.
   - Do not replace with hard-coded VND unless formula length/FORM constraints require fallback.

5. Add targeted tests:
   - H vs J test where control CC differs from depreciation CC.
   - Last depreciation month inside FY stops depreciation/interest after the cutoff.
   - Last month depreciation uses `Last Month Depr`.
   - Batch export includes fixed-asset-only CC.
   - Complete-v1 still places fixed-assets in canonical source-file order and not legacy visible rows 38/42.

## Risks/Unknowns

- The requirement phrase `code phòng chịu chi phí` must be confirmed as J / Depreciation Cost Center, not H / Control Cost Center. Workbook headers strongly suggest J, but this phase does not change code.
- Current parser uses fixed column indexes. If the 09.06.2026 source workbook changes column order, parser can silently misread data. Header-based detection should replace fixed indexes.
- Local dirty `mp2027.db` currently does not reflect a fresh fixed-asset parse. Do not use it as final business evidence.
- Complete-v1 source-order output still depends on legacy staging rows. This is acceptable short-term but should be replaced by direct source-order row construction later.

## Checks

- Code was not modified.
- No raw/generated/runtime files were modified.
- No commit or push was performed in this audit phase.
