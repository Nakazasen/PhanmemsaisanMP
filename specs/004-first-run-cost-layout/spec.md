# Feature Specification: First-run Cost Layout

**Feature Branch**: `004-first-run-cost-layout`

**Created**: 2026-09-02

**Status**: Ready for implementation

**Input**: User description: "Dùng SpecKit sửa lỗi: lần đầu chạy tính toán với FORM nguyên bản không thể đòi dấu mốc chi phí riêng."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run an original form for the first time (Priority: P1)

When a cost center has no previously saved user-owned special-cost section, a user can run the original FORM without being asked to provide a legacy row marker.

**Why this priority**: The current error blocks a first calculation before the app can create its own special-cost section.

**Independent Test**: A generated cost-center workbook with no special-cost metadata, no saved row order, and no configured legacy marker finishes with a new empty special-cost section.

**Acceptance Scenarios**:

1. **Given** an original/unmarked workbook for the selected cost center, **When** the user runs calculation for the first time, **Then** calculation completes and creates an empty, traceable special-cost section in the result.
2. **Given** the unmarked workbook has no user-owned special-cost layout, **When** it is considered for restoration, **Then** the app does not ask the user to identify a starting row.

---

### User Story 2 - Preserve known user-owned special costs (Priority: P2)

When a prior workbook has saved special-cost metadata, saved row ordering, or a project-configured legacy starting row, the app preserves that known user-owned content on the next run.

**Why this priority**: Removing the first-run block must not erase special costs whose ownership is known.

**Independent Test**: A source workbook carrying each supported preservation signal continues through the existing preservation path.

**Acceptance Scenarios**:

1. **Given** a prior workbook has a saved special-cost marker or saved row layout, **When** calculation runs again, **Then** that layout is restored.
2. **Given** a legacy workbook has manual rows and an explicit configured start row, **When** calculation runs, **Then** those rows are preserved.

### Edge Cases

- A malformed saved marker remains an error; it must not be silently ignored as a first-run form.
- A workbook with no known preservation signal is treated as having no restorable user-owned special-cost content.
- No source workbook is modified during classification or restoration.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow first calculation from an original/unmarked form without requiring a special-cost row marker.
- **FR-002**: The system MUST create a new empty, traceable special-cost section for the resulting workbook when no prior special-cost content is known.
- **FR-003**: The system MUST preserve the existing restoration path when a source workbook has saved special-cost metadata, saved row-order metadata, or an explicit legacy start configured for the same cost center.
- **FR-004**: The system MUST continue to reject malformed known metadata rather than classifying it as first-run input.
- **FR-005**: The regression suite MUST cover original first-run classification and preservation-signal classification without changing a source workbook.

### Key Entities

- **Preservation signal**: Evidence that a prior workbook contains user-owned special-cost content: a saved special-cost marker, saved row-order metadata, or configured legacy start row.
- **First-run source**: A workbook without a preservation signal, which contributes no user-owned special-cost rows to the new result.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-run unmarked workbook completes the special-cost stage without a marker error in automated regression testing.
- **SC-002**: All tested workbooks with a preservation signal keep using the preservation path.
- **SC-003**: Source-workbook byte content remains unchanged in automated regression checks.

## Assumptions

- A user who needs to preserve an old unmarked manual section records its start row in the existing project configuration.
- This change does not modify cost values, formulas, shared cost rows, or FORM layout before output generation.
