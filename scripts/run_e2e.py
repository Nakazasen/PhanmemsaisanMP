"""
MP2027 Manager - Universal E2E Execution Pipeline
Supports Single CC and Batch Export.

Compatibility guard: facility file-order export remains explicit via
`if facility_file_order_export:`; runtime adds workbook-existence checks.
"""
import sqlite3
import argparse
import csv
import inspect
import json
import os
import sys
import time
import traceback
from zipfile import BadZipFile


class _NullTextIO:
    encoding = "utf-8"

    def write(self, text):
        return len(str(text))

    def flush(self):
        return None

    def isatty(self):
        return False


def _ensure_text_streams() -> None:
    if sys.stdout is None:
        sys.stdout = _NullTextIO()
    if sys.stderr is None:
        sys.stderr = _NullTextIO()


_ensure_text_streams()

# Add root project to path
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from src.db.schema import get_connection, create_schema, init_sys_params
from src.db.loader import load_all
from src.audit.pipeline_audit import write_pipeline_audit_report
from src.audit.exchange_rate_audit import audit_exchange_rate_workbook, write_exchange_rate_audit_report
from src.parsers.facility import parse_facility
from src.parsers.ga import parse_ga
from src.parsers.birthday import parse_birthday_workbook
from src.parsers.manual_event_drivers import parse_manual_event_drivers
from src.parsers.manual_headcount import parse_manual_headcount
from src.parsers.manual_special_costs import parse_manual_special_costs
from src.parsers.nnn_paperwork import parse_nnn_paperwork
from src.parsers.it_sim import parse_it_simulation
from src.parsers.fixed_assets import parse_fixed_assets
from src.engine.allocator import AllocationEngine
from src.engine.hub_builder import HubBuilder
from src.engine.facility_file_order_writer import (
    apply_facility_file_order_to_workbook,
    write_facility_file_order_preview_workbook,
)
from src.engine.admin_consumables_writer import apply_admin_consumables_to_workbook
from src.engine.system_cost_writer import apply_system_cost_to_workbook
from src.engine.reference_assisted_fill import apply_reference_assisted_fill_to_workbook
from src.engine.fixed_assets_reference_skeleton import apply_fixed_assets_reference_skeleton_to_workbook
from src.engine.complete_v1_source_order_writer import apply_complete_v1_source_order_to_workbook
from src.engine.mp_saisan_complete_export import apply_mp_saisan_complete_v1
from src.utils.excel_helpers import get_fy_months
from src.utils.fiscal_periods import fiscal_baseline_period
from src.utils.source_manifest import describe_manifest
from src.services.headcount_source_importer import import_headcount_time_sources
from src.services.manual_staffing_overrides import (
    apply_manual_baseline_overrides,
    apply_manual_time_overrides,
    copy_annual_manual_inputs,
    migrate_legacy_fy2027_manual_inputs,
)
from src.services.fiscal_run import (
    REFERENCE_POLICY_DISABLED,
    REFERENCE_POLICY_EXPLICIT_SAME_FY,
    REFERENCE_POLICY_LEGACY_FY2027_MAP,
    create_fiscal_run_context,
    detect_fiscal_year,
    preflight_fiscal_run,
)
from src.services.run_history import (
    PipelineStageEvidence,
    RUN_STATUS_FAILED,
    RUN_STATUS_PRECHECK_FAILED,
    RUN_STATUS_RUNNING,
    RUN_STATUS_SUCCEEDED,
    RUN_STATUS_SUCCEEDED_INCOMPLETE,
    create_run_workspace,
    publish_run_output,
    register_legacy_fy2027_database,
    register_run,
    write_run_manifest,
)

COMPLETE_V1_SOURCE_ORDER_START_ROW = 30
COMPLETE_V1_SOURCE_ORDER_CLEAR_UNTIL_ROW = 199


def _safe_console_print(message):
    text = str(message)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        print(text.encode(encoding, errors="replace").decode(encoding, errors="replace"), flush=True)


def _timed_call(log_callback, label: str, function, *args, **kwargs):
    started = time.perf_counter()
    try:
        return function(*args, **kwargs)
    finally:
        log_callback(f"Thời gian {label}: {time.perf_counter() - started:.3f} giây")


def _create_allocation_engine(conn, target_cc=None):
    try:
        parameters = inspect.signature(AllocationEngine).parameters
    except (TypeError, ValueError):
        parameters = {}
    if target_cc is not None and "target_cc" in parameters:
        return AllocationEngine(conn, target_cc=target_cc)
    return AllocationEngine(conn)


def _default_template_path(fiscal_year: int = 2027) -> str:
    candidate = os.path.join(BASE_DIR, "docs", f"MP{fiscal_year}", "FORM.xlsx")
    if os.path.exists(candidate):
        return candidate
    # In packaged (COLLECT) mode, BASE_DIR is the exe dir but bundled data
    # lives under sys._MEIPASS (_internal/).
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        meipass_candidate = os.path.join(meipass, "docs", f"MP{fiscal_year}", "FORM.xlsx")
        if os.path.exists(meipass_candidate):
            return meipass_candidate
    raise FileNotFoundError(
        f"Không tìm thấy tệp mẫu bắt buộc: {candidate}. "
        "Không dùng lại FORM.xlsx cũ ở thư mục gốc vì tệp đó có công thức mẫu đã lỗi thời."
    )


def _default_source_dir(fiscal_year: int = 2027) -> str:
    candidate = os.path.join(BASE_DIR, "docs", f"MP{fiscal_year}")
    if os.path.isdir(candidate):
        return candidate
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        meipass_candidate = os.path.join(meipass, "docs", f"MP{fiscal_year}")
        if os.path.isdir(meipass_candidate):
            return meipass_candidate
    return candidate


def _friendly_pipeline_error_message(error) -> str:
    text = str(error or "").strip()
    lower_text = text.lower()
    expected_form = os.path.join(BASE_DIR, "docs", "MP2027", "FORM.xlsx")
    vietnamese_markers = (
        "không",
        "hãy",
        "tệp",
        "thư mục",
        "dữ liệu",
        "đường dẫn",
        "lỗi",
        "mẫu",
    )

    if "unable to locate system cost row" in lower_text or "không tìm thấy dòng system cost" in lower_text:
        return (
            "Không tìm thấy dòng System Cost trong tệp FORM. "
            f"Hãy chọn lại tệp FORM mới nhất tại {expected_form}."
        )
    if "unable to resolve kdc system cost account" in lower_text or "không xác định được tài khoản system cost" in lower_text:
        return (
            "Không xác định được tài khoản System Cost cho một mã bộ phận. "
            "Hãy kiểm tra mã bộ phận trong dữ liệu nguồn và loại chi phí trong master CC."
        )
    if "form template not found" in lower_text or "không tìm thấy tệp form template" in lower_text:
        return f"Không tìm thấy tệp mẫu FORM. Hãy chọn lại tệp FORM mới nhất tại {expected_form}."
    if "missing the mp detail sheet" in lower_text or "không có sheet chi tiết mp" in lower_text:
        return f"Tệp FORM không có sheet chi tiết MP đúng định dạng. Hãy dùng tệp FORM mới nhất tại {expected_form}."
    if "malformed or empty" in lower_text or "sai định dạng hoặc rỗng" in lower_text:
        return f"Tệp FORM sai định dạng hoặc rỗng. Hãy thay bằng tệp FORM mới nhất tại {expected_form}."
    if "append rows prepared" in lower_text or "không còn đủ dòng trống" in lower_text:
        return "Tệp FORM không còn đủ dòng trống để ghi thêm chi phí phát sinh. Hãy dùng FORM mới nhất hoặc chuẩn bị thêm vùng dòng trống."
    if "not found" in lower_text or "no such file" in lower_text:
        return "Không tìm thấy tệp hoặc thư mục cần dùng. Hãy kiểm tra lại Tệp mẫu FORM và Thư mục nguồn."
    if text and any(marker in lower_text for marker in vietnamese_markers):
        return text
    error_type = type(error).__name__ if error is not None else "UnknownError"
    return f"{error_type}: {text or 'Không có nội dung lỗi.'}"


def _log_debug_traceback(log_callback) -> None:
    if os.environ.get("MP2027_DEBUG_TRACEBACK") == "1":
        log_callback(traceback.format_exc())
    else:
        log_callback("Chi tiết kỹ thuật đã được ẩn. Nếu cần điều tra sâu, bật MP2027_DEBUG_TRACEBACK=1 rồi chạy lại.")


