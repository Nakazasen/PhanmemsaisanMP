"""Dịch vụ nhập giao dịch cho sổ nguồn nhân sự chính thức và đã trích xuất."""
from __future__ import annotations

import glob
import os
import sqlite3
import unicodedata
from datetime import datetime
from typing import Any

from src.parsers.extracted_headcount_time_plan import EXTRACTED_SOURCE, parse_extracted_headcount_time_plan
from src.parsers.headcount_time_plan import HEADCOUNT_SOURCE, parse_headcount_time_plan
from src.utils.fiscal_periods import fiscal_periods


def _is_department_plan(path: str, fiscal_year: int) -> bool:
    filename = os.path.basename(path)
    extension = os.path.splitext(filename)[1].lower()
    return (
        not filename.startswith("~$")
        and extension in {".xls", ".xlsx"}
        and f"FY{fiscal_year}" in filename
        and "マスタープラン人員・時間計画表" in filename
    )


def _is_extracted_plan(path: str, fiscal_year: int) -> bool:
    filename = os.path.basename(path)
    return (not filename.startswith("~$") and filename.lower().endswith(".xlsx") and f"FY{fiscal_year}" in filename and filename.endswith("_staffing_truth.xlsx"))


def _normalized_department_name(value: Any) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip()


def fiscal_year_periods(fiscal_year: int) -> tuple[str, ...]:
    """Return the canonical twelve periods for an MP fiscal year."""
    return tuple(fiscal_periods(fiscal_year))


def count_headcount_truth_rows(conn: sqlite3.Connection, fiscal_year: int) -> dict[str, Any]:
    """Count canonical staffing rows that a cleanup for one fiscal year would remove."""
    periods = fiscal_year_periods(fiscal_year)
    marks = ",".join("?" for _ in periods)
    monthly_rows = int(
        conn.execute(
            f"SELECT COUNT(*) FROM fact_monthly_headcount "
            f"WHERE source=? AND period IN ({marks})",
            (HEADCOUNT_SOURCE, *periods),
        ).fetchone()[0]
    )
    time_rows = int(
        conn.execute(
            f"SELECT COUNT(*) FROM fact_headcount_time_source WHERE period IN ({marks})",
            periods,
        ).fetchone()[0]
    )
    return {
        "fiscal_year": int(fiscal_year),
        "periods": periods,
        "monthly_headcount_rows": monthly_rows,
        "headcount_time_rows": time_rows,
        "total_rows": monthly_rows + time_rows,
    }


def cleanup_headcount_truth(conn: sqlite3.Connection, fiscal_year: int) -> dict[str, Any]:
    """Atomically remove canonical department-plan staffing data for one fiscal year."""
    counts = count_headcount_truth_rows(conn, fiscal_year)
    periods = counts["periods"]
    marks = ",".join("?" for _ in periods)
    with conn:
        conn.execute(
            f"DELETE FROM fact_monthly_headcount WHERE source=? AND period IN ({marks})",
            (HEADCOUNT_SOURCE, *periods),
        )
        conn.execute(
            f"DELETE FROM fact_headcount_time_source WHERE period IN ({marks})",
            periods,
        )
        synced_fy = conn.execute(
            "SELECT value FROM sys_params WHERE key='headcount_source_fiscal_year'"
        ).fetchone()
        if synced_fy and str(synced_fy[0] or "").strip() == str(int(fiscal_year)):
            conn.execute(
                "DELETE FROM sys_params "
                "WHERE key LIKE 'headcount_source_%' AND key <> 'headcount_source_dir'"
            )
    return counts


def _target_workbook_paths(
    workbook_paths: list[str],
    target_cc: str | None,
    target_names: tuple[str, ...],
) -> list[str]:
    """Narrow a single-CC run without weakening the full-year preflight scan."""
    if not target_cc:
        return workbook_paths
    normalized_names = {
        _normalized_department_name(name)
        for name in target_names
        if str(name or "").strip()
    }
    matches = []
    for path in workbook_paths:
        filename = _normalized_department_name(os.path.basename(path))
        if str(target_cc) in filename or any(name in filename for name in normalized_names):
            matches.append(path)
    # Fail safely: if naming conventions changed, retain the old complete scan
    # so the selected CC can still be discovered from workbook contents.
    return matches or workbook_paths


