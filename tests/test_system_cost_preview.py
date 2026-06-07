from pathlib import Path
from src.engine.system_cost_preview import preview_system_cost_file_order
SYSTEM=[Path('raw/システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls'),Path('raw/システム課金金額(Simulation)_FY2027_July.2026 ~ Dec.2026(Change AMS & PLM price).xls'),Path('raw/システム課金金額(Simulation)_FY2027_Jan.2027 ~ March.2027(Change SAP price).xls')]
def test_system_cost_preview_detects_native_structure():
 p=preview_system_cost_file_order(SYSTEM)
 assert p.items[0].confidence=='HIGH'
 assert len(p.items[0].month_values)==12
 assert set(p.items[0].month_values)=={6111363.0}
def test_system_cost_preview_single_row_211_blank_212():
 p=preview_system_cost_file_order(SYSTEM)
 assert p.items[0].planned_row==211
 assert p.blank_row_after==212
