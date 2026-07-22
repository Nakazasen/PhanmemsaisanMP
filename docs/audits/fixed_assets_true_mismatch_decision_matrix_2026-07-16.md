# Fixed assets: decision matrix for all true amount mismatches

- Generated from the reproducible 2026-07-16 cross-trace CSVs.
- Coverage: **638 of 638** `TRUE_AMOUNT_MISMATCH` monthly cells, across 66 FY/CC/account groups.
- This is an evidence classification, not permission to overwrite departmental submissions.

## Evidence classification

| Classification | Cells |
| --- | ---: |
| `CONSISTENT_REFERENCE_ADJUSTMENT` | 2 |
| `POST_TERMINAL_REFERENCE_CONTINUES` | 4 |
| `REFERENCE_ASSET_NOT_IN_SOURCE_SNAPSHOT` | 72 |
| `REFERENCE_EMBEDDED_USD_SNAPSHOT_FORMULA` | 198 |
| `REFERENCE_MIXED_STATIC_AND_FORMULA_INPUT` | 12 |
| `REFERENCE_STATIC_MANUAL_INPUT` | 349 |
| `UNEXPLAINED_FORMULA_OR_AGGREGATE_CONTRADICTION` | 1 |

## Decision status

| Status | Cells | Meaning |
| --- | ---: | --- |
| `KHONG_THE_XAC_DINH_TU_DU_LIEU` | 73 | Supplied data lacks the asset register or row-level explanation needed to decide. |
| `LA_NGOAI_LE_NHAP_TAY_HOAC_TANG_KHAC` | 361 | Reference is manual/another layer; preserve it as an exception and do not overwrite it. |
| `MAU_THUAN_CAN_NGHIEP_VU_DUYET` | 200 | Two source snapshots conflict; business must choose the governing snapshot/policy. |
| `XAC_DINH_TU_BANG_CHUNG` | 4 | Evidence proves the policy outcome; code may follow that policy, not the submitted reference. |

## Controls before accounting changes

1. The matrix proves every cell has source and reference provenance, but only `XAC_DINH_TU_BANG_CHUNG` is eligible for a policy fix without a business decision.
2. The 222 `ROUNDING_ORDER` cells are outside this matrix because their cause is already proven: round per asset before aggregation.
3. Do not encode a reference snapshot, static manual amount, cost center, account, period, FX rate, filename, sheet, or FORM row as a fallback.
4. Keep `FA-OPEN` open until the business decisions and a post-fix comparator are complete.

## Artifact

- `docs/audits/fixed_assets_true_mismatch_decision_matrix_2026-07-16.csv` contains every monthly cell, both values, delta, source L/P/Q/V/W, reference row/formula, classification, decision, and allowed action.
