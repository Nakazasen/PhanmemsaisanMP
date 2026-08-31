# G6 to G5 transition handling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users record G6-to-G5 internal transfers so only the residual
staff increase is charged as a new hire.

**Architecture:** Store FY/CC/month transition counts in a dedicated manual
input table.  Copy that table into each immutable run along with the existing
manual-input contract.  Centralize the subtraction in the new-hire count
helpers so only new-hire rules change; ordinary headcount and other drivers
continue using canonical source data unchanged.

**Tech Stack:** Python 3, SQLite, Tkinter, pytest.

---

### Task 1: Persist the explicit transition input

**Files:** `src/db/schema.py`, `src/services/manual_staffing_overrides.py`

- [x] Add `fact_manual_g6_to_g5_transition(period, cc_code, fiscal_year,
  transition_count, description, updated_at)` with a per-period/CC primary key.
- [x] Add it to the FY-scoped manual-input copy contract, so it is copied only
  from the selected FY store to the isolated run database.
- [x] Add a service helper that validates a complete FY-month mapping (blank
  is zero; negative/non-integer input is rejected) and replaces only this
  CC/FY's rows atomically.

### Task 2: Make the manual UI editable and durable

**Files:** `src/universal_app.py`, `src/services/i18n.py`

- [x] Add a `g6_to_g5` StringVar for each month and a localized column header.
- [x] Load saved values from the manual store without modifying source
  headcount fields.
- [x] Save the validated FY-month values via the service helper in the same
  transaction as the existing manual-input save.

### Task 3: Adjust only new-hire allocation

**Files:** `src/engine/allocator.py`

- [x] Add a private lookup for a run-database transition count.  Missing rows
  return zero, preserving legacy results.
- [x] Add a helper that returns adjusted staff new hires:
  `max(0, event_staff_delta - transition_count)`.
- [x] Route all new-hire paths through it: generic staff/all driver, uniform
  new-hire counts, and recruitment-health counts.  Leave worker deltas and
  all non-new-hire paths untouched.

### Task 4: Tests and audit

**Files:** `tests/test_headcount_and_export.py`,
`tests/test_gui_baseline_recovery.py`, `tests/test_gui_dynamic_localization.py`

- [x] First add failing tests for persistence/copy and the three allocation
  paths.  Run only those tests and observe failure before implementation.
- [x] Add regression assertions that omitted/zero transition input produces
  the old result and an ordinary headcount rule remains unmodified.
- [x] Run focused tests, relevant GUI/i18n tests, `py_compile`, and
  `git diff --check`; run the full suite if time permits and report unrelated
  failures separately.

### Task 5: Acceptance workbook and delivery

**Files:** user workbook only after all code/test checks pass.

- [x] Copy the source workbook to a side-by-side pre-acceptance backup.
- [x] Use Excel COM (not openpyxl save) to fill rows 820–835 green, then
  read back the fills without saving.
- [x] Commit and push all scoped changes after final review.
