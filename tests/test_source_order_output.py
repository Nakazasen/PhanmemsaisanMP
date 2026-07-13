from src.engine.source_order_output import (
    CANONICAL_SOURCE_FILE_ORDER,
    OutputRow,
    place_rows_by_source_file_order,
    source_order_index,
)


def test_canonical_source_order_matches_user_requirement():
    assert len(CANONICAL_SOURCE_FILE_ORDER) == 7
    assert CANONICAL_SOURCE_FILE_ORDER[0].endswith("MPFY2027.xlsx")
    assert "Fixed_Assets_Information_2025.11 - Nov.xlsx" in CANONICAL_SOURCE_FILE_ORDER[1]
    assert "Simulation)_FY2027_Apr.2026 ~ June.2026.xls" in CANONICAL_SOURCE_FILE_ORDER[2]
    assert "FY2027 MP" in CANONICAL_SOURCE_FILE_ORDER[3]
    assert CANONICAL_SOURCE_FILE_ORDER[4].startswith("Sinh")
    assert "(2025.12.29).xlsx" in CANONICAL_SOURCE_FILE_ORDER[5]
    assert "NNN FY2027.xlsx" in CANONICAL_SOURCE_FILE_ORDER[6]


def test_source_order_index_unknown_files_go_last():
    assert source_order_index(CANONICAL_SOURCE_FILE_ORDER[0]) == 0
    assert source_order_index(CANONICAL_SOURCE_FILE_ORDER[6]) == 6
    assert source_order_index("unknown.xlsx") > 6


def test_place_rows_by_source_order_inserts_one_blank_between_file_blocks():
    rows = [
        OutputRow(CANONICAL_SOURCE_FILE_ORDER[4], {"item": "birthday-1"}),
        OutputRow(CANONICAL_SOURCE_FILE_ORDER[0], {"item": "facility-1"}),
        OutputRow(CANONICAL_SOURCE_FILE_ORDER[0], {"item": "facility-2"}),
        OutputRow(CANONICAL_SOURCE_FILE_ORDER[6], {"item": "nnn-1"}),
    ]

    placed = place_rows_by_source_file_order(rows, start_row=200)

    assert [(r.output_row, r.source_file, r.values.get("item"), r.is_blank_separator) for r in placed] == [
        (200, CANONICAL_SOURCE_FILE_ORDER[0], "facility-1", False),
        (201, CANONICAL_SOURCE_FILE_ORDER[0], "facility-2", False),
        (202, CANONICAL_SOURCE_FILE_ORDER[0], None, True),
        (203, CANONICAL_SOURCE_FILE_ORDER[4], "birthday-1", False),
        (204, CANONICAL_SOURCE_FILE_ORDER[4], None, True),
        (205, CANONICAL_SOURCE_FILE_ORDER[6], "nnn-1", False),
    ]


def test_no_fixed_form_rows_are_required_by_policy():
    rows = [
        OutputRow(CANONICAL_SOURCE_FILE_ORDER[1], {"amount": 1}),
        OutputRow(CANONICAL_SOURCE_FILE_ORDER[6], {"amount": 2}),
    ]

    placed = place_rows_by_source_file_order(rows, start_row=1)

    assert [r.output_row for r in placed if not r.is_blank_separator] == [1, 3]
    assert all(r.output_row not in [38, 42, 58, 59, 97, 98, 137] for r in placed)
