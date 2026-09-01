# Tasks: AI Operations Assistant (Read-only MVP)

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contract](contracts/operational-case-v1.md), [quickstart](quickstart.md)  
**Safety boundary**: These tasks build a local, read-only support assistant. They do not implement model connectivity, automatic repair, source/workbook writes, pipeline execution, configuration edits, or release/update work.

## Gemini Flash Safety Envelope

Prepend this block to every Gemini task:

```text
You are working on MP2027. Read AGENTS.md and the exact task first.
Do only this one task; do not broaden scope. Preserve all unrelated edits.
Do not create/search/use signing keys, credentials, or external AI calls.
Do not alter Excel/CSV inputs, output workbooks, project.json, release/update files, or business rules.
Before editing: report git status and the exact files you will change.
After editing: run only the task's tests plus compile check when Python changes.
Do not commit or push. Report changed files, test output, and residual risks.
If evidence is missing or the task would require a write-capable action, stop and report the blocker.
```

## Phase 1: Planning Gate (no product code)

**Purpose**: Ensure that implementation begins from an agreed, safe boundary.

- [x] T001 Review `specs/002-ai-operations-assistant/spec.md` and `plan.md`; create `docs/operations/ai_operations_assistant_scope.md` stating the MVP is local-only/read-only and that automated repair is excluded.
- [x] T002 [P] Verify existing evidence formats in `src/services/run_history.py`, `scripts/run_e2e.py`, and fixture tests; record exact JSON/SQLite fields consumed by the MVP in `specs/002-ai-operations-assistant/contracts/operational-case-v1.md` without changing runtime code.
- [x] T003 [P] Create a CI-safe test fixture plan in `tests/services/test_operations_case_service.py` that uses only temporary `RUN_HISTORY` folders and no raw Excel/company data.

**Checkpoint**: A reviewer can approve the exact evidence boundary before service code is written.

## Phase 2: Foundational Read-only Case Service

**Purpose**: Build and test a service that can only read evidence for the selected run.

- [x] T004 Create immutable `OperationalCase` and `EvidenceReference` data classes in `src/services/operations_case_service.py` matching `specs/002-ai-operations-assistant/data-model.md`; add focused constructor tests in `tests/services/test_operations_case_service.py`.
- [x] T005 [P] Add a path-boundary validator in `src/services/operations_case_service.py` that rejects missing paths and paths outside the selected run workspace; test valid, missing, traversal, and mismatched-FY paths in `tests/services/test_operations_case_service.py`.
- [x] T006 Add a read-only history-catalog lookup in `src/services/operations_case_service.py` that retrieves exactly one existing terminal run; test unknown run ID and non-terminal run rejection in `tests/services/test_operations_case_service.py`.
- [x] T007 Add loaders for `run_manifest.json`, `reports/preflight_report.json`, `reports/pipeline_stage_evidence.json`, and `reports/failure_traceback.txt` in `src/services/operations_case_service.py`; represent absent files as visible missing evidence and add fixture tests.
- [x] T008 Assemble a complete unclassified `OperationalCase` from selected-run evidence in `src/services/operations_case_service.py`; test FY, CC scope, run ID, status, stage, and evidence ordering.
- [x] T009 Add a strict no-write regression test in `tests/services/test_operations_case_service.py` that verifies catalog/workspace file hashes are unchanged after case assembly.

**Checkpoint**: A local test can open a selected run case without changing one byte of its evidence.

## Phase 3: Deterministic Knowledge and Safe Guidance (User Story 1)

**Goal**: Explain a small number of known failures without a live model.

**Independent Test**: A fixture for each known class produces a confirmed, evidence-cited explanation; an unmatched fixture remains unknown.

- [x] T010 Create `src/services/operations_knowledge.py` with immutable `KnowledgeEntry` records, review status, evidence conditions, and approved structured VI/EN/JA content: title, what happened, why it happened, what to do, confidence label, evidence label, and technical-details label. Primary content must be plain operational language, not raw exceptions/logs. Add tests in `tests/services/test_operations_knowledge.py`.
- [x] T011 [P] Define the first approved class for missing staffing/baseline evidence in `src/services/operations_knowledge.py`; give it complete plain-language VI/EN/JA guidance and add positive and negative match tests in `tests/services/test_operations_knowledge.py`.
- [x] T012 [P] Define the first approved class for blocked output publication (for example an Excel/Windows file lock) in `src/services/operations_knowledge.py`; give it complete plain-language VI/EN/JA guidance and add positive and negative match tests in `tests/services/test_operations_knowledge.py`.
- [x] T013 [P] Define the first approved class for preflight source validation failure in `src/services/operations_knowledge.py`; give it complete plain-language VI/EN/JA guidance and add positive and negative match tests in `tests/services/test_operations_knowledge.py`.
- [x] T014 Integrate strict knowledge matching into `src/services/operations_case_service.py`; require every confirmed answer to include its matching evidence and tested conditions while keeping raw technical evidence separate from its primary guidance presentation.
- [x] T015 Add unknown/ambiguous fallback guidance in `src/services/operations_case_service.py`; provide complete, plain-language VI/EN/JA wording that says the cause is unconfirmed and offers no fix command.
- [x] T016 Add a multilingual presentation-contract test across `tests/services/test_operations_case_service.py` and `tests/services/test_operations_knowledge.py`: each VI/EN/JA known and unknown result has every required primary section, no untranslated UI key, and no raw exception/JSON/internal field used as its main explanation.

