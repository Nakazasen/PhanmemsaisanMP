"""
MP2027 Manager - IT Simulation Parser.

Parses the IT Simulation .xls files for the fiscal year. Besides the summary
total, it also captures per-system detailed terms so the exporter can rebuild
the business formula in the form `so_nguoi * don_gia`.
"""

from __future__ import annotations

import os
import sqlite3
import unicodedata
from collections import defaultdict
from urllib.parse import quote

import pandas as pd

from src.utils.excel_helpers import extract_cc_code, get_fy_months, safe_float
from src.utils.source_manifest import resolve_manifest_files

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

COMPONENT_SHEETS = {
    "vpn": ("vpn",),
    "mail": ("メール",),
    "r3": ("r3",),
    "mes": ("mes",),
    "plm": ("plm",),
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


def _metadata_parts(
    *,
    source_file: str | None = None,
    source_sheet: str | None = None,
    source_filter: str | None = None,
    audit_status: str | None = None,
    audit_diff_vnd: int | float | None = None,
) -> list[str]:
    metadata = {
        "source_file": source_file,
        "source_sheet": source_sheet,
        "source_filter": source_filter,
        "audit_status": audit_status,
        "audit_diff_vnd": audit_diff_vnd,
    }
    parts: list[str] = []
    for key, value in metadata.items():
        if value is None:
            continue
        parts.append(f"{key}={quote(str(value), safe=':-_.')}")
    return parts


def _join_description(*parts: object, metadata: list[str] | None = None) -> str:
    description_parts = [str(part) for part in parts if str(part) != ""]
    if metadata:
        description_parts.extend(metadata)
    return "|".join(description_parts)


def classify_it_summary_variance(detail_vnd: float, summary_vnd: float) -> tuple[str, int]:
    diff = int(round(float(detail_vnd or 0.0) - float(summary_vnd or 0.0)))
    if abs(diff) == 0:
        return "OK", diff
    if abs(diff) <= 5:
        return "WARN_ROUNDING", diff
    return "ERROR_REVIEW", diff


def _find_matching_sheet(sheet_names: list[str], tokens: tuple[str, ...]) -> str | None:
    normalized_pairs = [(name, _normalize_text(name)) for name in sheet_names]
    normalized_tokens = tuple(_normalize_text(token) for token in tokens)
    for name, normalized in normalized_pairs:
        if all(token in normalized for token in normalized_tokens):
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
    normalized_tokens = tuple(_normalize_text(token) for token in tokens)
    for col_index, value in enumerate(df.iloc[header_row].tolist()):
        normalized = _normalize_text(value)
        if all(token in normalized for token in normalized_tokens):
            return col_index
    return None


def _find_header_index_any(df: pd.DataFrame, header_row: int, token_groups: tuple[tuple[str, ...], ...]) -> int | None:
    for tokens in token_groups:
        found = _find_header_index(df, header_row, tokens)
        if found is not None:
            return found
    return None


def _parse_summary_sheet(
    df: pd.DataFrame,
    target_months: list[str],
    *,
    source_file: str | None = None,
    source_sheet: str | None = None,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    if len(df) <= 2:
        return records

    header_row = _find_header_row(df, "原価センター")
    if header_row is None:
        header_row = _find_header_row(df, "cost center")
    if header_row is None:
        header_row = 1

    cc_col = _find_header_index_any(df, header_row, (("原価センター",), ("cost", "center")))
    total_vnd_col = _find_header_index_any(
        df,
        header_row,
        (
            ("課金金額", "vnd"),
            ("amount", "vnd"),
        ),
    )
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
                    "description": _join_description(
                        "it_sim",
                        "system_usage_total",
                        metadata=_metadata_parts(
                            source_file=source_file,
                            source_sheet=source_sheet,
                            source_filter=f"cc:{cc_code}",
                        ),
                    ),
                }
            )
    return records


