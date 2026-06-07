from pathlib import Path

from src.engine.output_mode import (
    OutputMode,
    get_default_output_group_specs,
    get_group_spec,
    is_file_order_mode,
    is_fixed_row_compatible,
    requires_blank_row_after_group,
    sort_output_groups_by_file_order,
)


def test_default_output_group_order_matches_requirement_image():
    specs = get_default_output_group_specs()

    assert [spec.group_id for spec in specs] == [
        "facility",
        "fixed_assets",
        "system_cost",
        "admin_allocation",
        "birthday",
        "allocation_master",
        "nnn_paperwork",
    ]
    assert [spec.order_index for spec in specs] == list(range(1, 8))
    assert [spec.source_file_name for spec in specs] == [
        "施設課　MPFY2027.xlsx",
        "固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx",
        "システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls",
        "総務課 FY2027 MP 振替予定.xlsx",
        "Sinh nhật MP FY2027.xlsx",
        "FY2027配賦額一覧 (2025.12.29).xlsx",
        "Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx",
    ]


def test_facility_is_file_order_group_with_six_costs():
    spec = get_group_spec("facility")

    assert spec.output_mode == OutputMode.FILE_ORDER_GROUP
    assert spec.order_index == 1
    assert "6 chi phí" in spec.cost_items
    assert spec.costs_expected == 7
    assert requires_blank_row_after_group(spec)
    assert is_file_order_mode(spec)
    assert not spec.fixed_rows


def test_system_cost_is_file_order_single_row():
    spec = get_group_spec("system_cost")

    assert spec.output_mode == OutputMode.FILE_ORDER_SINGLE_ROW
    assert spec.cost_items == ("one combined row",)
    assert spec.costs_expected == 1
    assert is_file_order_mode(spec)


def test_fixed_assets_is_mixed_transition_with_rows_38_42():
    spec = get_group_spec("fixed_assets")

    assert spec.output_mode == OutputMode.MIXED_TRANSITION
    assert spec.fixed_rows == (38, 42)
    assert is_fixed_row_compatible(spec)
    assert not is_file_order_mode(spec)


def test_birthday_keeps_row_59_63_compatibility_risk():
    spec = get_group_spec("birthday")

    assert spec.output_mode == OutputMode.ROW_COMPAT_OR_FILE_ORDER_PENDING
    assert spec.fixed_rows == (59, 63)
    assert is_fixed_row_compatible(spec)
    assert "59/63" in spec.notes


def test_nnn_keeps_row_137_compatibility():
    spec = get_group_spec("nnn_paperwork")

    assert spec.output_mode == OutputMode.ROW_COMPAT_OR_FILE_ORDER_PENDING
    assert spec.fixed_rows == (137,)
    assert is_fixed_row_compatible(spec)


def test_all_default_groups_have_blank_row_after_group():
    for spec in get_default_output_group_specs():
        assert requires_blank_row_after_group(spec)


def test_sort_output_groups_by_file_order():
    specs = list(reversed(get_default_output_group_specs()))
    sorted_specs = sort_output_groups_by_file_order(specs)

    assert [spec.group_id for spec in sorted_specs] == [
        "facility",
        "fixed_assets",
        "system_cost",
        "admin_allocation",
        "birthday",
        "allocation_master",
        "nnn_paperwork",
    ]


def test_no_writer_integration_yet():
    hub_builder = Path("src/engine/hub_builder.py").read_text(encoding="utf-8")

    assert "sort_output_groups_by_file_order" not in hub_builder
    assert "insert_rows" not in hub_builder
    assert "blank_row_after_group" not in hub_builder
    assert "_write_file_order" not in hub_builder
    assert "_write_blank" not in hub_builder
    assert "self._output_group_specs()" not in hub_builder
    assert "self._write_fixed_rows(worksheet, target_cc)" in hub_builder


def test_hub_builder_exposes_output_group_specs_without_export_integration():
    from src.engine.hub_builder import HubBuilder

    builder = object.__new__(HubBuilder)
    specs = builder._output_group_specs()

    assert [spec.group_id for spec in specs] == [
        "facility",
        "fixed_assets",
        "system_cost",
        "admin_allocation",
        "birthday",
        "allocation_master",
        "nnn_paperwork",
    ]
    assert get_group_spec("facility") == specs[0]
    assert get_group_spec("system_cost") == specs[2]
    assert specs[0].output_mode == OutputMode.FILE_ORDER_GROUP
    assert specs[2].output_mode == OutputMode.FILE_ORDER_SINGLE_ROW
