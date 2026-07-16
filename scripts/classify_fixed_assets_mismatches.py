"""Create a row-level decision matrix for fixed-assets cross-trace mismatches.

This script intentionally consumes the reproducible CSV artifacts produced by
``audit_fixed_assets_cross_trace.py``.  It does not alter any source or output
workbook.  The purpose is to finish classifying every TRUE_AMOUNT_MISMATCH
before an accounting-code change is considered.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:  # Supports both ``py scripts/...`` and import from automated tests.
    from audit_fixed_assets_cross_trace import (
        AUDIT_DATE,
        CATEGORY_SPECS,
        INTEREST_ACCOUNT,
        ROOT,
        excel_round,
    )
except ModuleNotFoundError:  # pragma: no cover - exercised through package import.
    from scripts.audit_fixed_assets_cross_trace import (
        AUDIT_DATE,
        CATEGORY_SPECS,
        INTEREST_ACCOUNT,
        ROOT,
        excel_round,
    )

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.db.schema import create_schema, get_connection


AUDIT_DIR = ROOT / "docs" / "audits"
VALID_DECISIONS = {
    "XAC_DINH_TU_BANG_CHUNG",
    "LA_NGOAI_LE_NHAP_TAY_HOAC_TANG_KHAC",
    "MAU_THUAN_CAN_NGHIEP_VU_DUYET",
    "KHONG_THE_XAC_DINH_TU_DU_LIEU",
}


def read_csv(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def json_value(value: str | None, fallback: Any) -> Any:
    if value in (None, ""):
        return fallback
    return json.loads(value)


def as_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(float(value))


def asset_account(asset: dict[str, str]) -> int | None:
    if asset["category_status"] != "supported":
        return None
    key = asset["category_key"]
    spec = CATEGORY_SPECS.get(key)
    return int(spec["account"]) if spec else None


def source_assets_by_key(ledger: list[dict[str, str]]) -> dict[tuple[str, str, int], list[dict[str, str]]]:
    grouped: defaultdict[tuple[str, str, int], list[dict[str, str]]] = defaultdict(list)
    for asset in ledger:
        cc = asset["depreciation_cc"]
        account = asset_account(asset)
        if cc and account is not None:
            grouped[(asset["fy"], cc, account)].append(asset)
            grouped[(asset["fy"], cc, INTEREST_ACCOUNT)].append(asset)
    return dict(grouped)


def selected_reference_by_key(
    references: list[dict[str, str]],
) -> dict[tuple[str, str, int], list[dict[str, str]]]:
    grouped: defaultdict[tuple[str, str, int], list[dict[str, str]]] = defaultdict(list)
    for row in references:
        if row["source_candidate_status"] != "SELECTED_SOURCE_DERIVED_CANDIDATE":
            continue
        if row["cc"]:
            grouped[(row["fy"], row["cc"], int(row["account"]))].append(row)
    return dict(grouped)


def schedule_for(asset: dict[str, str], account: int) -> dict[str, float]:
    field = "interest_schedule" if account == INTEREST_ACCOUNT else "depreciation_schedule"
    return {period: float(amount) for period, amount in json_value(asset[field], {}).items()}


def formula_kind(reference_rows: list[dict[str, str]], period: str) -> str:
    formulas = [
        str(json_value(row["monthly_formulas"], {}).get(period, "") or "")
        for row in reference_rows
        if json_value(row["monthly_values"], {}).get(period) is not None
    ]
    if not formulas:
        return "NO_REFERENCE_COMPONENT"
    if all(not formula.startswith("=") for formula in formulas):
        return "STATIC_VALUE"
    if all(formula.startswith("=") and "$B$2" in formula for formula in formulas):
        return "EMBEDDED_USD_SNAPSHOT_FORMULA"
    if any(formula.startswith("=") for formula in formulas):
        return "MIXED_OR_LINKED_FORMULA"
    return "UNCLASSIFIED"


def has_mixed_static_and_formula_components(reference_rows: list[dict[str, str]], period: str) -> bool:
    formulas = [
        str(json_value(row["monthly_formulas"], {}).get(period, "") or "")
        for row in reference_rows
        if json_value(row["monthly_values"], {}).get(period) is not None
    ]
    return any(formula.startswith("=") for formula in formulas) and any(
        formula and not formula.startswith("=") for formula in formulas
    )


def reference_components(reference_rows: list[dict[str, str]], period: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in reference_rows:
        values = json_value(row["monthly_values"], {})
        amount = values.get(period)
        if amount is None:
            continue
        formulas = json_value(row["monthly_formulas"], {})
        result.append(
            {
                "reference_file": row["reference_file"],
                "sheet": row["sheet"],
                "row": int(row["row"]),
                "description": row["description"],
                "value_vnd": int(excel_round(float(amount))),
                "formula": formulas.get(period, ""),
            }
        )
    return result


def source_components(source_rows: list[dict[str, str]], account: int, period: str) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    for asset in source_rows:
        amount = schedule_for(asset, account).get(period, 0.0)
        terminal = asset["terminal_period"]
        if amount == 0 and not (terminal and terminal < period):
            continue
        components.append(
            {
                "source_file": asset["source_file"],
                "sheet": asset["source_sheet"],
                "row": int(asset["source_row"]),
                "asset_no": asset["asset_no"],
                "asset_text": asset["asset_text"],
                "L_monthly_depr_usd": as_int(asset["monthly_depr_usd"]),
                "P_terminal_period": terminal or None,
                "Q_terminal_depr_usd": as_int(asset["terminal_depr_usd"]),
                "V_apr_interest_usd": as_int(asset["apr_interest_usd"]),
                "W_may_interest_usd": as_int(asset["may_interest_usd"]),
                "scheduled_usd_for_period": amount,
                "terminal_relation": asset["terminal_relation"],
            }
        )
    return components


def known_reference_asset_numbers(reference_rows: list[dict[str, str]]) -> set[str]:
    found: set[str] = set()
    for row in reference_rows:
        found.update(re.findall(r"\d{6,}", row["description"] or ""))
    return found


def has_direct_post_terminal_continuation(
    source_rows: list[dict[str, str]], account: int, period: str, delta: int, rate: int
) -> bool:
    """Only claim a terminal defect when the added amount is exact evidence.

    It is intentionally conservative: either one expired asset or all expired
    assets must account for the complete positive difference.
    """
    if delta <= 0 or account == INTEREST_ACCOUNT or not rate:
        return False
    expired = [
        int(excel_round(float(asset["monthly_depr_usd"] or 0) * rate))
        for asset in source_rows
        if asset["terminal_relation"] == "within_fy"
        and asset["terminal_period"]
        and asset["terminal_period"] < period
    ]
    positives = [amount for amount in expired if amount > 0]
    return delta in positives or (positives and delta == sum(positives))


def has_direct_terminal_transition(
    source_rows: list[dict[str, str]],
    account: int,
    period: str,
    rate: int,
    comparison_by_key_period: dict[tuple[str, str, int, str], dict[str, str]],
    key: tuple[str, str, int],
) -> bool:
    """Prove a continuation by comparing the terminal-month transition.

    This captures the common real-world pattern where a reference keeps its
    prior-month amount unchanged after an asset expires, while unrelated
    snapshot variance prevents a simple current-month delta from matching.
    """
    if account == INTEREST_ACCOUNT or not rate:
        return False
    year, month = int(period[:4]), int(period[4:])
    # Fiscal April has no prior month inside this FY comparison.
    if month == 4:
        return False
    prior_period = f"{year - 1 if month == 1 else year}{12 if month == 1 else month - 1:02d}"
    prior = comparison_by_key_period.get((*key, prior_period))
    if not prior:
        return False
    terminal_amount = sum(
        int(excel_round(schedule_for(asset, account).get(prior_period, 0.0) * rate))
        for asset in source_rows
        if asset["terminal_relation"] == "within_fy" and asset["terminal_period"] == prior_period
    )
    if terminal_amount <= 0:
        return False
    expected_prior = as_int(prior["expected_per_asset_round_vnd"])
    expected_current = as_int(comparison_by_key_period[(*key, period)]["expected_per_asset_round_vnd"])
    actual_prior = as_int(prior["reference_actual_vnd"])
    actual_current = as_int(comparison_by_key_period[(*key, period)]["reference_actual_vnd"])
    return (
        expected_prior is not None
        and expected_current is not None
        and actual_prior is not None
        and actual_current is not None
        and expected_prior - expected_current == terminal_amount
        and actual_current == actual_prior
    )


def group_delta_pattern(rows: list[dict[str, str]]) -> dict[tuple[str, str, int], set[int]]:
    grouped: defaultdict[tuple[str, str, int], set[int]] = defaultdict(set)
    for row in rows:
        if row["classification"] != "TRUE_AMOUNT_MISMATCH":
            continue
        delta = as_int(row["delta_reference_minus_expected"])
        if delta is not None:
            grouped[(row["fy"], row["cc"], int(row["account"]))].add(delta)
    return dict(grouped)


def classify_row(
    row: dict[str, str],
    source_rows: list[dict[str, str]],
    reference_rows: list[dict[str, str]],
    all_source_asset_numbers: set[str],
    deltas_in_group: set[int],
    comparison_by_key_period: dict[tuple[str, str, int, str], dict[str, str]],
) -> tuple[str, str, str, str]:
    """Return (classification, decision_status, allowed_action, reason)."""
    period = row["period"]
    account = int(row["account"])
    actual = as_int(row["reference_actual_vnd"]) or 0
    expected = as_int(row["expected_per_asset_round_vnd"]) or 0
    delta = actual - expected
    components = reference_components(reference_rows, period)
    rates = {int(ref["fx_rate"]) for ref in reference_rows if ref["fx_rate"] not in ("", "0")}
    rate = next(iter(rates)) if len(rates) == 1 else 0
    reference_assets = known_reference_asset_numbers(reference_rows)
    if reference_assets and reference_assets.isdisjoint(all_source_asset_numbers):
        return (
            "REFERENCE_ASSET_NOT_IN_SOURCE_SNAPSHOT",
            "KHONG_THE_XAC_DINH_TU_DU_LIEU",
            "REQUEST_NEWER_ASSET_REGISTER_OR_BUSINESS_CONFIRMATION",
            "Reference describes asset number(s) absent from the audited source snapshot; the evidence does not establish whether they are future purchases or an alternative register.",
        )
    key = (row["fy"], row["cc"], account)
    if has_direct_terminal_transition(source_rows, account, period, rate, comparison_by_key_period, key):
        return (
            "POST_TERMINAL_REFERENCE_CONTINUES",
            "XAC_DINH_TU_BANG_CHUNG",
            "POLICY_FIX_ALLOWED_DO_NOT_COPY_REFERENCE",
            "The source total falls by the exact terminal-month Q amount, but the reference does not fall in the following month. This proves that the submitted reference continues a cost after P terminal month.",
        )
    if has_direct_post_terminal_continuation(source_rows, account, period, delta, rate):
        return (
            "POST_TERMINAL_REFERENCE_CONTINUES",
            "XAC_DINH_TU_BANG_CHUNG",
            "POLICY_FIX_ALLOWED_DO_NOT_COPY_REFERENCE",
            "The positive difference exactly equals depreciation of source asset(s) whose P terminal period precedes this month. Q is the terminal-month amount; no cost may continue afterwards.",
        )
    kind = formula_kind(reference_rows, period)
    if kind == "STATIC_VALUE":
        return (
            "REFERENCE_STATIC_MANUAL_INPUT",
            "LA_NGOAI_LE_NHAP_TAY_HOAC_TANG_KHAC",
            "PRESERVE_AS_REFERENCE_EXCEPTION_DO_NOT_OVERWRITE",
            "All selected reference components for this month are literal values, so the submitted amount is a manual/other-layer input rather than a formula linked to the audited source ledger.",
        )
    if kind == "EMBEDDED_USD_SNAPSHOT_FORMULA":
        return (
            "REFERENCE_EMBEDDED_USD_SNAPSHOT_FORMULA",
            "MAU_THUAN_CAN_NGHIEP_VU_DUYET",
            "REQUIRE_BUSINESS_DECISION_BEFORE_ACCOUNTING_CHANGE",
            "Selected reference formula(s) use embedded USD terms times $B$2, not a source-ledger link. The source snapshot and reference snapshot disagree, but neither may be overwritten automatically.",
        )
    if has_mixed_static_and_formula_components(reference_rows, period):
        return (
            "REFERENCE_MIXED_STATIC_AND_FORMULA_INPUT",
            "LA_NGOAI_LE_NHAP_TAY_HOAC_TANG_KHAC",
            "PRESERVE_AS_REFERENCE_EXCEPTION_DO_NOT_OVERWRITE",
            "The submitted total contains both a literal VND component and a formula component. The literal component has no source-ledger link, so this is a manual/other-layer reference exception rather than an unexplained source calculation defect.",
        )
    if len(deltas_in_group) == 1:
        return (
            "CONSISTENT_REFERENCE_ADJUSTMENT",
            "MAU_THUAN_CAN_NGHIEP_VU_DUYET",
            "REQUIRE_BUSINESS_DECISION_BEFORE_ACCOUNTING_CHANGE",
            "The same non-rounding adjustment recurs in every mismatching month of this FY/CC/account group; its provenance is not present in the supplied source ledger.",
        )
    return (
        "UNEXPLAINED_FORMULA_OR_AGGREGATE_CONTRADICTION",
        "KHONG_THE_XAC_DINH_TU_DU_LIEU",
        "REQUIRE_ROW_LEVEL_BUSINESS_EVIDENCE",
        "The amount differs after per-asset rounding and terminal-before-FY alternatives. Available source and reference rows do not prove a single cause.",
    )


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: json.dumps(value, ensure_ascii=False, sort_keys=True)
                    if isinstance(value, (dict, list))
                    else value
                    for key, value in row.items()
                }
            )


def write_report(path: Path, rows: list[dict[str, Any]]) -> None:
    classifications = Counter(row["evidence_classification"] for row in rows)
    decisions = Counter(row["decision_status"] for row in rows)
    groups = {(row["fy"], row["cc"], row["account"]) for row in rows}
    lines = [
        "# Fixed assets: decision matrix for all true amount mismatches",
        "",
        f"- Generated from the reproducible 2026-07-16 cross-trace CSVs.",
        f"- Coverage: **{len(rows)} of 638** `TRUE_AMOUNT_MISMATCH` monthly cells, across {len(groups)} FY/CC/account groups.",
        "- This is an evidence classification, not permission to overwrite departmental submissions.",
        "",
        "## Evidence classification",
        "",
        "| Classification | Cells |",
        "| --- | ---: |",
        *[f"| `{key}` | {value} |" for key, value in sorted(classifications.items())],
        "",
        "## Decision status",
        "",
        "| Status | Cells | Meaning |",
        "| --- | ---: | --- |",
        *[
            f"| `{key}` | {value} | "
            + {
                "XAC_DINH_TU_BANG_CHUNG": "Evidence proves the policy outcome; code may follow that policy, not the submitted reference.",
                "LA_NGOAI_LE_NHAP_TAY_HOAC_TANG_KHAC": "Reference is manual/another layer; preserve it as an exception and do not overwrite it.",
                "MAU_THUAN_CAN_NGHIEP_VU_DUYET": "Two source snapshots conflict; business must choose the governing snapshot/policy.",
                "KHONG_THE_XAC_DINH_TU_DU_LIEU": "Supplied data lacks the asset register or row-level explanation needed to decide.",
            }[key]
            + " |"
            for key, value in sorted(decisions.items())
        ],
        "",
        "## Controls before accounting changes",
        "",
        "1. The matrix proves every cell has source and reference provenance, but only `XAC_DINH_TU_BANG_CHUNG` is eligible for a policy fix without a business decision.",
        "2. The 222 `ROUNDING_ORDER` cells are outside this matrix because their cause is already proven: round per asset before aggregation.",
        "3. Do not encode a reference snapshot, static manual amount, cost center, account, period, FX rate, filename, sheet, or FORM row as a fallback.",
        "4. Keep `FA-OPEN` open until the business decisions and a post-fix comparator are complete.",
        "",
        "## Artifact",
        "",
        f"- `docs/audits/fixed_assets_true_mismatch_decision_matrix_{AUDIT_DATE}.csv` contains every monthly cell, both values, delta, source L/P/Q/V/W, reference row/formula, classification, decision, and allowed action.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def history_payload(rows: list[dict[str, Any]]) -> str:
    """Return a stable digest payload, independent of the execution timestamp."""
    return json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def display_path(path: Path) -> str:
    """Use repository-relative paths where possible, without restricting tests/users."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def fiscal_year_number(value: Any) -> int:
    """Normalize ledger labels such as ``FY2026`` before DB storage."""
    digits = re.sub(r"\D", "", str(value))
    if len(digits) != 4:
        raise ValueError(f"Invalid fiscal year for audit history: {value!r}")
    return int(digits)


