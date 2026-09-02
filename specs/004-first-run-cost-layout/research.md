# Research: First-run Cost Layout

## Decision 1: Require an explicit preservation signal

- **Decision**: A source workbook is restored only when it has special-cost metadata, saved row-order metadata, or a configured legacy start row for the selected cost center.
- **Rationale**: A current workbook may be an untouched/form-derived or common-cost-only output. Its mere existence does not prove that it contains user-owned special-cost rows.
- **Alternatives considered**:
  - Require a row marker for every existing file: rejected because it blocks first calculation.
  - Treat every unmarked workbook as legacy manual content: rejected because it creates a false prerequisite for original FORM.
  - Guess manual rows from their content: rejected because that can silently copy or lose financial data.

## Decision 2: Keep malformed known metadata fail-closed

- **Decision**: If a metadata sheet exists but is malformed, preserve the existing error.
- **Rationale**: A malformed marker is evidence of a data-integrity problem, not evidence of first-run status.

## Decision 3: Classify before snapshotting

- **Decision**: The pipeline does not snapshot an unmarked source without a configured legacy start.
- **Rationale**: The engine then receives no source and creates the existing empty, metadata-marked output section.
