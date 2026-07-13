# Phase 42N2H - Hybrid v2 Count Reconciliation

## Classification

`PASS_PHASE_42N2H_COUNT_RECONCILIATION_READY`

## Non-tech answer

Không nên nói đơn giản “chỉ thiếu 2 dòng” nếu chưa nói rõ count method.
Câu đúng hơn là:

> Hybrid v2 đã gần khớp số dòng vật lý theo count method mới: generated v2 có
> 282 business rows so với primary 284, delta còn 2.
> Delta này chủ yếu đến từ cách đếm và việc cố ý skip false gaps đã được chứng minh
> là alias đã generated, không phải bằng chứng công ty thiếu dữ liệu.

“v2 gần khớp số dòng” nghĩa là workbook generated đã được bổ sung các dòng
reference-assisted để gần bằng số dòng primary. Nó **không** nghĩa là mọi dòng đã
có source-derived proof.

`REFERENCE_FILLED_FROM_PRIMARY` khác `SOURCE_DERIVED`: reference-assisted là copy
skeleton/value/formula từ primary reference với nhãn minh bạch; source-derived
phải có raw workbook/sheet/row/cell/month proof.

Chỉ được nói “thiếu 2 dòng thật” nếu chứng minh 2 dòng đó không phải layout,
không phải false-gap alias, không phải duplicate/reference skip, và có yêu cầu
nghiệp vụ phải sinh thành dòng riêng.

## Count method comparison

| Method | Primary | Generated v2 | Delta primary - generated |
|---|---:|---:|---:|
| 42N1P-B old method: exclude rows 1,2,3,4,5,9,17,25 | 277 | 275 | 2 |
| 42N2G new method: count any B/S/F:Q business row | 284 | 282 | 2 |

## Why primary was previously 277 but now 284

42N1P-B excluded layout/header rows `1, 2, 3, 4, 5, 9, 17, 25` before counting.
42N2G used a broader helper that counted any row with account/description/month
content in B/S/F:Q and did not exclude those layout rows. The difference is a
count-method mismatch, not a business conclusion.

## Rows counted in primary but not generated v2 by exact row signature

