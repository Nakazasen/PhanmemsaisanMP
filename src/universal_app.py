"""
MP2027 Manager - ứng dụng giao diện chính.
"""

import csv
import hashlib
import os
import queue
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, scrolledtext, ttk

import openpyxl


def _default_fiscal_year(today: datetime | None = None) -> int:
    """Company FY ends in March: Apr-Dec belongs to the following FY."""
    current = today or datetime.now()
    return current.year + 1 if current.month >= 4 else current.year

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)


def _copy_missing_tree(source_dir: str, target_dir: str) -> None:
    if not os.path.isdir(source_dir):
        return
    os.makedirs(target_dir, exist_ok=True)
    for root, _dirs, files in os.walk(source_dir):
        relative_dir = os.path.relpath(root, source_dir)
        target_root = target_dir if relative_dir == "." else os.path.join(target_dir, relative_dir)
        os.makedirs(target_root, exist_ok=True)
        for filename in files:
            if filename.startswith("~$"):
                continue
            source_file = os.path.join(root, filename)
            target_file = os.path.join(target_root, filename)
            if not os.path.exists(target_file):
                shutil.copy2(source_file, target_file)


def _ensure_external_runtime_data() -> None:
    """Make bundled data editable next to the exe; _internal is fallback only."""
    if not getattr(sys, "frozen", False):
        return
    packaged_docs = resource_path(os.path.join("docs", "MP2027"))
    packaged_raw = resource_path("raw")
    external_docs = os.path.join(BASE_DIR, "docs", "MP2027")
    external_raw = os.path.join(BASE_DIR, "raw")
    _copy_missing_tree(packaged_docs, external_docs)
    _copy_missing_tree(packaged_raw, external_raw)


# Bundled data remains read-only package material. Business data is loaded only
# through the selected project.json; never copy it beside the executable at startup.

from src.db.loader import load_all, load_cost_centers
from src.db.schema import create_schema, get_connection
from src.services.headcount_source_importer import (
    cleanup_headcount_truth,
    count_headcount_truth_rows,
    import_headcount_time_sources,
    review_headcount_time_sources,
)
from src.services.manual_staffing_overrides import (
    copy_missing_baselines_from_april,
    find_missing_baseline_ccs,
    save_manual_baseline_override,
    save_manual_time_overrides,
)
from src.services.fiscal_run import annual_default_paths, create_fiscal_run_context, preflight_fiscal_run
from src.services.preflight_cache import cached_preflight_fiscal_run, get_cached_preflight
from src.services.project_config import (
    ProjectConfig,
    discover_or_create_project,
    remember_last_project,
)
from src.services.run_history import filter_runs
from src.parsers.manual_event_drivers import TEMPLATE_COLUMNS, ensure_manual_event_drivers_template
from src.parsers.manual_headcount import (
    BUS_DRIVER_COLUMNS,
    ensure_manual_bus_headcount_template,
    ensure_manual_headcount_template,
    get_required_headcount_periods,
    parse_manual_headcount,
    resolve_manual_headcount_source_dir,
    validate_manual_headcount_rows,
)
from src.utils.excel_helpers import (
    find_hub_sheet_name,
    get_fy_months,
    read_exchange_rate_from_form,
    validate_exchange_rate,
)
from src.utils.fiscal_periods import fiscal_month_labels
from src.utils.source_manifest import (
    CATEGORY_DISPLAY_NAMES,
    DEFAULT_DESCRIPTIONS,
    MANIFEST_COLUMNS,
    read_source_manifest_inventory_fast,
    write_source_manifest_xlsx,
)


def _headcount_save_error(period: str, field: str, raw_value: str, validation_rule: str, reason: str) -> dict:
    return {
        "period": period,
        "field": field,
        "raw_value": raw_value,
        "validation_rule": validation_rule,
        "reason": reason,
        "csv_row_written": False,
        "db_row_inserted": False,
    }


def _parse_blank_zero_save_int(period: str, field: str, raw_value: str, label: str) -> tuple[str | None, dict | None]:
    text = str(raw_value or "").strip()
    if text == "":
        return "0", None
    if not text.isdecimal():
        return None, _headcount_save_error(period, field, text, "INTEGER_GTE_0", f"{label.capitalize()} must be an integer >= 0")
    return str(int(text)), None


def _parse_optional_save_int(period: str, field: str, raw_value: str, label: str) -> tuple[str, dict | None]:
    text = str(raw_value or "").strip()
    if text == "":
        return "", None
    if not text.isdecimal():
        return "", _headcount_save_error(period, field, text, "INTEGER_GTE_0", f"{label.capitalize()} must be an integer >= 0")
    return str(int(text)), None


def validate_headcount_save_period_rows(periods, month_values, label_by_period=None):
    """Validate GUI headcount inputs for an atomic full-series save."""
    label_by_period = label_by_period or {}
    rows = []
    errors = []
    for period in periods:
        values = month_values.get(period, {})
        label = label_by_period.get(period, period)
        row_error_count = len(errors)

        staff, staff_error = _parse_blank_zero_save_int(
            period,
            "headcount_staff",
            values.get("staff", ""),
            f"staff at {label}",
        )
        worker, worker_error = _parse_blank_zero_save_int(
            period,
            "headcount_worker",
            values.get("worker", ""),
            f"worker at {label}",
        )
        if staff_error:
            errors.append(staff_error)
        if worker_error:
            errors.append(worker_error)

        male = ""
        female = ""
        if str(period).endswith("12"):
            male, male_error = _parse_optional_save_int(
                period,
                "headcount_male",
                values.get("male", ""),
                f"male headcount at {label}",
            )
            female, female_error = _parse_optional_save_int(
                period,
                "headcount_female",
                values.get("female", ""),
                f"female headcount at {label}",
            )
            if male_error:
                errors.append(male_error)
            if female_error:
                errors.append(female_error)

        if len(errors) != row_error_count:
            continue

        staff_int = int(staff or "0")
        worker_int = int(worker or "0")
        male_int = int(male or "0")
        female_int = int(female or "0")
        if male_int + female_int > staff_int + worker_int:
            errors.append(
                _headcount_save_error(
                    period,
                    "headcount_male/headcount_female",
                    f"{values.get('male', '')}/{values.get('female', '')}",
                    "SUM_LE_TOTAL",
                    f"Male + female exceeds staff + worker at {label}",
                )
            )
            continue

        rows.append(
            {
                "period": period,
                "headcount_staff": staff,
                "headcount_worker": worker,
                "headcount_male": male,
                "headcount_female": female,
                "description": str(values.get("description", "") or "").strip(),
            }
        )
    return rows, errors


def format_headcount_save_errors(errors) -> str:
    lines = []
    for error in errors:
        period = str(error.get("period", "") or "-")
        field = str(error.get("field", "") or "-")
        raw_value = str(error.get("raw_value", ""))
        raw_display = "trống" if raw_value == "" else raw_value
        rule = str(error.get("validation_rule", "") or "-")
        reason = str(error.get("reason", "") or "-")
        csv_written = error.get("csv_row_written", False)
        db_inserted = error.get("db_row_inserted", False)
        lines.append(
            f"{period} | {field} | {raw_display} | {rule} | {reason} | đã ghi tệp dữ liệu={csv_written} | đã nạp vào dữ liệu={db_inserted}"
        )
    return "\n".join(lines)


def validate_bus_headcount_save_rows(rows, valid_cc_codes) -> list[dict]:
    errors = []
    seen_cc = set()
    for row_number, row in enumerate(rows, start=2):
        cc_code = str(row.get("cc_code", "") or "").strip()
        expat_count = str(row.get("bus_expat_count", "") or "").strip()
        vietnamese_count = str(row.get("bus_vietnamese_count", "") or "").strip()
        description = str(row.get("description", "") or "").strip()
        if not any([cc_code, expat_count, vietnamese_count, description]):
            continue
        if not cc_code or cc_code not in valid_cc_codes:
            error = _headcount_save_error("bus", "cc_code", cc_code, "VALID_CC", "Bus driver cost center is invalid")
            error["csv_row"] = row_number
            errors.append(error)
            continue
        if cc_code in seen_cc:
            error = _headcount_save_error("bus", "cc_code", cc_code, "UNIQUE_CC", "Duplicate bus driver cost center")
            error["csv_row"] = row_number
            errors.append(error)
            continue
        if not expat_count.isdecimal():
            error = _headcount_save_error(
                "bus",
                "bus_expat_count",
                expat_count,
                "INTEGER_GTE_0",
                "Bus expat count must be an integer >= 0",
            )
            error["csv_row"] = row_number
            errors.append(error)
            continue
        if not vietnamese_count.isdecimal():
            error = _headcount_save_error(
                "bus",
                "bus_vietnamese_count",
                vietnamese_count,
                "INTEGER_GTE_0",
                "Bus Vietnamese count must be an integer >= 0",
            )
            error["csv_row"] = row_number
            errors.append(error)
            continue
        seen_cc.add(cc_code)
    return errors


def _annual_template_path(fiscal_year: int) -> str:
    return os.path.join(BASE_DIR, "docs", f"MP{int(fiscal_year)}", "FORM.xlsx")


def _annual_source_dir(fiscal_year: int) -> str:
    return os.path.join(BASE_DIR, "docs", f"MP{int(fiscal_year)}")


def _annual_headcount_source_dir(fiscal_year: int) -> str:
    annual_dir = os.path.join(BASE_DIR, "raw", f"FY{int(fiscal_year)}")
    if int(fiscal_year) == 2027:
        has_workbook = os.path.isdir(annual_dir) and any(
            name.lower().endswith((".xls", ".xlsx", ".xlsm"))
            for name in os.listdir(annual_dir)
        )
        if not has_workbook:
            return os.path.join(BASE_DIR, "raw")
    return annual_dir


def _annual_manual_input_store(fiscal_year: int) -> str:
    """Editable staffing overrides are isolated by FY, never shared mp2027.db."""
    path = annual_default_paths(int(fiscal_year), BASE_DIR)["manual_input_store"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def _default_template_path(fiscal_year: int = 2027) -> str:
    external_template = _annual_template_path(fiscal_year)
    if os.path.exists(external_template):
        return external_template
    if int(fiscal_year) == 2027:
        packaged_template = resource_path(os.path.join("docs", "MP2027", "FORM.xlsx"))
        if os.path.exists(packaged_template):
            return packaged_template
    return external_template


FORM_SYSTEM_ACCOUNT_CODES = {5005246282, 6005146628, 6005146542}


def _external_template_path(fiscal_year: int = 2027) -> str:
    return _annual_template_path(fiscal_year)


def _external_source_dir(fiscal_year: int = 2027) -> str:
    return _annual_source_dir(fiscal_year)


def _is_under_internal(path: str) -> bool:
    if not path:
        return False
    try:
        absolute_path = os.path.abspath(path)
        internal_dir = os.path.abspath(os.path.join(BASE_DIR, "_internal"))
        return os.path.commonpath([absolute_path, internal_dir]) == internal_dir
    except (OSError, ValueError):
        return False


def _validate_selected_template(path: str, fiscal_year: int = 2027) -> str | None:
    external_template = _external_template_path(fiscal_year)
    if not os.path.isfile(path):
        return "Không tìm thấy tệp mẫu FORM.\n\n" + f"Hãy chọn tệp: {external_template}"
    if _is_legacy_root_template(path):
        return "Không được dùng FORM.xlsx ở thư mục gốc vì tệp này còn công thức mẫu cũ.\n\n" + f"Hãy chọn tệp FORM mới nhất: {external_template}"
    if _is_under_internal(path) and os.path.exists(external_template):
        return "Đường dẫn tệp mẫu đang trỏ vào thư mục _internal của chương trình.\n\nNgười dùng không cần và không nên quản lý dữ liệu trong _internal.\n" + f"Hãy chọn tệp FORM bên ngoài: {external_template}"
    try:
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=False)
    except Exception:
        return "Không mở được tệp FORM. Tệp có thể không phải Excel .xlsx hợp lệ hoặc đang bị hỏng.\n\n" + f"Hãy dùng tệp FORM mới nhất: {external_template}"
    try:
        try:
            sheet_name = find_hub_sheet_name(workbook)
        except Exception:
            return "Tệp FORM không có sheet chi tiết MP đúng định dạng.\n\n" + f"Hãy dùng tệp FORM mới nhất: {external_template}"

    finally:
        workbook.close()
    return None

def _validate_selected_source_dir(path: str, fiscal_year: int = 2027) -> str | None:
    external_source = _external_source_dir(fiscal_year)
    if not os.path.isdir(path):
        return (
            "Không tìm thấy thư mục nguồn.\n\n"
            f"Hãy chọn thư mục chứa dữ liệu nguồn, ví dụ: {external_source}"
        )
    if _is_under_internal(path) and os.path.isdir(external_source):
        return (
            "Thư mục nguồn đang trỏ vào _internal của chương trình.\n\n"
            "Đây là thư mục đóng gói nội bộ, không phải nơi người dùng quản lý dữ liệu.\n"
            f"Hãy chọn thư mục bên ngoài cạnh file chạy: {external_source}"
        )
    return None


def _is_missing_baseline_error(error) -> bool:
    """Return True for both current preflight and legacy baseline error formats."""
    text = str(error or "").lower()
    return (
        "chưa có tổng số người tháng" in text
        or ("thiếu dữ liệu nhân sự/thời gian bắt buộc" in text and "baseline t3" in text)
    )


def _pipeline_failure_summary(output_lines: list[str], return_code: int) -> str:
    """Keep full subprocess output in the log while returning its final error block."""
    error_start = None
    for index in range(len(output_lines) - 1, -1, -1):
        if output_lines[index].strip().startswith("LỖI:"):
            error_start = index
            break
    if error_start is not None:
        error_lines = [
            line.strip()
            for line in output_lines[error_start:]
            if line.strip() and "chi tiết kỹ thuật đã được ẩn" not in line.lower()
        ]
        if error_lines:
            error_lines[0] = error_lines[0].removeprefix("LỖI:").strip()
            return "\n".join(error_lines)
    for line in reversed(output_lines):
        text = line.strip()
        if text and "chi tiết kỹ thuật đã được ẩn" not in text.lower():
            return text
    return f"Pipeline exited with code {return_code}"


def _failed_run_database_from_output(
    output_lines: list[str], history_root: str, fiscal_year: int
) -> str | None:
    """Resolve the exact immutable run DB named by the subprocess traceback."""
    marker = "Chi tiết lỗi đã lưu:"
    expected_root = os.path.realpath(os.path.join(history_root, f"FY{int(fiscal_year)}"))
    for line in reversed(output_lines):
        if marker not in line:
            continue
        trace_path = line.split(marker, 1)[1].strip()
        candidate = os.path.realpath(
            os.path.join(os.path.dirname(os.path.dirname(trace_path)), "run.db")
        )
        try:
            inside_expected_root = os.path.commonpath([expected_root, candidate]) == expected_root
        except ValueError:
            inside_expected_root = False
        if inside_expected_root and os.path.isfile(candidate):
            return candidate
    return None


def _friendly_error_message(error) -> str:
    text = str(error or "").strip()
    lower_text = text.lower()
    external_template = _external_template_path()
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

    if "chưa có tổng số người tháng" in lower_text:
        issue_lines = [
            line[2:].strip()
            for line in text.splitlines()
            if line.strip().startswith("- ") and "chưa có Tổng số người tháng" in line
        ]
        details = "\n".join(f"• {line}" for line in issue_lines)
        if not details:
            details = text
        return (
            "Thiếu dữ liệu nhân sự để xuất báo cáo.\n\n"
            f"{details}\n\n"
            "Cách xử lý:\n"
            "1. Đóng thông báo này.\n"
            "2. Chọn “Nhập nhân sự thủ công”.\n"
            "3. Nhập Tổng số người của tháng được thông báo cho đúng phòng.\n"
            "4. Lưu dữ liệu rồi bấm “CHẠY TÍNH TOÁN” lại."
        )

    if "unable to locate system cost row" in lower_text or "không tìm thấy dòng system cost" in lower_text:
        return (
            "Không tìm thấy dòng System Cost trong tệp FORM.\n\n"
            "Nguyên nhân thường gặp: đang dùng FORM.xlsx cũ hoặc FORM không đúng phiên bản.\n"
            f"Cách xử lý: chọn lại tệp FORM mới nhất tại {external_template}."
        )
    if "unable to resolve kdc system cost account" in lower_text or "không xác định được tài khoản system cost" in lower_text:
        return (
            "Không xác định được tài khoản System Cost cho một mã bộ phận.\n\n"
            "Cách xử lý: kiểm tra mã bộ phận trong dữ liệu nguồn và kiểm tra loại chi phí của mã đó trong master CC."
        )
    if "form template not found" in lower_text:
        return (
            "Không tìm thấy tệp mẫu FORM.\n\n"
            f"Cách xử lý: chọn lại tệp FORM mới nhất tại {external_template}."
        )
    if "missing the mp detail sheet" in lower_text or "không có sheet chi tiết mp" in lower_text:
        return (
            "Tệp FORM không có sheet chi tiết MP đúng định dạng.\n\n"
            f"Cách xử lý: dùng lại tệp FORM mới nhất tại {external_template}."
        )
    if "malformed or empty" in lower_text:
        return (
            "Tệp FORM sai định dạng hoặc rỗng.\n\n"
            f"Cách xử lý: thay bằng tệp FORM mới nhất tại {external_template}."
        )
    if "append rows prepared" in lower_text or "dòng trống để ghi thêm" in lower_text:
        return (
            "Tệp FORM không còn đủ dòng trống để ghi các chi phí phát sinh thêm.\n\n"
            "Cách xử lý: dùng FORM mới nhất hoặc chuẩn bị thêm vùng dòng trống trong sheet chi tiết MP."
        )
    if "not found" in lower_text or "no such file" in lower_text:
        return (
            "Không tìm thấy tệp hoặc thư mục cần dùng.\n\n"
            "Cách xử lý: kiểm tra lại đường dẫn Tệp mẫu FORM và Thư mục nguồn trên màn hình chính."
        )
    if text and any(marker in lower_text for marker in vietnamese_markers):
        return text
    return (
        "Đã xảy ra lỗi khi chạy chương trình.\n\n"
        "Cách xử lý: kiểm tra lại Tệp mẫu FORM, Thư mục nguồn và chạy lại. "
        "Nếu lỗi vẫn lặp lại, bật MP2027_DEBUG_TRACEBACK=1 để lấy chi tiết kỹ thuật."
    )


