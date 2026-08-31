# Feature Specification: Honor Saved Source File Order

**Feature Branch**: `001-source-order-runtime`
**Created**: 2026-08-31
**Status**: Approved for implementation
**Input**: Users report that changing file order in the Source File Order editor does not affect the calculation output.

## User Scenarios & Testing

### User Story 1 - Export in saved source order (Priority: P1)

An operator confirms source files, moves them up or down, saves the source manifest, and runs the calculation. The result presents source blocks in exactly that saved order.

**Why this priority**: The editor otherwise makes a promise that the final workbook does not fulfill.

**Independent Test**: Save a manifest whose enabled files differ from the historical category order, run the complete output writer, and verify that source provenance blocks follow the saved sequence.

**Acceptance Scenarios**:

1. **Given** enabled recognized files in a saved manifest, **When** the operator changes their order and saves, **Then** the next output orders its source blocks by that saved order.
2. **Given** a saved order that differs from FY2027 compatibility order, **When** the calculation runs, **Then** no compatibility default overrides the saved order.

### User Story 2 - Preserve financial behavior and traceability (Priority: P2)

An operator uses a reordered manifest without changing classifications or enabled flags. The calculation continues to use the same eligible inputs and produces the same values; only source-block placement and audit order change.

**Independent Test**: Compare source identities, formulas, amounts, and protected rows before and after a display-order-only permutation.

**Acceptance Scenarios**:

1. **Given** the same enabled sources, **When** only their manifest positions change, **Then** source selection, allocation values, formulas, and validation outcomes stay unchanged.
2. **Given** disabled, missing, or unconfirmed files, **When** an output is generated, **Then** those files do not gain output blocks merely because they appear in the manifest.

### Edge Cases

- A legacy or incomplete manifest lacks an eligible file required by an existing source-group writer.
- A manifest contains multiple files in one category, but only some of them participate in the current run.
- Existing source-order-marked rows are re-exported after the manifest is reordered.

## Requirements

### Functional Requirements

- **FR-001**: The saved manifest order MUST be the order used to place eligible source blocks in complete workbook output and source-order audit metadata.
- **FR-002**: The system MUST keep the existing category-to-business-row mapping separate from the operator's output ordering.
- **FR-003**: Only files that are enabled, valid, and resolved for the current fiscal run MAY participate in the operator-controlled output order.
- **FR-004**: Any eligible mapped source omitted from the saved display order MUST be appended deterministically, preserving compatibility and preventing data loss.
- **FR-005**: Reordering alone MUST NOT alter source classification, validation, allocation values, formulas, protected FORM rows, or Cost Center isolation.
- **FR-006**: The run audit/provenance MUST expose the resolved operator-controlled source order.

### Key Entities

- **Source manifest entry**: A saved filename, classification, enabled state, and user-assigned position.
- **Source-group mapping**: The stable category-to-business-row identity required by existing workbook writers.
- **Resolved display order**: The ordered subset of manifest files that is eligible for the active run, followed by deterministic compatibility fallbacks.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A saved permutation of at least seven eligible source files is reproduced exactly in generated source-block provenance.
- **SC-002**: Focused source-order, fiscal-run, and workbook-writer regressions pass with no value/formula regression.
- **SC-003**: Disabled, missing, and unconfirmed source entries create zero new source blocks.
- **SC-004**: A repeated export with the same manifest is deterministic.

## Assumptions

- The requested order governs workbook source-block placement and audit/provenance, not parser execution order or financial precedence.
- Existing category validation and input aggregation remain the authority for eligibility and calculation values.
- The Source File Order editor continues to save `source_file_order.xlsx` as the annual manifest.
