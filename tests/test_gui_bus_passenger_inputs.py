from pathlib import Path

from src.parsers.manual_event_drivers import OPTIONAL_COLUMNS, TEMPLATE_COLUMNS


def test_event_driver_gui_has_dedicated_bus_passenger_inputs():
    source = Path("src/universal_app.py").read_text(encoding="utf-8")

    assert "Người biệt phái đi xe bus" in source
    assert "Người Việt Nam đi xe bus" in source
    assert "bus_expat_people_var = tk.StringVar(value=\"0\")" in source
    assert "bus_vietnamese_people_var = tk.StringVar(value=\"0\")" in source
    assert "validate_non_negative_int" in source


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
