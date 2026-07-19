"""
MP2027 Manager - Database Schema (Refactored V4.5.0)
"""
import os
import sqlite3
import sys

from src.db.migrations import run_migrations

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(BASE_DIR, "mp2027.db")


def _default_database_path() -> str:
    runtime_root = os.environ.get("MP_MANAGER_RUNTIME_ROOT")
    if runtime_root:
        return os.path.join(os.path.abspath(runtime_root), "mp2027.db")
    if getattr(sys, "frozen", False):
        user_root = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".mp_manager")
        return os.path.join(os.path.abspath(user_root), "MPManager", "Projects", "MP2027", "mp2027.db")
    return DB_PATH


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(str(row[1]) == column_name for row in rows)


def _column_type(conn: sqlite3.Connection, table_name: str, column_name: str) -> str | None:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    for row in rows:
        if str(row[1]) == column_name:
            return str(row[2] or "").upper()
    return None


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    path = os.path.abspath(db_path or _default_database_path())
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn

def create_schema(conn: sqlite3.Connection) -> None:
    # Keep the historical callable API, but make all compatibility changes
    # versioned, backed up where needed, and transactional.
    run_migrations(
        conn,
        application_version=os.environ.get("MP_MANAGER_VERSION", "unversioned"),
    )
    cursor = conn.cursor()

    # Basic Dimension Tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dim_cost_centers (
            code TEXT PRIMARY KEY, name_jp TEXT NOT NULL, name_vn TEXT,
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
            id INTEGER PRIMARY KEY AUTOINCREMENT, period TEXT NOT NULL, cc_code TEXT NOT NULL,
            headcount_all REAL DEFAULT 0, headcount_expat REAL DEFAULT 0,
            headcount_staff REAL DEFAULT 0, headcount_worker REAL DEFAULT 0,
            headcount_male REAL DEFAULT 0, headcount_female REAL DEFAULT 0,
            split_status TEXT DEFAULT "READY", headcount_local_total REAL,
            source TEXT DEFAULT "hr", description TEXT, source_file TEXT, source_sheet TEXT,
            imported_at TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(period, cc_code, source)
        )''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fact_headcount_time_source (
            period TEXT NOT NULL, cc_code TEXT NOT NULL,
            fixed_hours_expat REAL DEFAULT 0, fixed_hours_local REAL DEFAULT 0,
            overtime_hours_expat REAL DEFAULT 0, overtime_hours_local REAL DEFAULT 0,
            source_file TEXT, source_sheet TEXT, source_cells TEXT,
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(period, cc_code)
        )''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fact_bus_headcount_drivers (
            cc_code TEXT PRIMARY KEY,
            fiscal_year INTEGER NOT NULL DEFAULT 0,
            bus_expat_count REAL DEFAULT 0,
            bus_vietnamese_count REAL DEFAULT 0,
            source TEXT DEFAULT "manual",
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fact_manual_headcount_baseline_override (
            period TEXT NOT NULL, cc_code TEXT NOT NULL, fiscal_year INTEGER NOT NULL DEFAULT 0,
            headcount_all REAL DEFAULT 0, headcount_expat REAL DEFAULT 0,
            headcount_staff REAL DEFAULT 0, headcount_worker REAL DEFAULT 0,
            headcount_male REAL DEFAULT 0, headcount_female REAL DEFAULT 0,
            split_status TEXT DEFAULT "READY", headcount_local_total REAL,
            description TEXT, source_file TEXT, source_sheet TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(period, cc_code)
        )''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fact_manual_headcount_time_override (
            period TEXT NOT NULL, cc_code TEXT NOT NULL, fiscal_year INTEGER NOT NULL DEFAULT 0,
            fixed_hours_expat REAL DEFAULT 0, fixed_hours_local REAL DEFAULT 0,
            overtime_hours_expat REAL DEFAULT 0, overtime_hours_local REAL DEFAULT 0,
            description TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(period, cc_code)
        )''')

    # Fact Tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fact_input_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL, period TEXT NOT NULL,
            amount_vnd REAL NOT NULL DEFAULT 0, amount_usd REAL DEFAULT NULL, cc_code INTEGER NOT NULL,
            account_code INTEGER NOT NULL, form_row INTEGER DEFAULT NULL,
            fiscal_year INTEGER DEFAULT NULL, source_snapshot TEXT DEFAULT NULL,
            scenario_id TEXT DEFAULT 'base', description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fact_allocation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, rule_id INTEGER NOT NULL, dest_cc TEXT NOT NULL,
            period TEXT NOT NULL, amount_vnd REAL NOT NULL, account_code INTEGER NOT NULL,
            driver_value REAL NOT NULL, driver_total REAL NOT NULL, step INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (rule_id) REFERENCES map_allocation_rules(id),
            FOREIGN KEY (dest_cc) REFERENCES dim_cost_centers(code)
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fact_missing_inputs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            severity TEXT NOT NULL DEFAULT 'action',
            cc_code TEXT,
            period TEXT,
            area TEXT NOT NULL,
            message TEXT NOT NULL,
            action TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'system',
            rule_id INTEGER DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_headcount_source_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fiscal_year INTEGER NOT NULL,
            source_file TEXT NOT NULL,
            cc_code TEXT NOT NULL,
            displayed_name TEXT,
            name_jp TEXT,
            name_vn TEXT,
            decision TEXT NOT NULL,
            reason TEXT NOT NULL,
            decided_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_uniform_cup_calculation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fiscal_year INTEGER NOT NULL,
            cc_code TEXT NOT NULL,
            period TEXT NOT NULL,
            item_key TEXT NOT NULL,
            item_name TEXT NOT NULL,
            release_type TEXT NOT NULL,
            source_periods TEXT,
            new_staff REAL NOT NULL DEFAULT 0,
            new_worker REAL NOT NULL DEFAULT 0,
            total_new_hires REAL NOT NULL DEFAULT 0,
            issue_quantity REAL NOT NULL DEFAULT 0,
            unit_price REAL NOT NULL DEFAULT 0,
            amount_vnd REAL NOT NULL DEFAULT 0,
            account_code INTEGER,
            rule_id INTEGER,
            entitlement_source_file TEXT,
            entitlement_source_sheet TEXT,
            entitlement_source_cell TEXT,
            formula_expr TEXT,
            status TEXT NOT NULL DEFAULT 'OK',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS map_cost_center_uniform_items (
            cc_code TEXT NOT NULL,
            item_key TEXT NOT NULL,
            item_name TEXT NOT NULL,
            eligible INTEGER NOT NULL DEFAULT 0 CHECK (eligible IN (0, 1)),
            source_file TEXT NOT NULL,
            source_sheet TEXT NOT NULL,
            source_cell TEXT NOT NULL,
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (cc_code, item_key)
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_fixed_asset_import_rows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fiscal_year INTEGER NOT NULL,
            source_snapshot TEXT NOT NULL,
            source_file TEXT NOT NULL,
            source_sheet TEXT NOT NULL,
            source_row INTEGER NOT NULL,
            asset_no TEXT,
            asset_text TEXT,
            category_raw TEXT,
            category_key TEXT,
            control_cc TEXT,
            depreciation_cc TEXT,
            monthly_depr_usd REAL,
            terminal_period TEXT,
            terminal_depr_usd REAL,
            apr_interest_usd REAL,
            may_interest_usd REAL,
            formula_cache_status TEXT NOT NULL,
            inclusion_status TEXT NOT NULL,
            exclusion_reason TEXT,
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_fixed_asset_mismatch_runs (
            run_id TEXT PRIMARY KEY,
            audit_date TEXT NOT NULL,
            executed_at TEXT NOT NULL,
            matrix_sha256 TEXT NOT NULL,
            matrix_csv_path TEXT NOT NULL,
            matrix_report_path TEXT NOT NULL,
            history_snapshot_dir TEXT NOT NULL,
            summary_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_fixed_asset_mismatch_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            fiscal_year INTEGER NOT NULL,
            cc_code TEXT NOT NULL,
            account_code INTEGER NOT NULL,
            period TEXT NOT NULL,
            expected_vnd INTEGER,
            reference_vnd INTEGER,
            delta_vnd INTEGER,
            reference_formula_kind TEXT,
            source_asset_count INTEGER NOT NULL,
            evidence_classification TEXT NOT NULL,
            decision_status TEXT NOT NULL,
            allowed_action TEXT NOT NULL,
            classification_reason TEXT NOT NULL,
            source_evidence_json TEXT NOT NULL,
            reference_evidence_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(run_id, fiscal_year, cc_code, account_code, period),
            FOREIGN KEY (run_id) REFERENCES audit_fixed_asset_mismatch_runs(run_id)
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sys_params (
            key TEXT PRIMARY KEY, value TEXT NOT NULL, description TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_input_period ON fact_input_data(period)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hc_period_cc ON fact_monthly_headcount(period, cc_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bus_hc_cc ON fact_bus_headcount_drivers(cc_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_manual_hc_baseline_cc ON fact_manual_headcount_baseline_override(cc_code, period)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_manual_hc_time_cc ON fact_manual_headcount_time_override(cc_code, period)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_missing_inputs_source ON fact_missing_inputs(source, cc_code, period)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_uniform_items_eligible "
        "ON map_cost_center_uniform_items(cc_code, eligible, item_key)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_uniform_cup_audit_lookup "
        "ON audit_uniform_cup_calculation(fiscal_year, cc_code, period, item_key)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_fixed_asset_audit_snapshot "
        "ON audit_fixed_asset_import_rows(fiscal_year, source_snapshot, source_sheet, source_row)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_fixed_asset_mismatch_history_lookup "
        "ON audit_fixed_asset_mismatch_history(fiscal_year, cc_code, account_code, period)"
    )

    for column_name, definition in (
        ("headcount_male", "REAL DEFAULT 0"),
        ("headcount_female", "REAL DEFAULT 0"),
        ("headcount_expat", "REAL DEFAULT 0"),
        ("source_file", "TEXT"),
        ("source_sheet", "TEXT"),
        ("imported_at", "TIMESTAMP"),
        ("split_status", "TEXT DEFAULT 'READY'"),
        ("headcount_local_total", "REAL"),
    ):
        if not _column_exists(conn, "fact_monthly_headcount", column_name):
            cursor.execute(f"ALTER TABLE fact_monthly_headcount ADD COLUMN {column_name} {definition}")
    for table_name in (
        "fact_bus_headcount_drivers",
        "fact_manual_headcount_baseline_override",
        "fact_manual_headcount_time_override",
    ):
        if not _column_exists(conn, table_name, "fiscal_year"):
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN fiscal_year INTEGER NOT NULL DEFAULT 0")
    if not _column_exists(conn, "fact_input_data", "form_row"):
        cursor.execute("ALTER TABLE fact_input_data ADD COLUMN form_row INTEGER DEFAULT NULL")
    if not _column_exists(conn, "fact_input_data", "fiscal_year"):
        cursor.execute("ALTER TABLE fact_input_data ADD COLUMN fiscal_year INTEGER DEFAULT NULL")
    if not _column_exists(conn, "fact_input_data", "source_snapshot"):
        cursor.execute("ALTER TABLE fact_input_data ADD COLUMN source_snapshot TEXT DEFAULT NULL")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_input_source_fy ON fact_input_data(source, fiscal_year)"
    )

    conn.commit()

def init_sys_params(
    conn: sqlite3.Connection,
    exchange_rate: float | None = None,
    fiscal_year: int = 2027,
    exchange_rate_source: str = "FORM B2",
) -> None:
    start_year = fiscal_year - 1
    params = [
        ('fiscal_year', f'FY{fiscal_year}', 'Current fiscal year (Apr-Mar)'),
        ('fy_start', f'{start_year}04', 'Fiscal year start period (YYYYMM)'),
        ('fy_end', f'{fiscal_year}03', 'Fiscal year end period (YYYYMM)'),
    ]
    if exchange_rate is not None:
        params.insert(0, ('exchange_rate_usd_vnd', str(float(exchange_rate)), f'USD/VND effective rate from {exchange_rate_source}'))
        params.insert(1, ('exchange_rate_source', str(exchange_rate_source), 'Authority for the effective USD/VND rate'))
    cursor = conn.cursor()
    for key, value, desc in params:
        cursor.execute("INSERT OR REPLACE INTO sys_params (key, value, description, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)", (key, value, desc))
    conn.commit()
