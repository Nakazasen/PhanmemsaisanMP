# Phase 42N3C - Real Writer Migration to Source File Order

## Classification

`PASS_PHASE_42N3C_SOURCE_ORDER_WRITER_MIGRATION_READY`

## Requirement

The real complete-v1 / GUI package export path must not place the current business modules by fixed FORM rows 38/42/58/59/97/98/137. Final output is grouped by source file order with one blank separator row between completed source blocks.

## Implementation

- Added `src/engine/complete_v1_source_order_writer.py`.
- Wired `scripts/run_e2e.py --mp-saisan-complete-v1` to call `apply_complete_v1_source_order_to_workbook(...)` after the existing source-specific writers and before reference-assisted fill.
- Kept `REFERENCE_FILLED_FROM_PRIMARY` rows appended by `mp_saisan_complete_export`; no 100% source-derived claim is made.

## Real Output Verification

Output workbook:

`dist\phase42n3c_source_order_complete_v1\OUTPUT_FY2027\MP_CC_1412000040.xlsx`

| Metric | Result |
|---|---:|
| Business rows | 242 |
| REFERENCE_FILLED_FROM_PRIMARY rows | 134 |
| Source-order rows migrated | 18 |
| Blank separator rows | 6 |

Blank separator rows: `[174, 177, 179, 183, 185, 190]`

## Observed Source Blocks

- `施設課　MPFY2027.xlsx`
- `固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx`
- `システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls`
- `総務課 FY2027 MP 振替予定.xlsx`
- `Sinh nhật MP FY2027.xlsx`
- `FY2027配賦額一覧 (2025.12.29).xlsx`
- `Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx`

## Legacy Fixed Rows

Rows 38, 42, 58, 59, 97, 98, and 137 were checked in the generated workbook. Their business descriptions and monthly values are blank after migration.

## Remaining Fixed-Row References

Inventory file:

`docs/audits/phase42n3c_active_fixed_row_reference_inventory.json`

Remaining hit count: `220`

These remaining references include schema fields, GUI/manual input support, tests, docs, and legacy staging/audit code. They must not be treated as final placement logic for complete-v1 source-order output.

## Final Classification

`PASS_PHASE_42N3C_SOURCE_ORDER_WRITER_MIGRATION_READY`
