# Phase 42N3Q - Post-Fix User Claims Full Audit

CLASSIFICATION:
- FAIL_PHASE_42N3Q_POST_FIX_USER_CLAIMS_FULL_AUDIT

REPORT:
- Branch: `main`
- Local HEAD: `cfa4646f64885949e25dd35421c64d5d8b59f455`
- origin/main ahead/behind: `origin/main...HEAD = 1 0` (`HEAD` is behind origin/main by 1, ahead by 0)
- Requirement source used: `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026.xlsx`
- Requirement source not used: `raw/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026_ảnh.xlsx`
- Commit/push: NO

## Output Files Audited

Primary current output:

- `OUTPUT_FY2027/MP_CC_1412000040.xlsx`
- Last write: `2026-06-10 05:58:35`
- Size: `4,826`
- Sheet: `内訳ﾘｽﾄ(4～3月)`
- Observed workbook shape: `max_row=1`, `max_col=1`, row 1 value `None`
- Result: unusable as MP output. This alone prevents a passing full audit on the current user-facing run.

Supporting generated evidence, not treated as current user output:

- `dist/phase42n3f_source_order_audit/OUTPUT_FY2027/MP_CC_1412000040.xlsx`
- Size: `163,028`
- Used only to inspect the last known generated complete-v1 source-order behavior.

Historical/reference workbook samples from the requested search scope:

- `reference_outputs/secondary/FY2027/01.KDTVN 機器製造1課　_MP FY2027_各予定(Ver01).xlsx`
- `reference_outputs/secondary/FY2027/14.KDTVN メカ製造技術1課_MP FY2027_各予定(Ver01).xlsx`
- `reference_outputs/secondary/FY2027/16.KDTVN 電気製造技術課_MP FY2027_各予定(Ver01).xlsx`

CCs audited:

- Current output: expected `1412000040`
- Supporting generated output: `1412000040`
- Reference samples: file prefixes `01`, `14`, `16`

## Precheck

Dirty files already existed and were preserved:

- `OUTPUT_FY2027/MP2027_AUDIT_REPORT.md`
- `OUTPUT_FY2027/MP2027_MISSING_INPUTS.csv`
- `mp2027.db`
- `raw/FORM.xlsx`
- many untracked `reference_outputs/secondary/FY2027/...` files

The current audit did not commit, push, or run full pytest.

## Claim 1 Duplicate New-Hire Stationery

PASS/FAIL: FAIL for current output validity; duplicate cost not provable from current output.

Evidence:

- Current output `OUTPUT_FY2027/MP_CC_1412000040.xlsx` has no business rows.
- Supporting generated output has new-hire rows but no F:Q amounts:
  - row 188: `新入社員：ノート（スタッフ用）/Người mới: Sổ tay (Dùng cho nhân viên)`, source `FY2027配賦額一覧 (2025.12.29).xlsx`, original row 97, all F:Q blank.
  - row 189: `新入社員：ノート (G7社員用）/Người mới: Sổ tay (Dùng cho công nhân)`, source `FY2027配賦額一覧 (2025.12.29).xlsx`, original row 98, all F:Q blank.
- `mp2027.db` has no `fact_input_data` rows for CC `1412000040` matching notebook/new-hire/health terms.

Suspected root cause:

- The latest output generation failed or produced an empty workbook.
- For the last known generated workbook, target CC `1412000040` has no new-hire driver facts, so duplicate stationery costs cannot be validated against real amounts.

## Claim 2 Multiplied By Total Headcount

PASS/FAIL: FAIL for current output validity; total-headcount multiplication not observed in output.

Expected formula:

- `new_employee_count[M] = max(employee_count[M] - employee_count[M-1], 0)`
- `new_worker_count[M] = max(worker_count[M] - worker_count[M-1], 0)`
- expected amount = staff delta * staff unit price + worker delta * worker unit price

Evidence:

- `fact_monthly_headcount` has no rows for CC `1412000040`.
- `dim_cost_centers` has CC `1412000040` with `staff_count=0`, `worker_count=0`.
- Supporting output rows 188 and 189 have no monthly amounts.
- Static code evidence: `src/engine/allocator.py` uses `_get_event_delta(...)` for posting-month rules such as `入社月`, so the intended code path is delta-based, not total-headcount-based.
- Test evidence in `tests/test_headcount_and_export.py` checks that notebook allocation uses deltas and explicitly does not use total headcount.

Actual formula/output:

- Current output: no rows.
- Supporting output: row 188/189 all F:Q blank.

Suspected root cause:

- Missing target-CC headcount/manual-event data, plus the current output file is empty.
- No evidence from this output proves the specific total-headcount bug is still active.

## Claim 3 Missing New-Hire Monthly Delta

PASS/FAIL: FAIL for current output validity and missing actual new-hire amounts.

Months with new hires:

- Not determinable from current data for CC `1412000040` because there is no monthly headcount series for that CC.

Expected output:

- New-hire stationery should post in month M when the headcount delta is positive.
- Recruitment health check should post in month M+1 when the previous month has a positive new-hire delta.

Actual output:

- Current output: empty.
- Supporting output:
  - row 187 recruitment health: all F:Q blank.
  - row 188 staff notebook: all F:Q blank.
  - row 189 worker notebook: all F:Q blank.
- `OUTPUT_FY2027/MP2027_MISSING_INPUTS.csv` explicitly flags missing/review-needed headcount for CC `1412000040`.

Suspected root cause:

- The generated run lacks target-CC headcount/manual event facts, so the delta engine has no driver values.
- The latest workbook generation also failed to preserve a usable output file.

## Claim 4 Column S Description Rule

PASS/FAIL: FAIL.

Rows with cost but blank S in supporting generated output:

