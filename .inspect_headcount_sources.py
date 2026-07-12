import xlrd, json
from pathlib import Path
files=list(Path('raw/10.07.2026').glob('*FY2027マスタープラン人員・時間計画表(Ver01).xls'))
wanted={'14.','15.','16.','72.','73.'}
for p in files:
 if not any(p.name.startswith(x) for x in wanted): continue
 wb=xlrd.open_workbook(str(p), formatting_info=False)
 print('\n###',p.name,'sheets=',wb.sheet_names())
 for sh in wb.sheets():
  print('SHEET',sh.name,sh.nrows,sh.ncols)
  for r in range(min(sh.nrows,45)):
   vals=[sh.cell_value(r,c) for c in range(min(sh.ncols,22))]
   non=[(xlrd.formula.colname(c),v) for c,v in enumerate(vals) if str(v).strip()]
   if non: print(r+1,non)
  print()
