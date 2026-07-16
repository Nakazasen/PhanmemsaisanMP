"""Persistent manual staffing overrides used by the GUI and pipeline."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import sqlite3
from pathlib import Path
import json
from hashlib import sha256

from src.utils.fiscal_periods import fiscal_baseline_period, fiscal_periods

TIME_FIELDS = (
    "fixed_hours_expat", "fixed_hours_local",
    "overtime_hours_expat", "overtime_hours_local",
)


_MANUAL_TABLES = (
    "fact_manual_headcount_time_override",
    "fact_manual_headcount_baseline_override",
    "fact_bus_headcount_drivers",
)


def _table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _copy_manual_rows(
    target_conn: sqlite3.Connection,
    source: sqlite3.Connection,
    fiscal_year: int,
    *,
    allow_legacy_unscoped_rows: bool,
) -> dict[str, int]:
    """Copy rows for one FY only, adding the explicit FY stamp in the run DB.

    ``allow_legacy_unscoped_rows`` is intentionally private to the one-time
    FY2027 migration.  Normal runs never infer a year from an unscoped row.
    """
    result = {table: 0 for table in _MANUAL_TABLES}
    target_conn.row_factory = sqlite3.Row
    for table in _MANUAL_TABLES:
        exists = source.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not exists:
            continue
        source_columns = _table_columns(source, table)
        target_columns = _table_columns(target_conn, table)
        shared_columns = [column for column in source_columns if column in target_columns and column != "fiscal_year"]
        insert_columns = [*shared_columns, "fiscal_year"]
        if "fiscal_year" in source_columns:
            where = "fiscal_year=?"
            params: list[object] = [int(fiscal_year)]
        elif allow_legacy_unscoped_rows:
            where = "1=1"
            params = []
        else:
            # A normal annual store must contain a year stamp.  This prevents
            # data copied from a manually selected FY folder leaking into the
            # current run simply because its periods happen to overlap.
            continue
        if table != "fact_bus_headcount_drivers":
            periods = [fiscal_baseline_period(fiscal_year), *fiscal_periods(fiscal_year)]
            where += " AND period IN (" + ",".join("?" for _ in periods) + ")"
            params.extend(periods)
        rows = source.execute(f"SELECT * FROM {table} WHERE {where}", params).fetchall()
        if not rows:
            continue
        placeholders = ",".join("?" for _ in insert_columns)
        target_conn.executemany(
            f"INSERT OR REPLACE INTO {table} ({','.join(insert_columns)}) VALUES ({placeholders})",
            [
                tuple(row[column] for column in shared_columns) + (int(fiscal_year),)
                for row in rows
            ],
        )
        result[table] = len(rows)
    target_conn.commit()
    return result


def copy_annual_manual_inputs(
    target_conn: sqlite3.Connection,
    fiscal_year: int,
    manual_input_store: str | Path | None,
) -> dict[str, int]:
    """Copy only the selected FY's user-entered inputs into an isolated run DB.

    The source database is never attached for calculation.  This makes a run
    reproducible while keeping the editable business input store outside its
    immutable run workspace.
    """
    result = {table: 0 for table in _MANUAL_TABLES}
    if not manual_input_store:
        return result
    source_path = Path(manual_input_store)
    if not source_path.is_file():
        return result
    source = sqlite3.connect(source_path)
    source.row_factory = sqlite3.Row
    try:
        result = _copy_manual_rows(
            target_conn, source, int(fiscal_year), allow_legacy_unscoped_rows=False
        )
    finally:
        source.close()
    return result


def migrate_legacy_fy2027_manual_inputs(
    manual_input_store: str | Path,
    legacy_database: str | Path,
) -> dict[str, int]:
    """One-time, non-destructive migration from the old shared FY2027 store."""
    destination = Path(manual_input_store)
    legacy = Path(legacy_database)
    receipt = destination.with_name("manual_inputs_migration_fy2027.json")
    if not legacy.is_file():
        return {table: 0 for table in _MANUAL_TABLES}
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Local import avoids a schema dependency at module import time.
    from src.db.schema import create_schema, get_connection

    target = get_connection(str(destination))
    try:
        create_schema(target)
        # Earlier delivered FY2027 annual stores did not yet carry the
        # fiscal-year field.  They live in the FY2027 folder, so this one-time
        # schema migration can safely stamp their rows before strict copying
        # is enforced for every later year.
        for table in _MANUAL_TABLES:
            target.execute(
                f"UPDATE {table} SET fiscal_year=2027 WHERE fiscal_year IS NULL OR fiscal_year=0"
            )
        target.commit()
        if receipt.exists():
            return {table: 0 for table in _MANUAL_TABLES}
        source = sqlite3.connect(legacy)
        source.row_factory = sqlite3.Row
        try:
            result = _copy_manual_rows(
                target, source, 2027, allow_legacy_unscoped_rows=True
            )
        finally:
            source.close()
    finally:
        target.close()
    digest = sha256(legacy.read_bytes()).hexdigest()
    receipt.write_text(json.dumps({
        "fiscal_year": 2027,
        "legacy_database": str(legacy.resolve()),
        "legacy_sha256": digest,
        "copied_rows": result,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def normalize_manual_time_rows(periods: Sequence[str], values_by_period: Mapping[str, Mapping[str, object]]) -> list[dict]:
    """Validate manual time values; blank cells intentionally mean zero."""
    rows = []
    for period in periods:
        values = values_by_period.get(str(period), {})
        row = {"period": str(period)}
        for field in TIME_FIELDS:
            raw = str(values.get(field, "") or "").strip().replace(",", ".")
            if raw == "":
                value = 0.0
            else:
                try:
                    value = float(raw)
                except ValueError as exc:
                    raise ValueError(f"{field} kỳ {period} phải là số không âm") from exc
            if value < 0:
                raise ValueError(f"{field} kỳ {period} phải là số không âm")
            row[field] = value
        rows.append(row)
    return rows


def apply_manual_time_overrides(conn: sqlite3.Connection, fiscal_year: int, target_cc: object | None = None) -> int:
    """Overlay persisted manual time rows after department workbook imports."""
    periods = fiscal_periods(fiscal_year)
    placeholders = ",".join("?" for _ in periods)
    target_clause = "AND CAST(cc_code AS TEXT)=?" if target_cc is not None else ""
    params = [*periods]
    if target_cc is not None:
        params.append(str(target_cc).strip())
    rows = conn.execute(
        f"""SELECT period,cc_code,fixed_hours_expat,fixed_hours_local,
                   overtime_hours_expat,overtime_hours_local,description
            FROM fact_manual_headcount_time_override
            WHERE fiscal_year=? AND period IN ({placeholders}) {target_clause}""", [int(fiscal_year), *params],
    ).fetchall()
    for row in rows:
        conn.execute(
            """INSERT INTO fact_headcount_time_source
               (period,cc_code,fixed_hours_expat,fixed_hours_local,
                overtime_hours_expat,overtime_hours_local,source_file,
                source_sheet,source_cells,imported_at)
               VALUES(?,?,?,?,?,?,'MANUAL_GUI','Nhập nhân sự thủ công',?,CURRENT_TIMESTAMP)
               ON CONFLICT(period,cc_code) DO UPDATE SET
                 fixed_hours_expat=excluded.fixed_hours_expat,
                 fixed_hours_local=excluded.fixed_hours_local,
                 overtime_hours_expat=excluded.overtime_hours_expat,
                 overtime_hours_local=excluded.overtime_hours_local,
                 source_file=excluded.source_file,
                 source_sheet=excluded.source_sheet,
                 source_cells=excluded.source_cells,
                 imported_at=CURRENT_TIMESTAMP""",
            (row["period"], row["cc_code"], row["fixed_hours_expat"], row["fixed_hours_local"],
             row["overtime_hours_expat"], row["overtime_hours_local"], row["description"] or "MANUAL_TIME_OVERRIDE"),
        )
    return len(rows)


def save_manual_time_overrides(conn: sqlite3.Connection, fiscal_year: int, cc_code: object, values_by_period: Mapping[str, Mapping[str, object]]) -> int:
    """Persist a complete 12-month manual series and apply it immediately."""
    periods = fiscal_periods(fiscal_year)
    rows = normalize_manual_time_rows(periods, values_by_period)
    cc = str(cc_code).strip()
    placeholders = ",".join("?" for _ in periods)
    conn.execute(
        f"DELETE FROM fact_manual_headcount_time_override WHERE fiscal_year=? AND CAST(cc_code AS TEXT)=? AND period IN ({placeholders})",
        (int(fiscal_year), cc, *periods),
    )
    conn.executemany(
        """INSERT INTO fact_manual_headcount_time_override
           (period,cc_code,fiscal_year,fixed_hours_expat,fixed_hours_local,
            overtime_hours_expat,overtime_hours_local,description,updated_at)
           VALUES(?,?,?,?,?,?,?, ?,CURRENT_TIMESTAMP)""",
        [(row["period"], cc, int(fiscal_year), row["fixed_hours_expat"], row["fixed_hours_local"],
          row["overtime_hours_expat"], row["overtime_hours_local"], "MANUAL_TIME_OVERRIDE_BLANK_AS_ZERO")
         for row in rows],
    )
    return apply_manual_time_overrides(conn, fiscal_year, target_cc=cc)


def apply_manual_baseline_overrides(conn: sqlite3.Connection, fiscal_year: int, target_cc: object | None = None) -> int:
    """Restore persistent baseline overrides after the manual CSV parser runs."""
    baseline = fiscal_baseline_period(fiscal_year)
    target_clause = "AND CAST(cc_code AS TEXT)=?" if target_cc is not None else ""
    params = [baseline]
    if target_cc is not None:
        params.append(str(target_cc).strip())
    rows = conn.execute(
        f"SELECT * FROM fact_manual_headcount_baseline_override WHERE fiscal_year=? AND period=? {target_clause}", [int(fiscal_year), *params],
    ).fetchall()
    for row in rows:
        conn.execute(
            """INSERT INTO fact_monthly_headcount
               (period,cc_code,headcount_all,headcount_expat,headcount_staff,
                headcount_worker,headcount_male,headcount_female,split_status,
                headcount_local_total,source,description,source_file,source_sheet,imported_at)
               SELECT ?,?,?,?,?,?,?,?,?,?,'manual',?,?,?,CURRENT_TIMESTAMP
               WHERE NOT EXISTS(
                 SELECT 1 FROM fact_monthly_headcount
                 WHERE period=? AND CAST(cc_code AS TEXT)=? AND source='manual'
               )""",
            (row["period"], row["cc_code"], row["headcount_all"], row["headcount_expat"],
             row["headcount_staff"], row["headcount_worker"], row["headcount_male"], row["headcount_female"],
             row["split_status"], row["headcount_local_total"], row["description"], row["source_file"],
             row["source_sheet"], row["period"], row["cc_code"]),
        )
    return len(rows)


def save_manual_baseline_override(conn: sqlite3.Connection, fiscal_year: int, cc_code: object, expat: float, staff: float, worker: float, description: str = "") -> None:
    """Persist a user-entered T3 baseline and apply it immediately."""
    baseline = fiscal_baseline_period(fiscal_year)
    cc = str(cc_code).strip()
    local_total = float(staff) + float(worker)
    total = float(expat) + local_total
    conn.execute(
        """INSERT INTO fact_manual_headcount_baseline_override
           (period,cc_code,fiscal_year,headcount_all,headcount_expat,headcount_staff,
            headcount_worker,headcount_male,headcount_female,split_status,
            headcount_local_total,description,source_file,source_sheet,updated_at)
           VALUES(?,?,?,?,?,?,?,0,0,'READY',?,?,'MANUAL_GUI','Nhập nhân sự thủ công',CURRENT_TIMESTAMP)
           ON CONFLICT(period,cc_code) DO UPDATE SET
             headcount_all=excluded.headcount_all, headcount_expat=excluded.headcount_expat,
             headcount_staff=excluded.headcount_staff, headcount_worker=excluded.headcount_worker,
             split_status='READY', headcount_local_total=excluded.headcount_local_total,
             description=excluded.description, source_file=excluded.source_file,
             source_sheet=excluded.source_sheet, updated_at=CURRENT_TIMESTAMP""",
        (baseline, cc, int(fiscal_year), total, expat, staff, worker, local_total, description or "MANUAL_BASELINE_T3"),
    )
    conn.execute(
        "DELETE FROM fact_monthly_headcount WHERE period=? AND CAST(cc_code AS TEXT)=? AND source='manual'",
        (baseline, cc),
    )
    apply_manual_baseline_overrides(conn, fiscal_year, target_cc=cc)


def copy_missing_baselines_from_april(conn: sqlite3.Connection, fiscal_year: int, target_cc: object | None = None) -> list[str]:
    """Persist user-approved T4 staffing as T3 without overwriting observed T3."""
    baseline = fiscal_baseline_period(fiscal_year)
    april = fiscal_periods(fiscal_year)[0]
    target_clause = "AND CAST(april.cc_code AS TEXT)=?" if target_cc is not None else ""
    params = [baseline, april]
    if target_cc is not None:
        params.append(str(target_cc).strip())
    conn.execute(
        f"""INSERT INTO fact_manual_headcount_baseline_override
            (period,cc_code,fiscal_year,headcount_all,headcount_expat,headcount_staff,
             headcount_worker,headcount_male,headcount_female,split_status,
             headcount_local_total,description,source_file,source_sheet,updated_at)
            SELECT ?,april.cc_code,?,april.headcount_all,april.headcount_expat,
                   april.headcount_staff,april.headcount_worker,april.headcount_male,
                   april.headcount_female,april.split_status,april.headcount_local_total,
                   'USER_APPROVED_BASELINE_T3_FROM_T4',april.source_file,april.source_sheet,CURRENT_TIMESTAMP
            FROM fact_monthly_headcount AS april
            WHERE april.period=? AND april.source='department_plan' {target_clause}
              AND NOT EXISTS(SELECT 1 FROM fact_monthly_headcount AS baseline
                  WHERE baseline.period=? AND baseline.source='manual'
                    AND CAST(baseline.cc_code AS TEXT)=CAST(april.cc_code AS TEXT))
              AND NOT EXISTS(SELECT 1 FROM fact_manual_headcount_baseline_override AS saved
                  WHERE saved.fiscal_year=? AND saved.period=? AND CAST(saved.cc_code AS TEXT)=CAST(april.cc_code AS TEXT))""",
        [*params, int(fiscal_year), baseline, int(fiscal_year), baseline],
    )
    copied = [str(row[0]) for row in conn.execute(
        """SELECT CAST(cc_code AS TEXT) FROM fact_manual_headcount_baseline_override
           WHERE fiscal_year=? AND period=? AND description='USER_APPROVED_BASELINE_T3_FROM_T4' ORDER BY 1""", (int(fiscal_year), baseline)
    ).fetchall()]
    if target_cc is not None:
        copied = [cc for cc in copied if cc == str(target_cc).strip()]
    apply_manual_baseline_overrides(conn, fiscal_year, target_cc=target_cc)
    return copied


def find_missing_baseline_ccs(conn: sqlite3.Connection, fiscal_year: int, target_cc: object | None = None) -> list[str]:
    """Return calculation-scope CCs that do not have canonical manual T3."""
    baseline = fiscal_baseline_period(fiscal_year)
    if target_cc is not None:
        scope = [str(target_cc).strip()]
    else:
        scope = [str(row[0]) for row in conn.execute(
            "SELECT DISTINCT CAST(cc_code AS TEXT) FROM fact_input_data WHERE account_code > 0 ORDER BY 1"
        ).fetchall()]
    return [cc for cc in scope if conn.execute(
        """SELECT 1 FROM fact_monthly_headcount
           WHERE CAST(cc_code AS TEXT)=? AND period=? AND source='manual' LIMIT 1""", (cc, baseline)
    ).fetchone() is None]