- Count in rows 30-260: `4`
- Examples:
  - row 66: monthly formula in G, blank S.
  - row 213: monthly values in F:H and later columns, blank S, T=`REFERENCE_FILLED_FROM_PRIMARY; primary_row=8; not source-derived`.
  - row 216: monthly values in F:H and later columns, blank S.
  - row 219: monthly values in F:H and later columns, blank S.

Rows without cost but nonblank S in supporting generated output:

- Count in rows 30-260: `86`
- Examples:
  - row 53: `出向者BUS送迎費/Chi phí xe bus người JP`, no F:Q amount.
  - row 54: `ローカル社BUS送迎費/Chi phí xe bus người VN`, no F:Q amount.
  - row 57: `定年の健康診断費/Chi phí khám sức khỏe hàng năm`, no F:Q amount.
  - row 90: `新入社員：名札+写真/Người mới: Thẻ + ảnh`, no F:Q amount.
  - row 96: `新入社員：ペン/Người mới: Bút bi`, no F:Q amount.
  - row 186: `定年の健康診断費/Chi phí khám sức khỏe hàng năm`, no F:Q amount.
  - row 187: `採用の健康診断費/Chi phí khám sức khỏe tuyển dụng`, no F:Q amount.
  - row 188/189: new-hire notebook rows, no F:Q amount.

Suspected root cause:

- The source-order migration clears selected business columns in target ranges and legacy rows, but it does not globally enforce `S blank iff no cost`.
- Template/reference descriptions remain in S on no-cost rows.
- Reference-assisted fill can add rows with values and T provenance while S remains blank.

## Claim 5 Seven-File Block Spacing

PASS/FAIL: PASS in supporting generated output; FAIL/blocked for current output because it is empty.

Block gap evidence from supporting output:

| Block | Rows | Next block start | Blank gap |
|---|---:|---:|---:|
| `施設課　MPFY2027.xlsx` | 168-173 | 175 | 1 |
| `固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx` | 175-176 | 178 | 1 |
| `システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls` | 178 | 180 | 1 |
| `総務課 FY2027 MP 振替予定.xlsx` | 180-182 | 184 | 1 |
| `Sinh nhật MP FY2027.xlsx` | 184 | 186 | 1 |
| `FY2027配賦額一覧 (2025.12.29).xlsx` | 186-189 | 191 | 1 |

Suspected root cause:

- No source-order spacing defect found in `src/engine/complete_v1_source_order_writer.py` or the supporting generated workbook.
- The current user-facing output cannot confirm this because it is empty.

## Claim 6 Garbage From Row 168

PASS/FAIL: FAIL for current output validity; PARTIAL for cross-CC evidence.

First garbage row:

- Current output: no row 168 exists in usable form.
- Supporting generated output: row 168 is not garbage; it is the intentional first source-order row:
  - account `5006016260`
  - S `減価償却費（建物）/Khấu hao (Nhà)`
  - T `source_file=施設課　MPFY2027.xlsx; original_row=36; source-order-complete-v1`

Evidence across CCs:

- Supporting generated output only covers CC `1412000040`, so it cannot prove the "every CC" claim.
- Reference samples are department-specific, not identical repeated garbage:
  - `01...xlsx` row 168 has account `5005046282`, monthly `50,000,000` repeated, S `生産技術 KTSX3`.
  - `16...xlsx` row 168 has account `5005046281`, no F:Q amount, S `Tonerセンサー半田ゴテ先`.
  - `14...xlsx` has no nonempty rows in 168-220 in the sampled columns.

Suspected root cause:

- If users see unwanted row-168+ data in generated files, the likely issue is not the source-order rows 168-191 themselves; those are intentionally written source blocks.
- The real risk is post-source-order residual/reference fill behavior, especially `REFERENCE_FILLED_FROM_PRIMARY` rows beginning at row 213 in the supporting output.
- The current empty workbook blocks a definitive multi-CC generated-output audit.

## Code Evidence

Relevant code paths inspected:

- `src/engine/complete_v1_source_order_writer.py`
  - collects staged rows from legacy rows, clears target range and legacy fixed rows, then writes source blocks starting at row 168.
  - inserts one blank row between nonempty source blocks.
- `src/engine/source_order_output.py`
  - pure placement helper also inserts exactly one blank separator between source-file groups.
- `src/engine/allocator.py`
  - event-month logic uses `_get_event_delta` for `入社月`.
  - next-event-month logic uses previous-period delta for M+1 posting.
- `src/parsers/ga.py`
  - maps GA/admin rows 58, 97, 98 and default unit prices.
- `tests/test_headcount_and_export.py`
  - targeted tests cover new-hire notebook delta behavior and GA admin allocation export.

## Files Modified

- `docs/audits/phase42n3q_post_fix_user_claims_full_audit.md`

No code files were modified.

## Recommended Fix Phases, Prioritized

1. Reproduce and fix the empty current output file.
   - The latest `OUTPUT_FY2027/MP_CC_1412000040.xlsx` is only 4,826 bytes and contains no business data.
   - Until this is fixed, user-facing acceptance cannot pass.

2. Add target-CC driver data or a fail-closed validation for new-hire claims.
   - Require manual monthly headcount or explicit event-driver data for CC `1412000040`.
   - If absent, report a blocking missing-input error before writing empty new-hire business rows.

3. Enforce column S consistency after all writers and reference fill.
   - Clear S when F:Q has no cost.
   - Require S when any F:Q monthly amount/formula exists.
   - Apply this after source-order migration and reference-assisted fill.

4. Audit generated multi-CC outputs after the current-output fix.
   - Need at least two real generated CC outputs to prove or disprove the "row 168 garbage in every CC" claim.
