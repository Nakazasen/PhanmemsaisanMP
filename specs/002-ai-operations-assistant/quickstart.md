# Quickstart Validation: Read-only Operations Assistant

## Prerequisites

- A disposable test history root with known failed or incomplete run fixtures.
- The existing CI-safe pytest environment (Python 3.10+).

## Scenario A: Known failure

1. Build a case for a fixture with an approved error classification (`missing_staffing_baseline`, `blocked_output_file_lock`, or `preflight_source_validation_failure`).
2. Verify FY, CC scope, run ID, stage, evidence links, confidence, and Vietnamese guidance.
3. Repeat in English and Japanese.
4. Verify the fixture files, SQLite catalog, source files, and output workbooks have unchanged checksums.

## Scenario B: Unknown failure

1. Build a case for a fixture with an unmatched error.
2. Verify the result says the cause is unconfirmed.
3. Verify it lists available evidence and no automated repair action.

## Scenario C: Bad evidence

1. Use a fixture whose report path is missing or points outside the selected workspace.
2. Verify the result marks evidence missing/mismatched and refuses a confirmed diagnosis.

## Scenario D: UI Orchestration & Singleton Guard

1. Open Run History window and verify the "Trợ lý xử lý lỗi" action button state is disabled without selection.
2. Select a `RUNNING` row and verify the button remains disabled and no service call occurs.
3. Select a terminal run (`FAILED`, `PRECHECK_FAILED`, `SUCCEEDED`, `SUCCEEDED_INCOMPLETE`, `LEGACY_FY2027`) and verify the button is enabled.
4. Verify that opening the dialog with the active language (`vi`, `en`, `ja`) correctly propagates and renders the dialog in that language.
5. Verify repeated open requests for the same run reuse the existing dialog and focus the window.

## Verified CI-Safe Test Suite (Passed Commands)

```powershell
# 1. Compilation & Syntax Verification
py -3 -m compileall -q src tests

# 2. Focused Test Suite for AI Operations Assistant Feature
py -3 -m pytest tests/test_i18n.py tests/ui/test_operations_assistant.py tests/services/test_operations_knowledge.py tests/services/test_operations_case_service.py tests/test_run_history.py tests/test_repo_handover_docs.py -q

# 3. Git Format & Whitespace Check
git diff --check
```

**Verification Results**:
- `compileall`: Passed (exit code 0, 0 errors).
- `pytest` suite: **135 passed in 9.66s** (100% pass rate).
- `git diff --check`: Clean (exit code 0).

## Unrun Acceptance Checks (Deferred / Manual Only)

- **T027 Human Acceptance Review**: A responsible reviewer must still run and record one known-error case and one unknown-error case. The fixture and fake-widget tests do not substitute for this review.
- **Manual Interactive Desktop Session**: Manual visual inspection on physical Windows monitors across different DPI scalings and dark/light Windows themes (automated tests use fake widget & headless mock harnesses).
- **Future Cloud/Autonomous Repair**: Deferred to future spec (AR001–AR005); not run or tested in MVP.