def scan_headcount_time_sources(
    source_dir: str,
    fiscal_year: int,
    *,
    target_cc: str | None = None,
    target_names: tuple[str, ...] = (),
) -> list[Any]:
    workbook_paths = sorted(set(
        glob.glob(os.path.join(source_dir, "*.xls"))
        + glob.glob(os.path.join(source_dir, "*.xlsx"))
    ))
    workbook_paths = _target_workbook_paths(workbook_paths, target_cc, target_names)
    official = [
        parse_headcount_time_plan(path, fiscal_year)
        for path in workbook_paths
        if _is_department_plan(path, fiscal_year)
    ]
    extracted = [
        parse_extracted_headcount_time_plan(path, fiscal_year)
        for path in workbook_paths
        if _is_extracted_plan(path, fiscal_year)
    ]
    return [*official, *extracted]


def _master_names(conn: sqlite3.Connection) -> dict[str, tuple[str, str]]:
    return {
        str(row["code"]): (str(row["name_jp"] or "").strip(), str(row["name_vn"] or "").strip())
        for row in conn.execute("SELECT code, name_jp, name_vn FROM dim_cost_centers")
    }


def _matches_master_name(result: Any, names: tuple[str, str]) -> bool:
    displayed = _normalized_department_name(result.department_name)
    return displayed in {
        _normalized_department_name(name) for name in names if str(name or "").strip()
    }


def review_headcount_time_sources(
    conn: sqlite3.Connection,
    source_dir: str,
    fiscal_year: int,
    *,
    scan_results: list[Any] | None = None,
    target_cc: str | None = None,
) -> dict[str, Any]:
    """Scan and classify staffing workbooks without writing the database."""
    master_names = _master_names(conn)
    target_names = master_names.get(str(target_cc), ("", "")) if target_cc else ("", "")
    results = scan_results if scan_results is not None else scan_headcount_time_sources(
        source_dir,
        fiscal_year,
        target_cc=str(target_cc) if target_cc else None,
        target_names=tuple(target_names),
    )
    importable: list[Any] = []
    unknown_cost_centers: list[Any] = []
    name_mismatches: list[Any] = []
    errors: list[Any] = []
    for result in results:
        if result.status != "valid":
            errors.append(result)
            continue
        if result.cc_code not in master_names:
            unknown_cost_centers.append(result)
            continue
        lookup_status = str(getattr(result, "lookup_status", "not_applicable"))
        if lookup_status == "matched":
            importable.append(result)
        elif lookup_status in {"missing", "not_applicable"} and _matches_master_name(
            result, master_names[result.cc_code]
        ):
            result.verification_method = "fallback_master_name"
            importable.append(result)
        else:
            name_mismatches.append(result)
    return {
        "files": len(results),
        "results": results,
        "importable": importable,
        "unknown_cost_centers": unknown_cost_centers,
        "name_mismatches": name_mismatches,
        "errors": errors,
    }


def _select_unique_sources(
    candidates: list[Any],
    skipped: list[tuple[Any, str]],
    errors: list[Any],
) -> list[Any]:
    grouped: dict[str, list[Any]] = {}
    for result in candidates:
        grouped.setdefault(result.cc_code, []).append(result)
    selected_results: list[Any] = []
    for cc_code, matches in grouped.items():
        official = [
            item for item in matches
            if "マスタープラン人員・時間計画表" in os.path.basename(str(item.path))
        ]
        if len(official) == 1:
            selected = official[0]
        elif len(official) > 1:
            for item in matches:
                item.errors.append(f"Có nhiều file chính thức cho CC {cc_code}")
                errors.append(item)
            continue
        elif len(matches) == 1:
            selected = matches[0]
        else:
            for item in matches:
                item.errors.append(f"Có nhiều nguồn trích xuất cho CC {cc_code}")
                errors.append(item)
            continue
        selected_results.append(selected)
        for item in matches:
            if item is not selected:
                skipped.append((item, "Đã ưu tiên file chính thức"))
    return selected_results


