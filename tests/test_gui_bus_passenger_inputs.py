from pathlib import Path

from src.parsers.manual_event_drivers import OPTIONAL_COLUMNS, TEMPLATE_COLUMNS
from src.parsers.manual_headcount import BUS_DRIVER_COLUMNS, BUS_DRIVER_FILENAME, get_required_headcount_periods
from src.universal_app import (
    format_headcount_save_errors,
    validate_bus_headcount_save_rows,
    validate_headcount_save_period_rows,
)


def test_event_driver_gui_has_dedicated_bus_passenger_inputs():
    source = Path("src/universal_app.py").read_text(encoding="utf-8")

    assert "Người biệt phái đi xe bus" in source
    assert "Người Việt Nam đi xe bus" in source
    assert "bus_expat_people_var = tk.StringVar(value=\"0\")" in source
    assert "bus_vietnamese_people_var = tk.StringVar(value=\"0\")" in source
    assert "validate_non_negative_int" in source


def test_headcount_gui_has_scalar_bus_driver_inputs():
    source = Path("src/universal_app.py").read_text(encoding="utf-8")

    assert "Th\\u00f4ng tin xe bus - d\\u00f9ng chung cho 12 th\\u00e1ng" in source
    assert "Ng\\u01b0\\u1eddi bi\\u1ec7t ph\\u00e1i \\u0111i xe bus" in source
    assert "Ng\\u01b0\\u1eddi Vi\\u1ec7t Nam \\u0111i xe bus" in source
    assert "bus_expat_count_var = tk.StringVar(value=\"0\")" in source
    assert "bus_vietnamese_count_var = tk.StringVar(value=\"0\")" in source
    assert "S\\u1ed1 l\\u01b0\\u1ee3ng n\\u00e0y \\u0111\\u01b0\\u1ee3c s\\u1eed d\\u1ee5ng chung cho 12 th\\u00e1ng FY." in source
    assert "ensure_manual_bus_headcount_template(source_dir)" in source


def test_headcount_gui_uses_canonical_manual_source_and_clears_on_cc_switch():
    source = Path("src/universal_app.py").read_text(encoding="utf-8")

    assert "resolve_manual_headcount_source_dir(self.source_dir.get() or BASE_DIR, base_dir=BASE_DIR)" in source
    assert "csv_path = ensure_manual_headcount_template(source_dir, fiscal_year)" in source
    assert "bus_csv_path = ensure_manual_bus_headcount_template(source_dir)" in source
    assert "result = parse_manual_headcount(conn, source_dir=source_dir)" in source

    clear_start = source.index("def clear_table")
    load_start = source.index("def load_selected_cc")
    clear_call = source.index("clear_table()", load_start)
    cc_parse = source.index("cc_code = parse_cc_code", load_start)
    assert clear_call < cc_parse
    assert 'field_var.set("")' in source[clear_start:load_start]


def test_manual_headcount_bus_driver_template_columns_are_scalar_per_cc():
    assert BUS_DRIVER_FILENAME == "bus_headcount_manual.csv"
    assert BUS_DRIVER_COLUMNS == ("cc_code", "bus_expat_count", "bus_vietnamese_count", "description")


def test_manual_event_driver_template_saves_bus_passenger_counts():
    assert "bus_expat_people" in TEMPLATE_COLUMNS
    assert "bus_vietnamese_people" in TEMPLATE_COLUMNS
    assert "bus_expat_people" in OPTIONAL_COLUMNS
    assert "bus_vietnamese_people" in OPTIONAL_COLUMNS


def test_bus_passenger_counts_are_not_formula_mapped_without_unit_cost_source():
    parser_source = Path("src/parsers/manual_event_drivers.py").read_text(encoding="utf-8")

    assert "safe_float(row.get(\"count\"))" in parser_source
    assert "safe_float(row.get(\"bus_expat_people\"))" not in parser_source
    assert "safe_float(row.get(\"bus_vietnamese_people\"))" not in parser_source


def _full_period_values(staff="1", worker="0"):
    return {
        period: {"staff": staff, "worker": worker, "male": "", "female": "", "description": ""}
        for period in get_required_headcount_periods(2027)
    }


