"""
Manual headcount parser.

Users can provide monthly staff/worker headcount by CC in:
  source_dir/headcount_manual.csv

CSV columns:
  cc_code,period,headcount_staff,headcount_worker,description
"""

import csv
import os
import sqlite3
from pathlib import Path
from typing import Any

from src.utils.excel_helpers import get_fy_months, normalize_cc_code, safe_float

TEMPLATE_FILENAME = "headcount_manual.csv"
BUS_DRIVER_FILENAME = "bus_headcount_manual.csv"
REQUIRED_COLUMNS = ("cc_code", "period", "headcount_staff", "headcount_worker")
OPTIONAL_COLUMNS = ("headcount_male", "headcount_female")
MANUAL_HEADCOUNT_COLUMNS = (*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS, "description")
BUS_DRIVER_COLUMNS = ("cc_code", "bus_expat_count", "bus_vietnamese_count", "description")


def resolve_manual_headcount_source_dir(source_dir: str | None = None, base_dir: str | None = None) -> str:
    """Resolve the active manual headcount folder.

    In the checked-out project, raw/ is the canonical manual CSV input area.
    If the user points the general source folder at docs/MP2027, keep business
    workbook loading there but read/write manual headcount from raw/.
    Custom source folders are left unchanged.
    """
    requested = Path(source_dir or os.getcwd()).expanduser()
    try:
        requested = requested.resolve()
    except OSError:
        requested = Path(os.path.abspath(str(requested)))

    project_root = Path(base_dir).expanduser() if base_dir else Path(__file__).resolve().parents[2]
    try:
        project_root = project_root.resolve()
    except OSError:
        project_root = Path(os.path.abspath(str(project_root)))

    raw_dir = project_root / "raw"
    docs_dir = project_root / "docs" / "MP2027"
    if requested in {project_root, docs_dir}:
        return str(raw_dir)
    return str(requested)


def get_required_headcount_periods(fiscal_year: int) -> list[str]:
    """Return baseline previous March plus the fiscal Apr-Mar months."""
    return [f"{fiscal_year - 1}03", *get_fy_months(fiscal_year)]


