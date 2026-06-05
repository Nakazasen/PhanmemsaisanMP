# MP2027 Reference Outputs

## Primary trusted reference

`primary/16.KDTVN 電気製造技術課_MP FY2027_各予定(Ver01).xlsx`

This is the trusted reference output for MP2027 validation.

Business note:
The requester said this file should be trusted as the main reference because the Administrative/HR-related contents for this department are stable and the department cost center is not expected to change.

Use this file as the primary expected output when comparing MP2027 generated results.

## Secondary reference archive

`secondary/FY2027.zip`

This archive contains MP FY2027 files from other departments/sections.

These files are for reference only:
- use them to understand formats,
- compare sheet structures,
- discover edge cases,
- but do not treat them as the main expected answer,
because other departments may have changed cost centers or department-specific contents.

## Requirement source workbooks

`raw/requirements/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026.xlsx`
is the latest requirement workbook.

`raw/requirements/Cải tiến nhập dữ liệu chung vào file MPnew12.04.2026.xlsx`
is the older requirement workbook kept for comparison.

## Comparison rule

When validating generated MP2027 output:
1. Compare against the primary trusted reference first.
2. Use secondary files only for supplementary format/edge-case checks.
3. Do not mark output wrong only because it differs from a secondary department file.
