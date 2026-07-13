# Phase 42N1R-B - Repo-wide Source Discovery

## Scope

Repo-wide scan for source evidence behind untraced primary detail rows from the
Phase 42N1Q-A / 42N1R-A audits. This is source discovery only: no code changes,
no workbook output changes, and no formula correctness conclusions.

## Scan scope

Directories scanned:

- `raw/`
- `raw/requirements/`
- `docs/MP2027/`
- `reference_outputs/secondary/`

File types requested/scanned:

- `.xlsx`
- `.xlsm`
- `.xls`
- `.csv`

## Scan summary

| Metric | Count |
|---|---:|
| Candidate files scanned/listed | 37 |
| Unreadable `.xls` files | 6 |
| Search tokens | 19 |
| Tokens found | 4 |
| Tokens not found | 15 |

`.xlsx`, `.xlsm`, and `.csv` files were scanned directly. `.xls` files were
listed but not parsed because the current environment lacks an `.xls` reader.

## Unreadable `.xls` files

These require an `.xls` reader/conversion step before source evidence can be
considered complete:

- `raw/システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls`
- `raw/システム課金金額(Simulation)_FY2027_Jan.2027 ~ March.2027(Change SAP price).xls`
- `raw/システム課金金額(Simulation)_FY2027_July.2026 ~ Dec.2026(Change AMS & PLM price).xls`
- `docs/MP2027/システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls`
- `docs/MP2027/システム課金金額(Simulation)_FY2027_Jan.2027 ~ March.2027(Change SAP price).xls`
- `docs/MP2027/システム課金金額(Simulation)_FY2027_July.2026 ~ Dec.2026(Change AMS & PLM price).xls`

## Token hit table

| Token | Hits | Representative matches |
|---|---:|---|
| `トイレットペーパー` | 8 | `raw/総務課 FY2027 MP 振替予定.xlsx` / `FY2027予定` row 7; `raw/FY2027配賦額一覧 (2025.12.29).xlsx` row 19 |
| `手洗い洗剤` | 9 | `raw/総務課 FY2027 MP 振替予定.xlsx` / `FY2027予定` row 6; `raw/FY2027配賦額一覧 (2025.12.29).xlsx` row 20 |
| `アルコール消毒` | 3 | `raw/総務課 FY2027 MP 振替予定.xlsx` / `Cách tính phân bổ 振替計算` row 15; `docs/MP2027/old/FORM_old.xlsx` row 126 |
| `COURIER` | 3 | `raw/FORM.xlsx` / `内訳ﾘｽﾄ(4～3月)` row 130; `docs/MP2027/FORM.xlsx` row 130; `docs/MP2027/old/FORM_old.xlsx` row 108 |

## Tokens not found

These tokens were not found in readable `.xlsx/.xlsm/.csv` sources under the
scan scope:

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

For these tokens the current result is `SOURCE_NOT_FOUND_IN_REPO_READABLE_FILES`.
This does not prove the data is absent from the project; it may be inside the
unread `.xls` workbooks, external source files not present in the repo, or only
present in the primary output workbook.

## Top source workbooks by hit count

| File | Hit count | Notes |
|---|---:|---|
| `raw/総務課 FY2027 MP 振替予定.xlsx` | 5 | Strong Admin/Tổng vụ consumables source |
| `docs/MP2027/総務課 FY2027 MP 振替予定.xlsx` | 5 | Mirror of Admin/Tổng vụ source |
| `raw/FY2027配賦額一覧 (2025.12.29).xlsx` | 4 | Allocation metadata for common consumables |
| `docs/MP2027/FY2027配賦額一覧 (2025.12.29).xlsx` | 4 | Mirror allocation metadata |
| `docs/MP2027/old/FORM_old.xlsx` | 3 | Historical/template references |
| `raw/FORM.xlsx` | 1 | Template row for courier |
| `docs/MP2027/FORM.xlsx` | 1 | Template row for courier |

## Does the repo have enough source evidence for the missing 140 rows?

No, not yet.

The repo has enough readable source evidence for a small Admin/Tổng vụ consumable
batch and template-level courier evidence. It does not currently have readable
source evidence for most sampled engineering/detail rows, including parts,
measurement tools, RAM/USB/media, calibration, import-air, and return-difference
items.

Because six `.xls` System Cost simulation workbooks were not parsed, the evidence
is incomplete for System Cost and related tokens. A conversion/read step for
those `.xls` workbooks is needed before deciding whether they explain a large
portion of the remaining gap.

## Recommended next implementation batch

### Batch 1 - Admin detail expense file-order group

Implement a small file-order group for confirmed readable Admin/Tổng vụ
consumables:

- `トイレットペーパー`
- `手洗い洗剤`
- `アルコール消毒`

Evidence exists in both the Admin workbook and allocation master.

### Batch 2 - `.xls` System Cost source-read/convert audit

Before implementing System Cost rows, add a read/convert audit for the three
System Cost `.xls` source workbooks. They are currently `NEED_XLS_READER` and may
contain source evidence for high-impact missing rows.

### Batch 3 - Request/add missing engineering detail source

For tokens not found in readable files (`Marking pen`, `Battery 9V`, `Panel LCD`,
`USB 10本`, etc.), ask the source owner for the workbook or identify whether these
rows are primary-only/manual additions.

## Conclusion

`WARNING_PHASE_42N1R_B_SOURCES_MISSING_OR_UNREADABLE`

The scan found solid evidence for the Admin consumables slice but not enough
repo-readable evidence to generate all missing detail rows. The largest blocker
is unread `.xls` source data and missing/unidentified engineering detail source
workbooks.
