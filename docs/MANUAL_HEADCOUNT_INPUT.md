# Manual Headcount Input Guide

This guide explains how users can provide monthly headcount manually when no reliable CC-level headcount source file exists.

## 1. Input directly from GUI (recommended)

You can now enter headcount directly in the program UI:

1. Open app: `run_MP2027.bat` (or run `src/universal_app.py`).
2. Set `Fiscal Year` and `Source folder`.
3. Click `Manual Headcount Input`.
4. In popup:
- select `CC`
- select `Period`
- enter `Staff` and `Worker`
- click `Add/Update`
5. Click `Save CSV`.
6. Run pipeline.

The popup writes data into `headcount_manual.csv` automatically.

## 2. Where to put the file (if editing outside GUI)

Place this file in the pipeline source directory:

- `headcount_manual.csv`

Example:
- If you run `py scripts/run_e2e.py --source .`, then the file must be in project root.

## 3. Auto-generated template

If `headcount_manual.csv` is missing, the pipeline auto-creates a template with sample rows.

Columns:
- `cc_code`
- `period`
- `headcount_staff`
- `headcount_worker`
- `description` (optional)

## 4. Column rules

`cc_code`
- Must exist in `FORM.xlsx` cost center master.
- Use full CC code (example: `1412000004`).

`period`
- Preferred: `YYYYMM` (example: `202604`).
- Also accepted: month number `1..12` (mapped to fiscal months).

`headcount_staff`
- Non-negative number.

`headcount_worker`
- Non-negative number.

`description`
- Optional text for note/tracking.

## 5. How values are used

For each row:
- `headcount_all = headcount_staff + headcount_worker`
- Data is written into `fact_monthly_headcount` with `source='manual'`.
- When both manual and GA exist for same `(cc_code, period)`, manual is prioritized.

## 6. Validation behavior

A row is rejected when:
- `cc_code` is not in master CC list.
- `period` is invalid or outside fiscal periods.
- staff/worker is negative.

A row is skipped when:
- all key cells are blank
- or `headcount_staff + headcount_worker <= 0`

## 7. Pipeline log messages

During E2E run, you will see:
- `Manual headcount: inserted=..., skipped=..., errors=..., file=...`

Use this message to verify whether your manual file is actually being consumed.

## 8. Minimal example

```csv
cc_code,period,headcount_staff,headcount_worker,description
1412000004,202604,21,180,baseline
1412000004,202605,21,182,hiring +2 workers
1412000025,202604,35,0,admin team
```
