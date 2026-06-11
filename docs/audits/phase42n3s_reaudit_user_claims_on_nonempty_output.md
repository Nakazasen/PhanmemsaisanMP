# Phase 42N3S - Re-audit user claims on non-empty output

CLASSIFICATION: FAIL_PHASE_42N3S_REAUDIT_USER_CLAIMS_ON_NONEMPTY_OUTPUT

## Scope

- Phase: `PHASE_42N3S_REAUDIT_USER_CLAIMS_ON_NONEMPTY_OUTPUT`
- Mode: read-only audit; no code fix, no commit, no push.
- Requirement source used for generation: `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026.xlsx`
- Requirement source explicitly not used: `raw/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026_ảnh.xlsx`
- Runtime stale workbook `OUTPUT_FY2027/MP_CC_1412000040.xlsx` was not used as primary evidence.

## Precheck

| Item | Result |
| --- | --- |
| Branch | `main` |
| Local HEAD | `eed4560e356487e1b6b43dfb7b3e41cdbf310bc5` |
| Fetch | `git fetch origin main` completed |
| `origin/main...HEAD` | `0 0` |
| Commit/push | No commit, no push |

Known dirty/runtime/reference leftovers were preserved and not staged:

- `OUTPUT_FY2027/MP2027_AUDIT_REPORT.md`
- `OUTPUT_FY2027/MP2027_MISSING_INPUTS.csv`
- `mp2027.db`
- `raw/FORM.xlsx`
- `docs/audits/phase42n3k_fixed_asset_cc_full_data_audit.md`
- `raw/requirements/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026.xlsx`
- `reference_outputs/secondary/FY2027/`
- `dist/`
- `build/`

## Generated audit outputs

Command path used:

```powershell
py -3 D:\Sandbox\MP2027\scripts\run_e2e.py --source D:\Sandbox\MP2027\raw --target-cc <CC> --mp-saisan-complete-v1
```

The command was run from `OUTPUT_FY2027/tmp_phase42n3s_reaudit` so generated workbooks were written under the temp audit folder instead of overwriting the stale runtime output.

| CC | Output | Generation result | Size | Sheet | max_row | max_col | Business rows |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: |
| `1412000040` | `OUTPUT_FY2027/tmp_phase42n3s_reaudit/OUTPUT_FY2027/MP_CC_1412000040.xlsx` | Full complete-v1 generation succeeded | 163,007 | `内訳ﾘｽﾄ(4～3月)` | 1015 | 55 | 128 rows in rows 30-260 by formula/value/provenance scan |
| `1412000006` | `OUTPUT_FY2027/tmp_phase42n3s_reaudit/OUTPUT_FY2027/MP_CC_1412000006.xlsx` | Base export and source-order rows were written; final reference-fill failed because `docs/config/reference_workbook_map.csv` only maps `1412000040` | 156,155 | `内訳ﾘｽﾄ(4～3月)` | 1015 | 55 | 84 rows in rows 30-260 by formula/value/provenance scan |

Audit method:

- Workbook values were read with `openpyxl`.
- Formula view (`data_only=False`) was used for cost detection because generated workbooks were not recalculated by Excel, so formula cached values are blank in `data_only=True`.
- Month/cost columns audited: `F:Q`.
- Column `S` audited as the user-facing explanation/remarks column.
- Column `T` audited as provenance.

## Claim 1 - Duplicate new-hire office/stationery costs

Result: FAIL, with target-CC driver caveat.

Target CC `1412000040` has the relevant new-hire rows, but no generated month costs on them:

| Row | Description in S | Month costs in F:Q |
| ---: | --- | --- |
| 90 | `新入社員：名札+写真/Người mới: Thẻ + ảnh` | none |
| 91 | `新入社員：ﾌｨﾛｿﾌｨ1,2/Người mới: triết lý 1,2` | none |
| 95 | `新入社員：名札ケース/Người mới: Vỏ thẻ+kẹp` | none |
| 96 | `新入社員：ペン/Người mới: Bút bi` | none |
| 188 | `新入社員：ノート（スタッフ用）/Người mới: Sổ tay (Dùng cho nhân viên)` | none |
| 189 | `新入社員：ノート (G7社員用）/Người mới: Sổ tay (Dùng cho công nhân)` | none |

Canonical DB evidence for target CC `1412000040`:

- `fact_monthly_headcount`: 0 rows for `1412000040`.
- `dim_cost_centers`: `staff_count=0`, `worker_count=0` for `1412000040`.
- `fact_input_data`: 0 rows for account `5005246281` and 0 rows for account `5005246288` for `1412000040`.
- Temp `MP2027_MISSING_INPUTS.csv` reports missing manual headcount for `1412000040`.

Supplemental CC `1412000006` does show duplicate/misaligned new-hire office cost output:

