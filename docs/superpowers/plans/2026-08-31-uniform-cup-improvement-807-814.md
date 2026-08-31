# Uniform and Cup Improvement 807-814 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allocate the approved 807-814 uniform and cup costs only for cost centers 1412000044, 1412000056, and 1412000088.

**Architecture:** Keep the current workbook-driven entitlement matrix as the source for its existing columns. Add two allocation-rule identities which are intentionally not source-backed, then overlay a narrowly-scoped approved amendment at allocation time. The overlay carries a fixed Excel provenance so audit rows remain traceable and does not alter other centers or raw source files.

**Tech Stack:** Python 3.13, SQLite, pytest, openpyxl.

---

### Task 1: Define source compatibility and approved entitlement amendment

**Files:**
- Modify: `src/engine/uniform_cup_rules.py`
- Modify: `src/db/loader.py`
- Test: `tests/test_uniform_cup_allocation.py`

- [x] Add a failing test proving the current loader needs only the 16 source-backed columns and that exact amendment data is limited to the three approved centers.
- [x] Add non-source-backed rule specs `safety_shoes_type_1` (one per hire) and `electrostatic_white_hat` (two per hire), matching the existing allocation rule names.
- [x] Add a pure amendment helper that removes `color_hat` for `1412000044`, adds the two new items and cup for `1412000044`, and adds cup only for `1412000056` and `1412000088`; synthetic rows must use source file, sheet, and cell range from the specification.
- [x] Change entitlement loader header validation and iteration to use only source-backed specs.
- [x] Run the new focused test and `pytest tests/test_uniform_cup_allocation.py -q`.

### Task 2: Apply the amendment to allocation and verify cost behavior

**Files:**
- Modify: `src/engine/allocator.py`
- Test: `tests/test_uniform_cup_allocation.py`

- [x] Add failing allocation tests for CC 1412000044 proving no colour-hat allocation, type-1 shoe and electrostatic-hat quantities, worker-only new-hire cup, periodic cup placeholder, and amendment provenance.
- [x] Add scope tests proving the amendment grants cup to 1412000056/1412000088 but no unrelated center.
- [x] Call the amendment helper inside `_effective_uniform_entitlements` after the existing role-split-hat logic.
- [x] Run the focused tests and preserve existing cup, shirt, role-split, and source-import behavior.

### Task 3: Audit, accept, and close the register entries

**Files:**
- Modify after acceptance: `C:\Users\Admin\Downloads\Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx`

- [x] Run `py -3 -m pytest tests/test_uniform_cup_allocation.py tests/test_posting_month_logic.py tests/test_complete_v1_source_order_writer.py tests/test_gui_bus_passenger_inputs.py tests/test_i18n.py tests/test_gui_dynamic_localization.py tests/test_user_guide_search.py -q` in groups if runner limits require it.
- [x] Run `py -3 -m py_compile src/engine/uniform_cup_rules.py src/db/loader.py src/engine/allocator.py` and `git diff --check`.
- [x] Inspect the output/audit assertions; only after all pass, apply solid green fill to rows 807 through 814 in sheet `Hạng mục cần cải tiến`, save the supplied workbook, and reopen it to confirm the fills persist.
- [x] Commit and push the source, tests, specification, and plan in one focused commit. The accepted workbook is user-supplied outside the repository and remains at its supplied Downloads path with a side-by-side backup.
