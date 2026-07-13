# Phase 42N2A - Exact Source Rows Verification

## Classification

`PASS_PHASE_42N2A_EXACT_ROWS_REDUCED_OR_FALSE_GAP_CONFIRMED`

## Summary

Verified the 4 `EXACT_SOURCE_FOUND` rows from the 136-row trace matrix. No code was changed.

| primary_row | account_code | description | exact_source_file | generated_match | classification | decision | reason_nontech | next_action |
|---:|---|---|---|---|---|---|---|---|
| 150 | 5005116292 | 保険代 | FY2027配賦額一覧 (2025.12.29).xlsx / 配賦額一覧 / row  |  | TEMPLATE_OR_ACCOUNT_MASTER_ONLY_NOT_SOURCE | No code | Insurance/travel allocation metadata exists, but exact monthly event values are not proven. | Confirm travel insurance monthly source rows before coding. |
| 158 | 5005056281 | ガス代 | Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026.xlsx / 勘定科目 / row  | row 46 None ガス代/Tiền gas | TEMPLATE_OR_ACCOUNT_MASTER_ONLY_NOT_SOURCE | No code | Exact text is in template/primary-style rows, but no safe source monthly values for gas were proven. | Find source workbook/sheet with Apr-Mar gas values before coding. |
| 159 | 5005066281 | 電気代 | Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026.xlsx / 勘定科目 / row  | row 44 None 電気代/Tiền điện; row 204 electricity Điện | ALREADY_GENERATED_FALSE_GAP | No code | Generated v1 already has the same business meaning under Facility writer naming. | Treat as identity-match correction, not new output row. |
| 160 | 5005066282 | 水道代 | Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026.xlsx / 勘定科目 / row  | row 45 None 水道代/Tiền nước; row 205 water Nước | ALREADY_GENERATED_FALSE_GAP | No code | Generated v1 already has the same business meaning under Facility writer naming. | Treat as identity-match correction, not new output row. |

## Result

- Exact rows checked: 4
- False-gap rows confirmed: 2
- Real rows implemented: 0
- No full pytest was run.

## Conclusion

Two rows (`電気代`, `水道代`) are already generated as Facility `electricity` and `water`, so they are false-gap identity issues. The remaining exact rows (`ガス代`, `保険代`) are not safe to implement without manual monthly source confirmation.
