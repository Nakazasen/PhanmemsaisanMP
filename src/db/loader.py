"""
MP2027 Manager - Master Data Loader
Loads Cost Centers, Accounts, and Allocation Rules from source Excel files.
"""
import sqlite3
import os
import pandas as pd
from src.db.schema import get_connection, create_schema, init_sys_params
from src.utils.excel_helpers import read_exchange_rate_from_form

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# Source file paths
FORM_PATH = os.path.join(BASE_DIR, 'FORM.xlsx')
ALLOC_PATH = os.path.join(BASE_DIR, 'FY2027配賦額一覧 (2025.12.29).xlsx')


def _classify_driver(raw_text: str) -> str:
    """Classify allocation driver from raw Japanese/Vietnamese text."""
    if not raw_text or pd.isna(raw_text):
        return 'unknown'
    text = str(raw_text).strip()
    if 'G7社員' in text or '公nhân' in text.lower() or 'công nhân' in text.lower():
        return 'headcount_worker'
    elif 'スタッフ' in text or 'nhân viên' in text.lower():
        return 'headcount_staff'
    elif '配属人数' in text or '人数' in text or 'số người' in text.lower():
        return 'headcount_all'
    elif '稼働日数' in text or 'ngày' in text.lower():
        return 'working_days'
    elif '固定' in text or 'tỷ lệ' in text.lower():
        return 'fixed_ratio'
    else:
        return 'headcount_all'  # Default fallback


def load_cost_centers(conn: sqlite3.Connection, form_path: str = None) -> int:
    """Load cost centers from FORM.xlsx 原価センタ sheet."""
    path = form_path or FORM_PATH
    if not os.path.exists(path):
        print(f"⚠️ FORM.xlsx not found at {path}")
        return 0

    xl = pd.ExcelFile(path, engine='openpyxl')
    # Find the cost center sheet (原価センタ)
    cc_sheet = None
    for name in xl.sheet_names:
        if '原価' in name or 'センタ' in name or 'cost' in name.lower():
            cc_sheet = name
            break

    if not cc_sheet:
        # Fall back to known index from extract_samples.py (index 5)
        if len(xl.sheet_names) > 5:
            cc_sheet = xl.sheet_names[5]
            print(f"Info: Using sheet by index: {cc_sheet}")
        else:
            print("Warning: Cost center sheet not found")
            return 0

    print(f"Reading cost centers from sheet: {cc_sheet}")
    df = pd.read_excel(path, sheet_name=cc_sheet, engine='openpyxl')

    cursor = conn.cursor()
    count = 0
    for _, row in df.iterrows():
        code = row.iloc[0]  # Unnamed: 0 = code
        if pd.isna(code):
            continue
        try:
            code = int(float(code))
        except (ValueError, TypeError):
            continue

        name_jp = str(row.iloc[1]).strip() if not pd.isna(row.iloc[1]) else ''
        seq_no = float(row.iloc[2]) if not pd.isna(row.iloc[2]) else None
        saisan = str(row.iloc[3]).strip() if len(row) > 3 and not pd.isna(row.iloc[3]) else ''
        cost_type = str(row.iloc[4]).strip() if len(row) > 4 and not pd.isna(row.iloc[4]) else ''

        if not name_jp:
            continue

        cursor.execute("""
            INSERT OR REPLACE INTO dim_cost_centers
            (code, name_jp, seq_no, saisan_type, cost_type)
            VALUES (?, ?, ?, ?, ?)
        """, (code, name_jp, seq_no, saisan, cost_type))
        count += 1

    conn.commit()
    print(f"Loaded {count} cost centers.")
    return count


