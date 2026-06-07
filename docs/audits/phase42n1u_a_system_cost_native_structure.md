# Phase 42N1U-A - System Cost Native Structure and Export Flag

## Scope

Accelerated System Cost phase with an internal decision gate:

1. Audit the native structure of the three System Cost `.xls` workbooks.
2. Implement a preview/writer/export flag only if mapping is clear.
3. Run a real export with Facility + Admin + System flags ON.
4. Recount business rows vs current Facility+Admin and primary.

No full pytest was run. No package/build was run. No commit was made.

## Precheck

- Branch: `main`
- HEAD: `681d542 docs(audit): recount output after admin consumables flag`
- `origin/main...HEAD`: `0 0`
- Working tree was clean before this phase.

## System source files inspected

All three `.xls` System Cost files were inspected with `xlrd`:

| File | Period represented | Native summary sheet | CC row evidence |
|---|---|---|---|
| `raw/システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls` | Apr-Jun | `部門別サマリー(VND)` | row 24, CC `1412000040` |
| `raw/システム課金金額(Simulation)_FY2027_July.2026 ~ Dec.2026(Change AMS & PLM price).xls` | Jul-Dec | `部門別サマリー(VND)` | row 24, CC `1412000040` |
| `raw/システム課金金額(Simulation)_FY2027_Jan.2027 ~ March.2027(Change SAP price).xls` | Jan-Mar | `部門別サマリー(VND)` | row 24, CC `1412000040` |

## Native structure summary

Each System Cost workbook contains these sheets:

- `部門別サマリー(VND)`
- `部門別サマリー (USD)`
- `VPN 明細`
- `メール 明細`
- `R3明細`
- `MES 明細`
- `PLM明細`
- `QLIK SENSE 明細`
- `VPS明細`
- `AMS明細`

The VND summary sheet has row-level department/CC totals. For CC `1412000040`,
row 24 has:

- Department: `電気製造技術課`
- Cost center: `1412000040`
- Account: `5005246282`
- Total transfer amount: `6,111,363` VND

Observed row 24 values in each of the three files:

```text
['電気製造技術課', 1412000040.0, 5005246282.0, '-', 83811.0, '-', 5140838.0, '-', '-', '-', 886714.0, 6111363.0]
```

The three files map to fiscal periods by filename/order:

- Apr-Jun workbook -> Apr, May, Jun
- Jul-Dec workbook -> Jul, Aug, Sep, Oct, Nov, Dec
- Jan-Mar workbook -> Jan, Feb, Mar

This is sufficient for the requested `FILE_ORDER_SINGLE_ROW` implementation.

## Decision

Implemented.

Decision gate was satisfied because all three required points were clear:

1. Source rows/cells for CC `1412000040`: summary sheet row 24, total column L.
2. Month values Apr-Mar: each workbook's row-24 total applies to its filename period.
3. Single-row aggregation: requirement says System Cost should be one combined row.

## Implemented files

Added:

- `src/engine/system_cost_preview.py`
- `src/engine/system_cost_writer.py`
- `tests/test_system_cost_preview.py`
- `tests/test_system_cost_writer.py`
- `tests/test_system_cost_export_flag.py`

Modified:

- `scripts/run_e2e.py`

This report:

- `docs/audits/phase42n1u_a_system_cost_native_structure.md`

## Row planned/written

System Cost file-order single row:

| Row | E item_id | F Apr | Q Mar | S display | T policy |
|---:|---|---:|---:|---|---|
| 211 | `system_cost_combined` | `6111363` | `6111363` | `System Cost / システム課金` | `COPY_SUMMARY_VND_TOTAL_BY_PERIOD` |
| 212 | blank |  |  |  |  |

## Export count result

Generated output:

`dist/phase42n1u_a_system_cost_export_flag/flag_on/OUTPUT_FY2027/MP_CC_1412000040.xlsx`

| Workbook | Business rows |
|---|---:|
| Facility + Admin flags ON | 140 |
| Facility + Admin + System flags ON | 141 |
| Primary reference | 277 |

| Metric | Count |
|---|---:|
| System flag delta | +1 |
| Remaining gap vs Primary | 136 |

## Gate results

Targeted tests:

```text
py -m pytest tests/test_system_cost_preview.py tests/test_system_cost_writer.py tests/test_system_cost_export_flag.py tests/test_admin_consumables_export_flag.py tests/test_facility_file_order_export_flag.py tests/test_output_placement.py tests/test_output_mode.py -q
38 passed in 8.56s
```

Compile/gate:

```text
py -m compileall src tools tests scripts
PASS

git diff --check
PASS
```

## Notes and limitations

This implementation uses the VND summary total column from `部門別サマリー(VND)`.
It intentionally does not expand detailed sheets into multiple output rows,
because the target output mode for this phase is `FILE_ORDER_SINGLE_ROW`.

## Conclusion

`PASS_PHASE_42N1U_A_SYSTEM_COST_EXPORT_FLAG_READY_TO_COMMIT`

System Cost native structure is clear enough for a guarded explicit-only
single-row export flag. Default export behavior remains unchanged.
