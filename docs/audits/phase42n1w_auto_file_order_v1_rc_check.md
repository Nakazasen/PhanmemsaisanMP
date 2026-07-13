# Phase 42N1W-AUTO - File-Order Export V1 Automated RC Check

## Release conclusion

`ACCEPT_MP2027_FILE_ORDER_V1_AUTOMATED_RC`

No user visual check is required for this automated RC decision.

## Command run

```powershell
py "..\..\scripts\run_e2e.py" --target-cc 1412000040 --file-order-export-v1
```

## Output path

`dist/phase42n1w_auto_file_order_v1_rc/OUTPUT_FY2027/MP_CC_1412000040.xlsx`

## Auto verification

- Workbook opens with `openpyxl`: PASS
- Sheet `内訳ﾘｽﾄ(4～3月)` exists: PASS
- Expected row IDs and blank separators: PASS
- Expected row counts: PASS

## Row verification 200-212

| Row | E item_id | F Apr/sample | Q Mar/sample | S description | T policy | Result |
|---:|---|---:|---:|---|---|---|
| 200 | `building_depreciation` | `293.02` | `289.03` | `Khấu hao nhà` | `ROUND_USD_BY_B2` | PASS |
| 201 | `land_depreciation` | `19.78` | `19.51` | `Khấu hao đất` | `ROUND_USD_BY_B2` | PASS |
| 202 | `building_interest` | `188.35` | `175.38` | `Lãi nhà` | `ROUND_USD_BY_B2` | PASS |
| 203 | `land_interest` | `23.88` | `22.85` | `Lãi đất` | `ROUND_USD_BY_B2` | PASS |
| 204 | `electricity` | `1577160` | `1203521` | `Điện` | `COPY_VND_MONTHLY` | PASS |
| 205 | `water` | `529671` | `637935` | `Nước` | `COPY_VND_MONTHLY` | PASS |
| 206 | `` | `` | `` | `` | `` | PASS |
| 207 | `toilet_paper` | `18895` | `20665` | `トイレットペーパー` | `COPY_SOURCE_MONTH_SAMPLE` | PASS |
| 208 | `hand_soap` | `1365` | `1462` | `手洗い洗剤` | `COPY_SOURCE_MONTH_SAMPLE` | PASS |
| 209 | `alcohol_disinfectant` | `UNKNOWN` | `UNKNOWN` | `アルコール消毒` | `UNKNOWN` | PASS |
| 210 | `` | `` | `` | `` | `` | PASS |
| 211 | `system_cost_combined` | `6111363` | `6111363` | `System Cost / システム課金` | `COPY_SUMMARY_VND_TOTAL_BY_PERIOD` | PASS |
| 212 | `` | `` | `` | `` | `` | PASS |

## Business row count

| Workbook | Business rows |
|---|---:|
| Generated file-order v1 | 141 |
| Primary reference | 277 |
| Gap | 136 |

## Known backlog

The remaining known gap is `136` rows. The backlog still includes:

- Fixed Assets transition
- Detail rows not yet matched with exact placement evidence
- Birthday / NNN rows
- Other unmatched rows needing focused source-to-output reconciliation

## Final decision

`ACCEPT_MP2027_FILE_ORDER_V1_AUTOMATED_RC`
