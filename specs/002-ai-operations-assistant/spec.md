# Feature Specification: AI Operations Assistant

**Feature Branch**: `002-ai-operations-assistant`  
**Created**: 2026-09-01  
**Status**: Implemented through T026; manual acceptance (T027) pending  
**Input**: A user can select a failed or incomplete MP2027 run and receive plain-language, evidence-based guidance for investigating and correcting it. Automated repair is explicitly deferred.

## Purpose and Scope

The first release is a safe support assistant, not an autonomous operator. It helps a user understand a known run failure, identify the affected fiscal year, Cost Center, source file and validation stage, then follow a documented repair path.

It may read approved local evidence from the selected run. It must not edit Excel workbooks, CSV files, project configuration, databases, source code, or release artifacts. It must not start a new calculation or send business data to an external AI service without an explicit future approval.

## User Scenarios & Testing

### User Story 1 - Open one error case with its evidence (Priority: P1)

After a calculation fails or is incomplete, a user opens the assistant from that run and sees one clear case: what failed, who is affected, the evidence used, and whether the system can safely identify a next step.

**Why this priority**: Without a trustworthy case record, any AI answer would be a guess.

**Independent Test**: Create a run with a known preflight or pipeline failure; the user can open its case and see the same run ID, FY, CC scope, stage, error code, source-path references, and evidence links as the stored run report.

**Acceptance Scenarios**:

1. **Given** a failed run with reports, **When** the user opens the assistant, **Then** the assistant shows only evidence from that selected run and labels missing evidence as unavailable.
2. **Given** a successful run, **When** the user opens the assistant, **Then** it can explain that there is no failure case and may show only non-destructive follow-up information.
3. **Given** an old run without the new case record, **When** the user opens the assistant, **Then** it explains that the record is insufficient and offers the existing report/log paths; it does not invent a diagnosis.

---

### User Story 2 - Receive plain-language repair guidance in the selected language (Priority: P2)

A user receives a short explanation in the current interface language: what happened, why it matters, what file or setting to inspect, and the safe next action. The main answer uses everyday operational language rather than exception names, JSON keys, stack traces, or internal pipeline terminology. Every recommendation identifies the evidence that supports it.

**Why this priority**: The practical value is reducing time spent translating technical logs into a correct next step.

**Independent Test**: Use a catalog of reproducible known errors. For each case, the displayed explanation names the expected affected scope and prescribed steps, and contains no recommendation that modifies data automatically.

**Acceptance Scenarios**:

1. **Given** an error that matches an approved knowledge entry, **When** the user requests guidance, **Then** the assistant presents the approved steps and links them to the selected run evidence.
2. **Given** an unknown or ambiguous error, **When** the user requests guidance, **Then** the assistant says that the cause is not confirmed, lists the available evidence, and directs the user to an existing manual investigation path.
3. **Given** the interface language is Vietnamese, English, or Japanese, **When** guidance is shown, **Then** headings, buttons, warnings, and the standard repair steps use that language.
4. **Given** any supported error, **When** guidance is shown, **Then** its primary view clearly separates: what happened, confidence, affected scope, what the user should do, and the evidence used.
5. **Given** technical evidence is available, **When** the user opens guidance, **Then** file paths, run IDs, source names, raw log lines, exception names, or report JSON are shown only as labelled evidence or optional technical details, never as the primary explanation or instruction.

---

### User Story 3 - Save an investigation note for future support (Priority: P3)

After resolving a case manually, an authorized user can save a concise resolution note that preserves the evidence and outcome for future support. The note does not alter calculation inputs or claim that a rule is globally valid without review.

**Why this priority**: A growing, reviewed case library lets later AI assistance learn from confirmed operational experience rather than from raw, ambiguous logs.

**Independent Test**: Save a resolution note against a known run, reopen it, and verify its author, time, evidence references, and approval state are preserved without changing the original run record.

**Acceptance Scenarios**:

1. **Given** a selected case, **When** an authorized user records a resolution, **Then** the original error evidence remains unchanged and the resolution is stored as a separate reviewed note.
2. **Given** an unreviewed note, **When** another user opens a similar case, **Then** the note is clearly marked as unreviewed and is not treated as a confirmed repair rule.

## Edge Cases