def _is_legacy_root_template(path: str) -> bool:
    selected_path = os.path.abspath(path)
    root_form = os.path.abspath(os.path.join(BASE_DIR, "FORM.xlsx"))
    if selected_path != root_form:
        return False

    canonical_candidates = [
        os.path.abspath(os.path.join(BASE_DIR, "docs", "MP2027", "FORM.xlsx")),
        os.path.abspath(resource_path(os.path.join("docs", "MP2027", "FORM.xlsx"))),
    ]
    canonical_form = next((candidate for candidate in canonical_candidates if os.path.exists(candidate)), None)
    if not os.path.exists(root_form):
        return True
    if canonical_form is None:
        return False

    def _sha256(file_path: str) -> str:
        digest = hashlib.sha256()
        with open(file_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    return _sha256(root_form) != _sha256(canonical_form)


def _default_source_dir(fiscal_year: int = 2027) -> str:
    external_source = _annual_source_dir(fiscal_year)
    if os.path.isdir(external_source) or int(fiscal_year) != 2027:
        return external_source
    packaged_source = resource_path(os.path.join("docs", "MP2027"))
    return packaged_source if os.path.isdir(packaged_source) else external_source

USER_GUIDE_TEXT = """
HƯỚNG DẪN SỬ DỤNG CHI TIẾT - MP2027 MANAGER

1. MỤC ĐÍCH
- Ứng dụng dùng để nạp dữ liệu nguồn, tính toán ngân sách MP và xuất tệp Excel theo từng CC.
- Chương trình giúp giảm nhập tay, nhưng không tự bịa số. Khoản nào thiếu dữ liệu thật sẽ được báo để người dùng nhập/chốt.

2. CÁC TRƯỜNG TRÊN MÀN HÌNH CHÍNH
- Năm tài chính:
  Nhập năm cần chạy, ví dụ 2027.
- Trung tâm chi phí:
  Để trống nếu muốn xuất toàn bộ.
  Chọn 1 dòng trong danh sách nếu chỉ muốn chạy cho một CC.
- Tệp mẫu:
  Đường dẫn đến FORM của năm đang chọn: docs/MP<YYYY>/FORM.xlsx.
- Thư mục nguồn:
  Thư mục chứa các tệp Excel nguồn và các tệp nhập tay.

3. QUY TRÌNH CHẠY ĐỀ XUẤT
Bước 1: Chọn năm tài chính cần lập.
Bước 2: Kiểm tra tệp mẫu là docs/MP<YYYY>/FORM.xlsx, không dùng FORM_old.xlsx.
Bước 3: Chọn đúng thư mục nguồn docs/MP<YYYY> và raw/FY<YYYY>.
Bước 4: Chờ trạng thái “Đúng năm và đủ nguồn”; chỉ khi đó nút chạy mới được bật.
Bước 4: Nếu cần, nhập bổ sung nhân sự bằng nút "Nhập nhân sự thủ công".
Bước 5: Nếu có khoản chương trình không thể tự biết, bấm "Nhập sự kiện thiếu dữ liệu".
Bước 6: Nếu chạy riêng, chọn 1 Trung tâm chi phí. Nếu không, để trống.
Bước 7: Bấm "CHẠY TÍNH TOÁN".
Bước 8: Xem Nhật ký xử lý và mở báo cáo lần chạy khi cần kiểm tra chi tiết.

4. VÌ SAO CÓ NÚT "NHẬP SỰ KIỆN THIẾU DỮ LIỆU"
Có những khoản chỉ người làm nghiệp vụ biết số thật, ví dụ:
- Có bao nhiêu người đi xe bus JP/VN.
- Có ai nhận quà vì không đi du lịch hay không.
- Có chi phí My Episode, kỷ niệm 10 năm, kỷ niệm công ty hay không.
- VISA/Passport/GPLD/NNN có phải ghi vào dòng khác dòng 137 hay không.

Nếu chương trình tự đoán các số này thì ngân sách công ty có thể sai. Vì vậy chương trình bắt buộc hỏi người dùng nhập/chốt.

Cách điền rất đơn giản:
Bước 1: Chọn CC.
Bước 2: Chọn tháng phát sinh.
Bước 3: Chọn loại sự kiện.
Bước 4: Nếu biết "số người" và "đơn giá", điền 2 ô đó. Chương trình sẽ tạo công thức số người nhân đơn giá.
Bước 5: Nếu chỉ biết tổng tiền cuối cùng, điền "số tiền trực tiếp".
Bước 6: Điền mã tài khoản. Nếu biết dòng FORM cần ghi, điền thêm dòng FORM. Nếu không chắc, hãy để ghi chú để kiểm toán lại.
Bước 7: Bấm "Thêm/Cập nhật", rồi bấm "Lưu tệp".

5. HƯỚNG DẪN NHẬP NHÂN SỰ THỦ CÔNG
- Bấm nút "Nhập nhân sự thủ công".
- Chọn mã CC trong danh sách.
- Chọn kỳ tháng trong năm tài chính.
- Nhập số nhân viên và công nhân.
- Nếu cần tính khám sức khỏe dòng 57/58, nhập thêm Nam/Nữ tháng 12.
- Nếu cần, thêm mô tả để ghi chú nguồn điều chỉnh.
- Bấm "Lưu 12 tháng" để ghi xuống tệp.

6. CÁCH ĐỌC DASHBOARD KIỂM TOÁN
- XANH: CC đã có dữ liệu nền tảng và chưa có cảnh báo cơ bản.
- VÀNG: CC có dữ liệu nhưng còn điều cần người dùng xem/chốt.
- ĐỎ: CC chưa có dữ liệu tính toán sau lần chạy gần nhất.

Khi thấy VÀNG hoặc ĐỎ:
Bước 1: Bấm chọn dòng CC đó.
Bước 2: Đọc cột "Lý do".
Bước 3: Xem bảng "Việc cần người dùng chốt".
Bước 4: Nếu thiếu sự kiện, bấm "Nhập dữ liệu thiếu".
Bước 5: Mở tệp kết quả CC để đối chiếu công thức.

7. LỖI THƯỜNG GẶP
- Lỗi không tìm thấy tệp mẫu: kiểm tra lại đường dẫn FORM.xlsx.
- Báo cáo lần chạy còn cảnh báo: đây không phải lỗi. Nghĩa là có dữ liệu cần người dùng xác nhận trước khi tin kết quả.
- Nhập xong nhưng chưa áp dụng: kiểm tra đã bấm "Lưu tệp" hoặc "Lưu 12 tháng" trước khi chạy tính toán.

8. KHUYẾN NGHỊ VẬN HÀNH
- Chạy thử với 1 CC trước khi xuất hàng loạt.
- Sau khi chạy, luôn mở Dashboard kiểm toán trước khi gửi tệp cho người khác.
- Không nhập số ước lượng nếu chưa chắc. Hãy để trống và ghi chú để kiểm toán lại.
""".strip()

USER_GUIDE_TEXT_LATEST = """
HƯỚNG DẪN SỬ DỤNG CHƯƠNG TRÌNH LẬP NGÂN SÁCH

1. CHƯƠNG TRÌNH DÙNG ĐỂ LÀM GÌ?

Chương trình tổng hợp dữ liệu chi phí, nhân sự và thời gian làm việc để lập tệp ngân sách cho từng Trung tâm chi phí.

Chương trình thực hiện các việc chính:
- Đọc dữ liệu chi phí từ thư mục nguồn chi phí.
- Nạp số người, thời gian cố định và thời gian tăng ca từ các tệp kế hoạch của phòng ban.
- Cho phép nhập các thông tin không có trong tệp nguồn, như số người đi xe buýt, số Nam/Nữ tháng 12 và các khoản phát sinh đặc biệt.
- Tính toán chi phí và xuất một tệp kết quả cho từng Trung tâm chi phí.

2. Ý NGHĨA CÁC MỤC TRÊN MÀN HÌNH CHÍNH

Năm tài chính:
- Nhập năm cần lập ngân sách. Chương trình tự tạo 12 kỳ từ tháng 4 đến tháng 3 và chỉ chấp nhận nguồn cùng năm.
- Năm tài chính bắt đầu từ tháng 4 và kết thúc vào tháng 3 năm sau.
- Khi thay đổi năm, tiêu đề chương trình và dữ liệu được sử dụng cũng thay đổi theo.

Tỷ giá (USD/VND):
- Là tỷ giá dùng cho lần tính hiện tại.
- Chương trình đọc tỷ giá ban đầu từ tệp mẫu. Có thể sửa trước khi chạy nếu nghiệp vụ yêu cầu.

Trung tâm chi phí (Tùy chọn):
- Để trống nếu muốn chạy tất cả Trung tâm chi phí có dữ liệu.
- Chọn một mã nếu chỉ muốn kiểm tra hoặc xuất kết quả cho một phòng.

Tệp mẫu FORM:
- Là tệp Excel mẫu dùng để tạo tệp kết quả.
- Nhấn "Chọn..." nếu cần đổi tệp.
- Chương trình ghi nhớ tệp đã chọn cho lần mở sau.

Thư mục nguồn chi phí:
- Là thư mục chứa các tệp phục vụ tính chi phí và phân bổ ngân sách.
- Nhấn "Chọn..." nếu cần đổi thư mục.
- Chương trình ghi nhớ thư mục đã chọn cho lần mở sau.

Nguồn nhân sự & thời gian:
- Là thư mục chứa các tệp kế hoạch nhân sự và thời gian do các phòng ban nộp.
- Chương trình chỉ nạp tệp đúng năm tài chính đang chọn.
- Nhấn "Cập nhật CSDL" để quét thư mục và nạp dữ liệu vào cơ sở dữ liệu.
- Dòng trạng thái bên dưới cho biết số phòng và số kỳ đã nạp.
- Chương trình ghi nhớ thư mục đã chọn cho lần mở sau.

3. TRÌNH TỰ SỬ DỤNG KHUYẾN NGHỊ

Bước 1: Chọn đúng Năm tài chính.
Bước 2: Kiểm tra Tệp mẫu FORM.
Bước 3: Kiểm tra Thư mục nguồn chi phí.
Bước 4: Chọn thư mục Nguồn nhân sự & thời gian.
Bước 5: Nhấn "Cập nhật CSDL" và đọc Nhật ký xử lý.
Bước 6: Nhấn "Nhập nhân sự thủ công" để kiểm tra số người, thời gian và nhập các phần bổ sung.
Bước 7: Nhấn "Nhập sự kiện thiếu dữ liệu" nếu có khoản phát sinh chương trình không thể tự xác định.
Bước 8: Chọn một Trung tâm chi phí để chạy thử; để trống khi muốn chạy tất cả.
Bước 9: Nhấn "CHẠY TÍNH TOÁN".
Bước 10: Đọc Nhật ký xử lý và mở tệp kết quả để đối chiếu.

4. CẬP NHẬT NGUỒN NHÂN SỰ VÀ THỜI GIAN

Trước khi cập nhật:
- Chọn đúng Năm tài chính.
- Chọn đúng thư mục chứa các tệp kế hoạch của năm đó.

Khi nhấn "Cập nhật CSDL", chương trình sẽ:
- Tìm các tệp kế hoạch nhân sự và thời gian đúng năm tài chính.
- Đọc mã Trung tâm chi phí và tên phòng.
- Đối chiếu với danh mục Trung tâm chi phí hiện hành.
- Nạp 12 tháng, từ tháng 4 đến tháng 3, cho từng phòng hợp lệ.
- Ghi lý do vào Nhật ký nếu có tệp không được nạp.

Ví dụ:
- Chọn năm 2027: chương trình nhận dữ liệu kỳ 202604 đến 202703.
- Với FY khác, chương trình đổi kỳ tháng theo lịch (ví dụ FY2029 là 202804 đến 202903), nhưng không tự đổi tên hoặc tạo source workbook FY2029. Người dùng phải cung cấp và kiểm tra đủ nguồn đúng năm.

5. KIỂM TRA VÀ BỔ SUNG NHÂN SỰ

Nhấn "Nhập nhân sự thủ công", sau đó chọn mã Trung tâm chi phí.

Thẻ "Số người & bổ sung":
- JP: số người biệt phái.
- Nhân viên: số nhân viên người Việt.
- Công nhân: số công nhân người Việt.
- Nam (T12), Nữ (T12): chỉ nhập tại tháng 12 khi cần tính các khoản liên quan.
- Tổng người: chương trình tự tính bằng JP + Nhân viên + Công nhân.
- Ghi chú: dùng để giải thích dữ liệu bổ sung hoặc điều chỉnh.

Thẻ "Thời gian cố định":
- Hiển thị giờ cố định của JP và người Việt theo từng tháng.
- Dữ liệu lấy từ nguồn nhân sự và thời gian đã nạp vào cơ sở dữ liệu.

Thẻ "Thời gian tăng ca":
- Hiển thị giờ tăng ca của JP và người Việt theo từng tháng.
- Dữ liệu lấy từ nguồn nhân sự và thời gian đã nạp vào cơ sở dữ liệu.

Thông tin xe buýt:
- Nhập riêng số người biệt phái đi xe buýt.
- Nhập riêng số người Việt Nam đi xe buýt.
- Các số này không có trong tệp nguồn nên người dùng phải nhập và xác nhận.

Lưu ý quan trọng:
- Cửa sổ chỉ hiển thị dữ liệu thuộc Năm tài chính đang chọn trên màn hình chính.
- Nếu năm đang chọn chưa có dữ liệu, các bảng thời gian sẽ để trống và chương trình báo chưa có dữ liệu nguồn cho năm đó.
- Sau khi nhập bổ sung, nhấn "Lưu 12 tháng".

6. DỮ LIỆU ĐƯỢC GHI VÀO TỆP KẾT QUẢ NHƯ THẾ NÀO?

Khi xuất kết quả, chương trình ghi dữ liệu từ tháng 4 đến tháng 3 vào các cột F đến Q của tệp FORM:
- Dòng 8: thời gian cố định của JP.
- Dòng 9: thời gian cố định của người Việt.
- Dòng 16: thời gian tăng ca của JP.
- Dòng 17: thời gian tăng ca của người Việt.
- Dòng 24: số người JP.
- Dòng 25: tổng số người Việt, bằng Nhân viên + Công nhân.

Ví dụ:
- Tháng 4 được ghi vào cột F.
- Tháng 3 được ghi vào cột Q.

Chương trình chỉ xuất khi Trung tâm chi phí có đủ dữ liệu nguồn của 12 tháng trong năm tài chính đã chọn. Nếu thiếu, chương trình dừng xuất Trung tâm chi phí đó và thông báo rõ các kỳ còn thiếu. Quy tắc này ngăn việc dùng nhầm dữ liệu của năm cũ.

7. NHẬP CÁC KHOẢN PHÁT SINH CÒN THIẾU

Nhấn "Nhập sự kiện thiếu dữ liệu" khi có khoản chỉ người làm nghiệp vụ mới biết, chẳng hạn:
- Quà cho người không tham gia du lịch.
- Khoản kỷ niệm hoặc sự kiện đặc biệt.
- Chi phí hộ chiếu, thị thực, giấy phép lao động hoặc nghiệp vụ người nước ngoài cần tách riêng.

Cách thực hiện:
Bước 1: Chọn Trung tâm chi phí.
Bước 2: Chọn kỳ phát sinh.
Bước 3: Chọn loại sự kiện.
Bước 4: Nhập số lượng và đơn giá nếu biết từng thành phần.
Bước 5: Nếu chỉ biết tổng tiền, nhập số tiền trực tiếp.
Bước 6: Nhập mã tài khoản và dòng FORM nếu đã được nghiệp vụ xác nhận.
Bước 7: Ghi chú rõ nguồn số liệu.
Bước 8: Nhấn "Thêm/Cập nhật", sau đó nhấn "Lưu tệp".

Không tự chọn dòng FORM hoặc mã tài khoản khi chưa được nghiệp vụ xác nhận.

8. THỨ TỰ TỆP NGUỒN CHI PHÍ

Nút "Thứ tự file nguồn" dùng để chọn các tệp chi phí được đọc và sắp xếp thứ tự xử lý.

Cách sử dụng:
Bước 1: Nhấn "Thứ tự file nguồn".
Bước 2: Chọn một dòng.
Bước 3: Nhấn "Chọn file..." nếu cần thay tệp.
Bước 4: Dùng "Lên" hoặc "Xuống" để đổi thứ tự.
Bước 5: Bỏ chọn "Dùng dòng này" nếu muốn tạm thời không đọc tệp đó.
Bước 6: Nhấn "Lưu".

9. CHẠY TÍNH TOÁN VÀ KIỂM TRA KẾT QUẢ

Trước khi nhấn "CHẠY TÍNH TOÁN", cần kiểm tra:
- Năm tài chính đã đúng chưa.
- Tỷ giá đã đúng chưa.
- Tệp mẫu và các thư mục nguồn đã đúng chưa.
- Nguồn nhân sự và thời gian đã được cập nhật chưa.
- Các dữ liệu bổ sung đã được lưu chưa.

Sau khi chạy:
- Đọc Nhật ký xử lý từ đầu đến cuối.
- Không bỏ qua các dòng báo thiếu dữ liệu hoặc không xuất được tệp.
- Mở tệp kết quả của Trung tâm chi phí đã chạy thử.
- Đối chiếu số người, thời gian cố định và thời gian tăng ca từ tháng 4 đến tháng 3.
- Kiểm tra các công thức và khoản chi phí trước khi gửi chính thức.

10. CÁC TÌNH HUỐNG THƯỜNG GẶP

Không thấy số người hoặc thời gian sau khi chọn mã Trung tâm chi phí:
- Kiểm tra Năm tài chính trên màn hình chính.
- Kiểm tra đã nhấn "Cập nhật CSDL" chưa.
- Kiểm tra Nhật ký xem tệp của phòng có bị bỏ qua không.

Chọn năm tương lai nhưng bảng thời gian trống:
- Đây là hành vi đúng nếu chưa có tệp nguồn của năm đó.
- Chương trình không dùng dữ liệu của năm cũ để thay thế.

Không xuất được tệp kết quả vì thiếu nguồn sự thật:
- Đọc thông báo để biết Trung tâm chi phí và các kỳ còn thiếu.
- Chọn đúng thư mục nguồn, cập nhật lại cơ sở dữ liệu rồi chạy lại.

Đã nhập bổ sung nhưng kết quả chưa thay đổi:
- Kiểm tra đã nhấn "Lưu 12 tháng" hoặc "Lưu tệp" chưa.
- Chạy tính toán lại sau khi lưu.

Đường dẫn trở về mặc định:
- Trường hợp này xảy ra khi tệp hoặc thư mục đã lưu không còn tồn tại.
- Chọn lại đường dẫn hợp lệ; chương trình sẽ ghi nhớ cho lần sau.

11. NGUYÊN TẮC AN TOÀN

- Luôn chạy thử một Trung tâm chi phí trước khi chạy tất cả.
- Không dùng dữ liệu của năm tài chính khác để bù cho năm đang thiếu.
- Không nhập số ước lượng nếu chưa được người phụ trách nghiệp vụ xác nhận.
- Không bỏ qua cảnh báo trong Nhật ký xử lý.
- Luôn mở và kiểm tra tệp Excel kết quả trước khi gửi chính thức.
""".strip()

# Current-code corrections kept next to the visible guide so the in-app help
# remains accurate while older explanatory paragraphs are retained for history.
USER_GUIDE_TEXT_LATEST += """

ĐÍNH CHÍNH THEO CODE HIỆN TẠI

- FY2027 là bộ dữ liệu đã nghiệm thu. Với FY2028 trở đi, phải chuẩn bị đầy đủ bộ nguồn cùng năm; chương trình
  không tự dùng file, đơn giá, dấu chọn hoặc kết quả tham khảo của FY trước.
- Nút "Cập nhật CSDL" chỉ đồng bộ nguồn nhân sự và thời gian. Các workbook chi phí (Facility, tài sản
  cố định, IT, Tổng vụ, sinh nhật, NNN) được đọc lại khi bấm "CHẠY TÍNH TOÁN".
- Khi mở `.exe`, chương trình tự tìm và đọc `project.json`: ưu tiên project gần nhất đã ghi nhớ trong LocalAppData,
  sau đó mới tìm file cạnh thư mục ứng dụng. Vì vậy không cần chọn lại FORM, nguồn, manual DB, output hoặc history
  mỗi lần khởi động. Dùng nút "Mở/đổi project..." khi chuyển sang bộ dữ liệu khác hoặc khi đã di chuyển project
  sang nơi có đường dẫn tuyệt đối mới.
- `project.json` là hồ sơ cấu hình đường dẫn, không phải dữ liệu nguồn và không phải file chạy chương trình.
  Dữ liệu chỉnh sửa manual vẫn nằm trong kho riêng theo FY; không trộn FY2027 với FY2028.
- Sau khi chạy, mở thư mục output cấu hình của FY và thư mục BAO_CAO_KIEM_TRA. Tên báo cáo hiện hành là
  BAO_CAO_LAN_CHAY.xlsx, DU_LIEU_CON_THIEU.xlsx và KIEM_TRA_TY_GIA.xlsx; không tìm các tên .md/.csv
  cũ trong tài liệu lịch sử.

- Tài sản cố định được xuất theo thứ tự source/manifest động của complete-v1. Không coi dòng FORM 38/42
  là vị trí đích cố định.
- Khi cần giải thích chênh lệch tài sản cố định, chạy riêng bộ audit:
  py scripts\\audit_fixed_assets_cross_trace.py
  py scripts\\classify_fixed_assets_mismatches.py
  py scripts\\build_fixed_assets_business_decision_pack.py
  Lịch sử từng lần chạy nằm trong docs\\audits\\history\\fixed_assets và trong mp2027.db.

CHI PHÍ ĐỒNG PHỤC VÀ CỐC XẾP

- Chương trình đọc dấu chọn của từng phòng từ sheet 原価センタ, cột F đến U, trong file yêu cầu
  Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx. Phòng không được đánh dấu sẽ không bị tính.
- Số người mới của từng tháng là phần tăng riêng của Nhân viên và Công nhân so với tháng trước;
  tổng người mới bằng hai phần tăng này cộng lại. Tháng 4 cần dữ liệu tháng 3 của năm tài chính trước.
- Quần, mũ và áo được cấp 2 cái/người; giày và áo khoác được cấp 1 cái/người.
- Phòng được đánh dấu áo ngắn tay thì toàn bộ người mới dùng áo ngắn tay. Phòng được đánh dấu áo polo
  thì toàn bộ người mới dùng áo polo. Phòng an ninh dùng cột áo riêng. Nếu nguồn đánh dấu trùng nhiều
  loại áo, chương trình không tự chọn và sẽ báo người dùng sửa nguồn.
- Người vào tháng 5 đến tháng 9 nhận áo ngắn tay/polo ngay tháng vào và nhận áo dài tay bổ sung tháng 10.
  Người vào tháng 1 nhận áo dài tay tháng 1 và áo ngắn tay/polo bổ sung tháng 2. Người vào các tháng
  2, 3, 4, 10, 11, 12 nhận cả hai nhóm áo trong tháng vào.
- Cốc cho người mới chỉ tính theo phần tăng Công nhân. Cốc định kỳ chỉ áp dụng tháng 2 và tháng 8 cho
  phòng được đánh dấu cốc xếp.
- Để nhập cốc định kỳ: mở "Nhập sự kiện thiếu dữ liệu", chọn "Cốc xếp định kỳ", chọn tháng 2 hoặc
  tháng 8 và nhập số lượng nguyên từ 0 trở lên. Nhập 0 nghĩa là đã xác nhận không phát. Để trống thì
  kết quả bằng 0 và báo thiếu dữ liệu.
- Chi phí cấp đổi đồng phục do hỏng/mất vẫn là số phát thực tế và không được chương trình suy ra từ
  chênh lệch nhân sự.

CHUẨN BỊ NĂM TÀI CHÍNH MỚI

1. Tạo riêng các thư mục docs/MP<năm>, raw/FY<năm>, OUTPUT_FY<năm>.
2. Đặt FORM, các file chi phí và source_file_order vào docs/MP<năm>.
3. Đặt nguồn nhân sự/thời gian, bảng dấu đồng phục/cốc xếp và manual_inputs.db vào raw/FY<năm>.
4. Mỗi file nguồn bắt buộc phải có dấu hiệu cùng năm trong tên file, tên trang hoặc tiêu đề. Không dùng
   file cũ rồi chỉ đổi tên.
5. Chọn năm trên màn hình, chờ kiểm tra nguồn đạt, rồi chạy thử một phòng trước. Nếu thiếu hoặc sai năm,
   chương trình dừng trước khi tính và tạo báo cáo trong RUN_HISTORY/FY<năm>/<mã lần chạy>/reports.
6. Kết quả chỉ được công bố khi chạy thành công. Lần chạy cũ và dữ liệu nhập tay của năm khác được giữ
   riêng, không tham gia tính toán của năm mới.
""".strip()


class MPManagerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.geometry("980x720")
        initial_fiscal_year = _default_fiscal_year()
        self.project, project_created = discover_or_create_project(BASE_DIR, initial_fiscal_year)
        if self.project.ensure_fiscal_year(initial_fiscal_year):
            self.project.save()
        initial_paths = self.project.fiscal_paths(initial_fiscal_year)
        self.project_file = tk.StringVar(value=self.project.config_path)
        template_path = initial_paths.template_path
        self.fiscal_year = tk.StringVar(value=str(initial_fiscal_year))
        self.exchange_rate = tk.StringVar(value=self._initial_exchange_rate(template_path))
        self.cc_code_filter = tk.StringVar(value="")
        self.template_path = tk.StringVar(value=template_path)
        self.source_dir = tk.StringVar(value=initial_paths.source_dir)
        self.headcount_source_dir = tk.StringVar(value=initial_paths.headcount_source_dir)
        self._auto_path_fiscal_year = initial_fiscal_year
        self.headcount_source_status = tk.StringVar(value=self._initial_headcount_source_status())
        self.preflight_status = tk.StringVar(value="Chưa kiểm tra nguồn cho năm tài chính đang chọn")
        self._preflight_token = 0
        self._approved_preflight_signature = None
        self._approved_preflight_report = None
        self._approved_uniform_policy_path = None
        self.last_excel_mtime = 0.0
        self.syncing_master = False
        self.ui_thread_id = threading.get_ident()
        self.ui_queue = queue.Queue()

        self.fiscal_year.trace_add("write", self._on_staffing_selection_changed)
        self.template_path.trace_add("write", self._on_source_selection_changed)
        self.source_dir.trace_add("write", self._on_source_selection_changed)
        self.headcount_source_dir.trace_add("write", self._on_source_selection_changed)
        self.setup_styles()
        self.setup_ui()
        self.preflight_status.trace_add("write", self._on_workflow_state_changed)
        self._refresh_fiscal_year_labels()
        self.set_icon()
        self.root.after(0, lambda: self.log(
            (f"Đã tạo project tương thích: {self.project.config_path}" if project_created
             else f"Đang dùng project: {self.project.config_path}")
        ))
        self.root.after(0, self._update_workflow_guide)
        self.root.after(50, self._drain_ui_queue)
        self.root.after(300, self.load_cc_list)
        self.root.after(500, self._mark_preflight_stale)

    def _on_staffing_selection_changed(self, *_args):
        self._refresh_fiscal_year_labels()
        try:
            fiscal_year = int(self.fiscal_year.get())
        except ValueError:
            return
        created = self.project.ensure_fiscal_year(fiscal_year)
        paths = self.project.fiscal_paths(fiscal_year)
        if created:
            self.project.save()
        self.template_path.set(paths.template_path)
        self.source_dir.set(paths.source_dir)
        self.headcount_source_dir.set(paths.headcount_source_dir)
        self.exchange_rate.set(self._initial_exchange_rate(paths.template_path))
        self._auto_path_fiscal_year = fiscal_year
        if hasattr(self, "headcount_source_status"):
            self.headcount_source_status.set(self._initial_headcount_source_status())
        self._mark_preflight_stale()

    def _on_source_selection_changed(self, *_args):
        self._mark_preflight_stale()

    def _mark_preflight_stale(self, force_refresh: bool = False):
        """Disable calculation immediately when the selected source changes."""
        if not hasattr(self, "start_btn"):
            return
        self._preflight_token += 1
        self._approved_preflight_signature = None
        self._approved_preflight_report = None
        self._approved_uniform_policy_path = None
        self._accepted_missing_categories = ()
        token = self._preflight_token
        self.start_btn.configure(state=tk.DISABLED)
        self.preflight_status.set(
            "Đang kiểm tra lại toàn bộ nguồn..."
            if force_refresh else
            "Đang đối chiếu nguồn đã chọn..."
        )
        self.root.after(350, lambda: self._start_preflight_check(token, force_refresh=force_refresh))

    def _start_preflight_check(self, token: int, *, force_refresh: bool = False):
        if token != self._preflight_token:
            return
        try:
            fiscal_year = int(self.fiscal_year.get())
            template = self.template_path.get().strip()
            source = self.source_dir.get().strip()
            headcount = self.headcount_source_dir.get().strip()
            exchange_rate = validate_exchange_rate(self.exchange_rate.get())
        except Exception as exc:
            self.preflight_status.set(f"Chưa thể kiểm tra: {_friendly_error_message(exc)}")
            return

        def worker():
            started_at = time.perf_counter()
            try:
                self._run_on_ui_thread(
                    self.preflight_status.set,
                    (
                        "Đang quét kỹ FORM và toàn bộ nguồn..."
                        if force_refresh else
                        "Đang kiểm tra metadata thay đổi..."
                    ),
                )
                paths = self._project_paths(fiscal_year)
                context = create_fiscal_run_context(
                    fiscal_year,
                    template_path=template,
                    source_dir=source,
                    headcount_source_dir=headcount,
                    uniform_policy_path=paths.uniform_policy_path,
                    output_dir=paths.output_dir,
                    exchange_rate=exchange_rate,
                    exchange_rate_source="FORM!B2 / người dùng xác nhận trên giao diện",
                    history_root=paths.history_root,
                    manual_input_store=paths.manual_input_store,
                    base_dir=self.project.root_dir,
                )
                if force_refresh:
                    report, cache_hit = cached_preflight_fiscal_run(
                        context,
                        force_refresh=True,
                        extra_paths=(self.project.config_path,),
                        checker=lambda active_context: preflight_fiscal_run(
                            active_context,
                            progress=lambda message: self._run_on_ui_thread(
                                self._update_preflight_progress,
                                token,
                                message,
                            ),
                        ),
                    )
                else:
                    report = get_cached_preflight(
                        context,
                        extra_paths=(self.project.config_path,),
                    )
                    cache_hit = report is not None
                    if report is None:
                        self._run_on_ui_thread(
                            self._finish_preflight_check,
                            token,
                            False,
                            (
                                "Nguồn đã thay đổi hoặc chưa có kết quả quét nội dung. "
                                "Bấm ‘Quét kỹ lại nội dung’ để xác nhận nguồn"
                            ),
                            None,
                            None,
                            context,
                            False,
                            time.perf_counter() - started_at,
                        )
                        return
                if report.ok:
                    summary = "Đủ nguồn và đúng năm"
                elif report.can_continue_incomplete:
                    missing = ", ".join(report.accepted_missing_categories())
                    summary = f"Thiếu nguồn chi phí có thể chấp nhận: {missing}"
                else:
                    summary = "; ".join(
                        f"{issue.reason}. {issue.action}" for issue in report.blocking_issues[:2]
                    )
                signature = (
                    fiscal_year,
                    os.path.abspath(template),
                    os.path.abspath(source),
                    os.path.abspath(headcount),
                    float(exchange_rate),
                )
                self._run_on_ui_thread(
                    self._finish_preflight_check,
                    token,
                    report.ok,
                    summary,
                    signature,
                    report,
                    context,
                    cache_hit,
                    time.perf_counter() - started_at,
                )
            except Exception as exc:
                self._run_on_ui_thread(
                    self._finish_preflight_check,
                    token,
                    False,
                    _friendly_error_message(exc),
                    None,
                    None,
                    None,
                    False,
                    time.perf_counter() - started_at,
                )

        threading.Thread(target=worker, daemon=True).start()

    def _update_preflight_progress(self, token: int, message: str) -> None:
        if token == self._preflight_token:
            self.preflight_status.set(message)

    def _finish_preflight_check(
        self,
        token: int,
        ok: bool,
        summary: str,
        signature=None,
        report=None,
        context=None,
        cache_hit: bool = False,
        elapsed_seconds: float = 0.0,
    ):
        if token != self._preflight_token:
            return
        reusable = bool(ok or getattr(report, "can_continue_incomplete", False))
        if reusable:
            self._approved_preflight_signature = signature
            self._approved_preflight_report = report
            self._approved_uniform_policy_path = getattr(context, "uniform_policy_path", None)
            if ok:
                prefix = "Đúng năm và đủ nguồn: có thể chạy tính toán"
            else:
                prefix = "Cảnh báo: " + summary + ". Có thể chạy sau khi xác nhận."
            mode = "cache hợp lệ" if cache_hit else "quét nội dung mới"
            self.preflight_status.set(
                f"{prefix} — {mode}, hoàn tất trong {elapsed_seconds:.1f} giây"
            )
            self.start_btn.configure(state=tk.NORMAL)
        else:
            self.preflight_status.set(
                f"Chưa thể chạy: {summary} — hoàn tất kiểm tra trong {elapsed_seconds:.1f} giây"
            )
            self.start_btn.configure(state=tk.DISABLED)

    def _project_paths(self, fiscal_year: int | None = None):
        year = int(fiscal_year if fiscal_year is not None else self.fiscal_year.get())
        created = self.project.ensure_fiscal_year(year)
        paths = self.project.fiscal_paths(year)
        if created:
            self.project.save()
        return paths

    def _operational_database(self) -> str:
        return self.project.operational_database

    def _manual_input_store(self, fiscal_year: int | None = None) -> str:
        return self._project_paths(fiscal_year).manual_input_store

    def _initial_headcount_source_status(self) -> str:
        conn = None
        try:
            conn = get_connection(self._operational_database())
            create_schema(conn)
            values = {
                str(row[0]): str(row[1] or "")
                for row in conn.execute(
                    "SELECT key,value FROM sys_params WHERE key LIKE 'headcount_source_%'"
                )
            }
            updated = values.get("headcount_source_updated_at", "")
            if not updated:
                return "Chưa cập nhật CSDL"
            imported = values.get("headcount_source_imported_files", "?")
            total = values.get("headcount_source_files", "?")
            skipped = values.get("headcount_source_skipped_files", "?")
            errors = values.get("headcount_source_error_files", "?")
            fy = values.get("headcount_source_fiscal_year", "?")
            return f"Đã cập nhật FY{fy}: {imported}/{total} tệp • bỏ qua {skipped} • lỗi {errors} • {updated[:16]}"
        except Exception:
            return "Chưa đọc được trạng thái cập nhật CSDL"
        finally:
            if conn is not None:
                conn.close()

    def _refresh_fiscal_year_labels(self, *_args):
        raw = self.fiscal_year.get().strip()
        label = raw if raw.isdigit() and len(raw) == 4 else "—"
        self.root.title(f"MP{label} Manager - Quản lý Ngân sách")
        if hasattr(self, "main_heading"):
            self.main_heading.configure(text=f"Tính toán Ngân sách MP{label}")

    @staticmethod
    def _initial_exchange_rate(template_path: str) -> str:
        try:
            return f"{read_exchange_rate_from_form(template_path):.0f}"
        except Exception:
            return ""

    def _activate_project(self, project: ProjectConfig) -> None:
        self._preflight_token += 1
        self.project = project
        remember_last_project(project.config_path)
        self.project_file.set(project.config_path)
        paths = self._project_paths(self._current_fiscal_year())
        self.template_path.set(paths.template_path)
        self.source_dir.set(paths.source_dir)
        self.headcount_source_dir.set(paths.headcount_source_dir)
        self.exchange_rate.set(self._initial_exchange_rate(paths.template_path))
        self.cc_code_filter.set("")
        self.headcount_source_status.set(self._initial_headcount_source_status())
        self.load_cc_list()
        self._mark_preflight_stale()
        self.log(f"Đang dùng project: {project.config_path}")

    def open_project(self) -> None:
        path = filedialog.askopenfilename(
            title="Mở project",
            initialdir=self.project.root_dir,
            filetypes=[("MP Manager project", "project.json"), ("JSON", "*.json")],
        )
        if not path:
            return
        try:
            self._activate_project(ProjectConfig.load(path))
        except Exception as exc:
            messagebox.showerror("Không mở được project", str(exc))

    def create_project(self) -> None:
        root_dir = filedialog.askdirectory(title="Chọn thư mục chứa dữ liệu project")
        if not root_dir:
            return
        config_path = os.path.join(root_dir, "project.json")
        try:
            if os.path.isfile(config_path):
                project = ProjectConfig.load(config_path)
            else:
                project = ProjectConfig.create_legacy_compatible(
                    root_dir, self._current_fiscal_year(), config_path=config_path
                )
                project.save()
            self._activate_project(project)
        except Exception as exc:
            messagebox.showerror("Không tạo được project", str(exc))

    def configure_project_storage(self) -> None:
        """Edit shared and selected-FY storage paths without touching their data."""
        fiscal_year = self._current_fiscal_year()
        paths = self._project_paths(fiscal_year)
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Cấu hình project FY{fiscal_year}")
        dialog.geometry("820x430")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.columnconfigure(1, weight=1)

        fields = [
            ("CSDL vận hành", self.project.operational_database, "file"),
            ("Policy đồng phục", paths.uniform_policy_path or "", "file"),
            ("Kho nhập tay FY", paths.manual_input_store, "file"),
            ("Thư mục output", paths.output_dir, "dir"),
            ("Thư mục run history", paths.history_root, "dir"),
        ]
        variables = {}
        for row, (label, value, kind) in enumerate(fields):
            ttk.Label(dialog, text=label).grid(row=row, column=0, sticky="w", padx=12, pady=8)
            variable = tk.StringVar(value=value)
            variables[label] = variable
            ttk.Entry(dialog, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=8, pady=8)
            if kind == "dir":
                command = lambda var=variable, title=label: self._choose_project_directory(var, title)
            else:
                command = lambda var=variable, title=label: self._choose_project_file(var, title)
            ttk.Button(dialog, text="Chọn…", command=command).grid(row=row, column=2, padx=(0, 12), pady=8)

        ttk.Label(
            dialog,
            text=("Các đường dẫn tương đối sẽ được lưu theo thư mục chứa project.json. "
                  "Kho nhập tay phải riêng cho từng FY."),
            wraplength=760,
        ).grid(row=len(fields), column=0, columnspan=3, sticky="w", padx=12, pady=(8, 16))

        button_bar = ttk.Frame(dialog)
        button_bar.grid(row=len(fields) + 1, column=0, columnspan=3, sticky="e", padx=12, pady=12)
        ttk.Button(button_bar, text="Hủy", command=dialog.destroy).pack(side="right")

        def save_configuration():
            try:
                self.project.update_storage_paths(
                    fiscal_year,
                    operational_database=variables["CSDL vận hành"].get().strip(),
                    uniform_policy_path=variables["Policy đồng phục"].get().strip(),
                    manual_input_store=variables["Kho nhập tay FY"].get().strip(),
                    output_dir=variables["Thư mục output"].get().strip(),
                    history_root=variables["Thư mục run history"].get().strip(),
                )
                self.project.save()
                refreshed = self._project_paths(fiscal_year)
                self.template_path.set(refreshed.template_path)
                self.source_dir.set(refreshed.source_dir)
                self.headcount_source_dir.set(refreshed.headcount_source_dir)
                self._mark_preflight_stale()
                self.log(f"Đã lưu cấu hình storage project FY{fiscal_year}")
                dialog.destroy()
            except Exception as exc:
                messagebox.showerror("Cấu hình không hợp lệ", str(exc), parent=dialog)

        ttk.Button(button_bar, text="Lưu cấu hình", style="Primary.TButton", command=save_configuration).pack(
            side="right", padx=(0, 8)
        )

    @staticmethod
    def _choose_project_file(variable: tk.StringVar, title: str) -> None:
        path = filedialog.askopenfilename(title=f"Chọn {title}")
        if path:
            variable.set(path)

    @staticmethod
    def _choose_project_directory(variable: tk.StringVar, title: str) -> None:
        path = filedialog.askdirectory(title=f"Chọn {title}")
        if path:
            variable.set(path)

    def _save_path_preference(self, key: str, path: str, description: str) -> None:
        aliases = {
            "template_path": "template_path",
            "cost_source_dir": "source_dir",
            "headcount_source_dir": "headcount_source_dir",
        }
        argument = aliases.get(key)
        if argument is None:
            raise KeyError(f"Đường dẫn project không được hỗ trợ: {key}")
        self.project.update_fiscal_paths(self._current_fiscal_year(), **{argument: os.path.abspath(path)})
        self.project.save()

    def _reload_exchange_rate_from_template(self) -> bool:
        """Refresh the editable rate and never retain a stale value."""
        rate_text = self._initial_exchange_rate(self.template_path.get())
        if rate_text:
            self.exchange_rate.set(rate_text)
            self.log(f"Đã đọc tỷ giá FORM!B2: {rate_text} USD/VND")
            return True

        self.exchange_rate.set("")
        self.log("FORM đang chọn không có tỷ giá hợp lệ tại B2; hãy nhập tỷ giá trước khi chạy.")
        return False

    def set_icon(self):
        icon_path = resource_path(os.path.join("assets", "app_icon.ico"))
        if os.path.exists(icon_path):
            try:
                # Windows specific icon loading
                self.root.iconbitmap(icon_path)
            except Exception as e:
                print(f"Lỗi khi nạp icon: {e}")


    def _on_workflow_state_changed(self, *_args):
        if hasattr(self, "workflow_cards"):
            self._update_workflow_guide()

    def _update_workflow_guide(self):
        if not hasattr(self, "workflow_cards"):
            return

        try:
            fiscal_year_ready = int(self.fiscal_year.get()) >= 2000
        except (TypeError, ValueError):
            fiscal_year_ready = False
        source_ready = all(
            (
                os.path.isfile(self.template_path.get()),
                os.path.isdir(self.source_dir.get()),
                os.path.isdir(self.headcount_source_dir.get()),
            )
        )
        report = self._approved_preflight_report
        preflight_ready = bool(report and getattr(report, "ok", False))
        preflight_warning = bool(report and getattr(report, "can_continue_incomplete", False))

        states = [
            "done" if fiscal_year_ready else "active",
            "done" if source_ready else ("active" if fiscal_year_ready else "pending"),
            "done" if preflight_ready else ("warning" if preflight_warning else ("active" if source_ready else "pending")),
            "optional" if (preflight_ready or preflight_warning) else "pending",
            "active" if (preflight_ready or preflight_warning) else "pending",
        ]
        palette = {
            "done": ("#dff4ea", "#176b4d", "✓"),
            "active": ("#e6efff", "#2457a6", "→"),
            "warning": ("#fff1cf", "#855b00", "!"),
            "optional": ("#eee9fb", "#5c3b8c", "○"),
            "pending": ("#f0f2f5", "#66707a", "·"),
        }
        for state, widgets in zip(states, self.workflow_cards):
            background, foreground, marker = palette[state]
            card, badge, title, detail = widgets
            card.configure(bg=background, highlightbackground=foreground)
            for widget in (badge, title, detail):
                widget.configure(bg=background, fg=foreground)
            badge.configure(text=marker)

        if not fiscal_year_ready:
            next_action = "Việc cần làm tiếp theo: nhập đúng năm tài chính."
        elif not source_ready:
            next_action = "Việc cần làm tiếp theo: chọn đủ FORM, nguồn chi phí và nguồn nhân sự cùng năm."
        elif preflight_warning:
            next_action = "Việc cần làm tiếp theo: đọc cảnh báo màu vàng; có thể bổ sung dữ liệu hoặc xác nhận chạy kết quả chưa đầy đủ."
        elif not preflight_ready:
            next_action = "Việc cần làm tiếp theo: chờ kiểm tra nguồn; nếu có lỗi đỏ, sửa nguồn rồi bấm “Kiểm tra lại từ đầu”."
        else:
            next_action = "Việc cần làm tiếp theo: bổ sung dữ liệu nhập tay nếu có, sau đó bấm “CHẠY TÍNH TOÁN”."
        self.workflow_next_action.configure(text=next_action)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Header.TLabel", font=("Segoe UI", 15, "bold"))
        style.configure("WorkflowTitle.TLabel", font=("Segoe UI", 11, "bold"), foreground="#1f344d")
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=10)

    def setup_ui(self):
        container = ttk.Frame(self.root, padding=20)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(14, weight=1)

        self.main_heading = ttk.Label(container, text="", style="Header.TLabel")
        self.main_heading.grid(row=0, column=0, sticky="w", pady=(0, 16))
        project_bar = ttk.Frame(container)
        project_bar.grid(row=0, column=1, columnspan=2, sticky="e", pady=(0, 16))
        ttk.Label(project_bar, textvariable=self.project_file, width=44).pack(side="left", padx=(0, 6))
        ttk.Button(project_bar, text="Mở/đổi project...", command=self.open_project).pack(side="left")
        ttk.Button(project_bar, text="Tạo project...", command=self.create_project).pack(side="left", padx=(6, 0))
        ttk.Button(project_bar, text="Cấu hình project...", command=self.configure_project_storage).pack(
            side="left", padx=(6, 0)
        )

        ttk.Label(container, text="Năm tài chính").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(container, textvariable=self.fiscal_year, width=20).grid(row=1, column=1, sticky="w")

        ttk.Label(container, text="Tỷ giá (USD/VND)").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(container, textvariable=self.exchange_rate, width=20).grid(row=2, column=1, sticky="w")
        ttk.Label(container, text="Áp dụng cho lần chạy này và ghi vào B2 của file kết quả.").grid(
            row=2, column=2, sticky="w", padx=(12, 0)
        )

        ttk.Label(container, text="Trung tâm chi phí (Tùy chọn)").grid(row=3, column=0, sticky="w", pady=4)
        cc_frame = ttk.Frame(container)
        cc_frame.grid(row=3, column=1, sticky="w")
        self.cc_combo = ttk.Combobox(cc_frame, textvariable=self.cc_code_filter, width=40, state="readonly")
        self.cc_combo.pack(side="left")
        self.refresh_btn = ttk.Button(
            cc_frame,
            text="Nạp lại CC từ FORM",
            command=self.refresh_cost_centers_from_form,
        )
        self.refresh_btn.pack(side="left", padx=(4, 0))
        ttk.Label(container, text="Để trống để xuất toàn bộ").grid(row=3, column=2, sticky="w", padx=(12, 0))

        ttk.Label(container, text="Tệp mẫu FORM").grid(row=4, column=0, sticky="w", pady=(14, 4))
        ttk.Entry(container, textvariable=self.template_path).grid(row=4, column=1, sticky="ew", padx=(0, 8))
        ttk.Button(container, text="Chọn...", width=11, command=self.browse_template).grid(row=4, column=2, sticky="w")

        ttk.Label(container, text="Thư mục nguồn chi phí").grid(row=5, column=0, sticky="w", pady=4)
        ttk.Entry(container, textvariable=self.source_dir).grid(row=5, column=1, sticky="ew", padx=(0, 8))
        ttk.Button(container, text="Chọn...", width=11, command=self.browse_source_dir).grid(row=5, column=2, sticky="w")

        ttk.Label(container, text="Nguồn nhân sự & thời gian").grid(row=6, column=0, sticky="w", pady=4)
        ttk.Entry(container, textvariable=self.headcount_source_dir).grid(row=6, column=1, sticky="ew", padx=(0, 8))
        source_buttons = ttk.Frame(container)
        source_buttons.grid(row=6, column=2, sticky="w")
        ttk.Button(source_buttons, text="Chọn...", width=11, command=self.browse_headcount_source_dir).pack(side="left")
        ttk.Button(
            source_buttons,
            text="Cập nhật CSDL",
            command=self.update_headcount_database,
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            source_buttons,
            text="Dọn dữ liệu FY",
            command=self.cleanup_headcount_database,
        ).pack(side="left", padx=(6, 0))
        ttk.Label(
            container,
            textvariable=self.headcount_source_status,
            font=("Segoe UI", 9, "italic"),
        ).grid(row=7, column=1, columnspan=2, sticky="w", pady=(0, 8))

        guide_panel = ttk.Frame(container, padding=(0, 6))
        guide_panel.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(4, 8))
        ttk.Label(guide_panel, text="Làm theo 5 bước", style="WorkflowTitle.TLabel").pack(anchor="w", pady=(0, 6))
        workflow_row = ttk.Frame(guide_panel)
        workflow_row.pack(fill="x")
        workflow_steps = (
            ("1", "Chọn năm", "Đúng năm tài chính"),
            ("2", "Chọn nguồn", "FORM · chi phí · nhân sự"),
            ("3", "Kiểm tra", "Xanh / vàng / đỏ"),
            ("4", "Bổ sung", "Chỉ khi nghiệp vụ có"),
            ("5", "Chạy", "Thử 1 phòng trước"),
        )
        self.workflow_cards = []
        for column, (number, title_text, detail_text) in enumerate(workflow_steps):
            workflow_row.columnconfigure(column, weight=1, uniform="workflow")
            card = tk.Frame(workflow_row, bg="#f0f2f5", highlightthickness=1, highlightbackground="#66707a")
            card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 4, 0), ipadx=6, ipady=4)
            badge = tk.Label(card, text=number, font=("Segoe UI", 11, "bold"), bg="#f0f2f5", fg="#66707a")
            badge.pack(anchor="w")
            title = tk.Label(card, text=f"{number}. {title_text}", font=("Segoe UI", 9, "bold"), bg="#f0f2f5", fg="#66707a")
            title.pack(anchor="w")
            detail = tk.Label(card, text=detail_text, font=("Segoe UI", 8), bg="#f0f2f5", fg="#66707a")
            detail.pack(anchor="w")
            self.workflow_cards.append((card, badge, title, detail))
        self.workflow_next_action = ttk.Label(guide_panel, text="", wraplength=900, font=("Segoe UI", 9, "bold"))
        self.workflow_next_action.pack(anchor="w", pady=(7, 0))

        actions = ttk.Frame(container)
        actions.grid(row=9, column=0, columnspan=3, sticky="w", pady=(4, 0))
        for text, command in (
            ("Nhập nhân sự thủ công", self.open_headcount_editor_v2),
            ("Nhập sự kiện thiếu dữ liệu", self.open_event_driver_editor),
            ("Thứ tự file nguồn", self.open_source_order_editor),
            ("Lịch sử lần chạy", self.open_run_history),
            ("Hướng dẫn trực quan", self.open_user_guide),
        ):
            ttk.Button(actions, text=text, command=command).pack(side="left", padx=(0, 8))

        ttk.Separator(container, orient=tk.HORIZONTAL).grid(
            row=10, column=0, columnspan=3, sticky="ew", pady=12
        )

        check_actions = ttk.Frame(container)
        check_actions.grid(row=11, column=0, sticky="w")
        ttk.Button(
            check_actions,
            text="Kiểm tra thay đổi nhanh",
            command=lambda: self._mark_preflight_stale(force_refresh=False),
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            check_actions,
            text="Quét kỹ lại nội dung",
            command=lambda: self._mark_preflight_stale(force_refresh=True),
        ).pack(side="left")
        ttk.Label(
            container,
            textvariable=self.preflight_status,
            font=("Segoe UI", 9, "italic"),
            wraplength=700,
        ).grid(row=11, column=1, columnspan=2, sticky="w", padx=(8, 0))
        self.start_btn = ttk.Button(
            container,
            text="CHẠY TÍNH TOÁN",
            style="Primary.TButton",
            command=self.start_pipeline,
        )
        self.start_btn.grid(row=12, column=0, columnspan=3, sticky="w", pady=(8, 0))

        ttk.Label(container, text="Nhật ký xử lý").grid(row=13, column=0, columnspan=3, sticky="w", pady=(12, 4))
        self.log_widget = scrolledtext.ScrolledText(
            container, height=12, state=tk.DISABLED, font=("Consolas", 9)
        )
        self.log_widget.grid(row=14, column=0, columnspan=3, sticky="nsew")


    def _run_on_ui_thread(self, callback, *args, **kwargs):
        if threading.get_ident() == self.ui_thread_id:
            callback(*args, **kwargs)
            return
        self.ui_queue.put((callback, args, kwargs))

    def _drain_ui_queue(self):
        while True:
            try:
                callback, args, kwargs = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            callback(*args, **kwargs)
        self.root.after(50, self._drain_ui_queue)

    def log(self, message: str):
        if threading.get_ident() != self.ui_thread_id:
            self._run_on_ui_thread(self.log, message)
            return
        self.log_widget.configure(state=tk.NORMAL)
        self.log_widget.insert(tk.END, f"{datetime.now().strftime('[%H:%M:%S]')} {message}\n")
        self.log_widget.see(tk.END)
        self.log_widget.configure(state=tk.DISABLED)

    def browse_template(self):
        current = self.template_path.get().strip()
        initial_dir = os.path.dirname(current) if os.path.isfile(current) else BASE_DIR
        path = filedialog.askopenfilename(initialdir=initial_dir, filetypes=[("Tệp Excel", "*.xlsx")])
        if path:
            validation_error = _validate_selected_template(path)
            if validation_error:
                messagebox.showerror("Lỗi", validation_error)
                return
            self.template_path.set(path)
            self._save_path_preference("template_path", path, "Selected FORM template")
            self._reload_exchange_rate_from_template()

    def browse_source_dir(self):
        initial_dir = self.source_dir.get().strip()
        if not os.path.isdir(initial_dir):
            initial_dir = BASE_DIR
        path = filedialog.askdirectory(initialdir=initial_dir)
        if path:
            validation_error = _validate_selected_source_dir(path)
            if validation_error:
                messagebox.showerror("Lỗi", validation_error)
                return
            self.source_dir.set(path)
            self._save_path_preference("cost_source_dir", path, "Selected cost source folder")

    def browse_headcount_source_dir(self):
        initial_dir = self.headcount_source_dir.get().strip()
        if not os.path.isdir(initial_dir):
            initial_dir = BASE_DIR
        path = filedialog.askdirectory(initialdir=initial_dir)
        if path:
            self.headcount_source_dir.set(path)
            try:
                self._save_path_preference(
                    "headcount_source_dir", path, "Department plan source folder"
                )
                self.headcount_source_status.set("Cần đồng bộ cho thư mục mới")
            except Exception as exc:
                self.log(f"Không lưu được thư mục nguồn nhân sự đã chọn: {exc}")

    def cleanup_headcount_database(self):
        try:
            fiscal_year = int(self.fiscal_year.get())
        except (TypeError, ValueError):
            messagebox.showerror("Năm tài chính không hợp lệ", "Hãy nhập năm tài chính gồm 4 chữ số.")
            return

        conn = None
        try:
            conn = get_connection(self._operational_database())
            create_schema(conn)
            counts = count_headcount_truth_rows(conn, fiscal_year)
            if counts["total_rows"] == 0:
                messagebox.showinfo(
                    "Không có dữ liệu cần dọn",
                    f"CSDL không có nguồn sự thật thuộc FY{fiscal_year} "
                    f"({counts['periods'][0]}–{counts['periods'][-1]}).",
                )
                return

            confirmed = messagebox.askyesno(
                "Xác nhận dọn nguồn sự thật",
                f"Bạn sắp xóa dữ liệu nguồn sự thật của FY{fiscal_year}\n"
                f"Phạm vi kỳ: {counts['periods'][0]}–{counts['periods'][-1]}\n\n"
                f"• Nhân sự kế hoạch phòng ban: {counts['monthly_headcount_rows']} dòng\n"
                f"• Giờ hành chính và tăng ca: {counts['headcount_time_rows']} dòng\n"
                f"• Tổng cộng: {counts['total_rows']} dòng\n\n"
                "Dữ liệu manual, GA, chi phí, danh mục CC và FY khác sẽ được giữ nguyên.\n"
                "Bạn có chắc chắn muốn tiếp tục?",
                icon="warning",
            )
            if not confirmed:
                self.log(f"Đã hủy dọn dữ liệu nguồn sự thật FY{fiscal_year}.")
                return

            result = cleanup_headcount_truth(conn, fiscal_year)
        except Exception as exc:
            self.log(f"Dọn nguồn sự thật FY{fiscal_year} thất bại; CSDL đã rollback: {exc}")
            messagebox.showerror(
                "Dọn dữ liệu thất bại",
                f"Không thay đổi dữ liệu trong CSDL.\n\n{exc}",
            )
            return
        finally:
            if conn is not None:
                conn.close()

        status = f"Đã dọn dữ liệu FY{fiscal_year} • chưa có nguồn sự thật"
        self.headcount_source_status.set(status)
        self.log(
            f"Đã dọn nguồn sự thật FY{fiscal_year}: "
            f"{result['monthly_headcount_rows']} dòng nhân sự + "
            f"{result['headcount_time_rows']} dòng giờ làm."
        )
        messagebox.showinfo(
            "Dọn dữ liệu thành công",
            f"Đã xóa {result['total_rows']} dòng nguồn sự thật của FY{fiscal_year}.\n\n"
            "Hãy bấm “Cập nhật CSDL” để nhập nguồn đã sửa.",
        )

    def _confirm_headcount_source_exceptions(self, review):
        """Return approved/rejected file sets, or None when the user cancels."""
        unknown = list(review.get("unknown_cost_centers", []))
        mismatches = list(review.get("name_mismatches", []))
        if not unknown and not mismatches:
            return set(), set(), set()

        dialog = tk.Toplevel(self.root)
        dialog.title("Xác nhận nguồn nhân sự cần kiểm tra")
        dialog.geometry("940x640")
        dialog.minsize(760, 480)
        dialog.transient(self.root)
        dialog.grab_set()
        outcome = {"value": None}

        outer = ttk.Frame(dialog, padding=14)
        outer.pack(fill=tk.BOTH, expand=True)
        ttk.Label(
            outer,
            text="Các mục dưới đây mặc định KHÔNG được nhập. Chỉ đánh dấu khi bạn đã kiểm tra A5/B5 trong file nguồn.",
            wraplength=880,
            justify=tk.LEFT,
        ).pack(fill=tk.X, pady=(0, 10))

        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        content = ttk.Frame(canvas)
        content.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        window_id = canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        variables = []

        def add_group(title, items, explanation, kind):
            if not items:
                return
            ttk.Label(content, text=title, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(8, 2))
            ttk.Label(content, text=explanation, wraplength=850, justify=tk.LEFT).pack(anchor="w", pady=(0, 6))
            for parsed in items:
                variable = tk.BooleanVar(value=False)
                expected = " / ".join(
                    value for value in (
                        getattr(parsed, "department_name_jp", ""),
                        getattr(parsed, "department_name_vn", ""),
                    ) if value
                )
                label = (
                    f"CC {parsed.cc_code} — B5: {parsed.department_name}\n"
                    f"File: {os.path.basename(parsed.path)}"
                )
                if expected:
                    label += f"\nLookup dự kiến: {expected}"
                ttk.Checkbutton(content, text=label, variable=variable).pack(
                    anchor="w", fill=tk.X, padx=(12, 0), pady=5
                )
                variables.append((kind, os.path.abspath(parsed.path), variable))

        add_group(
            "CC chưa có trong master",
            unknown,
            "Nếu xác nhận, dữ liệu sẽ được nhập theo nguyên CC trong A5; chương trình không tự tạo master. Sau đó cần đề nghị bổ sung CC vào danh mục.",
            "unknown",
        )
        add_group(
            "Tên B5 không xác minh tự động được",
            mismatches,
            "Chỉ xác nhận nếu CC A5 và tên hiển thị B5 đúng với phòng ban thực tế.",
            "name",
        )

        buttons = ttk.Frame(dialog, padding=(14, 8, 14, 14))
        buttons.pack(fill=tk.X)

        def submit():
            approved_unknown = {path for kind, path, var in variables if kind == "unknown" and var.get()}
            rejected_unknown = {path for kind, path, var in variables if kind == "unknown" and not var.get()}
            approved_names = {path for kind, path, var in variables if kind == "name" and var.get()}
            outcome["value"] = (approved_unknown, rejected_unknown, approved_names)
            dialog.destroy()

        ttk.Button(buttons, text="Hủy cập nhật", command=dialog.destroy).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(buttons, text="Tiếp tục với lựa chọn", command=submit).pack(side=tk.RIGHT)
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        self.root.wait_window(dialog)
        return outcome["value"]

    def update_headcount_database(self):
        source_dir = self.headcount_source_dir.get().strip()
        if not os.path.isdir(source_dir):
            messagebox.showerror("Nguồn không hợp lệ", "Hãy chọn thư mục nguồn nhân sự & thời gian.")
            return
        conn = None
        try:
            fiscal_year = int(self.fiscal_year.get())
            conn = get_connection(self._operational_database())
            create_schema(conn)
            review = review_headcount_time_sources(conn, source_dir, fiscal_year)
            approvals = self._confirm_headcount_source_exceptions(review)
            if approvals is None:
                self.log("Đã hủy cập nhật nguồn nhân sự trước khi ghi CSDL.")
                return
            approved_unknown, rejected_unknown, approved_names = approvals
            result = import_headcount_time_sources(
                conn,
                source_dir,
                fiscal_year,
                approved_unknown_files=approved_unknown,
                rejected_unknown_files=rejected_unknown,
                approved_name_files=approved_names,
                scan_results=review["results"],
            )
        except Exception as exc:
            self.log(f"Cập nhật nguồn nhân sự thất bại: {exc}")
            messagebox.showerror("Cập nhật thất bại", str(exc))
            return
        finally:
            if conn is not None:
                conn.close()
        for parsed, reason in result["skipped"]:
            self.log(f"Không nạp {os.path.basename(parsed.path)}: {reason}")
        for parsed in result["errors"]:
            self.log(f"Lỗi {os.path.basename(parsed.path)}: {'; '.join(parsed.errors)}")
        text = (
            f"Đã nạp {result['imported_files']}/{result['files']} phòng • "
            f"{result['imported_rows']} kỳ • cần bổ sung tách Nhân viên/Công nhân "
            f"{result.get('split_required_files', 0)} phòng • bỏ qua {len(result['skipped'])} • "
            f"lỗi {len(result['errors'])} • {datetime.now():%H:%M}"
        )
        self.headcount_source_status.set(text)
        self.log(f"Cập nhật nguồn nhân sự: {text}")
        detail_lines = []
        for parsed, reason in result["skipped"]:
            detail_lines.append(
                f"BỎ QUA: {os.path.basename(parsed.path)}\n"
                f"  CC {parsed.cc_code or 'không đọc được'} - {parsed.department_name or 'không đọc được tên phòng'}\n"
                f"  Lý do: {reason}"
            )
        for parsed in result["errors"]:
            detail_lines.append(
                f"LỖI: {os.path.basename(parsed.path)}\n  {'; '.join(parsed.errors) or 'Tệp không hợp lệ'}"
            )
        confirmed_unknown = result.get("confirmed_unknown_cost_centers", [])
        if confirmed_unknown:
            detail_lines.append(
                "KHUYẾN NGHỊ BỔ SUNG MASTER:\n  "
                + "\n  ".join(
                    f"CC {parsed.cc_code} — {parsed.department_name}" for parsed in confirmed_unknown
                )
            )
        message = text
        if detail_lines:
            message += "\n\nCác tệp cần kiểm tra:\n\n" + "\n\n".join(detail_lines)
        messagebox.showinfo("Đã cập nhật CSDL", message)

    def open_source_order_editor(self):
        source_dir = self.source_dir.get() or BASE_DIR
        if not os.path.isdir(source_dir):
            messagebox.showerror("Lỗi", f"Không tìm thấy thư mục nguồn:\n{source_dir}")
            return

        editor = tk.Toplevel(self.root)
        editor.title("Thứ tự file nguồn")
        editor.geometry("980x520")
        editor.transient(self.root)
        editor.grab_set()

        frame = ttk.Frame(editor, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text=(
                "Mọi tệp Excel được phát hiện đều hiển thị tại đây. Hãy xác nhận loại cho dòng cần xem xét "
                "hoặc bấm Bỏ qua có chủ đích; tệp đã bỏ qua sẽ không được dùng làm nguồn chi phí."
            ),
            wraplength=900,
        ).grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 4))
        summary_var = tk.StringVar()
        ttk.Label(frame, textvariable=summary_var).grid(row=1, column=0, columnspan=6, sticky="w", pady=(0, 8))

        category_labels = {
            code: CATEGORY_DISPLAY_NAMES.get(code, code)
            for code in DEFAULT_DESCRIPTIONS
        }
        category_codes = {label: code for code, label in category_labels.items()}
        status_labels = {
            "recognized": "Đã nhận diện",
            "needs_review": "Cần xác nhận",
            "ignored": "Đã bỏ qua",
        }
        status_codes = {label: code for code, label in status_labels.items()}
        detection_labels = {
            "manifest": "Theo cấu hình đã lưu",
            "structure": "Theo cấu trúc tệp Excel",
            "system_structure": "Theo cấu trúc hệ thống",
            "manual": "Người dùng xác nhận",
            "inventory": "Kiểm kê tên tệp",
        }
        detection_codes = {label: code for code, label in detection_labels.items()}

        def display_manifest_value(column: str, value: object) -> str:
            text = str(value or "")
            if column == "category":
                return category_labels.get(text, text)
            if column == "status":
                return status_labels.get(text, text)
            if column == "detection_method":
                return detection_labels.get(text, text)
            return text

        def internal_manifest_value(column: str, value: object) -> str:
            text = str(value or "")
            if column == "category":
                return category_codes.get(text, text)
            if column == "status":
                return status_codes.get(text, text)
            if column == "detection_method":
                return detection_codes.get(text, text)
            return text

        columns = MANIFEST_COLUMNS
        tree_frame = ttk.Frame(frame)
        tree_frame.grid(row=2, column=0, columnspan=6, sticky="nsew")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=13)
        headings = {
            "order": "Thứ tự", "category": "Loại nguồn", "filename": "Tên file",
            "enabled": "Dùng", "description": "Ghi chú", "status": "Trạng thái",
            "detection_method": "Cách nhận diện", "signature": "Dấu vết", "reason": "Lý do / bằng chứng",
        }
        widths = {"order": 55, "category": 145, "filename": 330, "enabled": 50,
                  "description": 180, "status": 105, "detection_method": 165,
                  "signature": 90, "reason": 340}
        for column in columns:
            tree.heading(column, text=headings[column])
            tree.column(column, width=widths[column], anchor="center" if column in {"order", "enabled", "status"} else "w")
        tree.grid(row=0, column=0, sticky="nsew")

        vertical_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=tree.xview)
        horizontal_scrollbar.grid(row=1, column=0, sticky="ew")
        tree.configure(
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        form = ttk.Frame(frame)
        form.grid(row=3, column=0, columnspan=6, sticky="ew", pady=(10, 0))
        ttk.Label(form, text="Loại nguồn").grid(row=0, column=0, sticky="w")
        category_var = tk.StringVar()
        category_combo = ttk.Combobox(
            form,
            textvariable=category_var,
            values=[""] + list(category_labels.values()),
            width=22,
            state="readonly",
        )
        category_combo.grid(row=1, column=0, sticky="w", padx=(0, 8))

        ttk.Label(form, text="Tên file").grid(row=0, column=1, sticky="w")
        filename_var = tk.StringVar()
        ttk.Entry(form, textvariable=filename_var, width=70).grid(row=1, column=1, sticky="w")
        ttk.Button(
            form,
            text="Chọn file...",
            command=lambda: browse_manifest_file(),
        ).grid(row=1, column=2, sticky="w", padx=(6, 8))

        enabled_var = tk.IntVar(value=1)
        ttk.Checkbutton(form, text="Dùng dòng này", variable=enabled_var).grid(row=1, column=3, sticky="w")

        ttk.Label(form, text="Ghi chú").grid(row=2, column=0, sticky="w", pady=(8, 0))
        description_var = tk.StringVar()
        ttk.Entry(form, textvariable=description_var, width=96).grid(
            row=3, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )

        def rows_from_tree() -> list[dict[str, str]]:
            rows: list[dict[str, str]] = []
            for index, item_id in enumerate(tree.get_children(), start=1):
                values = tree.item(item_id, "values")
                rows.append({
                    column: internal_manifest_value(column, values[column_index])
                    for column_index, column in enumerate(columns)
                    if column_index < len(values)
                })
                rows[-1]["order"] = str(index)
            return rows

        def refresh_order_numbers() -> None:
            for index, item_id in enumerate(tree.get_children(), start=1):
                values = list(tree.item(item_id, "values"))
                values[0] = str(index)
                tree.item(item_id, values=values)

        def update_summary() -> None:
            counts = {status: 0 for status in ("recognized", "needs_review", "ignored")}
            for item_id in tree.get_children():
                displayed_status = str(tree.item(item_id, "values")[5]).strip()
                status = internal_manifest_value("status", displayed_status).lower()
                if status in counts:
                    counts[status] += 1
            summary_var.set(
                f"Tổng {sum(counts.values())} file | Đã nhận diện: {counts['recognized']} | "
                f"Cần xác nhận: {counts['needs_review']} | Đã bỏ qua: {counts['ignored']}"
            )

        def load_rows() -> None:
            for item_id in tree.get_children():
                tree.delete(item_id)
            for row in read_source_manifest_inventory_fast(source_dir):
                tree.insert(
                    "",
                    tk.END,
                    values=tuple(
                        display_manifest_value(column, row.get(column, ""))
                        for column in columns
                    ),
                )
            refresh_order_numbers()
            update_summary()

        def selected_item() -> str | None:
            selection = tree.selection()
            return selection[0] if selection else None

        def fill_form_from_selection(_event=None) -> None:
            item_id = selected_item()
            if not item_id:
                return
            values = tree.item(item_id, "values")
            category_var.set(str(values[1]))
            filename_var.set(str(values[2]))
            enabled_var.set(1 if str(values[3]).strip() not in {"0", "False", "false"} else 0)
            description_var.set(str(values[4]))

        def browse_manifest_file() -> None:
            path = filedialog.askopenfilename(
                initialdir=source_dir,
                filetypes=[("Tệp Excel", "*.xlsx *.xls"), ("Tất cả tệp", "*.*")],
            )
            if not path:
                return
            try:
                filename_var.set(os.path.relpath(path, source_dir))
            except ValueError:
                filename_var.set(os.path.basename(path))

        def add_or_update() -> None:
            category_label = category_var.get().strip()
            category = category_codes.get(category_label, category_label)
            filename = filename_var.get().strip()
            if not category or not filename:
                messagebox.showwarning("Thiếu dữ liệu", "Hãy chọn loại nguồn và tên file. Muốn bỏ qua hãy bấm nút Bỏ qua.")
                return
            description = description_var.get().strip() or DEFAULT_DESCRIPTIONS.get(category, "")
            enabled = "1" if enabled_var.get() else "0"
            displayed_category = category_labels.get(category, category)
            item_id = selected_item()
            if item_id:
                values = list(tree.item(item_id, "values"))
                values[1:5] = [displayed_category, filename, enabled, description]
                values[5] = status_labels["recognized"]
                values[6] = detection_labels["manual"]
                values[8] = "Người dùng đã xác nhận loại nguồn này."
                tree.item(item_id, values=values)
            else:
                tree.insert(
                    "",
                    tk.END,
                    values=(
                        "", displayed_category, filename, enabled, description,
                        status_labels["recognized"], detection_labels["manual"], "",
                        "Người dùng đã xác nhận loại nguồn này.",
                    ),
                )
            refresh_order_numbers()
            update_summary()

        def ignore_selected() -> None:
            item_id = selected_item()
            if not item_id:
                messagebox.showwarning("Chưa chọn file", "Chọn một dòng cần bỏ qua trước.")
                return
            values = list(tree.item(item_id, "values"))
            values[1] = ""
            values[3] = "0"
            values[5] = status_labels["ignored"]
            values[6] = detection_labels["manual"]
            values[8] = "Người dùng đã chủ động bỏ qua; file vẫn được lưu trong danh sách để truy vết."
            tree.item(item_id, values=values)
            update_summary()

        def remove_selected() -> None:
            item_id = selected_item()
            if item_id:
                tree.delete(item_id)
                refresh_order_numbers()
                update_summary()

        def move_selected(delta: int) -> None:
            item_id = selected_item()
            if not item_id:
                return
            siblings = list(tree.get_children())
            current_index = siblings.index(item_id)
            target_index = current_index + delta
            if target_index < 0 or target_index >= len(siblings):
                return
            tree.move(item_id, "", target_index)
            tree.selection_set(item_id)
            refresh_order_numbers()

        def save_manifest() -> None:
            try:
                saved_path = write_source_manifest_xlsx(source_dir, rows_from_tree())
                self.log(f"Đã lưu thứ tự file nguồn: {saved_path}")
                messagebox.showinfo("Đã lưu", f"Đã lưu cấu hình:\n{saved_path}")
                self._mark_preflight_stale(force_refresh=True)
            except Exception as exc:
                messagebox.showerror("Lỗi", f"Không lưu được thứ tự file nguồn:\n{exc}")

        tree.bind("<<TreeviewSelect>>", fill_form_from_selection)
        load_rows()

        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=6, sticky="w", pady=(10, 0))
        ttk.Button(buttons, text="Thêm/Cập nhật", command=add_or_update).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(buttons, text="Xác nhận loại", command=add_or_update).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(buttons, text="Bỏ qua file", command=ignore_selected).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(buttons, text="Xóa dòng", command=remove_selected).grid(row=0, column=3, padx=(0, 6))
        ttk.Button(buttons, text="Lên", command=lambda: move_selected(-1)).grid(row=0, column=4, padx=(0, 6))
        ttk.Button(buttons, text="Xuống", command=lambda: move_selected(1)).grid(row=0, column=5, padx=(0, 6))
        ttk.Button(buttons, text="Lưu", command=save_manifest).grid(row=0, column=6, padx=(0, 6))
        ttk.Button(buttons, text="Đóng", command=editor.destroy).grid(row=0, column=7, padx=(0, 6))

        frame.rowconfigure(2, weight=1)
        frame.columnconfigure(2, weight=1)

    def load_cc_list(self):
        db_path = self._operational_database()

        if not os.path.exists(db_path):
            self.log("Chưa có dữ liệu nền. Hãy bấm 'Nạp lại CC từ FORM'.")
            return

        try:
            conn = get_connection(db_path)
            rows = conn.execute("SELECT code, name_jp FROM dim_cost_centers ORDER BY code").fetchall()
            if not rows:
                conn.close()
                self.cc_combo["values"] = []
                self.log("Danh sách CC trong DB đang trống. Hãy bấm 'Nạp lại CC từ FORM'.")
                return

            self.cc_combo["values"] = [f"{row['code']} - {row['name_jp']}" for row in rows]
            conn.close()
        except Exception as exc:
            self.log(f"Lỗi khi nạp danh sách CC: {exc}")

    def refresh_cost_centers_from_form(self):
        """Refresh existing CCs, or seed an empty master from the selected FORM."""
        db_path = self._operational_database()
        conn = None
        self.refresh_btn.configure(state=tk.DISABLED)
        try:
            conn = get_connection(db_path)
            create_schema(conn)
            current_count = int(conn.execute("SELECT COUNT(*) FROM dim_cost_centers").fetchone()[0])
            if current_count:
                rows = conn.execute(
                    "SELECT code, name_jp FROM dim_cost_centers ORDER BY code"
                ).fetchall()
                self.cc_combo["values"] = [f"{row['code']} - {row['name_jp']}" for row in rows]
                self.log(f"Đã làm mới danh sách {current_count} Trung tâm chi phí từ CSDL.")
                return

            template = self.template_path.get().strip()
            template_error = _validate_selected_template(template, self._current_fiscal_year())
            if template_error:
                raise ValueError(template_error)

            loaded_count = load_cost_centers(conn, template)
            if loaded_count <= 0:
                raise RuntimeError("FORM không chứa Trung tâm chi phí hợp lệ để nạp vào CSDL.")

            rows = conn.execute(
                "SELECT code, name_jp FROM dim_cost_centers ORDER BY code"
            ).fetchall()
            self.cc_combo["values"] = [f"{row['code']} - {row['name_jp']}" for row in rows]
            self.log(f"Đã nạp {loaded_count} Trung tâm chi phí từ FORM và làm mới danh sách.")
            messagebox.showinfo(
                "Nạp Trung tâm chi phí thành công",
                f"Đã nạp {loaded_count} Trung tâm chi phí từ:\n{template}",
            )
        except Exception as exc:
            message = _friendly_error_message(exc)
            self.log(f"Không thể nạp Trung tâm chi phí từ FORM: {message}")
            messagebox.showerror("Không thể nạp Trung tâm chi phí", message)
        finally:
            if conn is not None:
                conn.close()
            self.refresh_btn.configure(state=tk.NORMAL)

    def auto_init_master_data(self):
        """Automatically load master data if FORM.xlsx is available in current dir."""
        if self.syncing_master: return
        
        template = self.template_path.get()
        if not os.path.exists(template):
            template = _default_template_path()
            if not os.path.exists(template):
                return

        self.syncing_master = True
        self.log("--- TỰ ĐỘNG KHỞI TẠO DỮ LIỆU ---")
        self.log(f"Tệp mẫu đang dùng: {template}")
        self.log(f"Thư mục nguồn đang dùng: {self.source_dir.get() or BASE_DIR}")
        
        def run_sync():
            try:
                db_path = self._operational_database()
                load_all(db_path=db_path, template_path=template)
                self.log("Tự động nạp dữ liệu gốc THÀNH CÔNG.")
                self._run_on_ui_thread(lambda: self.root.after(100, self.load_cc_list))
            except Exception as e:
                self.log(f"Tự động nạp dữ liệu thất bại: {e}")
            finally:
                self._run_on_ui_thread(setattr, self, "syncing_master", False)

        threading.Thread(target=run_sync, daemon=True).start()

    def _get_cc_choices(self):
        db_path = self._operational_database()
        if not os.path.exists(db_path):
            return []
        conn = get_connection(db_path)
        try:
            rows = conn.execute("SELECT code, name_jp FROM dim_cost_centers ORDER BY code").fetchall()
            return [f"{row['code']} - {row['name_jp']}" for row in rows]
        finally:
            conn.close()

    def _read_manual_headcount_rows(self, csv_path: str):
        if not os.path.exists(csv_path):
            return []
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _write_manual_headcount_rows(self, csv_path: str, rows):
        fieldnames = [
            "cc_code",
            "period",
            "headcount_staff",
            "headcount_worker",
            "headcount_male",
            "headcount_female",
            "description",
        ]
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _read_csv_rows(self, csv_path: str):
        if not os.path.exists(csv_path):
            return []
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _write_csv_rows(self, csv_path: str, fieldnames, rows):
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _read_manual_bus_headcount_rows(self, csv_path: str):
        rows = self._read_csv_rows(csv_path)
        return [
            {column: str(row.get(column, "") or "").strip() for column in BUS_DRIVER_COLUMNS}
            for row in rows
        ]

    def _write_manual_bus_headcount_rows(self, csv_path: str, rows):
        self._write_csv_rows(csv_path, BUS_DRIVER_COLUMNS, rows)

    def open_user_guide(self):
        guide = tk.Toplevel(self.root)
        guide.title("Hướng dẫn trực quan")
        guide.geometry("920x700")
        guide.minsize(760, 560)

        frame = ttk.Frame(guide, padding=14)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Hướng dẫn trực quan", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            frame,
            text="Bắt đầu bằng sơ đồ 5 bước; mở thẻ Tra cứu chi tiết khi cần tìm một nghiệp vụ cụ thể.",
        ).pack(anchor="w", pady=(2, 10))

        notebook = ttk.Notebook(frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        quick = ttk.Frame(notebook, padding=14)
        details = ttk.Frame(notebook, padding=8)
        notebook.add(quick, text="Bắt đầu nhanh 1 → 5")
        notebook.add(details, text="Tra cứu chi tiết")

        diagram = tk.Canvas(quick, height=210, bg="#f7f9fc", highlightthickness=1, highlightbackground="#d7deea")
        diagram.pack(fill="x")
        steps = (
            ("1", "CHỌN NĂM", "Ví dụ: FY2028"),
            ("2", "CHỌN NGUỒN", "FORM + 2 thư mục"),
            ("3", "KIỂM TRA", "Đọc màu trạng thái"),
            ("4", "BỔ SUNG", "Nếu nghiệp vụ có"),
            ("5", "CHẠY", "Thử 1 phòng trước"),
        )

        def draw_diagram(_event=None):
            diagram.delete("all")
            width = max(diagram.winfo_width(), 760)
            margin = 70
            gap = (width - margin * 2) / 4
            centers = [margin + gap * index for index in range(5)]
            for index in range(4):
                diagram.create_line(centers[index] + 28, 70, centers[index + 1] - 28, 70, fill="#6b82a6", width=3, arrow=tk.LAST)
            colors = ("#2457a6", "#2457a6", "#176b4d", "#5c3b8c", "#b56a00")
            for center, color, (number, title, subtitle) in zip(centers, colors, steps):
                diagram.create_oval(center - 28, 42, center + 28, 98, fill=color, outline="")
                diagram.create_text(center, 70, text=number, fill="white", font=("Segoe UI", 16, "bold"))
                diagram.create_text(center, 125, text=title, fill="#1f344d", font=("Segoe UI", 9, "bold"))
                diagram.create_text(center, 148, text=subtitle, fill="#556273", font=("Segoe UI", 8))
            diagram.create_text(width / 2, 185, text="Không cần nhớ mọi thứ: làm từ trái sang phải và đọc dòng “Việc cần làm tiếp theo” trên màn hình chính.", fill="#33455d", font=("Segoe UI", 9, "italic"))

        diagram.bind("<Configure>", draw_diagram)

        ttk.Label(quick, text="Hiểu màu trước khi bấm chạy", style="WorkflowTitle.TLabel").pack(anchor="w", pady=(14, 8))
        legend = ttk.Frame(quick)
        legend.pack(fill="x")
        legend_items = (
            ("#dff4ea", "#176b4d", "XANH — Có thể chạy", "Nguồn đã đủ và đúng năm."),
            ("#fff1cf", "#855b00", "VÀNG — Có thể cân nhắc chạy", "Thiếu nguồn độc lập; kết quả sẽ được đánh dấu CHƯA ĐẦY ĐỦ."),
            ("#fde4e1", "#9b2c24", "ĐỎ — Chưa được chạy", "Sai năm, sai FORM, lỗi nguồn bắt buộc hoặc dữ liệu không đọc được."),
        )
        for column, (background, foreground, title, body) in enumerate(legend_items):
            legend.columnconfigure(column, weight=1, uniform="legend")
            card = tk.Frame(legend, bg=background, highlightthickness=1, highlightbackground=foreground)
            card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 6, 0), ipadx=8, ipady=8)
            tk.Label(card, text=title, bg=background, fg=foreground, font=("Segoe UI", 9, "bold"), wraplength=230, justify="left").pack(anchor="w")
            tk.Label(card, text=body, bg=background, fg=foreground, font=("Segoe UI", 8), wraplength=230, justify="left").pack(anchor="w", pady=(4, 0))

        tip = tk.Frame(quick, bg="#e8f1ff", highlightthickness=1, highlightbackground="#6b82a6")
        tip.pack(fill="x", pady=(14, 0), ipady=8)
        tk.Label(tip, text="MẸO AN TOÀN", bg="#e8f1ff", fg="#2457a6", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10)
        tk.Label(tip, text="Chạy thử một Trung tâm chi phí, mở tệp kết quả để đối chiếu, sau đó mới chạy toàn bộ.", bg="#e8f1ff", fg="#2457a6", font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(2, 0))

        guide_text = scrolledtext.ScrolledText(details, wrap=tk.WORD, font=("Segoe UI", 10))
        guide_text.pack(fill=tk.BOTH, expand=True)
        guide_text.insert("1.0", USER_GUIDE_TEXT_LATEST)
        guide_text.configure(state=tk.DISABLED)

        ttk.Button(frame, text="Đã hiểu — Đóng", command=guide.destroy).pack(anchor="e", pady=(10, 0))

    def open_run_history(self):
        history_root = self._project_paths().history_root
        dialog = tk.Toplevel(self.root)
        dialog.title("Lịch sử các lần chạy")
        dialog.geometry("1180x620")
        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        fiscal_var = tk.StringVar(value=str(self._current_fiscal_year()))
        status_labels = {
            "": "Tất cả",
            "PRECHECK_FAILED": "Chưa chạy — nguồn chưa đạt",
            "RUNNING": "Đang chạy",
            "SUCCEEDED": "Hoàn tất",
            "SUCCEEDED_INCOMPLETE": "Hoàn tất — chưa đầy đủ",
            "FAILED": "Không hoàn tất",
            "LEGACY_FY2027": "Dữ liệu lịch sử FY2027",
        }
        status_values = {label: code for code, label in status_labels.items()}
        status_var = tk.StringVar(value="Tất cả")
        cc_var = tk.StringVar()
        item_var = tk.StringVar()
        date_var = tk.StringVar()
        filters = ttk.Frame(frame)
        filters.pack(fill=tk.X, pady=(0, 8))
        for index, (label, variable, width) in enumerate((
            ("Năm tài chính", fiscal_var, 10),
            ("Trạng thái", status_var, 18),
            ("Mã phòng", cc_var, 16),
            ("Hạng mục", item_var, 18),
            ("Ngày chạy", date_var, 16),
        )):
            ttk.Label(filters, text=label).grid(row=0, column=index * 2, sticky="w", padx=(0 if index == 0 else 8, 3))
            if label == "Trạng thái":
                widget = ttk.Combobox(
                    filters,
                    textvariable=variable,
                    width=width,
                    state="readonly",
                    values=tuple(status_values),
                )
            else:
                widget = ttk.Entry(filters, textvariable=variable, width=width)
            widget.grid(row=0, column=index * 2 + 1, sticky="w")
        columns = ("run_id", "status", "started_at", "finished_at", "selected_cost_center", "output_path", "error_summary")
        table = ttk.Treeview(frame, columns=columns, show="headings")
        widths = {"run_id": 170, "status": 170, "started_at": 150, "finished_at": 150, "selected_cost_center": 120, "output_path": 210, "error_summary": 260}
        labels = {"run_id": "Mã lần chạy", "status": "Trạng thái", "started_at": "Bắt đầu", "finished_at": "Kết thúc", "selected_cost_center": "Mã phòng", "output_path": "Kết quả", "error_summary": "Ghi chú"}
        for column in columns:
            table.heading(column, text=labels[column])
            table.column(column, width=widths[column], stretch=True)
        table.pack(fill=tk.BOTH, expand=True)
        selected_rows: dict[str, dict[str, object]] = {}

        def render_rows(rows: list[dict[str, object]]) -> None:
            if not dialog.winfo_exists():
                return
            for node in table.get_children():
                table.delete(node)
            selected_rows.clear()
            for row in rows:
                values = [
                    status_labels.get(str(row.get(column) or ""), str(row.get(column) or ""))
                    if column == "status" else str(row.get(column) or "")
                    for column in columns
                ]
                node = table.insert("", tk.END, values=values)
                selected_rows[node] = row

        filter_button = None
        filter_token = {"value": 0}

        def finish_refresh(token: int, rows=None, error: Exception | None = None) -> None:
            if not dialog.winfo_exists() or token != filter_token["value"]:
                return
            if error is None:
                render_rows(rows or [])
            else:
                messagebox.showerror(
                    "Không đọc được lịch sử",
                    str(error),
                    parent=dialog,
                )
            if filter_button is not None:
                filter_button.configure(state=tk.NORMAL, text="Lọc")

        def refresh():
            nonlocal filter_button
            try:
                fiscal_year = int(fiscal_var.get()) if fiscal_var.get().strip() else None
            except ValueError:
                messagebox.showerror("Bộ lọc không hợp lệ", "Năm tài chính phải là số.", parent=dialog)
                return

            filter_token["value"] += 1
            token = filter_token["value"]
            criteria = {
                "status": status_values.get(status_var.get(), ""),
                "cost_center": cc_var.get().strip(),
                "item": item_var.get().strip(),
                "run_date": date_var.get().strip(),
            }
            if filter_button is not None:
                filter_button.configure(state=tk.DISABLED, text="Đang lọc…")

            def worker() -> None:
                try:
                    rows = filter_runs(history_root, fiscal_year, **criteria)
                except Exception as exc:
                    self._run_on_ui_thread(finish_refresh, token, None, exc)
                else:
                    self._run_on_ui_thread(finish_refresh, token, rows, None)

            threading.Thread(target=worker, daemon=True).start()

        def selected() -> dict[str, object] | None:
            nodes = table.selection()
            return selected_rows.get(nodes[0]) if nodes else None

        def open_path(path: str):
            if not path or not os.path.exists(path):
                messagebox.showerror("Không tìm thấy", "Tệp hoặc thư mục của lần chạy này không còn tồn tại.", parent=dialog)
                return
            os.startfile(path)  # type: ignore[attr-defined]

        def open_output():
            row = selected()
            if row:
                open_path(str(row.get("output_path") or ""))

        def open_run_file(relative: str):
            row = selected()
            if not row:
                return
            database_path = str(row.get("database_path") or "")
            workspace = os.path.dirname(database_path) if database_path else ""
            open_path(os.path.join(workspace, relative))

        filter_button = ttk.Button(filters, text="Lọc", command=refresh)
        filter_button.grid(row=0, column=10, padx=(12, 0))
        actions = ttk.Frame(frame)
        actions.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(actions, text="Mở kết quả", command=open_output).pack(side=tk.LEFT)
        ttk.Button(actions, text="Báo cáo kiểm tra", command=lambda: open_run_file(os.path.join("reports", "preflight_report.md"))).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="Nhật ký đồng phục", command=lambda: open_run_file("run.db")).pack(side=tk.LEFT)
        ttk.Button(actions, text="Nhật ký tài sản", command=lambda: open_run_file("run.db")).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="Mở CSDL lần chạy", command=lambda: open_run_file("run.db")).pack(side=tk.LEFT)
        refresh()
        ttk.Label(frame, text="Lịch sử chỉ để tra cứu; không thể sửa dữ liệu của lần chạy cũ.").pack(anchor="w", pady=(8, 0))

    def open_headcount_editor(self):
        try:
            fiscal_year = int(self.fiscal_year.get())
        except Exception:
            fiscal_year = 2027

        source_dir = resolve_manual_headcount_source_dir(self.source_dir.get() or BASE_DIR, base_dir=BASE_DIR)
        os.makedirs(source_dir, exist_ok=True)
        csv_path = ensure_manual_headcount_template(source_dir, fiscal_year)

        editor = tk.Toplevel(self.root)
        editor.title("Nhập liệu nhân sự thủ công")
        editor.geometry("1020x600")

        frame = ttk.Frame(editor, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=f"Tệp lưu dữ liệu: {csv_path}", font=("Segoe UI", 9, "italic")).grid(
            row=0, column=0, columnspan=6, sticky="w"
        )

        cc_var = tk.StringVar()
        period_var = tk.StringVar()
        staff_var = tk.StringVar()
        worker_var = tk.StringVar()
        desc_var = tk.StringVar()

        cc_choices = self._get_cc_choices()
        periods = get_required_headcount_periods(fiscal_year)

        ttk.Label(frame, text="Mã CC").grid(row=1, column=0, sticky="w", pady=5)
        cc_combo = ttk.Combobox(frame, textvariable=cc_var, values=cc_choices, width=34)
        cc_combo.grid(row=1, column=1, sticky="w")

        ttk.Label(frame, text="Kỳ (Tháng)").grid(row=1, column=2, sticky="w", pady=5, padx=(8, 0))
        period_combo = ttk.Combobox(frame, textvariable=period_var, values=periods, width=12)
        period_combo.grid(row=1, column=3, sticky="w")

        ttk.Label(frame, text="Nhân viên").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=staff_var, width=14).grid(row=2, column=1, sticky="w")
        ttk.Label(frame, text="Công nhân").grid(row=2, column=2, sticky="w", pady=5, padx=(8, 0))
        ttk.Entry(frame, textvariable=worker_var, width=14).grid(row=2, column=3, sticky="w")

        ttk.Label(frame, text="Mô tả").grid(row=3, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=desc_var, width=66).grid(row=3, column=1, columnspan=4, sticky="w")

        columns = ("cc_code", "period", "headcount_staff", "headcount_worker", "description")
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=18)
        for col, width, anchor, text in [
            ("cc_code", 130, "w", "Mã CC"),
            ("period", 100, "w", "Kỳ"),
            ("headcount_staff", 130, "w", "Nhân viên"),
            ("headcount_worker", 130, "w", "Công nhân"),
            ("description", 470, "w", "Mô tả"),
        ]:
            tree.heading(col, text=text)
            tree.column(col, width=width, anchor=anchor)
        tree.grid(row=5, column=0, columnspan=6, sticky="nsew", pady=(10, 0))

        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=5, column=6, sticky="ns", pady=(10, 0))

        frame.rowconfigure(5, weight=1)
        frame.columnconfigure(5, weight=1)

        def parse_cc_code(text: str) -> str:
            raw = (text or "").strip()
            if " - " in raw:
                raw = raw.split(" - ")[0].strip()
            return raw

        def clear_inputs():
            cc_var.set("")
            period_var.set("")
            staff_var.set("")
            worker_var.set("")
            desc_var.set("")

        def load_rows():
            for item in tree.get_children():
                tree.delete(item)
            if not os.path.exists(csv_path):
                return
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tree.insert(
                        "",
                        tk.END,
                        values=(
                            str(row.get("cc_code", "")).strip(),
                            str(row.get("period", "")).strip(),
                            str(row.get("headcount_staff", "")).strip(),
                            str(row.get("headcount_worker", "")).strip(),
                            str(row.get("description", "")).strip(),
                        ),
                    )

        def add_or_update():
            cc_code = parse_cc_code(cc_var.get())
            period = period_var.get().strip()
            staff = staff_var.get().strip() or "0"
            worker = worker_var.get().strip() or "0"
            desc = desc_var.get().strip()
            if not cc_code or not period:
                messagebox.showerror("Lỗi", "Yêu cầu nhập Mã CC và Kỳ.")
                return
            try:
                int(float(cc_code))
                float(staff)
                float(worker)
            except Exception:
                messagebox.showerror("Lỗi", "Giá trị số không hợp lệ.")
                return
            selected = tree.selection()
            row_values = (cc_code, period, staff, worker, desc)
            if selected:
                tree.item(selected[0], values=row_values)
            else:
                tree.insert("", tk.END, values=row_values)
            clear_inputs()

        def remove_selected():
            selected = tree.selection()
            for item in selected:
                tree.delete(item)

        def on_select(_event):
            selected = tree.selection()
            if not selected:
                return
            values = tree.item(selected[0], "values")
            if not values:
                return
            cc_var.set(values[0])
            period_var.set(values[1])
            staff_var.set(values[2])
            worker_var.set(values[3])
            desc_var.set(values[4])

        def save_file():
            rows = []
            for item in tree.get_children():
                val = tree.item(item, "values")
                rows.append(
                    {
                        "cc_code": val[0],
                        "period": val[1],
                        "headcount_staff": val[2],
                        "headcount_worker": val[3],
                        "description": val[4],
                    }
                )
            with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["cc_code", "period", "headcount_staff", "headcount_worker", "description"],
                )
                writer.writeheader()
                writer.writerows(rows)
            db_path = self._operational_database()
            conn = get_connection(db_path)
            try:
                create_schema(conn)
                result = parse_manual_headcount(conn, source_dir=source_dir)
            finally:
                conn.close()
            self.log(
                "Đã lưu nhân sự thủ công: {rows} hàng -> {path}; đã nạp vào dữ liệu={inserted}, lỗi={errors}".format(
                    rows=len(rows),
                    path=csv_path,
                    inserted=result.get("inserted", 0),
                    errors=result.get("errors", 0),
                )
            )
            messagebox.showinfo(
                "Đã lưu",
                "Đã lưu {rows} hàng. Đã nạp vào dữ liệu={inserted}, lỗi={errors}.".format(
                    rows=len(rows),
                    inserted=result.get("inserted", 0),
                    errors=result.get("errors", 0),
                ),
            )

        btn = ttk.Frame(frame)
        btn.grid(row=4, column=0, columnspan=6, sticky="w", pady=(6, 0))
        ttk.Button(btn, text="Thêm/Cập nhật", command=add_or_update).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(btn, text="Xóa đã chọn", command=remove_selected).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(btn, text="Lưu tệp", command=save_file).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(btn, text="Đóng", command=editor.destroy).grid(row=0, column=3, padx=(0, 6))

        tree.bind("<<TreeviewSelect>>", on_select)
        load_rows()

    def open_headcount_editor_v2(self, selected_cc=None):
        try:
            fiscal_year = int(self.fiscal_year.get())
        except Exception:
            fiscal_year = 2027
        periods = get_required_headcount_periods(fiscal_year)
        fy_periods = set(get_fy_months(fiscal_year))
        editor = tk.Toplevel(self.root)
        editor.title("Nhập liệu nhân sự 12 tháng")
        editor.geometry("1180x800")
        frame = ttk.Frame(editor, padding=10); frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Số nhân viên, công nhân và tổng người của 12 tháng FY lấy từ kế hoạch phòng ban. Nam/Nữ là dữ liệu bổ sung. Baseline T3 được nhập riêng để tính chi phí tháng 4.", font=("Segoe UI",9,"italic")).pack(anchor="w")
        top = ttk.Frame(frame); top.pack(fill="x", pady=8)
        ttk.Label(top,text="Mã CC").pack(side="left")
        cc_var=tk.StringVar(); cc_combo=ttk.Combobox(top,textvariable=cc_var,values=self._get_cc_choices(),width=42,state="readonly"); cc_combo.pack(side="left",padx=6)
        source_status=tk.StringVar(value="Chưa có dữ liệu nguồn"); ttk.Label(top,textvariable=source_status).pack(side="left",padx=8)
        bus_exp=tk.StringVar(value="0"); bus_vn=tk.StringVar(value="0"); bus_note=tk.StringVar()
        bus=ttk.LabelFrame(frame,text="Thông tin xe buýt — nhập riêng, dùng chung cho 12 tháng"); bus.pack(fill="x",pady=(0,8))
        for label,var in (("Người biệt phái đi xe buýt",bus_exp),("Người Việt Nam đi xe buýt",bus_vn)):
            ttk.Label(bus,text=label).pack(side="left",padx=(8,4)); ttk.Entry(bus,textvariable=var,width=10).pack(side="left")
        ttk.Label(bus,text="Ghi chú").pack(side="left",padx=(12,4)); ttk.Entry(bus,textvariable=bus_note).pack(side="left",fill="x",expand=True,padx=(0,8))
        notebook=ttk.Notebook(frame); notebook.pack(fill="both",expand=True)
        people=ttk.Frame(notebook,padding=6); fixed=ttk.Frame(notebook,padding=6); overtime=ttk.Frame(notebook,padding=6)
        notebook.add(people,text="Số người & bổ sung"); notebook.add(fixed,text="Thời gian cố định"); notebook.add(overtime,text="Thời gian tăng ca")
        fields=("expat","staff","worker","male","female","total","note"); month_vars={p:{f:tk.StringVar() for f in fields} for p in periods}
        headers=("Kỳ","JP","Nhân viên","Công nhân","Nam (T12)","Nữ (T12)","Tổng người","Ghi chú")
        for col,label in enumerate(headers): ttk.Label(people,text=label).grid(row=0,column=col,sticky="w",padx=3)
        def update_total(period):
            vals=month_vars[period]
            try: total=sum(float(vals[k].get() or 0) for k in ("expat","staff","worker")); vals["total"].set(f"{total:g}")
            except ValueError: vals["total"].set("?")
        for row,period in enumerate(periods,1):
            label=f"Tháng {int(period[-2:])}" if period in fy_periods else f"Baseline T3 ({period})"
            ttk.Label(people,text=label).grid(row=row,column=0,sticky="w",padx=3,pady=2)
            for col,key,width in ((1,"expat",9),(2,"staff",11),(3,"worker",11),(4,"male",10),(5,"female",10)):
                entry=ttk.Entry(people,textvariable=month_vars[period][key],width=width); entry.grid(row=row,column=col,padx=3,pady=2)
                if key in ("expat","staff","worker") and period in fy_periods: entry.state(["readonly"])
                if key in ("male","female") and not period.endswith("12"): entry.state(["disabled"])
                if key in ("expat","staff","worker"): month_vars[period][key].trace_add("write",lambda *_args,p=period:update_total(p))
            total=ttk.Entry(people,textvariable=month_vars[period]["total"],width=11,state="readonly"); total.grid(row=row,column=6,padx=3)
            ttk.Entry(people,textvariable=month_vars[period]["note"],width=42).grid(row=row,column=7,sticky="ew",padx=3)
            if period not in fy_periods:
                ttk.Label(people,text="Dùng tính 4 chi phí của tháng 4",foreground="#8A4B08").grid(row=row,column=8,sticky="w",padx=4)
        people.columnconfigure(7,weight=1)
        time_fields=("fixed_hours_expat","fixed_hours_local","overtime_hours_expat","overtime_hours_local")
        time_vars={p:{f:tk.StringVar() for f in time_fields} for p in get_fy_months(fiscal_year)}
        ttk.Label(fixed,text="Có thể để trống; chương trình sẽ lưu 0 giờ.",font=("Segoe UI",9,"italic")).grid(row=0,column=0,columnspan=4,sticky="w",pady=(0,6))
        ttk.Label(overtime,text="Có thể để trống; chương trình sẽ lưu 0 giờ.",font=("Segoe UI",9,"italic")).grid(row=0,column=0,columnspan=4,sticky="w",pady=(0,6))
        for tab in (fixed,overtime):
            for col,label in enumerate(("Kỳ","JP","Người Việt","Tổng giờ")):
                ttk.Label(tab,text=label).grid(row=1,column=col,sticky="w",padx=4)
        def update_time_total(period, kind, total_var):
            jp_key=f"{kind}_hours_expat"; local_key=f"{kind}_hours_local"
            try: total_var.set(f"{float(time_vars[period][jp_key].get() or 0)+float(time_vars[period][local_key].get() or 0):g}")
            except ValueError: total_var.set("?")
        for row,period in enumerate(get_fy_months(fiscal_year),2):
            for tab,kind in ((fixed,"fixed"),(overtime,"overtime")):
                ttk.Label(tab,text=f"Tháng {int(period[-2:])} ({period})").grid(row=row,column=0,sticky="w",padx=4,pady=2)
                jp_key=f"{kind}_hours_expat"; local_key=f"{kind}_hours_local"; total_var=tk.StringVar(value="0")
                ttk.Entry(tab,textvariable=time_vars[period][jp_key],width=18).grid(row=row,column=1,padx=4,pady=2)
                ttk.Entry(tab,textvariable=time_vars[period][local_key],width=18).grid(row=row,column=2,padx=4,pady=2)
                ttk.Entry(tab,textvariable=total_var,width=18,state="readonly").grid(row=row,column=3,padx=4,pady=2)
                time_vars[period][jp_key].trace_add("write",lambda *_args,p=period,k=kind,t=total_var:update_time_total(p,k,t))
                time_vars[period][local_key].trace_add("write",lambda *_args,p=period,k=kind,t=total_var:update_time_total(p,k,t))
        for tab in (fixed,overtime): tab.columnconfigure(4,weight=1)
        def cc_code():
            raw=cc_var.get().strip(); return raw.split(" - ")[0] if " - " in raw else raw
        def clear():
            for vals in month_vars.values():
                for var in vals.values(): var.set("")
            for vals in time_vars.values():
                for var in vals.values(): var.set("")
            bus_exp.set("0"); bus_vn.set("0"); bus_note.set("")
        def load_cc(*_):
            clear(); cc=cc_code()
            if not cc:return
            source_conn = None
            manual_conn = None
            try:
                source_conn=get_connection(self._operational_database()); create_schema(source_conn)
                manual_conn=get_connection(self._manual_input_store(fiscal_year)); create_schema(manual_conn)
                fy_period_list = get_fy_months(fiscal_year)
                period_placeholders = ",".join("?" for _ in fy_period_list)
                source_rows=source_conn.execute(
                    f"""SELECT * FROM fact_monthly_headcount
                    WHERE CAST(cc_code AS TEXT)=? AND source='department_plan'
                    AND period IN ({period_placeholders}) ORDER BY period""",
                    (cc, *fy_period_list),
                ).fetchall()
                manual_periods = periods
                manual_placeholders = ",".join("?" for _ in manual_periods)
                manual={
                    r["period"]:r
                    for r in manual_conn.execute(
                        f"""SELECT * FROM fact_monthly_headcount
                        WHERE CAST(cc_code AS TEXT)=? AND source='manual'
                        AND period IN ({manual_placeholders})""",
                        (cc, *manual_periods),
                    ).fetchall()
                }
                for r in source_rows:
                    if r["period"] in month_vars:
                        v=month_vars[r["period"]]; v["expat"].set(f"{float(r['headcount_expat'] or 0):g}"); v["staff"].set(f"{float(r['headcount_staff'] or 0):g}"); v["worker"].set(f"{float(r['headcount_worker'] or 0):g}")
                for period,r in manual.items():
                    if period in month_vars:
                        v=month_vars[period]
                        if period not in fy_periods:
                            v["expat"].set(f"{float(r['headcount_expat'] or 0):g}"); v["staff"].set(f"{float(r['headcount_staff'] or 0):g}"); v["worker"].set(f"{float(r['headcount_worker'] or 0):g}")
                        v["male"].set(f"{float(r['headcount_male'] or 0):g}" if period.endswith("12") else ""); v["female"].set(f"{float(r['headcount_female'] or 0):g}" if period.endswith("12") else ""); v["note"].set(r["description"] or "")
                busrow=manual_conn.execute(
                    "SELECT * FROM fact_bus_headcount_drivers WHERE cc_code=? AND fiscal_year=?",
                    (cc, fiscal_year),
                ).fetchone()
                if busrow: bus_exp.set(f"{float(busrow['bus_expat_count'] or 0):g}"); bus_vn.set(f"{float(busrow['bus_vietnamese_count'] or 0):g}"); bus_note.set(busrow["description"] or "")
                timerows=source_conn.execute(
                    f"""SELECT * FROM fact_headcount_time_source
                    WHERE CAST(cc_code AS TEXT)=? AND period IN ({period_placeholders}) ORDER BY period""",
                    (cc, *fy_period_list),
                ).fetchall()
                time_overrides={
                    r["period"]: r
                    for r in manual_conn.execute(
                        f"""SELECT * FROM fact_manual_headcount_time_override
                        WHERE fiscal_year=? AND CAST(cc_code AS TEXT)=?
                        AND period IN ({period_placeholders}) ORDER BY period""",
                        (fiscal_year, cc, *fy_period_list),
                    ).fetchall()
                }
                for r in timerows:
                    if r["period"] not in time_vars: continue
                    for key in time_fields:
                        time_vars[r["period"]][key].set(f"{float(r[key] or 0):g}")
                for period,r in time_overrides.items():
                    if period not in time_vars: continue
                    for key in time_fields:
                        time_vars[period][key].set(f"{float(r[key] or 0):g}")
                source_status.set(
                    f"Đã có {len(source_rows)} kỳ nguồn FY{fiscal_year} trong CSDL"
                    if source_rows
                    else f"Chưa có dữ liệu nguồn FY{fiscal_year} cho CC này"
                )
            finally:
                if manual_conn is not None: manual_conn.close()
                if source_conn is not None: source_conn.close()
        def nonneg(text,label):
            value=str(text or "").strip() or "0"
            if not value.isdecimal(): raise ValueError(f"{label} phải là số nguyên không âm")
            return float(value)
        def save():
            cc=cc_code()
            if not cc:return
            try: be=nonneg(bus_exp.get(),"Bus JP"); bv=nonneg(bus_vn.get(),"Bus Việt Nam")
            except ValueError as exc: messagebox.showerror("Dữ liệu không hợp lệ",str(exc)); return
            conn=get_connection(self._manual_input_store(fiscal_year)); create_schema(conn)
            try:
                with conn:
                    conn.execute("INSERT INTO fact_bus_headcount_drivers(cc_code,fiscal_year,bus_expat_count,bus_vietnamese_count,source,description) VALUES(?,?,?,?,'manual',?) ON CONFLICT(cc_code) DO UPDATE SET fiscal_year=excluded.fiscal_year,bus_expat_count=excluded.bus_expat_count,bus_vietnamese_count=excluded.bus_vietnamese_count,description=excluded.description",(cc,fiscal_year,be,bv,bus_note.get().strip()))
                    baseline_period=periods[0]; baseline=month_vars[baseline_period]
                    expat=nonneg(baseline["expat"].get(),f"JP {baseline_period}"); staff=nonneg(baseline["staff"].get(),f"Nhân viên {baseline_period}"); worker=nonneg(baseline["worker"].get(),f"Công nhân {baseline_period}")
                    save_manual_baseline_override(conn,fiscal_year,cc,expat,staff,worker,baseline["note"].get().strip())
                    for period,v in month_vars.items():
                        if period not in fy_periods: continue
                        male=nonneg(v["male"].get(),f"Nam {period}") if period.endswith("12") else 0; female=nonneg(v["female"].get(),f"Nữ {period}") if period.endswith("12") else 0
                        note=v["note"].get().strip()
                        conn.execute("DELETE FROM fact_monthly_headcount WHERE cc_code=? AND period=? AND source='manual'",(cc,period))
                        if male or female or note:
                            conn.execute("INSERT INTO fact_monthly_headcount(period,cc_code,headcount_all,headcount_expat,headcount_staff,headcount_worker,headcount_male,headcount_female,source,description) VALUES(?,?,0,0,0,0,?,?,'manual',?)",(period,cc,male,female,note))
                    save_manual_time_overrides(conn,fiscal_year,cc,{p:{f:v[f].get() for f in time_fields} for p,v in time_vars.items()})
            except ValueError as exc: conn.rollback(); messagebox.showerror("Dữ liệu không hợp lệ",str(exc)); return
            finally: conn.close()
            messagebox.showinfo("Đã lưu","Đã lưu baseline T3, dữ liệu bổ sung, xe buýt và 12 tháng thời gian (ô trống = 0).")
        buttons=ttk.Frame(frame); buttons.pack(fill="x",pady=(8,0)); ttk.Button(buttons,text="Tải dữ liệu CC",command=load_cc).pack(side="left"); ttk.Button(buttons,text="Lưu nhân sự & thời gian",style="Primary.TButton",command=save).pack(side="left",padx=6); ttk.Button(buttons,text="Đóng",command=editor.destroy).pack(side="left")
        cc_combo.bind("<<ComboboxSelected>>",load_cc)
        if cc_combo["values"]:
            initial=selected_cc if selected_cc in cc_combo["values"] else cc_combo["values"][0]
            cc_var.set(initial); load_cc()

    def open_event_driver_editor(self):
        try:
            fiscal_year = int(self.fiscal_year.get())
        except Exception:
            fiscal_year = 2027

        source_dir = self.source_dir.get() or BASE_DIR
        os.makedirs(source_dir, exist_ok=True)
        csv_path = ensure_manual_event_drivers_template(source_dir, fiscal_year)
        periods = get_fy_months(fiscal_year)

        editor = tk.Toplevel(self.root)
        editor.title("Nhập sự kiện thiếu dữ liệu")
        editor.geometry("1260x760")

        frame = ttk.Frame(editor, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=f"Tệp lưu dữ liệu: {csv_path}", font=("Segoe UI", 9, "italic")).grid(
            row=0, column=0, columnspan=8, sticky="w"
        )
        ttk.Label(
            frame,
            text=(
                "Mục này dùng cho khoản tiền mà chương trình không thể tự biết. "
                "Ví dụ: số người đi xe bus, quà không đi du lịch, kỷ niệm 10 năm, VISA/Passport ở dòng FORM khác. "
                "Có thể nhập account_jp_name để tự resolve account_code và unit_price_key để tự lấy đơn giá từ file phân bổ của năm đang chạy. "
                "Nếu không có số thật, hãy để trống; chương trình sẽ không tự bịa số."
            ),
            wraplength=1180,
        ).grid(row=1, column=0, columnspan=8, sticky="w", pady=(4, 6))

        guide = ttk.LabelFrame(frame, text="Cách điền: đọc từ trái sang phải")
        guide.grid(row=2, column=0, columnspan=8, sticky="ew", pady=(0, 10))
        guide.columnconfigure(0, weight=1)
        ttk.Label(
            guide,
            text=(
                "target_month/period = tháng ghi chi phí, ví dụ 202805 là tháng 5 của FY2028.  "
                "event_type có thể dùng month_specific_driver cho event theo tháng riêng.  "
                "Nếu nhập unit_price thì đơn giá nhập tay được ưu tiên; nếu bỏ trống unit_price, nhập unit_price_key/allocation_content để tự lấy đơn giá từ file phân bổ của năm đang chạy.  "
                "Có thể bỏ trống account_code nếu nhập account_jp_name/account_name, ví dụ 福利厚生費.  "
                "row/form_row = dòng FORM cần ghi, ví dụ 66 cho 社員旅行.  "
                "Sample help-only: 1412000089,202705,社員旅行 Du lịch công ty,month_specific_driver,111,社員旅行,福利厚生費,66,Sample: company trip May driver."
            ),
            wraplength=1160,
        ).grid(row=0, column=0, sticky="w", padx=8, pady=(6, 2))
        event_help_var = tk.StringVar(
            value="Gợi ý: hãy nhập số thật từ người phụ trách nghiệp vụ. Không nhập số ước lượng nếu chưa được chốt."
        )
        ttk.Label(
            guide,
            textvariable=event_help_var,
            foreground="#7a3f00",
            wraplength=1160,
        ).grid(row=1, column=0, sticky="w", padx=8, pady=(0, 6))

        cc_var = tk.StringVar()
        period_var = tk.StringVar()
        event_var = tk.StringVar()
        event_type_var = tk.StringVar(value="month_specific_driver")
        count_var = tk.StringVar()
        unit_price_var = tk.StringVar()
        unit_price_key_var = tk.StringVar()
        amount_var = tk.StringVar()
        bus_expat_people_var = tk.StringVar(value="0")
        bus_vietnamese_people_var = tk.StringVar(value="0")
        account_var = tk.StringVar()
        account_jp_name_var = tk.StringVar()
        form_row_var = tk.StringVar()
        desc_var = tk.StringVar()

        cc_choices = self._get_cc_choices()
        event_help = {
            "Cốc xếp định kỳ": "Chỉ dùng cho phòng được đánh dấu cốc xếp; nhập số lượng phát thực tế vào tháng 2 hoặc tháng 8. Nhập 0 nếu xác nhận không phát.",
            "Du lịch công ty": "Dùng khi cần nhập số người/số tiền cho chuyến du lịch công ty.",
            "Quà không đi du lịch": "Dùng cho người không tham gia du lịch nhưng có quà hoặc khoản hỗ trợ riêng.",
            "My Episode": "Dùng khi có khoản My Episode thật trong tháng đó.",
            "Tiệc kỷ niệm 10 năm": "Dùng khi có số người hoặc tổng tiền cho tiệc kỷ niệm 10 năm.",
            "Quà kỷ niệm 10 năm": "Dùng khi có quà kỷ niệm 10 năm theo số người hoặc tổng tiền.",
            "Kỷ niệm công ty": "Dùng cho kỷ niệm công ty khi workbook chưa đủ dữ liệu tự tính.",
            "Xe bus JP": "Dùng khi biết số người hoặc số chuyến xe bus JP.",
            "Xe bus VN": "Dùng khi biết số người hoặc số chuyến xe bus VN.",
            "Triết lý tháng 3 năm trước": "Dùng cho khoản phát sinh tháng 3 FY cũ nhưng cần đưa vào kế hoạch hiện tại.",
            "Sự kiện tháng 4": "Dùng cho sự kiện riêng phát sinh tháng 4 cần người dùng chốt.",
            "VISA/Passport dòng khác 137": "Dùng khi chi phí giấy tờ không đi vào dòng 137 theo cách map hiện tại.",
            "Khác": "Dùng khi khoản cần nhập chưa có trong danh sách. Hãy ghi chú rõ nguồn số liệu.",
        }
        event_choices = [
            "Cốc xếp định kỳ",
            "Du lịch công ty",
            "Quà không đi du lịch",
            "My Episode",
            "Tiệc kỷ niệm 10 năm",
            "Quà kỷ niệm 10 năm",
            "Kỷ niệm công ty",
            "Xe bus JP",
            "Xe bus VN",
            "Triết lý tháng 3 năm trước",
            "Sự kiện tháng 4",
            "VISA/Passport dòng khác 137",
            "Khác",
        ]

        def add_label_entry(row, column, label, variable, width=18, values=None):
            ttk.Label(frame, text=label).grid(row=row, column=column, sticky="w", padx=(0, 4), pady=3)
            if values is None:
                widget = ttk.Entry(frame, textvariable=variable, width=width)
            else:
                widget = ttk.Combobox(frame, textvariable=variable, values=values, width=width, state="readonly")
            widget.grid(row=row, column=column + 1, sticky="w", padx=(0, 12), pady=3)
            return widget

        add_label_entry(3, 0, "Mã CC", cc_var, width=38, values=cc_choices)
        add_label_entry(3, 2, "Tháng ghi chi phí", period_var, width=12, values=periods)
        event_combo = add_label_entry(3, 4, "Sự kiện", event_var, width=28, values=event_choices)
        add_label_entry(
            3,
            6,
            "Loại event",
            event_type_var,
            width=24,
            values=["manual_count_unit_price", "manual_amount", "month_specific_driver"],
        )
        add_label_entry(4, 0, "Số người/count", count_var, width=16)
        add_label_entry(4, 2, "Đơn giá nhập tay", unit_price_var, width=16)
        add_label_entry(4, 4, "Key đơn giá", unit_price_key_var, width=24)
        add_label_entry(4, 6, "Số tiền trực tiếp", amount_var, width=18)
        add_label_entry(5, 0, "Người biệt phái đi xe bus", bus_expat_people_var, width=16)
        add_label_entry(5, 2, "Người Việt Nam đi xe bus", bus_vietnamese_people_var, width=16)
        add_label_entry(6, 0, "Mã tài khoản", account_var, width=16)
        add_label_entry(6, 2, "Tên TK Nhật", account_jp_name_var, width=18)
        add_label_entry(6, 4, "Dòng FORM", form_row_var, width=12)
        ttk.Label(frame, text="Ghi chú").grid(row=6, column=6, sticky="w", padx=(0, 4), pady=3)
        ttk.Entry(frame, textvariable=desc_var, width=32).grid(row=6, column=7, sticky="w", pady=3)

        columns = tuple(TEMPLATE_COLUMNS)
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=20)
        headings = [
            ("cc_code", 105, "Mã CC"),
            ("period", 80, "Period"),
            ("target_month", 90, "Tháng"),
            ("event_name", 170, "Sự kiện"),
            ("event_type", 150, "Loại event"),
            ("count", 70, "Count"),
            ("unit_price", 100, "Đơn giá"),
            ("unit_price_key", 120, "Key đơn giá"),
            ("allocation_content", 130, "Nội dung phân bổ"),
            ("amount_vnd", 115, "Số tiền"),
            ("bus_expat_people", 115, "Bus biệt phái"),
            ("bus_vietnamese_people", 115, "Bus Việt Nam"),
            ("account_code", 95, "Mã TK"),
            ("account_jp_name", 120, "Tên TK Nhật"),
            ("account_name", 120, "Alias TK"),
            ("account_group", 100, "Nhóm TK"),
            ("form_row", 75, "Form row"),
            ("row", 65, "Row"),
            ("source_month", 100, "Source month"),
            ("headcount_basis", 120, "Headcount basis"),
            ("description", 180, "Description"),
            ("note", 220, "Note"),
        ]
        for col, width, text in headings:
            tree.heading(col, text=text)
            tree.column(col, width=width, anchor="w")
        tree.grid(row=12, column=0, columnspan=8, sticky="nsew", pady=(12, 0))
        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=8, column=8, sticky="ns", pady=(12, 0))
        frame.rowconfigure(8, weight=1)
        frame.columnconfigure(7, weight=1)

        def parse_cc_code(text: str) -> str:
            raw = (text or "").strip()
            if " - " in raw:
                raw = raw.split(" - ")[0].strip()
            return raw

        def clear_inputs():
            for variable in (
                cc_var,
                period_var,
                event_var,
                event_type_var,
                count_var,
                unit_price_var,
                unit_price_key_var,
                amount_var,
                bus_expat_people_var,
                bus_vietnamese_people_var,
                account_var,
                account_jp_name_var,
                form_row_var,
                desc_var,
            ):
                variable.set("")
            event_type_var.set("month_specific_driver")
            bus_expat_people_var.set("0")
            bus_vietnamese_people_var.set("0")

        def load_rows():
            for item in tree.get_children():
                tree.delete(item)
            for row in self._read_csv_rows(csv_path):
                values = []
                for col in columns:
                    value = str(row.get(col, "") or "").strip()
                    if col == "target_month" and not value:
                        value = str(row.get("period", "") or "").strip()
                    elif col == "row" and not value:
                        value = str(row.get("form_row", "") or "").strip()
                    elif col == "note" and not value:
                        value = str(row.get("description", "") or "").strip()
                    values.append(value)
                tree.insert("", tk.END, values=tuple(values))

        def validate_numeric(raw, label, required=False):
            text = str(raw or "").strip()
            if not text:
                if required:
                    raise ValueError(f"Thiếu {label}.")
                return ""
            float(text)
            return text

        def validate_non_negative_int(raw, label):
            text = str(raw or "").strip()
            if not text:
                return "0"
            if not text.isdecimal():
                raise ValueError(f"{label} phải là số nguyên không âm.")
            return str(int(text))

        def add_or_update():
            cc_code = parse_cc_code(cc_var.get())
            period = period_var.get().strip()
            event_name = event_var.get().strip()
            try:
                if not cc_code or not period or not event_name:
                    raise ValueError("Cần nhập Mã CC, Tháng ghi chi phí và Sự kiện.")
                count = validate_numeric(count_var.get(), "số người/count")
                if event_name == "Cốc xếp định kỳ":
                    count = validate_non_negative_int(count_var.get(), "Số lượng cốc xếp định kỳ")
                    if int(period[-2:]) not in {2, 8}:
                        raise ValueError("Cốc xếp định kỳ chỉ được nhập cho tháng 2 hoặc tháng 8.")
                unit_price = validate_numeric(unit_price_var.get(), "đơn giá")
                unit_price_key = unit_price_key_var.get().strip()
                amount_vnd = validate_numeric(amount_var.get(), "số tiền")
                bus_expat_people = validate_non_negative_int(
                    bus_expat_people_var.get(), "Người biệt phái đi xe bus"
                )
                bus_vietnamese_people = validate_non_negative_int(
                    bus_vietnamese_people_var.get(), "Người Việt Nam đi xe bus"
                )
                account_code = validate_numeric(account_var.get(), "mã tài khoản")
                account_jp_name = account_jp_name_var.get().strip()
                form_row = validate_numeric(form_row_var.get(), "dòng FORM")
                if not account_code and not account_jp_name:
                    raise ValueError("Cần nhập Mã tài khoản, hoặc Tên TK Nhật để tự resolve account_code.")
                if not ((count and (unit_price or unit_price_key)) or amount_vnd):
                    raise ValueError("Cần nhập count + unit_price, hoặc count + unit_price_key, hoặc amount_vnd.")
            except Exception as exc:
                messagebox.showerror("Lỗi dữ liệu", str(exc))
                return

            row_data = {col: "" for col in columns}
            row_data.update(
                {
                    "cc_code": cc_code,
                    "period": period,
                    "target_month": period,
                    "event_name": event_name,
                    "event_type": event_type_var.get().strip() or "month_specific_driver",
                    "count": count,
                    "unit_price": unit_price,
                    "unit_price_key": unit_price_key,
                    "allocation_content": unit_price_key,
                    "amount_vnd": amount_vnd,
                    "bus_expat_people": bus_expat_people,
                    "bus_vietnamese_people": bus_vietnamese_people,
                    "account_code": account_code,
                    "account_jp_name": account_jp_name,
                    "account_name": account_jp_name,
                    "form_row": form_row,
                    "row": form_row,
                    "description": desc_var.get().strip(),
                    "note": desc_var.get().strip(),
                }
            )
            values = tuple(row_data[col] for col in columns)
            selected = tree.selection()
            if selected:
                tree.item(selected[0], values=values)
            else:
                tree.insert("", tk.END, values=values)
            clear_inputs()

        def remove_selected():
            for item in tree.selection():
                tree.delete(item)

        def on_select(_event):
            selected = tree.selection()
            if not selected:
                return
            values = tree.item(selected[0], "values")
            row_data = {col: str(values[index]) if index < len(values) else "" for index, col in enumerate(columns)}
            cc_var.set(row_data.get("cc_code", ""))
            period_var.set(row_data.get("target_month") or row_data.get("period", ""))
            event_var.set(row_data.get("event_name", ""))
            event_type_var.set(row_data.get("event_type", "") or "month_specific_driver")
            count_var.set(row_data.get("count", ""))
            unit_price_var.set(row_data.get("unit_price", ""))
            unit_price_key_var.set(row_data.get("unit_price_key") or row_data.get("allocation_content", ""))
            amount_var.set(row_data.get("amount_vnd", ""))
            bus_expat_people_var.set(row_data.get("bus_expat_people", "") or "0")
            bus_vietnamese_people_var.set(row_data.get("bus_vietnamese_people", "") or "0")
            account_var.set(row_data.get("account_code", ""))
            account_jp_name_var.set(row_data.get("account_jp_name") or row_data.get("account_name", ""))
            form_row_var.set(row_data.get("row") or row_data.get("form_row", ""))
            desc_var.set(row_data.get("note") or row_data.get("description", ""))

        def save_file():
            rows = []
            for item in tree.get_children():
                values = tree.item(item, "values")
                rows.append({col: values[index] if index < len(values) else "" for index, col in enumerate(columns)})
            self._write_csv_rows(csv_path, columns, rows)
            self.log(f"Lưu sự kiện thiếu dữ liệu: số dòng={len(rows)}, tệp={csv_path}")
            messagebox.showinfo("Đã lưu", f"Đã lưu {len(rows)} dòng sự kiện.")

        button_row = ttk.Frame(frame)
        button_row.grid(row=9, column=0, columnspan=8, sticky="w", pady=(10, 0))
        ttk.Button(button_row, text="Thêm/Cập nhật", command=add_or_update).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(button_row, text="Xóa đã chọn", command=remove_selected).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(button_row, text="Lưu tệp", command=save_file).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(button_row, text="Đóng", command=editor.destroy).grid(row=0, column=3, padx=(0, 6))

        def refresh_event_help(*_args):
            selected = event_var.get().strip()
            event_help_var.set(event_help.get(selected, "Gợi ý: hãy nhập số thật từ người phụ trách nghiệp vụ. Không nhập số ước lượng nếu chưa được chốt."))
            if selected == "Cốc xếp định kỳ":
                event_type_var.set("manual_count_unit_price")
                unit_price_var.set("")
                unit_price_key_var.set("折りたたみコップ Cốc xếp")
                account_var.set("")
                account_jp_name_var.set("福利厚生費")
                amount_var.set("")

        event_combo.bind("<<ComboboxSelected>>", refresh_event_help)
        tree.bind("<<TreeviewSelect>>", on_select)
        load_rows()

    def _parse_selected_cc_code(self) -> str | None:
        raw = self.cc_code_filter.get().strip()
        if not raw:
            return None
        return raw.split(" - ")[0].strip() if " - " in raw else raw

    def _open_path(self, path: str):
        if not path or not os.path.exists(path):
            messagebox.showwarning("Chưa có tệp", f"Không tìm thấy tệp:\n{path}")
            return
        os.startfile(os.path.abspath(path))

    def _audit_output_dir(self) -> str:
        return self._project_paths().output_dir

    def _current_fiscal_year(self) -> int:
        try:
            return int(self.fiscal_year.get())
        except Exception:
            return 2027

    def _read_missing_inputs(self) -> list[dict[str, str]]:
        missing_path = os.path.join(
            self._audit_output_dir(), "BAO_CAO_KIEM_TRA", "DU_LIEU_CON_THIEU.xlsx"
        )
        if not os.path.exists(missing_path):
            return []
        workbook = load_workbook(missing_path, read_only=True, data_only=True)
        try:
            sheet = workbook.active
            rows = list(sheet.iter_rows(min_row=7, values_only=True))
            return [
                {
                    "severity": str(row[0] or ""), "cc_code": str(row[1] or ""),
                    "period": str(row[2] or ""), "area": str(row[3] or ""),
                    "message": str(row[3] or ""), "action": str(row[4] or ""),
                }
                for row in rows if any(value not in (None, "") for value in row)
            ]
        finally:
            workbook.close()

    def _manual_event_ccs(self) -> set[str]:
        source_dir = self.source_dir.get() or BASE_DIR
        path = ensure_manual_event_drivers_template(source_dir, self._current_fiscal_year())
        return {
            str(row.get("cc_code", "")).strip()
            for row in self._read_csv_rows(path)
            if str(row.get("cc_code", "")).strip()
        }


    def start_pipeline(self):
        try:
            fiscal_year = int(self.fiscal_year.get())
            exchange_rate = validate_exchange_rate(self.exchange_rate.get())

            cc_raw = self.cc_code_filter.get().strip()
            target_cc = None
            if cc_raw:
                target_cc = cc_raw.split(" - ")[0].strip() if " - " in cc_raw else cc_raw

            template = self.template_path.get()
            source = self.source_dir.get()
            template_error = _validate_selected_template(template, fiscal_year)
            if template_error:
                messagebox.showerror("Lỗi", template_error)
                return

            source_error = _validate_selected_source_dir(source, fiscal_year)
            if source_error:
                messagebox.showerror("Lỗi", source_error)
                return

            if self.syncing_master:
                messagebox.showinfo(
                    "Đang nạp dữ liệu",
                    "Chương trình đang tự động nạp dữ liệu gốc. Hãy đợi hoàn tất rồi chạy tính toán.",
                )
                return

            headcount_source = self.headcount_source_dir.get().strip()
            if not os.path.isdir(headcount_source):
                messagebox.showerror("Lỗi", "Hãy chọn thư mục nguồn nhân sự & thời gian hợp lệ.")
                return
            signature = (
                fiscal_year,
                os.path.abspath(template),
                os.path.abspath(source),
                os.path.abspath(headcount_source),
                float(exchange_rate),
            )
            approved_report = self._approved_preflight_report
            if (
                signature != self._approved_preflight_signature
                or not (
                    getattr(approved_report, "ok", False)
                    or getattr(approved_report, "can_continue_incomplete", False)
                )
            ):
                messagebox.showerror(
                    "Nguồn chưa được xác nhận",
                    "Bộ nguồn hiện tại chưa có kết quả kiểm tra còn hiệu lực. "
                    "Hãy chờ đối chiếu xong hoặc bấm “Kiểm tra lại từ đầu”.",
                )
                self._mark_preflight_stale()
                return

            accepted_missing_categories = ()
            if getattr(approved_report, "can_continue_incomplete", False):
                accepted_missing_categories = approved_report.accepted_missing_categories()
                warning_lines = "\n".join(
                    f"• {CATEGORY_DISPLAY_NAMES.get(issue.category, 'Nguồn dữ liệu')}: {issue.impact}"
                    for issue in approved_report.continuable_issues
                )
                proceed_incomplete = messagebox.askyesno(
                    "Xác nhận chạy với nguồn chưa đầy đủ",
                    "Một số nguồn chi phí độc lập đang thiếu:\n\n"
                    + warning_lines
                    + "\n\nKết quả sẽ được đánh dấu CHƯA ĐẦY ĐỦ và không lấy lại dữ liệu cũ "
                    "cho các phần bị ảnh hưởng. Bạn có muốn tiếp tục không?",
                )
                if not proceed_incomplete:
                    return
            self._accepted_missing_categories = accepted_missing_categories

            if target_cc is None:
                proceed = messagebox.askokcancel(
                    "Xuất toàn bộ Trung tâm chi phí",
                    "Bạn đang để trống Trung tâm chi phí.\n\n"
                    "Chương trình sẽ tự đồng bộ nguồn nhân sự, kiểm tra toàn bộ CC dự kiến xuất "
                    "và dừng trước khi xuất nếu có bất kỳ CC nào thiếu dữ liệu.\n\nTiếp tục?",
                )
                if not proceed:
                    return

            self.start_btn.configure(state=tk.DISABLED)
            self.log("--- BẮT ĐẦU TÍNH TOÁN ---")
            self.log(f"Tệp mẫu xác nhận chạy: {template}")
            self.log(f"Thư mục nguồn xác nhận chạy: {source}")
            self.log(f"Nguồn nhân sự & thời gian xác nhận chạy: {headcount_source}")
            self.log(f"Tỷ giá hiệu lực cho lần chạy này: {exchange_rate:,.0f} USD/VND")
            self._last_pipeline_args=(fiscal_year,template,source,headcount_source,exchange_rate,target_cc)
            threading.Thread(
                target=self.run_process,
                args=self._last_pipeline_args,
                daemon=True,
            ).start()
        except Exception as exc:
            messagebox.showerror("Lỗi nhập liệu", _friendly_error_message(exc))

    def run_process(self, fiscal_year: int, template: str, source: str, headcount_source: str, rate: float, target_cc: int | None):
        try:
            cmd = self._pipeline_subprocess_command(
                fiscal_year, template, source, headcount_source, rate, target_cc
            )
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            process = subprocess.Popen(
                cmd,
                cwd=BASE_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            assert process.stdout is not None
            output_lines=[]
            for line in process.stdout:
                text = line.rstrip()
                if text:
                    output_lines.append(text)
                    self.log(text)
            return_code = process.wait()
            success = return_code == 0
            self._last_failed_run_database = (
                None
                if success
                else _failed_run_database_from_output(
                    output_lines,
                    self._project_paths(fiscal_year).history_root,
                    fiscal_year,
                )
            )
            result = (
                self._project_paths(fiscal_year).output_dir
                if success
                else _pipeline_failure_summary(output_lines, return_code)
            )
        except Exception as exc:
            success = False
            self._last_failed_run_database = None
            result = exc

        self._run_on_ui_thread(self._finish_pipeline, success, result)

    def _pipeline_subprocess_command(
        self,
        fiscal_year: int,
        template: str,
        source: str,
        headcount_source: str,
        rate: float,
        target_cc: int | str | None,
    ) -> list[str]:
        if getattr(sys, "frozen", False):
            cmd = [sys.executable]
        else:
            cmd = [sys.executable, os.path.join(BASE_DIR, "scripts", "run_e2e.py")]
        cmd.extend(
            [
                "--fy",
                str(fiscal_year),
                "--template",
                template,
                "--source",
                source,
                "--headcount-source",
                headcount_source,
                "--exchange-rate",
                str(rate),
                "--exchange-rate-source",
                "FORM!B2 / người dùng xác nhận trên giao diện",
            ]
        )
        approved_uniform = getattr(self, "_approved_uniform_policy_path", None)
        paths = self._project_paths(fiscal_year)
        cmd.extend([
            "--operational-db", self._operational_database(),
            "--manual-input-store", paths.manual_input_store,
            "--output-dir", paths.output_dir,
            "--run-history-root", paths.history_root,
        ])
        if approved_uniform:
            cmd.extend(["--uniform-policy", str(approved_uniform)])
        if target_cc:
            cmd.extend(["--target-cc", str(target_cc)])
        for category in getattr(self, "_accepted_missing_categories", ()):
            cmd.extend(["--accept-missing-source", str(category)])
        return cmd

    def _missing_baseline_context(self, result):
        if not _is_missing_baseline_error(result):
            return None
        args=getattr(self,"_last_pipeline_args",None)
        run_database=getattr(self,"_last_failed_run_database",None)
        if not args or not run_database:return None
        fiscal_year,_,_,_,_,target_cc=args
        conn=get_connection(self._manual_input_store(fiscal_year)); create_schema(conn)
        try: missing=find_missing_baseline_ccs(conn,fiscal_year,target_cc=target_cc)
        finally: conn.close()
        return (fiscal_year,target_cc,missing,run_database) if missing else None

    def _open_baseline_recovery_dialog(self, fiscal_year, target_cc, missing_ccs, run_database):
        dialog=tk.Toplevel(self.root); dialog.title("Thiếu baseline T3"); dialog.geometry("680x300"); dialog.transient(self.root); dialog.grab_set()
        ttk.Label(dialog,text="Thiếu dữ liệu baseline T3",font=("Segoe UI",15,"bold")).pack(anchor="w",padx=18,pady=(18,6))
        preview=", ".join(missing_ccs[:12])+("…" if len(missing_ccs)>12 else "")
        ttk.Label(dialog,text=f"CC cần xử lý: {preview}\n\nChọn một hành động. Chương trình sẽ không tiếp tục tính toán nếu bạn đóng hộp thoại.",wraplength=640,justify="left").pack(anchor="w",padx=18)
        def use_april():
            conn=get_connection(self._manual_input_store(fiscal_year)); create_schema(conn)
            source_conn=None
            try:
                source_uri="file:"+os.path.realpath(run_database).replace("\\","/")+"?mode=ro"
                source_conn=sqlite3.connect(source_uri,uri=True)
                with conn:
                    copied=copy_missing_baselines_from_april(
                        conn,fiscal_year,target_cc=target_cc,source_conn=source_conn
                    )
            except Exception as exc:
                messagebox.showerror("Không thể dùng T4",_friendly_error_message(exc),parent=dialog); return
            finally:
                if source_conn is not None:source_conn.close()
                conn.close()
            unresolved=[cc for cc in missing_ccs if cc not in copied]
            if unresolved:
                messagebox.showerror("Không thể dùng T4",f"Không có dữ liệu T4 hợp lệ để điền baseline cho: {', '.join(unresolved)}",parent=dialog); return
            dialog.destroy(); self.log(f"Người dùng chấp thuận dùng T4 làm baseline T3 cho: {', '.join(copied)}"); self.start_pipeline()
        def manual():
            dialog.destroy()
            if target_cc:
                choices=list(self._get_cc_choices())
                selected=next((item for item in choices if item.split(" - ")[0]==str(target_cc)),None)
                if selected:self.root.after(100,lambda:self.open_headcount_editor_v2(selected))
                else:self.open_headcount_editor_v2()
            else:self.open_headcount_editor_v2()
        buttons=ttk.Frame(dialog); buttons.pack(fill="x",padx=18,pady=22)
        ttk.Button(buttons,text="1. Dùng dữ liệu T4 cho baseline T3",command=use_april).pack(fill="x",pady=3)
        ttk.Button(buttons,text="2. Mở nhập nhân sự thủ công",command=manual).pack(fill="x",pady=3)
        ttk.Button(buttons,text="3. Thoát — không tiếp tục tính toán",command=dialog.destroy).pack(fill="x",pady=3)
        dialog.protocol("WM_DELETE_WINDOW",dialog.destroy)

    def _finish_pipeline(self, success: bool, result):
        if success:
            self.log(f"THÀNH CÔNG. Kết quả: {result}")
            self.root.after(100, self.load_cc_list)
            messagebox.showinfo("Hoàn tất", f"Quá trình xuất dữ liệu hoàn tất.\n\nKết quả: {result}")
        else:
            recovery=self._missing_baseline_context(result)
            message = _friendly_error_message(result)
            self.log(f"THẤT BẠI: {message}")
            if recovery:
                self._open_baseline_recovery_dialog(*recovery)
            else:
                messagebox.showerror("Thất bại", message)
        # Source paths may have changed while the subprocess was running; do
        # not re-enable calculation until the current selection is checked.
        self._mark_preflight_stale()


if __name__ == "__main__":
    if "--reference-staffing-render-worker" in sys.argv[1:]:
        from src.services.reference_staffing_render_worker import main as _render_worker_main

        worker_args = [
            arg for arg in sys.argv[1:] if arg != "--reference-staffing-render-worker"
        ]
        raise SystemExit(_render_worker_main(worker_args))
    # Support headless export from packaged exe: child CLI invocations delegate
    # to the pipeline instead of opening a second GUI window.
    if len(sys.argv) > 1 and any(arg.startswith("--") for arg in sys.argv[1:]):
        from scripts.run_e2e import main as _cli_main
        raise SystemExit(_cli_main())
    root = tk.Tk()
    app = MPManagerApp(root)
    root.mainloop()
