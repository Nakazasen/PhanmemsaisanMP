# Phase 42N1K - Source workbook trace for rows 38, 40, 42

## Files inspected

- `docs/audits/phase42r0_canonical_requirement_reconciliation.md`
- `docs/audits/phase42n1i_strict_diff_classification.md`
- `docs/audits/phase42n1j_form_template_check_rows_38_42.md`
- `dist/phase42n1g2r2_identity_disambiguation/strict_compare/MP2027_primary_reference_compare.json`
- `raw/蝗ｺ螳夊ｳ・肇諠・ｱ_Fixed_Assets_Information_2025.11 - Nov.xlsx`
- `raw/譁ｽ險ｭ隱ｲ縲MPFY2027.xlsx`
- `dist/phase42n1b3_row5_template_parity_20260607_065031/generated/MP_CC_1412000040.xlsx`
- `reference_outputs/primary/16.KDTVN 髮ｻ豌苓｣ｽ騾謚陦楢ｪｲ_MP FY2027_蜷・ｺ亥ｮ・Ver01).xlsx`

## Source workbook paths found

- Fixed Assets: `raw/蝗ｺ螳夊ｳ・肇諠・ｱ_Fixed_Assets_Information_2025.11 - Nov.xlsx`
- Facility: `raw/譁ｽ險ｭ隱ｲ縲MPFY2027.xlsx`

## Sheet/header detection summary

### Fixed Assets workbook

Sheets:

- `2025.11`
- `Fixed assets list`
- `Sheet1`
- `KDTVN - useful life`
- `Useful life`
- `Calculate Depr&Interest FA`
- `Planned Depreciation`

Relevant headers:

- `2025.11` row 4 includes Asset No, Text, Control Cost Center,
  Depreciation Cost Center, November 2025 Depreciation,
  December 2025 Interest, Acquisition Amount, Asset Class,
  Last Depreciation Month, Last Month Depr, Allocation Info, WBS.
- `Planned Depreciation` row 4 includes Asset Number, Description,
  Class, Useful life, Control Cost Center, Depreciation Cost Center,
  Expected Last Depreciation Month, Estimated Interest Amount,
  Depreciation Simulation Amount.

Cost center `1412000040` was found in Fixed Assets source:

- `2025.11`: 2 rows with Depreciation Cost Center `1412000040`.
- `Fixed assets list`: 180 hits for control/depreciation cost center.
- `Sheet1`: 172 hits for control/depreciation cost center.
- `Planned Depreciation`: 172 hits for control/depreciation cost center.

### Facility workbook

Sheets:

- `貂帑ｾ｡蜆溷唆雋ｻ・・epreciation・荏
- `蝗ｺ螳夊ｳ・肇驥大茜・・nterest・荏
- `豌ｴ驕灘・辭ｱ雋ｻ・・lectric & Water・荏
- `B&L`
- `E&W`

Relevant headers:

- `B&L` row 6 includes Cost Center, Cost Center name, Japanese name,
  monthly ratio columns, building allocation, land allocation,
  building interest, and land interest.
- `貂帑ｾ｡蜆溷唆雋ｻ・・epreciation・荏 rows 65/66 expose building and land
  depreciation for cost center `1412000040` through `B&L` VLOOKUPs.
- `固定資産金利（Interest）` rows 65/66 expose building and land
  interest for cost center `1412000040` through `B&L` VLOOKUPs.

## Matched source rows for Cost Center 1412000040

### Fixed Assets source evidence

| Sheet | Source row | Evidence |
|---|---:|---|
| `2025.11` | 620 | Asset `170001604`, depreciation `449.26`, interest `16.17`, last depreciation month `2026-03-31`. |
| `2025.11` | 1105 | Asset `170002397`, depreciation `165.39`, interest `17.88`, last month depreciation `165.39`, asset acquired `2025-10-01`. |
| `Planned Depreciation` | 6681/6682/6687/6693 sample | Existing old assets have generated interest formulas but zero depreciation simulation after expected last depreciation month. |

### Facility source evidence

