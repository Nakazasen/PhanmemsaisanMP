"""Verify parser-to-writer fixed-assets policy against FY2026/FY2027 audit truth.

This is an in-memory integration check.  It imports each source ledger using
the production parser, builds production source-order payloads, evaluates only
their individual ``ROUND(USD*$B$2,0)`` terms at the rate observed in the
reference corpus, and reconciles them to the per-asset expected values from
the cross-trace comparator.  No workbook is written or changed.
"""

from __future__ import annotations

import csv
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from audit_fixed_assets_cross_trace import AUDIT_DATE, ROOT
from src.db.schema import create_schema, init_sys_params
from src.engine.hub_builder import HubBuilder
from src.parsers.fixed_assets import _asset_tag, parse_fixed_assets


AUDIT_DIR = ROOT / "docs" / "audits"
def read_csv(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def modal_rate(reference_rows: list[dict[str, str]], fy: str) -> int:
    rates = Counter(
        int(float(row["fx_rate"]))
        for row in reference_rows
        if row["fy"] == fy and row["fx_rate"] not in ("", "0")
    )
    if not rates:
        raise RuntimeError(f"No observed reference FX rate for {fy}")
    return rates.most_common(1)[0][0]


def expected_values(comparisons: list[dict[str, str]], fy: str) -> dict[tuple[str, int, str], int]:
    result: dict[tuple[str, int, str], int] = {}
    for row in comparisons:
        if row["fy"] != fy or row["expected_per_asset_round_vnd"] in ("", None):
            continue
        result[(row["cc"], int(row["account"]), row["period"])] = int(float(row["expected_per_asset_round_vnd"]))
    return result


def rendered_values(builder: HubBuilder, conn: sqlite3.Connection) -> dict[tuple[str, int, str], int]:
    result: defaultdict[tuple[str, int, str], int] = defaultdict(int)
    cost_centers = [str(row[0]) for row in conn.execute("SELECT DISTINCT cc_code FROM fact_input_data WHERE source='fixed_assets'")]
    for cc in cost_centers:
        for payload in builder._load_fixed_asset_source_order_rows(int(cc)):
            account = int(payload["account_code"])
            if payload["terms"]:
                raise RuntimeError("Fixed-assets output must contain pre-rounded VND values, not long Excel ROUND formulas")
            for period, amount in dict(payload["numeric_months"]).items():
                result[(cc, account, str(period))] += int(amount)
    return dict(result)


def terminal_posting_violations(conn: sqlite3.Connection) -> int:
    """Ensure no production fact row survives past the audited P terminal month."""
    fact_rows = conn.execute(
        "SELECT period, description FROM fact_input_data WHERE source='fixed_assets'"
    ).fetchall()
    violations = 0
    for audit in conn.execute(
        """
        SELECT asset_no, asset_text, source_sheet, source_row, terminal_period
        FROM audit_fixed_asset_import_rows
        WHERE inclusion_status='INCLUDED' AND terminal_period IS NOT NULL AND terminal_period<>''
        """
    ):
        tag = _asset_tag(audit["asset_no"], audit["asset_text"], audit["source_sheet"], int(audit["source_row"]))
        violations += sum(
            1
            for fact in fact_rows
            if str(fact["description"] or "").endswith("|" + tag)
            and str(fact["period"]) > str(audit["terminal_period"])
        )
    return violations


def verify_fy(fiscal_year: int, reference_rows: list[dict[str, str]], comparisons: list[dict[str, str]]) -> dict[str, int]:
    fy = f"FY{fiscal_year}"
    rate = modal_rate(reference_rows, fy)
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        create_schema(conn)
        init_sys_params(conn, exchange_rate=rate, fiscal_year=fiscal_year, exchange_rate_source="reference-output modal B2")
        parsed = parse_fixed_assets(conn, source_dir=str(ROOT / "docs" / f"MP{fiscal_year}"))
        builder = HubBuilder.__new__(HubBuilder)
        builder.conn = conn
        builder.fiscal_year = fiscal_year
        actual = rendered_values(builder, conn)
        expected = expected_values(comparisons, fy)
        keys = set(actual) | set(expected)
        mismatches = {
            key: (expected.get(key), actual.get(key))
            for key in keys
            if expected.get(key) != actual.get(key)
        }
        if mismatches:
            sample = list(sorted(mismatches.items()))[:10]
            raise RuntimeError(f"{fy} production parser/writer policy mismatches: {sample}")
        post_terminal = terminal_posting_violations(conn)
        if post_terminal:
            raise RuntimeError(f"{fy} has {post_terminal} fact rows after their P terminal month")
        audit_statuses = Counter(
            str(row[0])
            for row in conn.execute(
                "SELECT inclusion_status FROM audit_fixed_asset_import_rows WHERE fiscal_year=?", (fiscal_year,)
            )
        )
        return {
            "expected_monthly_cells": len(expected),
            "rendered_monthly_cells": len(actual),
            "source_rows": int(parsed["source_rows"]),
            "asset_rows": int(parsed["parsed_assets"]),
            "exchange_rate": rate,
            "post_terminal_fact_rows": post_terminal,
            "audit_included_rows": audit_statuses["INCLUDED"],
            "audit_excluded_rows": audit_statuses["EXCLUDED"],
        }
    finally:
        conn.close()


def main() -> None:
    references = read_csv(f"fixed_assets_reference_rows_{AUDIT_DATE}.csv")
    comparisons = read_csv(f"fixed_assets_monthly_comparison_{AUDIT_DATE}.csv")
    results = {f"FY{year}": verify_fy(year, references, comparisons) for year in (2026, 2027)}
    output = AUDIT_DIR / f"fixed_assets_policy_output_verification_{AUDIT_DATE}.json"
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"WROTE {output}")
    print(results)


if __name__ == "__main__":
    main()