def archive_audit_history(
    rows: list[dict[str, Any]],
    *,
    audit_date: str,
    matrix_csv_path: Path,
    matrix_report_path: Path,
    history_dir: Path,
    history_db: Path,
) -> tuple[str, Path]:
    """Persist an immutable, user-readable audit snapshot and queryable DB log.

    The dated decision-matrix files remain useful as the current view, but are
    overwritten when an audit is repeated on the same day.  This function is
    deliberately append-only: every invocation receives its own run id and
    preserves the exact rows, evidence and classification available then.
    """
    payload = history_payload(rows)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    executed_at = datetime.now(timezone.utc).replace(microsecond=0)
    base_run_id = f"fa-{executed_at.strftime('%Y%m%dT%H%M%SZ')}-{digest[:12]}"
    run_id = base_run_id
    snapshot_dir = history_dir / run_id
    sequence = 2
    while snapshot_dir.exists():
        run_id = f"{base_run_id}-{sequence}"
        snapshot_dir = history_dir / run_id
        sequence += 1
    snapshot_dir.mkdir(parents=True, exist_ok=False)
    snapshot_csv = snapshot_dir / matrix_csv_path.name
    snapshot_report = snapshot_dir / matrix_report_path.name
    shutil.copy2(matrix_csv_path, snapshot_csv)
    shutil.copy2(matrix_report_path, snapshot_report)

    classifications = Counter(row["evidence_classification"] for row in rows)
    decisions = Counter(row["decision_status"] for row in rows)
    manifest = {
        "run_id": run_id,
        "audit_date": audit_date,
        "executed_at_utc": executed_at.isoformat(),
        "matrix_sha256": digest,
        "cells": len(rows),
        "classifications": dict(sorted(classifications.items())),
        "decision_statuses": dict(sorted(decisions.items())),
        "current_matrix_csv": display_path(matrix_csv_path),
        "current_matrix_report": display_path(matrix_report_path),
        "snapshot_csv": display_path(snapshot_csv),
        "snapshot_report": display_path(snapshot_report),
    }
    (snapshot_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    index_row = {
        "run_id": run_id,
        "audit_date": audit_date,
        "executed_at_utc": executed_at.isoformat(),
        "matrix_sha256": digest,
        "cells": len(rows),
        "classification_summary": json.dumps(dict(sorted(classifications.items())), ensure_ascii=False),
        "decision_summary": json.dumps(dict(sorted(decisions.items())), ensure_ascii=False),
        "snapshot_dir": display_path(snapshot_dir),
    }
    conn: sqlite3.Connection = get_connection(str(history_db))
    try:
        create_schema(conn)
        conn.execute(
            """
            INSERT INTO audit_fixed_asset_mismatch_runs
            (run_id, audit_date, executed_at, matrix_sha256, matrix_csv_path,
             matrix_report_path, history_snapshot_dir, summary_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                audit_date,
                executed_at.isoformat(),
                digest,
                display_path(matrix_csv_path),
                display_path(matrix_report_path),
                display_path(snapshot_dir),
                json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            ),
        )
        conn.executemany(
            """
            INSERT INTO audit_fixed_asset_mismatch_history
            (run_id, fiscal_year, cc_code, account_code, period, expected_vnd,
             reference_vnd, delta_vnd, reference_formula_kind,
             source_asset_count, evidence_classification, decision_status,
             allowed_action, classification_reason, source_evidence_json,
             reference_evidence_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    run_id,
                    fiscal_year_number(row["fy"]),
                    row["cc"],
                    int(row["account"]),
                    row["period"],
                    row["expected_per_asset_round_vnd"],
                    row["reference_actual_vnd"],
                    row["delta_reference_minus_expected_vnd"],
                    row["reference_formula_kind"],
                    row["source_asset_count_in_group"],
                    row["evidence_classification"],
                    row["decision_status"],
                    row["allowed_action"],
                    row["classification_reason"],
                    json.dumps(row["source_asset_evidence"], ensure_ascii=False, sort_keys=True),
                    json.dumps(row["reference_evidence"], ensure_ascii=False, sort_keys=True),
                )
                for row in rows
            ],
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    index_path = history_dir / "run_index.csv"
    write_header = not index_path.exists()
    with index_path.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(index_row))
        if write_header:
            writer.writeheader()
        writer.writerow(index_row)
    return run_id, snapshot_dir


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--history-dir",
        type=Path,
        default=AUDIT_DIR / "history" / "fixed_assets",
        help="Append-only folder for immutable audit snapshots.",
    )
    parser.add_argument(
        "--history-db",
        type=Path,
        default=ROOT / "mp2027.db",
        help="SQLite database that stores queryable mismatch history.",
    )
    parser.add_argument(
        "--skip-history",
        action="store_true",
        help="Regenerate only the current matrix; do not create a history record.",
    )
    args = parser.parse_args()
    ledger = read_csv(f"fixed_assets_asset_ledger_{AUDIT_DATE}.csv")
    references = read_csv(f"fixed_assets_reference_rows_{AUDIT_DATE}.csv")
    comparisons = read_csv(f"fixed_assets_monthly_comparison_{AUDIT_DATE}.csv")
    true_rows = [row for row in comparisons if row["classification"] == "TRUE_AMOUNT_MISMATCH"]
    source_by_key = source_assets_by_key(ledger)
    reference_by_key = selected_reference_by_key(references)
    all_source_asset_numbers = {str(row["asset_no"]) for row in ledger if row["asset_no"] not in ("", "None")}
    group_deltas = group_delta_pattern(comparisons)
    comparison_by_key_period = {
        (row["fy"], row["cc"], int(row["account"]), row["period"]): row for row in comparisons
    }
    matrix: list[dict[str, Any]] = []
    for row in true_rows:
        key = (row["fy"], row["cc"], int(row["account"]))
        source_rows = source_by_key.get(key, [])
        reference_rows = reference_by_key.get(key, [])
        classification, decision, action, reason = classify_row(
            row,
            source_rows,
            reference_rows,
            all_source_asset_numbers,
            group_deltas.get(key, set()),
            comparison_by_key_period,
        )
        components = reference_components(reference_rows, row["period"])
        matrix.append(
            {
                "fy": row["fy"],
                "cc": row["cc"],
                "account": int(row["account"]),
                "period": row["period"],
                "expected_per_asset_round_vnd": as_int(row["expected_per_asset_round_vnd"]),
                "reference_actual_vnd": as_int(row["reference_actual_vnd"]),
                "delta_reference_minus_expected_vnd": as_int(row["delta_reference_minus_expected"]),
                "reference_formula_kind": formula_kind(reference_rows, row["period"]),
                "source_asset_count_in_group": len(source_rows),
                "source_asset_evidence": source_components(source_rows, int(row["account"]), row["period"]),
                "reference_evidence": components,
                "evidence_classification": classification,
                "decision_status": decision,
                "allowed_action": action,
                "classification_reason": reason,
            }
        )
    if len(matrix) != 638:
        raise RuntimeError(f"Expected 638 TRUE_AMOUNT_MISMATCH cells, found {len(matrix)}")
    if any(row["decision_status"] not in VALID_DECISIONS for row in matrix):
        raise RuntimeError("Decision matrix contains an invalid decision status")
    missing_provenance = [
        row
        for row in matrix
        if not row["source_asset_evidence"] or not row["reference_evidence"]
    ]
    if missing_provenance:
        sample = [
            {
                "fy": row["fy"], "cc": row["cc"], "account": row["account"], "period": row["period"],
                "has_source": bool(row["source_asset_evidence"]),
                "has_reference": bool(row["reference_evidence"]),
            }
            for row in missing_provenance[:10]
        ]
        raise RuntimeError(f"Decision rows missing provenance: {sample}")
    fields = [
        "fy", "cc", "account", "period", "expected_per_asset_round_vnd", "reference_actual_vnd",
        "delta_reference_minus_expected_vnd", "reference_formula_kind", "source_asset_count_in_group",
        "source_asset_evidence", "reference_evidence", "evidence_classification", "decision_status",
        "allowed_action", "classification_reason",
    ]
    csv_path = AUDIT_DIR / f"fixed_assets_true_mismatch_decision_matrix_{AUDIT_DATE}.csv"
    report_path = AUDIT_DIR / f"fixed_assets_true_mismatch_decision_matrix_{AUDIT_DATE}.md"
    write_csv(csv_path, matrix, fields)
    write_report(report_path, matrix)
    if not args.skip_history:
        run_id, snapshot_dir = archive_audit_history(
            matrix,
            audit_date=AUDIT_DATE,
            matrix_csv_path=csv_path,
            matrix_report_path=report_path,
            history_dir=args.history_dir.resolve(),
            history_db=args.history_db.resolve(),
        )
        print(f"WROTE history run {run_id}: {snapshot_dir}")
    print(f"WROTE {csv_path}")
    print(f"WROTE {report_path}")
    print(json.dumps({"cells": len(matrix), "classifications": Counter(row["evidence_classification"] for row in matrix), "decisions": Counter(row["decision_status"] for row in matrix)}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
