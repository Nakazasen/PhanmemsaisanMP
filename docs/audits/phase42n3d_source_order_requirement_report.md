# Phase 42N3D - Source File Order Requirement Verification

## Classification

`PASS_PHASE_42N3D_SOURCE_FILE_ORDER_REQUIREMENT_VERIFIED`

## Requirement Verified

The current business requirement is:

- do not place current complete-v1 business output by fixed FORM rows;
- output by source file order;
- after each source file block, leave one blank separator row;
- do not verify by hard-coded total output row count;
- do not verify by hard-coded `REFERENCE_FILLED_FROM_PRIMARY` row count.

## Output Audited

`dist\phase42n3d_source_order_requirement_verify\OUTPUT_FY2027\MP_CC_1412000040.xlsx`

## Audit Summary

| Metric | Result |
|---|---:|
| Observed business rows | 242 |
| Legacy fixed rows with business values | 0 |
| Source blocks observed | 7 |
| Source order non-decreasing | True |
| Blank separator rows detected | 103 |

## Observed Source Blocks

- `施設課　MPFY2027.xlsx`
- `固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx`
- `システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls`
- `総務課 FY2027 MP 振替予定.xlsx`
- `Sinh nhật MP FY2027.xlsx`
- `FY2027配賦額一覧 (2025.12.29).xlsx`
- `Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx`

## Static Fixed-Row Audit

Static hit count: `746`

Classification summary:

- `LEGACY_NOTE_OR_TEST_ONLY`: 637
- `NON_PLACEMENT_DATA_MODEL_OR_ACCOUNT_RESOLUTION`: 19
- `LEGACY_STAGING_OR_CLEAR_ONLY_NOT_FINAL_PLACEMENT`: 4
- `APPEND_REFERENCE_LAYER_NOT_FIXED_FORM_PLACEMENT`: 13
- `LEGACY_STAGING_REWRITTEN_BY_COMPLETE_V1`: 16
- `SOURCE_PARSER_LEGACY_METADATA_NOT_FINAL_PLACEMENT`: 57

`ACTIVE_PLACEMENT_LOGIC` count: `0`

Remaining fixed-row mentions are schema/manual metadata, legacy staging that is rewritten by complete-v1, tests, docs, or audit notes. They are not final complete-v1 placement logic.

## Git State Note

`origin/main...HEAD`: `1	0`

The branch is behind remote by one commit at verification time. Per instruction, no pull, merge, or reset was performed.

Forbidden dirty input/output/db files were present before commit and intentionally left unstaged:

- `OUTPUT_FY2027/MP2027_AUDIT_REPORT.md`
- `OUTPUT_FY2027/MP2027_MISSING_INPUTS.csv`
- `mp2027.db`
- `raw/FORM.xlsx`

## Git Status Before Commit

