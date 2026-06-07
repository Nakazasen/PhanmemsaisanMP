# Phase 42N1S-A2 - Full Raw Source Scan Including XLS

## Scope

Full source scan of current raw/input files before making any source-missing
claims. This scan includes `.xlsx`, `.xlsm`, `.csv`, and `.xls` files under the
requested source areas.

No business/export code was changed. No source workbook was modified. No output
workbook was generated.

## Precheck

- Branch: `main`
- HEAD: `f4cf8a4 docs(audit): discover repo sources for missing rows`
- `origin/main...HEAD`: `0 0`
- Working tree: clean before scan.

## Source files inspected

Scan roots:

- `raw/`
- `raw/requirements/`
- `docs/MP2027/`

Files discovered in scope:

| File type | Count | Read success |
|---|---:|---:|
| `.xlsx/.xlsm` | 23 | 23 |
| `.csv` | 8 | 8 |
| `.xls` | 6 | 6 |
| Total | 37 | 37 |

There were no unread files in this scan.

## Source file order confirmation

Both source-order files were inspected:

- `raw/source_file_order.csv`
- `raw/source_file_order.xlsx`

The scan also found mirror copies under `docs/MP2027/`.

The business source family confirmed by the requested file list is:

1. Facility: `施設課　MPFY2027.xlsx`
2. Fixed Assets: `固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx`
3. System Cost `.xls` simulation files
4. Admin/Tổng vụ: `総務課 FY2027 MP 振替予定.xlsx`
5. Birthday: `Sinh nhật MP FY2027.xlsx`
6. Allocation master: `FY2027配賦額一覧 (2025.12.29).xlsx`
7. NNN paperwork: `Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx`
8. Manual CSVs: `special_costs_manual.csv`, `event_drivers_manual.csv`, `headcount_manual.csv`

## XLS method and result

The six `.xls` System Cost files were not skipped.

Read method used:

- `xlrd` read all `.xls` files successfully.
- Excel COM conversion was not required.
- LibreOffice/soffice conversion was not required.
- No converted files were created.

`.xls` result:

| Metric | Count |
|---|---:|
| XLS total | 6 |
| XLS read success | 6 |
| XLS conversion success | 0 |
| XLS read/convert failed | 0 |

## Token scan result

Exact tokens searched:

- `Marking pen`
- `Sprayway 955 Anti Static`
- `TH conect`
- `Battery 9V`
- `Pin Energizer AA`
- `Main pictor`
- `冷却スプレー`
- `Panel LCD`
- `Vendor用Micro SD`
- `湿度計`
- `ノートPC`
- `USB 10本`
- `COURIER`
- `IMPORT AIR`
- `校正`
- `返却差異`
- `トイレットペーパー`
- `手洗い洗剤`
- `アルコール消毒`

Exact tokens found:

- `COURIER`
- `トイレットペーパー`
- `手洗い洗剤`
- `アルコール消毒`

Exact tokens not found after full raw/source scan:

- `Marking pen`
- `Sprayway 955 Anti Static`
- `TH conect`
- `Battery 9V`
- `Pin Energizer AA`
- `Main pictor`
- `冷却スプレー`
- `Panel LCD`
- `Vendor用Micro SD`
- `湿度計`
- `ノートPC`
- `USB 10本`
- `IMPORT AIR`
- `校正`
- `返却差異`

Fuzzy tokens found included:

- `Battery`
- `Courier`
- `Import`
- `Marking`
- `Panel`
- `Pictor`
- `USB`
- `アルコール`
- `トイレット`
- `洗剤`
- `返却`

Most fuzzy hits were broad matches in Fixed Assets or requirement/template sheets
and should not be treated as direct source evidence for the exact primary detail
rows without additional matching.

## Representative mapping table

