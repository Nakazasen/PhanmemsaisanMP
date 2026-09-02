# Data Model: First-run Cost Layout

## Preservation Signal

| Signal | Meaning | Restoration action |
|---|---|---|
| Special-cost metadata for the selected CC | Prior output recorded the manual-section bounds | Snapshot and restore it |
| Saved row-order metadata for the selected CC | Prior output recorded user order | Restore mixed layout |
| Configured legacy start row for the selected CC | User explicitly identifies an old manual section | Snapshot rows from that start |
| No signal | Original or common-cost-only source | Do not snapshot; create empty output section |

## State Rules

- `known_layout`: at least one preservation signal exists.
- `first_run`: no preservation signal exists.
- `invalid_known_layout`: metadata is present but invalid; stop with an actionable error.

## Relationships

- Classification is per cost center.
- A source workbook is never modified during classification.
- First-run output creates its own marker for future runs.
