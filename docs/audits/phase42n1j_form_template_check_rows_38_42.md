# Phase 42N1J - FORM/template check for rows 38 and 42

## Files inspected

- `FORM.xlsx` sheet `内訳ﾘｽﾄ(4～3月)`
- `raw\FORM.xlsx` sheet `内訳ﾘｽﾄ(4～3月)`
- `docs\MP2027\FORM.xlsx` sheet `内訳ﾘｽﾄ(4～3月)`
- `dist\phase42n1b3_row5_template_parity_20260607_065031\generated\MP_CC_1412000040.xlsx` sheet `内訳ﾘｽﾄ(4～3月)`
- `reference_outputs\primary\16.KDTVN 電気製造技術課_MP FY2027_各予定(Ver01).xlsx` sheet `内訳ﾘｽﾄ(4～3月)`

Template workbook path found: `FORM.xlsx` (same row snapshots as `raw/FORM.xlsx` and `docs/MP2027/FORM.xlsx`).

## Template workbook context

- Sheet inspected: `内訳ﾘｽﾄ(4～3月)`
- Rows 38/40/42 are not hidden.
- No merged cells around rows 38/40/42.
- Template F:Q cells are blank input/formula slots; R keeps `SUM(F:Q)`.

## Row snapshot table

| row | workbook | account/code | description | F sample | Q sample | R sample | classification |
|---:|---|---:|---|---|---|---|---|
| 38 | `FORM_root` | 5006016244 | 減価償却費（設備）/Khấu hao (Thiết bị) | `` | `` | `=SUM(F38:Q38)` | `TEMPLATE_CONFIRMED` |
| 38 | `generated` | 5006016244 | 減価償却費（設備）/Khấu hao (Thiết bị) | `=ROUND(165.39*$B$2,0)` | `=ROUND(165.39*$B$2,0)` | `=SUM(F38:Q38)` | `BAM_THEO_FORM_TEMPLATE` |
| 40 | `primary` | 5006016244 | Depreciation 工具治 | `=ROUND(165.39*26273,0)` | `=ROUND((165.39+152.78+166.67)*26273,0)` | `=SUM(F40:Q40)` | `PRIMARY_SAME_IDENTITY_DIFFERENT_ROW` |
| 40 | `FORM_root` | 9114120007 | 固定資産金利（建物）/Lãi (Nhà) | `` | `` | `=SUM(F40:Q40)` | `TEMPLATE_CONFIRMED` |
| 40 | `generated` | 9114120007 | 固定資産金利（建物）/Lãi (Nhà) | `=ROUND(188.35*$B$2,0)` | `=ROUND(175.38*$B$2,0)` | `=SUM(F40:Q40)` | `BAM_THEO_FORM_TEMPLATE` |
| 303 | `primary` | 9114120007 | 固定資産金利(建物、土地) | `=ROUND((188.35+23.88)*26273,0)` | `=ROUND((175.38+22.85)*26273,0)` | `=SUM(F303:Q303)` | `PRIMARY_SAME_IDENTITY_DIFFERENT_ROW` |
| 42 | `FORM_root` | 9114120007 | 固定資産金利（設備）/Lãi (Thiết bị) | `` | `` | `=SUM(F42:Q42)` | `TEMPLATE_CONFIRMED` |
| 42 | `generated` | 9114120007 | 固定資産金利（設備）/Lãi (Thiết bị) | `=ROUND(17.88*$B$2,0)` | `=ROUND(14.9*$B$2,0)` | `=SUM(F42:Q42)` | `BAM_THEO_FORM_TEMPLATE` |
| 302 | `primary` | 9114120007 | 固定資産金利(治具) | `=ROUND(17.88*26273,0)` | `=ROUND((14.9+16.5+18)*26273,0)` | `=SUM(F302:Q302)` | `PRIMARY_SAME_IDENTITY_DIFFERENT_ROW` |

## Answers to required checks

### A. FORM/template row 38

FORM row 38 is confirmed as fixed asset depreciation/equipment: `減価償却費（設備）/Khấu hao (Thiết bị)`, account `5006016244`, R formula `=SUM(F38:Q38)`. Generated row 38 keeps the same account/description/R formula and fills F:Q formulas. Primary same identity is row 40, not primary row 38.

### B. FORM/template row 42

FORM row 42 is confirmed as fixed asset interest/equipment: `固定資産金利（設備）/Lãi (Thiết bị)`, account `9114120007`, R formula `=SUM(F42:Q42)`. Generated row 42 keeps the same account/description/R formula and fills F:Q formulas. Primary same identity is row 302.

### C. FORM/template row 40

FORM row 40 is facility/building-land interest: `固定資産金利（建物）/Lãi (Nhà)`, account `9114120007`. It is not the fixed asset equipment interest row. Primary same identity is row 303.

### D. Generated rows 38/42

Generated rows 38 and 42 are following the FORM template row positions, account codes, descriptions, row heights, hidden flags, and R formulas. They are not following primary reference row numbers.

### E. Primary identity context

- Generated row 38 matches primary row 40 by depreciation/tool-equipment identity.
- Generated row 42 matches primary row 302 by fixed-asset interest/tool-jig identity.
- Primary row 303 is building/land interest and matches generated row 40, not generated row 42.

### F. Nature of F:Q/R diffs

The remaining F:Q/R diffs are formula/value expression differences after identity alignment. Template context confirms row placement, but it does not prove whether generated formulas or primary formulas are correct. The next evidence needed is the source workbook for fixed assets/facility and its monthly amount logic.

## Conclusion per row

| row | conclusion | rationale |
|---:|---|---|
| 38 | `TEMPLATE_CONFIRMED` + `NEED_SOURCE_WORKBOOK_CHECK` | FORM confirms row 38 is fixed asset depreciation; source workbook is still needed to judge F:Q formula/value differences. |
| 42 | `TEMPLATE_CONFIRMED` + `NEED_SOURCE_WORKBOOK_CHECK` | FORM confirms row 42 is fixed asset equipment interest; source workbook is still needed to judge F:Q formula/value differences. |

## Recommended next action

Inspect fixed asset source workbook `raw/固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx` and facility source workbook `raw/施設課　MPFY2027.xlsx` read-only, then trace monthly amounts for generated rows 38/40/42 against primary rows 40/302/303.

## Forbidden conclusions

- Do not call row 38/42 a code bug from strict diff alone.
- Do not claim missing input snapshot from formula/value diff alone.
- Do not compare generated row 38 to primary row 38 or generated row 42 to primary row 42 as fixed-row business evidence.
- Do not modify FORM/template/output during this audit.
