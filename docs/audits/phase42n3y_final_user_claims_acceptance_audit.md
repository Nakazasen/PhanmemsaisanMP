# Phase 42N3Y - Final user claims acceptance audit

CLASSIFICATION: PARTIAL_PHASE_42N3Y_ACCEPTANCE_BLOCKED_BY_MISSING_DRIVER_DATA

## Scope

- Phase: `PHASE_42N3Y_FINAL_USER_CLAIMS_ACCEPTANCE_AUDIT`
- Mode: read-only audit; no code fix, no full pytest, no commit, no push.
- Requirement source used for generation: `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026.xlsx`
- Requirement source explicitly not used: `raw/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026_ảnh.xlsx`
- Runtime stale workbook `OUTPUT_FY2027/MP_CC_1412000040.xlsx` was not used as evidence.

## Precheck

| Item | Result |
| --- | --- |
| Branch | `main` |
| Starting HEAD | `fdd86909c7eaef41ecc57de72f35aee071be3367` |
| Fetch | `git fetch origin main` completed |
| `origin/main...HEAD` | `0 0` |
| Commit/push | No commit, no push |

Recent relevant commits at audit start:

- `fdd8690 fix(output): scope reference-assisted fill rows`
- `7e61b8d fix(output): enforce column S descriptions by cost rows`
- `9b185eb fix(output): dedupe new-hire allocation identity`
- `7db14d6 fix(allocator): fail closed on incomplete headcount drivers`
- `f281c7c docs(audit): record nonempty output user claims reaudit`

Known dirty/runtime/reference leftovers were preserved and not staged:

- `OUTPUT_FY2027/MP2027_AUDIT_REPORT.md`
- `OUTPUT_FY2027/MP2027_MISSING_INPUTS.csv`
- `mp2027.db`
- `raw/FORM.xlsx`
- `docs/audits/phase42n3k_fixed_asset_cc_full_data_audit.md`
- `raw/requirements/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026.xlsx`
- `reference_outputs/secondary/FY2027/`
- prior temp audit folders under `OUTPUT_FY2027/tmp_phase42n3s_reaudit/`, `tmp_phase42n3u_headcount_fail_closed/`, `tmp_phase42n3w_column_s_rule/`, and `tmp_phase42n3x_reference_fill_scope/`

## Fresh generation

Command path used from `OUTPUT_FY2027/tmp_phase42n3y_final_acceptance`:

```powershell
py -3 D:\Sandbox\MP2027\scripts\run_e2e.py --source D:\Sandbox\MP2027\raw --target-cc <CC> --mp-saisan-complete-v1
```

| CC | Result | Output |
| --- | --- | --- |
| `1412000040` | PASS, workbook generated | `OUTPUT_FY2027/tmp_phase42n3y_final_acceptance/OUTPUT_FY2027/MP_CC_1412000040.xlsx` |
| `1412000006` | FAIL-CLOSED preflight; no partial workbook | `Reference-assisted fill requires --primary-reference-path for this target CC.` |

Target generation stats:

| Metric | Value |
| --- | ---: |
| Workbook size | 154,000 bytes |
| Sheet | `内訳ﾘｽﾄ(4～3月)` |
| `max_row` | 1015 |
| `max_col` | 55 |
| Workbook cost/provenance rows by formula scan | 25 |
| Complete-v1 source-order rows written | 14 |
| Complete-v1 source blocks written | 6 |
| Complete-v1 primary reference rows written | 0 |
| Complete-v1 primary reference rows quarantined | 130 |
| Complete-v1 final business rows reported by CLI | 52 |

Audit method:

- Workbook values were read with `openpyxl` using `data_only=False`.
- Formula strings in `F:Q` were treated as cost-bearing using `src.engine.column_s_normalizer.cell_has_month_cost`.
- Month/cost columns audited: `F:Q`.
- Column `S` audited as the user-facing explanation/remarks column.
- Column `T` audited as provenance.

## Claim 1 - Duplicate new-hire office/stationery costs

Result: PASS_FAIL_CLOSED.

The generated target workbook has no duplicate or misaligned new-hire office/stationery costs. The previously bad `=28*9100` pattern is absent.

