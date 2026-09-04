# Tasks: So Sánh Biến Động Chi Phí MP Giữa Các Năm

**Input**: Design documents from `specs/001-yoy-cost-variance/`

**Prerequisites**: plan.md, spec.md, data-model.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create `src/engine/variance_analyzer.py` file with basic structure
- [x] T002 Create `src/ui/tabs/variance_tab.py` file with basic structure
- [x] T003 Create `src/utils/excel_variance_writer.py` file with basic structure
- [x] T004 Create `tests/engine/test_variance_analyzer.py` for unit tests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Define `ComparisonContext`, `CostLineVariance`, and `VarianceReport` data classes in `src/engine/variance_analyzer.py`
- [x] T006 Setup basic `openpyxl` / `pandas` data loading utility function to read MP FORM files safely (read-only mode) in `src/engine/variance_analyzer.py`

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - So sánh đối chiếu biến động chi phí của 1 phòng ban / Cost Center (Priority: P1) 🎯 MVP

**Goal**: Đọc 2 file MP, ánh xạ dòng chi phí, tính toán chênh lệch % và hiển thị lên giao diện UI.

**Independent Test**: Nạp 1 file MP năm nay và 1 file năm ngoái, nhấn "So sánh" và xem kết quả khớp trên Treeview.

### Tests for User Story 1

- [x] T007 [P] [US1] Write unit tests for mapping logic (Account Code + Item Name) in `tests/engine/test_variance_analyzer.py`
- [x] T008 [P] [US1] Write unit tests for percentage variance calculation edge cases (e.g., div by zero) in `tests/engine/test_variance_analyzer.py`

### Implementation for User Story 1

- [x] T009 [P] [US1] Implement mapping logic to match rows by "Mã tài khoản" and "Tên khoản mục" in `src/engine/variance_analyzer.py`
- [x] T010 [US1] Implement variance calculation ($\Delta$ absolute, $\Delta$ %) and status tagging logic in `src/engine/variance_analyzer.py` (depends on T009)
- [x] T011 [P] [US1] Build the UI layout for `VarianceTab` (file selectors, threshold inputs, action buttons) in `src/ui/tabs/variance_tab.py`
- [x] T012 [P] [US1] Build the DataGrid/Treeview in `VarianceTab` to display `CostLineVariance` records with color highlighting (Yellow/Red) based on thresholds in `src/ui/tabs/variance_tab.py`
- [x] T013 [US1] Wire up the "So sánh" button in `src/ui/tabs/variance_tab.py` to trigger the `variance_analyzer` engine and populate the Treeview
- [x] T014 [US1] Modify `src/universal_app.py` to import and mount `VarianceTab` within the main MPManager application (e.g., as a new tab or accessible from a new button in the ribbon)"

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Xuất báo cáo giải trình biến động chi phí ra bảng tính Excel (Priority: P2)

**Goal**: Xuất toàn bộ kết quả phân tích trên giao diện ra file Excel báo cáo quản trị kèm cột Ghi chú.

**Independent Test**: Nhấn nút "Xuất báo cáo", kiểm tra file Excel có đầy đủ cột, số liệu khớp UI và định dạng chuẩn.

### Tests for User Story 2

- [x] T015 [P] [US2] Write unit test for excel export structure in `tests/engine/test_variance_analyzer.py` (mocking the export path)

### Implementation for User Story 2

- [x] T016 [US2] Implement `export_variance_report(report: VarianceReport, output_path: str)` function using `openpyxl` in `src/utils/excel_variance_writer.py`
- [x] T017 [US2] Apply Excel formatting (Number formats, Percentages, Conditional Formatting colors) in `src/utils/excel_variance_writer.py`
- [x] T018 [US2] Add "Xuất báo cáo Excel" button to `VarianceTab` in `src/ui/tabs/variance_tab.py`
- [x] T019 [US2] Wire the export button to prompt for save path and call `export_variance_report`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - So sánh hàng loạt biến động cho toàn bộ danh sách phòng ban (Priority: P3)

**Goal**: So sánh tự động tất cả các file trong 2 thư mục và xuất báo cáo tổng hợp.

**Independent Test**: Chọn thư mục năm nay và năm ngoái, chạy so sánh, kiểm tra báo cáo tổng hợp.

### Implementation for User Story 3

