"""
Manual headcount parser.

Users can provide monthly staff/worker headcount by CC in the active input:
  raw/headcount_manual.csv

CSV columns:
  cc_code,period,headcount_staff,headcount_worker,description
"""

import csv
import os
import sqlite3
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.utils.excel_helpers import get_fy_months, normalize_cc_code

TEMPLATE_FILENAME = "headcount_manual.csv"
BUS_DRIVER_FILENAME = "bus_headcount_manual.csv"
LEGACY_HEADCOUNT_SOURCE_WARNING = "LEGACY_HEADCOUNT_SOURCE_IGNORED"
REQUIRED_COLUMNS = ("cc_code", "period", "headcount_staff", "headcount_worker")
OPTIONAL_COLUMNS = ("headcount_male", "headcount_female")
MANUAL_HEADCOUNT_COLUMNS = (*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS, "description")
BUS_DRIVER_COLUMNS = ("cc_code", "bus_expat_count", "bus_vietnamese_count", "description")


def _warn_legacy_headcount_source(requested: Path, raw_dir: Path) -> None:
    warnings.warn(
        f"{LEGACY_HEADCOUNT_SOURCE_WARNING}: {requested} is not active; using {raw_dir}",
        RuntimeWarning,
        stacklevel=3,
    )


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
    if requested == project_root:
        return str(raw_dir)
    if requested == docs_dir:
        _warn_legacy_headcount_source(requested, raw_dir)
        return str(raw_dir)
    if requested.name == TEMPLATE_FILENAME:
        if requested.parent == docs_dir:
            _warn_legacy_headcount_source(requested, raw_dir)
            return str(raw_dir)
        if requested.parent == raw_dir:
            return str(raw_dir)
        return str(requested.parent)
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


def _make_validation_error(
    row_number: int | None,
    cc_code: Any,
    period: Any,
    field: str,
    raw_value: Any,
    validation_rule: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "csv_row": row_number,
        "cc_code": str(cc_code or "").strip(),
        "period": str(period or "").strip(),
        "field": field,
        "raw_value": "" if raw_value is None else str(raw_value),
        "validation_rule": validation_rule,
        "reason": reason,
        "csv_row_written": True,
        "db_row_inserted": False,
    }


def _parse_required_headcount_int(
    row_number: int | None,
    row: dict[str, Any],
    field: str,
    reason_label: str,
) -> tuple[int | None, dict[str, Any] | None]:
    raw_value = row.get(field, "")
    if not _has_value(raw_value):
        return None, _make_validation_error(
            row_number,
            row.get("cc_code"),
            row.get("period"),
            field,
            raw_value,
            "REQUIRED",
            f"Missing {reason_label} value",
        )
    parsed = _parse_non_negative_int(raw_value)
    if parsed is None:
        return None, _make_validation_error(
            row_number,
            row.get("cc_code"),
            row.get("period"),
            field,
            raw_value,
            "INTEGER_GTE_0",
            f"{reason_label.capitalize()} must be an integer >= 0",
        )
    return parsed, None


def _parse_optional_headcount_int(
    row_number: int | None,
    row: dict[str, Any],
    field: str,
    reason_label: str,
) -> tuple[int, dict[str, Any] | None]:
    raw_value = row.get(field, "")
    if not _has_value(raw_value):
        return 0, None
    parsed = _parse_non_negative_int(raw_value)
    if parsed is None:
        return 0, _make_validation_error(
            row_number,
            row.get("cc_code"),
            row.get("period"),
            field,
            raw_value,
            "INTEGER_GTE_0",
            f"{reason_label.capitalize()} must be an integer >= 0",
        )
    return parsed, None


