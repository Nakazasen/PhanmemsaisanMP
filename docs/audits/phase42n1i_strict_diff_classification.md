# Phase 42N1I - Strict identity diff classification
## Scope

This audit classifies strict compare diffs after Phase 42R0 and 42N1G-2R2. It does not change business logic, parser/exporter, template, output, compare tool, or tests.
## Inputs
- Requirement lock: `docs\audits\phase42r0_canonical_requirement_reconciliation.md`
- Strict compare JSON: `dist\phase42n1g2r2_identity_disambiguation\strict_compare\MP2027_primary_reference_compare.json`
- Strict compare XLSX: `dist/phase42n1g2r2_identity_disambiguation/strict_compare/MP2027_primary_reference_compare.xlsx`
## Strict compare summary
- `strict_diff_total`: `104`
- `new_identity_rows_matched`: `5`
- `new_identity_rows_ambiguous`: `0`
- `existing_identity_rows_matched`: `1`
- `existing_identity_rows_ambiguous`: `7`
- `real_identity_strict_diffs_remaining`: `55`

## 104 diffs by category

| Category | Diff count | Meaning |
|---|---:|---|
| `TEMPLATE_LAYOUT_DIFF` | 49 | Header/layout/template formula diffs, not business item evidence. |
| `REAL_IDENTITY_STRICT_DIFF` | 14 | Identity matched; formula/value differs from primary. |
| `NEED_FORM_TEMPLATE_CHECK` | 26 | Requirement/FORM target context must be verified first. |
| `NEED_SOURCE_WORKBOOK_CHECK` | 15 | Need actual source workbook/count/formula evidence. |
| `AMBIGUOUS_IDENTITY_REMAINING` | 0 | Identity not safe enough to compare values. |
| `REQUIREMENT_CONFIRMED_EXPECTED_DIFF` | 0 | Requirement indicates primary may be old/different; none concluded yet. |
| `POSSIBLE_INPUT_SNAPSHOT_MISMATCH` | 0 | Possible only after source workbook inspection; none concluded yet. |
| `POSSIBLE_CODE_BUG` | 0 | Requires clear requirement + source evidence; none concluded yet. |

## Row-level table

