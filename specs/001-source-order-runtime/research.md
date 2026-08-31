# Research: Saved source order

## Decision: separate output order from group mapping

`FiscalRunContext.ordered_sources` has the manifest's global order. The current `_annual_complete_v1_source_order()` instead iterates a hard-coded category tuple and chooses only the first resolved file. Passing a global permutation into `source_file_order` would be unsafe: the writer relies on position 0 for facility formatting and position 5 for allocation formatting.

Use a second `output_source_file_order` argument. It controls only the sequence of already-staged source blocks. `source_file_order` remains the category-to-business-row identity.

## Eligibility decision

The display resolver compares normalized manifest paths with the current `resolved_sources` paths. `resolved_sources` is the fiscal-run eligibility authority, so a disabled, missing, invalid, or unconfirmed manifest row cannot gain an output block. The resolver has no parser or allocation side effects.

## Compatibility decision

When an older/incomplete manifest lacks a mapped source, append that source after the manifest-derived display candidates in stable mapping order. This prevents an existing staged block from being lost.
