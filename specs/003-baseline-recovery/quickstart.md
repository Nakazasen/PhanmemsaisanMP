# Quickstart Validation: Reliable March Baseline Recovery

## Preconditions

- Work from the repository root with the FY2027 fixture/source files available.
- Do not modify `raw/FY2027/manual_inputs.db` during automated checks; tests must use temporary or in-memory databases.

## Automated regression checks

```powershell
py -3 -m pytest tests/test_gui_baseline_recovery.py tests/test_template_validation.py -q
py -3 -m pytest tests/test_headcount_time_source.py -q
py -3 -m compileall -q src tests
git diff --check
```

Expected outcomes:

- A legacy `MANUAL_GUI` all-zero March record with valid same-CC April data is replaced only after explicit recovery handling.
- A confirmed manual March baseline is unchanged.
- Mixed selections recover valid codes and list unavailable codes without cross-cost-center substitution.
- Readiness states and manual-editor selection report the active code correctly.

## Recorded local verification (2026-09-02)

The following CI-safe, feature-relevant command completed successfully:

```powershell
py -3 -m pytest tests/test_gui_baseline_recovery.py tests/test_template_validation.py tests/test_headcount_time_source.py tests/test_i18n.py tests/services tests/ui -q -m "not performance and not requires_raw_excel and not real_pipeline_acceptance"
```

Result: `188 passed, 11 subtests passed in 17.61s`.

`py -3 -m compileall -q src tests` and `git diff --check` also completed successfully. The real-workbook, real-pipeline, and performance profiles were intentionally not run because this repair uses temporary databases and does not alter workbook or output behavior.

## Desktop acceptance checks

1. Select CC `1412000006`, refresh checks, and confirm the readiness text names the missing March baseline rather than saying calculation is fully ready.
2. Choose Run, approve April recovery, and confirm the resulting T3 uses the same code's April staffing.
3. Repeat with an unavailable source: confirm the dialog keeps the unresolved code visible and offers manual entry.
4. Open manual staffing from a single selected CC and verify the combobox starts on that code.

## Out of scope

- No FORM/workbook formula changes.
- No automatic March substitution without a user action.
- No release, packaging, or runtime-database migration operation.
