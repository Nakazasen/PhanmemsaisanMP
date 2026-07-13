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
from datetime import date, datetime
from src.utils.excel_helpers import safe_float, extract_cc_code, get_fy_months
from src.utils.source_manifest import resolve_manifest_file

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

SOURCE_SPECS = {
    '減価償却費（Depreciation）': {
        'currency': 'USD',
        'items': {
            '建物 Building': 'depreciation_building',
            '土地 Land': 'depreciation_land',
        }
    },
    '固定資産金利（Interest）': {
        'currency': 'USD',
        'items': {
            '建物 Building': 'interest_building',
            '土地 Land': 'interest_land',
        }
    },
    '水道光熱費（Electric & Water）': {
        'currency': 'VND',
        'items': {
            '電気代 Electric': 'electric',
            '水道代 Water': 'water',
        }
    },
}

def _period(value: object) -> str | None:
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return f"{value.year:04d}{value.month:02d}"
    text = str(value or "").strip()
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None
    return f"{parsed.year:04d}{parsed.month:02d}"


def _month_columns(df: pd.DataFrame, fy_months: list[str]) -> tuple[int, dict[str, int]]:
    wanted = set(fy_months)
    candidates: list[tuple[int, dict[str, int]]] = []
    for row_index, row in df.iterrows():
        columns: dict[str, int] = {}
        for column, value in enumerate(row.tolist()):
            period = _period(value)
            if period in wanted and period not in columns:
                columns[period] = column
        if set(columns) == wanted:
            candidates.append((int(row_index), columns))
    if len(candidates) != 1:
        raise ValueError(f"Facility sheet phải có đúng một dòng tiêu đề 12 tháng; tìm thấy {len(candidates)}.")
    return candidates[0]


def _item_key(row: pd.Series, spec: dict, first_month_col: int) -> str | None:
    text = " ".join(str(value) for value in row.iloc[:first_month_col] if not pd.isna(value))
    matches = {key for label, key in spec["items"].items() if label in text}
    if len(matches) > 1:
        raise ValueError(f"Facility row có nhiều mã hạng mục: {sorted(matches)}")
    return next(iter(matches), None)


def _cc_before_month(row: pd.Series, first_month_col: int) -> str | None:
    matches = {
        str(code)
        for value in row.iloc[:first_month_col]
        for code in (extract_cc_code(value),)
        if code
    }
    if len(matches) > 1:
        raise ValueError(f"Facility row có nhiều Cost Center: {sorted(matches)}")
    return next(iter(matches), None)


def parse_facility_sheet(df: pd.DataFrame, spec: dict, fy_months: list[str]) -> list[dict]:
    """Parse by semantic item labels and fiscal-month headers only."""
    header_row, month_columns = _month_columns(df, fy_months)
    first_month_col = min(month_columns.values())
    records: list[dict] = []
    for row_index in range(header_row + 1, len(df)):
        row = df.iloc[row_index]
        item_key = _item_key(row, spec, first_month_col)
        if not item_key:
            continue
        cc_code = _cc_before_month(row, first_month_col)
        if not cc_code and row_index + 1 < len(df):
            cc_code = _cc_before_month(df.iloc[row_index + 1], first_month_col)
        if not cc_code:
            continue
        for item_order, period in enumerate(fy_months, start=1):
            amount = safe_float(row.iloc[month_columns[period]])
            if amount == 0.0:
                continue
            records.append({
                'cc_code': cc_code,
                'period': period,
                'amount': amount,
                'currency': spec['currency'],
                'item_type': item_key,
                'source_row': row_index + 1,
                'item_order': row_index * len(fy_months) + item_order,
            })
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
    path = manifest_path
    print(f"Đang mở tệp Cơ sở vật chất: {path}")
    if not path or not os.path.exists(path):
        print(f"Cảnh báo: manifest không có tệp Cơ sở vật chất hợp lệ trong {search_dir}")
        return {'total': 0}

    results = {}
    cursor = conn.cursor()
    total = 0

    xl = pd.ExcelFile(path, engine='openpyxl')
    for sheet_name, config in SOURCE_SPECS.items():
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
                 scenario_id, description, source_group, source_file, source_sheet,
                 source_row, item_key, item_order)
                VALUES (?, ?, ?, ?, ?, ?, 'base', ?, 'facility', ?, ?, ?, ?, ?)
            """, (
                'facility',
                rec['period'],
                round(amount_vnd),
                amount_usd,
                rec['cc_code'],
                0,
                rec['item_type'],
                os.path.basename(path),
                target_sheet,
                rec['source_row'],
                f"facility:{rec['item_type']}",
                rec['item_order'],
            ))
            total += 1
        results[sheet_name] = len(records)

    conn.commit()
    results['total'] = total
    print(f"Cơ sở vật chất: đã thêm {total} bản ghi.")
    return results
