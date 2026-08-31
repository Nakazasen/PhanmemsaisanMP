# Uniform and Cup Improvement 807-814 Specification

## Scope

Implement only the uncompleted improvement register entries `Hạng mục cần cải tiến!C807:C814` in `Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx`.

## Business rules

1. Cost center `1412000044` must allocate, for every new hire, one type-1 safety shoe and two mold white electrostatic hats. The prior colour-hat entitlement must not be allocated for this cost center.
2. Cost centers `1412000044`, `1412000056`, and `1412000088` must have collapsible-cup entitlement. New-hire cups use only the worker new-hire delta. Periodic cups remain separately entered actual counts in August and February.
3. The amendment must not change entitlement or allocation behavior for any other cost center, existing type-2 safety shoe, security items, or the role-split hats for `1412000019`.

## Acceptance criteria

- `1412000044` produces type-1 shoe and electrostatic-hat audit/fact rows from new hires and produces no colour-hat row.
- New-hire cup cost for each listed center is based on worker delta, never staff delta; periodic cup rows remain manual-count based.
- Audit provenance for synthetic additions identifies `Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx`, sheet `Hạng mục cần cải tiến`, cells `C807:C814`.
- Existing source workbook entitlement import remains compatible with its current 16 source-backed columns.
- Focused allocation, entitlement-import, source-order, lucky-money, bus, and localization regression tests pass.

## Out of scope

- Entries after row 814, including the G6-to-G5 reclassification work.
- Replacing or editing the operational `原価センタ` source worksheet.
- Changing periodic-cup actual-count input semantics.
