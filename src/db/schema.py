"""
MP2027 Manager - Database Schema (Refactored V4.5.0)
"""
import sqlite3
import os

import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(BASE_DIR, 'mp2027.db')

def get_connection(db_path: str = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn

def create_schema(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    # Basic Dimension Tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dim_cost_centers (
            code INTEGER PRIMARY KEY, name_jp TEXT NOT NULL, name_vn TEXT,
            seq_no REAL, saisan_type TEXT NOT NULL, cost_type TEXT NOT NULL,
            staff_count INTEGER DEFAULT 0, worker_count INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dim_accounts (
            code INTEGER PRIMARY KEY, name_jp TEXT NOT NULL, name_vn TEXT,
            group_name TEXT, group_vn TEXT, mfg_code INTEGER, ga_code INTEGER,
            sales_code INTEGER, remark TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS map_allocation_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT, source_dept TEXT NOT NULL, item_name TEXT NOT NULL,
            account_name TEXT, mfg_account INTEGER, ga_account INTEGER, sales_account INTEGER,
            posting_month TEXT, unit_price REAL NOT NULL, unit TEXT, driver_type TEXT NOT NULL,
            driver_raw TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    
    # New Monthly Helper Tables (from Refactor Patch)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fact_ga_monthly_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT, item_key TEXT NOT NULL, item_name TEXT NOT NULL,
            period TEXT NOT NULL, unit_price REAL NOT NULL, mfg_account INTEGER, ga_account INTEGER,
            sales_account INTEGER, source TEXT DEFAULT "ga", created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(item_key, period)
        )''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fact_monthly_headcount (
            id INTEGER PRIMARY KEY AUTOINCREMENT, period TEXT NOT NULL, cc_code INTEGER NOT NULL,
            headcount_all REAL DEFAULT 0, headcount_staff REAL DEFAULT 0, headcount_worker REAL DEFAULT 0,
            source TEXT DEFAULT "hr", description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(period, cc_code, source)
        )''')

    # Fact Tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fact_input_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL, period TEXT NOT NULL,
            amount_vnd REAL NOT NULL DEFAULT 0, amount_usd REAL DEFAULT NULL, cc_code INTEGER NOT NULL,
            account_code INTEGER NOT NULL, scenario_id TEXT DEFAULT 'base', description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fact_allocation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, rule_id INTEGER NOT NULL, dest_cc INTEGER NOT NULL,
            period TEXT NOT NULL, amount_vnd REAL NOT NULL, account_code INTEGER NOT NULL,
            driver_value REAL NOT NULL, driver_total REAL NOT NULL, step INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (rule_id) REFERENCES map_allocation_rules(id),
            FOREIGN KEY (dest_cc) REFERENCES dim_cost_centers(code)
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sys_params (
            key TEXT PRIMARY KEY, value TEXT NOT NULL, description TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_input_period ON fact_input_data(period)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hc_period_cc ON fact_monthly_headcount(period, cc_code)")
    conn.commit()

def init_sys_params(conn: sqlite3.Connection, exchange_rate: float | None = None, fiscal_year: int = 2027) -> None:
    start_year = fiscal_year - 1
    params = [
        ('fiscal_year', f'FY{fiscal_year}', 'Current fiscal year (Apr-Mar)'),
        ('fy_start', f'{start_year}04', 'Fiscal year start period (YYYYMM)'),
        ('fy_end', f'{fiscal_year}03', 'Fiscal year end period (YYYYMM)'),
    ]
    if exchange_rate is not None:
        params.insert(0, ('exchange_rate_usd_vnd', str(float(exchange_rate)), 'USD/VND rate from Hub B2'))
    cursor = conn.cursor()
    for key, value, desc in params:
        cursor.execute("INSERT OR REPLACE INTO sys_params (key, value, description, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)", (key, value, desc))
    conn.commit()
