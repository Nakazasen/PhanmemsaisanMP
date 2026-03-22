# MP2027 Manager — Implementation Plan

## Goal

Xây dựng công cụ Python tự động hóa lập kế hoạch tài chính FY2027, thay thế quy trình nhập tay vào file FORM.xlsx. Hệ thống theo mô hình **Hub-centric**: đổ dữ liệu vào sheet `内訳ﾘｽﾄ(4～3月)` (Hub), các sheet báo cáo (採算表 VND/USD) sẽ tự tính nhờ công thức Excel có sẵn.

## User Review Required

> [!IMPORTANT]
> **Python chưa được cài đặt trên máy.** Mọi nỗ lực cài tự động (winget, choco, direct download) đều thất bại. Bạn cần cài Python 3.12 trước khi tiến hành. Cách đơn giản nhất: tải từ https://www.python.org/downloads/ và chạy installer.

> [!WARNING]
> **File BRD `Cải tiến nhập dữ liệu chung vào file MP.xlsx`** (916KB) chưa được đọc vì không có Python. Sau khi cài Python, tôi sẽ đọc file này đầu tiên để xác nhận logic chi tiết trước khi coding.

---

## Proposed Changes

### Project Structure

#### [NEW] [project layout](file:///C:/ProgramData/Sandbox/MP2027/src)
```
C:\ProgramData\Sandbox\MP2027\
├── src\
│   ├── __init__.py
│   ├── main.py              # Entry point + CLI
│   ├── db\
│   │   ├── __init__.py
│   │   ├── schema.py        # SQLite schema creation
│   │   └── loader.py        # Master data loading
│   ├── parsers\
│   │   ├── __init__.py
│   │   ├── facility.py      # 施設課 parser (B&L, E&W)
│   │   ├── ga.py            # 総務課 parser (bus, gas, cleaning)
│   │   ├── it_sim.py        # IT Simulation parser (SAP, PLM, AMS)
│   │   └── fixed_assets.py  # 固定資産 parser
│   ├── engine\
│   │   ├── __init__.py
│   │   ├── allocation.py    # Allocation engine (3 drivers + step-down)
│   │   └── currency.py      # USD/VND conversion (ROUNDDOWN/ROUNDUP)
│   ├── export\
│   │   ├── __init__.py
│   │   └── form_writer.py   # Write to FORM.xlsx 内訳ﾘｽﾄ sheet
│   └── utils\
│       ├── __init__.py
│       └── excel_helpers.py  # Common Excel reading utilities
├── tests\
│   ├── test_allocation.py
│   ├── test_currency.py
│   └── test_integration.py
├── data\
│   └── mp2027.db            # SQLite database (generated)
└── requirements.txt
```

---

### Component 1: Database Schema & Master Data

#### [NEW] [schema.py](file:///C:/ProgramData/Sandbox/MP2027/src/db/schema.py)

6 tables (1 table added vs original spec):

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `dim_cost_centers` | Cost Center master | `code`, `name_jp`, `name_vn`, `expense_type`, **`staff_count`**, **`worker_count`** |
| `dim_accounts` | Account master | `code`, `name_jp`, `name_vn`, `group_name`, `mfg_code`, `ga_code`, `sales_code` |
| `map_allocation_rules` | Allocation rules | `source_dept`, `item_name`, `account_name`, `mfg_code`, `ga_code`, `sales_code`, `posting_month`, `unit_price`, `unit`, `driver_type` |
| `fact_input_data` | Input data hub | `source`, `period` (YYYYMM), `amount_vnd`, `cc_code`, `account_code`, `scenario_id` |
| `fact_allocation_log` | Audit trail | `rule_id`, `dest_cc`, `period`, `amount_vnd`, `driver_value`, `driver_total` |
| `sys_params` | System config | `key`, `value` (exchange_rate, fiscal_year) |

Key design decisions:
- `dim_accounts` has **3 separate code columns** (`mfg_code`, `ga_code`, `sales_code`) matching the 3 account codes per allocation rule
- `dim_cost_centers` has separate `staff_count` and `worker_count` columns per user requirement
- `fact_allocation_log` preserves intermediate calculations for audit trail

#### [NEW] [loader.py](file:///C:/ProgramData/Sandbox/MP2027/src/db/loader.py)

