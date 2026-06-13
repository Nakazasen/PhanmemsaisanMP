from pathlib import Path

from src.parsers.manual_event_drivers import OPTIONAL_COLUMNS, TEMPLATE_COLUMNS
from src.parsers.manual_headcount import BUS_DRIVER_COLUMNS, BUS_DRIVER_FILENAME


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
