from pathlib import Path

import scripts.run_e2e as run_e2e


def test_file_order_export_v1_flag_default_off():
    text = Path('scripts/run_e2e.py').read_text(encoding='utf-8')
    assert 'file_order_export_v1: bool = False' in text
    assert '--file-order-export-v1' in text


def test_file_order_export_v1_enables_facility_admin_system():
    text = Path('scripts/run_e2e.py').read_text(encoding='utf-8')
    assert 'if file_order_export_v1:' in text
    assert 'facility_file_order_export = True' in text
    assert 'facility_file_order_start_row = 200' in text
    assert 'admin_consumables_export = True' in text
    assert 'admin_consumables_start_row = 207' in text
    assert 'system_cost_export = True' in text
    assert 'system_cost_start_row = 211' in text


def test_individual_flags_still_exist():
    text = Path('scripts/run_e2e.py').read_text(encoding='utf-8')
    assert '--facility-file-order-export' in text
    assert '--admin-consumables-export' in text
    assert '--system-cost-export' in text
    assert '--file-order-export-v1' in text


def test_default_export_behavior_not_changed():
    text = Path('scripts/run_e2e.py').read_text(encoding='utf-8')
    assert 'facility_file_order_export: bool = False' in text
    assert 'admin_consumables_export: bool = False' in text
    assert 'system_cost_export: bool = False' in text
    assert 'file_order_export_v1: bool = False' in text


def test_file_order_v1_does_not_dirty_OUTPUT_FY2027_repo_root(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    output_dir = Path('OUTPUT_FY2027')
    output_dir.mkdir()
    assert output_dir.exists()
    assert not Path.cwd().samefile(Path(__file__).resolve().parents[1])
