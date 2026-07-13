# Phase 42N2D - All Saisan File Role Inventory

## Classification

`PASS_PHASE_42N2D_FIX_READY_TO_COMMIT`

## Executive correction

Previous "missing data/source" conclusion is NOT final.

- Physical row-count gap = `136` remains a counting fact.
- True source-derived gap is not final.
- Current blocker may be incomplete file-role mapping, parser coverage,
  or reference-role handling, not missing company data.
- Secondary reference pool may be usable as skeleton/formula/order guide,
  but is not raw amount proof unless source provenance is found.

## Inventory summary

| Metric | Count |
|---|---:|
| total files inventoried | 119 |
| raw/manual/template files | 27 |
| requirement files | 9 |
| primary reference files | 1 |
| secondary files | 82 |
| secondary root | 65 |
| secondary subfolder | 17 |
| read errors | 0 |

## Explicit vs recursive secondary comparison

| Metric | Count |
|---|---:|
| explicit_list_count | 65 |
| recursive_discovered_count | 82 |
| missing_explicit_files | 0 |
| extra_discovered_files | 17 |
| secondary_root_files | 65 |
| secondary_subfolder_files | 17 |

### Missing explicit files

None

### Extra discovered files

- `reference_outputs\secondary\FY2027\MP data\Copy of 報告データ.xlsx`
- `reference_outputs\secondary\FY2027\MP data\DL chung\固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx`
- `reference_outputs\secondary\FY2027\MP data\DL chung\施設課　MPFY2027.xlsx`
- `reference_outputs\secondary\FY2027\MP data\DL chung\総務課 FY2027 MP 振替予定.xlsx`
- `reference_outputs\secondary\FY2027\MP data\Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx`
- `reference_outputs\secondary\FY2027\MP data\file check time&人.xlsx`
- `reference_outputs\secondary\FY2027\MP data\file check.xlsx`
- `reference_outputs\secondary\FY2027\MP data\FY2026経費.xlsx`
- `reference_outputs\secondary\FY2027\MP data\FY2027固定資産計画.xlsx`
- `reference_outputs\secondary\FY2027\MP data\MPのデータ 2027.xlsx`
- `reference_outputs\secondary\FY2027\MP data\old\報告データ.xlsx`
- `reference_outputs\secondary\FY2027\old\メカ2\15.KDTVN メカ製造技術2課_MP FY2027_各予定(Ver01).xlsx`
- `reference_outputs\secondary\FY2027\メカ2\15.KDTVN メカ製造技術2課_MP FY2027_各予定(Ver01).xlsx`
- `reference_outputs\secondary\FY2027\メカ１\14.KDTVN メカ製造技術1課_MP FY2027_各予定(Ver01).xlsx`
- `reference_outputs\secondary\FY2027\管理課\73.KDTVN 製造技術管理課_MP FY2027_各予定(Ver01).xlsx`
- `reference_outputs\secondary\FY2027\製造システム開発課\72.KDTVN 製造システム開発課_MP FY2027_各予定(Ver01).xlsx`
- `reference_outputs\secondary\FY2027\電気\16.KDTVN 電気製造技術課_MP FY2027_各予定(Ver01).xlsx`

## Source-order handled/unhandled table

