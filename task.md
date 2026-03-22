# MP2027 Manager - Task Checklist

## Phase 0: Environment Setup
- [x] ~~Install Python 3.12~~ → Found Python 3.13.5 via [py](file:///C:/ProgramData/Sandbox/MP2027/analyze_mp.py)
- [x] Install dependencies (openpyxl, pandas, xlrd)
- [x] Create project folder structure

## Phase 1: Database Schema & Master Data
- [x] Create SQLite database with 6 tables → [data/mp2027.db](file:///c:/ProgramData/Sandbox/MP2027/data/mp2027.db)
- [x] Load `dim_cost_centers` → **62 records** (製造, 部内間接, 部外間接)
- [x] Load `dim_accounts` → **239 records** (with mfg/ga/sales codes)
- [x] Load `map_allocation_rules` → **50 rules** (34 HC_all, 11 HC_worker, 4 WD, 1 HC_staff)
- [x] Set [sys_params](file:///C:/ProgramData/Sandbox/MP2027/src/db/schema.py#134-155) → rate=25,450, FY2027 (202604→202703)

## Phase 2: Excel Parser (Import)
- [x] Read BRD file → 5 sheets, confirms Staff/Worker split
- [ ] Parse Facility data (施設課 MPFY2027.xlsx → B&L, E&W)
- [ ] Parse GA data (総務課 FY2027 MP 振替予定.xlsx)
- [ ] Parse IT Simulation data (3 xls files for 3 periods)
- [ ] Parse Fixed Assets data (固定資産情報)

## Phase 3: Allocation Engine
- [ ] Implement allocation by Headcount (Staff vs Worker)
- [ ] Implement allocation by Working Days
- [ ] Implement allocation by Fixed Ratio
- [ ] Step-down allocation (2-step)
- [ ] Account code selection by CC type (製造/間接/販売)

## Phase 4: Hub Builder (内訳ﾘｽﾄ Generator)
- [ ] Map database records to 内訳ﾘｽﾄ cell structure
- [ ] Handle 12-month columns (T4→T3)
- [ ] Generate hub data for all cost categories

## Phase 5: Report Generator (Export to FORM.xlsx)
- [ ] Write hub data to 内訳ﾘｽﾄ(4～3月) sheet
- [ ] Preserve existing formulas and formatting
- [ ] Verify 採算表(VND) auto-calculates correctly
- [ ] Verify 採算表(USD) auto-converts correctly

## Phase 6: Validation & Testing
- [ ] Compare output with original FORM.xlsx values
- [ ] Validate allocation calculations
- [ ] Validate USD/VND conversion
- [ ] End-to-end test with all source files
