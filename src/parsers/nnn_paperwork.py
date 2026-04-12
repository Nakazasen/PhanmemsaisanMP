"""Parser for FY2027 foreign-worker paperwork costs."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import openpyxl

from src.utils.excel_helpers import get_fy_months, normalize_cc_code, safe_float


SOURCE_NAME = "nnn_paperwork"
FORM_ROW = 137


def _format_formula_number(value: float) -> str:
    return str(int(round(value))) if abs(value - round(value)) < 1e-9 else str(value)


def find_nnn_paperwork_file(source_dir: str | None = None) -> str | None:
    search_dir = Path(source_dir or Path.cwd())
    for path in search_dir.glob("*.xlsx"):
        name = path.name.lower()
        if "nnn" in name and "giay" in name:
            return str(path)
    for path in search_dir.glob("*.xlsx"):
        name = path.name.lower()
        if "nnn" in name:
            return str(path)
    return None


def parse_nnn_paperwork(conn: sqlite3.Connection, source_dir: str | None = None, workbook_path: str | None = None) -> dict[str, int | str]:
    """Load NNN/VISA/GPLD/Passport paperwork workbook into explicit FORM row 137."""
    fy_row = conn.execute("SELECT value FROM sys_params WHERE key='fiscal_year'").fetchone()
    fiscal_year = int(str(fy_row[0]).upper().replace("FY", "").strip()) if fy_row else 2027
    fy_months = get_fy_months(fiscal_year)
    path = workbook_path or find_nnn_paperwork_file(source_dir)
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
    formula_wb = openpyxl.load_workbook(path, read_only=True, data_only=False)
    try:
        ws = wb["FY2027"] if "FY2027" in wb.sheetnames else wb[wb.sheetnames[0]]
        formula_ws = formula_wb[ws.title]
        formula_rows = formula_ws.iter_rows(min_row=3, values_only=True)
        for row, formula_row in zip(ws.iter_rows(min_row=3, values_only=True), formula_rows):
            cc_code = normalize_cc_code(row[3] if len(row) > 3 else None)
            if not cc_code:
                skipped += 1
                continue
            if cc_code not in valid_cc_codes:
                errors += 1
                continue

            account_code = int(safe_float(row[4] if len(row) > 4 else 0))
            if account_code <= 0:
                errors += 1
                continue

            employee_code = str(row[1] or "").strip() if len(row) > 1 else ""
            employee_name = str(row[2] or "").strip() if len(row) > 2 else ""
            description = "NNN paperwork"
            if employee_code or employee_name:
                description = f"{description}: {employee_code} {employee_name}".strip()

            for offset, period in enumerate(fy_months):
                amount = safe_float(row[5 + offset] if len(row) > 5 + offset else 0)
                if amount <= 0:
                    continue
                raw_formula = formula_row[5 + offset] if len(formula_row) > 5 + offset else None
                if isinstance(raw_formula, str) and raw_formula.startswith("="):
                    formula_expr = raw_formula[1:]
                else:
                    formula_expr = _format_formula_number(amount)
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
                        account_code,
                        FORM_ROW,
                        f"{description}|formula_expr={formula_expr}",
                    ),
                )
                inserted += 1
    finally:
        wb.close()
        formula_wb.close()

    conn.commit()
    return {"inserted": inserted, "skipped": skipped, "errors": errors, "path": str(path)}