**Checkpoint**: The assistant can give trustworthy help for three approved errors and safely declines to guess for everything else.

## Phase 4: Read-only User Interface (User Story 2)

**Goal**: Let a user open an evidence-backed case from the existing run-history screen.

**Independent Test**: From a selected fixture run, a user can open one assistant window, see evidence and guidance in the active language, and cannot invoke any write/run action.

- [x] T017 Add only the required localized labels/messages for the read-only assistant to `src/services/i18n.py` (or its active translation resources) in Vietnamese, English, and Japanese; add/update `tests/test_i18n.py` to prove no active-language label is missing.
- [x] T018 Create a presentation-only `OperationsAssistantDialog` in `src/ui/operations_assistant.py` that receives an already-built `OperationalCase` and the active application language; add rendering tests in `tests/ui/test_operations_assistant.py` using fake widgets only.
- [x] T019 Render the plain-language primary sections (what happened, certainty, affected scope, safe next steps), then a separately labelled evidence list and optional technical details in `src/ui/operations_assistant.py`; ensure missing evidence is visibly labelled and unknown guidance cannot look confirmed.
- [x] T020 Add a singleton-window guard to `src/ui/operations_assistant.py` or the owning controller; test repeated open requests reuse the existing dialog.
- [x] T021 Add one "Trợ lý xử lý lỗi" action only to the selected-run path in `src/universal_app.py`; it must build a case through the service and must not re-run, alter, or reopen the pipeline.
- [x] T022 Add UI integration tests in `tests/ui/test_operations_assistant.py` proving the localized action is disabled/no-op without a selected terminal run, the dialog follows the active VI/EN/JA language, and bad cases display a friendly evidence error rather than raw technical text.
- [x] T023 Add a regression assertion in `tests/ui/test_operations_assistant.py` that the dialog exposes no write, save-source, run-pipeline, apply-fix, or automatic-repair command.

**Checkpoint**: A user can safely obtain local support guidance from one selected run in Vietnamese, English, or Japanese.

## Phase 5: Operational Documentation and Acceptance

**Purpose**: Make the MVP supportable by people and future AI work.

- [x] T024 Update `docs/operations/ai_operations_assistant.md` with the user workflow, language policy, plain-language/technical-details separation, evidence limits, confidence meanings, three supported errors, unknown-error path, and explicit non-capabilities.
- [x] T025 [P] Update `docs/handover/code_walkthrough.md` and `docs/architecture/feature_registry.md` with the new read-only service/UI and its test evidence.
- [x] T026 Run the CI-safe focused suite named in this feature plus `py -3 -m compileall -q src`; record passed commands and unrun acceptance checks in `specs/002-ai-operations-assistant/quickstart.md`.
- [ ] T027 Perform a human acceptance review with one known failure and one unknown failure; record outcome and any rejected guidance in `docs/operations/ai_operations_assistant.md` without adding real company logs to Git.

## Explicitly Deferred: Future Autonomous-Repair Feature

Do not give these tasks to Gemini under this feature. They require a separate approved spec and a security/business review.

- [ ] AR001 Define which data, if any, may leave the workstation; choose provider, retention, credentials, and opt-in policy.
- [ ] AR002 Design a repair proposal format with exact file scope, preview, owner authority, and mandatory human confirmation.
- [ ] AR003 Design backup, rollback, conflict detection, and Excel/database validation for each permitted repair type.
- [ ] AR004 Create a benchmark of confirmed operational cases and measure model accuracy, hallucination rate, unsafe-action rate, and multilingual quality.
- [ ] AR005 Permit only sandboxed, reversible repair simulations before any production write capability.

## Dependencies and Safe Execution Order

`T001 → T002/T003 → T004–T009 → T010–T016 → T017–T023 → T024–T027`.

Tasks marked `[P]` can be delegated in parallel only after their prerequisite checkpoint is accepted. Gemini Flash should receive one unchecked task at a time, never an entire phase. Stop after every checkpoint for human review.