Load master data from:
- [FORM.xlsx](file:///C:/ProgramData/Sandbox/MP2027/FORM.xlsx) → sheet `原価センタ` (cost centers), sheet `勘定科目` (accounts)
- `FY2027配賦額一覧 (2025.12.29).xlsx` → allocation rules
- Headcount data (staff/worker split, source TBD after reading BRD)

---

### Component 2: Excel Parsers

#### [NEW] [facility.py](file:///C:/ProgramData/Sandbox/MP2027/src/parsers/facility.py)
- Parse `施設課 MPFY2027.xlsx` → depreciation, interest (B&L data), electricity & water (E&W data)
- Map each entry to [(cc_code, account_code, period, amount_vnd)](file:///C:/ProgramData/Sandbox/MP2027/analyze_mp.py#5-31)

#### [NEW] [ga.py](file:///C:/ProgramData/Sandbox/MP2027/src/parsers/ga.py)
- Parse `総務課 FY2027 MP 振替予定.xlsx` → bus, gas, cleaning, recruitment costs
- Handle working days × unit price calculations

#### [NEW] [it_sim.py](file:///C:/ProgramData/Sandbox/MP2027/src/parsers/it_sim.py)
- Parse 3 IT Simulation [.xls](file:///C:/ProgramData/Sandbox/MP2027/%E3%82%B7%E3%82%B9%E3%83%86%E3%83%A0%E8%AA%B2%E9%87%91%E9%87%91%E9%A1%8D%28Simulation%29_FY2027_Apr.2026%20~%20June.2026.xls) files (different price periods)
- Handle USD→VND conversion for SAP/PLM/AMS fees
- Merge 3 files into 12 months of data

#### [NEW] [fixed_assets.py](file:///C:/ProgramData/Sandbox/MP2027/src/parsers/fixed_assets.py)
- Parse `固定資産情報_Fixed_Assets_Information_2025.11.xlsx` → depreciation schedules

---

### Component 3: Allocation Engine

#### [NEW] [allocation.py](file:///C:/ProgramData/Sandbox/MP2027/src/engine/allocation.py)

Implements the allocation formula:
```
Amount = Unit_Price × Driver_Value
```

Where `Driver_Value` depends on `driver_type`:
- `headcount_all` → `staff_count + worker_count`
- `headcount_worker` → `worker_count` only (G7社員)
- `headcount_staff` → `staff_count` only (スタッフ)
- `working_days` → from sys_params or department input
- `fixed_ratio` → from allocation rules

Account code selection:
```python
if dest_cc.expense_type == '製造':
    code = rule.mfg_code
elif dest_cc.expense_type in ('部内間接', '部外間接'):
    code = rule.ga_code
elif dest_cc.expense_type == '販売':
    code = rule.sales_code
```

Step-down allocation: Phase 1 allocates to indirect CCs, Phase 2 re-allocates indirect costs to production CCs.

#### [NEW] [currency.py](file:///C:/ProgramData/Sandbox/MP2027/src/engine/currency.py)

```python
from decimal import Decimal, ROUND_DOWN, ROUND_UP

def vnd_to_usd_revenue(vnd: int, rate: Decimal) -> Decimal:
    """ROUNDDOWN(vnd / rate, 2) — conservative on revenue"""
    return (Decimal(vnd) / rate).quantize(Decimal('0.01'), rounding=ROUND_DOWN)

def vnd_to_usd_expense(vnd: int, rate: Decimal) -> Decimal:
    """ROUNDUP(vnd / rate, 2) — conservative on expenses"""
    return (Decimal(vnd) / rate).quantize(Decimal('0.01'), rounding=ROUND_UP)
```

---

### Component 4: Hub Builder & Report Generator

#### [NEW] [form_writer.py](file:///C:/ProgramData/Sandbox/MP2027/src/export/form_writer.py)

- Open [FORM.xlsx](file:///C:/ProgramData/Sandbox/MP2027/FORM.xlsx) with `openpyxl` (preserving formulas)
- Write computed data to `内訳ﾘｽﾄ(4～3月)` sheet, rows 26+ onwards
- Map: Column B = account code, Column D = lookup key, Columns F-Q = months (Apr-Mar)
- **Critical**: use `openpyxl` with `data_only=False` to preserve all formulas in other sheets
- Save as new file (never overwrite original FORM.xlsx)

---

## Verification Plan

### Automated Tests

1. **Unit test: Allocation math** (`tests/test_allocation.py`)
   ```
   Command: python -m pytest tests/test_allocation.py -v
   ```
   - Test headcount_all allocation: 58,000 VND/card × 5 people = 290,000 VND
   - Test headcount_worker vs staff split: sổ 4,000 for worker, 9,100 for staff
   - Test account code selection based on CC expense_type
   - Test step-down allocation (2 phases)

2. **Unit test: Currency conversion** (`tests/test_currency.py`)
   ```
   Command: python -m pytest tests/test_currency.py -v
   ```
   - Test ROUNDDOWN for revenue (VND 25,450,000 / 25,450 = 1,000.00 USD)
   - Test ROUNDUP for expenses
   - Test edge cases with Decimal precision

3. **Integration test: End-to-end** (`tests/test_integration.py`)
   ```
   Command: python -m pytest tests/test_integration.py -v
   ```
   - Load master data → parse sample input → run allocation → export to FORM.xlsx copy
   - Open exported file and verify 内訳ﾘｽﾄ has correct values
   - Verify 採算表(VND) formulas resolve correctly

### Manual Verification

1. **Open exported FORM.xlsx in Excel** and confirm:
   - 内訳ﾘｽﾄ(4～3月) sheet has correct data in rows 26+
   - 採算表(VND) shows correct totals (SUMIF working)
   - 採算表(USD) shows correct converted values
   - No broken formulas or formatting

2. **Compare specific values** between exported file and original source files to validate data flow
