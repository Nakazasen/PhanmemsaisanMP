# Output Cost Row Ordering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users save a full cost-row order in an MP output workbook without losing the distinction between calculated common costs and manually entered costs.

**Architecture:** A new isolated workbook engine owns hidden row-level layout metadata, snapshot/restore, and FY inheritance transforms. The pipeline calculates common rows as before, then uses the engine to merge them with prior manual rows in the saved global order. The Tkinter UI invokes the engine; it does not contain workbook rules.

**Tech Stack:** Python 3.13, openpyxl, Tkinter/ttk, pytest.

---

## File structure

- Create `src/engine/output_cost_row_ordering.py`: row identity, hidden metadata, snapshot and restore APIs.
- Modify `src/engine/manual_special_cost_sections.py`: legacy section compatibility and FY copy rules.
- Modify `scripts/run_e2e.py`: pass source kind and log final layout result.
- Modify `src/services/i18n.py`: Vietnamese, English, Japanese labels/messages.
- Modify `src/universal_app.py`: optional chooser and ordering dialog.
- Create `tests/test_output_cost_row_ordering.py`: real-workbook engine acceptance tests.
- Modify `tests/test_manual_special_cost_sections.py` and `tests/test_gui_cost_center_and_output_actions.py`.

### Task 1: Define hidden row layout metadata

**Files:**

- Create: `tests/test_output_cost_row_ordering.py`
- Create: `src/engine/output_cost_row_ordering.py`

- [ ] **Step 1: Write the failing test**

```python
def test_save_order_marks_legacy_manual_rows_and_keeps_mixed_order(tmp_path):
    workbook = _workbook_with_common_rows(tmp_path / "MP_CC_1412000030.xlsx")
    _add_legacy_manual_rows(workbook, 87)
    mark_legacy_manual_section(workbook, "1412000030", 87)

    save_cost_row_order(workbook, "1412000030", ["common:38", "manual:87", "common:39", "manual:88"])

    assert read_layout_kinds(workbook) == ["common", "manual", "common", "manual"]
```

- [ ] **Step 2: Verify RED**

Run `py -3 -m pytest tests/test_output_cost_row_ordering.py::test_save_order_marks_legacy_manual_rows_and_keeps_mixed_order -q`; it must fail because the module does not exist.

- [ ] **Step 3: Write minimal implementation**

Create a `veryHidden` sheet named `_mp2027_output_cost_row_order` with CC, sheet, row ID, row kind, signature, sort order and current row. Convert old contiguous manual-section metadata only when it exists. Derive common identity from account B, description S and occurrence; reject duplicated IDs and a metadata CC/sheet mismatch.

- [ ] **Step 4: Verify GREEN**

Run the same focused test; it must pass.

- [ ] **Step 5: Commit**

Run `git add tests/test_output_cost_row_ordering.py src/engine/output_cost_row_ordering.py` then `git commit -m "feat: track output cost row ownership"`.

### Task 2: Restore a mixed layout safely for reruns and new FYs

**Files:**

- Modify: `tests/test_output_cost_row_ordering.py`
- Modify: `src/engine/output_cost_row_ordering.py`
- Modify: `src/engine/manual_special_cost_sections.py`

- [ ] **Step 1: Write failing tests**

```python
def test_rerun_keeps_manual_money_when_rows_are_mixed(tmp_path):
    source = _saved_mixed_layout(tmp_path / "FY2027.xlsx")
    generated = _workbook_with_common_rows(tmp_path / "FY2027-rerun.xlsx", common_end=90)

    restore_cost_layout(generated, "1412000030", source, source_kind="current_fiscal_year")

    assert _labels(generated)[:4] == ["common-38", "manual-A", "common-39", "manual-B"]
    assert _amount_for(generated, "manual-A") == 1_250_000


def test_new_fy_keeps_manual_code_description_and_order_but_clears_money(tmp_path):
    source = _saved_mixed_layout(tmp_path / "FY2026.xlsx")
    generated = _workbook_with_common_rows(tmp_path / "FY2027.xlsx", common_end=90)

    restore_cost_layout(generated, "1412000030", source, source_kind="previous_fiscal_year")

    assert _row_for(generated, "manual-A").account_code == 5005246286
    assert _row_for(generated, "manual-A").description == "manual-A"
    assert _row_for(generated, "manual-A").money_cells == [None] * 13
```

- [ ] **Step 2: Verify RED**

Run `py -3 -m pytest tests/test_output_cost_row_ordering.py -q`; the new tests must fail because no layout merge/FY transform exists.

- [ ] **Step 3: Write minimal implementation**

