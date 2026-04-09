"""
MP2027 Manager - IT Simulation Parser.

Parses the IT Simulation .xls files for the fiscal year. The parser keeps the
summary total used by the current export and also captures per-system detail so
the exporter can rebuild formulas closer to the business workbook.
"""

from __future__ import annotations

import os
import sqlite3
import unicodedata
from collections import defaultdict

import pandas as pd

from src.utils.excel_helpers import extract_cc_code, get_fy_months, safe_float

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

SUMMARY_VND_SHEET = "部門別サマリー(VND)"
SUMMARY_USD_SHEET = "部門別サマリー (USD)"
COMPONENT_SHEETS = {
    "vpn": ("vpn", "vpn 明細"),
    "mail": ("mail", "メール"),
    "r3": ("r3", "r3"),
    "mes": ("mes", "mes"),
    "plm": ("plm", "plm"),
    "qlik_sense": ("qlik", "sense"),
    "vps": ("vps",),
    "ams": ("ams",),
}
FILE_RANGES = [
    (0, 3, ("apr", "june")),
    (3, 9, ("july", "dec")),
    (9, 12, ("jan", "march")),
]


def _normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("\n", " ").replace("\u3000", " ").strip().lower()
    return " ".join(text.split())


def _find_matching_sheet(sheet_names: list[str], tokens: tuple[str, ...]) -> str | None:
    normalized_pairs = [(name, _normalize_text(name)) for name in sheet_names]
    for name, normalized in normalized_pairs:
        if all(token in normalized for token in tokens):
            return name
    return None


def _find_header_row(df: pd.DataFrame, header_token: str) -> int | None:
    normalized_token = _normalize_text(header_token)
    for row_index in range(min(8, len(df))):
        for value in df.iloc[row_index].tolist():
            if normalized_token in _normalize_text(value):
                return row_index
    return None


def _find_header_index(df: pd.DataFrame, header_row: int, tokens: tuple[str, ...]) -> int | None:
    for col_index, value in enumerate(df.iloc[header_row].tolist()):
        normalized = _normalize_text(value)
        if all(token in normalized for token in tokens):
            return col_index
    return None


