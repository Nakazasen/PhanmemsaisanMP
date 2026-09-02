# Recovery UI Flow Contract

## Input

- Active fiscal year.
- One or more selected cost centers.
- A user explicitly clicks the action to use April as March.

## Required outcomes

1. The application identifies each affected cost center as recovered, already valid, or unresolved.
2. A recovered result means the March baseline has been saved with approved-April provenance for that same cost center.
3. An unresolved result names the exact code and does not alter its March data.
4. If any selected code remains unresolved, the recovery dialog stays actionable and calculation does not start.
5. If all affected codes recover, the dialog closes and the normal Run flow retries once.

## Manual entry targeting

- Recovery for one code opens manual staffing on that exact code.
- The main manual-staffing action uses the current selected code only when exactly one code is selected.

## Readiness wording

- When source checks pass but selected March baselines are missing, the UI says that source checks are complete and lists the remaining baseline action.
- It must not state that calculation can run until those selected baseline requirements are met.
