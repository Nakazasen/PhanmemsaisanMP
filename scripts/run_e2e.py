"""
MP2027 Manager - Universal E2E Execution Pipeline
Supports Single CC and Batch Export.

The canonical export is database-to-FORM in one dynamic write.
"""
import sqlite3
import argparse
import inspect
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
from src.parsers.manual_headcount import copy_missing_baseline_from_april, parse_manual_headcount
from src.parsers.manual_special_costs import parse_manual_special_costs
from src.parsers.nnn_paperwork import parse_nnn_paperwork
from src.parsers.it_sim import parse_it_simulation
from src.parsers.fixed_assets import parse_fixed_assets
from src.engine.allocator import AllocationEngine
from src.engine.dynamic_source_order_export import export_dynamic_source_order
from src.utils.excel_helpers import get_fy_months
from src.utils.fiscal_periods import fiscal_baseline_period
from src.utils.source_manifest import (
    describe_manifest,
    read_source_manifest,
    validate_cost_source_manifest,
)
from src.services.headcount_source_importer import import_headcount_time_sources

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


def _default_template_path() -> str:
    candidate = os.path.join(BASE_DIR, "docs", "MP2027", "FORM.xlsx")
    if os.path.exists(candidate):
        return candidate
    # In packaged (COLLECT) mode, BASE_DIR is the exe dir but bundled data
    # lives under sys._MEIPASS (_internal/).
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        meipass_candidate = os.path.join(meipass, "docs", "MP2027", "FORM.xlsx")
        if os.path.exists(meipass_candidate):
            return meipass_candidate
    raise FileNotFoundError(
        f"Không tìm thấy tệp mẫu bắt buộc: {candidate}. "
        "Không dùng lại FORM.xlsx cũ ở thư mục gốc vì tệp đó có công thức mẫu đã lỗi thời."
    )


def _default_source_dir() -> str:
    candidate = os.path.join(BASE_DIR, "docs", "MP2027")
    if os.path.isdir(candidate):
        return candidate
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        meipass_candidate = os.path.join(meipass, "docs", "MP2027")
        if os.path.isdir(meipass_candidate):
            return meipass_candidate
    return BASE_DIR


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
    return (
        "Đã xảy ra lỗi khi chạy chương trình. "
        "Hãy kiểm tra lại Tệp mẫu FORM, Thư mục nguồn và chạy lại. "
        "Nếu cần điều tra sâu, bật MP2027_DEBUG_TRACEBACK=1 để lấy chi tiết kỹ thuật."
    )


def _log_debug_traceback(log_callback) -> None:
    if os.environ.get("MP2027_DEBUG_TRACEBACK") == "1":
        log_callback(traceback.format_exc())
    else:
        log_callback("Chi tiết kỹ thuật đã được ẩn. Nếu cần điều tra sâu, bật MP2027_DEBUG_TRACEBACK=1 rồi chạy lại.")


def _format_dynamic_export_result_vi(result: dict[str, int]) -> str:
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


