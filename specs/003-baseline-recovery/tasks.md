# Tasks: Reliable March Baseline Recovery

**Input**: Design documents from `/specs/003-baseline-recovery/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [recovery UI flow](contracts/recovery-ui-flow.md)

**Tests**: Required. This repair is for a reproducible financial-input defect and must add regression coverage before implementation.

## Phase 1: Reproduction and Foundation

**Purpose**: Capture the historical data shape and the selected-scope contract before changing recovery behavior.

- [x] T001 Add failing legacy-zero and confirmed-zero classification/recovery tests in `tests/test_gui_baseline_recovery.py`.
- [x] T002 Add failing mixed-scope recovery tests proving one unavailable source cannot prevent same-CC April recovery for other selected codes in `tests/test_gui_baseline_recovery.py`.
- [x] T003 Add failing selected-scope readiness and manual-editor target-selection tests in `tests/test_template_validation.py` and `tests/test_gui_baseline_recovery.py`.

**Checkpoint**: Tests demonstrate the exact historical failure without modifying real FY2027 runtime databases.

---

## Phase 2: User Story 1 - Recover one blocked cost center (Priority: P1) 🎯 MVP

**Goal**: Explicit April approval repairs an absent or legacy-unconfirmed zero March baseline for the same code without overwriting a valid one.

**Independent Test**: A memory/temporary database with the `MANUAL_GUI` zero shape and a valid same-CC April row becomes valid after recovery; confirmed baselines remain unchanged.

- [x] T004 [US1] Implement explicit baseline-state classification and safe legacy-zero replacement in `src/services/manual_staffing_overrides.py`.
- [x] T005 [US1] Return per-cost-center recovery results and preserve source provenance in `src/services/manual_staffing_overrides.py`.
- [x] T006 [US1] Integrate the result into the single-cost-center April recovery dialog and log only actual recoveries in `src/universal_app.py`.

**Checkpoint**: CC 1412000006-style data can recover in one explicit action, and valid manual values remain protected.

---

## Phase 3: User Story 2 - Recover multiple cost centers without collateral failure (Priority: P2)

**Goal**: Mixed selections recover each usable code and name every unresolved code instead of falsely reporting all April data missing.

**Independent Test**: A selection containing recoverable and unavailable April sources produces recovered and unresolved outcomes in the same action.

- [x] T007 [US2] Change selected-source recovery orchestration to load reviewed candidates without all-or-nothing required-code gating in `src/universal_app.py`.
- [x] T008 [US2] Add localized recovered/unresolved summaries and keep the recovery dialog actionable while selected codes remain unresolved in `src/services/i18n.py` and `src/universal_app.py`.

**Checkpoint**: A missing source such as CC 1412000070 does not block recovery of unrelated valid sources.

---

## Phase 4: User Story 3 - Understand readiness and enter data in the correct place (Priority: P3)

**Goal**: The current selected scope explains its March-baseline requirement before Run, and manual staffing opens on the correct code.

**Independent Test**: One selected invalid code produces a baseline-required readiness message and opens the editor on that code.

- [x] T009 [US3] Add selected-scope missing-baseline state to preflight summary and workflow guidance without changing the reusable source-preflight contract in `src/universal_app.py` and `src/services/i18n.py`.
- [x] T010 [US3] Pass the sole main-window cost-center selection into the manual staffing editor while preserving chooser behavior for zero or multiple selections in `src/universal_app.py`.
- [x] T010a [US3] Log a successful manual staffing save with its affected cost-center code in `src/universal_app.py`.

**Checkpoint**: The user no longer sees an unconditional ready-to-run message or an unrelated initial cost center.

---

## Phase 5: Verification and Handover

**Purpose**: Validate the repair across data safety, UI flow, and existing feature behavior.

- [x] T011 Update the recovery validation procedure and known historical-data behavior in `specs/003-baseline-recovery/quickstart.md`.
- [x] T012 Run focused regression, CI-safe relevant tests, compile validation, and `git diff --check`; record the exact results in `specs/003-baseline-recovery/tasks.md`. (2026-09-02: 188 passed, 11 subtests; compile and diff checks passed.)

## Dependencies & Execution Order

- T001–T003 must complete before implementation.
- T004–T006 implement and validate the P1 single-CC path.
- T007–T008 depend on T005 because they consume per-CC outcomes.
- T009–T010 can follow T003 and are completed after the data-recovery behavior is stable.
- T011–T012 are last and require all implementation tasks.

## Parallel Opportunities

- T001 and T003 may proceed in parallel because they cover separate test contracts.
- T009 and T010 may proceed in parallel after their tests exist, but both change `src/universal_app.py` and must be merged sequentially.

## Implementation Strategy

1. Reproduce the legacy-zero contradiction in a temporary database.
2. Implement the smallest service-level replacement rule and prove that it preserves confirmed data.
3. Make multi-CC recovery independent per code.
4. Align the desktop guidance and editor target with the same selected scope.
5. Run focused and CI-safe regression suites before declaring the repair complete.
