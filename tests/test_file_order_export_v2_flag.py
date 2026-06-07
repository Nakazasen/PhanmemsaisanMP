from pathlib import Path

import pytest

import scripts.run_e2e as run_e2e


def test_file_order_export_v2_flag_default_off():
    text = Path("scripts/run_e2e.py").read_text(encoding="utf-8")
    assert "file_order_export_v2: bool = False" in text
    assert "primary_reference_fill: bool = False" in text
    assert "--file-order-export-v2" in text
    assert "--primary-reference-fill" in text
    assert "--primary-reference-path" in text


def test_file_order_export_v2_enables_v1_and_reference_fill():
    text = Path("scripts/run_e2e.py").read_text(encoding="utf-8")
    assert "if file_order_export_v2:" in text
    assert "file_order_export_v1 = True" in text
    assert "primary_reference_fill = True" in text
    assert "primary_reference_fill_start_row = 213" in text


def test_file_order_export_v1_does_not_enable_reference_fill():
    text = Path("scripts/run_e2e.py").read_text(encoding="utf-8")
    v1_block = text.split("if file_order_export_v1:", 1)[1].split("try:", 1)[0]
    assert "primary_reference_fill = True" not in v1_block


def test_reference_fill_is_after_normal_export():
    text = Path("scripts/run_e2e.py").read_text(encoding="utf-8")
    assert text.index("apply_system_cost_to_workbook") < text.index("apply_reference_assisted_fill_to_workbook")


def test_v2_current_target_can_use_default_primary_reference():
    resolved = run_e2e._resolve_primary_reference_path(1412000040, reference_map_path="missing-map.csv")
    assert resolved.endswith("16.KDTVN 電気製造技術課_MP FY2027_各予定(Ver01).xlsx")


def test_v2_other_cc_without_reference_path_fails(tmp_path):
    missing_map = tmp_path / "missing.csv"
    with pytest.raises(ValueError, match="Reference-assisted fill requires --primary-reference-path for this target CC"):
        run_e2e._resolve_primary_reference_path(9999999999, reference_map_path=str(missing_map))


def test_v2_other_cc_with_explicit_reference_path_is_accepted(tmp_path):
    ref = tmp_path / "reference.xlsx"
    ref.write_bytes(b"placeholder")
    resolved = run_e2e._resolve_primary_reference_path(9999999999, primary_reference_path=str(ref))
    assert resolved == str(ref.resolve())


def test_reference_map_accepts_mapped_other_cc(tmp_path):
    ref = tmp_path / "reference.xlsx"
    ref.write_bytes(b"placeholder")
    mapping = tmp_path / "reference_workbook_map.csv"
    mapping.write_text(
        "target_cc,department_name,reference_path,reference_role\n"
        f"9999999999,Dept,{ref},primary_reference\n",
        encoding="utf-8",
    )
    resolved = run_e2e._resolve_primary_reference_path(9999999999, reference_map_path=str(mapping))
    assert resolved == str(ref)
