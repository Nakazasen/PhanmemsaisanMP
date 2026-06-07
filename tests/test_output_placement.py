from dataclasses import replace

from src.engine.output_mode import OutputMode, get_default_output_group_specs, get_group_spec
from src.engine.output_placement import PlannedOutputGroup, plan_output_groups


def _planned_by_id(start_row=200, item_counts=None):
    return {
        group.group_id: group
        for group in plan_output_groups(
            get_default_output_group_specs(),
            start_row=start_row,
            item_counts=item_counts,
        )
    }


def test_planner_sorts_by_requirement_file_order():
    specs = tuple(reversed(get_default_output_group_specs()))
    planned = plan_output_groups(specs, start_row=200, item_counts={"facility": 6})

    assert [group.group_id for group in planned] == [
        "facility",
        "fixed_assets",
        "system_cost",
        "admin_allocation",
        "birthday",
        "allocation_master",
        "nnn_paperwork",
    ]


def test_facility_plans_six_rows_and_blank_separator():
    planned = _planned_by_id(item_counts={"facility": 6})
    facility = planned["facility"]

    assert isinstance(facility, PlannedOutputGroup)
    assert facility.output_mode == OutputMode.FILE_ORDER_GROUP
    assert facility.start_row == 200
    assert facility.end_row == 205
    assert facility.blank_row_after == 206
    assert len(facility.item_rows) == 6
    assert facility.item_rows[0] == ("6 chi phí", 200)
    assert facility.item_rows[-1][1] == 205


def test_system_cost_plans_single_row():
    planned = _planned_by_id(item_counts={"facility": 6})
    system_cost = planned["system_cost"]

    assert system_cost.output_mode == OutputMode.FILE_ORDER_SINGLE_ROW
    assert system_cost.item_rows == (("one combined row", 208),)
    assert system_cost.start_row == 208
    assert system_cost.end_row == 208
    assert system_cost.blank_row_after == 209


def test_blank_row_after_each_file_order_group():
    planned = _planned_by_id(item_counts={"facility": 6, "admin_allocation": 2, "allocation_master": 3})

    assert planned["facility"].blank_row_after == 206
    assert planned["system_cost"].blank_row_after == 209
    assert planned["admin_allocation"].blank_row_after == 212
    assert planned["allocation_master"].blank_row_after == 217
    assert planned["system_cost"].start_row == planned["fixed_assets"].blank_row_after + 1
    assert planned["admin_allocation"].start_row == planned["system_cost"].blank_row_after + 1


def test_mixed_transition_preserves_fixed_rows_metadata():
    spec = get_group_spec("fixed_assets")
    fixed_assets = _planned_by_id(item_counts={"facility": 6})["fixed_assets"]

    assert spec.fixed_rows == (38, 42)
    assert fixed_assets.output_mode == OutputMode.MIXED_TRANSITION
    assert fixed_assets.start_row is None
    assert fixed_assets.end_row is None
    assert fixed_assets.item_rows == ()
    assert fixed_assets.blank_row_after == 207
    assert fixed_assets.notes == "mixed_transition_no_write_yet"


def test_row_compat_pending_keeps_fixed_rows_metadata():
    birthday_spec = get_group_spec("birthday")
    nnn_spec = get_group_spec("nnn_paperwork")
    planned = _planned_by_id(item_counts={"facility": 6})

    assert birthday_spec.fixed_rows == (59, 63)
    assert nnn_spec.fixed_rows == (137,)
    assert planned["birthday"].start_row is None
    assert planned["birthday"].notes == "row_compat_or_file_order_pending_no_write_yet"
    assert planned["nnn_paperwork"].start_row is None
    assert planned["nnn_paperwork"].notes == "row_compat_or_file_order_pending_no_write_yet"


def test_planner_does_not_mutate_specs():
    specs = get_default_output_group_specs()
    before = tuple(replace(spec) for spec in specs)

    plan_output_groups(specs, start_row=200, item_counts={"facility": 6})

    assert specs == before


def test_no_excel_writer_dependency():
    import src.engine.output_placement as output_placement

    module_names = set(output_placement.__dict__)
    assert "openpyxl" not in module_names
    assert "Workbook" not in module_names
    assert "insert_rows" not in output_placement.__dict__