def _write_failure_traceback(run_context, error: BaseException) -> str | None:
    """Persist the real exception so a failed business run is diagnosable."""
    if run_context is None or not run_context.workspace_dir:
        return None
    reports_dir = os.path.join(str(run_context.workspace_dir), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    path = os.path.join(reports_dir, "failure_traceback.txt")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(f"{type(error).__name__}: {error}\n\n")
        handle.write(traceback.format_exc())
    return path


def _default_reference_map_path() -> str:
    return os.path.join(BASE_DIR, "docs", "config", "reference_workbook_map.csv")


class ReferenceNotConfiguredError(ValueError):
    """No optional reference exists for this CC; this is not a data mismatch."""


def _default_fixed_assets_skeleton_csv_path() -> str:
    return os.path.join(
        BASE_DIR,
        "docs",
        "audits",
        "phase42n2e_5005026371_secondary_skeleton_patterns.csv",
    )


def _apply_complete_v1_source_order(
    workbook_path: str,
    log_callback,
    phase: str,
    *,
    dynamic_allocation_rows=None,
    fiscal_periods=None,
    source_file_order=None,
) -> dict[str, int]:
    kwargs = {
        "start_row": COMPLETE_V1_SOURCE_ORDER_START_ROW,
        "clear_until_row": COMPLETE_V1_SOURCE_ORDER_CLEAR_UNTIL_ROW,
    }
    if dynamic_allocation_rows and fiscal_periods:
        kwargs["dynamic_allocation_rows"] = dynamic_allocation_rows
        kwargs["fiscal_periods"] = fiscal_periods
    if source_file_order:
        kwargs["source_file_order"] = source_file_order
    result = apply_complete_v1_source_order_to_workbook(workbook_path, **kwargs)
    log_callback(
        "Đã áp dụng ghi kết quả hoàn chỉnh theo thứ tự nguồn ({phase}): {summary}".format(
            phase=_translate_complete_v1_phase(phase),
            summary=_format_complete_v1_result_vi(result),
        )
    )
    return result


def _annual_complete_v1_source_order(run_context) -> list[str]:
    """Use the selected FY manifest rather than names embedded for FY2027."""
    categories = ("facility", "fixed_assets", "it_simulation", "ga", "birthday", "allocation_rules", "nnn_paperwork")
    names: list[str] = []
    for category in categories:
        paths = run_context.resolved_sources.get(category, ())
        if not paths:
            # Preflight will surface missing required sources; this guard keeps
            # the writer deterministic for diagnostic FY2027 runs.
            names.append(category)
        else:
            names.append(os.path.basename(paths[0]))
    return names


def _load_complete_v1_dynamic_allocation_rows(builder, target_cc) -> list[dict[str, object]]:
    loader = getattr(builder, "_load_append_rows", None)
    if not callable(loader):
        return []
    return loader(str(target_cc))


def _translate_complete_v1_phase(phase: str) -> str:
    translations = {
        "final": "cuối",
        "pre-reference": "trước tham chiếu",
    }
    return translations.get(str(phase), str(phase))


def _format_complete_v1_result_vi(result: dict[str, int]) -> str:
    labels = {
        "source_blocks_written": "nhóm nguồn",
        "rows_written": "dòng ghi",
        "preserved_rows_written": "dòng giữ lại",
        "blank_rows_written": "dòng trống",
        "start_row": "dòng bắt đầu",
        "end_row": "dòng kết thúc",
        "layout_fills_cleared": "ô nền đã xóa",
        "item_ids_cleared": "mã mục đã xóa",
    }
    parts = []
    for key, label in labels.items():
        if key in result:
            parts.append(f"{label}={result[key]}")
    return ", ".join(parts) if parts else str(result)


def _resolve_primary_reference_path(
    target_cc: int | str | None,
    primary_reference_path: str | None = None,
    reference_map_path: str | None = None,
    *,
    fiscal_year: int = 2027,
) -> str:
    """Resolve an explicit or mapped reference workbook for reference-assisted fill."""
    if primary_reference_path:
        resolved = os.path.abspath(primary_reference_path)
    else:
        if int(fiscal_year) != 2027:
            raise ValueError("FY từ 2028 chỉ dùng file tham chiếu được chọn rõ, đúng cùng năm tài chính.")
        target_text = str(target_cc or "")
        resolved = ""
        map_path = reference_map_path or _default_reference_map_path()
        if os.path.exists(map_path):
            with open(map_path, newline="", encoding="utf-8-sig") as handle:
                for row in csv.DictReader(handle):
                    if row.get("target_cc") == target_text and row.get("reference_role") == "primary_reference":
                        candidate = row.get("reference_path", "")
                        resolved = candidate if os.path.isabs(candidate) else os.path.join(BASE_DIR, candidate)
                        break
        if not resolved:
            raise ReferenceNotConfiguredError(
                "Điền theo tham chiếu cần --primary-reference-path hoặc bảng ánh xạ tham chiếu chính cho mã bộ phận này."
            )
    if not os.path.exists(resolved):
        raise FileNotFoundError(f"Không tìm thấy tệp tham chiếu chính để điền dữ liệu: {resolved}")
    detected = detect_fiscal_year(resolved)
    # FY2027's accepted legacy map predates annual labels in a few submitted
    # files.  Preserve that compatibility, but never extend it to FY2028+.
    if detected is None and int(fiscal_year) == 2027:
        return resolved
    if detected != int(fiscal_year):
        found = f"FY{detected}" if detected else "không xác định"
        raise ValueError(f"Tệp tham chiếu sai năm: cần FY{fiscal_year}, phát hiện {found}: {resolved}")
    return resolved


def _try_resolve_primary_reference_path(
    target_cc: int | str | None,
    primary_reference_path: str | None = None,
    reference_map_path: str | None = None,
    *,
    fiscal_year: int = 2027,
) -> str | None:
    """Resolve an optional reference workbook for canonical export."""
    if int(fiscal_year) != 2027 and not primary_reference_path:
        return None
    if not primary_reference_path and not reference_map_path:
        return None
    try:
        return _resolve_primary_reference_path(
            target_cc=target_cc,
            primary_reference_path=primary_reference_path,
            reference_map_path=reference_map_path,
            fiscal_year=fiscal_year,
        )
    except ReferenceNotConfiguredError:
        return None


def _parse_manual_headcount(conn, source_dir: str):
    """Call the parser with packaged raw-directory support when available."""
    signature = inspect.signature(parse_manual_headcount)
    if "base_dir" in signature.parameters:
        return parse_manual_headcount(conn, source_dir=source_dir, base_dir=BASE_DIR)
    return parse_manual_headcount(conn, source_dir=source_dir)


def _staffing_sync_log_lines(result: dict) -> list[str]:
    lines = [
        f"Nguồn nhân sự: nạp {result['imported_files']}/{result['files']} tệp, "
        f"bỏ qua {len(result['skipped'])}, lỗi {len(result['errors'])}."
    ]
    for parsed in result.get("results", []):
        if parsed.status == "valid" and not any(parsed is item for item, _ in result["skipped"]):
            lines.append(
                f"  ĐÃ NẠP: {os.path.basename(parsed.path)} | CC {parsed.cc_code} | "
                f"{parsed.department_name} | {len(parsed.rows)} tháng"
            )
    for parsed, reason in result["skipped"]:
        lines.append(
            f"  BỎ QUA: {os.path.basename(parsed.path)} | CC {parsed.cc_code or 'không đọc được'} | "
            f"{parsed.department_name or 'không đọc được tên phòng'} | {reason}"
        )
    for parsed in result["errors"]:
        lines.append(
            f"  LỖI: {os.path.basename(parsed.path)} | CC {parsed.cc_code or 'không đọc được'} | "
            f"{'; '.join(parsed.errors) or 'Tệp không hợp lệ'}"
        )
    return lines


def _staffing_preflight(
    conn,
    fiscal_year: int,
    target_cc=None,
    excluded_ccs: set[str] | None = None,
) -> list[str]:
    periods = get_fy_months(fiscal_year)
    baseline = fiscal_baseline_period(fiscal_year)
    if target_cc:
        cc_codes = [str(target_cc)]
    else:
        excluded = excluded_ccs or set()
        cc_codes = [
            str(row[0]) for row in conn.execute(
                "SELECT DISTINCT CAST(cc_code AS TEXT) FROM fact_input_data WHERE account_code > 0 ORDER BY 1"
            )
            if str(row[0]) not in excluded
        ]
    issues: list[str] = []
    for cc_code in cc_codes:
        department_row = conn.execute(
            """SELECT name_jp,name_vn FROM dim_cost_centers
               WHERE CAST(code AS TEXT)=? LIMIT 1""",
            (cc_code,),
        ).fetchone()
        department_names = []
        if department_row:
            for value in department_row:
                name = str(value or "").strip()
                if name and name not in department_names:
                    department_names.append(name)
        department = f"Phòng {cc_code}"
        if department_names:
            department += " – " + " / ".join(department_names)

        headcount_periods = {
            str(row[0]) for row in conn.execute(
                "SELECT period FROM fact_monthly_headcount WHERE CAST(cc_code AS TEXT)=? AND source='department_plan'",
                (cc_code,),
            )
        }
        baseline_available = conn.execute(
            "SELECT 1 FROM fact_monthly_headcount WHERE CAST(cc_code AS TEXT)=? AND period=? AND source='manual' LIMIT 1",
            (cc_code, baseline),
        ).fetchone() is not None
        time_periods = {
            str(row[0]) for row in conn.execute(
                "SELECT period FROM fact_headcount_time_source WHERE CAST(cc_code AS TEXT)=?",
                (cc_code,),
            )
        }
        missing_headcount = [period for period in periods if period not in headcount_periods]
        missing_time = [period for period in periods if period not in time_periods]
        if missing_headcount or missing_time or not baseline_available:
            parts = []
            if not baseline_available:
                baseline_label = f"{baseline[-2:]}/{baseline[:4]}"
                first_fy_label = f"{periods[0][-2:]}/{periods[0][:4]}"
                parts.append(
                    f"chưa có Tổng số người tháng {baseline_label}. "
                    f"Dữ liệu này cần để tính chi phí tháng {first_fy_label}. "
                    "Hãy chọn “Nhập nhân sự thủ công”, nhập dữ liệu tháng này và lưu lại"
                )
            if missing_headcount:
                parts.append("thiếu số người kế hoạch các tháng: " + ", ".join(missing_headcount))
            if missing_time:
                parts.append("thiếu thời gian làm việc các tháng: " + ", ".join(missing_time))
            issues.append(department + ": " + "; ".join(parts))
    return issues


def _simulate_missing_baseline_from_april(
    conn,
    fiscal_year: int,
    target_cc: object | None = None,
) -> int:
    """Create an explicitly marked manual T3 baseline from April for audit-only runs."""
    baseline_period = f"{fiscal_year - 1}03"
    april_period = f"{fiscal_year - 1}04"
    target_clause = "AND CAST(april.cc_code AS TEXT) = ?" if target_cc is not None else ""
    params: list[object] = [baseline_period, april_period]
    if target_cc is not None:
        params.append(str(target_cc).strip())

    cursor = conn.execute(
        f"""
        INSERT INTO fact_monthly_headcount (
            period, cc_code, headcount_all, headcount_expat,
            headcount_staff, headcount_worker, headcount_male, headcount_female,
            split_status, headcount_local_total, source, description,
            source_file, source_sheet, imported_at
        )
        SELECT
            ?, april.cc_code, april.headcount_all, april.headcount_expat,
            april.headcount_staff, april.headcount_worker,
            april.headcount_male, april.headcount_female,
            april.split_status, april.headcount_local_total,
            'manual', 'SIMULATED_BASELINE_T3_FROM_T4',
            april.source_file, april.source_sheet, CURRENT_TIMESTAMP
        FROM fact_monthly_headcount AS april
        WHERE april.period = ?
          AND april.source = 'department_plan'
          {target_clause}
          AND NOT EXISTS (
              SELECT 1
              FROM fact_monthly_headcount AS baseline
              WHERE baseline.period = ?
                AND baseline.source = 'manual'
                AND CAST(baseline.cc_code AS TEXT) = CAST(april.cc_code AS TEXT)
          )
        """,
        params + [baseline_period],
    )
    conn.commit()
    return max(int(cursor.rowcount or 0), 0)


def _exclude_incomplete_staffing_ccs_for_audit(conn, fiscal_year: int) -> list[str]:
    """Remove incomplete CCs from allocation scope in an isolated audit database."""
    fiscal_periods = get_fy_months(fiscal_year)
    placeholders = ",".join("?" for _ in fiscal_periods)
    complete_headcount = {
        str(row[0])
        for row in conn.execute(
            f"""
            SELECT CAST(cc_code AS TEXT)
            FROM fact_monthly_headcount
            WHERE source = 'department_plan' AND period IN ({placeholders})
            GROUP BY CAST(cc_code AS TEXT)
            HAVING COUNT(DISTINCT period) = ?
            """,
            [*fiscal_periods, len(fiscal_periods)],
        ).fetchall()
    }
    complete_time = {
        str(row[0])
        for row in conn.execute(
            f"""
            SELECT CAST(cc_code AS TEXT)
            FROM fact_headcount_time_source
            WHERE period IN ({placeholders})
            GROUP BY CAST(cc_code AS TEXT)
            HAVING COUNT(DISTINCT period) = ?
            """,
            [*fiscal_periods, len(fiscal_periods)],
        ).fetchall()
    }
    master_ccs = {
        str(row[0])
        for row in conn.execute("SELECT CAST(code AS TEXT) FROM dim_cost_centers").fetchall()
    }
    excluded = sorted(master_ccs - (complete_headcount & complete_time))
    if excluded:
        conn.executemany("DELETE FROM dim_cost_centers WHERE CAST(code AS TEXT) = ?", [(cc,) for cc in excluded])
        conn.commit()
    return excluded


def _close_pipeline_connection(
    conn,
    *,
    rollback: bool,
    log_callback=None,
    suppress_errors: bool = False,
) -> None:
    if conn is None:
        return

    cleanup_errors: list[Exception] = []
    if rollback:
        try:
            conn.rollback()
        except Exception as exc:
            cleanup_errors.append(exc)
    try:
        conn.close()
    except Exception as exc:
        cleanup_errors.append(exc)

    if cleanup_errors:
        details = "; ".join(str(error) for error in cleanup_errors)
        if log_callback is not None:
            log_callback(f"CẢNH BÁO: không thể dọn dẹp hoàn toàn kết nối database: {details}")
        if not suppress_errors:
            raise RuntimeError(f"Không thể đóng kết nối database an toàn: {details}") from cleanup_errors[0]


def run_universal_pipeline(fiscal_year: int, template_path: str, source_dir: str,
                           exchange_rate: float = 25450.0,
                           exchange_rate_source: str = "explicit pipeline input",
                           target_cc: int = None,
                           headcount_source_dir: str | None = None,
                           log_callback=None,
                           facility_file_order_preview: bool = False,
                           facility_preview_output: str | None = None,
                           facility_preview_start_row: int = 200,
                           facility_file_order_export: bool = False,
                           facility_file_order_start_row: int = 200,
                           admin_consumables_export: bool = False,
                           admin_consumables_start_row: int = 207,
                           system_cost_export: bool = False,
                           system_cost_start_row: int = 211,
                           file_order_export_v1: bool = False,
                           primary_reference_fill: bool = False,
                           primary_reference_fill_start_row: int = 213,
                           file_order_export_v2: bool = False,
                           primary_reference_path: str | None = None,
                           reference_map_path: str | None = None,
                           fixed_assets_reference_skeleton_export: bool = False,
                           fixed_assets_skeleton_csv: str | None = None,
                           fixed_assets_skeleton_start_row: int | None = None,
                           db_path: str | None = None,
                           operational_db_path: str | None = None,
                           manual_input_store: str | None = None,
                           output_dir: str | None = None,
                           simulate_baseline_t3_from_t4: bool = False,
                           audit_exclude_incomplete_staffing: bool = False,
                           uniform_policy_path: str | None = None,
                           run_history_root: str | None = None,
                           reference_policy: str | None = None,
                           preserve_run_history: bool = True,
                           accepted_missing_categories: tuple[str, ...] = (),
                           mp_saisan_complete_v1: bool = True):
    """
    Runs the pipeline and exports results to OUTPUT_FY[Year] folder.
    - target_cc: if None, exports every CC represented by generated facts.
    - operational_db_path: editable project database used as migration source.
    - db_path/output_dir: optional isolation paths retained for tests/diagnostics.
    - simulate_baseline_t3_from_t4: audit-only fallback with explicit provenance.
    """
    if log_callback is None:
        log_callback = _safe_console_print

    explicit_facility_file_order_export = facility_file_order_export
    explicit_admin_consumables_export = admin_consumables_export
    explicit_system_cost_export = system_cost_export
    explicit_complete_v1 = mp_saisan_complete_v1
    template_ext = os.path.splitext(str(template_path))[1].lower()
    template_is_excel = template_ext in {".xlsx", ".xlsm", ".xltx", ".xltm"}

    if file_order_export_v2 and fixed_assets_reference_skeleton_export:
        return False, (
            "Nguy cơ trùng dữ liệu: --fixed-assets-reference-skeleton-export không thể chạy cùng "
            "--primary-reference-fill hoặc --file-order-export-v2. Hãy chạy riêng."
        )

    if fixed_assets_reference_skeleton_export and primary_reference_fill:
        return False, (
            "Nguy cơ trùng dữ liệu: --fixed-assets-reference-skeleton-export không thể chạy cùng "
            "--primary-reference-fill hoặc --file-order-export-v2. Hãy chạy riêng."
        )

    if file_order_export_v2:
        file_order_export_v1 = True
        primary_reference_fill = True
        primary_reference_fill_start_row = 213

    if mp_saisan_complete_v1:
        file_order_export_v1 = True
        primary_reference_fill = False
        fixed_assets_reference_skeleton_export = False

    if file_order_export_v1:
        facility_file_order_export = True
        facility_file_order_start_row = 168
        admin_consumables_export = True
        admin_consumables_start_row = 175
        system_cost_export = True
        system_cost_start_row = 179

    production_db_path = os.path.abspath(
        operational_db_path or os.path.join(BASE_DIR, "mp2027.db")
    )
    requested_db_path = os.path.abspath(db_path) if db_path else None
    requested_output_dir = os.path.abspath(output_dir or os.path.join(os.getcwd(), f"OUTPUT_FY{fiscal_year}"))
    effective_history_root = run_history_root or os.environ.get("MP_MANAGER_TEST_HISTORY_ROOT")
    run_context = None
    conn = None
    preflight_failed = False
    stage_evidence = None
    pipeline_started = time.perf_counter()
    if simulate_baseline_t3_from_t4 or audit_exclude_incomplete_staffing:
        if (requested_db_path is None and not preserve_run_history) or (
            requested_db_path is not None and os.path.normcase(requested_db_path) == os.path.normcase(production_db_path)
        ):
            return False, (
                "Các tùy chọn audit chỉ được phép chạy với db_path cô lập, khác production mp2027.db."
            )

    try:
        log_callback(f"Quy trình năm tài chính {fiscal_year} (Tỷ giá: {exchange_rate:,.0f})")
        
        effective_reference_policy = reference_policy or (
            REFERENCE_POLICY_EXPLICIT_SAME_FY
            if primary_reference_path else (
                REFERENCE_POLICY_LEGACY_FY2027_MAP
                if int(fiscal_year) == 2027 else REFERENCE_POLICY_DISABLED
            )
        )
        if primary_reference_path and effective_reference_policy != REFERENCE_POLICY_EXPLICIT_SAME_FY:
            raise ValueError("File tham khảo do người dùng chọn chỉ được dùng với EXPLICIT_SAME_FY.")
        if primary_reference_fill and effective_reference_policy == REFERENCE_POLICY_DISABLED:
            raise ValueError("Điền theo tham khảo yêu cầu chọn rõ file cùng năm tài chính.")
        run_context = create_fiscal_run_context(
            fiscal_year,
            template_path=template_path,
            source_dir=source_dir,
            headcount_source_dir=headcount_source_dir,
            uniform_policy_path=uniform_policy_path,
            output_dir=requested_output_dir,
            exchange_rate=exchange_rate,
            exchange_rate_source=exchange_rate_source,
            history_root=effective_history_root,
            manual_input_store=manual_input_store,
            reference_policy=effective_reference_policy,
            base_dir=BASE_DIR,
        )
        preflight_started = time.perf_counter()
        preflight = preflight_fiscal_run(run_context)
        accepted_missing = tuple(sorted({str(value) for value in accepted_missing_categories}))
        unaccepted_preflight_issues = preflight.unaccepted_issues(accepted_missing)
        incomplete_run = bool(preflight.continuable_issues) and not unaccepted_preflight_issues
        run_context = run_context.with_resolution(preflight.resolved_sources)
        # Keep the legacy FY2027 shared DB discoverable without modifying it.
        if preserve_run_history and requested_db_path is None:
            register_legacy_fy2027_database(str(run_context.history_root), production_db_path)
        # The history workspace is safe to create before calculation: it holds
        # only evidence and reports, never shared calculation data.
        if preserve_run_history and requested_db_path is None:
            initial_status = RUN_STATUS_RUNNING if not unaccepted_preflight_issues else RUN_STATUS_PRECHECK_FAILED
            run_context = create_run_workspace(
                run_context,
                target_cc=target_cc,
                initial_status=initial_status,
                initial_error_summary=(
                    "\n".join(issue.as_text() for issue in unaccepted_preflight_issues)
                    if unaccepted_preflight_issues else None
                ),
            )
            stage_evidence = PipelineStageEvidence(
                str(run_context.workspace_dir),
                run_context.run_id,
                started_perf=pipeline_started,
            )
            stage_evidence.start("preflight", started_perf=preflight_started)
            write_run_manifest(run_context)
            report_payload = preflight.as_dict()
            report_payload["accepted_missing_categories"] = list(accepted_missing)
            report_payload["incomplete_run"] = incomplete_run
            report_path = os.path.join(str(run_context.workspace_dir), "reports", "preflight_report.json")
            with open(report_path, "w", encoding="utf-8") as handle:
                json.dump(report_payload, handle, ensure_ascii=False, indent=2)
            readable_report_path = os.path.join(str(run_context.workspace_dir), "reports", "preflight_report.md")
            with open(readable_report_path, "w", encoding="utf-8") as handle:
                handle.write(preflight.as_markdown())
                if incomplete_run:
                    handle.write(
                        "\n> KẾT QUẢ CHƯA ĐẦY ĐỦ: người dùng đã chấp nhận thiếu các nhóm nguồn: "
                        + ", ".join(accepted_missing)
                        + ".\n"
                    )
            log_callback(f"Báo cáo kiểm tra nguồn: {report_path}")
        if unaccepted_preflight_issues:
            preflight_failed = True
            preflight_error = "\n".join(issue.as_text() for issue in unaccepted_preflight_issues)
            if stage_evidence is not None:
                stage_evidence.finalize(
                    RUN_STATUS_PRECHECK_FAILED,
                    error_summary=preflight_error,
                )
            preflight.raise_if_invalid(accepted_missing)
        if incomplete_run:
            log_callback(
                "CẢNH BÁO — KẾT QUẢ CHƯA ĐẦY ĐỦ: thiếu nguồn "
                + ", ".join(accepted_missing)
                + ". Các phần bị ảnh hưởng không dùng dữ liệu từ lần chạy cũ."
            )
        if stage_evidence is not None:
            stage_evidence.complete(details={
                "status": "INCOMPLETE_ACCEPTED" if incomplete_run else "PASS",
                "accepted_missing_categories": list(accepted_missing),
            })

        # Production runs are immutable. Explicit db_path is retained for
        # isolated tests and diagnostic runs that deliberately manage storage.
        if preserve_run_history and requested_db_path is None:
            db_path = str(run_context.database_path)
            output_dir = os.path.join(str(run_context.workspace_dir), "outputs")
        else:
            db_path = requested_db_path or production_db_path
            output_dir = requested_output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # 2. Database & Loading
        if stage_evidence is not None:
            stage_evidence.start("initialize_database")
        conn = get_connection(db_path)
        create_schema(conn)
        init_sys_params(
            conn,
            exchange_rate=exchange_rate,
            fiscal_year=fiscal_year,
            exchange_rate_source=run_context.exchange_rate_source,
        )
        if run_context is not None and run_context.workspace_dir:
            if fiscal_year == 2027:
                migrated = migrate_legacy_fy2027_manual_inputs(
                    run_context.manual_input_store, production_db_path
                )
                if sum(migrated.values()):
                    log_callback("Đã chuyển dữ liệu nhập tay FY2027 từ kho cũ sang kho theo năm (không sửa mp2027.db).")

        # Clear old transaction data
        cursor = conn.cursor()
        cursor.execute("DELETE FROM fact_input_data")
        cursor.execute("DELETE FROM fact_allocation_log")
        cursor.execute("DELETE FROM fact_missing_inputs")
        conn.commit()
        if stage_evidence is not None:
            stage_evidence.complete()
            stage_evidence.start("import_sources")
        
        log_callback("Đang nạp dữ liệu gốc...")
        load_all(
            db_path=db_path,
            template_path=template_path,
            fiscal_year=fiscal_year,
            exchange_rate=exchange_rate,
            search_dir=source_dir,
            uniform_eligibility_path=run_context.uniform_policy_path,
        )

        staffing_dir = os.path.abspath(run_context.headcount_source_dir)
        if not os.path.isdir(staffing_dir):
            raise FileNotFoundError(f"Thư mục nguồn nhân sự & thời gian không tồn tại: {staffing_dir}")
        log_callback(f"Đang đồng bộ nguồn nhân sự & thời gian FY{fiscal_year}: {staffing_dir}")
        staffing_result = import_headcount_time_sources(
            conn,
            staffing_dir,
            fiscal_year,
            target_cc=str(target_cc) if target_cc is not None else None,
        )
        parser_results = {"headcount_time_sources": staffing_result}
        for line in _staffing_sync_log_lines(staffing_result):
            log_callback(line)

        if staffing_result["files"] == 0:
            raise ValueError(
                f"Không tìm thấy tệp kế hoạch nhân sự & thời gian FY{fiscal_year} trong {staffing_dir}."
            )
        
        # 3. Parsers
        manifest_lines = describe_manifest(source_dir)
        if manifest_lines:
            log_callback("Thứ tự tệp nguồn đã cấu hình:")
            for line in manifest_lines:
                log_callback(f"  {line}")

        facility_result = _timed_call(log_callback, "đọc Cơ sở vật chất", parse_facility, conn, source_dir=source_dir)
        parser_results["facility"] = facility_result
        fixed_assets_result = _timed_call(
            log_callback, "đọc Tài sản cố định", parse_fixed_assets, conn, source_dir=source_dir
        )
        parser_results["fixed_assets"] = fixed_assets_result
        it_result = _timed_call(
            log_callback, "đọc Mô phỏng hệ thống", parse_it_simulation, conn, source_dir=source_dir
        )
        parser_results["it_simulation"] = it_result
        ga_result = _timed_call(log_callback, "đọc Tổng vụ", parse_ga, conn, source_dir=source_dir)
        parser_results["ga"] = ga_result
        log_callback(f"Dữ liệu Tổng vụ: đơn giá={ga_result.get('total', 0)}, nhân sự={ga_result.get('headcount', 0)}")
        birthday_result = parse_birthday_workbook(conn, source_dir=source_dir)
        parser_results["birthday_workbook"] = birthday_result
        log_callback(
            "Tệp sinh nhật: thêm={inserted}, bỏ qua={skipped}, lỗi={errors}, tệp={path}".format(
                inserted=birthday_result.get("inserted", 0),
                skipped=birthday_result.get("skipped", 0),
                errors=birthday_result.get("errors", 0),
                path=birthday_result.get("path", ""),
            )
        )
        manual_hc_result = _parse_manual_headcount(conn, source_dir)
        # Copy editable annual entries only after parsers have refreshed their
        # own manual tables.  In particular, the legacy CSV parser clears bus
        # drivers; copying earlier silently discarded values entered in the UI.
        copied_manual = copy_annual_manual_inputs(
            conn, fiscal_year, run_context.manual_input_store
        ) if run_context is not None and run_context.workspace_dir else {}
        copied_total = sum(copied_manual.values())
        if copied_total:
            log_callback(f"Đã sao chép {copied_total} dữ liệu nhập tay của FY{fiscal_year} vào lần chạy cô lập.")
        manual_time_rows = apply_manual_time_overrides(conn, fiscal_year, target_cc=target_cc)
        if manual_time_rows:
            log_callback(f"Đã áp dụng {manual_time_rows} dòng thời gian nhập thủ công.")
        manual_baseline_rows = apply_manual_baseline_overrides(conn, fiscal_year, target_cc=target_cc)
        if manual_baseline_rows:
            log_callback(f"Đã áp dụng {manual_baseline_rows} baseline T3 nhập thủ công.")
        parser_results["manual_headcount"] = manual_hc_result
        log_callback(
            "Nhân sự nhập tay: thêm={inserted}, bỏ qua={skipped}, lỗi={errors}, "
            "chỉ bổ sung Nam/Nữ={supplemental_only}, tệp={path}".format(
                inserted=manual_hc_result.get("inserted", 0),
                skipped=manual_hc_result.get("skipped", 0),
                errors=manual_hc_result.get("errors", 0),
                supplemental_only=manual_hc_result.get("supplemental_only", 0),
                path=manual_hc_result.get("template_path", ""),
            )
        )
        manual_special_result = parse_manual_special_costs(conn, source_dir=source_dir)
        parser_results["manual_special_costs"] = manual_special_result
        log_callback(
            "Chi phí đặc biệt nhập tay: thêm={inserted}, bỏ qua={skipped}, lỗi={errors}, tệp={path}".format(
                inserted=manual_special_result.get("inserted", 0),
                skipped=manual_special_result.get("skipped", 0),
                errors=manual_special_result.get("errors", 0),
                path=manual_special_result.get("template_path", ""),
            )
        )
        manual_event_result = parse_manual_event_drivers(conn, source_dir=source_dir)
        parser_results["manual_event_drivers"] = manual_event_result
        log_callback(
            "Sự kiện nhập tay: thêm={inserted}, bỏ qua={skipped}, lỗi={errors}, tệp={path}".format(
                inserted=manual_event_result.get("inserted", 0),
                skipped=manual_event_result.get("skipped", 0),
                errors=manual_event_result.get("errors", 0),
                path=manual_event_result.get("template_path", ""),
            )
        )
        nnn_result = parse_nnn_paperwork(conn, source_dir=source_dir)
        parser_results["nnn_paperwork"] = nnn_result
        log_callback(
            "Tệp giấy tờ NNN: thêm={inserted}, bỏ qua={skipped}, lỗi={errors}, tệp={path}".format(
                inserted=nnn_result.get("inserted", 0),
                skipped=nnn_result.get("skipped", 0),
                errors=nnn_result.get("errors", 0),
                path=nnn_result.get("path", ""),
            )
        )

        if stage_evidence is not None:
            stage_evidence.complete(details={"parser_count": len(parser_results)})
            stage_evidence.start("validate_staffing")

        # 4. Kiểm tra nguồn sự thật trước khi tính phân bổ
        audit_excluded_ccs: list[str] = []
        if audit_exclude_incomplete_staffing:
            audit_excluded_ccs = _exclude_incomplete_staffing_ccs_for_audit(conn, fiscal_year)
            log_callback(
                "Audit staffing scope: loại khỏi lần chạy "
                f"{len(audit_excluded_ccs)} CC thiếu kế hoạch 12 tháng/time: "
                + (", ".join(audit_excluded_ccs) if audit_excluded_ccs else "không có")
            )
        if simulate_baseline_t3_from_t4:
            simulated_count = _simulate_missing_baseline_from_april(
                conn,
                fiscal_year,
                target_cc=target_cc,
            )
            log_callback(
                "Audit baseline simulation: "
                f"đã tạo {simulated_count} dòng SIMULATED_BASELINE_T3_FROM_T4."
            )
        staffing_issues = _staffing_preflight(
            conn,
            fiscal_year,
            target_cc=target_cc,
            excluded_ccs=set(audit_excluded_ccs),
        )
        if staffing_issues:
            scope = f"CC {target_cc}" if target_cc else "toàn bộ CC dự kiến xuất"
            details = "\n".join(f"- {issue}" for issue in staffing_issues)
            raise ValueError(
                f"Kiểm tra nguồn nhân sự & thời gian FY{fiscal_year} không đạt cho {scope}.\n"
                f"Chương trình dừng trước khi tính phân bổ và xuất FORM để tránh kết quả sai.\n{details}"
            )
        supplemental_rows = conn.execute(
            """
            SELECT COUNT(*)
            FROM fact_monthly_headcount AS manual
            WHERE manual.source='manual'
              AND EXISTS (
                  SELECT 1 FROM fact_monthly_headcount AS source
                  WHERE source.source='department_plan'
                    AND CAST(source.cc_code AS TEXT)=CAST(manual.cc_code AS TEXT)
                    AND source.period=manual.period
              )
            """
        ).fetchone()[0]
        log_callback(
            f"Kiểm tra nguồn nhân sự & thời gian đạt: "
            f"{'CC ' + str(target_cc) if target_cc else 'toàn bộ CC dự kiến xuất'}. "
            f"Có {supplemental_rows} dòng nhập tay chỉ được dùng bổ sung Nam/Nữ; "
            "không thay số nhân viên, công nhân hoặc tổng người."
        )

        if stage_evidence is not None:
            stage_evidence.complete(details={"supplemental_rows": int(supplemental_rows)})
            stage_evidence.start("allocation")

        # 5. Allocation Engine
        log_callback("Đang tính phân bổ...")
        engine = _create_allocation_engine(conn, target_cc=target_cc)
        _timed_call(log_callback, "xác định tài khoản và tính phân bổ", engine.run_allocation)
        if stage_evidence is not None:
            stage_evidence.complete()
            stage_evidence.start("export_workbooks")
        
        # 5. Export Logic
        source_file_by_category = {
            category: os.path.basename(paths[0])
            for category, paths in run_context.resolved_sources.items()
            if paths
        }
        builder = HubBuilder(
            conn, fiscal_year=fiscal_year, source_file_by_category=source_file_by_category
        )
        
        resolved = run_context.resolved_sources
        facility_source_path = (resolved.get("facility") or [None])[0]
        admin_source_path = (resolved.get("ga") or [None])[0]
        allocation_source_path = (resolved.get("allocation_rules") or [None])[0]
        system_source_paths = list(resolved.get("it_simulation") or [])
        if target_cc:
            # Single Export
            log_callback(f"Đang xuất riêng mã bộ phận: {target_cc}")
            out_path = os.path.join(output_dir, f"MP_CC_{target_cc}.xlsx")
            complete_v1_primary_path = None
            if mp_saisan_complete_v1 and run_context.reference_policy != REFERENCE_POLICY_DISABLED:
                complete_v1_primary_path = _try_resolve_primary_reference_path(
                    target_cc=target_cc,
                    primary_reference_path=primary_reference_path,
                    reference_map_path=reference_map_path,
                    fiscal_year=fiscal_year,
                )
            builder.export_to_template(template_path, out_path, cc_code=target_cc)
            complete_v1_dynamic_allocation_rows = (
                _load_complete_v1_dynamic_allocation_rows(builder, target_cc)
                if mp_saisan_complete_v1
                else []
            )
            complete_v1_fiscal_periods = get_fy_months(fiscal_year) if mp_saisan_complete_v1 else []
            output_workbook_exists = os.path.exists(out_path)
            if facility_file_order_export and facility_source_path and output_workbook_exists and (explicit_facility_file_order_export or template_is_excel):
                apply_facility_file_order_to_workbook(
                    workbook_path=out_path,
                    facility_source_path=facility_source_path,
                    cost_center=target_cc,
                    start_row=facility_file_order_start_row,
                )
                log_callback(f"Đã áp dụng xuất Cơ sở vật chất theo thứ tự tệp: {out_path}")
            if admin_consumables_export and admin_source_path and allocation_source_path and output_workbook_exists and (explicit_admin_consumables_export or template_is_excel):
                apply_admin_consumables_to_workbook(
                    workbook_path=out_path,
                    admin_source_path=admin_source_path,
                    allocation_source_path=allocation_source_path,
                    cost_center=target_cc,
                    start_row=admin_consumables_start_row,
                    fiscal_year=fiscal_year,
                )
                log_callback(f"Đã áp dụng xuất vật tư Tổng vụ: {out_path}")
            if system_cost_export and system_source_paths and output_workbook_exists and (explicit_system_cost_export or template_is_excel):
                apply_system_cost_to_workbook(
                    workbook_path=out_path,
                    system_source_paths=system_source_paths,
                    fiscal_year=fiscal_year,
                    cost_center=target_cc,
                    start_row=system_cost_start_row,
                )
                log_callback(f"Đã áp dụng xuất chi phí hệ thống: {out_path}")
            if (
                mp_saisan_complete_v1
                and output_workbook_exists
                and template_is_excel
                and (primary_reference_fill or complete_v1_primary_path or fixed_assets_reference_skeleton_export)
            ):
                _apply_complete_v1_source_order(
                    out_path, log_callback, phase="pre-reference",
                    source_file_order=_annual_complete_v1_source_order(run_context),
                )
            if primary_reference_fill:
                primary_path = _resolve_primary_reference_path(
                    target_cc=target_cc,
                    primary_reference_path=primary_reference_path,
                    reference_map_path=reference_map_path,
                    fiscal_year=fiscal_year,
                )
                invariant_path = os.path.join(
                    BASE_DIR,
                    "docs",
                    "audits",
                    "phase42n2b_invariant_gap_accounting.csv",
                )
                fill_result = apply_reference_assisted_fill_to_workbook(
                    workbook_path=out_path,
                    primary_path=primary_path,
                    invariant_csv_path=invariant_path,
                    start_row=primary_reference_fill_start_row,
                )
                log_callback(f"Đã áp dụng điền theo tệp tham chiếu chính: {fill_result}")
            if mp_saisan_complete_v1 and complete_v1_primary_path:
                complete_result = apply_mp_saisan_complete_v1(
                    workbook_path=out_path,
                    target_cc=target_cc,
                    primary_reference_path=complete_v1_primary_path,
                    reference_map_path=reference_map_path or _default_reference_map_path(),
                    fixed_assets_skeleton_csv=fixed_assets_skeleton_csv or _default_fixed_assets_skeleton_csv_path(),
                    invariant_csv_path=os.path.join(
                        BASE_DIR,
                        "docs",
                        "audits",
                        "phase42n2b_invariant_gap_accounting.csv",
                    ),
                )
                log_callback(f"Đã áp dụng hoàn chỉnh MP Saisan v1: {complete_result}")
            if fixed_assets_reference_skeleton_export:
                if primary_reference_fill:
                    raise ValueError(
                        "Nguy cơ trùng dữ liệu: --fixed-assets-reference-skeleton-export không thể chạy cùng "
                        "--primary-reference-fill hoặc --file-order-export-v2. Hãy chạy riêng."
                    )
                skeleton_result = apply_fixed_assets_reference_skeleton_to_workbook(
                    workbook_path=out_path,
                    csv_path=fixed_assets_skeleton_csv or _default_fixed_assets_skeleton_csv_path(),
                    start_row=fixed_assets_skeleton_start_row,
                )
                log_callback(f"Đã áp dụng khung tham chiếu tài sản cố định: {skeleton_result}")
            if mp_saisan_complete_v1 and output_workbook_exists and template_is_excel:
                _apply_complete_v1_source_order(
                    out_path,
                    log_callback,
                    phase="final",
                    dynamic_allocation_rows=complete_v1_dynamic_allocation_rows,
                    fiscal_periods=complete_v1_fiscal_periods,
                    source_file_order=_annual_complete_v1_source_order(run_context),
                )
            log_callback(f"Hoàn tất: {output_dir}")
        else:
            # Batch Export
            log_callback("Đang xuất hàng loạt...")
            cursor.execute("SELECT DISTINCT cc_code FROM fact_input_data WHERE account_code > 0")
            excluded_set = set(audit_excluded_ccs)
            all_ccs = [row[0] for row in cursor.fetchall() if str(row[0]) not in excluded_set]
            
            count = 0
            for cc in all_ccs:
                out_path = os.path.join(output_dir, f"MP_CC_{cc}.xlsx")
                if builder.export_to_template(template_path, out_path, cc_code=cc):
                    if facility_file_order_export and facility_source_path:
                        apply_facility_file_order_to_workbook(
                            workbook_path=out_path,
                            facility_source_path=facility_source_path,
                            cost_center=cc,
                            start_row=facility_file_order_start_row,
                        )
                        log_callback(f"Đã áp dụng xuất Cơ sở vật chất theo thứ tự tệp: {out_path}")
                    if admin_consumables_export and admin_source_path and allocation_source_path:
                        apply_admin_consumables_to_workbook(
                            workbook_path=out_path,
                            admin_source_path=admin_source_path,
                            allocation_source_path=allocation_source_path,
                            cost_center=cc,
                            start_row=admin_consumables_start_row,
                            fiscal_year=fiscal_year,
                        )
                        log_callback(f"Đã áp dụng xuất vật tư Tổng vụ: {out_path}")
                    if system_cost_export and system_source_paths:
                        apply_system_cost_to_workbook(
                            workbook_path=out_path,
                            system_source_paths=system_source_paths,
                            fiscal_year=fiscal_year,
                            cost_center=cc,
                            start_row=system_cost_start_row,
                        )
                        log_callback(f"Đã áp dụng xuất chi phí hệ thống: {out_path}")
                    if primary_reference_fill:
                        primary_path = _resolve_primary_reference_path(
                            target_cc=cc,
                            primary_reference_path=primary_reference_path,
                            reference_map_path=reference_map_path,
                            fiscal_year=fiscal_year,
                        )
                        invariant_path = os.path.join(
                            BASE_DIR,
                            "docs",
                            "audits",
                            "phase42n2b_invariant_gap_accounting.csv",
                        )
                        fill_result = apply_reference_assisted_fill_to_workbook(
                            workbook_path=out_path,
                            primary_path=primary_path,
                            invariant_csv_path=invariant_path,
                            start_row=primary_reference_fill_start_row,
                        )
                        log_callback(f"Đã áp dụng điền theo tệp tham chiếu chính: {fill_result}")
                    if fixed_assets_reference_skeleton_export:
                        if primary_reference_fill:
                            raise ValueError(
                                "Nguy cơ trùng dữ liệu: --fixed-assets-reference-skeleton-export không thể chạy cùng "
                                "--primary-reference-fill hoặc --file-order-export-v2. Hãy chạy riêng."
                            )
                        skeleton_result = apply_fixed_assets_reference_skeleton_to_workbook(
                            workbook_path=out_path,
                            csv_path=fixed_assets_skeleton_csv or _default_fixed_assets_skeleton_csv_path(),
                            start_row=fixed_assets_skeleton_start_row,
                        )
                        log_callback(f"Đã áp dụng khung tham chiếu tài sản cố định: {skeleton_result}")
                    if mp_saisan_complete_v1:
                        complete_v1_dynamic_rows = _load_complete_v1_dynamic_allocation_rows(builder, cc)
                        complete_v1_periods = get_fy_months(fiscal_year)
                        complete_v1_primary_path = None
                        if run_context.reference_policy != REFERENCE_POLICY_DISABLED:
                            complete_v1_primary_path = _try_resolve_primary_reference_path(
                                target_cc=cc,
                                primary_reference_path=primary_reference_path,
                                reference_map_path=reference_map_path,
                                fiscal_year=fiscal_year,
                            )
                        if complete_v1_primary_path:
                            _apply_complete_v1_source_order(
                                out_path, log_callback, phase="pre-reference",
                                source_file_order=_annual_complete_v1_source_order(run_context),
                            )
                            complete_result = apply_mp_saisan_complete_v1(
                                workbook_path=out_path,
                                target_cc=cc,
                                primary_reference_path=complete_v1_primary_path,
                                reference_map_path=reference_map_path or _default_reference_map_path(),
                                fixed_assets_skeleton_csv=fixed_assets_skeleton_csv or _default_fixed_assets_skeleton_csv_path(),
                                invariant_csv_path=os.path.join(
                                    BASE_DIR,
                                    "docs",
                                    "audits",
                                    "phase42n2b_invariant_gap_accounting.csv",
                                ),
                            )
                            log_callback(f"Đã áp dụng hoàn chỉnh MP Saisan v1: {complete_result}")
                        _apply_complete_v1_source_order(
                            out_path,
                            log_callback,
                            phase="final",
                            dynamic_allocation_rows=complete_v1_dynamic_rows,
                            fiscal_periods=complete_v1_periods,
                            source_file_order=_annual_complete_v1_source_order(run_context),
                        )
                    count += 1
            
            log_callback(f"Đã xuất thành công {count} tệp vào: {output_dir}")

        if stage_evidence is not None:
            stage_evidence.complete(details={"target_cc": str(target_cc) if target_cc is not None else None})
            stage_evidence.start("audit_reports")
        report_dir = os.path.join(output_dir, "BAO_CAO_KIEM_TRA")
        os.makedirs(report_dir, exist_ok=True)
        if incomplete_run:
            marker_path = os.path.join(report_dir, "KET_QUA_CHUA_DAY_DU.txt")
            with open(marker_path, "w", encoding="utf-8") as marker:
                marker.write(
                    "KẾT QUẢ CHƯA ĐẦY ĐỦ\n\n"
                    "Lần chạy này được người dùng xác nhận tiếp tục dù thiếu nguồn độc lập: "
                    + ", ".join(accepted_missing)
                    + ".\n"
                    "Các phần bị ảnh hưởng không dùng dữ liệu từ lần chạy cũ.\n"
                )
            log_callback(f"Đã ghi nhãn kết quả chưa đầy đủ: {marker_path}")
        output_workbooks = [
            os.path.join(output_dir, name)
            for name in os.listdir(output_dir)
            if name.lower().endswith(".xlsx") and name.startswith("MP_CC_")
        ]
        exchange_results = [
            audit_exchange_rate_workbook(path, exchange_rate) for path in output_workbooks
        ]
        exchange_report = write_exchange_rate_audit_report(
            os.path.join(report_dir, "KIEM_TRA_TY_GIA.xlsx"),
            exchange_rate,
            "Tỷ giá người dùng chọn cho lần chạy này",
            exchange_results,
        )
        log_callback(f"Báo cáo kiểm tra tỷ giá: {exchange_report}")

        audit_result = _timed_call(
            log_callback,
            "lập báo cáo kiểm tra",
            write_pipeline_audit_report,
            conn=conn,
            output_dir=report_dir,
            source_dir=source_dir,
            fiscal_year=fiscal_year,
            target_cc=target_cc,
            parser_results=parser_results,
        )
        log_callback(f"Báo cáo tóm tắt lần chạy: {audit_result['report_path']}")
        log_callback(f"Báo cáo dữ liệu cần bổ sung: {audit_result['missing_csv_path']}")
        if stage_evidence is not None:
            stage_evidence.complete(
                details={"report_path": str(audit_result["report_path"])}
            )

        if facility_file_order_preview:
            if not facility_source_path:
                raise ValueError("Không tìm được nguồn Cơ sở vật chất đúng năm để tạo tệp xem trước.")
            preview_output = facility_preview_output or os.path.join(
                BASE_DIR,
                "dist",
                "preview",
                "facility_file_order_preview.xlsx",
            )
            if target_cc is None:
                raise ValueError("Xem trước Cơ sở vật chất theo thứ tự nguồn cần tham số --target-cc.")
            preview_cc = target_cc
            preview_path = write_facility_file_order_preview_workbook(
                template_path=template_path,
                facility_source_path=facility_source_path,
                output_path=preview_output,
                cost_center=preview_cc,
                start_row=facility_preview_start_row,
            )
            log_callback(f"Tệp xem trước Cơ sở vật chất theo thứ tự nguồn: {preview_path}")
        
        if stage_evidence is not None:
            stage_evidence.start("publication")
        if conn is not None:
            conn.commit()
            _close_pipeline_connection(conn, rollback=False, log_callback=log_callback)
            conn = None

        published_output = output_dir
        if run_context is not None and run_context.workspace_dir:
            publication_mode = "merge" if target_cc is not None else "replace"
            published_output = publish_run_output(
                run_context,
                output_dir,
                mode=publication_mode,
                target_cc=target_cc,
            )
            if stage_evidence is not None:
                stage_evidence.complete(
                    details={"mode": publication_mode, "output_path": str(published_output)}
                )
                stage_evidence.finalize(
                    RUN_STATUS_SUCCEEDED_INCOMPLETE if incomplete_run else RUN_STATUS_SUCCEEDED
                )
            register_run(
                run_context,
                RUN_STATUS_SUCCEEDED_INCOMPLETE if incomplete_run else RUN_STATUS_SUCCEEDED,
                target_cc=target_cc,
                output_path=published_output,
                error_summary=(
                    "KẾT QUẢ CHƯA ĐẦY ĐỦ — đã chấp nhận thiếu nguồn: "
                    + ", ".join(accepted_missing)
                    if incomplete_run else None
                ),
            )
        return True, published_output


    except (FileNotFoundError, BadZipFile) as e:
        _close_pipeline_connection(
            conn, rollback=True, log_callback=log_callback, suppress_errors=True
        )
        conn = None
        message = _friendly_pipeline_error_message(e)
        log_callback(f"LỖI: {message}")
        trace_path = _write_failure_traceback(run_context, e)
        if trace_path:
            log_callback(f"Chi tiết lỗi đã lưu: {trace_path}")
        _log_debug_traceback(log_callback)
        if stage_evidence is not None:
            stage_evidence.finalize(RUN_STATUS_FAILED, error_summary=message)
        if run_context is not None and run_context.workspace_dir and not preflight_failed:
            register_run(run_context, RUN_STATUS_FAILED, target_cc=target_cc, error_summary=message)
        return False, message

    except Exception as e:
        _close_pipeline_connection(
            conn, rollback=True, log_callback=log_callback, suppress_errors=True
        )
        conn = None
        message = _friendly_pipeline_error_message(e)
        log_callback(f"LỖI: {message}")
        trace_path = _write_failure_traceback(run_context, e)
        if trace_path:
            log_callback(f"Chi tiết lỗi đã lưu: {trace_path}")
        _log_debug_traceback(log_callback)
        if stage_evidence is not None:
            stage_evidence.finalize(RUN_STATUS_FAILED, error_summary=message)
        if run_context is not None and run_context.workspace_dir and not preflight_failed:
            register_run(run_context, RUN_STATUS_FAILED, target_cc=target_cc, error_summary=message)
        return False, message

    finally:
        _close_pipeline_connection(
            conn, rollback=True, log_callback=log_callback, suppress_errors=True
        )
        conn = None

def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--fy', type=int, default=2027)
    parser.add_argument('--template', type=str, default=None)
    parser.add_argument('--source', type=str, default=None)
    parser.add_argument('--headcount-source', type=str, default=None)
    parser.add_argument('--uniform-policy', type=str, default=None)
    parser.add_argument('--operational-db', type=str, default=None)
    parser.add_argument('--manual-input-store', type=str, default=None)
    parser.add_argument('--output-dir', type=str, default=None)
    parser.add_argument('--run-history-root', type=str, default=None)
    parser.add_argument(
        '--no-run-history',
        action='store_true',
        help='Diagnostic only: do not create the immutable run-history workspace.',
    )
    parser.add_argument('--exchange-rate', type=float, default=25450.0)
    parser.add_argument('--exchange-rate-source', type=str, default="explicit pipeline input")
    parser.add_argument('--target-cc', type=int, default=None)
    parser.add_argument(
        '--accept-missing-source',
        action='append',
        default=[],
        help='Chỉ dùng sau xác nhận: chấp nhận một nhóm nguồn chi phí độc lập đang thiếu.',
    )
    parser.add_argument(
        '--facility-file-order-preview',
        action='store_true',
        help='Explicit opt-in: create Facility file-order preview workbook after the normal pipeline.',
    )
    parser.add_argument(
        '--facility-preview-output',
        type=str,
        default=None,
        help='Output path for Facility preview workbook. Defaults to dist/preview/facility_file_order_preview.xlsx when preview is enabled.',
    )
    parser.add_argument('--facility-preview-start-row', type=int, default=200)
    parser.add_argument(
        '--facility-file-order-export',
        action='store_true',
        help='Explicit opt-in: apply Facility file-order rows to generated output workbook(s).',
    )
    parser.add_argument('--facility-file-order-start-row', type=int, default=200)
    parser.add_argument(
        '--admin-consumables-export',
        action='store_true',
        help='Explicit opt-in: apply Admin consumables file-order rows to generated output workbook(s).',
    )
    parser.add_argument('--admin-consumables-start-row', type=int, default=207)
    parser.add_argument(
        '--system-cost-export',
        action='store_true',
        help='Explicit opt-in: apply System Cost file-order single row to generated output workbook(s).',
    )
    parser.add_argument('--system-cost-start-row', type=int, default=211)
    parser.add_argument(
        '--file-order-export-v1',
        action='store_true',
        help='Explicit opt-in: apply Facility, Admin consumables, and System Cost file-order rows with v1 row placement.',
    )
    parser.add_argument(
        '--primary-reference-fill',
        action='store_true',
        help='Explicit opt-in: append primary reference-assisted rows with provenance labels after normal export.',
    )
    parser.add_argument('--primary-reference-fill-start-row', type=int, default=213)
    parser.add_argument(
        '--file-order-export-v2',
        action='store_true',
        help='Explicit opt-in: v1 file-order export plus primary reference-assisted fill starting at row 213.',
    )
    parser.add_argument(
        '--primary-reference-path',
        type=str,
        default=None,
        help='Primary reference workbook for reference-assisted fill. Required unless the target CC is mapped.',
    )
    parser.add_argument('--reference-map-path', type=str, default=_default_reference_map_path())
    parser.add_argument(
        '--reference-policy',
        choices=(REFERENCE_POLICY_DISABLED, REFERENCE_POLICY_EXPLICIT_SAME_FY, REFERENCE_POLICY_LEGACY_FY2027_MAP),
        default=None,
        help='Chính sách dùng file kết quả tham khảo; FY2028+ chỉ chấp nhận EXPLICIT_SAME_FY với file cùng năm.',
    )
    parser.add_argument(
        '--fixed-assets-reference-skeleton-export',
        action='store_true',
        help='Explicit opt-in: append fixed-assets secondary skeleton rows with not-source-derived provenance.',
    )
    parser.add_argument(
        '--fixed-assets-skeleton-csv',
        type=str,
        default=_default_fixed_assets_skeleton_csv_path(),
        help='42N2E fixed-assets secondary skeleton candidate CSV.',
    )
    parser.add_argument('--fixed-assets-skeleton-start-row', type=int, default=None)
    parser.add_argument(
        '--mp-saisan-complete-v1',
        action='store_true',
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)
    template_path = args.template or os.path.join(BASE_DIR, "docs", f"MP{args.fy}", "FORM.xlsx")
    source_dir = args.source or _default_source_dir(args.fy)

    success, message = run_universal_pipeline(
        fiscal_year=args.fy,
        template_path=template_path,
        source_dir=source_dir,
        exchange_rate=args.exchange_rate,
        exchange_rate_source=args.exchange_rate_source,
        target_cc=args.target_cc,
        headcount_source_dir=args.headcount_source,
        uniform_policy_path=args.uniform_policy,
        operational_db_path=args.operational_db,
        manual_input_store=args.manual_input_store,
        output_dir=args.output_dir,
        run_history_root=args.run_history_root,
        preserve_run_history=not args.no_run_history,
        accepted_missing_categories=tuple(args.accept_missing_source),
        facility_file_order_preview=args.facility_file_order_preview,
        facility_preview_output=args.facility_preview_output,
        facility_preview_start_row=args.facility_preview_start_row,
        facility_file_order_export=args.facility_file_order_export,
        facility_file_order_start_row=args.facility_file_order_start_row,
        admin_consumables_export=args.admin_consumables_export,
        admin_consumables_start_row=args.admin_consumables_start_row,
        system_cost_export=args.system_cost_export,
        system_cost_start_row=args.system_cost_start_row,
        file_order_export_v1=args.file_order_export_v1,
        primary_reference_fill=args.primary_reference_fill,
        primary_reference_fill_start_row=args.primary_reference_fill_start_row,
        file_order_export_v2=args.file_order_export_v2,
        primary_reference_path=args.primary_reference_path,
        reference_map_path=args.reference_map_path,
        reference_policy=args.reference_policy,
        fixed_assets_reference_skeleton_export=args.fixed_assets_reference_skeleton_export,
        fixed_assets_skeleton_csv=args.fixed_assets_skeleton_csv,
        fixed_assets_skeleton_start_row=args.fixed_assets_skeleton_start_row,
        mp_saisan_complete_v1=True,
    )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
