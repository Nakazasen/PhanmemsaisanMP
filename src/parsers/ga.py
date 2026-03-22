"""
MP2027 Manager - GA Parser (総務課)
Parses 総務課 FY[Year] MP 振替予定.xlsx to extract:
  - Per-person costs: Gas, hand soap, toilet paper, cleaning (一人当たり)
  - Working days and headcount data from 振替計算 sheet
"""
import pandas as pd
import sqlite3
import os
from src.utils.excel_helpers import safe_float, get_fy_months

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

def parse_ga_main_sheet(df: pd.DataFrame, fy_months: list) -> list:
    """Parse the main allocation sheet (per-person allocation costs)."""
    records = []
    header_row = None
    for i in range(min(15, len(df))):
        val = df.iloc[i, 0]
        if not pd.isna(val) and '項目' in str(val):
            header_row = i
            break

    if header_row is None:
        return records

    data_start = header_row + 1
    for i in range(data_start, len(df)):
        row = df.iloc[i]
        item_name = str(row.iloc[0]).strip() if not pd.isna(row.iloc[0]) else ''
        if not item_name or '合計' in item_name:
            continue

        basis = str(row.iloc[14]).strip() if len(row) > 14 and not pd.isna(row.iloc[14]) else ''
        driver = 'headcount_per_person'
        if '稼働日' in basis or '日数' in basis:
            driver = 'working_days'

        for m in range(12):
            col_idx = m + 1
            if col_idx >= len(row):
                continue
            amount = safe_float(row.iloc[col_idx])
            if amount == 0.0:
                continue

            records.append({
                'period': fy_months[m],
                'amount_per_unit': amount,
                'item_name': item_name,
                'driver': driver,
                'source': 'ga',
            })
    return records

def parse_ga_calculation_sheet(df: pd.DataFrame, fy_months: list) -> dict:
    """Parse 振替計算 sheet to get working days and headcount per month."""
    result = {'working_days': {}, 'headcount': {}}
    for i in range(len(df)):
        val = df.iloc[i, 1] if len(df.columns) > 1 and not pd.isna(df.iloc[i, 1]) else ''
        s = str(val)

        if '稼働日' in s or 'ngày làm' in s.lower():
            for m in range(12):
                col_idx = m + 2
                if col_idx < len(df.columns):
                    days = safe_float(df.iloc[i, col_idx])
                    if days > 0:
                        result['working_days'][fy_months[m]] = int(days)

        elif '人員数' in s or 'Số người' in s:
            for m in range(12):
                col_idx = m + 2
                if col_idx < len(df.columns):
                    hc = safe_float(df.iloc[i, col_idx])
                    if hc > 0:
                        result['headcount'][fy_months[m]] = int(hc)
    return result

def parse_ga(conn: sqlite3.Connection, source_dir: str = None) -> dict:
    """Parse GA file and insert data into database."""
    fy_row = conn.execute("SELECT value FROM sys_params WHERE key='fiscal_year'").fetchone()
    fy_str = fy_row[0] if fy_row else "FY2027"
    fy_int = int(fy_str.replace('FY', ''))
    fy_months = get_fy_months(fy_int)

    search_dir = source_dir or BASE_DIR
    path = os.path.join(search_dir, f'総務課 {fy_str} MP 振替予定.xlsx')
    
    if not os.path.exists(path):
        # Try finding any GA file in search_dir
        for f in os.listdir(search_dir):
            if '総務課' in f and '振替予定' in f:
                path = os.path.join(search_dir, f)
                break
        
    if not path or not os.path.exists(path):
        print(f"⚠️ GA file not found: {path} in {search_dir}")
        return {'total': 0}

    xl = pd.ExcelFile(path, engine='openpyxl')
    results = {}
    cursor = conn.cursor()
    total = 0

    main_sheet = xl.sheet_names[0]
    df_main = pd.read_excel(path, sheet_name=main_sheet, header=None, engine='openpyxl')
    per_person_records = parse_ga_main_sheet(df_main, fy_months)
    results['per_person_items'] = len(per_person_records)

    calc_data = {'working_days': {}, 'headcount': {}}
    for sname in xl.sheet_names:
        if '計算' in sname or '振替' in sname:
            df_calc = pd.read_excel(path, sheet_name=sname, header=None, engine='openpyxl')
            calc_data = parse_ga_calculation_sheet(df_calc, fy_months)
            break

    for period, days in calc_data['working_days'].items():
        cursor.execute("INSERT OR REPLACE INTO sys_params (key, value, description) VALUES (?, ?, ?)",
                       (f'working_days_{period}', str(days), f'Working days for {period}'))
    for period, hc in calc_data['headcount'].items():
        cursor.execute("INSERT OR REPLACE INTO sys_params (key, value, description) VALUES (?, ?, ?)",
                       (f'headcount_total_{period}', str(hc), f'Total headcount for {period}'))

    for rec in per_person_records:
        cursor.execute("""
            INSERT INTO fact_input_data
            (source, period, amount_vnd, cc_code, account_code, scenario_id, description)
            VALUES ('ga_unit_price', ?, ?, 0, 0, 'base', ?)
        """, (rec['period'], rec['amount_per_unit'], f"{rec['item_name']}|{rec['driver']}"))
        total += 1

    conn.commit()
    results['total'] = total
    print(f"✅ GA total: {total} records.")
    return results
