# MP2027 Manager - Task Checklist

## Phase 0: Environment Setup
- [x] Install dependencies (openpyxl, pandas, xlrd)
- [x] Create project folder structure

## Phase 1: Database Schema & Master Data
- [x] Create SQLite database with 6 tables → [data/mp2027.db](file:///c:/ProgramData/Sandbox/MP2027/data/mp2027.db)
- [x] Load dim_cost_centers → **62 records** (製造, 一般, 販売)
- [x] Load dim_accounts → **239 records** (with mfg/ga/sales codes)
- [x] Load map_allocation_rules → **50 rules**
- [x] Set exchange rate dynamic from FORM.xlsx B2

## Phase 2: Excel Parser (Refactor)
- [x] Read BRD file → 5 sheets, confirms Staff/Worker split & Final Month logic
- [ ] Refactor Fixed Assets Parser: Add 'Last Depreciation Month' support
- [ ] Refactor GA Parser: Add Unit prices (Gas, VPN) from BRD
- [ ] Refactor IT Simulation: Handle periods & exchange rates

## Phase 3: Allocation Engine (Refactor Required)
- [ ] Implement logic: if current_month > last_depreciation_month then amount = 0
- [ ] Implement dynamic FX rate from Hub ô B2
- [ ] Implement monthly headcount variance
- [ ] Account code selection by CC type (製造/一般/販売)

## Phase 4: Hub Builder (内訳ﾘｽﾄ Generator)
- [ ] Write hub data to 内訳ﾘｽﾄ(4～3月) sheet
- [ ] Preserve existing formulas and formatting

## Phase 5: Validation & Testing
- [ ] Unit Test: 1 asset ending Oct 2026 must be 0 in Nov 2026.
- [ ] Integration Test: End-to-end with dynamic FX rate.
