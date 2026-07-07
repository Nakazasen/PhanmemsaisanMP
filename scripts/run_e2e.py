"""
MP2027 Manager - Universal E2E Execution Pipeline
Supports Single CC and Batch Export.

Compatibility guard: facility file-order export remains explicit via
`if facility_file_order_export:`; runtime adds workbook-existence checks.
"""
import sqlite3
import csv
import inspect
import os
import sys
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
from src.utils.source_manifest import describe_manifest

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
        print(text)
    except UnicodeEncodeError:
        print(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))


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


def _default_reference_map_path() -> str:
    return os.path.join(BASE_DIR, "docs", "config", "reference_workbook_map.csv")


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
) -> dict[str, int]:
    result = apply_complete_v1_source_order_to_workbook(
        workbook_path,
        start_row=COMPLETE_V1_SOURCE_ORDER_START_ROW,
        clear_until_row=COMPLETE_V1_SOURCE_ORDER_CLEAR_UNTIL_ROW,
        dynamic_allocation_rows=dynamic_allocation_rows,
        fiscal_periods=fiscal_periods,
    )
    log_callback(
        "Đã áp dụng ghi kết quả hoàn chỉnh theo thứ tự nguồn ({phase}): {summary}".format(
            phase=_translate_complete_v1_phase(phase),
            summary=_format_complete_v1_result_vi(result),
        )
    )
    return result


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
) -> str:
    """Resolve an explicit or mapped reference workbook for reference-assisted fill."""
    if primary_reference_path:
        resolved = os.path.abspath(primary_reference_path)
    else:
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
            raise ValueError("Điền theo tham chiếu cần --primary-reference-path hoặc bảng ánh xạ tham chiếu chính cho mã bộ phận này.")
    if not os.path.exists(resolved):
        raise FileNotFoundError(f"Không tìm thấy tệp tham chiếu chính để điền dữ liệu: {resolved}")
    return resolved


def _try_resolve_primary_reference_path(
    target_cc: int | str | None,
    primary_reference_path: str | None = None,
    reference_map_path: str | None = None,
) -> str | None:
    """Resolve an optional reference workbook for canonical export."""
    if not primary_reference_path and not reference_map_path:
        return None
    try:
        return _resolve_primary_reference_path(
            target_cc=target_cc,
            primary_reference_path=primary_reference_path,
            reference_map_path=reference_map_path,
        )
    except ValueError:
        return None


def _parse_manual_headcount(conn, source_dir: str):
    """Call the parser with packaged raw-directory support when available."""
    signature = inspect.signature(parse_manual_headcount)
    if "base_dir" in signature.parameters:
        return parse_manual_headcount(conn, source_dir=source_dir, base_dir=BASE_DIR)
    return parse_manual_headcount(conn, source_dir=source_dir)


