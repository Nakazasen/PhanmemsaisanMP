<!--
Sync Impact Report
- Version change: template (unversioned) → 1.0.0
- Modified principles: placeholder principles → five MP2027 engineering principles
- Added sections: Data & Output Safety Constraints; Development Workflow & Quality Gates
- Removed sections: none
- Follow-up TODOs: none
-->
# MP2027 Manager Constitution

## Core Principles

### I. Financial Data and Evidence Integrity

The canonical business workbook takes precedence over derived Markdown, handover notes,
and inferred assumptions. The system MUST NOT invent values, substitute Cost Center data,
turn blanks into zero, or silently accept incomplete source data. Missing, invalid, or
ambiguous input MUST fail closed: preserve the blank where required, record the gap in an
audit or missing-input artifact, and require explicit business confirmation before a rule
is changed. This protects financial planning accuracy and makes every output explainable.

### II. Excel Template and Output Fidelity

The application MUST preserve approved FORM workbook structure, sheet conventions,
formatting, formulas, source-file order, and output placement unless a verified business
requirement explicitly authorizes a change. Allocation, workbook-writing, fiscal-calendar,
and account-resolution behavior requires focused regression coverage and evidence before
modification. Generated workbook output is trusted only after the relevant validation and
audit checks have passed.

### III. Layered, Testable Python Architecture

Business rules belong in engine and service modules; Tkinter handlers in `src/universal_app.py`
MUST remain orchestration and presentation code. Persistence, fiscal-run resolution, Excel
utilities, allocation, and export responsibilities MUST remain separated with explicit
interfaces. Shared components with broad dependency impact—especially `AllocationEngine`,
`HubBuilder`, fiscal-run services, and Excel helpers—MUST receive targeted tests whenever
changed. New coupling, hidden global state, and UI-driven domain rules require a documented
justification in the implementation plan.

### IV. Verification Before Trust

Every code change MUST be proportionately verified before it is reported complete. At a
minimum, compile the affected Python areas and run the CI-safe pytest profile unless a
narrower validated command is more appropriate. Changes to financial rules, workbooks,
exports, packaging, updates, or persistence MUST include targeted regression tests; a new
reproducible defect MUST receive a regression test when practical. Real-workbook,
acceptance, performance, package, or clean-machine checks that were not run MUST be stated
explicitly with the reason and residual risk.

### V. Secure, Reproducible Delivery and Repository Hygiene

Secrets, credentials, private company source files, runtime databases, generated output
workbooks, caches, and transient build artifacts MUST NOT be committed. Release, updater,
backup, rollback, and portable-bundle contracts MUST be preserved and validated when
changed. Operational behavior changes MUST update the relevant handover, architecture,
requirement, or release documentation so a subsequent maintainer can reproduce and audit
the result.

## Data & Output Safety Constraints

- `raw/Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx` is the highest-priority
  canonical business input unless an approved replacement is documented.
- The program MUST not use a root-level legacy `FORM.xlsx` as a fallback where the current
  workflow requires `docs/MP2027/FORM.xlsx`.
- Cost-center isolation is mandatory: cross-Cost-Center fallback requires an explicit,
  documented business rule and test evidence.
- Each output-affecting change MUST preserve or improve traceability through run history,
  audit reports, source provenance, and missing-input reporting.
- External input paths and update packages MUST be validated before use; errors MUST be
  actionable and must not create fabricated output.

## Development Workflow & Quality Gates

1. Ground planned work in the canonical workbook and current repository documentation before
   changing a business rule.
2. Keep feature work scoped; document affected data flow, modules, output contracts, and
   test profile in the implementation plan.
3. Implement with the smallest safe change, preserving unrelated comments and docstrings.
4. Run the relevant validation profile:
   - CI-safe: `py -m pytest -m "not requires_raw_excel and not real_pipeline_acceptance and not performance" -q`
   - Local regression where canonical raw data is available: `py -m pytest -m "not performance" -q`
   - Compile check: `py -m compileall src scripts packaging`
5. Review generated outputs and audit evidence for changes that affect financial calculations,
   Excel writers, fiscal periods, input resolution, or packaging.
6. Record material behavior, safety, or operational changes in durable documentation and
   state exactly which checks passed, failed, or were intentionally not run.

## Governance

This constitution supersedes local implementation preferences where they conflict. Every
feature specification, plan, task list, code review, release decision, and acceptance
summary MUST evaluate compliance with these principles. A violation is permitted only when
an approved business requirement documents the exception, rationale, impact, migration or
rollback approach, and compensating verification.

Amendments require a documented proposal, review against canonical business evidence, and
an updated Sync Impact Report at the top of this file. Versioning follows semantic intent:
MAJOR for incompatible removal or redefinition of governance, MINOR for a new principle or
materially expanded requirement, and PATCH for clarifications that do not change policy.
Compliance review occurs during planning and final verification; unresolved deviations must
be reported as residual risk rather than concealed.

**Version**: 1.0.0 | **Ratified**: 2026-08-04 | **Last Amended**: 2026-08-04