def _parse_component_sheet(
    df: pd.DataFrame,
) -> tuple[dict[int, dict[str, float]], dict[int, list[dict[str, float]]]]:
    header_row = _find_header_row(df, "原価センター")
    if header_row is None:
        header_row = _find_header_row(df, "cost center")
    if header_row is None:
        return {}, {}

    cc_col = _find_header_index_any(df, header_row, (("原価センター",), ("cost", "center")))
    amount_usd_col = _find_header_index_any(
        df,
        header_row,
        (
            ("課金金額", "usd"),
            ("amount", "usd"),
        ),
    )
    amount_vnd_col = _find_header_index_any(
        df,
        header_row,
        (
            ("課金金額", "vnd"),
            ("amount", "vnd"),
        ),
    )
    unit_price_usd_col = _find_header_index_any(
        df,
        header_row,
        (
            ("課金単価", "usd"),
            ("unit", "usd"),
        ),
    )
    usage_count_col = _find_header_index_any(
        df,
        header_row,
        (
            ("使用id数",),
            ("id数",),
            ("quantity",),
        ),
    )
    if cc_col is None:
        return {}, {}

    aggregated: dict[int, dict[str, float]] = defaultdict(lambda: {"amount_usd": 0.0, "amount_vnd": 0.0})
    term_map: dict[int, list[dict[str, float]]] = defaultdict(list)

    for row_index in range(header_row + 1, len(df)):
        cc_code = extract_cc_code(df.iloc[row_index, cc_col])
        if not cc_code:
            continue

        amount_usd = safe_float(df.iloc[row_index, amount_usd_col]) if amount_usd_col is not None else 0.0
        amount_vnd = safe_float(df.iloc[row_index, amount_vnd_col]) if amount_vnd_col is not None else 0.0
        unit_price_usd = safe_float(df.iloc[row_index, unit_price_usd_col]) if unit_price_usd_col is not None else 0.0
        usage_count = safe_float(df.iloc[row_index, usage_count_col]) if usage_count_col is not None else 0.0

        if unit_price_usd <= 0 and amount_usd > 0 and usage_count > 0:
            unit_price_usd = amount_usd / usage_count
        # Some sheets already contain total USD. Others only expose count + price.
        if amount_usd <= 0 and amount_vnd > 0 and unit_price_usd > 0 and usage_count > 0:
            amount_usd = usage_count * unit_price_usd

        if amount_usd <= 0 and amount_vnd <= 0:
            continue

        aggregated[cc_code]["amount_usd"] += amount_usd
        aggregated[cc_code]["amount_vnd"] += amount_vnd

        if unit_price_usd > 0 and amount_usd > 0:
            quantity = usage_count if usage_count > 0 else round(amount_usd / unit_price_usd, 6)
            if quantity > 0:
                term_map[cc_code].append(
                    {
                        "quantity": quantity,
                        "unit_price_usd": unit_price_usd,
                    }
                )

    return aggregated, term_map


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
            records.extend(
                _parse_summary_sheet(
                    summary_df,
                    target_months,
                    source_file=os.path.basename(path),
                    source_sheet=summary_sheet,
                )
            )

        for component_key, tokens in COMPONENT_SHEETS.items():
            sheet_name = _find_matching_sheet(excel_file.sheet_names, tokens)
            if not sheet_name:
                continue

            component_df = pd.read_excel(path, sheet_name=sheet_name, header=None, engine="xlrd")
            aggregated, term_map = _parse_component_sheet(component_df)

            for cc_code, amounts in aggregated.items():
                for month in target_months:
                    records.append(
                        {
                            "cc_code": cc_code,
                            "period": month,
                            "amount_vnd": amounts["amount_vnd"],
                            "amount_usd": amounts["amount_usd"],
                            "source": "it_sim",
                            "description": _join_description(
                                "it_sim",
                                "component",
                                component_key,
                                metadata=_metadata_parts(
                                    source_file=os.path.basename(path),
                                    source_sheet=sheet_name,
                                    source_filter=f"cc:{cc_code}",
                                ),
                            ),
                        }
                    )

            for cc_code, terms in term_map.items():
                for term in terms:
                    for month in target_months:
                        records.append(
                            {
                                "cc_code": cc_code,
                                "period": month,
                                "amount_vnd": 0.0,
                                "amount_usd": term["quantity"] * term["unit_price_usd"],
                                "source": "it_sim",
                                "description": _join_description(
                                    "it_sim",
                                    "component_term",
                                    component_key,
                                    f"qty={term['quantity']}",
                                    f"unit_usd={term['unit_price_usd']}",
                                    metadata=_metadata_parts(
                                        source_file=os.path.basename(path),
                                        source_sheet=sheet_name,
                                        source_filter=f"cc:{cc_code}",
                                    ),
                                ),
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
    manifest_files = resolve_manifest_files(search_dir, "it_simulation")
    all_files = [os.path.basename(path) for path in manifest_files] if manifest_files else os.listdir(search_dir)
    manifest_by_name = {os.path.basename(path): path for path in manifest_files}
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
                matched_path = manifest_by_name.get(name, os.path.join(search_dir, name))
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
