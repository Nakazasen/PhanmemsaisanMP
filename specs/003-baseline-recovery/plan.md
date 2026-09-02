# Implementation Plan: Reliable March Baseline Recovery

**Branch**: `003-baseline-recovery` | **Date**: 2026-09-02 | **Spec**: [spec.md](spec.md)

## Summary

Repair the March-baseline recovery path so explicitly approved April data can replace only legacy, unconfirmed zero March records for the same cost center. Recover multiple cost centers independently, expose missing baselines in the current-scope readiness state, and default manual staffing to the active cost center. The repair retains fail-closed financial behavior: no automatic substitute, no cross-cost-center values, no overwrite of a valid manual baseline, and no calculation output until all selected baselines are valid.

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: Tkinter desktop UI, standard-library SQLite, existing Excel source importer

**Storage**: Per-fiscal-year SQLite manual-input store and operational SQLite source store

**Testing**: pytest; focused service/UI regression tests plus CI-safe regression profile

**Target Platform**: Windows desktop application

**Project Type**: Single Python desktop application

**Performance Goals**: Recovery feedback remains responsive for the selected scope; no new full calculation or output workbook is created during recovery.

**Constraints**: Preserve financial evidence, cost-center isolation, explicit user approval, existing valid manual baselines, and the existing project-scoped data locations. The feature must work with historical `MANUAL_GUI` zero records without silently reclassifying them as confirmed.

**Scale/Scope**: FY2027 selected-cost-center runs; changes are limited to baseline recovery, readiness/UI guidance, and regression documentation.

## Constitution Check

| Principle | Status | Evidence / decision |
|---|---|---|
| Financial Data and Evidence Integrity | PASS | April-to-March substitution remains an explicit user action, same CC/FY only, and provenance is retained. |
| Excel Template and Output Fidelity | PASS | No FORM or writer logic changes; recovery completes before any calculation output. |
| Layered, Testable Python Architecture | PASS | Baseline classification/recovery stays in `manual_staffing_overrides`; Tkinter only orchestrates and presents outcomes. |
| Verification Before Trust | PASS | Historical data state is reproduced in tests before service/UI implementation. |
| Secure, Reproducible Delivery and Repository Hygiene | PASS | No secrets, release, package, or runtime database writes are added to the repository. |

## Research Decisions

See [research.md](research.md). The implementation uses a narrow legacy-record predicate rather than weakening the valid-baseline rule, imports reusable April candidates without making the multi-CC import atomic, and keeps unresolved cost centers blocked.

## Project Structure

### Documentation (this feature)

```text
specs/003-baseline-recovery/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── recovery-ui-flow.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── services/
│   ├── manual_staffing_overrides.py   # baseline classification and recovery
│   ├── headcount_source_importer.py   # reviewed April-source import
│   └── i18n.py                        # user-facing readiness/recovery text
└── universal_app.py                   # selected-scope orchestration and Tkinter UI

tests/
├── test_gui_baseline_recovery.py      # service regression cases
└── test_template_validation.py        # user-facing baseline guidance
```

**Structure Decision**: Keep financial data decisions in the existing staffing service and keep `MPManagerApp` responsible only for selected-scope coordination and display. No new persistence layer or background service is required.

## Complexity Tracking

No constitution violations or additional architectural layers are required.
