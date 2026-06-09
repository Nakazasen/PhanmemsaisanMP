# Phase 42N3B - Source File Order Output Policy

## Classification

`PASS_PHASE_42N3B_SOURCE_FILE_ORDER_POLICY_READY`

## User Requirement Change

Previous screenshots and earlier compatibility logic mentioned fixed FORM target
rows such as 38, 42, 58, 59, 97, 98, and 137.

Those rows are now legacy reference only for the source-order output policy. They
must not control current output placement for the MP source-file-order layer.

## Canonical Rule

Output rows are placed by the default source file order in
`src.engine.output_mode.get_default_output_group_specs()`.

After each completed source file block, one blank separator row is reserved
before the next source file block.

## Implementation

- `src/engine/output_mode.py` now classifies fixed assets, birthday, and NNN as
  source-order groups/rows instead of pending fixed-row compatibility groups.
- `src/engine/source_order_output.py` provides a pure placement helper for
  already-derived rows.
- `tests/test_source_order_output.py`, `tests/test_output_mode.py`, and
  `tests/test_output_placement.py` lock the source-order policy.

## Limitation

Legacy workbook writer functions still exist for older export paths. This phase
updates the canonical placement policy and tests; writer migrations should call
the source-order helper instead of hard-coding FORM rows.
