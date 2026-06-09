"""Shared account resolver for Cost Center -> cost type -> account column lookup."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


COST_TYPE_TO_ACCOUNT_COLUMN = {
    "製造": "mfg_code",
    "一般": "ga_code",
    "販売": "sales_code",
}

ACCOUNT_STRATEGY_DIRECT_BY_CC = "direct_by_cc"
ACCOUNT_STRATEGY_SUMMARY_BY_CC = "summary_by_cc"
ACCOUNT_STRATEGY_CC_RESOLVER = "cc_resolver"
ACCOUNT_STRATEGY_FIXED_BASE_ACCOUNT = "fixed_base_account"
ACCOUNT_STRATEGY_FORM_ROW_BASE_ACCOUNT = "form_row_base_account"
ACCOUNT_STRATEGY_DESCRIPTION_BASE_ACCOUNT = "description_base_account"
ACCOUNT_STRATEGY_ALLOCATION_RULE = "allocation_rule"
ACCOUNT_STRATEGY_NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class SourceAccountPolicy:
    strategy: str
    cc_only: bool = True
    notes: str = ""
    fixed_form_row: int | None = None
    fixed_base_account_code: int | None = None
    base_account_by_form_row: Mapping[int, int] = field(default_factory=dict)
    base_account_by_description: Mapping[str, int | tuple[str, ...]] = field(default_factory=dict)


SOURCE_ACCOUNT_POLICIES: dict[str, SourceAccountPolicy] = {
    "nnn_paperwork": SourceAccountPolicy(
        strategy=ACCOUNT_STRATEGY_DIRECT_BY_CC,
        notes="Read account_code directly from source rows keyed by CC.",
    ),
    "manual_special_costs": SourceAccountPolicy(
        strategy=ACCOUNT_STRATEGY_DIRECT_BY_CC,
        notes="Manual override requires explicit CC + account_code.",
    ),
    "manual_event_driver": SourceAccountPolicy(
        strategy=ACCOUNT_STRATEGY_CC_RESOLVER,
        notes="Resolve account from CC cost_type plus explicit account code/name.",
    ),
    "it_sim": SourceAccountPolicy(
        strategy=ACCOUNT_STRATEGY_SUMMARY_BY_CC,
        fixed_base_account_code=5005246282,
        notes="Prefer summary-sheet CC->account mapping; fall back to system-cost master account.",
    ),
    "birthday_workbook": SourceAccountPolicy(
        strategy=ACCOUNT_STRATEGY_FIXED_BASE_ACCOUNT,
        fixed_form_row=59,
        fixed_base_account_code=5004086291,
        notes="Birthday cost resolves from one logical base account via CC cost_type.",
    ),
    "ga_admin_allocation": SourceAccountPolicy(
        strategy=ACCOUNT_STRATEGY_FORM_ROW_BASE_ACCOUNT,
        base_account_by_form_row={
            46: 5005056281,
            48: 5005016372,
            51: 5005246286,
            54: 5004086291,
            56: 5004086291,
            58: 5004086291,
            97: 5005246288,
            98: 5005246288,
        },
        notes="GA admin rows choose a logical base account by form_row, then resolve by CC cost_type.",
    ),
    "facility": SourceAccountPolicy(
        strategy=ACCOUNT_STRATEGY_DESCRIPTION_BASE_ACCOUNT,
        base_account_by_description={
            "depreciation_building": 5006016260,
            "depreciation_land": 5006016261,
            "interest_building": 9114120007,
            "interest_land": 9114120007,
            "electric": ("電気", "electric", "điện"),
            "water": ("水道", "water", "nước"),
        },
        notes="Facility parser emits CC plus item type; account comes from source-specific description rules.",
    ),
    "fixed_assets": SourceAccountPolicy(
        strategy=ACCOUNT_STRATEGY_DESCRIPTION_BASE_ACCOUNT,
        base_account_by_description={
            "fixed_assets_depr|": 5006016244,
            "fixed_assets_interest|": 9114120007,
        },
        notes="Fixed-assets parser emits CC plus depreciation/interest descriptor.",
    ),
    "ga_unit_price": SourceAccountPolicy(
        strategy=ACCOUNT_STRATEGY_NOT_APPLICABLE,
        notes="Unit-price driver rows are consumed by fixed-row formulas, not exported as direct account lines.",
    ),
}


class AccountResolutionError(ValueError):
    """Raised when account resolution cannot be performed unambiguously."""


def _connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _is_valid_account_code(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return text not in {"", "0", "0.0"}


def get_source_account_policy(source: str) -> SourceAccountPolicy | None:
    source_text = str(source or "").strip()
    if not source_text:
        return None
    if source_text.startswith("alloc_"):
        return SourceAccountPolicy(
            strategy=ACCOUNT_STRATEGY_ALLOCATION_RULE,
            notes="Generated allocation row; account is already chosen from rule + CC cost_type.",
        )
    return SOURCE_ACCOUNT_POLICIES.get(source_text)


def _find_account_code_by_keywords(conn: sqlite3.Connection, keywords: tuple[str, ...]) -> int:
    rows = conn.execute("SELECT code, name_jp, name_vn FROM dim_accounts").fetchall()
    matches: list[int] = []
    for row in rows:
        haystack = f"{row['name_jp'] or ''} {row['name_vn'] or ''}".lower()
        if any(keyword.lower() in haystack for keyword in keywords):
            matches.append(int(row["code"]))

    unique_matches = sorted(set(matches))
    if not unique_matches:
        raise AccountResolutionError(f"Account not found for keyword lookup: {keywords}")
    if len(unique_matches) > 1:
        raise AccountResolutionError(f"Ambiguous account keywords for account lookup: {keywords}")
    return unique_matches[0]


def _candidate_rows_for_group_name(conn: sqlite3.Connection, group_name: str) -> list[sqlite3.Row]:
    if not group_name:
        return []
    return conn.execute(
        """
        SELECT code, name_jp, group_name, mfg_code, ga_code, sales_code
        FROM dim_accounts
        WHERE group_name = ?
        """,
        (group_name,),
    ).fetchall()


def _pick_row_for_cost_type_with_conn(
    conn: sqlite3.Connection, rows: list[sqlite3.Row], column: str, account_key: str
) -> sqlite3.Row | None:
    if not rows:
        return None

    valid_rows = [row for row in rows if _is_valid_account_code(row[column])]
    if len(valid_rows) == 1:
        return valid_rows[0]
    if len(valid_rows) > 1:
        raise AccountResolutionError(f"Ambiguous account rows for account lookup: {account_key}")

    group_names = sorted({str(row["group_name"] or "").strip() for row in rows if str(row["group_name"] or "").strip()})
    if len(group_names) == 1:
        sibling_rows = _candidate_rows_for_group_name(conn, group_names[0])
        sibling_valid_rows = [row for row in sibling_rows if _is_valid_account_code(row[column])]
        if len(sibling_valid_rows) == 1:
            return sibling_valid_rows[0]
        if len(sibling_valid_rows) > 1:
            raise AccountResolutionError(f"Ambiguous grouped account rows for account lookup: {account_key}")

    return rows[0]


def _find_account_row_by_numeric_key(conn: sqlite3.Connection, account_key: str, column: str) -> sqlite3.Row | None:
    numeric_key = int(float(account_key))
    rows = conn.execute(
        """
        SELECT code, name_jp, group_name, mfg_code, ga_code, sales_code
        FROM dim_accounts
        WHERE code = ? OR mfg_code = ? OR ga_code = ? OR sales_code = ?
        """,
        (numeric_key, numeric_key, numeric_key, numeric_key),
    ).fetchall()
    return _pick_row_for_cost_type_with_conn(conn, rows, column, account_key)


def _account_column_for_connection(conn: sqlite3.Connection, target_cc: int | str) -> tuple[str, str]:
    cc_text = str(target_cc or "").strip()
    if not cc_text:
        raise AccountResolutionError("Missing target cost center for account lookup")

    row = conn.execute(
        "SELECT cost_type FROM dim_cost_centers WHERE code = ?",
        (cc_text,),
    ).fetchone()
    if row is None:
        raise AccountResolutionError(f"Cost center not found for account lookup: {cc_text}")
    cost_type = str(row["cost_type"] or "").strip()
    if not cost_type:
        raise AccountResolutionError(f"Cost center has no cost_type for account lookup: {cc_text}")
    return cost_type, resolve_account_column_by_cost_type(cost_type)


def _resolve_source_base_account_code(
    conn: sqlite3.Connection,
    source: str,
    *,
    description: str | None = None,
    form_row: int | None = None,
) -> int:
    policy = get_source_account_policy(source)
    if policy is None:
        raise AccountResolutionError(f"Unsupported source for account policy lookup: {source}")

    if policy.fixed_base_account_code:
        return int(policy.fixed_base_account_code)

    if policy.base_account_by_form_row:
        if form_row is None:
            raise AccountResolutionError(f"Missing form_row for source account policy: {source}")
        account_code = policy.base_account_by_form_row.get(int(form_row))
        if account_code is None:
            raise AccountResolutionError(f"Unsupported form_row for source account policy: {source}:{form_row}")
        return int(account_code)

    if policy.base_account_by_description:
        description_text = str(description or "").strip().lower()
        for token, account_ref in policy.base_account_by_description.items():
            if token.lower() not in description_text:
                continue
            if isinstance(account_ref, tuple):
                return _find_account_code_by_keywords(conn, account_ref)
            return int(account_ref)
        raise AccountResolutionError(f"Unsupported description for source account policy: {source}:{description_text}")

    raise AccountResolutionError(f"Source account policy has no base-account resolver: {source}")


def resolve_account_column_by_cost_type(cost_type: str) -> str:
    """Return dim_accounts column for FORM cost type/原価区分."""
    text = str(cost_type or "").strip()
    for token, column in COST_TYPE_TO_ACCOUNT_COLUMN.items():
        if token in text:
            return column
    raise AccountResolutionError(f"Unsupported cost type for account lookup: {cost_type!r}")


def resolve_cost_type_for_connection(conn: sqlite3.Connection, target_cc: int | str) -> str:
    """Resolve 原価区分/cost_type using an existing SQLite connection."""
    cost_type, _ = _account_column_for_connection(conn, target_cc)
    return cost_type


def resolve_cost_type_for_cc(db_path: str | Path, target_cc: int | str) -> str:
    """Resolve 原価区分/cost_type for a target cost center from dim_cost_centers."""
    with _connect(db_path) as conn:
        return resolve_cost_type_for_connection(conn, target_cc)


def resolve_account_code_for_connection(
    conn: sqlite3.Connection, target_cc: int | str, account_key_or_name: int | str
) -> int:
    """Resolve account_code using an existing SQLite connection."""
    account_key = str(account_key_or_name or "").strip()
    if not account_key:
        raise AccountResolutionError("Missing account key/name for account lookup")

    cost_type, column = _account_column_for_connection(conn, target_cc)
    if account_key.replace(".", "", 1).isdigit():
        row = _find_account_row_by_numeric_key(conn, account_key, column)
    else:
        rows = conn.execute(
            """
            SELECT code, name_jp, group_name, mfg_code, ga_code, sales_code
            FROM dim_accounts
            WHERE name_jp = ? OR group_name = ?
            """,
            (account_key, account_key),
        ).fetchall()
        row = _pick_row_for_cost_type_with_conn(conn, rows, column, account_key)

    if row is None:
        raise AccountResolutionError(f"Account not found for account lookup: {account_key}")
    value = row[column]
    if not _is_valid_account_code(value):
        raise AccountResolutionError(
            f"Account {account_key!r} has no {column} value for cost type {cost_type!r}"
        )
    return int(float(value))


def resolve_account_code_for_source(
    conn: sqlite3.Connection,
    source: str,
    target_cc: int | str,
    *,
    description: str | None = None,
    form_row: int | None = None,
) -> int:
    """Resolve a source-specific account via CC-only policy metadata."""

    base_account_code = _resolve_source_base_account_code(
        conn,
        source,
        description=description,
        form_row=form_row,
    )
    return resolve_account_code_for_connection(conn, target_cc, base_account_code)


def resolve_account_code(db_path: str | Path, target_cc: int | str, account_key_or_name: int | str) -> int:
    """Resolve account_code using target CC cost type and dim_accounts.

    ``account_key_or_name`` may be an existing account code or an account Japanese
    name. The resolver never falls back to another cost-type column.
    """
    with _connect(db_path) as conn:
        return resolve_account_code_for_connection(conn, target_cc, account_key_or_name)
