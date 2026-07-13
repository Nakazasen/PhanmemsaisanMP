# Phase 42N1R-A - Unknown Detail Source Trace

## Scope

Trace representative `Unknown/needs manual mapping` primary rows from Phase 42N1Q-A
back to candidate source workbooks. This is source-trace only: no code changes,
no export changes, and no formula correctness conclusions.

## Inputs

- Primary: `reference_outputs/primary/16.KDTVN 電気製造技術課_MP FY2027_各予定(Ver01).xlsx`
- Generated flag ON: `dist/phase42n1p_b_facility_export_flag/flag_on/OUTPUT_FY2027/MP_CC_1412000040.xlsx`
- Gap report: `docs/audits/phase42n1q_a_missing_row_gap_breakdown.md`

## Source workbook path found

Primary Admin/Tổng vụ candidate exists in both raw and docs mirrors:

- `raw/総務課 FY2027 MP 振替予定.xlsx`
- `docs/MP2027/総務課 FY2027 MP 振替予定.xlsx`

Related allocation master candidates also contain some matched items:

- `raw/FY2027配賦額一覧 (2025.12.29).xlsx`
- `docs/MP2027/FY2027配賦額一覧 (2025.12.29).xlsx`

## Sheets inspected

`raw/総務課 FY2027 MP 振替予定.xlsx`:

| Sheet | Dimensions | Relevant hits |
|---|---:|---:|
| `FY2027予定` | 20 x 19 | 2 |
| `Cách tính phân bổ 振替計算` | 48 x 21 | 3 |
| `cách tính Gas` | 25 x 13 | 0 |
| `Số ngày xe bus ` | 42 x 13 | 0 |
| `Tính NRT, GVS (2)` | 48 x 15 | 0 |
| `Tính gas` | 13 x 13 | 0 |
| `Tính NRT, GVS` | 50 x 15 | 0 |
| `Tính bus VN` | 83 x 16 | 0 |
| `Dự kiến tuyển dụng` | 5 x 14 | 0 |
| `Số ngày xe bus` | 33 x 13 | 0 |

`raw/FY2027配賦額一覧 (2025.12.29).xlsx`:

| Sheet | Relevant hits |
|---|---:|
| `配賦額一覧` | 2 |
| `FY2027配賦額一覧` | 2 |

## Mapping summary

| Primary row | Primary account | Primary description | Suspected source workbook | Source sheet | Source row | Source account / cost center | Source description | Source month values sample | Confidence | Proposed group |
|---:|---|---|---|---|---:|---|---|---|---|---|
| 42 | `5005016372` | `トイレットペーパー` | `raw/総務課 FY2027 MP 振替予定.xlsx` | `FY2027予定` | 7 | `5005016372 / 6005016422 / 6005016413` | `トイレットペーパー / Giấy vệ sinh` | Apr `18895`, May `18117`, Mar `20665` | HIGH | Admin detail expense / Consumables |
| 43 | `5005016372` | `手洗い洗剤` | `raw/総務課 FY2027 MP 振替予定.xlsx` | `FY2027予定` | 6 | `5005016372 / 6005016422 / 6005016413` | `手洗い洗剤 / Nước rửa tay` | Apr `1365`, May `1284`, Mar `1462` | HIGH | Admin detail expense / Consumables |
| 44 | `5005016372` | `アルコール消毒` | `raw/総務課 FY2027 MP 振替予定.xlsx` | `Cách tính phân bổ 振替計算` | 15 | not visible in hit row | `アルコール消毒 / Cồn khử trùng` | total row present, month values blank in visible sample | MEDIUM | Admin detail expense / Consumables |
| 45 | `5005016372` | `Marking pen` | not found in Admin workbook search | n/a | n/a | n/a | n/a | n/a | LOW | Unknown / likely detail consumable |
| 46 | `5005016372` | `Sprayway 955 Anti Static` | not found in Admin workbook search | n/a | n/a | n/a | n/a | n/a | LOW | Unknown / likely detail consumable |
| 49 | `5005016371` | `TH conect, conecR半田ブリッジ対応実験` | not found in Admin workbook search | n/a | n/a | n/a | n/a | n/a | LOW | Parts / engineering detail |
| 50 | `5005016371` | `Battery 9V(13,000)` | not found in Admin workbook search | n/a | n/a | n/a | n/a | n/a | LOW | Parts / consumables |
| 51 | `5005016371` | `Pin Energizer AA(26,500/pcs)` | not found in Admin workbook search | n/a | n/a | n/a | n/a | n/a | LOW | Parts / consumables |
| 52 | `5005016371` | `Main pictor TV2YV01010 DL治具開発用 + Main pictor TV2YW01010 DL治具開発用` | not found in Admin workbook search | n/a | n/a | n/a | n/a | n/a | LOW | Parts / engineering detail |
| 54 | `5005016371` | `冷却スプレー Nabakem SF-1013` | not found in Admin workbook search | n/a | n/a | n/a | n/a | n/a | LOW | Parts / consumables |
| 55 | `5005016373` | `Panel LCD 3V2Y301040` | not found in Admin workbook search | n/a | n/a | n/a | n/a | n/a | LOW | Parts |
| 57 | `5005026371` | `Vendor用Micro SD(8B) 単価:VND` | not found in Admin workbook search | n/a | n/a | n/a | n/a | n/a | LOW | Parts / media |
| 58 | `5005026371` | `湿度計 単価:$28, LCRmeter Probe(SMDA-22)` | not found in Admin workbook search | n/a | n/a | n/a | n/a | n/a | LOW | Parts / measurement tools |
| 59 | `5005026371` | `ノートPCのRAM 16gb` | not found in Admin workbook search | n/a | n/a | n/a | n/a | n/a | LOW | Parts / IT hardware |
| 61 | `5005026371` | `USB 10本(単価$7.5)` | not found in Admin workbook search | n/a | n/a | n/a | n/a | n/a | LOW | Parts / media |
| 130-like template | `5005076289` | `COURIER CHARGES (P)` | `raw/FORM.xlsx` / `docs/MP2027/FORM.xlsx` | `内訳ﾘｽﾄ(4～3月)` | 130 | `5005076289` | `COURIER CHARGES (P)` | template row, no source months | MEDIUM | Courier / template-fixed candidate |

