---
type: "query"
date: "2026-08-12T10:06:32.407534+00:00"
question: "người dùng đang claim dù không nhập baselinet3 thì khi chạy tính toán, chương trình vẫn cho chạy bình thường, không check, vẫn xuất kết quả như bình thường"
contributor: "graphify"
outcome: "useful"
source_nodes: ["manual_staffing_overrides.py", "universal_app.py", "run_e2e.py"]
---

# Q: người dùng đang claim dù không nhập baselinet3 thì khi chạy tính toán, chương trình vẫn cho chạy bình thường, không check, vẫn xuất kết quả như bình thường

## Answer

Expanded from original query via graph vocab: [baseline, march, manual, calculation, preflight, run, validation, validator, fiscal, month]. Root cause verified against the real LocalAppData manual_inputs.db: four legacy records had all staffing fields zero with description MANUAL_BASELINE_T3 and source_file MANUAL_GUI, created when the GUI converted a completely blank T3 row to zeros. Existence-only checks treated those rows as valid. Fixed the GUI validator to reject a completely unentered baseline, added explicit provenance for confirmed zero baselines, centralized validity checking in has_valid_manual_baseline, and applied it both before GUI launch and in pipeline staffing preflight. Relevant tests passed 74/74; mojibake and compile checks passed. The full suite exceeded the available timeout without reporting a failure.

## Outcome

- Signal: useful

## Source Nodes

- manual_staffing_overrides.py
- universal_app.py
- run_e2e.py