"""
MP2027 Manager - Fixed Assets Parser (Refactored V4.5.0)
Processes depreciation and interest schedules with month-end logic.
"""
import sqlite3
from pathlib import Path
import openpyxl
from src.utils import excel_helpers as helpers
from src.utils.source_manifest import resolve_manifest_file

def find_fixed_assets_file(source_dir: str = None) -> str | None:
    manifest_path = resolve_manifest_file(source_dir, "fixed_assets")
    if manifest_path:
        return manifest_path

    search_dir = Path(source_dir or Path(__file__).resolve().parents[2])
    for path in search_dir.glob('*.xlsx'):
        if 'Fixed_Assets_Information' in path.name: return str(path)
    return None

def expand_depreciation_schedule(monthly_depr: float, last_month: str | None, last_month_depr: float, fy_months: list[str]) -> dict[str, float]:
    result = {}
    for period in fy_months:
        if not last_month or period < last_month: amount = monthly_depr
        elif period == last_month: amount = last_month_depr if last_month_depr > 0 else monthly_depr
        else: amount = 0.0
        if amount > 0: result[period] = amount
    return result

def expand_interest_schedule(apr_interest: float, may_interest: float, last_month: str | None, fy_months: list[str]) -> dict[str, float]:
    result = {}
    for period in fy_months:
        if last_month and period > last_month: continue
        amount = apr_interest if period == fy_months[0] else may_interest
        if amount > 0: result[period] = amount
    return result

def parse_fixed_assets(conn: sqlite3.Connection, fa_path: str = None, source_dir: str = None) -> dict:
    fpath = fa_path or find_fixed_assets_file(source_dir)
    if not fpath: return {'total': 0}
    path = Path(fpath)
    if not path.is_file(): return {'total': 0}
    
    rate_row = conn.execute("SELECT value FROM sys_params WHERE key='exchange_rate_usd_vnd'").fetchone()
    rate = float(rate_row[0]) if rate_row else 25450.0
    fy_row = conn.execute("SELECT value FROM sys_params WHERE key='fiscal_year'").fetchone()
    fy_months = helpers.get_fy_months(int((fy_row[0] if fy_row else 'FY2027').replace('FY', '')))
    
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb['2025.11'] if '2025.11' in wb.sheetnames else wb[wb.sheetnames[0]]
        cursor = conn.cursor()
        total = 0
        for row in ws.iter_rows(min_row=5, values_only=True):
            cc_code = helpers.extract_cc_code(row[7] if len(row) > 7 else None)
            if not cc_code: continue
            
            asset_no, asset_text = str(row[2] or '').strip(), str(row[3] or '').strip()
            asset_tag = f'{asset_no}|{asset_text}' if asset_text else asset_no
            monthly_depr = helpers.safe_float(row[11] if len(row) > 11 else None)
            last_month = helpers.normalize_period(row[15] if len(row) > 15 else None)
            last_month_depr = helpers.safe_float(row[16] if len(row) > 16 else None)
            apr_interest = helpers.safe_float(row[21] if len(row) > 21 else None)
            may_interest = helpers.safe_float(row[22] if len(row) > 22 else None)
            
            # Expand Depreciation
            for p, val in expand_depreciation_schedule(monthly_depr, last_month, last_month_depr, fy_months).items():
                cursor.execute("INSERT INTO fact_input_data (source, period, amount_vnd, amount_usd, cc_code, account_code, description) VALUES (?, ?, ?, ?, ?, 0, ?)",
                               ('fixed_assets', p, round(val * rate, 0), val, cc_code, f'fixed_assets_depr|{asset_tag}'))
                total += 1
            # Expand Interest
            for p, val in expand_interest_schedule(apr_interest, may_interest, last_month, fy_months).items():
                cursor.execute("INSERT INTO fact_input_data (source, period, amount_vnd, amount_usd, cc_code, account_code, description) VALUES (?, ?, ?, ?, ?, 0, ?)",
                               ('fixed_assets', p, round(val * rate, 0), val, cc_code, f'fixed_assets_interest|{asset_tag}'))
                total += 1
        conn.commit()
        return {'total': total}
    finally: wb.close()
