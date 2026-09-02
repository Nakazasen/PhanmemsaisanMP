# Data Model: Reliable March Baseline Recovery

## March Baseline State

| State | Meaning | May April Recovery Replace It? |
|---|---|---|
| `valid_confirmed` | Complete March values with current explicit confirmation or an earlier approved-April provenance | No |
| `legacy_unconfirmed_zero` | Historic manual UI March row where all staffing components are zero and no current explicit confirmation exists | Yes, only after user approval |
| `missing` | No March baseline exists for the selected cost center | Yes, only after user approval and valid April source |
| `invalid_other` | March data is incomplete, negative, or inconsistent | No; user must correct it manually |

## April Recovery Candidate

| Field | Rule |
|---|---|
| Fiscal year | Must equal the active fiscal year |
| Cost center | Must exactly equal the March baseline target |
| Staffing components | Total, expatriate, staff, worker, and local total must be present, non-negative, and internally balanced |
| Provenance | Retain the reviewed source file and worksheet on the resulting March record |

## Recovery Outcome

| Field | Meaning |
|---|---|
| `cc_code` | Affected cost center |
| `status` | `recovered`, `already_valid`, or `unresolved` |
| `reason` | User-displayable explanation when unresolved |
| `baseline_provenance` | Explicit approved-April marker for recovered rows |

## Relationships

- A selected scope has one recovery outcome per selected cost center requiring a March baseline.
- A recovery candidate can only supply the March baseline for its exact same cost center.
- Calculation is eligible only when every selected cost center is `valid_confirmed` after any recovery action.