def load_accounts(conn: sqlite3.Connection, form_path: str = None) -> int:
    """Load accounts from FORM.xlsx 勘定科目 sheet."""
    path = form_path or FORM_PATH
    if not os.path.exists(path):
        return 0

    xl = pd.ExcelFile(path, engine='openpyxl')
    # Find the account sheet (勘定科目)
    acc_sheet = None
    for name in xl.sheet_names:
        if '勘定' in name or '科目' in name:
            acc_sheet = name
            break

    if not acc_sheet:
        if len(xl.sheet_names) > 4:
            acc_sheet = xl.sheet_names[4]
            print(f" Using sheet by index: {acc_sheet}")
        else:
            print("Warning: Account sheet not found")
            return 0

    print(f" Reading accounts from sheet: {acc_sheet}")
    df = pd.read_excel(path, sheet_name=acc_sheet, engine='openpyxl')

    cursor = conn.cursor()
    count = 0
    for _, row in df.iterrows():
        code = row.get('Account_Code', row.iloc[0] if len(row) > 0 else None)
        if pd.isna(code):
            continue
        try:
            code = int(float(code))
        except (ValueError, TypeError):
            continue

        name_jp = str(row.iloc[1]).strip() if len(row) > 1 and not pd.isna(row.iloc[1]) else ''
        name_vn = str(row.iloc[2]).strip() if len(row) > 2 and not pd.isna(row.iloc[2]) else None
        group_name = str(row.iloc[3]).strip() if len(row) > 3 and not pd.isna(row.iloc[3]) else None
        group_vn = str(row.iloc[4]).strip() if len(row) > 4 and not pd.isna(row.iloc[4]) else None

        # 製造/一般/販売 codes (columns 5, 6, 7)
        mfg_code = None
        ga_code = None
        sales_code = None
        if len(row) > 5 and not pd.isna(row.iloc[5]):
            try:
                mfg_code = int(float(row.iloc[5]))
            except (ValueError, TypeError):
                pass
        if len(row) > 6 and not pd.isna(row.iloc[6]):
            try:
                ga_code = int(float(row.iloc[6]))
            except (ValueError, TypeError):
                pass
        if len(row) > 7 and not pd.isna(row.iloc[7]):
            try:
                sales_code = int(float(row.iloc[7]))
            except (ValueError, TypeError):
                pass

        remark = str(row.iloc[8]).strip() if len(row) > 8 and not pd.isna(row.iloc[8]) else None

        if not name_jp:
            continue

        cursor.execute("""
            INSERT OR REPLACE INTO dim_accounts
            (code, name_jp, name_vn, group_name, group_vn, mfg_code, ga_code, sales_code, remark)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (code, name_jp, name_vn, group_name, group_vn, mfg_code, ga_code, sales_code, remark))
        count += 1

    conn.commit()
    print(f"Loaded {count} accounts.")
    return count


def load_allocation_rules(conn: sqlite3.Connection, alloc_path: str = None) -> int:
    """Load allocation rules from FY2027配賦額一覧."""
    path = alloc_path or ALLOC_PATH
    if not os.path.exists(path):
        print(f"Warning: Allocation rules file not found at {path}")
        return 0

    print(f"Reading allocation rules from: {os.path.basename(path)}")
    xl = pd.ExcelFile(path, engine='openpyxl')
    df = pd.read_excel(path, sheet_name=xl.sheet_names[0], engine='openpyxl')

    cursor = conn.cursor()
    cursor.execute("DELETE FROM map_allocation_rules")
    count = 0
    current_dept = None

    for _, row in df.iterrows():
        # Column mapping from master data:
        # 0: 配布元 (source dept) - may be NaN for continuation rows
        # 1: 内容 (item name)
        # 2: 科目名称 (account name)
        # 3: 製造コード
        # 4: 間接コード
        # 5: 販売コード
        # 6: 計上月 (posting month)
        # 7: 単価 (unit price)
        # 8: 単位 (unit)
        # 9: 計上基準 (driver/criteria)

        dept = row.iloc[0] if not pd.isna(row.iloc[0]) else current_dept
        item = row.iloc[1] if len(row) > 1 and not pd.isna(row.iloc[1]) else None
        if not item:
            continue

        # Skip header rows
        item_str = str(item)
        if '内　容' in item_str or 'Nội dung' in item_str:
            continue

        if not pd.isna(row.iloc[0]):
            current_dept = str(row.iloc[0]).strip()

        if not current_dept:
            continue

        # Skip if no unit price or it's not a number
        unit_price = row.iloc[7] if len(row) > 7 else None
        if pd.isna(unit_price):
            continue
        try:
            unit_price = float(unit_price)
        except (ValueError, TypeError):
            continue

        account_name = str(row.iloc[2]).strip() if len(row) > 2 and not pd.isna(row.iloc[2]) else None

        def _safe_int(val):
            """Convert value to int, handling '-', empty strings, etc."""
            if pd.isna(val):
                return None
            try:
                return int(float(val))
            except (ValueError, TypeError):
                return None

        mfg_acc = _safe_int(row.iloc[3]) if len(row) > 3 else None
        ga_acc = _safe_int(row.iloc[4]) if len(row) > 4 else None
        sales_acc = _safe_int(row.iloc[5]) if len(row) > 5 else None
        posting_month = str(row.iloc[6]).strip() if len(row) > 6 and not pd.isna(row.iloc[6]) else None
        unit = str(row.iloc[8]).strip() if len(row) > 8 and not pd.isna(row.iloc[8]) else None
        driver_raw = str(row.iloc[9]).strip() if len(row) > 9 and not pd.isna(row.iloc[9]) else None

        driver_type = _classify_driver(driver_raw)

        cursor.execute("""
            INSERT INTO map_allocation_rules
            (source_dept, item_name, account_name, mfg_account, ga_account, sales_account,
             posting_month, unit_price, unit, driver_type, driver_raw)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (current_dept, item_str.strip(), account_name, mfg_acc, ga_acc, sales_acc,
              posting_month, unit_price, unit, driver_type, driver_raw))
        count += 1

    conn.commit()
    print(f"Loaded {count} allocation rules.")
    return count


