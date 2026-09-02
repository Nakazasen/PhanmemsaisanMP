# Research: Reliable March Baseline Recovery

## Decision 1: Treat historical unconfirmed zero records as replaceable only after explicit approval

- **Decision**: A March row is replaceable by April only when it is absent or matches the historic manual UI zero-record signature and is not a valid confirmed baseline.
- **Rationale**: The current validation correctly rejects an unconfirmed all-zero record, but the recovery routine treats any existing manual row as immutable. A narrow predicate resolves that contradiction without changing the meaning of a valid confirmed zero.
- **Alternatives considered**:
  - Mark all old zero rows valid: rejected because it removes the confirmation requirement.
  - Overwrite every invalid baseline: rejected because malformed or incomplete data needs a human review path.

## Decision 2: Recover selected cost centers independently

- **Decision**: Load reviewed source candidates once, then attempt April recovery for each selected code independently.
- **Rationale**: The existing importer returns no data for the whole request when any required code lacks a source. This creates a false "no April data" result for otherwise recoverable codes.
- **Alternatives considered**:
  - Keep atomic recovery: rejected because recovery is per cost center and a missing source must not block unrelated departments.
  - Automatically exclude unavailable codes: rejected because users must see and resolve every selected unavailable code.

## Decision 3: Keep the preflight source report and add a selected-scope baseline state

- **Decision**: Do not redefine the shared source preflight contract. Add a current-selection baseline state to the UI readiness summary and workflow guidance.
- **Rationale**: Source preflight is reusable without a selected cost center, while March-baseline validity is selection-specific. The UI must stop saying an unconditional "ready" when the next Run click will be blocked.
- **Alternatives considered**:
  - Fold manual baseline checks into every source preflight: rejected because it would couple reusable source validation to transient UI selection.
  - Disable Run permanently when a baseline is missing: rejected because Run is the existing entry into the explicit recovery dialog.

## Decision 4: Preserve the selected cost center when opening manual staffing

- **Decision**: Pass the current one-item selection to the editor from the main action and preserve the existing explicit recovery target behavior.
- **Rationale**: The generic editor currently defaults to the first list item when no explicit target is provided, which can show CC 1412000004 while CC 1412000006 is selected.
- **Alternatives considered**:
  - Remove the default entirely: rejected because the editor must remain usable with no current selection.
