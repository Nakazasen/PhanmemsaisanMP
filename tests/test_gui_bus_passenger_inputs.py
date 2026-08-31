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


def test_annual_staffing_editor_uses_project_canonical_and_annual_manual_stores():
    source = Path("src/universal_app.py").read_text(encoding="utf-8")
    load_start = source.index("        def load_cc(*_):")
    save_start = source.index("        def nonneg(text,label):", load_start)
    load_source = source[load_start:save_start]

    assert 't("hc_v2_bus_frame")' in source
    assert 't("hc_v2_bus_expat")' in source
    assert 't("hc_v2_bus_vn")' in source
    assert "bus_exp=tk.StringVar(value=\"0\")" in source
    assert "bus_vn=tk.StringVar(value=\"0\")" in source
    assert "source_conn = get_connection(self._operational_database())" in load_source
    assert "manual_conn = get_connection(self._manual_input_store(fiscal_year))" in load_source
    assert "source_conn.execute(" in load_source
    assert "fact_manual_headcount_time_override" in load_source
    assert "manual_conn.execute(" in load_source
    assert "source_rows = manual_conn.execute(" not in load_source
    assert "timerows = manual_conn.execute(" not in load_source



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


def test_headcount_save_partially_blank_baseline_keeps_explicit_zero_and_no_old_defaulting_source():
    periods = get_required_headcount_periods(2027)
    values = _full_period_values()
    values["202603"]["staff"] = ""
    rows, errors = validate_headcount_save_period_rows(periods, values, {period: period for period in periods})

    assert errors == []
    assert rows[0]["period"] == "202603"
    assert rows[0]["headcount_staff"] == "0"
    formatted = format_headcount_save_errors(errors)
    assert formatted == ""

    source = Path("src/universal_app.py").read_text(encoding="utf-8")
    assert "conn=get_connection(self._manual_input_store(fiscal_year))" in source
    assert "save_manual_baseline_override(conn,fiscal_year,cc" in source
    assert "save_manual_time_overrides(conn,fiscal_year,cc" in source
    assert "staff_text = month_vars[period][\"staff\"].get().strip() or \"0\"" not in source


def test_headcount_save_rejects_completely_unentered_baseline():
    periods = get_required_headcount_periods(2027)
    values = _full_period_values()
    values["202603"].update({"expat": "", "staff": "", "worker": ""})

    rows, errors = validate_headcount_save_period_rows(
        periods,
        values,
        {period: period for period in periods},
    )

    assert not any(row["period"] == "202603" for row in rows)
    assert any(
        error["period"] == "202603"
        and error["field"] == "baseline_t3"
        and error["validation_rule"] == "REQUIRED"
        for error in errors
    )


def test_headcount_save_blank_worker_is_zero_and_invalid_numbers_are_exact_errors():
    periods = get_required_headcount_periods(2027)
    values = _full_period_values()
    values["202604"]["worker"] = ""
    values["202605"]["staff"] = "-1"
    values["202606"]["staff"] = "1.5"
    values["202607"]["worker"] = "abc"

    _, errors = validate_headcount_save_period_rows(periods, values, {period: period for period in periods})
    observed = {(error["period"], error["field"], error["raw_value"], error["validation_rule"]) for error in errors}

    assert ("202604", "headcount_worker", "", "REQUIRED") not in observed
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