```text
 M OUTPUT_FY2027/MP2027_AUDIT_REPORT.md
 M OUTPUT_FY2027/MP2027_MISSING_INPUTS.csv
 M mp2027.db
 M raw/FORM.xlsx
 M scripts/run_e2e.py
 M src/engine/account_resolver.py
 M src/engine/allocator.py
 M src/engine/facility_file_order_preview.py
 M src/engine/facility_file_order_writer.py
 M src/engine/hub_builder.py
 M src/engine/output_mode.py
 M src/parsers/birthday.py
 M src/parsers/ga.py
 M src/parsers/it_sim.py
 M src/parsers/manual_event_drivers.py
 M src/utils/excel_helpers.py
 M tests/test_account_resolver.py
 M tests/test_facility_file_order_preview.py
 M tests/test_facility_file_order_writer.py
 M tests/test_file_order_export_v1_flag.py
 M tests/test_headcount_and_export.py
 M tests/test_it_sim_parser.py
 M tests/test_manual_event_drivers.py
 M tests/test_output_mode.py
 M tests/test_output_placement.py
?? docs/audits/phase42n2q_all_department_simulation_matrix.csv
?? docs/audits/phase42n2q_all_department_simulation_summary.md
?? docs/audits/phase42n2q_source_derived_gap_to_100_percent.md
?? docs/audits/phase42n3b_source_file_order_output_policy.md
?? docs/audits/phase42n3c_active_fixed_row_reference_inventory.json
?? docs/audits/phase42n3c_source_order_output_verify.json
?? docs/audits/phase42n3c_source_order_writer_migration.md
?? docs/audits/phase42n3d_fixed_form_row_static_audit.json
?? docs/audits/phase42n3d_fixed_form_row_static_audit_classified.json
?? docs/audits/phase42n3d_source_order_requirement_verify.json
?? packaging/mp2027_portable_entry.py
?? "raw/requirements/C\341\272\243i ti\341\272\277n nh\341\272\255p d\341\273\257 li\341\273\207u chung v\303\240o file MPnew 09.06.2026.xlsx"
?? "reference_outputs/secondary/FY2027/01.KDTVN \346\251\237\345\231\250\350\243\275\351\200\2401\350\252\262\343\200\200_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/02.KDTVN \346\251\237\345\231\250\350\243\275\351\200\240\357\274\222\350\252\262\343\200\200_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/03.KDTVN \346\251\237\345\231\250\350\243\275\351\200\240\347\256\241\347\220\206\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/04.KDTVN \343\203\210\343\203\212\343\203\274\350\243\275\351\200\240\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/05.KDTVN \343\203\210\343\203\212\343\203\274\347\224\237\347\224\243\346\212\200\350\241\223\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/06.KDTVN \343\203\210\343\203\212\343\203\274\345\223\201\350\263\252\347\256\241\347\220\206\350\252\262\343\200\200_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/07.KDTVN MD1\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/08.KDTVN MD2\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/09.KDTVN \345\267\245\347\250\213\345\223\201\350\263\252\347\256\241\347\220\2061\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/10.KDTVN \347\224\237\347\224\243\347\256\241\347\220\206\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/11.KDTVN \346\216\241\347\256\227\347\256\241\347\220\206\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/12.KDTVN \343\203\236\343\202\271\343\202\277\343\203\274\347\256\241\347\220\206\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/13.KDTVN \351\203\250\345\223\201\347\256\241\347\220\2061\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/14.KDTVN \343\203\241\343\202\253\350\243\275\351\200\240\346\212\200\350\241\2231\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/15.KDTVN \343\203\241\343\202\253\350\243\275\351\200\240\346\212\200\350\241\2232\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/16.KDTVN \351\233\273\346\260\227\350\243\275\351\200\240\346\212\200\350\241\223\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/18.KDTVN \351\203\250\345\223\201\346\244\234\346\237\2731\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01-OK).xlsx"
?? "reference_outputs/secondary/FY2027/20.KDTVN \351\203\250\345\223\201\346\212\200\350\241\223\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/22.KDTVN \351\207\221\345\236\213\346\212\200\350\241\223\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/23.KDTVN \351\203\250\345\223\201\350\243\275\351\200\240\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/24.KDTVN \345\223\201\350\263\252\344\277\235\350\250\274\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/25.KDTVN \350\243\275\345\223\201\344\277\235\350\250\274\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/26.KDTVN \347\254\2541\350\263\207\346\235\220\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/27.KDTVN \347\254\2542\350\263\207\346\235\220\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/28.KDTVN \347\254\2543\350\263\207\346\235\220\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/29.KDTVN \350\263\207\346\235\220\347\256\241\347\220\206\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/30.KDTVN \347\267\217\345\213\231\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/31.KDTVN \344\272\272\344\272\213\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/32.KDTVN \346\226\275\350\250\255\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/33.KDTVN \344\274\232\350\250\210\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/34.KDTVN \347\265\214\345\226\266\347\256\241\347\220\206\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/35.KDTVN \350\262\277\346\230\223\347\256\241\347\220\206\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232 final.xlsx"
?? "reference_outputs/secondary/FY2027/36.KDTVN \346\203\205\345\240\261\343\202\267\343\202\271\343\203\206\343\203\240\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver03).xlsx"
?? "reference_outputs/secondary/FY2027/38.KDTVN \343\203\210\343\203\212\343\203\274\350\243\275\351\200\240\347\256\241\347\220\206\350\252\262\343\200\200_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/39.KDTVN RPS\350\243\275\351\200\240\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/40.KDTVN \351\203\250\345\223\201\345\223\201\350\263\252\347\256\241\347\220\2061\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/42.KDTVN \347\224\237\347\224\243\346\212\200\350\241\2231\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/43.KDTVN \347\224\237\347\224\243\346\212\200\350\241\2232\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/44.KDTVN \347\254\2544\350\263\207\346\235\220\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/45.KDTVN \350\243\275\345\223\201\347\256\241\347\220\206\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/46.KDTVN \347\211\251\346\265\201\347\256\241\347\220\206\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/47.KDTVN \345\267\245\347\250\213\345\223\201\350\263\252\347\256\241\347\220\2062\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/49.KDTVN EI1\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/50.KDTVN ESD1\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/51.KDTVN \345\212\264\345\203\215\347\265\204\345\220\210_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/52.KDTVN \346\251\237\345\231\250\350\243\275\351\200\240\357\274\223\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/53.KDTVN MD3\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/54.KDTVN \347\224\237\347\224\243\346\212\200\350\241\2233\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/55.KDTVN \351\203\250\345\223\201\350\243\275\351\200\240\347\256\241\347\220\206\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/56.KDTVN \345\223\201\350\263\252\347\256\241\347\220\206\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/58.KDTVN \344\277\235\345\256\211\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/59.KDTVN \351\203\250\345\223\201\346\244\234\346\237\2732\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/60.KDTVN \343\203\252\343\202\271\343\202\257\343\203\236\343\203\215\343\202\270\343\203\241\343\203\263\343\203\210\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01) 1 1.xlsx"
?? "reference_outputs/secondary/FY2027/61.KDTVN \351\203\250\345\223\201\345\234\250\345\272\253\347\256\241\347\220\206\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/63.KDTVN ESD2\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/64.KDTVN \351\233\273\345\267\245\350\243\275\351\200\240\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/65.KDTVN MD4\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/66.KDTVN EI2\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/68.KDTVN MD5\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/69.KDTVN \351\203\250\345\223\201\347\256\241\347\220\2062\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/70.KDTVN \345\267\245\347\250\213\345\223\201\350\263\252\347\256\241\347\220\2063\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/71.KDTVN \345\267\245\347\250\213\345\223\201\350\263\252\347\256\241\347\220\2064\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/72.KDTVN \350\243\275\351\200\240\343\202\267\343\202\271\343\203\206\343\203\240\351\226\213\347\231\272\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/73.KDTVN \350\243\275\351\200\240\346\212\200\350\241\223\347\256\241\347\220\206\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/74.KDTVN \351\203\250\345\223\201\345\223\201\350\263\252\347\256\241\347\220\2062\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/MP data/Copy of \345\240\261\345\221\212\343\203\207\343\203\274\343\202\277.xlsx"
?? "reference_outputs/secondary/FY2027/MP data/DL chung/\343\202\267\343\202\271\343\203\206\343\203\240\350\252\262\351\207\221\351\207\221\351\241\215(Simulation)_FY2027_Apr.2026 ~ June.2026.xls"
?? "reference_outputs/secondary/FY2027/MP data/DL chung/\343\202\267\343\202\271\343\203\206\343\203\240\350\252\262\351\207\221\351\207\221\351\241\215(Simulation)_FY2027_Jan.2027 ~ March.2027(Change SAP price).xls"
?? "reference_outputs/secondary/FY2027/MP data/DL chung/\343\202\267\343\202\271\343\203\206\343\203\240\350\252\262\351\207\221\351\207\221\351\241\215(Simulation)_FY2027_July.2026 ~ Dec.2026(Change AMS & PLM price).xls"
?? "reference_outputs/secondary/FY2027/MP data/DL chung/\345\233\272\345\256\232\350\263\207\347\224\243\346\203\205\345\240\261_Fixed_Assets_Information_2025.11 - Nov.xlsx"
?? "reference_outputs/secondary/FY2027/MP data/DL chung/\346\226\275\350\250\255\350\252\262\343\200\200MPFY2027.xlsx"
?? "reference_outputs/secondary/FY2027/MP data/DL chung/\347\267\217\345\213\231\350\252\262 FY2027 MP \346\214\257\346\233\277\344\272\210\345\256\232.xlsx"
?? "reference_outputs/secondary/FY2027/MP data/D\341\273\261 t\303\255nh chi ph\303\255 l\303\240m gi\341\272\245y t\341\273\235 cho NNN FY2027.xlsx"
?? "reference_outputs/secondary/FY2027/MP data/FW_ M365 copilot\346\264\273\347\224\250\343\201\253\343\201\244\343\201\204\343\201\246.msg"
?? "reference_outputs/secondary/FY2027/MP data/FY2026\347\265\214\350\262\273.xlsx"
?? "reference_outputs/secondary/FY2027/MP data/FY2027\345\233\272\345\256\232\350\263\207\347\224\243\350\250\210\347\224\273.xlsx"
?? "reference_outputs/secondary/FY2027/MP data/MP\343\201\256\343\203\207\343\203\274\343\202\277 2027.xlsx"
?? "reference_outputs/secondary/FY2027/MP data/RE_ \343\200\220\346\235\245\346\234\237MP\343\201\256\343\201\224\351\200\243\347\265\241\343\200\221FY2027 VPS\343\203\251\343\202\244\343\202\273\343\203\263\343\202\271\344\277\235\345\256\210\343\203\273COLMINA\347\265\214\350\262\273\343\201\253\343\201\244\343\201\204\343\201\246.msg"
?? "reference_outputs/secondary/FY2027/MP data/file check time&\344\272\272.xlsx"
?? "reference_outputs/secondary/FY2027/MP data/file check.xlsx"
?? "reference_outputs/secondary/FY2027/MP data/old/\345\240\261\345\221\212\343\203\207\343\203\274\343\202\277.xlsx"
?? "reference_outputs/secondary/FY2027/old/\343\203\241\343\202\2532/15.KDTVN \343\203\241\343\202\253\350\243\275\351\200\240\346\212\200\350\241\2232\350\252\262_FY2027\343\203\236\343\202\271\343\202\277\343\203\274\343\203\227\343\203\251\343\203\263\344\272\272\345\223\241\343\203\273\346\231\202\351\226\223\350\250\210\347\224\273\350\241\250(Ver01)old.xls"
?? "reference_outputs/secondary/FY2027/old/\343\203\241\343\202\2532/15.KDTVN \343\203\241\343\202\253\350\243\275\351\200\240\346\212\200\350\241\2232\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/old/\343\203\241\343\202\2532/mail check/RE_ VPS\343\203\215\343\203\203\343\203\210\343\203\257\343\203\274\343\202\257\343\202\244\343\203\263\343\203\225\343\203\251.msg"
?? "reference_outputs/secondary/FY2027/old/\343\203\241\343\202\2532/mail check/RE_ \343\200\220\346\235\245\346\234\237MP\343\201\256\343\201\224\351\200\243\347\265\241\343\200\221FY2027 VPS\343\203\251\343\202\244\343\202\273\343\203\263\343\202\271\344\277\235\345\256\210\343\203\273COLMINA\347\265\214\350\262\273\343\201\253\343\201\244\343\201\204\343\201\246.msg"
?? "reference_outputs/secondary/FY2027/\343\203\241\343\202\2532/15.KDTVN \343\203\241\343\202\253\350\243\275\351\200\240\346\212\200\350\241\2232\350\252\262_FY2027\343\203\236\343\202\271\343\202\277\343\203\274\343\203\227\343\203\251\343\203\263\344\272\272\345\223\241\343\203\273\346\231\202\351\226\223\350\250\210\347\224\273\350\241\250(Ver01).xls"
?? "reference_outputs/secondary/FY2027/\343\203\241\343\202\2532/15.KDTVN \343\203\241\343\202\253\350\243\275\351\200\240\346\212\200\350\241\2232\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/\343\203\241\343\202\253\357\274\221/14.KDTVN \343\203\241\343\202\253\350\243\275\351\200\240\346\212\200\350\241\2231\350\252\262_FY2027\343\203\236\343\202\271\343\202\277\343\203\274\343\203\227\343\203\251\343\203\263\344\272\272\345\223\241\343\203\273\346\231\202\351\226\223\350\250\210\347\224\273\350\241\250(Ver01).xls"
?? "reference_outputs/secondary/FY2027/\343\203\241\343\202\253\357\274\221/14.KDTVN \343\203\241\343\202\253\350\243\275\351\200\240\346\212\200\350\241\2231\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/\347\256\241\347\220\206\350\252\262/73.KDTVN \350\243\275\351\200\240\346\212\200\350\241\223\347\256\241\347\220\206\350\252\262_FY2027\343\203\236\343\202\271\343\202\277\343\203\274\343\203\227\343\203\251\343\203\263\344\272\272\345\223\241\343\203\273\346\231\202\351\226\223\350\250\210\347\224\273\350\241\250(Ver01).xls"
?? "reference_outputs/secondary/FY2027/\347\256\241\347\220\206\350\252\262/73.KDTVN \350\243\275\351\200\240\346\212\200\350\241\223\347\256\241\347\220\206\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/\350\243\275\351\200\240\343\202\267\343\202\271\343\203\206\343\203\240\351\226\213\347\231\272\350\252\262/72.KDTVN \350\243\275\351\200\240\343\202\267\343\202\271\343\203\206\343\203\240\351\226\213\347\231\272\350\252\262_FY2027\343\203\236\343\202\271\343\202\277\343\203\274\343\203\227\343\203\251\343\203\263\344\272\272\345\223\241\343\203\273\346\231\202\351\226\223\350\250\210\347\224\273\350\241\250(Ver01).xls"
?? "reference_outputs/secondary/FY2027/\350\243\275\351\200\240\343\202\267\343\202\271\343\203\206\343\203\240\351\226\213\347\231\272\350\252\262/72.KDTVN \350\243\275\351\200\240\343\202\267\343\202\271\343\203\206\343\203\240\351\226\213\347\231\272\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? "reference_outputs/secondary/FY2027/\351\233\273\346\260\227/16.KDTVN \351\233\273\346\260\227\350\243\275\351\200\240\346\212\200\350\241\223\350\252\262_FY2027\343\203\236\343\202\271\343\202\277\343\203\274\343\203\227\343\203\251\343\203\263\344\272\272\345\223\241\343\203\273\346\231\202\351\226\223\350\250\210\347\224\273\350\241\250(Ver01).xls"
?? "reference_outputs/secondary/FY2027/\351\233\273\346\260\227/16.KDTVN \351\233\273\346\260\227\350\243\275\351\200\240\346\212\200\350\241\223\350\252\262_MP FY2027_\345\220\204\344\272\210\345\256\232(Ver01).xlsx"
?? src/engine/complete_v1_source_order_writer.py
?? src/engine/source_order_output.py
?? tests/test_complete_v1_source_order_writer.py
?? tests/test_source_order_output.py
?? tools/verify_system_cost.py

```

## Non-Tech Conclusion

Yeu cau moi da duoc verify theo dung nghiep vu hien tai: ket qua complete-v1 duoc trinh bay theo block file nguon, theo dung thu tu 7 file, giua cac block co dong trong. Cac dong FORM cu nhu 38/42/58/59/97/98/137 khong con la vi tri xuat du lieu nghiep vu trong output da audit.

## Final Classification

`PASS_PHASE_42N3D_SOURCE_FILE_ORDER_REQUIREMENT_VERIFIED`
