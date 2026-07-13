# Phase 42N1Y-A - Bulk Gap Reducer Blocker

## Classification

`WARNING_PHASE_42N1Y_A_NO_LARGE_IMPLEMENTABLE_CLUSTER`

## Scope

This phase tried to reduce the remaining MP2027 file-order v1 gap by finding the
largest primary-driven row cluster with enough source evidence to implement
safely.

No code was changed. No full pytest was run. No package was created. No commit
was made.

## Counts

| Workbook | Business rows |
|---|---:|
| Generated v1 | 141 |
| Primary reference | 277 |
| Current count gap | 136 |

The row-count gap is the release-readiness gap: `277 - 141 = 136`.

## Top primary-driven candidate clusters

These clusters are candidates for reducing the remaining gap. They are grouped by
account/code, contiguous primary blocks, description family, and likely source
family. They are not implemented yet.

| cluster_id | row_count | primary_row_range | account/code samples | description samples | likely source workbook | evidence_found | implementable_now | reason |
|---|---:|---|---|---|---|---|---|---|
| C1 | 75 | 56-130 | `5005026371` | `Vendor用Micro SD`; `湿度計`; `ノートPCのRAM`; `Master用DVD` | Fixed Assets / detail source candidates | PARTIAL | NO | Largest cluster, but evidence is broad/fuzzy. No one-to-one source row/cell and Apr-Mar monthly mapping for all 75 rows. |
| C2 | 29 | 268-296 | `5004086291` | `昼食事の差異`; `誕生日会`; `制服`; welfare/event rows | Birthday / welfare / event source candidates | PARTIAL | NO | Some related source families exist, but exact row/cell/month placement for the cluster is not proven. |
| C3 | 21 | 162-182 | `5005046281` | `Flash Programmer`; `FP-10予備`; `治具PC用`; `半田ゴテ` | Fixed Assets / tools detail candidates | PARTIAL | NO | Related item text appears in source scans only as partial/fuzzy evidence; monthly values cannot be generated without guessing. |
| C4 | 13 | 132-144 | `5005116291` | `Partnerタクシー代`; `宿泊出張費`; `出張食事代` | Allocation workbook metadata | PARTIAL | NO | Allocation metadata exists, but actual monthly travel events/counts by output row are not identified. |
| C5 | 13 | 215-227 | `5005246286` | `清掃費`; `パスポート更新経費`; `労働許可証取得費用` | `総務課` + allocation workbook | PARTIAL | NO | Some Admin source rows exist, but the block mixes concepts and requires headcount/event logic not proven for every primary row. |
| C6 | 10 | 146-155 | `5005116292` | `AIR代(日本出張)`; `日当`; `宿泊費`; `保険代` | Allocation workbook metadata | PARTIAL | NO | Source has allocation rules, not the exact monthly event source for each primary row. |

## Chosen cluster

No cluster was implemented.

The largest cluster (`C1`, 75 rows, mostly account `5005026371`) is the best
bulk-reduction candidate by size, but it is not safe to generate now.

## Non-technical blocker reason

The primary workbook has many detailed lines that look like real business items,
for example consumables, tools, repairs, travel, cleaning, and admin fees. The
repo sources contain some related words and account codes, but for the large
clusters the evidence is not complete enough to know exactly which source row,
month, and amount should be copied into each output row.

Implementing these rows now would require guessing. Even if done manually, the
operator would need a source table that says, for each primary line:

1. source workbook name,
2. sheet name,
3. source row/cell,
4. account code,
5. cost center `1412000040`,
6. Apr-Mar monthly values or formulas,
7. output placement/order.

That complete mapping was not found for any cluster of at least 10 rows.

## Evidence checked

Inputs compared:

- `dist/phase42n1w_auto_file_order_v1_rc/OUTPUT_FY2027/MP_CC_1412000040.xlsx`
- `reference_outputs/primary/16.KDTVN 電気製造技術課_MP FY2027_各予定(Ver01).xlsx`

Sources searched:

- `raw/`
- `raw/requirements/`
- `docs/MP2027/`

Audits used:

- `docs/audits/phase42n1w_auto_file_order_v1_rc_check.md`
- `docs/audits/phase42n1x_a_file_order_v1_release_readiness.md`
- `docs/audits/phase42n1q_a_missing_row_gap_breakdown.md`
- `docs/audits/phase42n1s_a2_raw_source_full_scan.md`

## What would be needed next

For a large safe reduction phase, start with one focused reconciliation:

1. Fixed Assets/detail cluster around account `5005026371` and rows `56-130`.
   Match by asset/item text, account, cost center, and monthly amount.
2. Admin/travel allocation clusters around accounts `5005246286`, `5005116291`,
   and `5005116292`. Identify the real monthly event/count source, not only the
   allocation master metadata.
3. Fixed Assets transition rows. Reconcile against the fixed asset workbook by
   asset code and depreciation/interest monthly amounts.

## Decision

No preview/writer/export flag was added in this phase because no cluster with at
least 10 rows had sufficiently exact source-to-output evidence.

## Conclusion

`WARNING_PHASE_42N1Y_A_NO_LARGE_IMPLEMENTABLE_CLUSTER`