| generated_row | primary_row | business label | diff_count | sample diff cells | category | confidence | recommended next action | forbidden conclusion |
|---:|---:|---|---:|---|---|---|---|---|
| 3 | 3 | Layout/header/template row | 12 | `F, G, H, I, J, K, L, M, N, O, P, Q` | `TEMPLATE_LAYOUT_DIFF` | High | Inspect template/header formula parity separately; do not treat as business item. | Do not claim missing input snapshot or code bug from layout rows alone. |
| 9 | 9 | Layout/header/template row | 12 | `F, G, H, I, J, K, L, M, N, O, P, Q` | `TEMPLATE_LAYOUT_DIFF` | High | Inspect template/header formula parity separately; do not treat as business item. | Do not claim missing input snapshot or code bug from layout rows alone. |
| 17 | 17 | Layout/header/template row | 12 | `F, G, H, I, J, K, L, M, N, O, P, Q` | `TEMPLATE_LAYOUT_DIFF` | High | Inspect template/header formula parity separately; do not treat as business item. | Do not claim missing input snapshot or code bug from layout rows alone. |
| 25 | 25 | Layout/header/template row | 13 | `F, G, H, I, J, K, L, M, N, O, P, Q, R` | `TEMPLATE_LAYOUT_DIFF` | High | Inspect template/header formula parity separately; do not treat as business item. | Do not claim missing input snapshot or code bug from layout rows alone. |
| 38 | 40 | Fixed asset depreciation | 13 | `F, G, H, I, J, K, L, M, N, O, P, Q, R` | `NEED_FORM_TEMPLATE_CHECK` | Medium | Check FORM target row/template meaning and source workbook before deciding code/input issue. | Do not call code bug or missing snapshot before FORM/template and source workbook check. |
| 40 | 303 | Facility/building-land interest | 13 | `F, G, H, I, J, K, L, M, N, O, P, Q, R` | `REAL_IDENTITY_STRICT_DIFF` | Medium | Identity is evidence-matched; inspect facility source rows and formulas before deciding input/code. | Do not collapse Facility into one row; do not call code bug without source workbook check. |
| 42 | 302 | Fixed asset equipment/tool interest | 13 | `F, G, H, I, J, K, L, M, N, O, P, Q, R` | `NEED_FORM_TEMPLATE_CHECK` | Medium | Check FORM target row/template meaning and source workbook before deciding code/input issue. | Do not call code bug or missing snapshot before FORM/template and source workbook check. |
| 51 | 215 | Cleaning/admin allocation | 13 | `F, G, H, I, J, K, L, M, N, O, P, Q, R` | `NEED_SOURCE_WORKBOOK_CHECK` | Medium | Inspect admin allocation/cleaning source and account mapping; row 51 was identity-matched. | Do not use Phase 42N1D/E fixed-row request pack. |
| 59 | 269 | Birthday | 2 | `J, R` | `NEED_SOURCE_WORKBOOK_CHECK` | Medium | Inspect birthday source counts/new joiners/unit price and FORM row 59/63 conflict context. | Do not assert missing input solely from primary diff; birthday has known row 63 vs 59 requirement risk. |
| 66 | 281 | Company trip | 1 | `R` | `REAL_IDENTITY_STRICT_DIFF` | Low | Existing identity row still has one strict diff; inspect business/source if this row remains in scope. | Do not conflate with new rows 38/40/42/51/59. |
| 53 |  | 蜃ｺ蜷題・US騾∬ｿ手ｲｻ/Chi phﾃｭ xe bus ngﾆｰ盻拱 JP | 0 | `` | `AMBIGUOUS_IDENTITY_REMAINING` | High | Keep out of strict value conclusions until identity evidence is refined. | Do not force match by row number or same account only. |
| 54 |  | 繝ｭ繝ｼ繧ｫ繝ｫ遉ｾBUS騾∬ｿ手ｲｻ/Chi phﾃｭ xe bus ngﾆｰ盻拱 VN | 0 | `` | `AMBIGUOUS_IDENTITY_REMAINING` | High | Keep out of strict value conclusions until identity evidence is refined. | Do not force match by row number or same account only. |
| 58 |  | 謗｡逕ｨ縺ｮ蛛･蠎ｷ險ｺ譁ｭ雋ｻ/Chi phﾃｭ khﾃ｡m s盻ｩc kh盻銃 tuy盻ハ d盻･ng | 0 | `` | `AMBIGUOUS_IDENTITY_REMAINING` | High | Keep out of strict value conclusions until identity evidence is refined. | Do not force match by row number or same account only. |
| 75 |  | System Cost (Mail,VPN,R3, Mes,PLM,VPS,窶ｦ) | 0 | `` | `AMBIGUOUS_IDENTITY_REMAINING` | High | Keep out of strict value conclusions until identity evidence is refined. | Do not force match by row number or same account only. |
| 97 |  | 譁ｰ蜈･遉ｾ蜩｡・壹ヮ繝ｼ繝茨ｼ医せ繧ｿ繝・ヵ逕ｨ・・Ngﾆｰ盻拱 m盻嬖: S盻・tay (Dﾃｹng cho nhﾃ｢n viﾃｪn) | 0 | `` | `AMBIGUOUS_IDENTITY_REMAINING` | High | Keep out of strict value conclusions until identity evidence is refined. | Do not force match by row number or same account only. |
| 98 |  | 譁ｰ蜈･遉ｾ蜩｡・壹ヮ繝ｼ繝・(G7遉ｾ蜩｡逕ｨ・・Ngﾆｰ盻拱 m盻嬖: S盻・tay (Dﾃｹng cho cﾃｴng nhﾃ｢n) | 0 | `` | `AMBIGUOUS_IDENTITY_REMAINING` | High | Keep out of strict value conclusions until identity evidence is refined. | Do not force match by row number or same account only. |
| 137 |  | 蜃ｺ蜷題・・譖ｸ鬘樒筏隲玖ｲｻ/Chi phﾃｭ lﾃm gi蘯･y t盻・cho ngﾆｰ盻拱 bi盻㏄ phﾃ｡i | 0 | `` | `AMBIGUOUS_IDENTITY_REMAINING` | High | Keep out of strict value conclusions until identity evidence is refined. | Do not force match by row number or same account only. |

## Requirement lock notes for business rows with diffs

### Row 38

- Generated description: `貂帑ｾ｡蜆溷唆雋ｻ・郁ｨｭ蛯呻ｼ・Kh蘯･u hao (Thi蘯ｿt b盻・`
- Primary matched row: `40`
- Primary description: `Depreciation 蟾･蜈ｷ豐ｻ`
- Matched fields: `account,tokens`
- Match note: `same account with preferred identity token`
- Classification from compare: `matched_identity_with_strict_diffs`
- Requirement note: 42R0-G1: Fixed asset depreciation target F38:Q38; NEED_FORM_TEMPLATE_CHECK; compare to primary must be identity-aware.

### Row 40

- Generated description: `蝗ｺ螳夊ｳ・肇驥大茜・亥ｻｺ迚ｩ・・Lﾃ｣i (Nhﾃ)`
- Primary matched row: `303`
- Primary description: `蝗ｺ螳夊ｳ・肇驥大茜(蟒ｺ迚ｩ縲∝悄蝨ｰ)`
- Matched fields: `account,tokens,building_land_tokens`
- Match note: `disambiguated by building/land token evidence`
- Classification from compare: `matched_identity_with_strict_diffs`
- Requirement note: 42R0-F1/F2: Facility has six separate items; do not collapse or fixed-row compare by primary row number.

### Row 42

- Generated description: `蝗ｺ螳夊ｳ・肇驥大茜・郁ｨｭ蛯呻ｼ・Lﾃ｣i (Thi蘯ｿt b盻・`
- Primary matched row: `302`
- Primary description: `蝗ｺ螳夊ｳ・肇驥大茜(豐ｻ蜈ｷ)`
- Matched fields: `account,tokens,tool_jig_tokens`
- Match note: `disambiguated by tool/jig token evidence`
- Classification from compare: `matched_identity_with_strict_diffs`
- Requirement note: 42R0-G2: Fixed asset interest target F42:Q42; NEED_FORM_TEMPLATE_CHECK; compare to primary must be identity-aware.

### Row 51

- Generated description: `cleaning fee`
- Primary matched row: `215`
- Primary description: `貂・祉雋ｻ`
- Matched fields: `account,tokens`
- Match note: `same account with preferred identity token`
- Classification from compare: `matched_identity_with_strict_diffs`
- Requirement note: 42R0-H1/H2: Administrative allocation is high priority; classify by business item/account, not same-row primary.

### Row 59

- Generated description: `隱慕函譌･莨・Ti盻］ sinh nh蘯ｭt`
- Primary matched row: `269`
- Primary description: `隱慕函譌･莨夲ｼ・52,000vnd`
- Matched fields: `account,tokens`
- Match note: `same account with preferred identity token`
- Classification from compare: `matched_identity_with_strict_diffs`
- Requirement note: 42R0-D1: Birthday accepted target F59:Q59 but row 63 conflict remains MD_INTERPRETATION_RISK.

### Row 66

- Generated description: `None`
- Primary matched row: `281`
- Primary description: `遉ｾ蜩｡譌・｡鯉ｼ・,874,000`
- Matched fields: `account,tokens`
- Match note: `same account`
- Classification from compare: `matched_identity_with_strict_diffs`
- Requirement note: N/A

## Top 3 next safest actions

1. Inspect source workbooks for row 51 Cleaning/admin allocation and row 59 Birthday before claiming input mismatch or code bug.
2. Check FORM/template context for Fixed Assets rows 38 and 42, then inspect Fixed Assets source workbook for formulas/month logic.
3. Keep existing ambiguous identity rows out of strict value conclusions until identity rules are refined with evidence.

## Conclusions we must NOT make yet

- Do not say 窶徇issing input snapshot窶・for layout rows 3/9/17/25.
- Do not say 窶彡ode bug窶・for rows 38/40/42/51/59 before source workbook inspection.
- Do not send or rely on Phase 42N1D/42N1E fixed-row request packs.
- Do not force-match existing identity rows by row number or same account alone.
- Do not treat System Cost/Facility layout differences as bugs without applying the 42R0 requirement lock.

## Commit recommendation

DO_NOT_COMMIT unless the user approves a report-only commit.