| Primary row | Account/code | Description | F:Q non-empty count | Reconciliation |
|---:|---|---|---:|---|
| 2 | `` |  | 12 | `LAYOUT_EXCLUDED_BY_OLD_METHOD` |
| 3 | `` |  | 12 | `LAYOUT_EXCLUDED_BY_OLD_METHOD` |
| 9 | `ローカル社員定時` |  | 12 | `LAYOUT_EXCLUDED_BY_OLD_METHOD` |
| 17 | `ローカル社員残業` |  | 12 | `LAYOUT_EXCLUDED_BY_OLD_METHOD` |
| 25 | `ローカル社員(人)` |  | 12 | `LAYOUT_EXCLUDED_BY_OLD_METHOD` |
| 42 | `5005016372` | トイレットペーパー | 12 | `NEEDS_MANUAL_RECONCILIATION` |
| 43 | `5005016372` | 手洗い洗剤 | 12 | `NEEDS_MANUAL_RECONCILIATION` |
| 44 | `5005016372` | アルコール消毒 | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 159 | `5005066281` | 電気代 | 12 | `FALSE_GAP_ALIAS_ALREADY_GENERATED_SKIPPED` |
| 160 | `5005066282` | 水道代 | 12 | `FALSE_GAP_ALIAS_ALREADY_GENERATED_SKIPPED` |
| 174 | `5005046281` | PETフィルム3-2160-08 | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 175 | `5005046281` | PETフィルム3-2160-05 | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 176 | `5005046281` | PictorのCIS検査治具修正の基板(TV2YW01100) | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 177 | `5005046281` | 半田ゴテT12-K | 1 | `NEEDS_MANUAL_RECONCILIATION` |
| 178 | `5005046281` | 半田ゴテT12-C1 | 1 | `NEEDS_MANUAL_RECONCILIATION` |
| 179 | `5005046281` | 半田ゴテT12-C4 | 1 | `NEEDS_MANUAL_RECONCILIATION` |
| 180 | `5005046281` | 半田ゴテT12-BC2 | 1 | `NEEDS_MANUAL_RECONCILIATION` |
| 181 | `5005046281` | FT予備品 | 1 | `NEEDS_MANUAL_RECONCILIATION` |
| 182 | `5005046281` | OscilocopeのProbe購入 | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 184 | `5005046282` | Laptop 修正 | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 185 | `5005046282` | ノートPCのメインボード交換修理(HuyさんのPC/3月に修正間に合わないのため4月にズレ) | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 186 | `5005046282` | AnさんのMouse交換 | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 187 | `5005046282` | マウス購入 | 2 | `NEEDS_MANUAL_RECONCILIATION` |
| 188 | `5005046282` | note book PC交換(10月：さん) | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 189 | `5005046282` | Laptop Battery | 4 | `NEEDS_MANUAL_RECONCILIATION` |
| 190 | `5005046282` | PCのSSD交換購入 | 1 | `NEEDS_MANUAL_RECONCILIATION` |
| 192 | `5005046283` | 計測器校正(新規購入テスタ） | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 193 | `5005046283` | 計測器校正(オシロ):1,800,000 (Tektronix) | 3 | `NEEDS_MANUAL_RECONCILIATION` |
| 194 | `5005046283` | 計測器校正(高電圧プローブ):1,500,000 | 2 | `NEEDS_MANUAL_RECONCILIATION` |
| 195 | `5005046283` | 計測器校正(テスタ)FLUKE 53880074MV; 37781226WS; 20280213;15760076 :500,000 | 5 | `NEEDS_MANUAL_RECONCILIATION` |
| 196 | `5005046283` | 計測器校正(電流プローブ):1500000 | 3 | `NEEDS_MANUAL_RECONCILIATION` |
| 197 | `5005046283` | 計測器校正(LCRメータ):500,000 | 1 | `NEEDS_MANUAL_RECONCILIATION` |
| 198 | `5005046283` | 計測器校正(温度計):500,000 | 1 | `NEEDS_MANUAL_RECONCILIATION` |
| 199 | `5005046283` | 計測器校正(静電気測定器 FMX-004):800,000->700,000 | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 200 | `5005046283` | 計測器校正(オシロYokogawa):1,800,000 | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 202 | `5005246292` | polaris fax unit返却差異 | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 204 | `5005076289` | COURIER CHARGES (P)：不具合基板をメーカへ返却して調査する | 12 | `NEEDS_MANUAL_RECONCILIATION` |
| 205 | `5005076283` | IMPORT AIR FEE (P) 輸入諸費用 | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 207 | `5005076281` | DECLARATION FEE (P): Iris2020のPanel main不具合基板は中国から返却貰って調査する | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 208 | `5005076281` | 3月購入　T102SM3EP0の通関費 4月 ⇒ 5月
分離申告($20×4+α) | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 209 | `5005076281` | SHARP選別治具備品輸入費$15 AIR FEEへ変更 | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 210 | `5005076289` | DeltaのHeatsinkに糸金属成分分析発送費 | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 211 | `5005076289` | Sunviewの要因でLCD発送費請求 | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 212 | `5005076289` | Courier import | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 215 | `5005246286` | 清掃費 | 12 | `NEEDS_MANUAL_RECONCILIATION` |
| 216 | `5005246286` | パスポート更新経費 | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 217 | `5005246286` | 労働許可証取得費用 | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 218 | `5005246286` | 滞在カード取得費用 | 0 | `NEEDS_MANUAL_RECONCILIATION` |
| 219 | `5005246286` | 出向者の費用 | 2 | `NEEDS_MANUAL_RECONCILIATION` |
| 220 | `5005246286` | プロファイルセット費用/パスポート更新申請料 | 0 | `NEEDS_MANUAL_RECONCILIATION` |


## Provenance counts

| Provenance bucket | Count |
|---|---:|
| SOURCE_DERIVED / v1 generated rows | 148 |
| REFERENCE_FILLED_FROM_PRIMARY | 134 |
| False gaps skipped | 2 |
| Remaining new-method physical delta | 2 |

## False gaps intentionally skipped

| Primary row | Primary description | Generated match item | Reason |
|---:|---|---|---|
| 159 | 電気代 | electricity | `ALREADY_GENERATED_FALSE_GAP` |
| 160 | 水道代 | water | `ALREADY_GENERATED_FALSE_GAP` |


## Interpretation of remaining 2-row delta

The remaining delta is **not safe to call real missing rows** yet. Current evidence
shows:

- Hybrid v2 wrote 134 reference-assisted rows.
- 2 false-gap rows were intentionally skipped because invariant accounting
  classified them as already generated aliases.
- The old and new count methods disagree on primary count (277 vs 284).

Therefore, the correct non-tech wording is:

> v2 closes the practical row-count gap to near parity under the new count method,
> with 134 transparent reference-assisted rows and 2 known false
> gaps skipped. The remaining numeric delta should be treated as count-method /
> false-gap reconciliation until each row is proven separately.

## Source files used

- `dist/phase42n2g_hybrid_v2/OUTPUT_FY2027/MP_CC_1412000040.xlsx`
- `reference_outputs/primary/16.KDTVN 電気製造技術課_MP FY2027_各予定(Ver01).xlsx`
- `docs/audits/phase42n2g_hybrid_v2_reference_fill_result.md`
- `docs/audits/phase42n1p_b_output_row_count_vs_primary.md`
- `docs/audits/phase42n2b_invariant_gap_accounting.csv`
