# Phase 42N2R - CC Map and Timeout-Safe Scanner

## Classification

`WARNING_PHASE_42N2R_CC_MAP_INCOMPLETE`

## Summary

42N2R made progress on infrastructure, but it did not unlock full all-department simulation yet.

| Item | Result |
|---|---:|
| CC map candidate rows | 6 |
| Trusted rows with target_cc | 0 |
| Safe scanner exists | YES |
| Primary reference smoke status | `READ_TIMEOUT` |

## What was completed

Created timeout-safe workbook scanner:

`tools/safe_workbook_inventory.py`

The scanner supports:

- `--input`
- `--output`
- `--timeout-seconds`
- per-workbook timeout handling
- `READ_TIMEOUT` / `READ_ERROR` recording
- no workbook modification

## Smoke test result

Command tested:

    py tools\safe_workbook_inventory.py --input "reference_outputs\primary\16.KDTVN 電気製造技術課_MP FY2027_各予定(Ver01).xlsx" --output "dist\phase42n2r_safe_scanner_smoke_primary.csv" --timeout-seconds 20

Result:

`READ_TIMEOUT`

Non-tech meaning: the scanner is safe because it does not hang forever. If a workbook is too slow or unsafe to read, it records timeout and continues.

## CC map result

Current candidate file:

`docs/audits/phase42n2r_department_cc_map_candidates.csv`

Result:

- Candidate rows: `6`
- Rows with trusted target_cc: `0`

This is not enough to run all-department simulation.

## Why full simulation cannot run yet

The all-department folder contains many department reference workbooks, but the program still does not have a trusted map:

`department reference workbook -> target cost center / CC`

Without this map, running simulation would require guessing CC from filename or using the wrong reference workbook. That would be unsafe and could produce attractive but false results.

## What is needed next

Create a trusted department-to-CC map.

Recommended file:

`docs/config/department_cc_map.csv`

Suggested schema:

    department_no,department_name,department_jp_name,target_cc,cost_type,reference_path,source_file,source_sheet,source_row,confidence,approved_by

Minimum required fields for simulation:

- department_no
- department_jp_name
- target_cc
- reference_path
- confidence

## Next phase recommendation

`42N2S - Build or request trusted department_cc_map`

Goal:

- map as many of the 65 root department files as possible,
- do not guess CC,
- use only trusted source/master evidence or user-provided mapping,
- then rerun 42N2Q full simulation.

## Non-tech conclusion

Có thể gọi 100% source-derived chưa? **Chưa.**

Lý do chính không phải vì complete-v1 không chạy được cho `1412000040`, mà vì khi mở rộng ra toàn bộ phòng ban thì chưa có bản đồ đáng tin cậy nối từng phòng ban/reference workbook với CC tương ứng.

## Final classification

`WARNING_PHASE_42N2R_CC_MAP_INCOMPLETE`
