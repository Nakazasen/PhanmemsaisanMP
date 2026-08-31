# Implementation Plan: Honor Saved Source File Order

**Branch**: `001-source-order-runtime` | **Date**: 2026-08-31 | **Spec**: [spec.md](spec.md)

## Summary

The source-order editor already saves global manifest positions, but the Complete-v1 exporter rebuilds a fixed category sequence immediately before writing the workbook. Add a separate resolved display order from the active manifest and pass it through the exporter. Keep the established category-to-business-row mapping for parsing, dynamic rows, formatting, and calculations.

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: openpyxl, pytest
**Storage**: `source_file_order.xlsx` manifest in the selected source directory
**Testing**: pytest
**Target Platform**: Windows desktop application
**Project Type**: Desktop application with Python pipeline
**Constraints**: no change to input eligibility, parser execution, allocation values, formulas, protected FORM rows, or Cost Center isolation
**Scope**: `scripts/run_e2e.py`, Complete-v1 source-order writer, focused tests and feature documentation

## Constitution Check

No project constitution is present. The implementation must preserve the repository's existing fiscal-run and workbook safety contracts. This plan passes because it adds an optional presentation/provenance argument while retaining the existing source-group mapping as the compatibility default.

## Design

1. Keep `source_file_order` as the stable seven-category mapping used to identify workbook business rows.
2. Resolve `output_source_file_order` from `FiscalRunContext.ordered_sources`, constrained to paths actually resolved for this run. This excludes disabled, invalid, missing, and unconfirmed inputs because they never enter `resolved_sources`.
3. Pass both orders to each single and batch Complete-v1 write phase.
4. Write blocks according to `output_source_file_order`; append any mapped source not listed there deterministically.
5. Determine facility/allocation intra-block rules from the stable mapping index, never from the moved output position.

## Project Structure

```text
scripts/run_e2e.py
src/engine/complete_v1_source_order_writer.py
tests/test_complete_v1_source_order_writer.py
tests/test_canonical_gui_export_path.py
specs/001-source-order-runtime/
```

## Complexity Tracking

No constitution exception is required.