def test_headcount_save_requires_full_13_period_series_before_write():
    periods = get_required_headcount_periods(2027)
    values = _full_period_values()
    rows, errors = validate_headcount_save_period_rows(periods, values, {period: period for period in periods})

    assert len(rows) == 13
    assert errors == []
    assert rows[0]["period"] == "202603"


def test_headcount_save_missing_baseline_is_exact_error_and_no_success_title_source():
    periods = get_required_headcount_periods(2027)
    values = _full_period_values()
    values["202603"]["staff"] = ""
    rows, errors = validate_headcount_save_period_rows(periods, values, {period: period for period in periods})

    assert rows
    assert errors[0]["period"] == "202603"
    assert errors[0]["field"] == "headcount_staff"
    assert errors[0]["validation_rule"] == "REQUIRED"
    assert errors[0]["csv_row_written"] is False
    assert errors[0]["db_row_inserted"] is False
    formatted = format_headcount_save_errors(errors)
    assert "202603 | headcount_staff | blank | REQUIRED" in formatted

    source = Path("src/universal_app.py").read_text(encoding="utf-8")
    assert "Lưu chưa hoàn tất cho CC {cc_code}. Không có thay đổi nào được áp dụng." in source
    assert "Đã lưu đầy đủ {rows} kỳ cho CC {cc}." in source
    assert "staff_text = month_vars[period][\"staff\"].get().strip() or \"0\"" not in source


def test_headcount_save_missing_worker_and_invalid_numbers_are_exact_errors():
    periods = get_required_headcount_periods(2027)
    values = _full_period_values()
    values["202604"]["worker"] = ""
    values["202605"]["staff"] = "-1"
    values["202606"]["staff"] = "1.5"
    values["202607"]["worker"] = "abc"

    _, errors = validate_headcount_save_period_rows(periods, values, {period: period for period in periods})
    observed = {(error["period"], error["field"], error["raw_value"], error["validation_rule"]) for error in errors}

    assert ("202604", "headcount_worker", "", "REQUIRED") in observed
    assert ("202605", "headcount_staff", "-1", "INTEGER_GTE_0") in observed
    assert ("202606", "headcount_staff", "1.5", "INTEGER_GTE_0") in observed
    assert ("202607", "headcount_worker", "abc", "INTEGER_GTE_0") in observed


def test_headcount_save_zero_values_and_optional_gender_blanks_are_valid():
    periods = get_required_headcount_periods(2027)
    values = _full_period_values(staff="0", worker="0")

    rows, errors = validate_headcount_save_period_rows(periods, values, {period: period for period in periods})

    assert errors == []
    assert len(rows) == 13
    assert all(row["headcount_staff"] == "0" for row in rows)
    assert all(row["headcount_worker"] == "0" for row in rows)
    december = next(row for row in rows if row["period"] == "202612")
    assert december["headcount_male"] == ""
    assert december["headcount_female"] == ""


def test_headcount_save_rejects_gender_split_over_total():
    periods = get_required_headcount_periods(2027)
    values = _full_period_values(staff="1", worker="0")
    values["202612"]["male"] = "2"

    _, errors = validate_headcount_save_period_rows(periods, values, {period: period for period in periods})

    assert any(error["period"] == "202612" and error["validation_rule"] == "SUM_LE_TOTAL" for error in errors)


def test_bus_zero_rows_validate_and_invalid_bus_row_is_exact_error():
    errors = validate_bus_headcount_save_rows(
        [{"cc_code": "1412000006", "bus_expat_count": "0", "bus_vietnamese_count": "0", "description": ""}],
        {"1412000006"},
    )
    assert errors == []

    bad_errors = validate_bus_headcount_save_rows(
        [{"cc_code": "1412000006", "bus_expat_count": "1.5", "bus_vietnamese_count": "0", "description": ""}],
        {"1412000006"},
    )
    assert bad_errors[0]["period"] == "bus"
    assert bad_errors[0]["field"] == "bus_expat_count"
    assert bad_errors[0]["validation_rule"] == "INTEGER_GTE_0"

    blank_errors = validate_bus_headcount_save_rows(
        [{"cc_code": "1412000006", "bus_expat_count": "", "bus_vietnamese_count": "0", "description": ""}],
        {"1412000006"},
    )
    assert blank_errors[0]["field"] == "bus_expat_count"
    assert blank_errors[0]["validation_rule"] == "INTEGER_GTE_0"
