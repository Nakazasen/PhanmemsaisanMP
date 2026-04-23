"""
MP2027 Manager - Facility Parser (施設課)
Parses 施設課 MPFY[Year].xlsx to extract:
  - Depreciation (減価償却費) per CC in USD → convert to VND
  - Interest (固定資産金利) per CC in USD → convert to VND
  - Electricity & Water (水道光熱費) per CC in VND
"""
import pandas as pd
import sqlite3
import os
from src.utils.excel_helpers import safe_float, extract_cc_code, get_fy_months
from src.utils.source_manifest import resolve_manifest_file

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

SHEET_CONFIG = {
    '減価償却費（Depreciation）': {
        'currency': 'USD',
        'header_row': 2,
        'data_start': 6,
        'cc_name_col': 1,
        'cc_code_col': 1,
        'type_col': 2,
        'month_start_col': 3,
        'items': {
            '建物 Building': 'depreciation_building',
            '土地 Land': 'depreciation_land',
        }
    },
    '固定資産金利（Interest）': {
        'currency': 'USD',
        'header_row': 2,
        'data_start': 6,
        'cc_name_col': 1,
        'cc_code_col': 1,
        'type_col': 2,
        'month_start_col': 3,
        'items': {
            '建物 Building': 'interest_building',
            '土地 Land': 'interest_land',
        }
    },
    '水道光熱費（Electric & Water）': {
        'currency': 'VND',
        'header_row': 2,
        'data_start': 6,
        'cc_name_col': 1,
        'cc_code_col': 1,
        'type_col': 2,
        'month_start_col': 3,
        'items': {
            '電気代 Electric': 'electric',
            '水道代 Water': 'water',
        }
    },
}

def parse_facility_sheet(df: pd.DataFrame, config: dict, fy_months: list) -> list:
    """Parse a facility sheet into list of dicts."""
    records = []
    data_start = config['data_start']
    type_col = config['type_col']
    month_start = config['month_start_col']
    currency = config['currency']

    current_cc = None
    i = data_start
    while i < len(df):
        row = df.iloc[i]
        item_type = str(row.iloc[type_col]).strip() if not pd.isna(row.iloc[type_col]) else ''
        item_key = None
        for key in config['items']:
            if key in item_type:
                item_key = config['items'][key]
                break

        if not item_key:
            i += 1
            continue

        cc_code = None
        seq = row.iloc[0]
        if not pd.isna(seq):
            try:
                float(seq)
                if i + 1 < len(df):
                    next_row = df.iloc[i + 1]
                    cc_val = next_row.iloc[config['cc_code_col']]
                    cc_code = extract_cc_code(cc_val)
                    if cc_code:
                        current_cc = cc_code
            except (ValueError, TypeError):
                pass
        else:
            cc_val = row.iloc[config['cc_code_col']]
            cc_code = extract_cc_code(cc_val)
            if cc_code:
                current_cc = cc_code

        if not current_cc:
            i += 1
            continue

        for m in range(12):
            col_idx = month_start + m
            if col_idx >= len(row):
                continue
            amount = safe_float(row.iloc[col_idx])
            if amount == 0.0:
                continue
            records.append({
                'cc_code': current_cc,
                'period': fy_months[m],
                'amount': amount,
                'currency': currency,
                'item_type': item_key,
                'source': 'facility',
            })
        i += 1
    return records

def parse_facility(conn: sqlite3.Connection, source_dir: str = None) -> dict:
    """Parse all sheets from the facility file and insert into fact_input_data."""
    # Get dynamic parameters from DB
    rate_row = conn.execute("SELECT value FROM sys_params WHERE key='exchange_rate_usd_vnd'").fetchone()
    rate = float(rate_row[0]) if rate_row else 25450.0
    
    fy_row = conn.execute("SELECT value FROM sys_params WHERE key='fiscal_year'").fetchone()
    fy_str = fy_row[0] if fy_row else "FY2027"
    fy_int = int(fy_str.replace('FY', ''))
    fy_months = get_fy_months(fy_int)

    # Use source_dir if provided
    search_dir = source_dir or BASE_DIR
    manifest_path = resolve_manifest_file(search_dir, "facility")
    path = os.path.join(search_dir, f'施設課　MP{fy_str}.xlsx')
    if manifest_path:
        path = manifest_path
    print(f"Opening Facility: {path}")
    if not os.path.exists(path):
        # Try local folder
        path = f'施設課　MP{fy_str}.xlsx'
        if not os.path.exists(path):
            print(f"Warning: Facility file not found: {path} in {search_dir}")
            return {'total': 0}

    results = {}
    cursor = conn.cursor()
    total = 0

    xl = pd.ExcelFile(path, engine='openpyxl')
    for sheet_name, config in SHEET_CONFIG.items():
        target_sheet = None
        for s in xl.sheet_names:
            if sheet_name[:6] in s:
                target_sheet = s
                break
        if not target_sheet:
            continue

        df = pd.read_excel(path, sheet_name=target_sheet, header=None, engine='openpyxl')
        records = parse_facility_sheet(df, config, fy_months)

        for rec in records:
            amount_vnd = rec['amount']
            amount_usd = None
            if rec['currency'] == 'USD':
                amount_usd = rec['amount']
                amount_vnd = rec['amount'] * rate

            cursor.execute("""
                INSERT INTO fact_input_data
                (source, period, amount_vnd, amount_usd, cc_code, account_code,
                 scenario_id, description)
                VALUES (?, ?, ?, ?, ?, ?, 'base', ?)
            """, (
                'facility',
                rec['period'],
                round(amount_vnd),
                amount_usd,
                rec['cc_code'],
                0,
                rec['item_type']
            ))
            total += 1
        results[sheet_name] = len(records)

    conn.commit()
    results['total'] = total
    print(f"Facility total: {total} records inserted.")
    return results
