# Implementation Plan: First-run Cost Layout

**Branch**: `004-first-run-cost-layout` | **Date**: 2026-09-02 | **Spec**: [spec.md](spec.md)

## Summary

Classify an existing cost-center workbook as a preservation source only when it contains explicit evidence of user-owned special-cost layout. An unmarked original or common-cost-only workbook is a first-run source: no rows are copied from it, and the generated workbook receives its new empty special-cost section. Known metadata, saved row order, and configured legacy row starts retain the current preservation behavior.

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: openpyxl, existing MP2027 export pipeline

**Storage**: Excel output workbooks; project configuration for explicit legacy row starts

**Testing**: pytest with synthetic workbooks

**Target Platform**: Windows desktop application

**Project Type**: Single Python desktop application

**Performance Goals**: One bounded workbook-inspection pass per selected cost center; no changes to source workbooks.

**Constraints**: Do not guess that unknown rows are manual. Preserve only metadata, saved order, or a user-configured legacy start. Do not modify FORM or cost values.

**Scale/Scope**: The special-cost restore stage in `scripts/run_e2e.py` and `src/engine/manual_special_cost_sections.py`; no UI redesign or output formula changes.

## Constitution Check

| Principle | Status | Evidence / decision |
|---|---|---|
| Financial Data and Evidence Integrity | PASS | An unmarked form contributes no invented or copied manual rows; known layouts retain evidence-based preservation. |
| Excel Template and Output Fidelity | PASS | Source workbooks remain read-only and output creation continues to own the new special-cost separator. |
| Layered, Testable Python Architecture | PASS | Source classification is a reusable engine helper; the pipeline orchestrates selection only. |
| Verification Before Trust | PASS | Reproduction tests cover original, metadata, row-order, and configured-legacy cases. |
| Secure, Reproducible Delivery and Repository Hygiene | PASS | No secrets, release behavior, or runtime data migration. |

## Research Decisions

See [research.md](research.md). The source is considered restorable only with an explicit preservation signal; a current output file by itself is insufficient evidence of user-owned rows.

## Project Structure

```text
src/engine/manual_special_cost_sections.py  # special-cost metadata inspection
scripts/run_e2e.py                          # source staging classification
tests/test_manual_special_cost_sections.py  # synthetic-workbook regressions
specs/004-first-run-cost-layout/            # feature records
```

**Structure Decision**: Keep ownership classification in the engine module and pass the resulting source/no-source decision through the existing pipeline wrapper.

## Complexity Tracking

No additional layers or constitution exceptions are required.
