# Fixed-assets cross-trace audit — FY2026/FY2027

**Audit date:** `2026-07-16`  
**Mode:** read-only source/reference audit; no production accounting code changed  
**Classification:** `NOT_ACCEPTED_FIXED_ASSETS_CALCULATION`; lifecycle remains `OPEN_AUDIT`

## Scope and authority

1. Canonical requirement: `raw/Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx`, sheet `Chi phí tài sản cố định`.
2. Company calculation sources: the two `固定資産情報_Fixed_Assets_Information_*.xlsx` workbooks in `docs/MP2026` and `docs/MP2027`.
3. Department truth folders: `raw/FY2026`, `raw/FY2027`.
4. Submitted reference outputs: top-level `.xlsx` workbooks in `reference_outputs/secondary/FY2026` and `FY2027`.
5. Current code is compared as implementation evidence, not business authority.

## Corpus summary

| FY | Source rows | Supported source rows | Reference workbooks | Reference CCs | FX rates | Raw truth workbooks | Raw fixed-asset account cells |
|---|---:|---:|---:|---:|---|---:|---:|
| FY2026 | 1997 | 1860 | 64 | 62 | `{"25390": 64}` | 63 | 0 |
| FY2027 | 1267 | 1141 | 65 | 64 | `{"26273": 59}` | 64 | 0 |

`raw/FY2026` and `raw/FY2027` are headcount/time-plan submissions in the current corpus. FY2026 scanned cleanly with no fixed-assets account-code cell. FY2027 had the same result for readable files, but one legacy `.xls` failed `xlrd` parsing, so the claim is limited to 63/64 FY2027 workbooks. Fixed-assets amount truth is carried by the company calculation workbooks and submitted final reference outputs, not by the readable raw headcount files.

## Reference-layer separation

Reference workbooks frequently contain source-derived rows beside manual carry-over, cumulative, facility, and future-asset rows sharing the same account. The comparator selects, per FY/CC/account, the subset of rows with the lowest 12-month absolute difference to the source-derived target. Excluded rows remain in the reference-row ledger and are never silently discarded.

| FY | Selected source-derived candidates | Excluded manual/other layers | Critical L/P/Q/V/W cache gaps | Negative critical inputs | Terminal-within-FY missing Q |
|---|---:|---:|---:|---:|---:|
| FY2026 | 172 | 122 | 0 | 0 | 0 |
| FY2027 | 166 | 197 | 0 | 0 | 0 |

## Monthly comparison result

| Classification | FY2026 | FY2027 | Total |
|---|---:|---:|---:|
| `EXACT_MATCH` | 155 | 249 | 404 |
| `EXTRA_REFERENCE_OUTPUT` | 3 | 4 | 7 |
| `MISSING_REFERENCE_OUTPUT` | 125 | 78 | 203 |
| `ROUNDING_ORDER` | 134 | 88 | 222 |
| `TRUE_AMOUNT_MISMATCH` | 243 | 395 | 638 |

Compared monthly CC/account cells: **1474**. Non-exact cells: **1070**. True amount mismatches after separating rounding/terminal-policy cases: **638**.

## Decision

The fixed-assets calculation is **not accepted as correct**. Exact matches exist, but the current implementation violates the per-asset rounding contract, and hundreds of source/reference monthly cells remain materially different after separating manual layers.

| FY | Rounding-order cells | Net VND delta vs per-asset | Absolute VND delta | True mismatch cells | True mismatches > 1m VND | Largest true mismatch |
|---|---:|---:|---:|---:|---:|---:|
| FY2026 | 134 | -824 | 920 | 243 | 132 | 250877381 |
| FY2027 | 88 | -2 | 194 | 395 | 169 | 362905231 |

## Proven rules and findings

- Reference output uses the workbook FX rate in `B2`; the observed FY-specific rates are evidence, not production constants.
- `ROUNDING_ORDER` cells are cases where submitted output equals the current writer's category-first rounding but differs from the required per-asset rounding. The monetary deltas are small, but the calculation order is still wrong.
- Terminal within FY has a direct failure example: source `docs/MP2026/固定資産情報_Fixed_Assets_Information_2024.12 - December.xlsx`, `2024.12!L42/P42/Q42`, ends in `202601`; reference `24.KDTVN 品質保証課_MP FY2026_各予定(Ver01).xlsx`, detail row 123, continues the same monthly depreciation through `202602` and `202603`.
- Terminal before FY is determined at amount level as no FY cost: source FY2027 `2025.11!L1257/P1257/Q1257` ends in `202512`; reference CC `1412000081`, account `5006016247`, row 45 is zero for all FY2027 months. New output must represent post-terminal as blank, not zero, per canonical wording.
- `TRUE_AMOUNT_MISMATCH` remains unexplained after both policy calculations and requires row/formula-level review in the evidence CSVs.
- Several large true mismatches are identifiable as source-snapshot/manual future-asset differences rather than arithmetic alone; they cannot be accepted or overwritten without row-level provenance.

## Current-code assessment

- `src/parsers/fixed_assets.py` still has fallback FY/FX values, hard-coded category/account mapping, positive-only filtering, Q-to-L fallback, and deletes all fixed-assets history on import.
- `src/engine/hub_builder.py::_load_fixed_asset_source_order_rows()` sums asset USD by category and then emits one `ROUND(sum*$B$2,0)`. This is not the canonical per-asset rounding contract and the monthly evidence file quantifies the affected rows.
- The source-order writer correctly relocates dynamic fixed-assets rows when provided, but it cannot repair upstream calculation/provenance loss.

## Evidence artifacts

- `docs/audits/fixed_assets_asset_ledger_2026-07-16.csv`
- `docs/audits/fixed_assets_reference_rows_2026-07-16.csv`
- `docs/audits/fixed_assets_monthly_comparison_2026-07-16.csv`
- `docs/audits/fixed_assets_cross_trace_summary_2026-07-16.json`

## Status

Keep `FA-OPEN` as `OPEN_AUDIT`. Fixing rounding order is evidence-backed; resolving the remaining source-snapshot/manual rows requires a decision matrix and provenance classification before changing accounting logic.