| Sheet | Source row | Evidence |
|---|---:|---|
| `貂帑ｾ｡蜆溷唆雋ｻ・・epreciation・荏 | 65 | Building depreciation for 髮ｻ豌苓｣ｽ騾謚陦楢ｪｲ uses `VLOOKUP(B66,'B&L'...)`. |
| `貂帑ｾ｡蜆溷唆雋ｻ・・epreciation・荏 | 66 | Land depreciation for cost center `1412000040` uses `VLOOKUP(B66,'B&L'...)`. |
| `蝗ｺ螳夊ｳ・肇驥大茜・・nterest・荏 | 65 | Building interest for 髮ｻ豌苓｣ｽ騾謚陦楢ｪｲ uses `VLOOKUP(B66,'B&L'...)`. |
| `蝗ｺ螳夊ｳ・肇驥大茜・・nterest・荏 | 66 | Land interest for cost center `1412000040` uses `VLOOKUP(B66,'B&L'...)`. |
| `B&L` | 23 | Cost center `1412000040`; monthly building/land depreciation and interest values are allocated by ratio. |

## Business confirmation: file-order output mode

User/business confirmation after this trace:

- For groups without a clear fixed-row requirement, output should run by source-file order from `H蘯｡ng m盻･c c蘯ｧn c蘯｣i ti蘯ｿn`.
- After finishing one source file, leave one blank row before the next file group.
- The cost order inside each source file comes from the corresponding adjacent sheet / linked guidance.
- Do not use primary same-row or fixed-row comparison to conclude a bug while file-order mode is under consideration.

Relevant source-file order from the requirement image:

1. `譁ｽ險ｭ隱ｲ縲MPFY2027.xlsx`
2. `蝗ｺ螳夊ｳ・肇諠・ｱ_Fixed_Assets_Information_2025.11 - Nov.xlsx`
3. `繧ｷ繧ｹ繝・Β隱ｲ驥鷹≡鬘・Simulation)_FY2027_Apr.2026 ~ June.2026.xls`
4. `邱丞漁隱ｲ FY2027 MP 謖ｯ譖ｿ莠亥ｮ・xlsx`
5. `Sinh nh蘯ｭt MP FY2027.xlsx`
6. `FY2027驟崎ｳｦ鬘堺ｸ隕ｧ (2025.12.29).xlsx`
7. `D盻ｱ tﾃｭnh chi phﾃｭ lﾃm gi蘯･y t盻・cho NNN FY2027.xlsx`

The image also has a `6 chi phﾃｭ` link near Facility and `g盻冪 thﾃnh 1 dﾃｲng chi phﾃｭ` near System Cost.

## Row-fixed vs file-order decision needed

| Group | Current interpretation | Decision needed |
|---|---|---|
| Facility | File-order group; 6 costs; fixed row not yet mandatory. | Decide whether to output as 6 Facility costs by file order, not by primary row. |
| Fixed Assets | In file-order list, but older lock/audits mention FORM rows 38/42. | Decide transition: keep row-fixed rows 38/42 or emit fixed-assets file-order block. |
| System Cost | File-order group; linked note says combine into 1 cost row. | Confirm one-row output and placement in file order. |
| Admin allocation | File-order group; high priority because strict diff row 51 needs source/order trace. | Trace source-file order and blank-row separator. |
| Birthday | Row 59/63 conflict exists, but file-order mode may reduce row dependence. | Keep conflict note until output mode is decided. |
| NNN | Requirement mentions F137:Q137 but NNN is also in file-order list. | Decide if NNN remains row-fixed or moves to file-order block. |

## Row trace table

