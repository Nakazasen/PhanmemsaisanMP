# Phase 42N1Q-A - Missing Row Gap Breakdown

## Scope

This audit breaks down the `140` business-row count gap reported in Phase 42N1P-B.
It is a planning report only. It does not change code and does not conclude a bug
where rows simply have not yet migrated to file-order output.

## Files inspected

- Generated flag ON: `dist/phase42n1p_b_facility_export_flag/flag_on/OUTPUT_FY2027/MP_CC_1412000040.xlsx`
- Primary reference: `reference_outputs/primary/16.KDTVN 電気製造技術課_MP FY2027_各予定(Ver01).xlsx`
- Prior audit: `docs/audits/phase42n1p_b_output_row_count_vs_primary.md`
- Architecture audit: `docs/audits/phase42n1l_output_mode_architecture.md`
- Requirement reconciliation: `docs/audits/phase42r0_canonical_requirement_reconciliation.md`

## Count method

Sheet: `内訳ﾘｽﾄ(4～3月)`.

A row is counted as business row when it is not one of layout rows
`1, 2, 3, 4, 5, 9, 17, 25` and has at least one of:

- code/account-like value in column `B`, or
- description in column `S`, or
- value/formula in month columns `F:Q`.

Matching was heuristic:

- prefer exact normalized description match,
- otherwise require compatible account/code and strong token overlap,
- do not force ambiguous matches.

> [!WARNING]
> Group mapping is approximate. Many primary rows do not have enough stable
> source metadata in the output sheet alone, so they remain classified as
> `Unknown/needs manual mapping` until traced to source files.

## Count summary

| Metric | Count |
|---|---:|
| Generated flag ON business rows | 137 |
| Primary business rows | 277 |
| Count gap | 140 |
| Heuristic matched primary rows | 19 |
| Heuristic missing primary rows | 258 |
| Heuristic extra generated rows | 118 |

The `140` count gap is the reliable total row-count gap from Phase 42N1P-B.
The matched/missing/extra numbers above are heuristic identity-analysis numbers;
they are higher because generated rows and primary rows often use different row
placement or text conventions.

## Group breakdown

| Group | Primary rows | Generated rows | Matched | Missing | Extra generated | Confidence |
|---|---:|---:|---:|---:|---:|---|
| Unknown/needs manual mapping | 224 | 86 | 1 | 223 | 85 | low |
| System Cost | 21 | 13 | 1 | 20 | 12 | medium |
| Existing fixed-row/template/header | 15 | 12 | 5 | 10 | 7 | medium |
| Admin allocation | 12 | 13 | 12 | 0 | 1 | high |
| Facility | 0 | 6 | 0 | 0 | 6 | high |
| NNN paperwork | 3 | 3 | 0 | 3 | 3 | low-medium |
| Fixed Assets | 1 | 3 | 0 | 1 | 3 | low-medium |
| Birthday | 1 | 1 | 0 | 1 | 1 | low-medium |

## Top missing groups

1. `Unknown/needs manual mapping` dominates the missing identity analysis.
   These are mostly concrete expense/detail rows in primary that need source
   trace before safe migration.
2. `System Cost` is the largest identifiable implementation group.
3. `Existing fixed-row/template/header` still has mismatches in fixed-form rows
   and should be treated carefully because it may include template/layout rows.

## Facility status

Facility generated rows `200-205` are complete against the current Facility
file-order requirement:

- Khấu hao nhà
- Khấu hao đất
- Lãi nhà
- Lãi đất
- Điện
- Nước

Row `206` is blank in the generated flag ON workbook.

Facility should not be judged by primary row number identity in this phase,
because the approved architecture allows file-order placement instead of primary
fixed-row matching.

## Sample missing primary rows

| Primary row | Group | Code/account | Description |
|---:|---|---|---|
| 8 | Existing fixed-row/template/header | 出向社員定時 |  |
| 10 | Existing fixed-row/template/header | 出向社員定時 |  |
| 11 | Existing fixed-row/template/header | ローカル社員定時 |  |
| 16 | Existing fixed-row/template/header | 出向社員残業 |  |
| 18 | Existing fixed-row/template/header | 出向社員残業 |  |
| 19 | Existing fixed-row/template/header | ローカル社員残業 |  |
| 24 | Existing fixed-row/template/header | 出向社員(人) |  |
| 36 | Existing fixed-row/template/header | 9114120009 |  |
| 38 | Existing fixed-row/template/header | 5006016260 | 建物 |
| 39 | Existing fixed-row/template/header | 5006016261 | 土地 |
| 40 | Fixed Assets | 5006016244 | Depreciation 工具治 |
| 42 | Unknown/needs manual mapping | 5005016372 | トイレットペーパー |
| 43 | Unknown/needs manual mapping | 5005016372 | 手洗い洗剤 |
| 44 | Unknown/needs manual mapping | 5005016372 | アルコール消毒 |
| 45 | Unknown/needs manual mapping | 5005016372 | Marking pen |
| 46 | Unknown/needs manual mapping | 5005016372 | Sprayway 955 Anti Static |
| 49 | Unknown/needs manual mapping | 5005016371 | TH conect, conecR半田ブリッジ対応実験 |
| 50 | Unknown/needs manual mapping | 5005016371 | Battery 9V(13,000) |
| 51 | Unknown/needs manual mapping | 5005016371 | Pin Energizer AA(26,500/pcs) |
| 52 | Unknown/needs manual mapping | 5005016371 | Main pictor TV2YV01010 DL治具開発用 + Main pictor TV2YW01010 DL治具開発用 |

## Recommended implementation batches

### Batch 1 - System Cost

System Cost is the clearest large identifiable group after Facility. It likely
benefits from the same file-order placement pattern already introduced for
Facility, but needs source trace for exact row grouping and item ordering.

### Batch 2 - Unknown/detail expense source trace

The largest row gap is currently classified as unknown/detail rows. Many rows
look like concrete consumables, parts, repair, calibration, import/courier, or
local detail expenses. This should be traced to source files before coding.

### Batch 3 - Birthday + NNN paperwork

These groups are smaller. They can reduce mismatch risk incrementally once their
source rows and desired output mode are confirmed.

### Batch 4 - Fixed Assets

Fixed Assets intersects with existing fixed rows and row-compatibility concerns.
Treat this as higher risk and avoid direct row patching until source trace and
placement mode are clear.

## Conclusion

`COUNT_METHOD_UNCERTAIN`

The reliable count fact remains: generated flag ON has `137` business rows,
primary has `277`, and the output is still `140` rows shorter. The group mapping
strongly suggests the largest remaining work is not Facility, but detailed
expense rows and System Cost-like groups. However, output-only classification is
not precise enough to safely implement all missing rows without a source-trace
phase.
