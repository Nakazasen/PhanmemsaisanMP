# Handover: UI Not Responding With Clean FORM

Date: 2026-07-10

## Context

The runtime FORM at `docs/MP2027/FORM.xlsx` was cleaned so detail-sheet columns `B`, `S`, and `T` are blank from row 30 onward. The formulas/styles in other columns are preserved. The exporter was updated so those blank template labels do not break fixed-row output.

The CLI pipeline can run with the cleaned FORM. Verified command:

```powershell
py -3 scripts\run_e2e.py --fy 2027 --template docs\MP2027\FORM.xlsx --source docs\MP2027 --target-cc 1412000006
```

This completed successfully and wrote `OUTPUT_FY2027\MP_CC_1412000006.xlsx`.

## Implemented Changes

- `src/engine/hub_builder.py`
  - Recurring admin rows for gas, hand wash, toilet paper, and cleaning now use DB headcount from `fact_monthly_headcount`.
  - Priority is `manual > ga > others`.
  - Output formulas use explicit configured headcount such as `=26*1339`, not workbook row formulas like `SUM(...$24:...$25)`.
  - Missing headcount leaves the month cell blank instead of falling back to template rows.
  - Fixed row descriptions/accounts are rebuilt from code/source data so blank `B/S/T` rows in FORM do not inject old template data.

- `docs/MP2027/FORM.xlsx`
  - Cleaned columns `B`, `S`, and `T` from row 30 downward.

- `scripts/run_e2e.py`
  - Removed the `--legacy-export` switch. CLI now always uses canonical complete-v1 export.
  - Added a defensive helper so mocked/replaced builders without `_load_append_rows` do not crash canonical source-order tests.

- `src/universal_app.py`
  - Initial thread-safety changes: UI updates go through a queue and `log()` no longer calls Tk directly from worker threads.
  - Removed automatic heavy source loading from GUI startup `load_cc_list()`.
  - GUI pipeline invocation was moved toward a child process via `subprocess.Popen`, so the Tk process should not run the heavy Excel/openpyxl pipeline in-process.

## Current UI Issue

The user still observed `MP2027 Manager - Quản lý Ngân sách (Not Responding)` after starting the GUI from:

```powershell
run_MP2027.bat
```

Observed process details from the same machine:

- `py.exe src/universal_app.py`
- child `python.exe src/universal_app.py`
- Window title: `MP2027 Manager - Quản lý Ngân sách`
- `Responding=False`
- CPU continued increasing in the Python GUI process.

A short debug run with `faulthandler.dump_traceback_later()` showed the main thread in `tkinter.mainloop` while the UI was still responsive early in startup. The debug hook was removed before commit. The freeze happened later, so the next investigation should capture a stack while the process is already `Responding=False`.

## Important Finding

This is not proof that the cleaned FORM cannot run. The cleaned FORM works through CLI.

The remaining problem is the GUI process becoming unresponsive, likely due to one of:

- a Tkinter thread-safety path still left in the GUI,
- a high-CPU loop in a Tk callback after startup,
- the GUI reading or refreshing DB/output state while the CLI/pipeline process updates `mp2027.db` or output files,
- an old packaged/launcher process still running stale code.

## Suggested Next Steps

1. Reproduce from a clean state:

```powershell
Get-Process | Where-Object { $_.MainWindowTitle -like '*MP2027 Manager*' } | Stop-Process -Force
py src\universal_app.py
```

2. If it freezes, capture stack while frozen:

```powershell
py -m pip install py-spy
py-spy dump --pid <frozen-python-pid>
```

3. If `py-spy` cannot be installed, temporarily add a `faulthandler.dump_traceback_later(..., repeat=True)` hook, reproduce, and inspect the dump.

4. Consider disabling GUI DB refreshes while the child pipeline process is running. In particular, avoid `load_cc_list()` or dashboard/audit refresh callbacks until `_finish_pipeline()` fires.

5. Re-test from GUI after the fix with:

- cleaned `docs/MP2027/FORM.xlsx`,
- source folder `docs/MP2027`,
- target CC `1412000006`,
- then inspect output formulas for gas/hand wash/toilet/cleaning.

## Verification Already Run

```powershell
py -3 -m py_compile src\universal_app.py scripts\run_e2e.py tests\test_canonical_gui_export_path.py
py -3 -m pytest tests/test_canonical_gui_export_path.py tests/test_packaging_entrypoint.py tests/test_packaged_raw_resolution.py
py -3 -m pytest tests/test_headcount_and_export.py::TestHubBuilderExport::test_fixed_rows_follow_mp2027_form_layout tests/test_headcount_and_export.py::TestManualSpecialCosts::test_recurring_admin_rows_use_configured_previous_month_headcount_formulas
py -3 scripts\run_e2e.py --fy 2027 --template docs\MP2027\FORM.xlsx --source docs\MP2027 --target-cc 1412000006
```

Results at handover time:

- GUI/packaging tests: 24 passed.
- Headcount/export targeted tests: 2 passed.
- CLI export with cleaned FORM and CC `1412000006`: succeeded.

