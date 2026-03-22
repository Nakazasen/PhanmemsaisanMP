"""
MP2027 Manager - GA Parser (総務課)
Final refined version that handles:
1. Per-person unit costs (Gas, Soap, etc.) -> fact_input_data
2. Working days -> sys_params
3. Detailed Headcount by CC & Category (Staff/Worker) -> fact_monthly_headcount
"""
import pandas as pd
import openpyxl
import os
import sqlite3
from src.utils.excel_helpers import safe_float, get_fy_months, extract_cc_code

def parse_ga_sheet(conn, path, sheet_name, fy_months):
    """
    Parses a single calculation sheet for:
    - Working days (logged to sys_params)
    - Headcount sequences by CC (logged to fact_monthly_headcount)
    """
    try:
        df = pd.read_excel(path, sheet_name=sheet_name, header=None, engine='openpyxl')
    except:
        return 0

    recs = []
    current_cc = None
    current_category = "staff" # Default
    
    # 0. Detect Working Days (Usually near top, Col B)
    # \u7a3c\u50cd\u65e5 = 稼働日, \u9805\u76ee = 項目
    for i in range(min(20, len(df))):
        val_b = str(df.iloc[i, 1]) if len(df.columns) > 1 else ""
        if "\u7a3c\u50cd\u65e5" in val_b or "ng\u00e0y l\u00e0m" in val_b.lower():
            for m_idx in range(12):
                col_idx = m_idx + 2 # Offset by 2 (Col C onwards)
                if col_idx < len(df.columns):
                    days = safe_float(df.iloc[i, col_idx])
                    if days > 0:
                        period = fy_months[m_idx]
                        conn.execute("INSERT OR REPLACE INTO sys_params (key, value, description) VALUES (?, ?, ?)",
                                    (f'working_days_{period}', str(int(days)), f'Working days for {period}'))
            conn.commit()
            break # Usually only one working days row per sheet

    # 1. Detect Headcount sequences
    for i, row in df.iterrows():
        # CC Detection
        val_a = str(row.iloc[0]) if len(row) > 0 else ""
        cc = extract_cc_code(val_a)
        if cc:
            current_cc = cc
            continue
            
        # Category Detection (Direct vs Indirect)
        row_str = " ".join([str(c) for c in row if not pd.isna(c)]).lower()
        if 'bi\u1ebfn ph\u00ed' in row_str or 'tr\u1ef1c ti\u1ebfp' in row_str or 'direct' in row_str:
            current_category = "worker"
        elif '\u0111\u1ecbnh ph\u00ed' in row_str or 'gi\u00e1n ti\u1ebfp' in row_str or 'indirect' in row_str:
            current_category = "staff"

        # Headcount Sequence (Col C-N usually)
        vals = []
        for col_idx in range(2, 14):
            vals.append(safe_float(row.iloc[col_idx]))
            
        if current_cc and sum(vals) > 0 and any(v > 0 for v in vals):
            # item_name check to skip Totals
            item_name = str(row.iloc[0]) if not pd.isna(row.iloc[0]) else ""
            # \u5408\u8a08 = 合計
            if "\u5408\u8a08" in item_name or 'T\u1ed5ng' in item_name or 'rate' in item_name.lower():
                continue
                
            for m_idx, val in enumerate(vals):
                if val > 0:
                    recs.append((current_cc, current_category, fy_months[m_idx], val))

    if recs:
        # Aggregation and Save
        aggregated = {}
        for cc, cat, period, val in recs:
            key = (cc, cat, period)
            aggregated[key] = aggregated.get(key, 0) + val
            
        cursor = conn.cursor()
        for (cc, cat, period), val in aggregated.items():
            if cat == "staff":
                cursor.execute("""
                    INSERT INTO fact_monthly_headcount (cc_code, period, headcount_staff)
                    VALUES (?, ?, ?)
                    ON CONFLICT(cc_code, period) DO UPDATE SET headcount_staff = excluded.headcount_staff
                """, (cc, period, val))
            else:
                cursor.execute("""
                    INSERT INTO fact_monthly_headcount (cc_code, period, headcount_worker)
                    VALUES (?, ?, ?)
                    ON CONFLICT(cc_code, period) DO UPDATE SET headcount_worker = excluded.headcount_worker
                """, (cc, period, val))
        conn.commit()
    return len(recs)