- A log/report path is missing, moved, unreadable, or belongs to a different FY/CC.
- A run contains private local paths or sensitive business values that cannot be sent outside the workstation.
- Multiple errors happen in one run; each diagnosis must retain the relevant source and scope.
- The assistant cannot match an error to a confirmed knowledge entry.
- A selected language lacks a required translated entry or user-facing label.
- A report contains a technical exception, JSON field, or stack trace that is useful as evidence but would not be understandable as the main explanation.
- A user attempts to treat guidance as permission to alter source data or rerun the pipeline automatically.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST create or reconstruct a read-only operational case from an existing run without changing that run's inputs, outputs, history, or audit reports.
- **FR-002**: Each case MUST identify the fiscal year, Cost Center scope, run identifier, processing stage, outcome, evidence locations, and a stable error classification when available.
- **FR-003**: The system MUST preserve a distinction between confirmed facts, inferred possibilities, and unavailable evidence.
- **FR-004**: The system MUST provide guidance only from approved local knowledge and selected-run evidence in the first release.
- **FR-005**: Every displayed recommendation MUST show the source evidence or knowledge entry on which it is based.
- **FR-006**: The system MUST present all assistant headings, confidence labels, warnings, safe actions, known-error guidance, and unknown-error guidance in the currently selected Vietnamese, English, or Japanese interface language.
- **FR-007**: The system MUST refuse any action that would write to business input, output, configuration, database, source code, or release artifacts in the first release.
- **FR-008**: The system MUST record user-created resolution notes separately from immutable run evidence, including author, timestamp, review state, and referenced case.
- **FR-009**: The system MUST keep the feature usable when AI/model connectivity is absent by showing evidence and approved non-AI guidance only.
- **FR-010**: The system MUST not transmit local run evidence to an external provider until the owner approves a separate data-sharing, retention, and provider decision.
- **FR-011**: The primary guidance view MUST use plain operational language and answer, in a consistent structure: what happened, how certain the conclusion is, what fiscal year/Cost Center/source is affected, what the user should do safely, and which evidence supports the conclusion.
- **FR-012**: Raw exception text, internal stage names, JSON fields, traceback content, and unprocessed logs MUST be limited to an explicitly labelled technical-details or evidence view. They MUST NOT be presented as the primary reason or repair instruction.
- **FR-013**: Known guidance and the unknown-error fallback MUST use approved written Vietnamese, English, and Japanese text. The system MUST NOT rely on runtime machine translation or silently show a different user-visible language when a required translation is unavailable.

### Key Entities

- **Operational Case**: A read-only support view of one run or one error within a run, with scope and evidence references.
- **Evidence Reference**: A verified pointer to a report, log segment, validation result, or approved documentation section.
- **Error Classification**: A stable code and category that distinguishes known, ambiguous, and unavailable diagnoses.
- **Knowledge Entry**: A reviewed explanation of a known error, its conditions, and safe user actions.
- **Guidance Presentation**: The language-specific, user-facing explanation of a case, including its plain-language summary, certainty, actions, evidence labels, and optional technical-detail label.
- **Resolution Note**: A user or reviewer note associated with a case; it never changes the original evidence.

## Success Criteria

### Measurable Outcomes

- **SC-001**: For every supported known failure, a user can open a case and reach an evidence-backed next step in under two minutes.
- **SC-002**: In acceptance cases, 100% of guidance displays its FY, CC scope, evidence source, and confidence status.
- **SC-003**: In acceptance cases for unknown errors, 100% of responses explicitly state that the cause is unconfirmed rather than presenting a fabricated fix.
- **SC-004**: The first release performs zero unapproved writes to business inputs, outputs, configuration, databases, code, or release artifacts.
- **SC-005**: Standard known-error guidance is available in all three supported interface languages.
- **SC-006**: In acceptance fixtures for every supported language, 100% of known and unknown responses contain the required primary sections in the selected language and do not expose raw exception text, JSON, or internal keys as their primary explanation.

## Assumptions

- Existing run history, preflight reports, audit reports, and UI logs are the initial evidence sources.
- The workbook and approved operational documentation remain the business source of truth; an assistant cannot replace them.
- Gemini Flash is the implementation worker for small reviewed tasks, not an authorization to send production business data to Gemini at runtime.
- Literal source file names, run IDs, Cost Center codes, and user-entered business names may remain unchanged as evidence; their surrounding labels and explanation must use the selected interface language.
- Any future external AI provider, data-retention policy, credentials, model selection, or automatic repair capability is a separate approved feature.
- The first deployable slice is User Story 1 plus a small catalog of deterministic, approved guidance; it does not depend on a live LLM.
