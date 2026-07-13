"""
MP2027 Manager - Fixed Assets Parser (Refactored V4.5.0)
Processes depreciation and interest schedules with month-end logic.
"""
from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import openpyxl

from src.engine.account_resolver import resolve_account_code_by_keywords_for_connection

from src.utils import excel_helpers as helpers
from src.utils.source_manifest import resolve_manifest_file


HEADER_ALIASES = {
    "category": ("category", "asset category", "asset class", "資産クラス", "資産分類"),
    "asset_no": ("asset no", "asset_no", "資産番号", "固定資産番号", "no."),
    "asset_text": ("asset text", "asset_text", "資産テキスト", "資産名", "名称"),
    "control_cc": ("control cost center", "management cost center", "管理原価センタ"),
    "depreciation_cc": (
        "code phòng chịu chi phí", "depreciation cost center", "depr cost center",
        "khấu hao cost center", "償却原価センタ", "費用負担原価センタ",
    ),
    "monthly_depr": ("chi phí khấu hao", "monthly depr", "monthly depreciation", "減価償却費", "償却費"),
    "last_month": ("tháng khấu hao cuối cùng", "last month", "last depreciation month", "償却終了", "最終償却", "最終月"),
    "last_month_depr": ("chi phí khấu hao của tháng cuối cùng", "last month depr", "last month depreciation", "最終月償却", "最終償却額"),
    "apr_interest": ("chi phí lãi tháng 4", "apr interest", "april interest", "4月利息", "4月金利", "4月"),
    "may_interest": ("chi phí lãi", "may interest", "interest from may", "5月以降利息", "5月金利", "5月以降"),
}

LEGACY_COLUMN_MAP = {
    "category": 1,
    "asset_no": 2,
    "asset_text": 3,
    "control_cc": 7,
    "depreciation_cc": 9,
    "monthly_depr": 11,
    "last_month": 15,
    "last_month_depr": 16,
    "apr_interest": 21,
    "may_interest": 22,
}

CATEGORY_SPECS = {
    "machinery_equipment": {
        "aliases": ("mfg)machinery and equipment", "machinery and equipment"),
        "account_keywords": ("減価償却費", "機械装置"),
        "label": "Machinery and Equipment",
    },
    "vehicles": {
        "aliases": ("mfg)vehicles", "vehicles"),
        "account_keywords": ("減価償却費", "車輌運搬具"),
        "label": "Vehicles",
    },
    "tools_furniture_fixtures": {
        "aliases": ("mfg)tools furniture and fixtures", "tools furniture and fixtures"),
        "account_keywords": ("減価償却費", "工具器具備品"),
        "label": "Tools Furniture and Fixtures",
    },
    "other_tangible_fixed_assets": {
        "aliases": ("mfg)other tangible fixed assets", "other tangible fixed assets"),
        "account_keywords": ("減価償却費", "その他有形固定資産"),
        "label": "Other Tangible Fixed Assets",
    },
    "mold": {
        "aliases": ("mfg)mold", "mold"),
        "account_keywords": ("減価償却費", "金型"),
        "label": "Mold",
    },
}
INTEREST_ACCOUNT_KEYWORDS = ("固定資産", "金利")
OUT_OF_SCOPE_CATEGORY_MARKERS = (
    "sga)", "software", "buildings", "structures", "land use rights",
)


def _category_status(value: Any) -> tuple[str | None, str]:
    key = _normalize_category(value)
    if key is not None:
        return key, "supported"
    text = " ".join(_norm(value).split())
    if text and any(marker in text for marker in OUT_OF_SCOPE_CATEGORY_MARKERS):
        return None, "out_of_scope"
    return None, "unknown"



def _norm(value: Any) -> str:
    return helpers.normalize_text(str(value or "")).replace("\u3000", " ")


def _header_score(row: tuple[Any, ...]) -> int:
    text = " | ".join(_norm(cell) for cell in row if cell not in (None, ""))
    score = 0
    for aliases in HEADER_ALIASES.values():
        if any(_norm(alias) in text for alias in aliases):
            score += 1
    return score