| order | expected_file | absolute_path | exists | current_handling | status |
|---:|---|---|---|---|---|
| 1 | `施設課　MPFY2027.xlsx` | `D:\Sandbox\MP2027\raw\施設課　MPFY2027.xlsx` | YES | HANDLED_EXPLICIT_EXPORT_FLAG | Facility export v1 handles electricity/water/building/land families; still role-check remaining Facility rows. |
| 2 | `固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx` | `D:\Sandbox\MP2027\raw\固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx` | YES | PARTIAL_PARSER_COVERAGE | Fixed asset workbook is inventoried; current 5005026371 detail rows are not source-derived until exact row/cell/month mapping is proven. |
| 3 | `システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls` | `D:\Sandbox\MP2027\raw\システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls` | YES | HANDLED_EXPLICIT_EXPORT_FLAG | System cost flag covers simulation source period. |
| 4 | `システム課金金額(Simulation)_FY2027 July.2026 ~ Dec.2026(Change AMS & PLM price).xls` | `D:\Sandbox\MP2027\raw\システム課金金額(Simulation)_FY2027 July.2026 ~ Dec.2026(Change AMS & PLM price).xls` | NO | HANDLED_EXPLICIT_EXPORT_FLAG | System cost flag covers simulation source period. |
| 5 | `システム課金金額(Simulation)_FY2027 Jan.2027 ~ March.2027(Change SAP price).xls` | `D:\Sandbox\MP2027\raw\システム課金金額(Simulation)_FY2027 Jan.2027 ~ March.2027(Change SAP price).xls` | NO | HANDLED_EXPLICIT_EXPORT_FLAG | System cost flag covers simulation source period. |
| 6 | `総務課 FY2027 MP 振替予定.xlsx` | `D:\Sandbox\MP2027\raw\総務課 FY2027 MP 振替予定.xlsx` | YES | PARTIAL_PARSER_COVERAGE | Admin/GA workbook inventoried; some admin consumables exported, remaining allocation/order roles need row-level provenance. |
| 7 | `Sinh nhật MP FY2027.xlsx` | `D:\Sandbox\MP2027\raw\Sinh nhật MP FY2027.xlsx` | YES | UNHANDLED_SOURCE_ORDER_FILE | Birthday source is inventoried but not proven handled by an explicit export writer in current v1 flow. |
| 8 | `FY2027配賦額一覧 (2025.12.29).xlsx` | `D:\Sandbox\MP2027\raw\FY2027配賦額一覧 (2025.12.29).xlsx` | YES | PARTIAL_PARSER_COVERAGE | Allocation source is inventoried; travel/allocation rows require exact mapping before output generation. |
| 9 | `Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx` | `D:\Sandbox\MP2027\raw\Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx` | YES | UNHANDLED_SOURCE_ORDER_FILE | NNN paperwork source is inventoried but not proven handled by an explicit export writer in current v1 flow. |
| 10 | `event_drivers_manual.csv` | `D:\Sandbox\MP2027\raw\event_drivers_manual.csv` | YES | HANDLED_MANUAL_CSV | Manual CSV exists as explicit input channel; currently header-only/no rows for the target gap group. |
| 11 | `special_costs_manual.csv` | `D:\Sandbox\MP2027\raw\special_costs_manual.csv` | YES | HANDLED_MANUAL_CSV | Manual CSV exists as explicit input channel; currently header-only/no rows for the target gap group. |
| 12 | `headcount_manual.csv` | `D:\Sandbox\MP2027\raw\headcount_manual.csv` | YES | HANDLED_MANUAL_CSV | Manual CSV exists as explicit input channel for headcount-style rows. |

## Secondary FY2027 role conclusion

| Metric | Count |
|---|---:|
| files with sheet `内訳ﾘｽﾄ(4～3月)` | 71 |
| files containing account `5005026371` | 71 |
| files containing CC `1412000040` | 76 |
| looks_like generated_output_reference | 74 |
| looks_like skeleton_reference | 7 |

Concrete conclusion: secondary FY2027 workbooks are mostly
`generated_output_reference` or `skeleton_reference` files. They can be used
for skeleton, formula, row-order, and reference-fill guidance. They cannot be
used as source-derived amount proof unless the upstream raw source workbook,
sheet, row/cell, account, cost center, and Apr-Mar values are proven.

## Files by type

| file_type | Count |
|---|---:|
| `requirement` | 9 |
| `raw_input` | 23 |
| `manual_csv` | 3 |
| `template` | 1 |
| `primary_reference` | 1 |
| `secondary_reference` | 65 |
| `secondary_subfolder_file` | 17 |

## Looks-like role summary

| looks_like | Count |
|---|---:|
| `requirement` | 9 |
| `raw_source` | 14 |
| `source_master` | 10 |
| `skeleton_template` | 1 |
| `generated_output_reference` | 74 |
| `skeleton_reference` | 7 |
| `unknown` | 4 |

## Recommended fastest safe path: HYBRID PATH

Use a HYBRID PATH:

1. Use secondary references as skeleton/formula/order guide.
2. Use reference-assisted fill only with a provenance label.
3. Implement source parsers only when source workbook/sheet/row/cell/month
   values are proven.

This is fastest because it can close the physical row-count gap transparently
without pretending every filled line is source-derived.

## Output CSV

`docs/audits/phase42n2d_all_saisan_file_role_inventory.csv`

## Conclusion

`PASS_PHASE_42N2D_FIX_READY_TO_COMMIT`