def _parse_summary_sheet(df: pd.DataFrame, target_months: list[str]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    if len(df) <= 2:
        return records

    header_row = _find_header_row(df, "原価センター")
    if header_row is None:
        header_row = 1

    cc_col = _find_header_index(df, header_row, ("原価", "センター"))
    total_vnd_col = _find_header_index(df, header_row, ("課金", "振替", "vnd"))
    if total_vnd_col is None:
        total_vnd_col = _find_header_index(df, header_row, ("課金", "vnd"))
    if cc_col is None or total_vnd_col is None:
        return records

    for row_index in range(header_row + 1, len(df)):
        cc_code = extract_cc_code(df.iloc[row_index, cc_col])
        if not cc_code:
            continue

        amount_vnd = safe_float(df.iloc[row_index, total_vnd_col])
        if amount_vnd <= 0:
            continue

        for month in target_months:
            records.append(
                {
                    "cc_code": cc_code,
                    "period": month,
                    "amount_vnd": amount_vnd,
                    "amount_usd": 0.0,
                    "source": "it_sim",
                    "description": "it_sim|system_usage_total",
                }
            )
    return records


def _parse_component_sheet(df: pd.DataFrame, component_key: str) -> dict[int, dict[str, float]]:
    header_row = _find_header_row(df, "原価センター")
    if header_row is None:
        return {}

    cc_col = _find_header_index(df, header_row, ("原価", "センター"))
    amount_usd_col = _find_header_index(df, header_row, ("課金", "usd"))
    amount_vnd_col = _find_header_index(df, header_row, ("課金", "vnd"))
    if cc_col is None:
        return {}

    aggregated: dict[int, dict[str, float]] = defaultdict(lambda: {"amount_usd": 0.0, "amount_vnd": 0.0})
    for row_index in range(header_row + 1, len(df)):
        cc_code = extract_cc_code(df.iloc[row_index, cc_col])
        if not cc_code:
            continue

        amount_usd = safe_float(df.iloc[row_index, amount_usd_col]) if amount_usd_col is not None else 0.0
        amount_vnd = safe_float(df.iloc[row_index, amount_vnd_col]) if amount_vnd_col is not None else 0.0
        if amount_usd <= 0 and amount_vnd <= 0:
            continue

        aggregated[cc_code]["amount_usd"] += amount_usd
        aggregated[cc_code]["amount_vnd"] += amount_vnd

    return aggregated


def parse_it_sim_file(path: str, target_months: list[str]) -> list[dict[str, object]]:
    """Parse a single IT Simulation .xls file."""
    records: list[dict[str, object]] = []
    try:
        excel_file = pd.ExcelFile(path, engine="xlrd")
    except Exception as exc:
        print(f"Warning: Cannot open {os.path.basename(path)}: {exc}")
        return records

    try:
        summary_sheet = _find_matching_sheet(excel_file.sheet_names, ("サマリー", "vnd"))
        if summary_sheet:
            summary_df = pd.read_excel(path, sheet_name=summary_sheet, header=None, engine="xlrd")
            records.extend(_parse_summary_sheet(summary_df, target_months))

        for component_key, tokens in COMPONENT_SHEETS.items():
            sheet_name = _find_matching_sheet(excel_file.sheet_names, tokens)
            if not sheet_name:
                continue
            component_df = pd.read_excel(path, sheet_name=sheet_name, header=None, engine="xlrd")
            aggregated = _parse_component_sheet(component_df, component_key)
            for cc_code, amounts in aggregated.items():
                for month in target_months:
                    records.append(
                        {
                            "cc_code": cc_code,
                            "period": month,
                            "amount_vnd": amounts["amount_vnd"],
                            "amount_usd": amounts["amount_usd"],
                            "source": "it_sim",
                            "description": f"it_sim|component|{component_key}",
                        }
                    )
    finally:
        excel_file.close()

    return records


def parse_it_simulation(conn: sqlite3.Connection, source_dir: str | None = None) -> dict[str, int]:
    """Discover and parse IT Simulation files."""
    fy_row = conn.execute("SELECT value FROM sys_params WHERE key='fiscal_year'").fetchone()
    fy_str = fy_row[0] if fy_row else "FY2027"
    fy_int = int(str(fy_str).replace("FY", ""))
    fy_months = get_fy_months(fy_int)

    search_dir = source_dir or BASE_DIR
    all_files = os.listdir(search_dir)
    files_to_parse: list[tuple[str, list[str]]] = []

    for start, end, keywords in FILE_RANGES:
        months = fy_months[start:end]
        matched_path: str | None = None
        for name in all_files:
            lower_name = name.lower()
            if not lower_name.endswith(".xls") or "simulation" not in lower_name:
                continue
            if str(fy_int) not in name and str(fy_int - 1) not in name:
                continue
            if any(keyword in lower_name for keyword in keywords):
                matched_path = os.path.join(search_dir, name)
                break
        if matched_path:
            files_to_parse.append((matched_path, months))
        else:
            print(f"Info: Could not find IT Simulation file for {keywords}")

    cursor = conn.cursor()
    cursor.execute("DELETE FROM fact_input_data WHERE source = 'it_sim'")

    total = 0
    results: dict[str, int] = {}

    for path, months in files_to_parse:
        records = parse_it_sim_file(path, months)
        for record in records:
            cursor.execute(
                """
                INSERT INTO fact_input_data
                (source, period, amount_vnd, amount_usd, cc_code, account_code, scenario_id, description)
                VALUES ('it_sim', ?, ?, ?, ?, 0, 'base', ?)
                """,
                (
                    record["period"],
                    record["amount_vnd"],
                    record["amount_usd"],
                    record["cc_code"],
                    record["description"],
                ),
            )
            total += 1
        results[os.path.basename(path)[:30]] = len(records)

    conn.commit()
    results["total"] = total
    print(f"IT Simulation total: {total} records.")
    return results