def _find_header_row(ws) -> tuple[int | None, dict[str, int]]:
    best_row = None
    best_score = 0
    best_values: tuple[Any, ...] = ()
    for idx, row in enumerate(ws.iter_rows(min_row=1, max_row=min(ws.max_row, 20), values_only=True), start=1):
        score = _header_score(row)
        if score > best_score:
            best_score = score
            best_row = idx
            best_values = row
    if best_row is None or best_score < 2:
        return None, {}

    mapping: dict[str, int] = {}
    normalized_cells = [_norm(cell) for cell in best_values]
    for field, aliases in HEADER_ALIASES.items():
        for col_idx, cell_text in enumerate(normalized_cells):
            if cell_text and any(_norm(alias) in cell_text for alias in aliases):
                mapping[field] = col_idx
                break
    if "depreciation_cc" not in mapping:
        return None, {}
    return best_row, mapping


def _value(row: tuple[Any, ...], mapping: dict[str, int], field: str) -> Any:
    idx = mapping.get(field)
    if idx is None or idx >= len(row):
        return None
    return row[idx]


def _asset_tag(asset_no: Any, asset_text: Any, sheet_name: str, row_number: int) -> str:
    no = str(asset_no or "").strip()
    text = str(asset_text or "").strip()
    if no and text:
        return f"{no}|{text}"
    if no:
        return no
    if text:
        return text
    return f"{sheet_name}!row{row_number}"


def _sheet_plan(ws) -> tuple[int, dict[str, int], str]:
    header_row, mapping = _find_header_row(ws)
    if header_row is not None:
        return header_row + 1, mapping, "header"
    return 5, dict(LEGACY_COLUMN_MAP), "legacy"


def _normalize_category(value: Any) -> str | None:
    text = " ".join(_norm(value).split())
    for key, spec in CATEGORY_SPECS.items():
        if text in {_norm(alias) for alias in spec["aliases"]}:
            return key
    return None


def _selected_worksheets(wb) -> list[Any]:
    """Use the latest YYYY.MM source sheet; compact fixtures may use matching sheets."""
    period_sheets = []
    for ws in wb.worksheets:
        title = str(ws.title).strip()
        parts = title.split(".")
        if len(parts) == 2 and all(part.isdigit() for part in parts):
            period_sheets.append((int(parts[0]), int(parts[1]), ws))
    if period_sheets:
        return [max(period_sheets, key=lambda item: (item[0], item[1]))[2]]
    return [ws for ws in wb.worksheets if _find_header_row(ws)[0] is not None]



def find_fixed_assets_file(source_dir: str = None) -> str | None:
    manifest_path = resolve_manifest_file(source_dir, "fixed_assets")
    if manifest_path:
        return manifest_path

    search_dir = Path(source_dir or Path(__file__).resolve().parents[2])
    for path in search_dir.glob("*.xlsx"):
        if "Fixed_Assets_Information" in path.name:
            return str(path)
    return None


def expand_depreciation_schedule(monthly_depr: float, last_month: str | None, last_month_depr: float, fy_months: list[str]) -> dict[str, float]:
    result = {}
    for period in fy_months:
        if last_month and period > last_month:
            continue
        if last_month and period == last_month:
            amount = last_month_depr if last_month_depr > 0 else monthly_depr
        else:
            amount = monthly_depr
        if amount > 0:
            result[period] = amount
    return result


def expand_interest_schedule(apr_interest: float, may_interest: float, last_month: str | None, fy_months: list[str]) -> dict[str, float]:
    result = {}
    for period in fy_months:
        if last_month and period > last_month:
            continue
        amount = apr_interest if period == fy_months[0] else may_interest
        if amount > 0:
            result[period] = amount
    return result


