# Phase 42N1N-A - Facility File-Order Dry Run

## Scope

Read-only dry-run only. No Excel output was written and no writer flow was changed.

## Planned placement

- Cost center: `1412000040`
- Facility planned rows: `200`-`205`
- Blank row after Facility group: `206`

## Scanned sheets

- `減価償却費（Depreciation）`
- `固定資産金利（Interest）`
- `水道光熱費（Electric & Water）`
- `B&L`
- `E&W`

## Dry-run items

| # | item_id | display_name | source_sheet | source_row | Apr sample | Mar sample | formula_policy | planned_row | confidence | note |
|---|---|---|---|---:|---:|---:|---|---:|---|---|
| 1 | `building_depreciation` | Khấu hao nhà | `減価償却費（Depreciation）` | 65 | 293.02 | 289.03 | `ROUND_USD_BY_B2` | 200 | HIGH | matched cost-center row with paired building/electric row above |
| 2 | `land_depreciation` | Khấu hao đất | `減価償却費（Depreciation）` | 66 | 19.78 | 19.51 | `ROUND_USD_BY_B2` | 201 | HIGH | matched cost-center row |
| 3 | `building_interest` | Lãi nhà | `固定資産金利（Interest）` | 65 | 188.35 | 175.38 | `ROUND_USD_BY_B2` | 202 | HIGH | matched cost-center row with paired building/electric row above |
| 4 | `land_interest` | Lãi đất | `固定資産金利（Interest）` | 66 | 23.88 | 22.85 | `ROUND_USD_BY_B2` | 203 | HIGH | matched cost-center row |
| 5 | `electricity` | Điện | `水道光熱費（Electric & Water）` | 64 | 1577160 | 1203521 | `COPY_VND_MONTHLY` | 204 | HIGH | matched cost-center row with paired building/electric row above |
| 6 | `water` | Nước | `水道光熱費（Electric & Water）` | 65 | 529671 | 637935 | `COPY_VND_MONTHLY` | 205 | HIGH | matched cost-center row |
