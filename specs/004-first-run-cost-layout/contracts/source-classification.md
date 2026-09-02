# Pipeline Contract: Special-cost Source Classification

For each selected cost center, the export pipeline classifies a candidate existing workbook before copying it to the run workspace.

| Condition | `source_path` | `source_kind` |
|---|---|---|
| Current output has a preservation signal | staged snapshot | `current_fiscal_year` |
| Configured prior-FY inheritance source has a preservation signal or explicit legacy start | inherited workbook | `previous_fiscal_year` |
| Existing workbook has no signal and no explicit legacy start | none | `new_fiscal_year` |
| Metadata is malformed | error | no output |

The result stage creates a new empty special-cost section when `source_path` is absent.