def inspect_fixed_assets_workbook(fa_path: str | Path) -> dict:
    """Return non-sensitive source-row coverage counts by sheet, CC and Category."""
    path = Path(fa_path)
    if not path.is_file():
        return {"source_rows": 0, "by_cc": {}, "by_category": {}, "by_sheet": {}, "skipped_reasons": {"missing_file": 1}}

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    by_cc: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    by_sheet: dict[str, dict[str, Any]] = {}
    skipped: Counter[str] = Counter()
    try:
        selected = _selected_worksheets(wb)
        if not selected:
            return {"source_rows": 0, "by_cc": {}, "by_category": {}, "by_sheet": {}, "skipped_reasons": {"missing_source_sheet": 1}}
        for ws in selected:
            start_row, mapping, mode = _sheet_plan(ws)
            sheet_rows = 0
            sheet_skipped: Counter[str] = Counter()
            for row in ws.iter_rows(min_row=start_row, values_only=True):
                if not any(cell not in (None, "") for cell in row):
                    continue
                cc_code = helpers.extract_cc_code(_value(row, mapping, "depreciation_cc"))
                monthly_depr = helpers.safe_float(_value(row, mapping, "monthly_depr"))
                apr_interest = helpers.safe_float(_value(row, mapping, "apr_interest"))
                may_interest = helpers.safe_float(_value(row, mapping, "may_interest"))
                category_key, category_status = _category_status(_value(row, mapping, "category"))
                if not cc_code:
                    sheet_skipped["missing_depreciation_cc"] += 1
                    continue
                if monthly_depr <= 0 and apr_interest <= 0 and may_interest <= 0:
                    sheet_skipped["no_fixed_asset_amount"] += 1
                    continue
                if category_status == "out_of_scope":
                    sheet_skipped["out_of_scope_category"] += 1
                    continue
                if category_key is None:
                    sheet_skipped["missing_or_unknown_category"] += 1
                    continue
                by_cc[cc_code] += 1
                by_category[category_key] += 1
                sheet_rows += 1
            skipped.update(sheet_skipped)
            by_sheet[ws.title] = {"mode": mode, "selected": True, "source_rows": sheet_rows, "skipped_reasons": dict(sheet_skipped)}
        return {
            "source_rows": sum(by_cc.values()), "by_cc": dict(by_cc), "by_category": dict(by_category),
            "by_sheet": by_sheet, "selected_sheets": [ws.title for ws in selected], "skipped_reasons": dict(skipped),
        }
    finally:
        wb.close()


