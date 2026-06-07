from pathlib import Path

import scripts.run_e2e as run_e2e


def test_admin_consumables_export_flag_default_off():
    text = Path("scripts/run_e2e.py").read_text(encoding="utf-8")
    assert "admin_consumables_export: bool = False" in text
    assert "--admin-consumables-export" in text


def test_admin_consumables_export_flag_on_writes_rows(monkeypatch, tmp_path):
    calls = []
    out = tmp_path / "OUTPUT_FY2027" / "MP_CC_1412000040.xlsx"
    out.parent.mkdir()
    out.write_bytes(b"placeholder")

    def fake_apply(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(run_e2e, "apply_admin_consumables_to_workbook", fake_apply)
    run_e2e.apply_admin_consumables_to_workbook(
        workbook_path=out,
        admin_source_path="admin.xlsx",
        allocation_source_path="alloc.xlsx",
        cost_center=1412000040,
        start_row=207,
    )
    assert calls[0]["start_row"] == 207


def test_admin_consumables_export_does_not_dirty_OUTPUT_FY2027_repo_root(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    output_dir = Path("OUTPUT_FY2027")
    output_dir.mkdir()
    assert output_dir.exists()
    assert not Path.cwd().samefile(Path(__file__).resolve().parents[1])


def test_admin_consumables_flag_is_separate_from_facility_flags():
    text = Path("scripts/run_e2e.py").read_text(encoding="utf-8")
    assert "facility_file_order_export: bool = False" in text
    assert "admin_consumables_export: bool = False" in text
    assert "--facility-file-order-export" in text
    assert "--admin-consumables-export" in text
