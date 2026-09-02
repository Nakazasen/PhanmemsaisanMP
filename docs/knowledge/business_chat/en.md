# MP2027 Business Chat Knowledge — English

Schema version: 2.0

This document is auto-generated from knowledge_catalog.json and source_registry.json.
This is curated local retrieval; not vector/embedding RAG and does not read original documents at runtime.
Gemini is the external answer-composition layer when available.
Do not edit directly — update the catalog and regenerate.

---

## bck_locked_file: Output file is locked

**Status**: active | **Review**: approved
**Source**: Approved MP2027 business guidance

When the output Excel workbook is open in another application or by another user, the program cannot overwrite it to save new results.

1. Close all Excel files open in the output folder.
2. Close any File Explorer windows browsing the output folder.
3. Wait a few seconds and click Run Calculation again.

Keywords: locked, file locked, excel locked, cannot save, open by another, permission denied, cannot write

---

## bck_missing_baseline: Missing March baseline headcount

**Status**: active | **Review**: approved
**Source**: Approved MP2027 business guidance

The program requires March headcount data (the opening-month baseline) to calculate cost allocations for the entire fiscal year. Without this data, the calculation cannot proceed.

1. Click Manual Staffing Input on the main screen.
2. Select the department and enter the total headcount for March.
3. Click Save Staffing & Time, then click Run Calculation.

Keywords: baseline, headcount, march, missing staffing, personnel, missing baseline, staffing data

---

## bck_source_validation: Input source file does not meet requirements

**Status**: active | **Review**: approved
**Source**: Approved MP2027 business guidance

Before calculation, the program checks all input source files. If a file has missing sheets, wrong fiscal year, or incorrect column structure, an error is reported and calculation cannot start.

1. Read the error message to identify which file has an issue and what the problem is.
2. Open the workbook, fix it as instructed, and save.
3. Click Rescan Sources and then Run Calculation.

Keywords: source, source file, validation, input file, wrong structure, missing sheet, source error, preflight

---

## bck_fiscal_year_mismatch: Fiscal year mismatch

**Status**: active | **Review**: approved
**Source**: Approved MP2027 business guidance

The FORM template and all source files must be for the same fiscal year. If the fiscal year on the main screen does not match the source files, the program will refuse to run.

1. Check that the fiscal year on the main screen matches the year you want to calculate.
2. Verify the FORM template and source folders are for the correct year.
3. If wrong, select the correct FORM and source folders, then click Rescan Sources.

Keywords: fiscal year, year, wrong year, mismatch, FY, year mismatch

---

## bck_cost_center_selection: How to select a cost center (department)

**Status**: active | **Review**: approved
**Source**: Approved MP2027 business guidance

Before running the calculation, you need to select the cost centers (departments) for which you want to generate output. You can select one, several, or all departments.

1. Click Select Department on the main screen.
2. Check the departments you need, or click Select All.
3. Click Confirm to return to the main screen, then click Run Calculation.

Keywords: cost center, department, CC, select department, choose room, select CC

---

## bck_data_entry_manual: How to enter manual supplementary data

**Status**: active | **Review**: approved
**Source**: Approved MP2027 business guidance

Some cost items are not available from automatic source files and must be entered manually, such as company trips, folding cups, anniversaries, or bus costs.

1. Click Event Driver Input on the main screen.
2. Select the event type and enter the actual quantity or amount.
3. Click Save, then click Run Calculation.

Keywords: manual input, manual entry, event driver, supplementary, data entry, manual data

---

## bck_rerun_calculation: How to rerun calculation after fixing data

**Status**: active | **Review**: approved
**Source**: Approved MP2027 business guidance

After fixing source files, entering supplementary data, or resolving errors, you need to rescan sources and then run the calculation again to get updated results.

1. Click Rescan Sources (or Quick Change Check) so the program reads the updated files.
2. Verify the status shows green (sources are ready) on the main screen.
3. Click Run Calculation to generate updated results.

Keywords: rerun, recalculate, run again, run calculation, after fix, retry

---

## bck_excel_format_error: Excel format or structure error

**Status**: active | **Review**: approved
**Source**: Approved MP2027 business guidance

If a source Excel workbook has wrong formatting, missing required worksheets, or incorrect columns, the program cannot read it and will report an error during the check.

1. Review the error message to find the file name and missing or incorrect worksheet.
2. Open the Excel file and add the missing worksheet or fix the columns as required.
3. Save the file, then click Rescan Sources.

Keywords: excel, format, structure, column, sheet, worksheet, format error

---

## bck_headcount_input: How to enter 12-month headcount data

**Status**: active | **Review**: approved
**Source**: Approved MP2027 business guidance

The 12-month headcount data includes employee, worker, and expatriate counts for each month of the fiscal year. The program uses this to allocate personnel costs.

1. Click Manual Staffing Input and select the department (CC) to enter.
2. Enter employee and worker counts for each month. Blank cells will be saved as 0.
3. Click Save Staffing & Time.

Keywords: headcount, 12 months, staffing, personnel, employee count, worker, staff input

---

## bck_workflow_overview: 5-step workflow to run MP2027 calculation

**Status**: active | **Review**: approved
**Source**: Approved MP2027 business guidance

The MP2027 workflow has 5 steps: (1) Choose fiscal year, (2) Select the FORM template and source folders, (3) Check source status, (4) Add manual data if needed, (5) Click Run Calculation.

1. Select the correct fiscal year, FORM template, and cost/staffing source folders.
2. Click Rescan Sources and review the status colors on the main screen.
3. If status is green, click Run Calculation. Try one department first before running all.

Keywords: workflow, 5 steps, how to use, getting started, guide, process, start

---

## bck_account_lookup_rules: Account code lookup hierarchy rules

**Status**: active | **Review**: approved
**Source**: Approved MP2027 business guidance

Account codes must not be matched directly by text description. They must follow the 5-step business chain: (1) Cost Center, (2) Cost Center Master, (3) Cost Category, (4) Select Manufacturing/General/Sales column, (5) Retrieve accurate account code.

1. Identify the target Cost Center code.
2. Look up the Cost Category for that department in the master list.
3. Select the matching column (Manufacturing, General, or Sales) and pick the exact account code.

Keywords: account, account code, lookup, hierarchy, cost category, department account, ledger

---

## bck_special_cost_manual: How to handle manual special cost adjustments

**Status**: active | **Review**: approved
**Source**: Approved MP2027 business guidance

Special expenses that are not part of automated source flows can be declared via the manual special cost input channel according to standard templates.

1. Open the manual cost entry screen or inspect the supplementary expense ledger.
2. Enter the department code, account code, and monthly amounts.
3. Save the entries and click Rescan Sources.

Keywords: special cost, special expense, manual adjustment, extra cost, supplementary cost, cost entry

---

## bck_update_rollback_procedure: Software update and version rollback procedure

**Status**: active | **Review**: approved
**Source**: Approved MP2027 business guidance

The system supports safe updates via company-controlled LAN shares. It performs SHA-256 integrity verification, safe extraction, and automatic backup before applying updates.

1. Ensure your computer is connected to the company internal network share.
2. Follow the on-screen prompt to apply the verified update.
3. If any issue occurs after updating, contact IT to revert to the automated backup.

Keywords: update, software update, rollback, version, restore, LAN share, upgrade

---