def parse_fixed_assets(conn: sqlite3.Connection, fa_path: str = None, source_dir: str = None) -> dict:
    fpath = fa_path or find_fixed_assets_file(source_dir)
    if not fpath or not Path(fpath).is_file():
        return {"total": 0, "source_rows": 0, "parsed_assets": 0, "skipped_reasons": {"missing_file": 1}}

    rate_row = conn.execute("SELECT value FROM sys_params WHERE key='exchange_rate_usd_vnd'").fetchone()
    rate = float(rate_row[0]) if rate_row else 25450.0
    fy_row = conn.execute("SELECT value FROM sys_params WHERE key='fiscal_year'").fetchone()
    fiscal_year = int((fy_row[0] if fy_row else "FY2027").replace("FY", ""))
    fy_months = helpers.get_fy_months(fiscal_year)

    wb = openpyxl.load_workbook(Path(fpath), read_only=True, data_only=True)
    pending: list[tuple[object, ...]] = []
    parsed_assets = 0
    source_rows = 0
    depr_rows = 0
    interest_rows = 0
    by_cc: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    by_sheet: dict[str, dict[str, Any]] = {}
    skipped: Counter[str] = Counter()
    warnings: Counter[str] = Counter()

    try:
        selected = _selected_worksheets(wb)
        if not selected:
            raise ValueError("Fixed-assets workbook has no recognizable current source sheet")
        for ws in selected:
            start_row, mapping, mode = _sheet_plan(ws)
            sheet_source_rows = 0
            sheet_parsed_assets = 0
            sheet_skipped: Counter[str] = Counter()
            for row_number, row in enumerate(ws.iter_rows(min_row=start_row, values_only=True), start=start_row):
                if not any(cell not in (None, "") for cell in row):
                    continue
                cc_code = helpers.extract_cc_code(_value(row, mapping, "depreciation_cc"))
                if not cc_code:
                    sheet_skipped["missing_depreciation_cc"] += 1
                    continue
                monthly_depr = helpers.safe_float(_value(row, mapping, "monthly_depr"))
                last_month = helpers.normalize_period(_value(row, mapping, "last_month"))
                last_month_depr = helpers.safe_float(_value(row, mapping, "last_month_depr"))
                apr_interest = helpers.safe_float(_value(row, mapping, "apr_interest"))
                may_interest = helpers.safe_float(_value(row, mapping, "may_interest"))
                if monthly_depr <= 0 and apr_interest <= 0 and may_interest <= 0:
                    sheet_skipped["no_fixed_asset_amount"] += 1
                    continue

                category_value = _value(row, mapping, "category")
                category_key, category_status = _category_status(category_value)
                if category_key is None and mode == "legacy" and category_value in (None, ""):
                    category_key = "tools_furniture_fixtures"
                    category_status = "supported"
                    warnings["legacy_missing_category_defaulted_to_tools"] += 1
                if category_status == "out_of_scope":
                    sheet_skipped["out_of_scope_category"] += 1
                    continue
                if category_key is None:
                    raw_category = str(category_value or "<blank>").strip()
                    raise ValueError(f"Unknown fixed-assets Category at {ws.title}!{row_number}: {raw_category}")

                asset_tag = _asset_tag(_value(row, mapping, "asset_no"), _value(row, mapping, "asset_text"), ws.title, row_number)
                source_rows += 1
                sheet_source_rows += 1
                parsed_assets += 1
                sheet_parsed_assets += 1
                by_cc[cc_code] += 1
                by_category[category_key] += 1
                if last_month in fy_months and last_month_depr <= 0 and monthly_depr > 0:
                    warnings["last_month_depr_fallback_to_monthly"] += 1

                dep_desc = f"fixed_assets_depr|{category_key}|{asset_tag}"
                int_desc = f"fixed_assets_interest|{category_key}|{asset_tag}"
                dep_account = resolve_account_code_by_keywords_for_connection(
                    conn,
                    cc_code,
                    all_of=tuple(CATEGORY_SPECS[category_key]["account_keywords"]),
                    none_of=("リース",),
                )
                interest_account = resolve_account_code_by_keywords_for_connection(
                    conn,
                    cc_code,
                    all_of=INTEREST_ACCOUNT_KEYWORDS,
                )
                for period, val in expand_depreciation_schedule(monthly_depr, last_month, last_month_depr, fy_months).items():
                    pending.append((
                        "fixed_assets", period, round(val * rate, 0), val, cc_code, dep_account, dep_desc,
                        Path(fpath).name, ws.title, row_number,
                        f"fixed_assets:depreciation:{category_key}:{asset_tag}", row_number * 2,
                    ))
                    depr_rows += 1
                for period, val in expand_interest_schedule(apr_interest, may_interest, last_month, fy_months).items():
                    pending.append((
                        "fixed_assets", period, round(val * rate, 0), val, cc_code, interest_account, int_desc,
                        Path(fpath).name, ws.title, row_number,
                        f"fixed_assets:interest:{category_key}:{asset_tag}", row_number * 2 + 1,
                    ))
                    interest_rows += 1
            skipped.update(sheet_skipped)
            by_sheet[ws.title] = {
                "mode": mode, "selected": True, "source_rows": sheet_source_rows,
                "parsed_assets": sheet_parsed_assets, "skipped_reasons": dict(sheet_skipped),
            }
    finally:
        wb.close()

    cursor = conn.cursor()
    cursor.execute("SAVEPOINT fixed_assets_import")
    try:
        cursor.execute("DELETE FROM fact_input_data WHERE source='fixed_assets'")
        cursor.executemany(
            """
            INSERT INTO fact_input_data
            (source, period, amount_vnd, amount_usd, cc_code, account_code, description,
             source_group, source_file, source_sheet, source_row, item_key, item_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'fixed_assets', ?, ?, ?, ?, ?)
            """,
            pending,
        )
        cursor.execute("RELEASE SAVEPOINT fixed_assets_import")
        conn.commit()
    except Exception:
        cursor.execute("ROLLBACK TO SAVEPOINT fixed_assets_import")
        cursor.execute("RELEASE SAVEPOINT fixed_assets_import")
        raise

    return {
        "total": len(pending), "source_rows": source_rows, "parsed_assets": parsed_assets,
        "depreciation_rows": depr_rows, "interest_rows": interest_rows,
        "fiscal_year": fiscal_year, "exchange_rate": rate,
        "selected_sheets": [ws.title for ws in selected], "by_cc": dict(by_cc),
        "by_category": dict(by_category), "by_sheet": by_sheet,
        "skipped_reasons": dict(skipped), "warnings": dict(warnings),
    }
