# Phase 42N1V-A - File-Order Export V1 Acceptance Audit

## Scope

This phase adds and verifies MP2027 file-order export v1 as an explicit-only
master flag:

```text
--file-order-export-v1
```

The flag enables the file-order groups that are already implemented and tested:

- Facility
- Admin consumables
- System Cost

No default export behavior is changed. Individual flags remain available.

## Precheck

- Branch: `main`
- HEAD: `9536a34 feat(workflow): add system cost export flag`
- `origin/main...HEAD`: `0 0`
- Working tree was clean before implementation.

## Master flag behavior

When `--file-order-export-v1` is ON, it is equivalent to:

```text
--facility-file-order-export --facility-file-order-start-row 200
--admin-consumables-export --admin-consumables-start-row 207
--system-cost-export --system-cost-start-row 211
```

When the flag is OFF, default export remains unchanged.

## Included in v1

| Group | Rows | Evidence basis |
|---|---:|---|
| Facility | 200-205 | Facility source workbook and previous row-count gates |
| Admin consumables | 207-209 | Exact Admin source rows from `総務課 FY2027 MP 振替予定.xlsx` |
| System Cost | 211 | Native `.xls` summary row for CC `1412000040` |

Separator rows:

- row 206 blank after Facility
- row 210 blank after Admin
- row 212 blank after System Cost

## Not included in v1

The following groups are intentionally not included in file-order export v1:

- Fixed Assets transition rows
- Birthday / NNN rows
- Remaining unmatched detail rows

Reasons not included yet:

- Exact source-to-primary placement is not sufficiently proven for all rows.
- Some groups need native mapping or reconciliation by account/asset/amount, not text alone.
- Some rows require a separate focused phase to avoid broad unsafe placement.

## Gate results

Targeted gate:

```text
py -m pytest tests/test_file_order_export_v1_flag.py tests/test_system_cost_export_flag.py tests/test_admin_consumables_export_flag.py tests/test_facility_file_order_export_flag.py tests/test_output_placement.py tests/test_output_mode.py -q
38 passed in 4.74s
```

Compile and diff checks:

```text
py -m compileall src tools tests scripts
PASS

git diff --check
PASS
```

No full pytest was run.

## Real output run

Command used from isolated output directory:

```text
py "..\..\..\scripts\run_e2e.py" --target-cc 1412000040 --file-order-export-v1
```

Generated output:

`dist/phase42n1v_a_file_order_export_v1/flag_on/OUTPUT_FY2027/MP_CC_1412000040.xlsx`

## Row verification

| Row | E item_id | F Apr/sample | Q Mar/sample | S description | T policy | Result |
|---:|---|---:|---:|---|---|---|
| 200 | `building_depreciation` | `293.02` | `289.03` | `Khấu hao nhà` | `ROUND_USD_BY_B2` | Facility OK |
| 201 | `land_depreciation` | `19.78` | `19.51` | `Khấu hao đất` | `ROUND_USD_BY_B2` | Facility OK |
| 202 | `building_interest` | `188.35` | `175.38` | `Lãi nhà` | `ROUND_USD_BY_B2` | Facility OK |
| 203 | `land_interest` | `23.88` | `22.85` | `Lãi đất` | `ROUND_USD_BY_B2` | Facility OK |
| 204 | `electricity` | `1577160` | `1203521` | `Điện` | `COPY_VND_MONTHLY` | Facility OK |
| 205 | `water` | `529671` | `637935` | `Nước` | `COPY_VND_MONTHLY` | Facility OK |
| 206 |  |  |  |  |  | Blank OK |
| 207 | `toilet_paper` | `18895` | `20665` | `トイレットペーパー` | `COPY_SOURCE_MONTH_SAMPLE` | Admin OK |
| 208 | `hand_soap` | `1365` | `1462` | `手洗い洗剤` | `COPY_SOURCE_MONTH_SAMPLE` | Admin OK |
| 209 | `alcohol_disinfectant` | `UNKNOWN` | `UNKNOWN` | `アルコール消毒` | `UNKNOWN` | Admin OK |
| 210 |  |  |  |  |  | Blank OK |
| 211 | `system_cost_combined` | `6111363` | `6111363` | `System Cost / システム課金` | `COPY_SUMMARY_VND_TOTAL_BY_PERIOD` | System OK |
| 212 |  |  |  |  |  | Blank OK |

## Business row counts

| Workbook | Business rows |
|---|---:|
| File-order export v1 generated | 141 |
| Primary reference | 277 |

Remaining gap:

```text
277 - 141 = 136 rows
```

## Recommendation

If the user wants to end early with a usable review build, use:

```text
py scripts/run_e2e.py --target-cc 1412000040 --file-order-export-v1
```

If the user wants to keep reducing the gap, the next phase should choose only
one high-impact group and prove exact source/placement before writing rows.
Likely candidates are Fixed Assets transition or remaining detail rows with
clear source/account/amount evidence.

## Conclusion

`PASS_PHASE_42N1V_A_FILE_ORDER_EXPORT_V1_READY_TO_COMMIT`

File-order export v1 is explicit-only, keeps default export unchanged, and
combines the three implemented safe groups into one master flag.
