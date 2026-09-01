# Implementation Plan: AI Operations Assistant (Read-only MVP)

**Branch**: `002-ai-operations-assistant` | **Date**: 2026-09-01 | **Spec**: [spec.md](spec.md)

## Summary

Build a local-only support path from an existing MP2027 run to a plain-language, evidence-backed explanation. The MVP never changes business data or starts a run. It first supports a deliberately small catalog of reproducible errors, and handles unknown errors by saying so plainly.

The autonomous-repair agent is not part of this feature. It needs a separate spec, authority model, preview/approval workflow, backup, rollback, and acceptance evidence.

## Technical Context

**Language/Version**: Python 3.13  
**Primary Dependencies**: Standard library, Tkinter, existing i18n service, existing run-history service  
**Storage**: Existing read-only run workspace files and `RUN_HISTORY/.../run_history.db`; reviewed resolution notes may later use a separate table in the history catalog  
**Testing**: pytest, CI-safe fixtures only  
**Target Platform**: Windows desktop application; local project storage  
**Project Type**: Tkinter desktop application  
**Performance Goals**: A normal case opens in under two seconds from local evidence  
**Constraints**: No external model call, no credentials, no business-data write, no output publication, no pipeline invocation, no mutation of immutable run evidence  
**Scale/Scope**: One selected run, initially three known error families plus an unknown-error fallback

## Constitution Check

| Principle | Decision |
|---|---|
| Financial Data and Evidence Integrity | Pass. The assistant reads selected-run evidence and labels unconfirmed conclusions. |
| Excel Template and Output Fidelity | Pass. MVP does not write workbooks or outputs. |
| Layered, Testable Architecture | Pass. Evidence parsing/service logic stays outside `universal_app.py`; UI only orchestrates. |
| Verification Before Trust | Pass only with fixture-based tests for known, unknown, missing, and wrong-scope evidence. |
| Secure, Reproducible Delivery | Pass. No secrets, provider credential, package or update flow is changed. |

## Research Decisions

See [research.md](research.md). The key decisions are: reuse the immutable run workspace, make evidence references explicit, begin with deterministic knowledge entries, and defer any external AI provider to a later approved feature.

## Project Structure

```text
src/
├── services/
│   ├── run_history.py                 # existing run/workspace catalog
│   ├── operations_case_service.py     # new read-only case assembly
│   └── operations_knowledge.py        # new approved known-error catalog
├── ui/
│   └── operations_assistant.py        # new support dialog/frame
└── universal_app.py                   # add one command only after service tests pass

docs/
└── operations/
    └── ai_operations_assistant.md     # user/operator runbook

tests/
├── services/test_operations_case_service.py
├── services/test_operations_knowledge.py
└── ui/test_operations_assistant.py
```

## Design Boundaries

- The service accepts a selected `run_id` and history root, verifies that all loaded evidence belongs to that run, and returns a serializable `OperationalCase`.
- The knowledge catalog matches only stable error classifications. Free-text similarity alone may never produce a confirmed diagnosis.
- The primary UI uses the selected application language (Vietnamese, English, or Japanese) and presents: what happened, certainty, affected scope, safe manual next steps, and labelled evidence. It must use ordinary operational language; exception names, JSON, stack traces, and internal stage names are optional technical details only.
- Each approved knowledge entry and the unknown fallback has reviewed, complete VI/EN/JA text. The application must not machine-translate at runtime or silently substitute a different visible language when a translation is absent.
- The UI displays: confirmed facts, confidence, evidence links, and safe manual next steps. It has no “Fix”, “Run”, “Save source”, or “Apply” action.
- Resolution-note persistence is planned only after the read-only MVP is accepted; it must live separately from run evidence and carry review status.
- Any future model provider sits behind a provider-neutral contract and requires a separate approved data-sharing decision. Gemini Flash is a development worker only, not the chosen production provider.

## Delivery Slices

1. **Foundation**: case data model, evidence loader, error taxonomy, tests.
2. **MVP**: three deterministic knowledge entries, each with plain-language VI/EN/JA presentation content, plus an evidence viewer; no model needed.
3. **User interface**: localized read-only dialog launched from selected run history; primary guidance and optional technical evidence are visually separate.
4. **Reviewed learning**: resolution-note design and implementation only after MVP acceptance.
5. **Future feature, excluded**: provider integration, retrieval, model evaluation, repair proposal, approval, backup/rollback, and autonomous repair.

## Complexity Tracking

No constitution exception is requested. The feature deliberately avoids adding a network service, model SDK, credentials, background agent, or output-writing capability.
