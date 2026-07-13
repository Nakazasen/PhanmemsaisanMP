"""Parser for FY2027 birthday-cost workbook."""

from __future__ import annotations

import sqlite3
from pathlib import Path
import unicodedata

import openpyxl

from src.engine.account_resolver import resolve_account_column_by_cost_type, resolve_cost_type_for_connection
from src.utils.excel_helpers import get_fy_months, normalize_cc_code, safe_float
from src.utils.source_manifest import resolve_manifest_file


SOURCE_NAME = "birthday_workbook"


def _normalized(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").lower())
    return "".join(char for char in text if not unicodedata.combining(char))


def _birthday_rule(conn: sqlite3.Connection):
    matches = []
    for rule in conn.execute("SELECT * FROM map_allocation_rules").fetchall():
        name = _normalized(rule["item_name"])
        if "誕生日" in name or "birthday" in name or "sinh nhat" in name:
            matches.append(rule)
    if len(matches) != 1:
        raise ValueError(f"Birthday master phải có đúng một hạng mục; tìm thấy {len(matches)}.")
    if float(matches[0]["unit_price"] or 0) <= 0:
        raise ValueError("Birthday master không có đơn giá hợp lệ.")
    return matches[0]


def _birthday_account(conn: sqlite3.Connection, rule, cc_code: str) -> int:
    cost_type = resolve_cost_type_for_connection(conn, cc_code)
    master_column = {
        "mfg_code": "mfg_account",
        "ga_code": "ga_account",
        "sales_code": "sales_account",
    }[resolve_account_column_by_cost_type(cost_type)]
    account = int(rule[master_column] or 0)
    if account <= 0:
        raise ValueError(f"Birthday master thiếu account cho CC {cc_code}.")
    return account


def find_birthday_file(source_dir: str | None = None) -> str | None:
    manifest_path = resolve_manifest_file(source_dir, "birthday")
    if manifest_path:
        return manifest_path

    search_dir = Path(source_dir or Path.cwd())
    for path in search_dir.glob("*.xlsx"):
        name = path.name.lower()
        if "sinh" in name and "nh" in name:
            return str(path)
    return None


def parse_birthday_workbook(conn: sqlite3.Connection, source_dir: str | None = None, workbook_path: str | None = None) -> dict[str, int | str]:
    """Load birthday workbook amounts without assigning a FORM row."""
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
    birthday_rule = _birthday_rule(conn)
    unit_price_vnd = float(birthday_rule["unit_price"])

    inserted = 0
    skipped = 0
    errors = 0

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb["Sinh nhật MP FY2027"] if "Sinh nhật MP FY2027" in wb.sheetnames else wb[wb.sheetnames[0]]
        for source_row, row in enumerate(ws.iter_rows(min_row=4, values_only=True), start=4):
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
                amount = count * unit_price_vnd
                count_text = str(int(round(count))) if abs(count - round(count)) < 1e-9 else str(count)
                cursor.execute(
                    """
                    INSERT INTO fact_input_data
                    (source, period, amount_vnd, cc_code, account_code, scenario_id, description,
                     source_group, source_file, source_sheet, source_row, item_key, item_order)
                    VALUES (?, ?, ?, ?, ?, 'base', ?, 'birthday', ?, ?, ?, 'birthday', ?)
                    """,
                    (
                        SOURCE_NAME,
                        period,
                        amount,
                        cc_code,
                        _birthday_account(conn, birthday_rule, cc_code),
                        f"Birthday workbook: {cc_name}|formula_expr={count_text}*{unit_price_vnd:g}",
                        Path(path).name,
                        ws.title,
                        source_row,
                        source_row,
                    ),
                )
                inserted += 1
    finally:
        wb.close()

    conn.commit()
    return {"inserted": inserted, "skipped": skipped, "errors": errors, "path": str(path)}