| Row | B | S | T | Month costs in `F:Q` |
| ---: | --- | --- | --- | --- |
| 88 | blank | blank | blank | none |
| 90 | blank | blank | blank | none |
| 91 | blank | blank | blank | none |
| 95 | blank | blank | blank | none |
| 96 | blank | blank | blank | none |
| 188 | blank | blank | blank | none |
| 189 | blank | blank | blank | none |

Formula scan result:

- Formulas containing `9100`: 0.
- Formulas containing `3600`: 0.
- Formulas containing `28*` or `*28`: 0.

DB cross-check:

- `fact_input_data` rows for target `1412000040` and accounts `5005246281` / `5005246288`: 0.
- `fact_input_data` rows for supplemental `1412000006` and accounts `5005246281` / `5005246288`: 0 after the fail-closed driver check.

The acceptance caveat is that the target CC still lacks monthly headcount driver data, so the absence of duplicate amounts is a fail-closed result, not proof that target new-hire amounts can be calculated.

## Claim 2 - New-hire office costs still use total headcount

Result: PASS_FAIL_CLOSED.

No generated target formula uses total-headcount-style multiplication for new-hire office/stationery items. The workbook has no `=28*9100`, `=28*3600`, `28*`, or `*28` formula hits in `F:Q`.

Driver evidence:

| Source | Evidence |
| --- | --- |
| `fact_monthly_headcount` for `1412000040` | 0 rows |
| `dim_cost_centers` for `1412000040` | `staff_count=0`, `worker_count=0` |
| Missing input CSV | one manual headcount review row plus event-delta missing-driver rows |
| `fact_monthly_headcount` for supplemental `1412000006` | only `202701=28`, `202702=28`, `202703=28` |
| Supplemental complete-v1 output | no `MP_CC_1412000006.xlsx` produced because reference-map preflight fails before workbook export |

This is the intended fail-closed behavior: incomplete event-delta headcount data no longer creates a first-month total-headcount allocation.

## Claim 3 - New-hire monthly delta availability

Result: BLOCKED_BY_MISSING_DRIVER_DATA, with safe fail-closed behavior.

The target output still cannot calculate real new-hire monthly amounts because the canonical driver data is missing. Unlike the earlier audit, the allocator now records actionable missing-input rows and suppresses the allocation instead of treating missing previous months as zero.

| Evidence | Value |
| --- | --- |
| `fact_monthly_headcount` rows for `1412000040` | 0 |
| `dim_cost_centers` fallback for `1412000040` | `staff_count=0`, `worker_count=0` |
| CSV rows for `1412000040` | 39 total |
| CSV `headcount_event_delta` rows for `1412000040` | 36 |
| Example missing period | `202604` requires current month `202604` and previous month `202603` |

Conclusion: the code path is safer, but final acceptance with real target new-hire amounts is blocked until the target CC has a complete monthly headcount series, including the previous month needed for event-delta rules.

## Claim 4 - Column S rule

Result: PASS.

Rule audited: from row 30 onward, rows with any month cost in `F:Q` must have an explanation in `S`; rows without any month cost in `F:Q` must not have an explanation in `S`.

Target `1412000040` results:

| Metric | Count |
| --- | ---: |
| Rows with cost but blank `S` | 0 |
| Rows without cost but nonblank `S` | 0 |

Previously bad no-cost rows are now blank in `S`:

| Row | S | Month costs |
| ---: | --- | --- |
| 31 | blank | none |
| 53 | blank | none |
| 56 | blank | none |
| 57 | blank | none |
| 87 | blank | none |

Valid cost rows retain `S`; for example row 168 has `減価償却費（建物）/Khấu hao (Nhà)` and 12 month formulas.

## Claim 5 - Seven source-file block spacing

Result: PARTIAL_PASS_FOR_WRITTEN_BLOCKS.

All written source-order blocks have exactly one blank row between adjacent blocks. However, only 6 blocks are present in the fresh target workbook, not the prior 7, because the allocation-rule block that previously contained new-hire rows is suppressed by the fail-closed missing headcount driver check.

| Block | Source | Start | End | Rows | Blank gap before |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `施設課 MPFY2027.xlsx` | 168 | 173 | 6 | n/a |
| 2 | `固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx` | 175 | 176 | 2 | 1 |
| 3 | `システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls` | 178 | 178 | 1 | 1 |
| 4 | `総務課 FY2027 MP 振替予定.xlsx` | 180 | 182 | 3 | 1 |
| 5 | `Sinh nhật MP FY2027.xlsx` | 184 | 184 | 1 | 1 |
| 6 | `Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx` | 186 | 186 | 1 | 1 |

