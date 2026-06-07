# Phase 42N1T-B - Facility + Admin Export Flag Row Count

## Scope

Ran a real single-CC export with both explicit flags enabled:

- `--facility-file-order-export`
- `--admin-consumables-export`

No business/export code was changed. No full pytest was run. No commit was made.

## Precheck

- Branch: `main`
- HEAD: `67a3053 feat(workflow): add admin consumables export flag`
- `origin/main...HEAD`: `0 0`
- Working tree was clean before export.

## Output path

Generated output:

`dist/phase42n1t_b_facility_admin_export_flags/flag_on/OUTPUT_FY2027/MP_CC_1412000040.xlsx`

## Count method

Sheet: `内訳ﾘｽﾄ(4～3月)`

A row is counted as a business row if any of the following is present:

- Account/code in column `B`
- Description in column `S`
- Value/formula in columns `F:Q`

Layout rows excluded:

- `1, 2, 3, 4, 5, 9, 17, 25`

## Business row counts

| Workbook | Business rows |
|---|---:|
| Facility-only flag ON | 137 |
| Facility + Admin flags ON | 140 |
| Primary reference | 277 |

## Delta

| Metric | Count |
|---|---:|
| Admin flag delta vs Facility-only | +3 |
| Remaining gap vs Primary | 137 |

## Rows 200-210 verification

| Row | B | E item_id | F Apr/sample | Q Mar/sample | S description | T note/policy | Result |
|---:|---|---|---:|---:|---|---|---|
| 200 | `5004086291` | `building_depreciation` | `293.02` | `289.03` | `Khấu hao nhà` | `ROUND_USD_BY_B2` | Facility row OK |
| 201 | `5005136291` | `land_depreciation` | `19.78` | `19.51` | `Khấu hao đất` | `ROUND_USD_BY_B2` | Facility row OK |
| 202 |  | `building_interest` | `188.35` | `175.38` | `Lãi nhà` | `ROUND_USD_BY_B2` | Facility row OK |
| 203 |  | `land_interest` | `23.88` | `22.85` | `Lãi đất` | `ROUND_USD_BY_B2` | Facility row OK |
| 204 |  | `electricity` | `1577160` | `1203521` | `Điện` | `COPY_VND_MONTHLY` | Facility row OK |
| 205 |  | `water` | `529671` | `637935` | `Nước` | `COPY_VND_MONTHLY` | Facility row OK |
| 206 |  |  |  |  |  |  | Blank separator OK |
| 207 |  | `toilet_paper` | `18895` | `20665` | `トイレットペーパー` | `COPY_SOURCE_MONTH_SAMPLE` | Admin row OK |
| 208 |  | `hand_soap` | `1365` | `1462` | `手洗い洗剤` | `COPY_SOURCE_MONTH_SAMPLE` | Admin row OK |
| 209 |  | `alcohol_disinfectant` | `UNKNOWN` | `UNKNOWN` | `アルコール消毒` | `UNKNOWN` | Admin row OK, source monthly sample not inferred |
| 210 |  |  |  |  |  |  | Blank separator OK |

## Interpretation

The Admin consumables flag adds exactly three business rows after the Facility
file-order block. The row count moves from `137` to `140`.

The remaining gap to primary is `137` rows. This is expected after a small,
explicit-only Admin consumables batch and does not imply the remaining groups are
implemented yet.

## Conclusion

`PASS_PHASE_42N1T_B_FACILITY_ADMIN_ROW_COUNT_READY`

Both explicit flags produced the expected incremental row-count change:
Facility rows `200-205`, blank row `206`, Admin rows `207-209`, and blank row
`210`.