| Row | Business item | Source workbook | Source evidence | Generated evidence | Primary evidence | Conclusion | Confidence | Next action |
|---:|---|---|---|---|---|---|---|---|
| 38 | Fixed asset depreciation / equipment | Fixed Assets | `2025.11` row 1105 gives depreciation `165.39`; row 620 has last depreciation month before FY2027, so not active monthly depreciation. | Row 38 uses `=ROUND(165.39*$B$2,0)` in F:Q and `=SUM(F38:Q38)`. | Primary row 40 uses `165.39` in F/G but adds old last-month values in later months, e.g. `165.39+152.78+166.67`. | `SOURCE_CONFIRMS_GENERATED` for current source snapshot; primary appears to include different/older source snapshot or accumulated legacy assets. | High | Do not change code from primary diff alone; if primary parity is required, identify the exact primary source snapshot. |
| 40 | Facility building/land interest | Facility | `固定資産金利（Interest）` rows 65/66 and `B&L` row 23 show separate building and land interest allocations. | Row 40 uses building-only samples, e.g. `188.35` in F and `175.38` in Q. | Primary row 303 uses building + land, e.g. `(188.35+23.88)` in F and `(175.38+22.85)` in Q. | `SOURCE_CONFIRMS_PRIMARY_FOR_COMBINED_BUILDING_LAND_BUT_ROW_FIXEDNESS_NOT_REQUIRED` / `NEED_OUTPUT_MODE_DECISION` | High | Do not patch row 40 yet; trace whether Facility output is fixed-row, file-order mode, or mixed. |
| 42 | Fixed asset interest / equipment/tool | Fixed Assets | `2025.11` row 1105 gives interest `17.88`; planned depreciation contains additional interest formulas for many old assets. | Row 42 uses `17.88`, then `14.9` etc. as monthly source amounts. | Primary row 302 uses cumulative/combined amounts from multiple assets over months, e.g. `14.9+16.5+18`. | `SOURCE_AMBIGUOUS` / `NEED_CODE_TRACE`; current source has row 1105 but primary includes more interest components than the generated row. | Medium | Trace fixed asset parser aggregation rules for interest by depreciation cost center and active months. |

## Explicit conclusion per row

### Row 38

`SOURCE_CONFIRMS_GENERATED` against the current fixed-assets workbook snapshot:
row 1105 contains depreciation `165.39`, matching generated row 38.
Primary row 40 adds additional last-month depreciation amounts in later months.
That difference is not enough to call a code bug without the exact primary source
snapshot/version.

### Row 40

`SOURCE_CONFIRMS_PRIMARY_FOR_COMBINED_BUILDING_LAND_BUT_ROW_FIXEDNESS_NOT_REQUIRED` / `NEED_OUTPUT_MODE_DECISION`:
Facility source confirms distinct building and land interest components and primary row 303 combines them. However, the user/business confirmation says output can run by source-file order and is not necessarily tied to fixed rows. Therefore generated row 40 being building-only is not an immediate code bug by row-fixed interpretation; it first requires deciding whether Facility should be emitted as file-order 6-cost group, fixed FORM rows, or a mixed transition.

### Row 42

`SOURCE_AMBIGUOUS` / `NEED_CODE_TRACE`:
the fixed-assets source confirms at least one current asset interest amount
`17.88`, matching generated row 42 F. However, primary row 302 includes
additional accumulated components in later months. Need code-level aggregation
trace before classifying as bug or source-version mismatch.

## If source check is insufficient

Missing evidence:

- The exact source snapshot used to create the primary reference workbook.
- A code trace showing which fixed-assets rows are included/excluded for row 42.
- An output mode decision on whether Facility is row-fixed or file-order 6-cost block, and whether building/land interest must be combined in one emitted cost item.

## Recommended next phase

Phase 42N1L - Determine output mode architecture: fixed-row vs file-order groups.

## Forbidden conclusions

- Do not claim missing input snapshot for rows 38/42 from primary diff alone.
- Do not call row 40 a code bug just because generated does not match primary row 303.
- Do not force Facility into a fixed row when user/business has confirmed file-order mode is acceptable.
- Do not use strict diffs for rows 38/40/42 to request source-owner input additions.
- Do not edit code before deciding output mode architecture.
- Do not call row 42 a code bug until fixed-assets aggregation logic and output mode are traced.
- Do not compare generated rows 38/40/42 to primary same row numbers.
- Do not modify workbooks, template, parser/exporter, output, or compare tool in this phase.
