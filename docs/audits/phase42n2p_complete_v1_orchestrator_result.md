# Phase 42N2P - Complete v1 Orchestrator Result

## Classification

`PASS_PHASE_42N2P_COMPLETE_V1_READY_TO_COMMIT`

## What changed

Implemented one explicit unified product command:

```powershell
py scripts/run_e2e.py --target-cc 1412000040 --mp-saisan-complete-v1
```

This mode runs the existing file-order v1 source-derived layer first, then applies
reference-assisted primary fill, then attempts fixed-assets secondary skeleton
fill only for identities not already represented.

## Priority policy

The complete mode uses this priority order:

1. `SOURCE_DERIVED`
2. `MANUAL_INPUT`
3. `REFERENCE_FILLED_FROM_PRIMARY`
4. `REFERENCE_ASSISTED_SECONDARY_SKELETON`
5. `UNKNOWN_NEEDS_MAPPING`

Known false-gap aliases are normalized so they do not create duplicate rows:

- `電気代` = `electricity` = `Điện`
- `水道代` = `water` = `Nước`

## Dry run summary

Command:

```powershell
py "..\..\scripts\run_e2e.py" --target-cc 1412000040 --mp-saisan-complete-v1
```

Pipeline summary:

```text
source_rows=148
primary_reference_rows_written=134
fixed_assets_skeleton_rows_written=0
skipped_duplicate=48
skipped_incomplete=0
final_business_rows=282
primary_business_rows=284
physical_gap=2
logical_false_gaps=2
primary_reference_rows_total=134
fixed_assets_skeleton_rows_total=0
```

42N1P-B count-method summary:

| Workbook/mode | Business rows | Source/v1 rows | Primary reference rows | Secondary skeleton rows | 5005026371 rows | Gap vs primary |
|---|---:|---:|---:|---:|---:|---:|
| Primary reference | 277 | 277 | 0 | 0 | 75 | 0 |
| Complete v1 | 275 | 141 | 134 | 0 | 83 | 2 |

## Non-tech explanation

This is the first unified complete export mode. The user now needs one command
instead of choosing between HYBRID v2 and fixed-assets skeleton mode.

It does **not** pretend that reference-assisted rows are source-derived. Rows
copied from the primary reference remain labelled `REFERENCE_FILLED_FROM_PRIMARY;
not source-derived`. Secondary skeleton rows would be labelled
`REFERENCE_ASSISTED_SECONDARY_SKELETON; not source-derived`, but in this run all
48 secondary skeleton candidates were skipped as duplicates because the primary
reference layer already represented them.

The mode avoids double counting by using a business identity policy with account,
normalized description/alias, month vector, source family, and target CC. The
secondary skeleton layer is lower priority than primary reference fill, so it does
not append another copy when the primary reference already provides that business
identity.

## Gap explanation

The remaining physical gap is `2` rows. This is classified as logical false-gap
alias behavior for:

- `電気代` / `electricity` / `Điện`
- `水道代` / `water` / `Nước`

Non-tech conclusion: the complete v1 command is ready for CC `1412000040` as a
transparent, provenance-labelled release candidate, but it is still not a 100%
source-derived engine.

## Safety notes

- Default export remains unchanged.
- Complete v1 is explicit-only.
- CC other than `1412000040` requires a valid reference map/path.
- Source-derived/manual rows are never overwritten by reference-assisted layers.
- Secondary skeleton rows are skipped when already represented by higher-priority
  source/manual/primary-reference rows.

## Conclusion

`PASS_PHASE_42N2P_COMPLETE_V1_READY_TO_COMMIT`
