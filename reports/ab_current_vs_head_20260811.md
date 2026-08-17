# A/B validation: current worktree vs HEAD

Date: 2026-08-11  
Baseline commit: `4fa2f7f7c2144d3a274a768dca6f474b4b661c45`  
Random seed: `20260811`

## Runtime configuration

- Fiscal year: 2027
- Exchange rate: 26,273 USD/VND
- FORM: `C:\Users\tvn183660\AppData\Local\MPManager\Projects\MP2027\docs\MP2027\FORM.xlsx`
- Cost source: `D:\Sandbox\MP2027\docs\MP2027`
- Headcount/time source: `D:\Sandbox\MP2027\raw\FY2027`
- Both branches used independent copies of the same operational and manual-input databases.
- Because only CC 1412000036 had an approved March-2026 manual baseline, the isolated diagnostic runs used the application's audited `simulate_baseline_t3_from_t4` option for missing baselines. The option and inputs were identical on both branches.

## Five randomly selected cost centers

A business row means a row from 38 onward with an account, monthly payload, description, or WBS value. Rows were aligned by account + description + duplicate occurrence before formulas and values were compared, so row movement was not misreported as a financial difference.

| Cost center | HEAD rows | Current rows | Added | Removed | Changed formula/value | Moved | Fixed B31:D36 cells |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1412000008 | 26 | 26 | 0 | 0 | 0 | 23 | 18 |
| 1412000026 | 26 | 26 | 0 | 0 | 0 | 23 | 18 |
| 1412000078 | 41 | 41 | 0 | 0 | 0 | 40 | 18 |
| 1412000036 | 42 | 42 | 0 | 0 | 0 | 41 | 18 |
| 1412000073 | 41 | 41 | 0 | 0 | 0 | 40 | 18 |
| **Total** | **176** | **176** | **0** | **0** | **0** | **167** | **90** |

All non-detail-sheet cell differences were confined to `_mp2027_source_order_meta`, which records the changed source-row order. No business data on the other sheets changed.

## Requirement checks

- Welfare ordering: all five outputs follow the requested April-to-March business sequence.
- New-hire grouping: all five pass the order/contiguity check. CCs 1412000078, 1412000036, and 1412000073 contain the full block.
- The A/B run exposed that real output uses two descriptions, `フィロソフィ手帳1` and `フィロソフィ手帳2`, while the earlier test used a combined description. Recognition and regression coverage were corrected; the final real order is uniform, recruitment health, philosophy 1, philosophy 2, time card/photo, notebook, pen, holder/lanyard, pocket calendar.
- FORM contract: all current outputs restore the 18 cells in B31:D36, use automatic/full recalculation, and retain valid profit lookup keys.
- Travel targeted check, CC 1412000035: HEAD used `=28*2061000` (May headcount); current uses `=26*2061000` (April headcount). Row count remains 39 on both sides.
- Hat targeted check, CC 1412000019: HEAD emitted color hat `=1*39000*2`; current emits white hat `=1*33500*2` for the observed staff new hire. Row count remains 39 on both sides.
- Valid FORM confirmation behavior remains covered by automated regression tests; it does not alter workbook data.

## Regression result

Final verification: **29 Complete-v1 writer tests passed**, followed by
**141 related regression tests and 3 subtests passed**. Aggregate: **170 tests
passed, 3 subtests passed**.

Evidence directories:

- Random A/B: `D:\Sandbox\MP2027_AB_GUI_20260811_1800`
- Targeted A/B: `D:\Sandbox\MP2027_AB_TARGETED_20260811_1810`
