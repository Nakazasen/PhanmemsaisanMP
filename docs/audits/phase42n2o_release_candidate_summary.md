# Phase 42N2O - MP Saisan Release Candidate Summary

## Classification

`PASS_PHASE_42N2O_RELEASE_CANDIDATE_READY`

## What is ready

The project now has a release-candidate workflow for CC `1412000040`.

There are two explicit modes:

1. **HYBRID v2 final-check mode**
   - Command:
     `py scripts/run_e2e.py --target-cc 1412000040 --file-order-export-v2`
   - Purpose:
     close practical row-count parity against the primary reference using transparent reference-assisted rows.
   - Important:
     reference-assisted rows are not source-derived.

2. **Fixed-assets secondary skeleton mode**
   - Command:
     `py scripts/run_e2e.py --target-cc 1412000040 --file-order-export-v1 --fixed-assets-reference-skeleton-export`
   - Purpose:
     test/use secondary skeleton candidates for account `5005026371`.
   - Important:
     this mode is blocked from combining with primary reference fill to avoid duplicate risk.

## Row-count summary using 42N1P-B count method

| Workbook/mode | Business rows | Gap vs primary | Primary reference fill rows | Fixed-assets skeleton rows | 5005026371 rows |
|---|---:|---:|---:|---:|---:|
| Primary reference | 277 | 0 | 0 | 0 | 75 |
| HYBRID v2 | 275 | 2 | 134 | 0 | 83 |
| Fixed-assets skeleton mode | 189 | 88 | 0 | 48 | 56 |

## Non-tech explanation

This release candidate is **not** claiming that every row is automatically
source-derived from raw business files.

Correct claim:

> For CC `1412000040`, HYBRID v2 can generate a workbook that is practically
> aligned with the primary reference while labelling reference-assisted rows
> transparently. The two physical-row delta rows are known false-gap aliases:
> `電気代` and `水道代`, already generated as `electricity` and `water`.

Wrong claim:

> The system fully auto-calculates every MP Saisan row from raw source files.

## Safety rules

- Default export remains unchanged.
- HYBRID v2 is explicit-only.
- Fixed-assets skeleton export is explicit-only.
- Fixed-assets skeleton export cannot be combined with primary reference fill because of duplicate-risk.
- CC other than `1412000040` requires an explicit reference path/map for reference-assisted fill.
- `REFERENCE_FILLED_FROM_PRIMARY` rows are not source-derived.
- `REFERENCE_ASSISTED_SECONDARY_SKELETON` rows are not source-derived.

## Remaining work

To become fully source-derived, remaining modules still need raw workbook/sheet/row/cell/month mapping and migration to shared account resolver:

- Fixed assets detail beyond skeleton/reference-assisted mode
- Birthday
- NNN paperwork
- Allocation
- Other source-order modules not fully migrated

## Recommended release wording

`MP Saisan HYBRID v2 release candidate for CC 1412000040: usable with transparent provenance, not a 100% source-derived engine yet.`

## Conclusion

`PASS_PHASE_42N2O_RELEASE_CANDIDATE_READY`
