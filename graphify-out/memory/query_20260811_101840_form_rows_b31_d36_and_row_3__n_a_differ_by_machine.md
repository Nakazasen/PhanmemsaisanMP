---
type: "query"
date: "2026-08-11T10:18:40.537586+00:00"
question: "FORM rows B31:D36 and row 3 #N/A differ by machine or renamed file"
contributor: "graphify"
outcome: "useful"
source_nodes: ["_collect_preserved_unmanaged_rows()", "._write_fixed_rows()", "complete_v1_source_order_writer.py"]
---

# Q: FORM rows B31:D36 and row 3 #N/A differ by machine or renamed file

## Answer

Expanded from original query via vocab: [form, workbook, preserved, protected, lookup, formula, template, output, rows, payload, complete, writer]. Direct workbook inspection proved two internal FORM variants: one has blank QLNN rows; the other has profit lookup keys whose word order does not match the row-3 VLOOKUP. Normalize the copied output contract and force full recalculation.

## Outcome

- Signal: useful

## Source Nodes

- _collect_preserved_unmanaged_rows()
- ._write_fixed_rows()
- complete_v1_source_order_writer.py