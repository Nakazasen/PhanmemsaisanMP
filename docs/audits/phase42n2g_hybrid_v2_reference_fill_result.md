# Phase 42N2G - Hybrid v2 Reference-Assisted Fill Result

## Classification

`PHYSICAL_GAP_REMAINING=2`

## Summary

Hybrid v2 is explicit-only. It keeps default export unchanged and keeps
`--file-order-export-v1` unchanged. New `--file-order-export-v2` enables v1 plus
reference-assisted fill from the primary reference with provenance labels.

Reference-assisted rows are **NOT source-derived**. They are copied from the
primary reference as skeleton/reference fill and labelled in column T.

## Generated output

- `dist/phase42n2g_hybrid_v2/OUTPUT_FY2027/MP_CC_1412000040.xlsx`

## Row count table

| Workbook | Business rows |
|---|---:|
| Primary reference | 284 |
| Generated hybrid v2 | 282 |
| Physical gap after v2 | 2 |

## Provenance count table

| Provenance bucket | Count |
|---|---:|
| SOURCE_DERIVED / v1 generated rows | 148 |
| REFERENCE_FILLED_FROM_PRIMARY | 134 |
| Skipped false gaps | 2 |
| Remaining physical delta | 2 |

## Implementation facts

- Default export unchanged.
- `--file-order-export-v1` unchanged.
- `--file-order-export-v2` is explicit only.
- v2 enables Facility row 200, Admin row 207, System row 211, and reference fill start row 213.
- Reference fill does not overwrite rows 200-212.
- Reference fill adds column T label:
  `REFERENCE_FILLED_FROM_PRIMARY; primary_row=<n>; not source-derived`.

## Known remaining blockers

- Source-derived proof is still missing for reference-assisted rows.
- Fixed assets/account `5005026371` still needs raw workbook/sheet/row/cell/month mapping before source-derived export.
- Birthday, NNN, and allocation mappings remain separate source-derived work.

## Conclusion

`WARNING_PHASE_42N2G_HYBRID_V2_GAP_NOT_CLOSED`
