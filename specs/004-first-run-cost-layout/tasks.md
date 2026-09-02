# Tasks: First-run Cost Layout

**Input**: Design documents from `/specs/004-first-run-cost-layout/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/source-classification.md

**Tests**: Required. This is an output-stage defect affecting the first financial calculation.

## Phase 1: Reproduce and Classify

- [x] T001 Add a failing current-output/no-signal first-run classification test in `tests/test_manual_special_cost_sections.py`.
- [x] T002 Add failing preservation-signal tests for explicit legacy start and saved special-cost metadata in `tests/test_manual_special_cost_sections.py`.

## Phase 2: User Story 1 - Run original form (P1)

**Goal**: An original or common-cost-only output does not impose a legacy row marker before the first calculation.

- [x] T003 [US1] Add a reusable per-CC preservation-signal helper in `src/engine/manual_special_cost_sections.py`.
- [x] T004 [US1] Classify unmarked current output as `new_fiscal_year` before staging in `scripts/run_e2e.py`.

## Phase 3: User Story 2 - Preserve known layouts (P2)

**Goal**: Existing metadata, saved order, and explicit legacy configuration continue to restore user-owned special-cost content.

- [x] T005 [US2] Retain known-layout staging paths and malformed-metadata failure behavior in `scripts/run_e2e.py` and `src/engine/manual_special_cost_sections.py`.

## Phase 4: Verification

- [x] T006 Run focused output-layout regressions, CI-safe relevant tests, compile validation, and `git diff --check`; record results in `specs/004-first-run-cost-layout/quickstart.md`. (2026-09-02: 65 passed; compile and diff checks passed.)

## Dependencies

- T001-T002 before T003-T005.
- T003 before T004.
- T004-T005 before T006.
