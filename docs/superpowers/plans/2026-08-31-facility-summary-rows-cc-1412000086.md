# Facility Summary-Row Exclusion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent facility workbook subtotal/total rows from being attributed to the last real Cost Center, while retaining every valid cost-center amount for depreciation, interest, electricity, and water.

**Architecture:** `parse_facility_sheet()` will derive a Cost Center from the current row itself, or—only for a numbered department-name row—from the immediate next row. Rows such as `合計` have neither form of Cost Center evidence and will be skipped instead of inheriting stale parser state. The change ends at normalized `fact_input_data`; `AllocationEngine`, account resolution, and `HubBuilder` keep consuming the same valid records and formulas.

**Tech Stack:** Python 3.13, pandas, SQLite, openpyxl, pytest.

---

### Task 1: Lock down the parser regression

**Files:**
- Modify: `tests/test_headcount_and_export.py`
- Verify: `docs/MP2027/施設課　MPFY2027.xlsx`

- [X] **Step 1: Add a focused failing parser test for each of the three facility sheets.**

Add `pandas`, `SHEET_CONFIG`, and `parse_facility_sheet` imports. Create `TestFacilityParserSummaryRows` with this test shape:

```python
def test_summary_rows_do_not_inherit_the_last_cost_center(self):
    fy_months = get_fy_months(2027)
    for config in SHEET_CONFIG.values():
        first_label, first_key = next(iter(config["items"].items()))
        second_label, second_key = tuple(config["items"].items())[1]
        rows = [[None] * 15 for _ in range(config["data_start"])] + [
            [63, "Information System", first_label] + [11.0] * 12,
            [None, 1412000086, second_label] + [22.0] * 12,
            ["合計", None, first_label] + [999.0] * 12,
            [None, None, second_label] + [888.0] * 12,
        ]
        records = parse_facility_sheet(pd.DataFrame(rows), config, fy_months)
        self.assertEqual(len(records), 24)
        self.assertEqual(
            {(row["item_type"], row["amount"]) for row in records},
            {(first_key, 11.0), (second_key, 22.0)},
        )
        self.assertEqual({row["cc_code"] for row in records}, {1412000086})
```

- [X] **Step 2: Run the new test before implementation.**

Run: `py -3 -m pytest tests/test_headcount_and_export.py::TestFacilityParserSummaryRows::test_summary_rows_do_not_inherit_the_last_cost_center -q`

Expected: FAIL because the current parser emits the `999.0` and `888.0` summary amounts using the previous Cost Center.

### Task 2: Make the smallest parser-only correction

**Files:**
- Modify: `src/parsers/facility.py:56-117`
- Test: `tests/test_headcount_and_export.py::TestFacilityParserSummaryRows`

- [X] **Step 1: Replace persistent Cost Center inheritance with per-row resolution.**

Use a local helper inside `parse_facility_sheet()` that accepts the current row and its index. It must return `extract_cc_code(row.iloc[cc_code_col])` when present. If column A is numeric, it may read `extract_cc_code(df.iloc[i + 1].iloc[cc_code_col])`; otherwise it must return `None`. Do not retain `current_cc` across rows.

```python
def _row_cc_code(row: pd.Series, row_index: int) -> int | None:
    direct_code = extract_cc_code(row.iloc[config["cc_code_col"]])
    if direct_code:
        return direct_code
    sequence = row.iloc[0]
    try:
        float(sequence)
    except (TypeError, ValueError):
        return None
    if row_index + 1 >= len(df):
        return None
    return extract_cc_code(df.iloc[row_index + 1].iloc[config["cc_code_col"]])
```

Call it after recognizing an allowed item label and skip that row when it returns `None`. Keep all currency conversion, fiscal-period mapping, and database insert code unchanged.

- [X] **Step 2: Run the focused regression after implementation.**

Run: `py -3 -m pytest tests/test_headcount_and_export.py::TestFacilityParserSummaryRows -q`

Expected: PASS; exactly the two real rows per sheet are imported and all summary rows are absent.

### Task 3: Verify actual workbook behavior and non-regression boundaries

**Files:**
- Verify: `docs/MP2027/施設課　MPFY2027.xlsx`
- Verify: `src/parsers/facility.py`
- Verify: `src/engine/hub_builder.py:1376-1560`

- [X] **Step 1: Parse the production facility workbook into an in-memory SQLite schema.**

Run a read-only-source diagnostic which calls `parse_facility()` against `:memory:` with FY2027 and exchange rate `26273`, then group CC `1412000086` by `description` and period. Verify April values are exactly `491.26`, `33.16`, `315.77`, `40.04` USD and `2,227,240`, `382,540` VND—with no `324,649.60`, `21,912.57`, `208,679.16`, `26,458.43`, `2,389,607,989`, or `168,200,000` summary values.

- [X] **Step 2: Run export regression coverage.**

Run: `py -3 -m pytest tests/test_headcount_and_export.py::TestHubBuilderExport::test_fixed_rows_follow_mp2027_form_layout tests/test_headcount_and_export.py::TestHubBuilderExport::test_fixed_rows_resolve_facility_accounts_for_general_cost_center -q`

Expected: PASS. The change does not alter FORM row placement, FX formulas, or manufacturing/general account resolution.

- [X] **Step 3: Audit the patch.**

Run: `py -3 -m py_compile src/parsers/facility.py tests/test_headcount_and_export.py` and `git diff --check`.

Expected: both commands succeed. Review the diff to confirm it modifies only the parser, its test import/test class, and this plan; it must not alter `mp2027.db`, allocation rules, or templates.