def validate_manual_headcount_rows(
    rows: list[dict[str, Any]],
    valid_cc_codes: set[str],
    fiscal_year: int = 2027,
) -> dict[str, Any]:
    """Validate manual headcount rows without mutating CSV or DB."""
    fiscal_months = get_fy_months(fiscal_year)
    valid_periods = set(get_required_headcount_periods(fiscal_year))
    valid_rows: list[dict[str, Any]] = []
    skipped = 0
    error_details: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()

    for index, row in enumerate(rows, start=2):
        row_number = row.get("_csv_row", index)
        try:
            row_number = int(row_number)
        except (TypeError, ValueError):
            row_number = index

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
            error_details.append(
                _make_validation_error(row_number, raw_cc, raw_period, "cc_code", raw_cc, "VALID_CC", "Cost center is blank or invalid")
            )
            continue
        if cc_code not in valid_cc_codes:
            error_details.append(
                _make_validation_error(
                    row_number,
                    raw_cc,
                    raw_period,
                    "cc_code",
                    raw_cc,
                    "VALID_CC",
                    "Cost center is not in dim_cost_centers",
                )
            )
            continue

        period = _normalize_period(raw_period, valid_periods, fiscal_months)
        if period is None:
            error_details.append(
                _make_validation_error(
                    row_number,
                    raw_cc,
                    raw_period,
                    "period",
                    raw_period,
                    "VALID_PERIOD",
                    "Period is not in required fiscal-year period set",
                )
            )
            continue
        key = (cc_code, period)
        if key in seen_keys:
            error_details.append(
                _make_validation_error(
                    row_number,
                    raw_cc,
                    raw_period,
                    "cc_code/period",
                    f"{raw_cc}/{raw_period}",
                    "UNIQUE_CC_PERIOD",
                    "Duplicate manual headcount cost center and period",
                )
            )
            continue
        seen_keys.add(key)

        staff, staff_error = _parse_required_headcount_int(row_number, row, "headcount_staff", "staff")
        worker, worker_error = _parse_required_headcount_int(row_number, row, "headcount_worker", "worker")
        male, male_error = _parse_optional_headcount_int(row_number, row, "headcount_male", "male")
        female, female_error = _parse_optional_headcount_int(row_number, row, "headcount_female", "female")
        row_errors = [error for error in (staff_error, worker_error, male_error, female_error) if error]
        if row_errors:
            error_details.extend(row_errors)
            continue

        assert staff is not None
        assert worker is not None
        headcount_all = staff + worker
        if male + female > headcount_all:
            error_details.append(
                _make_validation_error(
                    row_number,
                    raw_cc,
                    raw_period,
                    "headcount_male/headcount_female",
                    f"{raw_male}/{raw_female}",
                    "SUM_LE_TOTAL",
                    "Male + female exceeds staff + worker",
                )
            )
            continue

        valid_rows.append(
            {
                "period": period,
                "cc_code": cc_code,
                "headcount_all": float(headcount_all),
                "headcount_staff": float(staff),
                "headcount_worker": float(worker),
                "headcount_male": float(male),
                "headcount_female": float(female),
                "description": description,
            }
        )

    return {
        "valid_rows": valid_rows,
        "skipped": skipped,
        "errors": len(error_details),
        "error_details": error_details,
    }


def validate_manual_bus_headcount_rows(
    rows: list[dict[str, Any]],
    valid_cc_codes: set[str],
) -> dict[str, Any]:
    """Validate scalar bus passenger rows without mutating DB."""
    valid_rows: list[dict[str, Any]] = []
    skipped = 0
    errors = 0
    error_details: list[dict[str, Any]] = []
    seen_cc: set[str] = set()

    for index, row in enumerate(rows, start=2):
        row_number = row.get("_csv_row", index)
        try:
            row_number = int(row_number)
        except (TypeError, ValueError):
            row_number = index
        raw_values = [str(row.get(col, "") or "").strip() for col in BUS_DRIVER_COLUMNS]
        if not any(raw_values):
            skipped += 1
            continue

        cc_code = normalize_cc_code(row.get("cc_code"))
        if not cc_code or cc_code not in valid_cc_codes:
            error_details.append(
                _make_validation_error(
                    row_number,
                    row.get("cc_code"),
                    "",
                    "cc_code",
                    row.get("cc_code"),
                    "VALID_CC",
                    "Bus driver cost center is invalid or not in dim_cost_centers",
                )
            )
            errors += 1
            continue
        if cc_code in seen_cc:
            error_details.append(
                _make_validation_error(
                    row_number,
                    row.get("cc_code"),
                    "",
                    "cc_code",
                    row.get("cc_code"),
                    "UNIQUE_CC",
                    "Duplicate bus driver cost center",
                )
            )
            errors += 1
            continue

        expat_count = _parse_non_negative_int(row.get("bus_expat_count"))
        vietnamese_count = _parse_non_negative_int(row.get("bus_vietnamese_count"))
        if expat_count is None:
            error_details.append(
                _make_validation_error(
                    row_number,
                    row.get("cc_code"),
                    "",
                    "bus_expat_count",
                    row.get("bus_expat_count"),
                    "INTEGER_GTE_0",
                    "Bus expat count must be an integer >= 0",
                )
            )
            errors += 1
            continue
        if vietnamese_count is None:
            error_details.append(
                _make_validation_error(
                    row_number,
                    row.get("cc_code"),
                    "",
                    "bus_vietnamese_count",
                    row.get("bus_vietnamese_count"),
                    "INTEGER_GTE_0",
                    "Bus Vietnamese count must be an integer >= 0",
                )
            )
            errors += 1
            continue

        description = str(row.get("description", "") or "").strip()
        valid_rows.append(
            {
                "cc_code": cc_code,
                "bus_expat_count": float(expat_count),
                "bus_vietnamese_count": float(vietnamese_count),
                "description": description,
            }
        )
        seen_cc.add(cc_code)

    return {
        "valid_rows": valid_rows,
        "skipped": skipped,
        "errors": errors,
        "error_details": error_details,
    }


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


