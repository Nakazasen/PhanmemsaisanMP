# Feature Specification: Reliable March Baseline Recovery

**Feature Branch**: `003-baseline-recovery`

**Created**: 2026-09-02

**Status**: Ready for implementation

**Input**: User description: "Dùng SpecKit để sửa cẩn thận lỗi T3 cũ, sao chép T4, trạng thái sẵn sàng và chọn đúng phòng."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recover one blocked cost center (Priority: P1)

When a user runs one cost center whose March baseline is absent or is a legacy unconfirmed zero record, the user can explicitly choose to use that cost center's valid April staffing as March. The calculation then proceeds only after the replacement has been saved and verified.

**Why this priority**: This is the immediate production-blocking defect for CC 1412000006 and CC 1412000040.

**Independent Test**: With a legacy zero March record and a valid April record for the same cost center, choose the April recovery action and confirm that the March record becomes valid. Repeat with no valid April record and confirm that no data changes.

**Acceptance Scenarios**:

1. **Given** a selected cost center has an invalid legacy all-zero March record and valid April staffing, **When** the user explicitly approves April recovery, **Then** the March record is replaced with a traceable approved-April baseline for that same cost center.
2. **Given** a selected cost center has no valid April staffing, **When** the user chooses April recovery, **Then** the app names that cost center as unresolved and does not claim that April was used.
3. **Given** a selected cost center has a valid manually entered March baseline, **When** the user chooses recovery, **Then** the existing baseline is not overwritten.

---

### User Story 2 - Recover multiple cost centers without collateral failure (Priority: P2)

When several cost centers need March baselines, the app recovers every cost center that has valid April staffing and clearly reports only the remaining unresolved cost centers.

**Why this priority**: A missing source for one cost center must not prevent recovery of unrelated cost centers.

**Independent Test**: Use a selection containing two recoverable cost centers and one cost center without April data; verify that the two recoverable ones are saved and that the third is reported separately.

**Acceptance Scenarios**:

1. **Given** a multi-cost-center selection contains both valid and unavailable April sources, **When** the user approves April recovery, **Then** every recoverable cost center is recovered and only unavailable cost centers remain unresolved.
2. **Given** recovery finishes with unresolved cost centers, **When** the result is shown, **Then** the message identifies the exact unresolved codes and directs the user to manual entry for those codes.

---

### User Story 3 - Understand readiness and enter data in the correct place (Priority: P3)

Before pressing Run, a user can see that the selected scope still needs a March baseline. If the user opens manual staffing from that workflow, the form opens on the blocked cost center rather than an unrelated first item.

**Why this priority**: The current ready message and unrelated default cost center cause avoidable clicks and wrong data entry.

**Independent Test**: Select a cost center with an invalid baseline, refresh the readiness state, and open manual staffing from the recovery flow; confirm the scope warning appears before calculation and the editor initially displays the selected code.

**Acceptance Scenarios**:

1. **Given** selected cost centers are otherwise source-ready but need March baselines, **When** readiness is displayed, **Then** it does not state that calculation can run without action.
2. **Given** a single cost center is blocked for March baseline, **When** the user chooses manual entry, **Then** the form opens on that cost center.
3. **Given** the user opens manual staffing from the main action while exactly one cost center is selected, **When** the editor opens, **Then** it initially displays that selected cost center.

### Edge Cases

- A confirmed all-zero March baseline remains valid only when it was explicitly saved under the current confirmation rule; legacy zero records are never silently treated as confirmed.
- April recovery may only use data for the same fiscal year and same cost center; it must not substitute a different department's values.
- If April data is incomplete, negative, or internally inconsistent, recovery leaves that cost center unchanged and reports the reason.
- A partial multi-cost-center recovery must be traceable per recovered code and must not start the calculation while any selected code remains unresolved.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST distinguish a valid confirmed March baseline from a legacy unconfirmed March record, including an all-zero record.
- **FR-002**: After explicit user approval, the system MUST replace only an invalid legacy March record with valid April staffing from the same cost center and fiscal year.
- **FR-003**: The system MUST preserve a valid manual March baseline and never replace it through the April recovery action.
- **FR-004**: For a multi-cost-center recovery, the system MUST process each cost center independently and report recovered and unresolved codes separately.
- **FR-005**: The system MUST not present an unavailable April source as though it were absent when another selected cost center has usable April data.
- **FR-006**: The readiness message for the current selected scope MUST identify missing March baselines before the user begins calculation.
- **FR-007**: The manual staffing editor MUST default to the one selected cost center when invoked from the main action or the recovery action; when no single cost center is selected, it may retain its normal chooser behavior.
- **FR-008**: Recovery and manual-entry outcomes MUST be logged with the affected cost-center code and must not create calculation output before all selected baselines are valid.
- **FR-009**: The regression suite MUST cover legacy-zero replacement, valid-baseline preservation, partial multi-cost-center recovery, readiness messaging, and editor target selection.

### Key Entities

- **March baseline**: The fiscal-year March staffing record required before cost calculation, including confirmation provenance.
- **April recovery candidate**: The validated April staffing record for the same cost center that a user may explicitly approve as a March substitute.
- **Recovery outcome**: The per-cost-center result: recovered, already valid, or unresolved with a human-readable reason.
- **Selected scope**: The cost center or cost centers the user has chosen for the next calculation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can recover a single affected cost center with a valid April source in one confirmation action and then proceed to calculation without reopening the manual-entry form.
- **SC-002**: In a mixed selection, 100% of cost centers with valid April data are recovered while each unavailable cost center is listed individually.
- **SC-003**: No valid manually confirmed March baseline is changed by the recovery action in automated regression checks.
- **SC-004**: A selected scope with an unresolved March baseline never displays an unconditional "ready to calculate" message.
- **SC-005**: Automated regression tests reproduce the historical `MANUAL_GUI` all-zero record and verify the corrected outcome.

## Assumptions

- Using April as March remains an explicit user decision; the application will not perform this substitution automatically.
- The existing source-validation rules remain authoritative for deciding whether April staffing is usable.
- The change is limited to staffing-baseline recovery, readiness wording, and manual-editor targeting; it does not alter cost formulas, workbook output layout, or AI assistant behavior.