def load_all(db_path: str = None, template_path: str = None, 
             rules_path: str = None, fiscal_year: int = 2027,
             exchange_rate: float = 25450.0) -> dict:
    """Load all master data into the database with dynamic configuration."""
    # Determine actual paths
    t_path = template_path or FORM_PATH
    r_path = rules_path or ALLOC_PATH

    # SSOT: Always try to read exchange rate from FORM.xlsx B2 as per Spec V4
    if os.path.exists(t_path):
        try:
            excel_rate = read_exchange_rate_from_form(t_path)
            if excel_rate > 0:
                print(f"SSOT: Using Exchange Rate from {os.path.basename(t_path)} [B2]: {excel_rate:,.0f}")
                exchange_rate = excel_rate
        except Exception as e:
            print(f"Warning: Could not read rate from B2, falling back to {exchange_rate:,.0f}. Error: {e}")

    conn = get_connection(db_path)
    # Ensure Row factory for Row-based access in loaders if needed (schema.py usually sets this)
    conn.row_factory = sqlite3.Row 
    create_schema(conn)
    
    # Initialize system params with SSOT rate
    init_sys_params(conn, exchange_rate=exchange_rate, fiscal_year=fiscal_year)
    
    # Determine actual paths
    t_path = template_path or FORM_PATH
    r_path = rules_path or ALLOC_PATH
    
    # If the rules file contains the fiscal year in its name, 
    # and we didn't get an explicit path, let's try to be smart
    if not rules_path and not os.path.exists(r_path):
        # Try finding a file like "FY2028配賦額一覧..." if current is 2027
        potential_name = ALLOC_PATH.replace('2027', str(fiscal_year))
        if os.path.exists(potential_name):
            r_path = potential_name

    results = {
        'cost_centers': load_cost_centers(conn, t_path),
        'accounts': load_accounts(conn, t_path),
        'allocation_rules': load_allocation_rules(conn, r_path),
    }

    conn.close()
    return results


if __name__ == '__main__':
    results = load_all()
    print(f"\nSummary: {results}")
