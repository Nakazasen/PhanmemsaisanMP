"""Parser for FY2027 birthday-cost workbook."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import openpyxl

from src.utils.excel_helpers import get_fy_months, normalize_cc_code, safe_float


SOURCE_NAME = "birthday_workbook"
FORM_ROW = 59
ACCOUNT_CODE = 5004086291
UNIT_PRICE_VND = 152000


def find_birthday_file(source_dir: str | None = None) -> str | None:
    search_dir = Path(source_dir or Path.cwd())
    for path in search_dir.glob("*.xlsx"):
        name = path.name.lower()
        if "sinh" in name and "nh" in name:
            return str(path)
    return None


def parse_birthday_workbook(conn: sqlite3.Connection, source_dir: str | None = None, workbook_path: str | None = None) -> dict[str, int | str]:
    """Load birthday workbook amounts into explicit FORM row 59."""
    fy_row = conn.execute("SELECT value FROM sys_params WHERE key='fiscal_year'").fetchone()
    fiscal_year = int(str(fy_row[0]).upper().replace("FY", "").strip()) if fy_row else 2027
    fy_months = get_fy_months(fiscal_year)
    path = workbook_path or find_birthday_file(source_dir)
    if not path or not Path(path).is_file():
        return {"inserted": 0, "skipped": 0, "errors": 0, "path": path or ""}

    valid_cc_codes = {
        str(row[0]).strip()
        for row in conn.execute("SELECT code FROM dim_cost_centers").fetchall()
        if row[0] is not None
    }
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fact_input_data WHERE source = ?", (SOURCE_NAME,))

    inserted = 0
    skipped = 0
    errors = 0

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb["Sinh nhật MP FY2027"] if "Sinh nhật MP FY2027" in wb.sheetnames else wb[wb.sheetnames[0]]
        for row in ws.iter_rows(min_row=4, values_only=True):
            cc_code = normalize_cc_code(row[0] if len(row) > 0 else None)
            if not cc_code:
                skipped += 1
                continue
            if cc_code not in valid_cc_codes:
                errors += 1
                continue

            cc_name = str(row[1] or "").strip() if len(row) > 1 else ""
            for offset, period in enumerate(fy_months):
                count = safe_float(row[2 + offset] if len(row) > 2 + offset else 0)
                if count <= 0:
                    continue
                amount = count * UNIT_PRICE_VND
                count_text = str(int(round(count))) if abs(count - round(count)) < 1e-9 else str(count)
                cursor.execute(
                    """
                    INSERT INTO fact_input_data
                    (source, period, amount_vnd, cc_code, account_code, form_row, scenario_id, description)
                    VALUES (?, ?, ?, ?, ?, ?, 'base', ?)
                    """,
                    (
                        SOURCE_NAME,
                        period,
                        amount,
                        cc_code,
                        ACCOUNT_CODE,
                        FORM_ROW,
                        f"Birthday workbook: {cc_name}|formula_expr={count_text}*{UNIT_PRICE_VND}",
                    ),
                )
                inserted += 1
    finally:
        wb.close()

    conn.commit()
    return {"inserted": inserted, "skipped": skipped, "errors": errors, "path": str(path)}