def run_universal_pipeline(fiscal_year: int, template_path: str, source_dir: str, 
                           exchange_rate: float = 25450.0,
                           target_cc: int = None,
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
                           mp_saisan_complete_v1: bool = True):
    """
    Runs the pipeline and exports results to OUTPUT_FY[Year] folder.
    - target_cc: if None, exports all 62 CCs.
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

    try:
        log_callback(f"Quy trình năm tài chính {fiscal_year} (Tỷ giá: {exchange_rate:,.0f})")
        
        # 1. Setup Environment
        db_path = os.path.join(BASE_DIR, 'mp2027.db')
        
        # Output Directory
        output_dir = os.path.join(os.getcwd(), f"OUTPUT_FY{fiscal_year}")
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
        
        # 3. Parsers
        parser_results = {}
        manifest_lines = describe_manifest(source_dir)
        if manifest_lines:
            log_callback("Thứ tự tệp nguồn đã cấu hình:")
            for line in manifest_lines:
                log_callback(f"  {line}")

        facility_result = parse_facility(conn, source_dir=source_dir)
        parser_results["facility"] = facility_result
        fixed_assets_result = parse_fixed_assets(conn, source_dir=source_dir)
        parser_results["fixed_assets"] = fixed_assets_result
        it_result = parse_it_simulation(conn, source_dir=source_dir)
        parser_results["it_simulation"] = it_result
        ga_result = parse_ga(conn, source_dir=source_dir)
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
        parser_results["manual_headcount"] = manual_hc_result
        log_callback(
            "Nhân sự nhập tay: thêm={inserted}, bỏ qua={skipped}, lỗi={errors}, tệp={path}".format(
                inserted=manual_hc_result.get("inserted", 0),
                skipped=manual_hc_result.get("skipped", 0),
                errors=manual_hc_result.get("errors", 0),
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

        # 4. Allocation Engine
        log_callback("Đang tính phân bổ...")
        engine = AllocationEngine(conn)
        engine.run_allocation()
        
        # 5. Export Logic
        builder = HubBuilder(conn, fiscal_year=fiscal_year)
        
        facility_source_path = os.path.join(source_dir, "施設課　MPFY2027.xlsx")
        admin_source_path = os.path.join(source_dir, "総務課 FY2027 MP 振替予定.xlsx")
        allocation_source_path = os.path.join(source_dir, "FY2027配賦額一覧 (2025.12.29).xlsx")
        system_source_paths = [
            os.path.join(source_dir, "システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls"),
            os.path.join(source_dir, "システム課金金額(Simulation)_FY2027_July.2026 ~ Dec.2026(Change AMS & PLM price).xls"),
            os.path.join(source_dir, "システム課金金額(Simulation)_FY2027_Jan.2027 ~ March.2027(Change SAP price).xls"),
        ]
        if target_cc:
            # Single Export
            log_callback(f"Đang xuất riêng mã bộ phận: {target_cc}")
            out_path = os.path.join(output_dir, f"MP_CC_{target_cc}.xlsx")
            complete_v1_primary_path = None
            if mp_saisan_complete_v1:
                complete_v1_primary_path = _try_resolve_primary_reference_path(
                    target_cc=target_cc,
                    primary_reference_path=primary_reference_path,
                    reference_map_path=reference_map_path,
                )
            builder.export_to_template(template_path, out_path, cc_code=target_cc)
            complete_v1_dynamic_allocation_rows = builder._load_append_rows(str(target_cc)) if mp_saisan_complete_v1 else []
            complete_v1_fiscal_periods = get_fy_months(fiscal_year) if mp_saisan_complete_v1 else []
            output_workbook_exists = os.path.exists(out_path)
            if facility_file_order_export and output_workbook_exists and (explicit_facility_file_order_export or template_is_excel):
                apply_facility_file_order_to_workbook(
                    workbook_path=out_path,
                    facility_source_path=facility_source_path,
                    cost_center=target_cc,
                    start_row=facility_file_order_start_row,
                )
                log_callback(f"Đã áp dụng xuất Cơ sở vật chất theo thứ tự tệp: {out_path}")
            if admin_consumables_export and output_workbook_exists and (explicit_admin_consumables_export or template_is_excel):
                apply_admin_consumables_to_workbook(
                    workbook_path=out_path,
                    admin_source_path=admin_source_path,
                    allocation_source_path=allocation_source_path,
                    cost_center=target_cc,
                    start_row=admin_consumables_start_row,
                )
                log_callback(f"Đã áp dụng xuất vật tư Tổng vụ: {out_path}")
            if system_cost_export and output_workbook_exists and (explicit_system_cost_export or template_is_excel):
                apply_system_cost_to_workbook(
                    workbook_path=out_path,
                    system_source_paths=system_source_paths,
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
                _apply_complete_v1_source_order(out_path, log_callback, phase="pre-reference")
            if primary_reference_fill:
                primary_path = _resolve_primary_reference_path(
                    target_cc=target_cc,
                    primary_reference_path=primary_reference_path,
                    reference_map_path=reference_map_path,
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
                )
            log_callback(f"Hoàn tất: {output_dir}")
        else:
            # Batch Export
            log_callback("Đang xuất hàng loạt...")
            cursor.execute("SELECT DISTINCT cc_code FROM fact_input_data WHERE account_code > 0")
            all_ccs = [row[0] for row in cursor.fetchall()]
            
            count = 0
            for cc in all_ccs:
                out_path = os.path.join(output_dir, f"MP_CC_{cc}.xlsx")
                if builder.export_to_template(template_path, out_path, cc_code=cc):
                    if facility_file_order_export:
                        apply_facility_file_order_to_workbook(
                            workbook_path=out_path,
                            facility_source_path=facility_source_path,
                            cost_center=cc,
                            start_row=facility_file_order_start_row,
                        )
                        log_callback(f"Đã áp dụng xuất Cơ sở vật chất theo thứ tự tệp: {out_path}")
                    if admin_consumables_export:
                        apply_admin_consumables_to_workbook(
                            workbook_path=out_path,
                            admin_source_path=admin_source_path,
                            allocation_source_path=allocation_source_path,
                            cost_center=cc,
                            start_row=admin_consumables_start_row,
                        )
                        log_callback(f"Đã áp dụng xuất vật tư Tổng vụ: {out_path}")
                    if system_cost_export:
                        apply_system_cost_to_workbook(
                            workbook_path=out_path,
                            system_source_paths=system_source_paths,
                            cost_center=cc,
                            start_row=system_cost_start_row,
                        )
                        log_callback(f"Đã áp dụng xuất chi phí hệ thống: {out_path}")
                    if primary_reference_fill:
                        primary_path = _resolve_primary_reference_path(
                            target_cc=cc,
                            primary_reference_path=primary_reference_path,
                            reference_map_path=reference_map_path,
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
                        complete_v1_primary_path = _try_resolve_primary_reference_path(
                            target_cc=cc,
                            primary_reference_path=primary_reference_path,
                            reference_map_path=reference_map_path,
                        )
                        if complete_v1_primary_path:
                            _apply_complete_v1_source_order(out_path, log_callback, phase="pre-reference")
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
                        _apply_complete_v1_source_order(out_path, log_callback, phase="final")
                    count += 1
            
            log_callback(f"Đã xuất thành công {count} tệp vào: {output_dir}")

        audit_result = write_pipeline_audit_report(
            conn=conn,
            output_dir=output_dir,
            source_dir=source_dir,
            fiscal_year=fiscal_year,
            target_cc=target_cc,
            parser_results=parser_results,
        )
        log_callback(f"Báo cáo kiểm tra: {audit_result['report_path']}")
        log_callback(f"Tệp dữ liệu thiếu: {audit_result['missing_csv_path']}")

        if facility_file_order_preview:
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
        
        conn.close()
        return True, output_dir


    except (FileNotFoundError, BadZipFile) as e:
        message = f"Không tìm thấy hoặc tệp mẫu/nguồn không hợp lệ: {e}"
        log_callback(f"LỖI: {message}")
        log_callback(traceback.format_exc())
        return False, message

    except Exception as e:
        log_callback(f"LỖI: {str(e)}")
        log_callback(traceback.format_exc())
        return False, str(e)

def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--fy', type=int, default=2027)
    parser.add_argument('--template', type=str, default=_default_template_path())
    parser.add_argument('--source', type=str, default=_default_source_dir())
    parser.add_argument('--exchange-rate', type=float, default=25450.0)
    parser.add_argument('--target-cc', type=int, default=None)
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
        '--legacy-export',
        action='store_true',
        help='Use legacy fixed-row export instead of canonical complete-v1 source-order export.',
    )
    parser.add_argument(
        '--mp-saisan-complete-v1',
        action='store_true',
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)

    success, message = run_universal_pipeline(
        fiscal_year=args.fy,
        template_path=args.template,
        source_dir=args.source,
        exchange_rate=args.exchange_rate,
        target_cc=args.target_cc,
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
        fixed_assets_reference_skeleton_export=args.fixed_assets_reference_skeleton_export,
        fixed_assets_skeleton_csv=args.fixed_assets_skeleton_csv,
        fixed_assets_skeleton_start_row=args.fixed_assets_skeleton_start_row,
        mp_saisan_complete_v1=not args.legacy_export,
    )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
