# Phase 42N2N - Fixed Assets Reference Skeleton Result

## Classification

`PASS_PHASE_42N2N_FIXED_ASSETS_SKELETON_READY_TO_COMMIT`

## Scope

Implemented an explicit-only fixed-assets reference skeleton writer for account
`5005026371`, based on the Phase 42N2E secondary skeleton candidate CSV.

This mode is not enabled by default and does not claim source-derived proof.

## Files changed

- `src/engine/fixed_assets_reference_skeleton.py`
- `scripts/run_e2e.py`
- `tests/test_fixed_assets_reference_skeleton.py`
- `docs/audits/phase42n2n_fixed_assets_reference_skeleton_result.md`

## Behavior

The writer loads only rows with:

```text
classification == REFERENCE_ASSISTED_FILL_CANDIDATE
account == 5005026371
```

Rows written to the workbook carry column `T` provenance:

```text
REFERENCE_ASSISTED_SECONDARY_SKELETON; account=5005026371; not source-derived
```

The writer does not overwrite rows that already contain business content in
`B/S/F:Q/T`. If `start_row` is not provided, it appends after the last business
row.

## CLI integration

Added explicit-only flags:

```text
--fixed-assets-reference-skeleton-export
--fixed-assets-skeleton-csv
--fixed-assets-skeleton-start-row
```

Default export remains unchanged. `--file-order-export-v2` remains unchanged
except that combining it with fixed-assets skeleton export fails early because
v2 enables primary reference fill and creates duplicate-risk ambiguity.

## Dry run

Command:

```powershell
py scripts/run_e2e.py --target-cc 1412000040 --file-order-export-v1 --fixed-assets-reference-skeleton-export
```

Result from pipeline:

```text
selected=48
written=48
skipped_existing=0
skipped_incomplete=0
start_row=212
```

Workbook count after dry run:

| Metric | Count |
|---|---:|
| Generated business rows | 196 |
| Primary business rows | 284 |
| Gap vs primary | 88 |
| Fixed-assets skeleton provenance rows | 48 |
| Generated `5005026371` rows | 56 |
| Primary `5005026371` rows | 75 |
| Provenance row range | 212-259 |

## Duplicate risk assessment

Duplicate risk exists if this secondary skeleton writer is combined with primary
reference fill, because both are reference-assisted row completion mechanisms.
The implementation therefore fails early for this combination.

Safe modes:

- default export: unaffected
- `--file-order-export-v1`: unaffected unless fixed-assets flag is also passed
- fixed-assets skeleton only: safe explicit add-on

Unsafe mode blocked:

- fixed-assets skeleton + `--primary-reference-fill`
- fixed-assets skeleton + `--file-order-export-v2`

## Gap impact

The dry run writes 48 reference-assisted secondary skeleton rows. This reduces
physical row-count gap materially, but the generated workbook still remains 88
business rows below primary using the count method applied in this phase.

## Source-derived status

These rows are reference-assisted secondary skeleton rows only. They are not
source-derived and must not be described as source-derived in user-facing reports.

## Conclusion

`PASS_PHASE_42N2N_FIXED_ASSETS_SKELETON_READY_TO_COMMIT`
