# MP2027 — Audit Lifecycle Index

As of: `2026-07-16`

> [!NOTE]
> This index changes the **lifecycle of old conclusions**, not the evidence recorded inside each audit. The authoritative active backlog is `docs/handover/CURRENT_OPEN_ITEMS.md`.

## Current evidence

| Document | Lifecycle | What remains active |
|---|---|---|
| `fixed_assets_cross_trace_audit_2026-07-16.md` | `OPEN_AUDIT` | Current quantitative successor evidence: calculation is not accepted; asset/reference ledgers separate manual layers, quantify per-asset rounding defects and retain 638 true source/reference monthly mismatches for decision-matrix review. |
| `history/fixed_assets/run_index.csv` | `LIVING_AUDIT_LOG` | Append-only index of every fixed-assets decision-matrix run. Each run preserves its CSV/Markdown evidence snapshot and is also queryable in `mp2027.db`. |
| `fixed_assets_true_mismatch_decision_matrix_2026-07-16.md` | `OPEN_AUDIT` | Current row-level successor: all 638 true mismatches have source/reference provenance and a decision status. Four terminal-continuation defects are proven; 634 remaining cells cannot be overwritten without the recorded business/source evidence. |
| `fixed_assets_policy_output_verification_2026-07-16.json` | `OPEN_AUDIT` | Production integration evidence: parser-to-source-order writer matches all 649 FY2026 and 726 FY2027 source-derived expected cells and emits zero post-terminal fact rows. It does not authorize overwriting reference manual/snapshot layers. |
| `fixed_assets_business_decision_requests_2026-07-16.md` | `OPEN_AUDIT` | Reviewer pack: condenses 273 snapshot/unknown cells into 32 actionable business requests with allowed responses and source/reference examples. |
| `FIXED_ASSETS_DEEP_AUDIT_HANDOVER_2026-07-16.md` | `OPEN_AUDIT` | Active successor: evidence-first asset ledger/decision matrix across canonical, company sources, FY2026/FY2027 references and code; implementation remains open. |
| `fixed_assets_gap_and_implementation_plan_2026-07-15.md` | `HISTORICAL` | Finding provenance only; its ask-Accounting-first workflow and `Chưa chốt` table are superseded by the deep-audit handover. |
| `phase42n3y_final_user_claims_acceptance_audit.md` | `OPEN_AUDIT` | Current successor evidence for old defects, but partial: real monthly headcount for `1412000040` and full canonical-10.07 acceptance remain open. |
| `reports/fy2027_audit_report_2026-07-13.md` | `HISTORICAL` | Mixed evidence: fixed-assets comparison remains useful; the old gas identity blocker is superseded by current fail-closed resolver/writer code, with output acceptance still open. |
| `docs/handover/ui_not_responding_clean_form_handover.md` | `IMPLEMENTED_PENDING_ACCEPTANCE` | One current Windows GUI acceptance/reproduction with stack capture if still frozen. |

## Superseded defect audits

| Document | Lifecycle | Successor |
|---|---|---|
| `phase42n3q_post_fix_user_claims_full_audit.md` | `SUPERSEDED` | Historical chronology; N3S proved non-empty output and N3Y closed duplicate, total-headcount, Column S and reference-garbage defects. |
| `phase42n3s_reaudit_user_claims_on_nonempty_output.md` | `SUPERSEDED` | Historical chronology; N3Y records post-fix outcomes. Missing real headcount remains active under `HC-1412000040`. |
| `phase42r0_canonical_requirement_reconciliation.md` | `SUPERSEDED` | Historical 04.06-era reconciliation; canonical 10.07 workbook and current requirement mapping replace it. |
| `repo_handover_hardening_audit.md` | `HISTORICAL` | Its implementation actions are completed; data-governance review remains an open decision in the current register. |

## Historical implementation trail

The following phase reports remain useful provenance, but their “recommended next phase” sections are **not active backlog** unless linked from `CURRENT_OPEN_ITEMS.md`:

- `phase42n1*`: early source discovery, row mapping, source-order and release-readiness trail;
- `phase42n2*`: exact-source scans, reference-assisted skeleton/fill and coverage experiments;
- `phase42n3*` before N3Y: intermediate implementation/audit results;
- fixed-assets reports before 2026-07-15: inputs to the current GAP register, not independent plans.

## Disposition by topic

| Topic | Current disposition |
|---|---|
| Empty generated output | `SUPERSEDED` by later non-empty generation. |
| Duplicate new-hire formulas | `CLOSED`; real-data amount acceptance remains separate. |
| Total-headcount fallback | `CLOSED`; real-data amount acceptance remains separate. |
| Column S descriptions | `CLOSED` in N3Y evidence. |
| Reference-fill garbage at/after row 213 | `CLOSED` in N3Y evidence. |
| One blank row between written blocks | `CLOSED`; scoped to populated blocks. Missing blocks are input/coverage work, not spacing defects. |
| Bus JP/VN flow | `CLOSED` as generic event backlog; now a dedicated driver flow. |
| Gas identity/export blocker | `SUPERSEDED` as the old identity defect: current account+token resolution fails closed and writes to the resolved row. Regression tests define row-46/native-parser expectations but currently stop at the FY2027 headcount guard before gas assertions; output acceptance remains under `OPEN_AUDIT`. |
| Fixed assets | `OPEN_AUDIT`; governed by `docs/handover/FIXED_ASSETS_DEEP_AUDIT_HANDOVER_2026-07-16.md`. The 15 July GAP plan remains provenance, not the active decision workflow. |
| GUI not responding | `IMPLEMENTED_PENDING_ACCEPTANCE`; no current manual evidence closes it. |
| 04.06 / 09.06 requirement conclusions | `HISTORICAL`; neither overrides canonical 10.07. |

## Maintenance rule

When a newer audit resolves an older finding:

1. preserve the old report unchanged except for a short status banner if needed;
2. add the successor here;
3. update `CURRENT_OPEN_ITEMS.md`;
4. never copy every historical recommendation into the live handover.