def parse_ga_unit_costs(conn, path, fy_months):
    """Parses the first sheet for per-person allocation unit costs."""
    try:
        xl = pd.ExcelFile(path, engine='openpyxl')
        sheet_name = xl.sheet_names[0]
        df = pd.read_excel(path, sheet_name=sheet_name, header=None, engine='openpyxl')
    except:
        return 0

    header_row = None
    # \u9805\u76ee = 項目
    for i in range(min(20, len(df))):
        val = df.iloc[i, 0]
        if not pd.isna(val) and "\u9805\u76ee" in str(val):
            header_row = i
            break
    
    if header_row is None:
        return 0

    count = 0
    cursor = conn.cursor()
    for i in range(header_row + 1, len(df)):
        row = df.iloc[i]
        item_name = str(row.iloc[0]).strip() if not pd.isna(row.iloc[0]) else ''
        # \u5408\u8a08 = 合計
        if not item_name or "\u5408\u8a08" in item_name:
            continue

        # Basis/Driver logic
        basis = str(row.iloc[14]).strip() if len(row) > 14 and not pd.isna(row.iloc[14]) else ''
        driver = 'headcount_per_person'
        # \u7a3c\u50cd\u65e5 = 稼働日
        if "\u7a3c\u50cd\u65e5" in basis or "niss\u016b" in basis.lower():
            driver = 'working_days'

        for m_idx in range(12):
            col_idx = m_idx + 1 # Col B-M
            amount = safe_float(row.iloc[col_idx])
            if amount > 0:
                cursor.execute("""
                    INSERT INTO fact_input_data
                    (source, period, amount_vnd, cc_code, account_code, scenario_id, description)
                    VALUES ('ga_unit_price', ?, ?, 0, 0, 'base', ?)
                """, (fy_months[m_idx], amount, f"{item_name}|{driver}"))
                count += 1
    conn.commit()
    return count

def parse_ga(conn, source_dir=None):
    """Main entry for GA parsing."""
    fy_row = conn.execute("SELECT value FROM sys_params WHERE key='fiscal_year'").fetchone()
    if fy_row:
        fy_val = str(fy_row[0]).upper().replace('FY', '').strip()
        fiscal_year = int(fy_val)
    else:
        fiscal_year = 2027
    fy_months = get_fy_months(fiscal_year)
    
    # \u7dcf\u52d9\u8ab2 = 総務課, \u632f\u66ff\u4e88\u5b9a = 振替予定
    fn_prefix = "\u7dcf\u52d9\u8ab2"
    fn_suffix = "\u632f\u66ff\u4e88\u5b9a.xlsx"
    fn = f"{fn_prefix} FY{fiscal_year} MP {fn_suffix}"
    
    path = os.path.join(source_dir, fn)
    print(f"Opening GA: {path}")
    if not os.path.exists(path):
        print(f"GA File not found: {path}")
        return

    # Clear old data
    conn.execute("DELETE FROM fact_monthly_headcount")
    conn.execute("DELETE FROM fact_input_data WHERE source='ga_unit_price'")
    conn.commit()

    # 1. Parse Unit Costs (First sheet)
    unit_counts = parse_ga_unit_costs(conn, path, fy_months)
    print(f"GA Unit Costs imported: {unit_counts}")

    # 2. Parse Calculations (Headcount + Working Days)
    wb = openpyxl.load_workbook(path, read_only=True)
    # \u8a08\u7b97 = 計算, \u632f\u66ff = 振替
    target_sheets = [s for s in wb.sheetnames if "\u8a08\u7b97" in s or "\u632f\u66ff" in s]
    
    total_hc = 0
    for sn in target_sheets:
        total_hc += parse_ga_sheet(conn, path, sn, fy_months)
    
    print(f"GA Parsing Complete: {total_hc} HC points, {unit_counts} Cost items in {len(target_sheets)} sheets.")
    for sn in wb.sheetnames:
        print(f"Sheet found: {sn}")