- [x] T020 [US3] Implement directory scanning and file-pairing logic (by Cost Center code in filename) in `src/engine/variance_analyzer.py`
- [x] T021 [US3] Add batch processing method to `variance_analyzer.py` to loop through pairs and generate a combined `VarianceReport`
- [x] T022 [US3] Update `excel_variance_writer.py` to support multi-sheet or consolidated summary export
- [x] T023 [US3] Add "So sánh hàng loạt (Thư mục)" option/buttons to `VarianceTab` in `src/ui/tabs/variance_tab.py`

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T024 [P] Verify `quickstart.md` validation scenarios manually
- [x] T025 [P] Optimize Pandas Dataframe merging performance for large files in `src/engine/variance_analyzer.py`
- [x] T026 Code cleanup: ensure typing hints and docstrings are complete in `variance_analyzer.py` and `excel_variance_writer.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2)
- **User Story 2 (P2)**: Depends on User Story 1 (requires `VarianceReport` generation to export it)
- **User Story 3 (P3)**: Depends on User Story 1 (reuses core variance logic) and User Story 2 (reuses export formatting)

### Parallel Opportunities

- T007, T008 (Tests for US1) can run in parallel with T011, T012 (UI components).
- T015 (Test for US2) can run in parallel with T016 (Excel export logic).

---

## Phase 7: Correction / Hardening Plan (2026-08-17)

- [x] T027 [P0] Normalize rows and fix `acc_col + "_base"` string concat error by converting to f-strings or standardizing column names in `map_and_analyze_variances`. Add integer UI column index test in `test_variance_analyzer.py`.
- [x] T028 [P0] Fix packaged Manager startup dependency risk: either bundle pandas or use deferred import in `universal_app.py`/`variance_tab.py`. Add package smoke test (`MP2027_Manager.spec`).
- [x] T029 [P1] Aggregate duplicate keys `(account_code, item_name)` during merge in `variance_analyzer.py` so they don't multiply/inflate costs.
- [x] T030 [P1] Sanitize input data (blanks to 0, numeric check) and define sheet name reading logic explicitly.
- [x] T031 [P1] Extract Cost Center correctly using regex or explicit split in `scan_directories_and_pair_files` and handle failures without silently dropping files. Sanitize sheet names in batch export.
- [x] T032 [P2] Fix export report Excel file to use real Excel formulas for Diff and % columns, or clearly specify values. (Using formulas is better).
- [x] T034 [P0] Run all affected tests, compile checks, CI-safe pytest, and smoke tests before completion.

---

## Phase 8: Hardening & Bug Fixes (2026-08-17)

- [x] T035 [P0] Remove top-level `import pandas` in `variance_analyzer.py` and `variance_tab.py` completely. Defer import inside functions.
- [x] T036 [P1] Update regex in `scan_directories_and_pair_files` to support 10-digit Cost Center codes.
- [x] T037 [P0] Implement fail-closed validation for non-numeric financial data instead of silently converting to 0.
- [x] T038 [P1] Track and report unmatched files during batch pair scanning.
- [x] T039 [P2] Resolve Excel formula inconsistency: either use formulas for Status as well, or revert to static snapshot values.
- [x] T040 [P2] Add UTF-8 headers to files and fix mojibake in `variance_tab.py`, `variance_analyzer.py`, `excel_variance_writer.py`.
- [x] T041 [P0] Run related unit tests and verify PyInstaller executable failure mode.

---

## Phase 9: Final Regex, UI & Data Rules (2026-08-17)

- [x] T042 [P0] Update regex to use lookaround `(?<!\d)(\d{10}|\d{4})(?!\d)` to fix matching Cost Centers with underscores.
- [x] T043 [P1] Fix mojibake in string literals across `variance_analyzer.py`, `variance_tab.py`, `excel_variance_writer.py`.
- [x] T044 [P1] Improve UI to show up to 10 filenames of unmatched files instead of just the count.
- [x] T045 [P0] Explicitly cast blank/NaN to 0.0 before validation, and ensure tests cover it.
- [x] T046 [P1] Remove `.xls` support from glob and UI file dialogues since `openpyxl` requires `.xlsx`.
- [x] T047 [P0] Add unit tests for regex, unmatched logic, text validation, and blank coercion.

---

## Phase 10: Strict Blank/NaN Validation for YoY (2026-08-17)

- [x] T048 [P0] Implement `_validate_and_extract_cost_series()` to stop and fail on blank `""`, whitespace `"   "`, `None`, and `NaN` with descriptive Vietnamese message.
- [x] T049 [P0] Ensure explicit `0`, `0.0`, `"0"`, `"0.0"` remain valid and correctly calculated.
- [x] T050 [P0] Add regression tests for empty string, whitespace, None/NaN, explicit 0, invalid text, and batch execution (error + valid pair).

---

## Phase 11: Hub Sheet Resolution & Cost Row Filter (2026-08-17)

- [x] T051 [P0] `safe_load_mp_form()` must use `find_hub_sheet_name()` (resolves `内訳ﾘｽﾄ(4～3月)`) instead of `sheet_name=0` (which was `採算表(USD)`).
- [x] T052 [P0] Add `_resolve_hub_sheet_name()` with fallback chain: `find_hub_sheet_name()` → `内訳` substring match → first sheet.
- [x] T053 [P0] Add `_is_cost_row()` filter: only rows with a 7+ digit numeric account code are cost rows; header/dept/total/blank rows are silently skipped.
- [x] T054 [P0] `map_and_analyze_variances()` pre-filters DataFrame to cost rows before validation, preventing false failures on layout rows.
- [x] T055 [P0] Update all test account codes from 4-digit (`1001`) to 10-digit (`9114120018` etc.) to match production data.
- [x] T056 [P0] Add `test_is_cost_row_filter` unit test for the new helper.
- [x] T057 [P0] Add `test_header_and_layout_rows_are_skipped` unit test proving non-cost rows are silently skipped.
- [x] T058 [P0] Add `test_integration_realistic_mp_workbook` proving: hub sheet selection, non-cost row skipping, blank cost cell blocking, and batch success/failure with realistic workbooks.

---

## Phase 12: Column Synchronization & Exact Filtering (2026-08-17)

- [x] T059 [P0] Update `map_and_analyze_variances()` default signature to use exact production columns: `acc_col=1, name_col=2, val_col=17` (representing B, C, R).
- [x] T060 [P0] Update `batch_analyze_variances()` and `variance_tab.py` to stop using hardcoded `0, 1, 13` offsets and rely on the shared production defaults.
- [x] T061 [P0] Harden `_is_cost_row()` to check row index against `FORM_TEMPLATE_INPUT_ROWS` and `FORM_SHARED_COST_START_ROW`, effectively preventing Cost Center `1412000040` (row 2) from being misidentified as a cost row.
- [x] T062 [P0] Rewrite `test_variance_analyzer.py` completely to construct mock data using the exact column locations and simulate row 2 header exclusion.

---

---

## Phase 14: Comprehensive System-Wide Exception Localization (2026-08-17)

- [x] T066 [P0] Localize all 17 `AccountResolutionError` messages in `src/engine/account_resolver.py` to Vietnamese with rich context (sheet, line, account key, cost type).
- [x] T067 [P0] Localize all remaining exception messages in `src/parsers/fixed_assets.py` (cached formula values, unknown category, terminal depreciation) to Vietnamese.
- [x] T068 [P0] Localize missing source directory exception in `src/db/loader.py` to Vietnamese.
- [x] T069 [P0] Localize NNN paperwork and file order exceptions in `src/engine/complete_v1_source_order_writer.py` to Vietnamese.
- [x] T070 [P0] Localize exceptions in `system_cost_writer.py`, `admin_consumables_writer.py`, `cost_center_context.py`, `output_mode.py`, `fixed_assets_reference_skeleton.py`, and `hub_builder.py`.
- [x] T071 [P0] Add comprehensive test suite `tests/test_all_vietnamese_exceptions.py` covering all exceptions and ensuring no English error messages leak. All 47 tests passing.

---

## Phase 15: Sales Account Inheritance & Migrations Localization (2026-08-17)

- [x] T072 [P0] Fix sales account inheritance bug in `src/db/loader.py:622` where continuation rows with blank sales account did not inherit `current_sales_acc`.
- [x] T073 [P0] Localize all `SchemaCompatibilityError` exceptions in `src/db/migrations.py` with structured "Nguyên nhân:" and "Cách xử lý:".
- [x] T074 [P0] Add dedicated regression test `tests/test_allocation_rules_sales_inheritance.py` to verify multi-line sales_account inheritance on continuation rows.
- [x] T075 [P0] Update `tests/test_schema_migrations.py` and `tests/test_all_vietnamese_exceptions.py` to verify Vietnamese localization of migrations.

---

## Phase 16: Structured Cause and Action Guidance for Content Packs, Headcount Plan, and System Cost (2026-08-17)

- [x] T076 [P0] Enrich all `ContentPackError` exceptions in `src/services/content_packs.py` with structured "Nguyên nhân:" and "Cách xử lý:".
- [x] T077 [P0] Enrich all parse errors in `src/parsers/headcount_time_plan.py` with structured "Nguyên nhân:" and "Cách xử lý:".
- [x] T078 [P0] Enrich `SystemSourcePeriodError` and validation exceptions in `src/utils/fiscal_periods.py` with structured "Nguyên nhân:" and "Cách xử lý:".
- [x] T079 [P0] Add regression tests in `tests/test_all_vietnamese_exceptions.py` to verify cause and action presence across all packages.

---

## Phase 17: Department NFKC Normalization & Test Suite Robustness (2026-08-17)

- [x] T080 [P0] Restore NFKC Unicode normalization in `src/parsers/headcount_time_plan.py` (`_resolve_lookup_identity`) for full-width/half-width Japanese character and cost center matching.
- [x] T081 [P0] Add regression test `test_headcount_time_plan_nfkc_unicode_normalization_department_match` in `tests/test_all_vietnamese_exceptions.py`.
- [x] T082 [P0] Update `tests/test_headcount_time_source.py` with explicit T3 baseline data and `@unittest.skipUnless` for physical fixture dependencies.
- [x] T083 [P0] Add cause/action guidance to all `ArtifactVerificationError` in `src/services/update_security.py` and guard against unwrapped exceptions in `src/services/content_packs.py`.

---

## Phase 18: Complete safe_extract_zip Localization & Branch Tests (2026-08-17)

- [x] T084 [P0] Localize 4 remaining `ArtifactVerificationError` in `src/services/update_security.py:safe_extract_zip` (unsupported kind, max bytes exceeded, escape target, size mismatch) with "Nguyên nhân:" and "Cách xử lý:".
- [x] T085 [P0] Add exhaustive branch test `test_update_security_all_exception_branches_produce_cause_and_action` in `tests/test_all_vietnamese_exceptions.py`.