def _has_value(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _parse_non_negative_int(value: Any) -> int | None:
    text = str(value or "").strip()
    if text == "":
        return None
    if not text.isdecimal():
        return None
    parsed = int(text)
    return parsed if parsed >= 0 else None


def _normalize_period(raw_period: Any, valid_periods: set[str], fiscal_months: list[str]) -> str | None:
    if raw_period is None:
        return None
    text = str(raw_period).strip()
    if text in valid_periods:
        return text

    # Accept MM for fiscal month label, map only to FY months.
    # Baseline previous March must be entered explicitly as YYYYMM to avoid
    # ambiguity with FY March.
    if text.isdigit() and 1 <= int(text) <= 12:
        month = int(text)
        for period in fiscal_months:
            if int(period[-2:]) == month:
                return period
    return None


def ensure_manual_headcount_template(source_dir: str, fiscal_year: int) -> str:
    """Create template file if not found. Returns the template path."""
    path = os.path.join(source_dir, TEMPLATE_FILENAME)
    if os.path.exists(path):
        return path

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(MANUAL_HEADCOUNT_COLUMNS)
    return path


def ensure_manual_bus_headcount_template(source_dir: str) -> str:
    """Create the scalar bus headcount driver template if not found."""
    path = os.path.join(source_dir, BUS_DRIVER_FILENAME)
    if os.path.exists(path):
        return path

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(BUS_DRIVER_COLUMNS)
    return path


def _parse_manual_bus_headcount(conn: sqlite3.Connection, source_dir: str, valid_cc_codes: set[str]) -> dict[str, int | str]:
    """Load scalar per-CC bus passenger counts used by the allocation engine."""
    path = ensure_manual_bus_headcount_template(source_dir)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fact_bus_headcount_drivers WHERE source = 'manual'")

    inserted = 0
    skipped = 0
    errors = 0

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return {"inserted": 0, "skipped": 0, "errors": 1, "template_path": path}

        missing_cols = [c for c in BUS_DRIVER_COLUMNS if c not in reader.fieldnames]
        if missing_cols:
            return {
                "inserted": 0,
                "skipped": 0,
                "errors": 1,
                "template_path": path,
                "error_message": f"Missing required columns: {', '.join(missing_cols)}",
            }

        seen_cc: set[str] = set()
        for row in reader:
            raw_values = [str(row.get(col, "") or "").strip() for col in BUS_DRIVER_COLUMNS]
            if not any(raw_values):
                skipped += 1
                continue

            cc_code = normalize_cc_code(row.get("cc_code"))
            if not cc_code or cc_code not in valid_cc_codes or cc_code in seen_cc:
                errors += 1
                continue

            expat_count = _parse_non_negative_int(row.get("bus_expat_count"))
            vietnamese_count = _parse_non_negative_int(row.get("bus_vietnamese_count"))
            if expat_count is None or vietnamese_count is None:
                errors += 1
                continue

            description = str(row.get("description", "") or "").strip()
            cursor.execute(
                """
                INSERT INTO fact_bus_headcount_drivers
                (cc_code, bus_expat_count, bus_vietnamese_count, source, description)
                VALUES (?, ?, ?, 'manual', ?)
                ON CONFLICT(cc_code) DO UPDATE SET
                    bus_expat_count = excluded.bus_expat_count,
                    bus_vietnamese_count = excluded.bus_vietnamese_count,
                    source = excluded.source,
                    description = excluded.description
                """,
                (cc_code, float(expat_count), float(vietnamese_count), description),
            )
            seen_cc.add(cc_code)
            inserted += 1

    return {"inserted": inserted, "skipped": skipped, "errors": errors, "template_path": path}


def parse_manual_headcount(
    conn: sqlite3.Connection,
    source_dir: str | None = None,
    base_dir: str | None = None,
) -> dict[str, int | str]:
    """Load manual headcount from CSV and write to fact_monthly_headcount source='manual'."""
    fy_row = conn.execute("SELECT value FROM sys_params WHERE key='fiscal_year'").fetchone()
    fiscal_year = int(str(fy_row[0]).upper().replace("FY", "").strip()) if fy_row else 2027
    fiscal_months = get_fy_months(fiscal_year)
    valid_periods = set(get_required_headcount_periods(fiscal_year))

    search_dir = resolve_manual_headcount_source_dir(source_dir, base_dir=base_dir)
    os.makedirs(search_dir, exist_ok=True)
    template_path = ensure_manual_headcount_template(search_dir, fiscal_year)
    if not os.path.exists(template_path):
        return {"inserted": 0, "skipped": 0, "errors": 0, "template_path": template_path}

    valid_cc_codes = {str(row[0]).strip() for row in conn.execute("SELECT code FROM dim_cost_centers").fetchall() if row[0] is not None}
    bus_result = _parse_manual_bus_headcount(conn, search_dir, valid_cc_codes)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fact_monthly_headcount WHERE source = 'manual'")

    inserted = 0
    skipped = 0
    errors = 0

    with open(template_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return {"inserted": 0, "skipped": 0, "errors": 1, "template_path": template_path}

        missing_cols = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing_cols:
            return {
                "inserted": 0,
                "skipped": 0,
                "errors": 1,
                "template_path": template_path,
                "error_message": f"Missing required columns: {', '.join(missing_cols)}",
            }

        for row in reader:
            raw_cc = str(row.get("cc_code", "")).strip()
            raw_period = row.get("period", "")
            raw_staff = row.get("headcount_staff", "")
            raw_worker = row.get("headcount_worker", "")
            raw_male = row.get("headcount_male", "")
            raw_female = row.get("headcount_female", "")
            description = str(row.get("description", "") or "").strip()

            # Allow blank rows in template.
            if (
                not raw_cc
                and not str(raw_period).strip()
                and not str(raw_staff).strip()
                and not str(raw_worker).strip()
                and not str(raw_male).strip()
                and not str(raw_female).strip()
            ):
                skipped += 1
                continue

            cc_code = normalize_cc_code(raw_cc)
            if not cc_code:
                errors += 1
                continue
            if cc_code not in valid_cc_codes:
                errors += 1
                continue

            period = _normalize_period(raw_period, valid_periods, fiscal_months)
            if period is None:
                errors += 1
                continue
            if not _has_value(raw_staff) or not _has_value(raw_worker):
                errors += 1
                continue

            staff = safe_float(raw_staff)
            worker = safe_float(raw_worker)
            male = safe_float(raw_male)
            female = safe_float(raw_female)
            if staff < 0 or worker < 0 or male < 0 or female < 0:
                errors += 1
                continue

            headcount_all = staff + worker
            if headcount_all <= 0:
                skipped += 1
                continue
            if male + female > headcount_all:
                errors += 1
                continue

            cursor.execute(
                """
                INSERT INTO fact_monthly_headcount
                (
                    period, cc_code, headcount_all, headcount_staff, headcount_worker,
                    headcount_male, headcount_female, source, description
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'manual', ?)
                ON CONFLICT(period, cc_code, source) DO UPDATE SET
                    headcount_all = excluded.headcount_all,
                    headcount_staff = excluded.headcount_staff,
                    headcount_worker = excluded.headcount_worker,
                    headcount_male = excluded.headcount_male,
                    headcount_female = excluded.headcount_female,
                    description = excluded.description
                """,
                (period, cc_code, headcount_all, staff, worker, male, female, description),
            )
            inserted += 1

    conn.commit()
    return {
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors + int(bus_result.get("errors", 0)),
        "template_path": template_path,
        "bus_inserted": int(bus_result.get("inserted", 0)),
        "bus_errors": int(bus_result.get("errors", 0)),
        "bus_template_path": str(bus_result.get("template_path", "")),
    }