def quarantine_manual_headcount_rows(
    conn: sqlite3.Connection,
    source_dir: str,
    cc_code: str,
    periods: list[str],
    quarantine_path: str,
    reason: str,
    quarantined_at: str | None = None,
    base_dir: str | None = None,
) -> dict[str, int | str]:
    """Quarantine and remove explicit manual headcount rows by exact CC/period keys."""
    search_dir = resolve_manual_headcount_source_dir(source_dir, base_dir=base_dir)
    csv_path = Path(search_dir) / TEMPLATE_FILENAME
    period_keys = {str(period).strip() for period in periods if str(period).strip()}
    cc_key = normalize_cc_code(cc_code)
    if not cc_key:
        raise ValueError("cc_code is required")
    if not period_keys:
        raise ValueError("periods is required")
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    timestamp = quarantined_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or MANUAL_HEADCOUNT_COLUMNS)
        rows = list(reader)

    kept_rows: list[dict[str, Any]] = []
    quarantine_rows: list[dict[str, str]] = []
    csv_rows_removed = 0
    for row in rows:
        row_cc = normalize_cc_code(row.get("cc_code"))
        row_period = str(row.get("period", "") or "").strip()
        should_remove = row_cc == cc_key and row_period in period_keys
        if not should_remove:
            kept_rows.append(row)
            continue

        csv_rows_removed += 1
        description = str(row.get("description", "") or "").strip()
        for driver_type, column in (
            ("headcount_staff", "headcount_staff"),
            ("headcount_worker", "headcount_worker"),
        ):
            value = str(row.get(column, "") or "").strip()
            if not _has_value(value):
                continue
            quarantine_rows.append(
                {
                    "cost_center": cc_key,
                    "period": row_period,
                    "driver_type": driver_type,
                    "value": value,
                    "old_source": "manual",
                    "old_description": description,
                    "quarantine_reason": reason,
                    "quarantined_at": timestamp,
                }
            )

    if quarantine_rows:
        quarantine_file = Path(quarantine_path)
        quarantine_file.parent.mkdir(parents=True, exist_ok=True)
        quarantine_exists = quarantine_file.exists()
        with quarantine_file.open("a", encoding="utf-8-sig", newline="") as f:
            fieldnames_quarantine = [
                "cost_center",
                "period",
                "driver_type",
                "value",
                "old_source",
                "old_description",
                "quarantine_reason",
                "quarantined_at",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames_quarantine)
            if not quarantine_exists:
                writer.writeheader()
            writer.writerows(quarantine_rows)

    if csv_rows_removed:
        tmp_path = csv_path.with_suffix(csv_path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(kept_rows)
        tmp_path.replace(csv_path)

    placeholders = ",".join("?" for _ in sorted(period_keys))
    params = [cc_key, *sorted(period_keys)]
    cursor = conn.cursor()
    cursor.execute(
        f"""
        DELETE FROM fact_monthly_headcount
        WHERE source = 'manual'
          AND CAST(cc_code AS TEXT) = ?
          AND period IN ({placeholders})
        """,
        params,
    )
    conn.commit()

    return {
        "csv_path": str(csv_path),
        "quarantine_path": quarantine_path,
        "csv_rows_removed": csv_rows_removed,
        "logical_values_quarantined": len(quarantine_rows),
        "db_rows_deleted": int(cursor.rowcount if cursor.rowcount is not None else 0),
    }


def parse_manual_headcount(
    conn: sqlite3.Connection,
    source_dir: str | None = None,
    base_dir: str | None = None,
) -> dict[str, int | str]:
    """Load manual headcount from CSV and write to fact_monthly_headcount source='manual'."""
    fy_row = conn.execute("SELECT value FROM sys_params WHERE key='fiscal_year'").fetchone()
    fiscal_year = int(str(fy_row[0]).upper().replace("FY", "").strip()) if fy_row else 2027

    search_dir = resolve_manual_headcount_source_dir(source_dir, base_dir=base_dir)
    os.makedirs(search_dir, exist_ok=True)
    template_path = ensure_manual_headcount_template(search_dir, fiscal_year)
    if not os.path.exists(template_path):
        return {"inserted": 0, "skipped": 0, "errors": 0, "template_path": template_path}

    valid_cc_codes = {str(row[0]).strip() for row in conn.execute("SELECT code FROM dim_cost_centers").fetchall() if row[0] is not None}
    bus_template_path = ensure_manual_bus_headcount_template(search_dir)

    with open(template_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return {
                "inserted": 0,
                "skipped": 0,
                "errors": 1,
                "template_path": template_path,
                "error_details": [
                    _make_validation_error(None, "", "", "header", "", "REQUIRED_COLUMNS", "Missing manual headcount header")
                ],
            }

        missing_cols = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing_cols:
            return {
                "inserted": 0,
                "skipped": 0,
                "errors": 1,
                "template_path": template_path,
                "error_message": f"Missing required columns: {', '.join(missing_cols)}",
                "error_details": [
                    _make_validation_error(
                        None,
                        "",
                        "",
                        "header",
                        ", ".join(missing_cols),
                        "REQUIRED_COLUMNS",
                        f"Missing required columns: {', '.join(missing_cols)}",
                    )
                ],
            }

        csv_rows: list[dict[str, Any]] = []
        for row_number, row in enumerate(reader, start=2):
            row["_csv_row"] = row_number
            csv_rows.append(row)

    with open(bus_template_path, "r", encoding="utf-8-sig", newline="") as f:
        bus_reader = csv.DictReader(f)
        if bus_reader.fieldnames is None:
            return {
                "inserted": 0,
                "skipped": 0,
                "errors": 1,
                "template_path": template_path,
                "error_details": [
                    _make_validation_error(None, "", "", "header", "", "REQUIRED_COLUMNS", "Missing bus driver header")
                ],
                "bus_inserted": 0,
                "bus_errors": 1,
                "bus_template_path": bus_template_path,
            }
        missing_bus_cols = [c for c in BUS_DRIVER_COLUMNS if c not in bus_reader.fieldnames]
        if missing_bus_cols:
            return {
                "inserted": 0,
                "skipped": 0,
                "errors": 1,
                "template_path": template_path,
                "error_message": f"Missing required columns: {', '.join(missing_bus_cols)}",
                "error_details": [
                    _make_validation_error(
                        None,
                        "",
                        "",
                        "header",
                        ", ".join(missing_bus_cols),
                        "REQUIRED_COLUMNS",
                        f"Missing required columns: {', '.join(missing_bus_cols)}",
                    )
                ],
                "bus_inserted": 0,
                "bus_errors": 1,
                "bus_template_path": bus_template_path,
            }
        bus_rows: list[dict[str, Any]] = []
        for row_number, row in enumerate(bus_reader, start=2):
            row["_csv_row"] = row_number
            bus_rows.append(row)

    validation = validate_manual_headcount_rows(csv_rows, valid_cc_codes, fiscal_year)
    bus_result = validate_manual_bus_headcount_rows(bus_rows, valid_cc_codes)
    error_details = list(validation.get("error_details", []))
    error_details.extend(bus_result.get("error_details", []))
    total_errors = int(validation.get("errors", 0)) + int(bus_result.get("errors", 0))
    if total_errors:
        return {
            "inserted": 0,
            "skipped": int(validation.get("skipped", 0)),
            "errors": total_errors,
            "template_path": template_path,
            "error_details": error_details,
            "bus_inserted": 0,
            "bus_errors": int(bus_result.get("errors", 0)),
            "bus_template_path": str(bus_template_path),
        }

    cursor = conn.cursor()
    cursor.execute("DELETE FROM fact_monthly_headcount WHERE source = 'manual'")
    cursor.execute("DELETE FROM fact_bus_headcount_drivers WHERE source = 'manual'")

    inserted = 0
    for row in validation["valid_rows"]:
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
            (
                row["period"],
                row["cc_code"],
                row["headcount_all"],
                row["headcount_staff"],
                row["headcount_worker"],
                row["headcount_male"],
                row["headcount_female"],
                row["description"],
            ),
        )
        inserted += 1

    bus_inserted = 0
    for row in bus_result["valid_rows"]:
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
            (row["cc_code"], row["bus_expat_count"], row["bus_vietnamese_count"], row["description"]),
        )
        bus_inserted += 1

    conn.commit()
    return {
        "inserted": inserted,
        "skipped": int(validation.get("skipped", 0)),
        "errors": 0,
        "template_path": template_path,
        "error_details": error_details,
        "bus_inserted": bus_inserted,
        "bus_errors": 0,
        "bus_template_path": str(bus_template_path),
    }
