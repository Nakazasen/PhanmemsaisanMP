# Phase 42N2C - Fixed Assets Detail Account 5005026371 Mapping

## Classification

`WARNING_PHASE_42N2C_FIXED_ASSETS_DETAIL_NOT_IMPLEMENTABLE_YET`

## Scope

Focused only on the largest remaining invariant-accounting group:

- account code: `5005026371`
- candidate family: fixed-assets/detail expense
- target rows: `75`

No output code was changed. No full pytest was run. No package was created.

## Source files inspected

- `raw/固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx`
- `raw/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026.xlsx`
- `raw/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026_ảnh.xlsx`
- `raw/event_drivers_manual.csv`
- `raw/special_costs_manual.csv`
- `raw/requirements/`
- `docs/MP2027/`

## Result summary

| Metric | Count |
|---|---:|
| 5005026371 target rows | 75 |
| IMPLEMENTABLE_NOW | 0 |
| SOURCE_MASTER_ONLY_NO_MONTH_VALUES | 75 |

## Fixed asset workbook finding

The fixed asset workbook has rows for cost center `1412000040`, especially in
`Planned Depreciation`. Example evidence:

| Sheet | Row | Evidence sample |
|---|---:|---|
| 2025.11 | 620 | `=SUBTOTAL(3,$B$5:B620) | MFG)TOOLS FURNITURE AND FIXTURES | 170001604 | Oscilloscope DLM5058-F-HE (May phat hien song) |  | 2021-04-16 00:00:00 | 005 | 1412000040 | Elect Produ Engi Sec | 1412000040 | Elect Produ Engi Se` |
| 2025.11 | 1105 | `=SUBTOTAL(3,$B$5:B1105) | MFG)TOOLS FURNITURE AND FIXTURES | 170002397 | CURRENT PROBE YOKOGAWA (PBC100) |  | 2025-10-01 00:00:00 | 003 | 1412000040 | Elect Produ Engi Sec | 1412000040 | Elect Produ Engi Sec | 165.39 | 1` |
| Fixed assets list | 579 | `574 | 160000471 | 0 | 160000471 | 3V2LV01080 - P.W.BOARD ASSY TONER SENSOR | 1412000015 | Factory(C/3F) | 1412000040 | Elect Produ Engi Sec | 1412000040 | Elect Produ Engi Sec | 2013-07-04 00:00:00 | 2875.9 | 0 | 002 | F` |
| Fixed assets list | 7079 | `7074 | 170000001 | 0 | 170000001 | 2M2-9004_PRT Main PWB F/W Download No.1 | 1412000015 | Factory(C/3F) | 1412000040 | Elect Produ Engi Sec | 1412000004 | Machi Manufact 1 Se | 2012-10-04 00:00:00 | 2867.75 | 0 | 003 | L` |
| Fixed assets list | 7080 | `7075 | 170000002 | 0 | 170000002 | 2M2-9004_PRT Main PWB F/W Download No.2 | 1412000015 | Factory(C/3F) | 1412000040 | Elect Produ Engi Sec | 1412000004 | Machi Manufact 1 Se | 2012-10-04 00:00:00 | 2807.29 | 0 | 003 | L` |

However, this is not enough to generate account `5005026371` detail expense
rows. The workbook is a fixed-asset master/planned depreciation source. It shows
asset records and CC references, but it does not provide a one-to-one mapping for
the primary detail expense lines with Apr-Mar output values.

## Manual check needed

For each row in the CSV, a non-technical reviewer should confirm:

1. Which source workbook contains the exact item.
2. Which sheet and row/cell hold the source amount.
3. Whether the row belongs to CC `1412000040`.
4. Whether the amount maps to account `5005026371`.
5. The Apr-Mar monthly values or formulas.
6. The intended output order in file-order export.

If the reviewer can provide those fields for at least 10 rows, the next phase can
safely implement a `--fixed-assets-detail-export` writer. Without that mapping,
implementation would require guessing monthly values.

## Mapping CSV

`docs/audits/phase42n2c_fixed_assets_detail_5005026371_mapping.csv`

## Decision

No batch was implemented because `IMPLEMENTABLE_NOW = 0` for the 5005026371 rows.

## Conclusion

`WARNING_PHASE_42N2C_FIXED_ASSETS_DETAIL_NOT_IMPLEMENTABLE_YET`