Conclusion: spacing passes for populated blocks. A strict "seven populated blocks" acceptance cannot pass on this target data until the missing allocation/headcount driver data is supplied and the allocation-rule rows are safely generated.

## Claim 6 - Garbage from row 168 onward

Result: PASS.

Row 168 is valid source-order output, not garbage:

| Row | B | S | T | Month costs |
| ---: | --- | --- | --- | ---: |
| 168 | `5006016260` | `減価償却費（建物）/Khấu hao (Nhà)` | `source_file=施設課 MPFY2027.xlsx; original_row=36; source-order-complete-v1` | 12 |

Reference-fill risk is removed from the user-facing workbook:

| Metric | Count |
| --- | ---: |
| `REFERENCE_FILLED_FROM_PRIMARY` rows in workbook | 0 |
| Unscoped primary reference rows in workbook | 0 |
| Scoped primary reference rows in workbook | 0 |
| Business rows from row 213 onward | 0 |
| Quarantined primary reference rows in sidecar CSV | 130 |

Rows that previously demonstrated the issue are now empty in business columns:

| Row | B | S | T | Month costs |
| ---: | --- | --- | --- | ---: |
| 213 | blank | blank | blank | 0 |
| 216 | blank | blank | blank | 0 |
| 219 | blank | blank | blank | 0 |

Sidecar quarantine evidence:

- File: `OUTPUT_FY2027/tmp_phase42n3y_final_acceptance/OUTPUT_FY2027/MP_CC_1412000040_REFERENCE_FILL_QUARANTINE.csv`
- Rows: 130.
- First quarantined primary rows include `8`, `16`, `24`, `36`, and `38`.
- Reason: `unscoped reference-assisted fill is not allowed`.

## Overall acceptance

| Claim | Result |
| --- | --- |
| 1. Duplicate new-hire office/stationery costs | PASS_FAIL_CLOSED |
| 2. Total-headcount multiplier | PASS_FAIL_CLOSED |
| 3. New-hire monthly delta | BLOCKED_BY_MISSING_DRIVER_DATA |
| 4. Column S rule | PASS |
| 5. Source-file block spacing | PARTIAL_PASS_FOR_WRITTEN_BLOCKS |
| 6. Row 168+ garbage/reference-fill | PASS |

The code fixes materially address the previously observed output defects. The remaining blocker is input data, not a stale duplicate/reference-fill symptom: target CC `1412000040` still has no canonical monthly headcount series, so real new-hire monthly delta amounts cannot be certified.

## Final checks

| Check | Result |
| --- | --- |
| `git diff --check` | PASS, no output |
| `git diff --cached --name-only` | empty |
| `origin/main...HEAD` after final check | `0 0` |
| Code edits | none |
| Commit/push | none |

New audit artifact created but not committed:

- `docs/audits/phase42n3y_final_user_claims_acceptance_audit.md`

Fresh temp outputs created but not committed:

- `OUTPUT_FY2027/tmp_phase42n3y_final_acceptance/OUTPUT_FY2027/MP_CC_1412000040.xlsx`
- `OUTPUT_FY2027/tmp_phase42n3y_final_acceptance/OUTPUT_FY2027/MP_CC_1412000040_REFERENCE_FILL_QUARANTINE.csv`
- `OUTPUT_FY2027/tmp_phase42n3y_final_acceptance/OUTPUT_FY2027/MP2027_AUDIT_REPORT.md`
- `OUTPUT_FY2027/tmp_phase42n3y_final_acceptance/OUTPUT_FY2027/MP2027_MISSING_INPUTS.csv`

## Recommended next phase

`PHASE_42N3Z_PROVIDE_TARGET_HEADCOUNT_DRIVER_AND_REGENERATE_ACCEPTANCE`

Minimum acceptance input for that phase:

1. Provide complete monthly headcount for target CC `1412000040`.
2. Include the previous period needed by event-delta allocation, such as `202603` before `202604`.
3. Regenerate complete-v1 output and re-audit claims 1, 2, 3, and 5 against actual target new-hire amounts.
