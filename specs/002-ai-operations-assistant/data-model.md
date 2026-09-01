# Data Model: AI Operations Assistant

## OperationalCase

| Field | Meaning | Validation |
|---|---|---|
| case_id | Stable identifier derived from selected run and error occurrence | Non-empty; tied to one run |
| run_id | Existing run identifier | Must exist in history catalog |
| fiscal_year | FY of selected run | Must match catalog/workspace evidence |
| cost_center_scope | One CC, multiple CCs, or all | Taken from run catalog; never inferred from another run |
| status | Terminal run outcome | Existing run status only |
| stage | Failing/last known pipeline stage | Evidence-backed or `unavailable` |
| classification | Known error code/category or `unknown` | Match only approved rules |
| confidence | `confirmed`, `possible`, or `unknown` | `confirmed` requires catalog rule + evidence |
| summary | Plain-language explanation | Must not claim facts beyond evidence |
| evidence | Ordered `EvidenceReference` list | Every entry belongs to selected run |
| guidance | Ordered safe next steps | No write/run action in MVP |
| presentation | Current-language `GuidancePresentation` for a confirmed or fallback result | Preserves every required primary section for the UI; `None` only during the temporary pre-T015 unknown fallback |

## EvidenceReference

| Field | Meaning |
|---|---|
| type | Catalog row, run manifest, preflight report, stage evidence, failure trace, or approved documentation |
| local_path | Local path shown to user |
| locator | JSON key, report section, or line range when available |
| summary | Short description of what this evidence establishes |
| verification | `verified`, `missing`, or `mismatch` |

## KnowledgeEntry

| Field | Meaning |
|---|---|
| error_code | Stable error classification |
| conditions | Evidence conditions required for a confirmed match |
| translations | Approved, structured explanations in VI/EN/JA. Each language contains a title, what happened, why it happened, what to do, evidence label, technical-details label, and confidence label. |
| evidence_requirements | Evidence types that must be present |
| review_status | `approved` or `draft` |
| owner | Business/technical owner |

## GuidancePresentation

| Field | Meaning |
|---|---|
| language | Current interface language: `vi`, `en`, or `ja` |
| title | Short, non-technical statement of the issue |
| what_happened | Plain explanation of the observed result |
| why_it_happened | Evidence-backed reason, or a clear statement that the reason is not confirmed |
| what_to_do | Ordered safe manual actions a user can perform |
| confidence_label | Localized indication of `confirmed`, `possible`, or `unknown` |
| evidence_label | Localized label for source paths, run IDs, report sections, and other proof |
| technical_details_label | Localized label for optional raw log, exception, or report detail |

## ResolutionNote (future slice)

| Field | Meaning |
|---|---|
| note_id | Stable separate identifier |
| case_id | Linked operational case |
| author | Person who recorded the note |
| created_at | Timestamp |
| text | Manual outcome/observation |
| review_status | `unreviewed`, `approved`, or `rejected` |
| evidence_refs | Evidence used by the author |

## State Rules

- Run evidence is immutable after a terminal run status.
- A case is read-only and may be rebuilt from the same evidence.
- A known entry becomes `confirmed` only when all its evidence conditions match.
- A resolution note never changes case evidence or knowledge rules by itself.
- The primary presentation must use `GuidancePresentation`; raw technical evidence is supplementary and never replaces a required primary field.