## Trace totals

| Result | Count |
|---|---:|
| Sample rows checked | 16 |
| Traced to Admin workbook | 3 |
| Traced to allocation master | 2 related allocation rows |
| Traced to template row | 1 |
| Not found in searched Admin/workbook set | 12 |

The two allocation master rows are the same consumable items also found in the
Admin workbook:

- `トイレットペーパー / Giấy vệ sinh`
- `手洗い洗剤 / Nước rửa tay`

## Top source sheets

1. `raw/総務課 FY2027 MP 振替予定.xlsx` / `FY2027予定`
   - Contains the clearest consumable rows with monthly values and accounts.
2. `raw/総務課 FY2027 MP 振替予定.xlsx` / `Cách tính phân bổ 振替計算`
   - Contains calculation/support rows for handwashing, alcohol, toilet paper.
3. `raw/FY2027配賦額一覧 (2025.12.29).xlsx` / `配賦額一覧`
   - Contains allocation-rule metadata for toilet paper and handwashing.
4. `raw/FORM.xlsx` / `内訳ﾘｽﾄ(4～3月)`
   - Contains template row for `COURIER CHARGES (P)`.

## Findings

- The first consumable rows in primary are traceable to Admin/Tổng vụ sources.
- Many engineering-detail rows (`Marking pen`, `Battery`, `Main pictor`, `Panel LCD`,
  `Micro SD`, `RAM`, `USB`) were not found in the Admin workbook or allocation
  master candidates searched here.
- This suggests the `Unknown/detail` gap is not one single source group. It likely
  combines:
  - Admin/Tổng vụ common consumables,
  - allocation-master driven common expenses,
  - template fixed rows,
  - engineering/detail expense rows from another source or embedded primary-only
    workbook content.

## Recommended fast implementation batch

### 1. Admin detail expense file-order group

Start with rows proven in `raw/総務課 FY2027 MP 振替予定.xlsx`:

- `トイレットペーパー`
- `手洗い洗剤`
- `アルコール消毒`

This is a safe small batch because source workbook, sheet, row, account, and
month samples are known for at least two rows, and a support calculation row is
known for the third.

### 2. System Cost

Still recommended as a high-impact identifiable group from Phase 42N1Q-A, but it
needs separate source trace against the IT/System simulation workbooks.

### 3. Birthday / NNN

Small enough to implement after dedicated source mapping.

### 4. Fixed Assets later

Keep later because it intersects fixed-form rows and existing output placement
risks.

## Conclusion

`WARNING_PHASE_42N1R_A_SOURCE_TRACE_PARTIAL`

The source trace is strong for a small Admin consumables slice, but partial for
most sampled Unknown/detail rows. The fastest safe next implementation is an
Admin detail expense file-order group for the confirmed consumable rows, while
remaining detail rows require broader source discovery.
