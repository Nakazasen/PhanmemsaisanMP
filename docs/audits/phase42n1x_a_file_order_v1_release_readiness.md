# Phase 42N1X-A - File-Order Export V1 Release Readiness

## Release status

`RELEASE_READY_MP2027_FILE_ORDER_V1`

MP2027 file-order export v1 is release-ready/useable within its explicit scope.
This is not a parity claim against the primary workbook.

## Usage command

```powershell
py scripts/run_e2e.py --target-cc 1412000040 --file-order-export-v1
```

## What v1 includes

| Group | Rows | Notes |
|---|---:|---|
| Facility | 200-205 | six implemented Facility file-order rows |
| Separator | 206 | blank row |
| Admin consumables | 207-209 | toilet paper, hand soap, alcohol disinfectant |
| Separator | 210 | blank row |
| System Cost | 211 | single combined System Cost row |
| Separator | 212 | blank row |

The master flag `--file-order-export-v1` is default OFF.

Individual flags remain available:

- `--facility-file-order-export`
- `--admin-consumables-export`
- `--system-cost-export`

## Automated RC result

From `docs/audits/phase42n1w_auto_file_order_v1_rc_check.md`:

| Metric | Result |
|---|---:|
| Generated file-order v1 rows | 141 |
| Primary reference rows | 277 |
| Remaining gap | 136 |

RC conclusion:

`ACCEPT_MP2027_FILE_ORDER_V1_AUTOMATED_RC`

## Gate results

Targeted gate only, no full pytest:

```text
py -m pytest tests/test_file_order_export_v1_flag.py tests/test_system_cost_export_flag.py tests/test_admin_consumables_export_flag.py tests/test_facility_file_order_export_flag.py tests/test_output_placement.py tests/test_output_mode.py -q
38 passed in 4.59s
```

Compile and diff checks:

```text
py -m compileall src tools tests scripts
PASS

git diff --check
PASS
```

## Known backlog

The remaining `136` row gap is known and not hidden.

Backlog not included in v1:

- Fixed Assets transition
- Birthday / NNN
- Unmatched primary detail rows
- Exact-source-missing rows documented in `phase42n1s_a2_raw_source_full_scan.md`

These groups do not block v1 because v1 is explicitly scoped to the implemented
and automatically verified file-order groups only.

## What not to claim

Do not claim:

- parity with the primary `277` business rows
- full business completion
- default export behavior changed
- unmatched rows are generated
- Fixed Assets / Birthday / NNN are included in v1

## Recommendation

If the goal is a runnable/useable review build, use file-order export v1:

```powershell
py scripts/run_e2e.py --target-cc 1412000040 --file-order-export-v1
```

If the goal is parity with the primary workbook, open a separate backlog phase
and choose one high-impact group with exact source, placement, and amount
evidence before adding more rows.

## Conclusion

`RELEASE_READY_MP2027_FILE_ORDER_V1`
