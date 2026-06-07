"""Shared account resolver for Cost Center -> cost type -> account column lookup."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


COST_TYPE_TO_ACCOUNT_COLUMN = {
    "製造": "mfg_code",
    "一般": "ga_code",
    "販売": "sales_code",
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
        row = conn.execute(
            f"SELECT {column} AS account_code FROM dim_accounts WHERE code = ?",
            (int(float(account_key)),),
        ).fetchone()
    else:
        rows = conn.execute(
            f"SELECT {column} AS account_code FROM dim_accounts WHERE name_jp = ?",
            (account_key,),
        ).fetchall()
        if len(rows) > 1:
            raise AccountResolutionError(f"Ambiguous account name for account lookup: {account_key}")
        row = rows[0] if rows else None

    if row is None:
        raise AccountResolutionError(f"Account not found for account lookup: {account_key}")
    value = row["account_code"]
    if not _is_valid_account_code(value):
        raise AccountResolutionError(
            f"Account {account_key!r} has no {column} value for cost type {cost_type!r}"
        )
    return int(float(value))


def resolve_account_code(db_path: str | Path, target_cc: int | str, account_key_or_name: int | str) -> int:
    """Resolve account_code using target CC cost type and dim_accounts.

    ``account_key_or_name`` may be an existing account code or an account Japanese
    name. The resolver never falls back to another cost-type column.
    """
    with _connect(db_path) as conn:
        return resolve_account_code_for_connection(conn, target_cc, account_key_or_name)