Snapshot A:T including styles, dimensions and formula translation. Merge source manual snapshots with freshly generated common snapshots by prior sort order; append unmatched common signatures and return their count. For `previous_fiscal_year`, retain B and S plus presentation formatting but clear F:R values/formulas. For `current_fiscal_year`, retain the whole manual snapshot. Keep `preserve_manual_special_cost_section` as a compatibility wrapper and keep first-year automatic empty-section creation.

- [ ] **Step 4: Verify GREEN**

Run `py -3 -m pytest tests/test_output_cost_row_ordering.py tests/test_manual_special_cost_sections.py -q`; all must pass.

- [ ] **Step 5: Commit**

Run `git add tests/test_output_cost_row_ordering.py tests/test_manual_special_cost_sections.py src/engine/output_cost_row_ordering.py src/engine/manual_special_cost_sections.py` then `git commit -m "feat: preserve mixed cost layout across fiscal runs"`.

### Task 3: Integrate pipeline and business messages

**Files:**

- Modify: `scripts/run_e2e.py`
- Modify: `src/services/i18n.py`
- Modify: `tests/test_manual_special_cost_sections.py`

- [ ] **Step 1: Write a failing test**

```python
def test_pipeline_logs_new_common_rows_and_new_fy_clear_money(tmp_path):
    result = _restore_manual_special_cost_section(..., source_kind="previous_fiscal_year", log_callback=logs.append)

    assert result["new_common_rows"] == 1
    assert any("mã và mô tả" in log for log in logs)
```

- [ ] **Step 2: Verify RED**

Run `py -3 -m pytest tests/test_manual_special_cost_sections.py::test_pipeline_logs_new_common_rows_and_new_fy_clear_money -q`; it must fail because results/logs do not distinguish FY-new behavior.

- [ ] **Step 3: Write minimal implementation**

Pass `source_kind` to the engine, expose `new_common_rows`, and use translated strings. Prior-FY wording must say “giữ mã và mô tả; xoá số tiền/công thức tiền”; it must not say that old money is retained.

- [ ] **Step 4: Verify GREEN**

Run `py -3 -m pytest tests/test_manual_special_cost_sections.py tests/test_i18n.py -q`; all must pass.

- [ ] **Step 5: Commit**

Run `git add scripts/run_e2e.py src/services/i18n.py tests/test_manual_special_cost_sections.py` then `git commit -m "fix: clear inherited manual money for new fiscal year"`.

### Task 4: Add the optional row-ordering UI

**Files:**

- Modify: `src/universal_app.py`
- Modify: `src/services/i18n.py`
- Modify: `tests/test_gui_cost_center_and_output_actions.py`

- [ ] **Step 1: Write a failing test**

```python
def test_output_row_order_action_is_optional_and_uses_output_folder(monkeypatch, tmp_path):
    app = _app_with_output_dir(tmp_path)
    monkeypatch.setattr("src.universal_app.filedialog.askopenfilename", lambda **_: str(_marked_workbook(tmp_path)))

    app.open_output_cost_row_ordering()

    assert app._opened_cost_order_dialog_for.endswith(".xlsx")
```

- [ ] **Step 2: Verify RED**

Run `py -3 -m pytest tests/test_gui_cost_center_and_output_actions.py::test_output_row_order_action_is_optional_and_uses_output_folder -q`; it must fail because the UI action does not exist.

- [ ] **Step 3: Write minimal implementation**

Add `output_cost_row_order_btn` to the existing actions bar. Choose an Excel file rooted at current FY output. Build a `ttk.Treeview` from the engine read API, support mouse drag/release and Lên/Xuống fallback buttons, then call the save API. Give a clear error when legacy start metadata is missing. Add all locale strings and update the button during language refresh.

- [ ] **Step 4: Verify GREEN**

Run `py -3 -m pytest tests/test_gui_cost_center_and_output_actions.py tests/test_gui_dynamic_localization.py tests/test_i18n.py -q`; all must pass.

- [ ] **Step 5: Commit**

Run `git add src/universal_app.py src/services/i18n.py tests/test_gui_cost_center_and_output_actions.py` then `git commit -m "feat: add output cost row ordering dialog"`.

### Task 5: Audit and regression acceptance

- [ ] **Step 1: Run focused acceptance suite**

Run `py -3 -m pytest tests/test_output_cost_row_ordering.py tests/test_manual_special_cost_sections.py tests/test_complete_v1_source_order_writer.py tests/test_headcount_and_export.py tests/test_fiscal_run_context.py tests/test_i18n.py tests/test_gui_cost_center_and_output_actions.py tests/test_gui_dynamic_localization.py -q`; every test must pass.

- [ ] **Step 2: Run static audit**

Run `py -3 -m compileall -q src scripts` and `git diff --check`; both must produce no errors.

- [ ] **Step 3: Review business-rule coverage**

Verify tests cover: optional/no-button legacy flow, current-FY full preservation, prior-FY code/description/order only, mixed layout, new common row, missing/corrupt metadata, and three locales.
