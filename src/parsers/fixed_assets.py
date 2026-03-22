"""
MP2027 Manager - Fixed Assets Parser (固定資産情報)
Parses Fixed Assets .xlsx files to extract depreciation schedules for the given fiscal year.
"""
import sqlite3
import os
from datetime import datetime
import openpyxl
from src.utils.excel_helpers import safe_float, extract_cc_code, get_fy_months

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

def find_fixed_assets_file(source_dir: str = None) -> str:
    search_dir = source_dir or BASE_DIR
    for f in os.listdir(search_dir):
        if '固定資産情報' in f and f.endswith('.xlsx'):
            return os.path.join(search_dir, f)
    return ''

def parse_fixed_assets(conn: sqlite3.Connection, fa_path: str = None, source_dir: str = None) -> dict:
    """Parse fixed assets file with dynamic year support."""
    path = fa_path or find_fixed_assets_file(source_dir)
    if not path or not os.path.exists(path):
        print(f"⚠️ Fixed assets file not found")
        return {'total': 0}

    # Get year-aware months
    fy_row = conn.execute("SELECT value FROM sys_params WHERE key='fiscal_year'").fetchone()
    fy_str = fy_row[0] if fy_row else "FY2027"
    fy_int = int(fy_str.replace('FY', ''))
    fy_months = get_fy_months(fy_int)

    print(f"📖 Reading: {os.path.basename(path)}")
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        print(f"⚠️ Error opening fixed assets file: {e}")
        return {'total': 0}

    cursor = conn.cursor()
    total = 0
    results = {}

    for sname in wb.sheetnames:
        if sname not in ('Planned Depreciation', 'Sheet1'):
            continue 

        ws = wb[sname]
        cc_col_idx = None
        data_start_row = None
        
        header_rows = []
        for row in ws.iter_rows(min_row=1, max_row=15, values_only=True):
            header_rows.append(row)
            
        for r_idx, row in enumerate(header_rows):
            for c_idx, val in enumerate(row):
                sval = str(val).strip().replace('\n', '')
                if 'Cost Center' in sval or '原価センタ' in sval or 'CC' in sval:
                    if 'Control' in sval: continue
                    cc_col_idx = c_idx
                    data_start_row = r_idx + 2
                    break
            if cc_col_idx is not None: break

        if cc_col_idx is None: continue

        # Identify date columns
        month_cols_idx = []
        date_row_idx = data_start_row - 1
        if date_row_idx < len(header_rows):
            for c_idx in range(cc_col_idx + 1, len(header_rows[date_row_idx])):
                val = header_rows[date_row_idx][c_idx]
                if val: month_cols_idx.append(c_idx)

        if not month_cols_idx:
            month_cols_idx = list(range(cc_col_idx + 1, cc_col_idx + 13))

        count = 0
        for row in ws.iter_rows(min_row=data_start_row + 1, values_only=True):
            if cc_col_idx >= len(row): continue
            cc = extract_cc_code(row[cc_col_idx])
            if not cc or cc < 1000000: continue

            for m_idx in range(12):
                period = fy_months[m_idx]
                col = month_cols_idx[m_idx] if m_idx < len(month_cols_idx) else month_cols_idx[-1]
                amount = safe_float(row[col]) if col < len(row) else 0.0
                
                if amount == 0.0: continue

                cursor.execute("""
                    INSERT INTO fact_input_data
                    (source, period, amount_vnd, cc_code, account_code, scenario_id, description)
                    VALUES ('fixed_assets', ?, ?, ?, 0, 'base', ?)
                """, (period, amount, cc, f"fixed_assets|{sname}"))
                count += 1
                total += 1

        results[sname] = count
        print(f"  📊 {sname}: {count} records inserted")

    conn.commit()
    wb.close()
    results['total'] = total
    print(f"✅ Fixed Assets total: {total} records.")
    return results
