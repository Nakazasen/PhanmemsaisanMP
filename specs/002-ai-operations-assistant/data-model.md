# Data Model: C-AGENT Operations Guidance

The existing `OperationalCase`, `EvidenceReference`, `KnowledgeEntry`, and `GuidancePresentation` remain the local authoritative model. The following types are additive and must never mutate an `OperationalCase` or its evidence.

## CagentProviderPolicy

| Field | Meaning | Validation |
|---|---|---|
| enabled | Whether company AI requests are allowed on this deployment | `False` by default |
| endpoint_url | Deployment-supplied C-AGENT endpoint | HTTPS URL; no UI entry/persistence |
| auth_mode | Approved authentication method | `none` or `bearer_env` only (v1 strict allow-list) |
| timeout_seconds | Maximum client wait | Integer 1–60; default 60 |
| data_policy_id | Company approval reference | Non-empty whenever `enabled=True` |
| allowed_packet_version | Packet contract accepted by C-AGENT | Exact contract version |

The policy contains no secret value. A token, if required, is read from the deployment environment or OS secret facility at call time and is never rendered, logged, serialised, or added to a test fixture.

## CagentGuidancePacket

| Field | Meaning | Validation |
|---|---|---|
| packet_version | Contract version | `cagent-guidance/v1` |
| packet_id | Ephemeral request correlation ID | Generated in memory; not a run ID |
| case_context | FY, CC scope, terminal status, stage, classification, confidence | Values copied from the selected local case only |
| local_guidance_summary | Existing approved plain-language summary | Bounded text |
| evidence_items | `SafeEvidenceItem` and selected-run technical evidence records | Verified only; each gets an opaque ordinal such as `E1` |
| question | Fixed operational question template in active language | No free-text in v1 |
| language | `vi`, `en`, or `ja` | Must match the active UI language |

## SafeEvidenceItem

| Field | Meaning | Validation |
|---|---|---|
| evidence_id | Packet-local `E1`, `E2`, ... | Opaque; never derived from file name/path |
| type | Coarse evidence type | Allow-listed type only |
| summary | Short approved statement | Bounded; may be accompanied by a selected-run technical excerpt |
| verification | `verified` only | Missing/mismatch evidence is omitted |

## CagentGuidanceResult

| Field | Meaning | Validation |
|---|---|---|
| status | `ready`, `unavailable`, `rejected`, `failed`, or `timed_out` | UI state, not persisted |
| provider_label | Localised `C-AGENT (company service)` | Fixed label; no user-supplied URL |
| answer | Bounded plain-language advisory text | Removes control characters, secrets, paths, and prohibited action claims |
| cited_evidence_ids | Evidence IDs returned/recognised in answer | Must be subset of packet IDs |
| limitation | Localised disclosure when result is incomplete/unavailable | Always present |
| request_started_at | In-memory timing metadata | Never written into run history |

## CompanyInternalEvidence (implemented in T030)

| Field | Meaning | Validation |
|---|---|---|
| evidence_id | Packet-local opaque ID | Unique within packet |
| type | Run-manifest, stage report, preflight report, failure traceback, or catalog evidence | Allow-listed type only |
| selected_run_path | Location of evidence in the selected run workspace | Must resolve inside that workspace |
| locator | Relevant line range or report section | Bounded |
| excerpt | Technical content needed for diagnosis | Bounded per item and total packet budget |
| verification | `verified` only | Missing/mismatch evidence is omitted |

## GeminiPublicExperimentRequest and Result

`GeminiPublicExperimentRequest` contains exactly one `scenario_id` from the built-in allow-list and a fixed fictional prompt. It has no run, history, file, free-text, image, or clipboard field. Its result carries `status`, bounded `answer`, `provider_label`, and the fixed public-data warning.

## State Rules

- An `OperationalCase` is constructed locally before any provider state exists.
- Only an explicit user action can create a C-AGENT packet; opening a dialog creates none.
- C-AGENT failure does not change local confidence/classification or invoke another provider.
- Provider answers are advisory display state only and vanish when the dialog closes.
- Gemini experiment state cannot reference `OperationalCase` or be reachable from the C-AGENT failure path.
- Neither provider model has a write, run, repair, save, configuration, history, or export operation.