def _normalized_cc_codes(cc_codes: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """Return unique, non-empty cost-center codes while preserving the UI order."""
    return tuple(dict.fromkeys(
        str(code).strip() for code in cc_codes if str(code or "").strip()
    ))


def assess_headcount_time_source_coverage(
    conn: sqlite3.Connection,
    source_dir: str,
    fiscal_year: int,
    required_cc_codes: tuple[str, ...] | list[str],
    *,
    scan_results: list[Any] | None = None,
) -> dict[str, Any]:
    """Report whether each selected cost center has one usable staffing source.

    A valid workbook alone is not sufficient: it must belong to every cost
    center selected for the run.  Name mismatches, unknown cost centers and
    duplicate candidate files are deliberately not counted as coverage.
    """
    required = _normalized_cc_codes(required_cc_codes)
    review = review_headcount_time_sources(
        conn,
        source_dir,
        fiscal_year,
        scan_results=scan_results,
    )
    selection_errors = list(review["errors"])
    importable = _select_unique_sources(
        list(review["importable"]),
        [],
        selection_errors,
    )
    available = tuple(sorted({str(result.cc_code) for result in importable}))
    missing = tuple(code for code in required if code not in available)
    return {
        **review,
        "required_cc_codes": required,
        "available_cc_codes": available,
        "missing_cc_codes": missing,
        "coverage_errors": selection_errors,
    }


def import_headcount_time_sources(
    conn: sqlite3.Connection,
    source_dir: str,
    fiscal_year: int,
    *,
    approved_unknown_files: set[str] | None = None,
    rejected_unknown_files: set[str] | None = None,
    approved_name_files: set[str] | None = None,
    scan_results: list[Any] | None = None,
    target_cc: str | None = None,
    required_cc_codes: tuple[str, ...] | list[str] = (),
) -> dict[str, Any]:
    """Import reviewed sources atomically; all approval lists are exact absolute paths."""
    approved_unknown = {os.path.abspath(path) for path in (approved_unknown_files or set())}
    rejected_unknown = {os.path.abspath(path) for path in (rejected_unknown_files or set())}
    approved_names = {os.path.abspath(path) for path in (approved_name_files or set())}
    review = review_headcount_time_sources(
        conn,
        source_dir,
        fiscal_year,
        scan_results=scan_results,
        target_cc=target_cc,
    )
    skipped: list[tuple[Any, str]] = []
    errors = list(review["errors"])
    confirmed_unknown: list[Any] = []
    rejected_unknown_results: list[Any] = []
    explicitly_rejected_unknown: list[Any] = []
    approved_name_results: list[Any] = []
    candidates = list(review["importable"])

    for result in review["unknown_cost_centers"]:
        resolved = os.path.abspath(result.path)
        if resolved in approved_unknown:
            result.verification_method = "confirmed_unknown_cc"
            confirmed_unknown.append(result)
            candidates.append(result)
        else:
            rejected_unknown_results.append(result)
            if resolved in rejected_unknown:
                explicitly_rejected_unknown.append(result)
                reason = "Người dùng bỏ qua CC chưa có master"
            else:
                reason = "CC chưa có master và chưa được xác nhận"
            skipped.append((result, reason))
    for result in review["name_mismatches"]:
        if os.path.abspath(result.path) in approved_names:
            result.verification_method = "confirmed_name_mismatch"
            approved_name_results.append(result)
            candidates.append(result)
        else:
            skipped.append((result, "Tên B5 chưa được xác nhận"))

    importable = _select_unique_sources(candidates, skipped, errors)
    required = _normalized_cc_codes(required_cc_codes)
    available = tuple(sorted({str(result.cc_code) for result in importable}))
    missing_required_cc_codes = tuple(
        code for code in required if code not in available
    )
    if missing_required_cc_codes:
        # Do not partially synchronize another selected cost center.  The
        # caller can display the missing CCs and no calculation input changes.
        return {
            "files": len(review["results"]),
            "imported_files": 0,
            "imported_rows": 0,
            "split_required_files": 0,
            "skipped": skipped,
            "errors": errors,
            "results": review["results"],
            "unknown_cost_centers": review["unknown_cost_centers"],
            "name_mismatches": review["name_mismatches"],
            "confirmed_unknown_cost_centers": confirmed_unknown,
            "rejected_unknown_cost_centers": rejected_unknown_results,
            "approved_name_mismatches": approved_name_results,
            "required_cc_codes": required,
            "available_cc_codes": available,
            "missing_required_cc_codes": missing_required_cc_codes,
            "imported_cc_codes": (),
        }
    imported_rows = 0
    split_required_files = 0
    periods = fiscal_year_periods(fiscal_year)
    period_placeholders = ",".join("?" for _ in periods)
    with conn:
        for result in importable:
            source = HEADCOUNT_SOURCE
            conn.execute(
                f"DELETE FROM fact_monthly_headcount WHERE cc_code=? AND source=? AND period IN ({period_placeholders})",
                (result.cc_code, source, *periods),
            )
            conn.execute(
                f"DELETE FROM fact_headcount_time_source WHERE cc_code=? AND period IN ({period_placeholders})",
                (result.cc_code, *periods),
            )
            file_split_required = False
            for row in result.rows:
                split_status = str(row.get("split_status") or "READY")
                local_total = float(row.get("headcount_local_total", float(row.get("headcount_staff") or 0) + float(row.get("headcount_worker") or 0)))
                expat = float(row["headcount_expat"] or 0)
                staff = row.get("headcount_staff")
                worker = row.get("headcount_worker")
                file_split_required |= split_status != "READY"
                conn.execute("""INSERT INTO fact_monthly_headcount
                    (period,cc_code,headcount_all,headcount_expat,headcount_staff,headcount_worker,headcount_local_total,split_status,source,description,source_file,source_sheet,imported_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
                    (row["period"], result.cc_code, expat + local_total, expat, staff, worker, local_total, split_status, source, result.department_name, result.path, result.sheet_name))
                conn.execute("""INSERT INTO fact_headcount_time_source
                    (period,cc_code,fixed_hours_expat,fixed_hours_local,overtime_hours_expat,overtime_hours_local,source_file,source_sheet,source_cells,imported_at)
                    VALUES (?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
                    (row["period"], result.cc_code, row["fixed_hours_expat"], row["fixed_hours_local"], row["overtime_hours_expat"], row["overtime_hours_local"], result.path, result.sheet_name, row["source_cells"]))
                imported_rows += 1
            split_required_files += int(file_split_required)

        for result in [*confirmed_unknown, *explicitly_rejected_unknown]:
            decision = "CONFIRMED_IMPORT" if result in confirmed_unknown else "REJECTED"
            conn.execute("""INSERT INTO audit_headcount_source_decisions
                (fiscal_year,source_file,cc_code,displayed_name,name_jp,name_vn,decision,reason)
                VALUES(?,?,?,?,?,?,?,?)""", (
                fiscal_year, os.path.abspath(result.path), result.cc_code,
                result.department_name, getattr(result, "department_name_jp", ""),
                getattr(result, "department_name_vn", ""), decision,
                "CC chưa tồn tại trong dim_cost_centers",
            ))
        values = {
            "headcount_source_dir": os.path.abspath(source_dir),
            "headcount_source_updated_at": datetime.now().isoformat(timespec="seconds"),
            "headcount_source_fiscal_year": str(fiscal_year),
            "headcount_source_files": str(len(review["results"])),
            "headcount_source_imported_files": str(len(importable)),
            "headcount_source_skipped_files": str(len(skipped)),
            "headcount_source_error_files": str(len(errors)),
            "headcount_source_split_required_files": str(split_required_files),
            "headcount_source_confirmed_unknown_files": str(len(confirmed_unknown)),
        }
        conn.executemany(
            "INSERT OR REPLACE INTO sys_params(key,value,description,updated_at) VALUES(?,?,'Staffing synchronization status',CURRENT_TIMESTAMP)",
            values.items(),
        )
    return {
        "files": len(review["results"]),
        "imported_files": len(importable),
        "imported_rows": imported_rows,
        "split_required_files": split_required_files,
        "skipped": skipped,
        "errors": errors,
        "results": review["results"],
        "unknown_cost_centers": review["unknown_cost_centers"],
        "name_mismatches": review["name_mismatches"],
        "confirmed_unknown_cost_centers": confirmed_unknown,
        "rejected_unknown_cost_centers": rejected_unknown_results,
        "approved_name_mismatches": approved_name_results,
        "required_cc_codes": required,
        "available_cc_codes": available,
        "missing_required_cc_codes": (),
        "imported_cc_codes": tuple(sorted({str(result.cc_code) for result in importable})),
    }
