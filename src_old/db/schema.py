"""
MP2027 Manager - Database Schema
Creates SQLite database with all tables for the Hub-centric financial planning system.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'mp2027.db')


def get_connection(db_path: str = None) -> sqlite3.Connection:
    """Get a database connection, creating the data directory if needed."""
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    """Create all tables for the MP2027 database."""
    cursor = conn.cursor()

    # 1. Dimension: Cost Centers (原価センタ)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dim_cost_centers (
            code        INTEGER PRIMARY KEY,
            name_jp     TEXT NOT NULL,
            name_vn     TEXT,
            seq_no      REAL,
            saisan_type TEXT NOT NULL,        -- 採算区分: 製造, 部内間接, 部外間接1, etc.
            cost_type   TEXT NOT NULL,        -- 原価区分: 製造, 一般, 販売
            staff_count INTEGER DEFAULT 0,   -- スタッフ headcount (office workers)
            worker_count INTEGER DEFAULT 0,  -- G7社員 headcount (production workers)
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Dimension: Accounts (勘定科目)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dim_accounts (
            code        INTEGER PRIMARY KEY,
            name_jp     TEXT NOT NULL,        -- JPN (50cha)
            name_vn     TEXT,                 -- Tiếng Việt tên tài khoản
            group_name  TEXT,                 -- JP_Name (group)
            group_vn    TEXT,                 -- Tiếng Việt hạng mục lợi nhuận
            mfg_code    INTEGER,             -- 製造コード (manufacturing account code)
            ga_code     INTEGER,             -- 一般コード (GA/indirect account code)
            sales_code  INTEGER,             -- 販売コード (sales account code)
            remark      TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. Map: Allocation Rules (配賦額一覧)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS map_allocation_rules (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            source_dept     TEXT NOT NULL,        -- 配布元 (HR, GA, etc.)
            item_name       TEXT NOT NULL,        -- 内容 (content/item description)
            account_name    TEXT,                 -- 科目名称
            mfg_account     INTEGER,             -- 製造コード
            ga_account      INTEGER,             -- 間接コード
            sales_account   INTEGER,             -- 販売コード
            posting_month   TEXT,                 -- 計上月 (入社月, 配布月, 毎月, etc.)
            unit_price      REAL NOT NULL,        -- 単価 (VND)
            unit            TEXT,                 -- 単位 (/枚, /個, /本, /冊, etc.)
            driver_type     TEXT NOT NULL,        -- 計上基準 (headcount_all, headcount_worker, headcount_staff, etc.)
            driver_raw      TEXT,                 -- Raw Japanese text for audit
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 4. Fact: Input Data Hub (内訳リスト equivalent)
    # Note: No FK constraints — parsers insert staging data with placeholder codes
    # that get mapped to real CC/Account codes during allocation phase
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fact_input_data (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            source          TEXT NOT NULL,        -- facility, ga, it_sim, allocation, etc.
            period          TEXT NOT NULL,        -- YYYYMM format (e.g. 202604 for Apr 2026)
            amount_vnd      REAL NOT NULL DEFAULT 0,
            amount_usd      REAL DEFAULT NULL,
            cc_code         INTEGER NOT NULL,
            account_code    INTEGER NOT NULL,
            scenario_id     TEXT DEFAULT 'base',  -- base, sim_1, sim_2, etc.
            description     TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 5. Fact: Allocation Log (Audit Trail)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fact_allocation_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id         INTEGER NOT NULL,
            dest_cc         INTEGER NOT NULL,
            period          TEXT NOT NULL,        -- YYYYMM
            amount_vnd      REAL NOT NULL,
            account_code    INTEGER NOT NULL,
            driver_value    REAL NOT NULL,        -- e.g. headcount of this CC
            driver_total    REAL NOT NULL,        -- e.g. total headcount across all CCs
            step            INTEGER DEFAULT 1,    -- 1 = first pass, 2 = step-down
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (rule_id) REFERENCES map_allocation_rules(id),
            FOREIGN KEY (dest_cc) REFERENCES dim_cost_centers(code)
        )
    """)

    # 6. System Parameters
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sys_params (
            key         TEXT PRIMARY KEY,
            value       TEXT NOT NULL,
            description TEXT,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_input_period ON fact_input_data(period)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_input_cc ON fact_input_data(cc_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_input_account ON fact_input_data(account_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_input_source ON fact_input_data(source)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alloc_log_rule ON fact_allocation_log(rule_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alloc_log_cc ON fact_allocation_log(dest_cc)")

    conn.commit()
    print("✅ Database schema created successfully.")


def init_sys_params(conn: sqlite3.Connection, exchange_rate: float = 25450.0,
                    fiscal_year: int = 2027) -> None:
    """Initialize system parameters with dynamic values."""
    start_year = fiscal_year - 1
    fy_start = f"{start_year}04"
    fy_end = f"{fiscal_year}03"
    
    params = [
        ('exchange_rate_usd_vnd', str(exchange_rate),
         'USD/VND exchange rate for reporting'),
        ('fiscal_year', f"FY{fiscal_year}",
         'Current fiscal year (Apr-Mar)'),
        ('fy_start', fy_start,
         'Fiscal year start period (YYYYMM)'),
        ('fy_end', fy_end,
         'Fiscal year end period (YYYYMM)'),
    ]
    cursor = conn.cursor()
    for key, value, desc in params:
        cursor.execute("""
            INSERT OR REPLACE INTO sys_params (key, value, description, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (key, value, desc))
    conn.commit()
    print(f"✅ System params initialized (rate={exchange_rate}, fy={fiscal_year}).")


if __name__ == '__main__':
    conn = get_connection()
    create_schema(conn)
    init_sys_params(conn)
    conn.close()
    print(f"📁 Database created at: {DB_PATH}")
