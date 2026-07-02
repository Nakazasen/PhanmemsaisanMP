"""Non-sensitive fixed-assets coverage audit helpers."""
from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from src.parsers.fixed_assets import inspect_fixed_assets_workbook


def fixed_assets_db_coverage(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT cc_code, description, COUNT(*) AS period_rows
        FROM fact_input_data
        WHERE source='fixed_assets'
        GROUP BY cc_code, description
        """
    ).fetchall()
    assets_by_cc: Counter[str] = Counter()
    period_rows_by_cc: Counter[str] = Counter()
    depreciation_rows_by_cc: Counter[str] = Counter()
    interest_rows_by_cc: Counter[str] = Counter()
    for row in rows:
        cc_code = str(row["cc_code"])
        description = str(row["description"] or "")
        assets_by_cc[cc_code] += 1
        period_rows_by_cc[cc_code] += int(row["period_rows"] or 0)
        if description.startswith("fixed_assets_depr|"):
            depreciation_rows_by_cc[cc_code] += int(row["period_rows"] or 0)
        elif description.startswith("fixed_assets_interest|"):
            interest_rows_by_cc[cc_code] += int(row["period_rows"] or 0)
    return {
        "asset_series_by_cc": dict(assets_by_cc),
        "period_rows_by_cc": dict(period_rows_by_cc),
        "depreciation_rows_by_cc": dict(depreciation_rows_by_cc),
        "interest_rows_by_cc": dict(interest_rows_by_cc),
    }


def build_fixed_assets_coverage_report(
    conn: sqlite3.Connection,
    workbook_path: str | Path | None,
) -> dict[str, Any]:
    source = inspect_fixed_assets_workbook(workbook_path) if workbook_path else {
        "source_rows": 0,
        "by_cc": {},
        "by_sheet": {},
        "skipped_reasons": {"missing_file": 1},
    }
    db = fixed_assets_db_coverage(conn)
    source_by_cc = {str(k): int(v) for k, v in source.get("by_cc", {}).items()}
    parsed_series_by_cc = {str(k): int(v) for k, v in db.get("asset_series_by_cc", {}).items()}
    mismatches: dict[str, dict[str, int]] = {}
    for cc_code, source_count in source_by_cc.items():
        if parsed_series_by_cc.get(cc_code, 0) == 0:
            mismatches[cc_code] = {
                "source_asset_rows": source_count,
                "parsed_series": parsed_series_by_cc.get(cc_code, 0),
            }
    return {
        "source": source,
        "db": db,
        "mismatches": mismatches,
    }
