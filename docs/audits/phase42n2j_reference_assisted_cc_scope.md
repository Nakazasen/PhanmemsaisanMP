# Phase 42N2J - Reference-Assisted CC Scope Guard

## Classification

`PASS_PHASE_42N2J_REFERENCE_ASSISTED_SCOPE_GUARD_READY`

## Finding

Current Hybrid v2 originally used a hard-coded primary reference workbook:

`reference_outputs/primary/16.KDTVN 電気製造技術課_MP FY2027_各予定(Ver01).xlsx`

That workbook is the proven primary reference for target CC `1412000040` /
`電気製造技術課`. It must not be silently reused for other cost centers or
departments.

## Change

Added explicit reference resolution:

- `--primary-reference-path <path>` can provide the exact reference workbook.
- `--reference-map-path <path>` can provide a CSV map.
- Default reference remains available only for current proven target CC
  `1412000040`.
- If reference-assisted fill is requested for another CC without a mapped or
  explicit primary reference, the pipeline fails clearly:

```text
Reference-assisted fill requires --primary-reference-path for this target CC.
```

## Reference map

Created:

`docs/config/reference_workbook_map.csv`

Schema:

```text
target_cc,department_name,reference_path,reference_role
```

Initial row:

```text
1412000040,電気製造技術課,reference_outputs/primary/16.KDTVN 電気製造技術課_MP FY2027_各予定(Ver01).xlsx,primary_reference
```

No secondary files are mapped as primary references.

## Non-tech explanation

Current HYBRID v2 has proven row-count behavior for CC `1412000040` only.
Reference-assisted fill is not universal unless the correct MP FY2027 reference
workbook is mapped for the target CC/department.

For other CCs, the user must provide or map the corresponding MP FY2027 workbook.
This avoids using the wrong department's reference, avoids false completion, and
keeps provenance honest.

## Provenance policy

Reference-assisted rows remain labelled as reference-assisted and `not source-derived`.
The scope guard does not change this policy.

## Conclusion

`PASS_PHASE_42N2J_REFERENCE_ASSISTED_SCOPE_GUARD_READY`
