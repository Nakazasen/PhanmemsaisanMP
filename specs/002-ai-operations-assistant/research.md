# Research: AI Operations Assistant

## Decision 1: Use existing run workspaces as the evidence boundary

**Decision**: A case may read only the workspace for the selected run and its matching entry in `run_history.db`.

**Rationale**: `src/services/run_history.py` already creates a per-run workspace, immutable terminal status, a run manifest, and `reports/pipeline_stage_evidence.json`. Existing reports include preflight evidence and failure traceback where applicable.

**Alternatives considered**:

- Search arbitrary folders: rejected because it can mix FY/CC evidence and expose unrelated files.
- Re-run preflight automatically: rejected because an assistant must first explain the selected historical evidence without changing state.

## Decision 2: Start with deterministic knowledge, not a live LLM

**Decision**: The MVP matches a small reviewed error taxonomy and renders approved steps.

**Rationale**: A deterministic catalog is testable, multilingual, local-only, and safe for financial operations. It also creates a benchmark for any later model.

**Alternatives considered**:

- Send logs straight to a cloud LLM: rejected until business-data sharing, retention, provider, credentials, and evaluation are approved.
- Let a model infer repairs from raw logs: rejected because an unsupported conclusion must remain explicitly unconfirmed.

## Decision 3: Keep immutable evidence and human notes separate

**Decision**: Future resolution notes are separate reviewed records keyed to a run/case; the run evidence is never overwritten.

**Rationale**: This preserves auditability and makes it clear whether a repair is confirmed or only a user observation.

## Decision 4: Treat auto-repair as a separate product boundary

**Decision**: No repair command is planned in this feature.

**Rationale**: Automatic changes require authority, explicit scope, preview, confirmation, backup, rollback, and regression evidence. These controls must be designed before any write-capable agent is introduced.
