import xlrd
from pathlib import Path
wanted=('14.','15.','16.','72.','73.')
for p in sorted(Path('raw/10.07.2026').glob('*.xls')):
 if not p.name.startswith(wanted): continue
 wb=xlrd.open_workbook(str(p)); sh=wb.sheet_by_index(0)
 print('\n###',p.name); print('shape',sh.nrows,sh.ncols)
 for r in range(sh.nrows):
  label=' | '.join(str(sh.cell_value(r,c)).strip() for c in range(min(2,sh.ncols)) if str(sh.cell_value(r,c)).strip())
  if r<15:
   vals=[sh.cell_value(r,c) for c in range(2,min(14,sh.ncols))]
   print(f'{r+1:02} {label}:',vals)