| Token | Match type | Source file | Converted file | Sheet | Row | Col | Sample | Confidence | Proposed group |
|---|---|---|---|---|---:|---:|---|---|---|
| `トイレットペーパー` | exact | `raw/総務課 FY2027 MP 振替予定.xlsx` | n/a | `FY2027予定` | 7 | 1 | `トイレットペーパー / Giấy vệ sinh`, monthly values, accounts `5005016372/6005016422/6005016413` | HIGH | Admin Detail |
| `手洗い洗剤` | exact | `raw/総務課 FY2027 MP 振替予定.xlsx` | n/a | `FY2027予定` | 6 | 1 | `手洗い洗剤 / Nước rửa tay`, monthly values, accounts `5005016372/6005016422/6005016413` | HIGH | Admin Detail |
| `アルコール消毒` | exact | `raw/総務課 FY2027 MP 振替予定.xlsx` | n/a | `Cách tính phân bổ 振替計算` | 15 | 1 | `アルコール消毒 / Cồn khử trùng`, total row | HIGH | Admin Detail |
| `トイレットペーパー` | exact | `raw/FY2027配賦額一覧 (2025.12.29).xlsx` | n/a | `配賦額一覧` | 19 | 2 | Allocation metadata, account `5005016372` | HIGH | Allocation/Admin Detail |
| `手洗い洗剤` | exact | `raw/FY2027配賦額一覧 (2025.12.29).xlsx` | n/a | `配賦額一覧` | 20 | 2 | Allocation metadata, account `5005016372` | HIGH | Allocation/Admin Detail |
| `COURIER` | exact | `raw/FORM.xlsx` | n/a | `内訳ﾘｽﾄ(4～3月)` | 130 | 19 | `COURIER CHARGES (P)` template row | HIGH | Template/Unknown |
| `Panel` | fuzzy | `raw/固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx` | n/a | `Fixed assets list` | many | 5 | Many fixed-asset rows containing `PANEL`, often CC `1412000008` | MEDIUM | Fixed Assets |
| `USB` | fuzzy | `raw/固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx` | n/a | `Fixed assets list` | many | 5 | Fixed-asset rows containing `USB`, often not exact `USB 10本` | MEDIUM | Fixed Assets |
| `Pictor` | fuzzy | `raw/固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx` | n/a | `2025.11` / `Fixed assets list` | many | 4/16 | Fixed-asset rows containing `PICTOR`, not exact `Main pictor...` | MEDIUM | Fixed Assets |
| `返却` | fuzzy | `raw/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026_ảnh.xlsx` | n/a | `勘定科目` | 53 | 2 | `空箱返却費用` account metadata | MEDIUM | Requirement/account metadata |

## Top source files by hit count

The largest hit counts are dominated by broad fuzzy matches:

| Source file | Hit count | Notes |
|---|---:|---|
| `raw/固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx` | 394 | Broad fuzzy `Panel`/`USB`/`Pictor`/`Battery` matches |
| `docs/MP2027/固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx` | 394 | Mirror of Fixed Assets source |
| `raw/総務課 FY2027 MP 振替予定.xlsx` | 10 | Strong exact Admin consumable hits |
| `docs/MP2027/総務課 FY2027 MP 振替予定.xlsx` | 10 | Mirror exact Admin consumable hits |
| `docs/MP2027/old/FORM_old.xlsx` | 10 | Historical/template exact/fuzzy hits |

## Correction of earlier source-missing conclusion

The earlier broad wording that source was missing was too strong before the raw
source scan was complete.

Corrected conclusion:

- `SOURCE_FOUND_IN_RAW` for Admin consumables:
  - `トイレットペーパー`
  - `手洗い洗剤`
  - `アルコール消毒`
- `SOURCE_FOUND_IN_RAW_TEMPLATE` for `COURIER` template row.
- `SOURCE_FOUND_IN_RAW_FUZZY_ONLY` for broad Fixed Asset terms such as `Panel`,
  `USB`, `Pictor`, and `Battery`; these are not direct evidence for the exact
  primary detail rows.
- `SOURCE_NOT_FOUND_AFTER_FULL_RAW_SCAN` for exact tokens still not found after
  reading all `.xlsx/.xlsm/.csv/.xls` files in the requested source roots.

No `SOURCE_UNKNOWN_DUE_XLS_UNREADABLE` remains for the requested `.xls` files,
because all six were read successfully.

## Does repo now have enough source evidence for the missing rows?

Partially.

Enough evidence exists for a small Admin detail implementation batch and for some
fixed-assets fuzzy investigation. Exact source evidence is still missing for many
engineering/detail rows from the primary output, including `Marking pen`,
`Battery 9V`, `Panel LCD`, `USB 10本`, `IMPORT AIR`, `校正`, and `返却差異`.

## Recommended next implementation batch

### Batch 1 - Admin detail expense file-order group

Proceed with confirmed Admin/Tổng vụ consumables from `raw/総務課 FY2027 MP 振替予定.xlsx`
and allocation metadata from `raw/FY2027配賦額一覧 (2025.12.29).xlsx`:

- `トイレットペーパー`
- `手洗い洗剤`
- `アルコール消毒`

### Batch 2 - Fixed Assets fuzzy-to-primary reconciliation

Because Fixed Assets produced many fuzzy hits for `Panel`, `USB`, `Pictor`, and
`Battery`, reconcile primary exact detail rows against Fixed Assets by account,
CC, asset code, and monthly amounts rather than text alone.

### Batch 3 - System Cost native-structure audit

The `.xls` System Cost files were readable, but the searched exact/detail tokens
were not present. If System Cost is next, audit by CC/account/month structure.

### Batch 4 - Source-owner clarification for unmatched exact rows

For exact tokens still not found after full raw scan, request the missing source
or confirm whether these are primary-only/manual rows.

## Conclusion

`WARNING_PHASE_42N1S_A2_SOURCES_STILL_MISSING_AFTER_FULL_SCAN`

The previous source-missing conclusion has been corrected to a narrower finding:
raw sources are present and were fully readable, including all `.xls` files, but
many exact primary detail tokens still do not appear in the current source/input
set.
