# Implementation Plan: AI Operations Assistant (C-AGENT primary)

**Branch**: `002-ai-operations-assistant` | **Date**: 2026-09-01 | **Spec**: [spec.md](spec.md)

## Summary

Extend the existing read-only Operations Assistant so a user can explicitly ask the company's C-AGENT service for a plain-language analysis of one selected terminal run. C-AGENT is the only operational AI provider and is an IT-approved internal data boundary; it can receive relevant technical evidence from that selected run. The existing local evidence and reviewed guidance remain available without a network connection.

Gemini Web Direct is a separately labelled, opt-in experiment. It may send only a built-in fictional incident to the public Gemini Web endpoint so an owner can observe answer quality. It is never a fallback, never receives a selected MP2027 run, and is off by default.

The feature remains read-only: neither provider can write a source file, change a workbook/database/configuration, run the pipeline, or persist an AI answer into run history.

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: Standard library, Tkinter, existing i18n service, existing run-history service; no model SDK
**Storage**: Existing read-only run workspace and `RUN_HISTORY/.../run_history.db`; provider responses are in-memory UI state only
**Testing**: pytest, CI-safe temporary run-history fixtures; all provider HTTP calls mocked in automated tests
**Target Platform**: Windows desktop application; C-AGENT normally reachable on the approved company network
**Project Type**: Tkinter desktop application
**Performance Goals**: Local case opens under two seconds; one C-AGENT request times out visibly within 60 seconds without freezing the UI
**Constraints**: C-AGENT endpoint must be explicitly configured and company-approved; HTTPS required unless a separately approved internal exception is documented; provider secrets never appear in source, UI, logs, test fixtures, or Git
**Scale/Scope**: One selected terminal run per request; no conversation memory, resolution-note persistence, model fallback, RAG, automatic repair, or batch analysis

## Constitution Check

| Principle | Decision |
|---|---|
| Financial Data and Evidence Integrity | Pass. The local case remains authoritative. The provider receives a minimised packet, must cite packet evidence identifiers, and cannot alter the run. |
| Excel Template and Output Fidelity | Pass. No workbook, output, or pipeline method is callable by either provider integration. |
| Layered, Testable Architecture | Pass. Provider configuration, packet building, HTTP client, response validation, and Tkinter rendering are separate modules. |
| Verification Before Trust | Pass only with mocked request/response tests, no-leak regression tests, UI non-blocking/error tests, and a manual C-AGENT acceptance after the company supplies its contract. |
| Secure, Reproducible Delivery | Conditional pass. No credential is committed. Implementation stops at the C-AGENT contract gate if URL/auth/retention approval is not supplied. Gemini remains public-fixture-only and disabled. |

## Research Decisions

See [research.md](research.md). The decisive choices are C-AGENT-only production routing, data minimisation before any provider call, no silent provider fallback, and a physically separate Gemini public experiment.

## Project Structure

```text
src/
├── services/
│   ├── operations_case_service.py        # existing selected-run, read-only case
│   ├── operations_ai_packet.py           # new approved/minimised packet builder
│   ├── operations_ai_provider.py         # new provider-neutral interfaces/results
│   ├── operations_cagent_client.py       # new C-AGENT-only HTTP client
│   ├── operations_gemini_experiment.py   # new, isolated public-fixture experiment
│   └── operations_knowledge.py           # existing offline guidance
├── ui/
│   └── operations_assistant.py           # add explicit ask/preview/result state only
└── universal_app.py                       # remains selected-run orchestration only

specs/002-ai-operations-assistant/
├── contracts/
│   ├── operational-case-v1.md
│   ├── cagent-guidance-v1.md
│   └── gemini-public-experiment-v1.md
└── quickstart.md

tests/
├── services/test_operations_ai_packet.py
├── services/test_operations_cagent_client.py
├── services/test_operations_gemini_experiment.py
└── ui/test_operations_assistant.py
```

## Design Boundaries

### C-AGENT company-internal path

1. The user opens an already selected terminal run and sees the current local, deterministic guidance first.
2. The dialog builds a reviewable `CagentGuidancePacket` from verified selected-run facts and technical evidence: FY, CC scope, terminal status, stage, stable classification/confidence, approved local guidance, report/log excerpts, and relevant selected-run paths/locators.
3. The packet is capped and run-bound: it excludes credentials, process environment values, arbitrary external files, another run's evidence, and evidence marked missing or mismatched. It does not need to redact selected-run technical details merely because they are technical.
4. The dialog states that selected-run technical details will be sent to the company C-AGENT service and requires an explicit **Ask C-AGENT** click. It sends no request merely by opening the dialog.
5. The C-AGENT client reads a deployment-provided endpoint and credential only at runtime, requires a configured/approved provider policy, applies a timeout, and returns a bounded, sanitised answer. The answer is displayed as advisory guidance with the packet evidence IDs; it is not written to disk.
6. A missing configuration, policy failure, network error, malformed response, or timeout keeps the local deterministic guidance visible and explains that company AI was unavailable. It never calls Gemini, Nakazasen, a generic router, or any other provider.

### Gemini Web Direct public experiment

- It is enabled only by `MP2027_ENABLE_GEMINI_WEB_EXPERIMENT=1` and an explicit user action.
- It uses a built-in fictional incident card. The experiment API accepts that card type only; it has no `OperationalCase`, `run_id`, history root, file path, free-text, or pasted-data parameter.
- The UI calls it **Public Gemini experiment — fictional data only**, displays the provider/model uncertainty, and never presents its answer as an operational diagnosis.
- It is isolated from C-AGENT configuration and cannot be a retry or fallback target.
- Live public-network execution is manual and optional; CI tests must use a fake transport and make zero external requests.

## Delivery Slices

1. **Contract and privacy gate**: update the feature specification, define packet/provider/experiment contracts, and leave the feature inactive without company configuration.
2. **C-AGENT core**: build the minimiser, configuration validation, HTTP client, response envelope, and exhaustive no-leak/no-fallback tests.
3. **User experience**: add reviewable C-AGENT request/result states without weakening the existing read-only UI or blocking Tkinter.
4. **Public experiment**: add the isolated fictional Gemini Direct probe behind its disabled flag; prove it cannot consume selected-run data.
5. **Acceptance**: run CI-safe checks; conduct one approved C-AGENT manual test on the company network and one Gemini fictional-data test separately. Do not record business content in Git.

## Complexity Tracking

The external-provider exception is justified only for company-approved C-AGENT under the documented minimisation and credential rules. The exact C-AGENT URL, authentication scheme, retention policy, request schema, and company data classification are deployment inputs, not assumptions; Gemini implementation must stop before live production use if any of them is absent.
