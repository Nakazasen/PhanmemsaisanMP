# Data model

| Entity | Source | Meaning |
|---|---|---|
| `source_file_order` | `_annual_complete_v1_source_order` | Stable category-to-business-row mapping; exactly the historic writer contract. |
| `output_source_file_order` | `FiscalRunContext.ordered_sources` filtered by `resolved_sources` | Operator-controlled global sequence for writing already-classified source blocks. |
| staged row `source_file` | workbook provenance note | Immutable source identity used for grouping and audit. |

`output_source_file_order` may be a strict subset of `source_file_order`; the writer appends unmapped display entries deterministically only when staged rows exist.
