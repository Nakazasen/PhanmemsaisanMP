# Quickstart Validation: First-run Cost Layout

## Automated checks

```powershell
py -3 -m pytest tests/test_manual_special_cost_sections.py tests/test_output_cost_row_ordering.py -q
py -3 -m compileall -q src scripts packaging
git diff --check
```

Expected outcomes:

- An unmarked current workbook with no configured legacy start is classified as first-run and produces an empty special-cost section.
- A metadata-marked source, saved-order source, and configured legacy source still preserve their content.
- A malformed metadata marker still fails clearly.

## Recorded local verification (2026-09-02)

```powershell
py -3 -m pytest tests/test_manual_special_cost_sections.py tests/test_output_cost_row_ordering.py tests/test_source_order_output.py tests/test_mp_saisan_complete_export.py tests/test_refactor_output_verifier.py tests/test_run_history.py tests/test_no_src_hardcodes.py -q
```

Result: `65 passed in 5.38s` (five known `openpyxl` warnings about a legacy worksheet title longer than Excel's recommended limit).

`py -3 -m compileall -q src scripts packaging` and `git diff --check` also passed. No real workbook/pipeline run was performed because that would write a business output file.

## Desktop acceptance

1. Choose a CC whose existing output is an original/common-cost-only workbook with no special-cost configuration.
2. Run calculation.
3. Confirm the run completes the special-cost stage without asking for a starting row.
4. Open the result and confirm it contains the new special-cost separator and no copied unknown rows.
