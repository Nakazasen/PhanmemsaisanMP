"""Persistent manual staffing overrides used by the GUI and pipeline."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import sqlite3

from src.utils.fiscal_periods import fiscal_baseline_period, fiscal_periods

TIME_FIELDS = (
    "fixed_hours_expat", "fixed_hours_local",
    "overtime_hours_expat", "overtime_hours_local",
)


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
            WHERE period IN ({placeholders}) {target_clause}""", params,
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
        f"DELETE FROM fact_manual_headcount_time_override WHERE CAST(cc_code AS TEXT)=? AND period IN ({placeholders})",
        (cc, *periods),
    )
    conn.executemany(
        """INSERT INTO fact_manual_headcount_time_override
           (period,cc_code,fixed_hours_expat,fixed_hours_local,
            overtime_hours_expat,overtime_hours_local,description,updated_at)
           VALUES(?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
        [(row["period"], cc, row["fixed_hours_expat"], row["fixed_hours_local"],
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
        f"SELECT * FROM fact_manual_headcount_baseline_override WHERE period=? {target_clause}", params,
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
           (period,cc_code,headcount_all,headcount_expat,headcount_staff,
            headcount_worker,headcount_male,headcount_female,split_status,
            headcount_local_total,description,source_file,source_sheet,updated_at)
           VALUES(?,?,?,?,?,?,0,0,'READY',?,?,'MANUAL_GUI','Nhập nhân sự thủ công',CURRENT_TIMESTAMP)
           ON CONFLICT(period,cc_code) DO UPDATE SET
             headcount_all=excluded.headcount_all, headcount_expat=excluded.headcount_expat,
             headcount_staff=excluded.headcount_staff, headcount_worker=excluded.headcount_worker,
             split_status='READY', headcount_local_total=excluded.headcount_local_total,
             description=excluded.description, source_file=excluded.source_file,
             source_sheet=excluded.source_sheet, updated_at=CURRENT_TIMESTAMP""",
        (baseline, cc, total, expat, staff, worker, local_total, description or "MANUAL_BASELINE_T3"),
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
            (period,cc_code,headcount_all,headcount_expat,headcount_staff,
             headcount_worker,headcount_male,headcount_female,split_status,
             headcount_local_total,description,source_file,source_sheet,updated_at)
            SELECT ?,april.cc_code,april.headcount_all,april.headcount_expat,
                   april.headcount_staff,april.headcount_worker,april.headcount_male,
                   april.headcount_female,april.split_status,april.headcount_local_total,
                   'USER_APPROVED_BASELINE_T3_FROM_T4',april.source_file,april.source_sheet,CURRENT_TIMESTAMP
            FROM fact_monthly_headcount AS april
            WHERE april.period=? AND april.source='department_plan' {target_clause}
              AND NOT EXISTS(SELECT 1 FROM fact_monthly_headcount AS baseline
                  WHERE baseline.period=? AND baseline.source='manual'
                    AND CAST(baseline.cc_code AS TEXT)=CAST(april.cc_code AS TEXT))
              AND NOT EXISTS(SELECT 1 FROM fact_manual_headcount_baseline_override AS saved
                  WHERE saved.period=? AND CAST(saved.cc_code AS TEXT)=CAST(april.cc_code AS TEXT))""",
        [*params, baseline, baseline],
    )
    copied = [str(row[0]) for row in conn.execute(
        """SELECT CAST(cc_code AS TEXT) FROM fact_manual_headcount_baseline_override
           WHERE period=? AND description='USER_APPROVED_BASELINE_T3_FROM_T4' ORDER BY 1""", (baseline,)
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