def run_universal_pipeline(fiscal_year: int, template_path: str, source_dir: str, 
                           exchange_rate: float = 25450.0,
                           target_cc: int = None,
                           headcount_source_dir: str | None = None,
                           log_callback=None,
                           db_path: str | None = None,
                           output_dir: str | None = None,
                           copy_baseline_t3_from_t4: bool = False,
                           simulate_baseline_t3_from_t4: bool = False,
                           audit_exclude_incomplete_staffing: bool = False,
                           **legacy_output_options):
    """
    Runs the pipeline and exports results to OUTPUT_FY[Year] folder.
    - target_cc: if None, exports every CC represented by generated facts.
    - db_path/output_dir: optional isolation paths; production defaults are unchanged.
    - copy_baseline_t3_from_t4: user-confirmed production fallback persisted to manual CSV.
    - simulate_baseline_t3_from_t4: audit-only fallback with explicit provenance.
    """
    if log_callback is None:
        log_callback = _safe_console_print

    if legacy_output_options:
        names = ", ".join(sorted(legacy_output_options))
        return False, (
            "Chế độ xuất theo dòng cố định không còn được hỗ trợ. "
            f"Hãy bỏ các tham số cũ: {names}."
        )

    production_db_path = os.path.abspath(os.path.join(BASE_DIR, "mp2027.db"))
    requested_db_path = os.path.abspath(db_path) if db_path else None
    if simulate_baseline_t3_from_t4 or audit_exclude_incomplete_staffing:
        if requested_db_path is None or os.path.normcase(requested_db_path) == os.path.normcase(production_db_path):
            return False, (
                "Các tùy chọn audit chỉ được phép chạy với db_path cô lập, khác production mp2027.db."
            )

    try:
        log_callback(f"Quy trình năm tài chính {fiscal_year} (Tỷ giá: {exchange_rate:,.0f})")
        
        # Validate before opening or clearing the database. A staffing-only
        # directory must never be accepted as the cost-source directory.
        validate_cost_source_manifest(source_dir)

        # 1. Setup Environment
        db_path = requested_db_path or production_db_path

        # Output Directory
        output_dir = os.path.abspath(output_dir or os.path.join(os.getcwd(), f"OUTPUT_FY{fiscal_year}"))
        os.makedirs(output_dir, exist_ok=True)
        
        # 2. Database & Loading
        conn = get_connection(db_path)
        create_schema(conn)
        init_sys_params(conn, exchange_rate=exchange_rate, fiscal_year=fiscal_year)
        
        # Clear old transaction data
        cursor = conn.cursor()
        cursor.execute("DELETE FROM fact_input_data")
        cursor.execute("DELETE FROM fact_allocation_log")
        cursor.execute("DELETE FROM fact_missing_inputs")
        conn.commit()
        
        log_callback("Đang nạp dữ liệu gốc...")
        load_all(
            db_path=db_path,
            template_path=template_path,
            fiscal_year=fiscal_year,
            exchange_rate=exchange_rate,
            search_dir=source_dir,
        )

        staffing_dir = os.path.abspath(headcount_source_dir or source_dir)
        if not os.path.isdir(staffing_dir):
            raise FileNotFoundError(f"Thư mục nguồn nhân sự & thời gian không tồn tại: {staffing_dir}")
        log_callback(f"Đang đồng bộ nguồn nhân sự & thời gian FY{fiscal_year}: {staffing_dir}")
        staffing_result = import_headcount_time_sources(conn, staffing_dir, fiscal_year)
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
        if copy_baseline_t3_from_t4:
            copied_baseline = copy_missing_baseline_from_april(
                conn,
                staffing_dir,
                fiscal_year,
                target_cc=target_cc,
                base_dir=BASE_DIR,
            )
            log_callback(
                "Baseline T3: đã sao chép dữ liệu T4 cho "
                f"{copied_baseline['copied']} CC vào {copied_baseline['template_path']}."
            )
        manual_hc_result = _parse_manual_headcount(conn, staffing_dir)
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

        # 5. Allocation Engine
        log_callback("Đang tính phân bổ...")
        engine = _create_allocation_engine(conn, target_cc=target_cc)
        _timed_call(log_callback, "xác định tài khoản và tính phân bổ", engine.run_allocation)
        
        # 5. Export Logic: database -> FORM exactly once.
        builder = None
        manifest_entries = read_source_manifest(source_dir)
        if target_cc:
            # Single Export
            log_callback(f"Đang xuất riêng mã bộ phận: {target_cc}")
            out_path = os.path.join(output_dir, f"MP_CC_{target_cc}.xlsx")
            dynamic_result = export_dynamic_source_order(
                conn,
                fiscal_year=fiscal_year,
                template_path=template_path,
                output_path=out_path,
                cc_code=target_cc,
                manifest_entries=manifest_entries,
            )
            log_callback(
                "Đã xuất động theo thứ tự nguồn: "
                + _format_dynamic_export_result_vi(dynamic_result)
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
                dynamic_result = export_dynamic_source_order(
                    conn,
                    fiscal_year=fiscal_year,
                    template_path=template_path,
                    output_path=out_path,
                    cc_code=cc,
                    manifest_entries=manifest_entries,
                )
                export_succeeded = bool(dynamic_result.get("rows_written", 0))
                if export_succeeded:
                    count += 1
            
            log_callback(f"Đã xuất thành công {count} tệp vào: {output_dir}")

        report_dir = os.path.join(output_dir, "BAO_CAO_KIEM_TRA")
        os.makedirs(report_dir, exist_ok=True)
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

        conn.close()
        return True, output_dir


    except (FileNotFoundError, BadZipFile) as e:
        message = _friendly_pipeline_error_message(e)
        log_callback(f"LỖI: {message}")
        _log_debug_traceback(log_callback)
        return False, message

    except Exception as e:
        message = _friendly_pipeline_error_message(e)
        log_callback(f"LỖI: {message}")
        _log_debug_traceback(log_callback)
        return False, message

def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--fy', type=int, default=2027)
    parser.add_argument('--template', type=str, default=_default_template_path())
    parser.add_argument('--source', type=str, default=_default_source_dir())
    parser.add_argument('--headcount-source', type=str, default=None)
    parser.add_argument('--exchange-rate', type=float, default=25450.0)
    parser.add_argument('--target-cc', type=int, default=None)
    parser.add_argument(
        '--copy-baseline-t3-from-t4',
        action='store_true',
        help='Copy missing baseline T3 from T4 after the user confirms the GUI prompt.',
    )
    args = parser.parse_args(argv)

    success, message = run_universal_pipeline(
        fiscal_year=args.fy,
        template_path=args.template,
        source_dir=args.source,
        exchange_rate=args.exchange_rate,
        target_cc=args.target_cc,
        headcount_source_dir=args.headcount_source,
        copy_baseline_t3_from_t4=args.copy_baseline_t3_from_t4,
    )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
