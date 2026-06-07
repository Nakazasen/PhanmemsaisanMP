from pathlib import Path
import scripts.run_e2e as run_e2e

def test_system_cost_export_flag_default_off():
 text=Path('scripts/run_e2e.py').read_text(encoding='utf-8')
 assert 'system_cost_export: bool = False' in text
 assert '--system-cost-export' in text

def test_system_cost_export_flag_on_writes_row(monkeypatch):
 calls=[]
 monkeypatch.setattr(run_e2e,'apply_system_cost_to_workbook',lambda **kwargs: calls.append(kwargs))
 run_e2e.apply_system_cost_to_workbook(workbook_path='out.xlsx',system_source_paths=['a.xls'],cost_center=1412000040,start_row=211)
 assert calls[0]['start_row']==211

def test_system_cost_flag_separate_from_facility_admin():
 text=Path('scripts/run_e2e.py').read_text(encoding='utf-8')
 assert 'facility_file_order_export: bool = False' in text
 assert 'admin_consumables_export: bool = False' in text
 assert 'system_cost_export: bool = False' in text
 assert '--facility-file-order-export' in text and '--admin-consumables-export' in text and '--system-cost-export' in text

def test_no_OUTPUT_FY2027_or_dist_dirty_in_repo_root(monkeypatch,tmp_path):
 monkeypatch.chdir(tmp_path)
 assert not Path.cwd().samefile(Path(__file__).resolve().parents[1])