| Row | Description in S | Jan formula | Provenance |
| ---: | --- | --- | --- |
| 90 | `新入社員：名札+写真/Người mới: Thẻ + ảnh` | `=28*9100` | base export row |
| 188 | `新入社員：ノート（スタッフ用）/Người mới: Sổ tay (Dùng cho nhân viên)` | `=28*9100` | `source-order-complete-v1` from allocation row 97 |
| 189 | `新入社員：ノート (G7社員用）/Người mới: Sổ tay (Dùng cho công nhân)` | `=28*9100` | `source-order-complete-v1` from allocation row 98 |

DB cross-check for `1412000006`:

- There is one `fact_input_data` row for `alloc_5110` / `ノート Sổ` / account `5005246288` at `202701` for `254800 = 28 * 9100`.
- The same `=28*9100` is emitted in multiple workbook rows with different descriptions, including a name-tag row and both staff/worker notebook rows.
- This is not a valid one-identity-one-output mapping.

Suspected cause: export row placement/source-order copy is not deduping by allocation source identity and is not binding the generated amount to the correct business item row.

## Claim 2 - New-hire office costs still use total headcount

Result: FAIL for generated evidence; BLOCKED for direct target-CC formula proof.

The allocator code path intends event-month rules such as `入社月` to use positive month-to-month delta, not total headcount. The current data/output still shows total-headcount-style multiplication when a CC has only partial monthly headcount data.

Evidence from supplemental CC `1412000006`:

| Evidence | Value |
| --- | --- |
| `fact_monthly_headcount` rows | `202701=28`, `202702=28`, `202703=28`; no April-December 2026 rows |
| Row 88 Jan formula | `=28*3600` |
| Row 90 Jan formula | `=28*9100` |
| Row 188 Jan formula | `=28*9100` |
| Row 189 Jan formula | `=28*9100` |

If the output headcount row is used as the driver, row 25 has `Dec=27`, `Jan=28`, so the positive delta for January is `1`, not `28`. If the DB driver is used, the missing December row makes the allocator fall back to zero and turns the first available January headcount into a `+28` delta.

For target CC `1412000040`, direct proof is blocked because the canonical monthly headcount driver is missing entirely:

- `fact_monthly_headcount` rows for `1412000040`: 0.
- Master fallback counts for `1412000040`: `staff_count=0`, `worker_count=0`.
- New-hire office rows in the generated workbook have no amount cells.

Suspected cause: incomplete headcount series is not fail-closed for event-delta allocation. Missing previous months are treated like zero, so the first populated month can be interpreted as all-new headcount.

## Claim 3 - The output still cannot get the new-hire count for the month with new hires

Result: BLOCKED_MISSING_DRIVER_DATA for target CC; failure symptom present in supplemental CC.

Target CC `1412000040` cannot be passed because canonical driver data is missing:

| Source | Evidence |
| --- | --- |
| DB `fact_monthly_headcount` | no rows for `1412000040` |
| DB `dim_cost_centers` | `staff_count=0`, `worker_count=0` |
| Temp missing-input report | `Chưa có manual headcount cho CC này` |
| Generated target rows 90/91/95/96/188/189 | descriptions exist, but F:Q amount cells are blank |

The generated target workbook row 25 contains local headcount values with visible increases (`Apr=22`, `May=22`, `Jun=26`, `Jul=27`, `Jan=28`), but those values are not backed by canonical `fact_monthly_headcount` rows for `1412000040`, and the new-hire office rows do not post matching month costs.

Supplemental CC `1412000006` shows the other side of the same issue: only Jan-Mar headcount rows exist, so new-hire allocations appear only in January and use `28` as the driver. That does not prove correct month-specific new-hire delta handling.

Conclusion: not PASS. The target output is blocked by missing driver data, and the allocator/export path needs a fail-closed full-series driver check before claiming the new-hire month logic is correct.

## Claim 4 - Column S rule

Result: FAIL.

Rule audited: from row 30 onward, rows with any month cost in `F:Q` must have an explanation in `S`; rows without any month cost in `F:Q` must not have an explanation in `S`.

Target CC `1412000040` results:

| Metric | Count |
| --- | ---: |
| Rows with cost but blank S | 3 |
| Rows without cost but nonblank S | 147 |

Examples: cost exists but S is blank.

| Row | B | Example month costs | T/provenance |
| ---: | --- | --- | --- |
| 213 | `出向社員定時` | Apr `153`, May `110.5`, Jun `170` | `REFERENCE_FILLED_FROM_PRIMARY; primary_row=8; not source-derived` |
| 216 | `出向社員残業` | Apr `36`, May `26`, Jun `40` | `REFERENCE_FILLED_FROM_PRIMARY; primary_row=16; not source-derived` |
| 219 | `出向社員(人)` | Apr `1`, May `1`, Jun `1` | `REFERENCE_FILLED_FROM_PRIMARY; primary_row=24; not source-derived` |

