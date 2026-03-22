"""
MP2027 Manager - IT Simulation Parser (システム課金)
Parses IT Simulation .xls files for the given fiscal year.
"""
import pandas as pd
import sqlite3
import os
from src.utils.excel_helpers import safe_float, extract_cc_code, get_fy_months

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

def parse_it_sim_file(path: str, target_months: list) -> list:
    """Parse a single IT Simulation .xls file."""
    records = []
    try:
        # Use xlrd for .xls files
        df = pd.read_excel(path, sheet_name='部門別サマリー(VND)', header=None, engine='xlrd')
    except Exception as e:
        print(f"⚠️ Cannot open {os.path.basename(path)}: {e}")
        return records

    if len(df) <= 2:
        return records
        
    system_headers = []
    header_row = 1
    for c in range(3, min(15, len(df.columns))):
        val = str(df.iloc[header_row, c]).strip()
        if '(VND)' in val and val != '課金振替額（VND）':
            system_name = val.replace('(VND)', '').strip()
            system_headers.append((c, system_name))
            
    if not system_headers:
        for c in range(3, 11):
            if c < len(df.columns):
                system_headers.append((c, f'System_{c}'))

    for r in range(2, len(df)):
        cc_val = df.iloc[r, 1]
        cc_code = extract_cc_code(cc_val)
        if not cc_code:
            continue
            
        for col_idx, sys_name in system_headers:
            amount = safe_float(df.iloc[r, col_idx])
            if amount <= 0:
                continue
                
            for month in target_months:
                records.append({
                    'cc_code': cc_code,
                    'period': month,
                    'amount_vnd': amount,
                    'source': 'it_sim',
                    'description': sys_name
                })
    return records

def parse_it_simulation(conn: sqlite3.Connection, source_dir: str = None) -> dict:
    """Discover and parse IT Simulation files."""
    fy_row = conn.execute("SELECT value FROM sys_params WHERE key='fiscal_year'").fetchone()
    fy_str = fy_row[0] if fy_row else "FY2027"
    fy_int = int(fy_str.replace('FY', ''))
    fy_months = get_fy_months(fy_int)
    
    # Months ranges for the 3 files typical structure:
    # 1: Apr-Jun, 2: Jul-Dec, 3: Jan-Mar
    ranges = [
        (fy_months[0:3], ["Apr", "June"]),
        (fy_months[3:9], ["July", "Dec"]),
        (fy_months[9:12], ["Jan", "March"])
    ]

    search_dir = source_dir or BASE_DIR
    files_to_parse = []
    
    # Smart discovery in search_dir
    all_files = os.listdir(search_dir)
    for months, keywords in ranges:
        found = False
        for f in all_files:
            if 'システム課金' in f and f.endswith('.xls'):
                # Basic check: does it match the year and one of the keywords?
                if str(fy_int) in f or str(fy_int-1) in f:
                    if any(k.lower() in f.lower() for k in keywords):
                        files_to_parse.append((os.path.join(search_dir, f), months))
                        found = True
                        break
        if not found:
             print(f"ℹ️ Could not find IT Sim file for {keywords}")

    cursor = conn.cursor()
    total = 0
    results = {}

    for path, months in files_to_parse:
        records = parse_it_sim_file(path, months)
        for rec in records:
            cursor.execute("""
                INSERT INTO fact_input_data
                (source, period, amount_vnd, cc_code, account_code, scenario_id, description)
                VALUES ('it_sim', ?, ?, ?, 0, 'base', ?)
            """, (rec['period'], rec['amount_vnd'], rec['cc_code'], f"it_sim|{rec['description']}"))
            total += 1
        results[os.path.basename(path)[:30]] = len(records)

    conn.commit()
    results['total'] = total
    print(f"✅ IT Simulation total: {total} records.")
    return results