Examples: no month cost in F:Q but S is nonblank.

| Row | B | S |
| ---: | --- | --- |
| 31 | blank | `この分には間接部門から直接部門に配賦された数字` |
| 53 | blank | `出向者BUS送迎費/Chi phí xe bus người JP` |
| 56 | blank | `制服(新人）/Đồng phục (người mới)` |
| 57 | blank | `定年の健康診断費/Chi phí khám sức khỏe hàng năm` |
| 87 | blank | `11月に配賦のPocket Calendar/Lịch bỏ túi phân bổ tháng 11` |

Supplemental CC `1412000006` also fails the same rule:

- Rows with cost but blank S: 4.
- Rows without cost but nonblank S: 54.
- Examples with cost but blank S: rows 79, 80, 81, 89.

Suspected cause: column S is still treated as static template/reference text in several writers. No final post-writer validation clears S for no-cost rows or requires S for cost rows.

## Claim 5 - Seven source-file block spacing

Result: PASS.

Target CC `1412000040` source-order block evidence:

| Block | Source | Start | End | Rows | Blank gap before |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `施設課　MPFY2027.xlsx` | 168 | 173 | 6 | n/a |
| 2 | `固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx` | 175 | 176 | 2 | 1 |
| 3 | `システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls` | 178 | 178 | 1 | 1 |
| 4 | `総務課 FY2027 MP 振替予定.xlsx` | 180 | 182 | 3 | 1 |
| 5 | `Sinh nhật MP FY2027.xlsx` | 184 | 184 | 1 | 1 |
| 6 | `FY2027配賦額一覧 (2025.12.29).xlsx` | 186 | 189 | 4 | 1 |
| 7 | `Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx` | 191 | 191 | 1 | 1 |

All inter-block gaps are exactly one blank row. Supplemental CC `1412000006` has the same block ranges and one-row gaps through the source-order stage.

## Claim 6 - Garbage from row 168 onward, any CC

Result: PARTIAL.

The literal row 168 claim is not correct for the generated output:

- Row 168 is a valid source-order row.
- Target row 168: account `5006016260`, S `減価償却費（建物）/Khấu hao (Nhà)`, T `source_file=施設課　MPFY2027.xlsx; original_row=36; source-order-complete-v1`.
- Supplemental CC `1412000006` also has row 168 as a valid source-order facility row.

However, there is a real row-168-plus risk after the seven source-order blocks:

| First suspicious row | Evidence |
| ---: | --- |
| 213 | `REFERENCE_FILLED_FROM_PRIMARY; primary_row=8; not source-derived`; has month costs but blank S |

Target CC `1412000040` has 848 non-empty rows from row 168 onward because complete-v1 adds source-order rows and then reference-assisted primary rows. Many row 213+ rows are marked `REFERENCE_FILLED_FROM_PRIMARY; ... not source-derived`, and the column S rule already fails in that region.

The "every CC" part cannot be fully proven for reference-fill rows because the only configured primary reference map is for `1412000040`. A second CC (`1412000006`) can be generated through source-order rows 168-191, but full complete-v1 reference fill stops with:

```text
MP Saisan complete v1 requires a primary reference path/map for reference-assisted fill.
```

Conclusion: row 168 itself is intentional, not garbage. The first suspicious row is row 213 in the mapped target output, where reference-filled/non-source-derived data starts.

## Root Cause Suspected

1. New-hire allocation depends on `fact_monthly_headcount`, but target CC `1412000040` has no canonical monthly driver rows and zero master fallback counts.
2. Event-delta allocation can misinterpret the first populated month as all-new headcount when prior months are missing and fallback to zero.
3. Export/source-order row placement is not binding allocation source identity to exactly one correct business row, causing repeated/misaligned formulas such as `=28*9100`.
4. Column S is not normalized after all writers/reference fill layers.
5. Reference-assisted fill begins at row 213 and introduces many `not source-derived` rows into the user-facing workbook.

## Recommended Fix Phases

1. Headcount driver fail-closed phase: require a complete FY monthly headcount series, including prior period for event-delta rules, before generating new-hire allocations. Missing target driver data should block export with a clear missing-input error.
2. New-hire allocation identity/dedupe phase: map each allocation source row to the correct output item, account, month, and unit-price identity; prevent one source amount from appearing under multiple descriptions.
3. Column S enforcement phase: after all writers and reference-fill layers, clear S on no-cost rows and require S on cost-bearing rows.
4. Reference-fill scope phase: separate valid source-order rows 168-191 from reference-assisted rows 213+, and suppress or quarantine `REFERENCE_FILLED_FROM_PRIMARY` rows that are not source-derived or have no cost.
5. Multi-CC complete-v1 phase: either provide reference maps for non-target CCs or fail before writing partial workbooks when complete-v1 cannot finish for that CC.
