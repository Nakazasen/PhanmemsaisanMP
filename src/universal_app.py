"""
MP2027 Manager - ứng dụng giao diện chính.
"""

import csv
import hashlib
import os
import sqlite3
import sys
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, scrolledtext, ttk


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
from scripts.run_e2e import run_universal_pipeline
from src.config import EXCHANGE_RATE_USD_VND
from src.db.loader import load_all
from src.db.schema import create_schema, get_connection
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
from src.utils.excel_helpers import get_fy_months
from src.utils.source_manifest import (
    DEFAULT_DESCRIPTIONS,
    MANIFEST_COLUMNS,
    ensure_source_manifest,
    read_source_manifest,
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


def _parse_required_save_int(period: str, field: str, raw_value: str, label: str) -> tuple[str | None, dict | None]:
    text = str(raw_value or "").strip()
    if text == "":
        return None, _headcount_save_error(period, field, text, "REQUIRED", f"Missing {label} value")
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

        staff, staff_error = _parse_required_save_int(
            period,
            "headcount_staff",
            values.get("staff", ""),
            f"staff at {label}",
        )
        worker, worker_error = _parse_required_save_int(
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
        raw_display = "blank" if raw_value == "" else raw_value
        rule = str(error.get("validation_rule", "") or "-")
        reason = str(error.get("reason", "") or "-")
        csv_written = error.get("csv_row_written", False)
        db_inserted = error.get("db_row_inserted", False)
        lines.append(
            f"{period} | {field} | {raw_display} | {rule} | {reason} | CSV written={csv_written} | DB inserted={db_inserted}"
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


def _default_template_path() -> str:
    external_mp2027 = os.path.join(BASE_DIR, "docs", "MP2027", "FORM.xlsx")
    if os.path.exists(external_mp2027):
        return external_mp2027

    packaged_mp2027 = resource_path(os.path.join("docs", "MP2027", "FORM.xlsx"))
    if os.path.exists(packaged_mp2027):
        return packaged_mp2027

    external_root_form = os.path.join(BASE_DIR, "FORM.xlsx")
    if os.path.exists(external_root_form):
        return external_root_form

    raise FileNotFoundError(
        f"Không tìm thấy tệp mẫu bắt buộc: {external_mp2027}. "
        "Không dùng FORM.xlsx cũ ở thư mục gốc vì tệp đó còn công thức mẫu cũ."
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


def _default_source_dir() -> str:
    external_mp2027 = os.path.join(BASE_DIR, "docs", "MP2027")
    if os.path.isdir(external_mp2027):
        return external_mp2027

    packaged_mp2027 = resource_path(os.path.join("docs", "MP2027"))
    if os.path.isdir(packaged_mp2027):
        return packaged_mp2027

    return BASE_DIR

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
  Đường dẫn đến FORM MP2027. Bản đúng hiện tại là docs/MP2027/FORM.xlsx.
- Thư mục nguồn:
  Thư mục chứa các tệp Excel nguồn và các tệp nhập tay.

3. QUY TRÌNH CHẠY ĐỀ XUẤT
Bước 1: Kiểm tra tệp mẫu là docs/MP2027/FORM.xlsx, không dùng FORM_old.xlsx.
Bước 2: Chọn đúng Thư mục nguồn chứa các tệp nghiệp vụ.
Bước 3: Nhập Năm tài chính.
Bước 4: Nếu cần, nhập bổ sung nhân sự bằng nút "Nhập nhân sự thủ công".
Bước 5: Nếu có khoản chương trình không thể tự biết, bấm "Nhập sự kiện thiếu dữ liệu".
Bước 6: Nếu chạy riêng, chọn 1 Trung tâm chi phí. Nếu không, để trống.
Bước 7: Bấm "CHẠY TÍNH TOÁN".
Bước 8: Mở Dashboard kiểm toán để xem đèn xanh/vàng/đỏ và kiểm tra công thức.

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
- Dashboard còn báo VÀNG: đây không phải lỗi. Nghĩa là có dữ liệu cần người dùng xác nhận trước khi tin kết quả.
- Nhập xong nhưng chưa áp dụng: kiểm tra đã bấm "Lưu tệp" hoặc "Lưu 12 tháng" trước khi chạy tính toán.

8. KHUYẾN NGHỊ VẬN HÀNH
- Chạy thử với 1 CC trước khi xuất hàng loạt.
- Sau khi chạy, luôn mở Dashboard kiểm toán trước khi gửi tệp cho người khác.
- Không nhập số ước lượng nếu chưa chắc. Hãy để trống và ghi chú để kiểm toán lại.
""".strip()

USER_GUIDE_TEXT_LATEST = """
HƯỚNG DẪN SỬ DỤNG MP2027 MANAGER

1. MỤC ĐÍCH
MP2027 Manager dùng để lập ngân sách MP FY2027 theo từng Cost Center.
Chương trình đọc dữ liệu từ thư mục docs/MP2027, tính phân bổ chi phí, rồi xuất file Excel theo FORM MP2027.

Nguyên tắc quan trọng:
- Chương trình không tự bịa số.
- Khoản nào thiếu dữ liệu thật sẽ được báo trên Dashboard để người dùng nhập hoặc chốt lại.
- FORM.xlsx là mẫu xuất kết quả, không phải nơi nhập tay chính cho headcount hoặc sự kiện.

2. THƯ MỤC ĐÚNG KHI CHẠY
Khi chạy từ source code:
- Tệp mẫu FORM: docs/MP2027/FORM.xlsx
- Thư mục nguồn: docs/MP2027

Khi dùng bản đóng gói onefile:
- Đặt MP2027_Manager.exe trong một thư mục riêng.
- Bên cạnh exe phải có thư mục docs/MP2027.
- Người dùng sửa dữ liệu trong docs/MP2027 bên cạnh exe, không sửa dữ liệu bên trong file exe.

Ví dụ:
MP2027_App/
  MP2027_Manager.exe
  docs/
    MP2027/
      FORM.xlsx
      source_file_order.xlsx
      event_drivers_manual.csv
      special_costs_manual.csv
  raw/
    headcount_manual.csv
      các file Excel nguồn khác

3. CÁC TRƯỜNG TRÊN MÀN HÌNH CHÍNH
- Năm tài chính:
  Nhập năm cần chạy, ví dụ 2027.

- Trung tâm chi phí:
  Để trống nếu muốn xuất toàn bộ CC có dữ liệu.
  Chọn một CC nếu chỉ muốn kiểm tra/chạy thử một bộ phận.

- Tệp mẫu FORM:
  Phải trỏ tới docs/MP2027/FORM.xlsx.
  Không dùng FORM.xlsx ở thư mục gốc nếu đó là bản cũ.

- Thư mục nguồn:
  Phải trỏ tới docs/MP2027.
  Đây là nơi chứa FORM, file nguồn, CSV nhập tay và source_file_order.xlsx.

4. THỨ TỰ FILE NGUỒN
Nút "Thứ tự file nguồn" dùng để quy định file nào được đọc và đọc theo thứ tự nào.

Cách dùng:
Bước 1: Bấm "Thứ tự file nguồn".
Bước 2: Chọn một dòng trong bảng.
Bước 3: Bấm "Chọn file..." nếu cần đổi file nguồn.
Bước 4: Bấm "Lên" hoặc "Xuống" để đổi thứ tự.
Bước 5: Bỏ chọn "Dùng dòng này" nếu muốn tạm thời không đọc một file.
Bước 6: Bấm "Lưu".

Tệp được lưu là:
docs/MP2027/source_file_order.xlsx

Không nên sửa source_file_order.csv bằng Excel. CSV chỉ là fallback kỹ thuật và có thể lỗi font nếu mở sai encoding.

5. QUY TRÌNH CHẠY ĐỀ XUẤT
Bước 1: Kiểm tra Tệp mẫu FORM là docs/MP2027/FORM.xlsx.
Bước 2: Kiểm tra Thư mục nguồn là docs/MP2027.
Bước 3: Bấm "Thứ tự file nguồn" nếu vừa đổi tên file hoặc thêm file nguồn.
Bước 4: Nếu cần, nhập nhân sự bằng nút "Nhập nhân sự thủ công".
Bước 5: Nếu có khoản thiếu dữ liệu thật, bấm "Nhập sự kiện thiếu dữ liệu".
Bước 6: Nếu muốn kiểm tra nhanh, chọn một CC; nếu không thì để trống.
Bước 7: Bấm "CHẠY TÍNH TOÁN".
Bước 8: Mở Dashboard kiểm toán.
Bước 9: Mở file kết quả CC để kiểm tra công thức và số liệu.

6. NHẬP NHÂN SỰ THỦ CÔNG
Dùng khi cần chốt số người theo CC/tháng hoặc khi Dashboard báo thiếu headcount.

Cách nhập:
Bước 1: Bấm "Nhập nhân sự thủ công".
Bước 2: Chọn CC.
Bước 3: Nhập số nhân viên và công nhân cho 12 tháng.
Bước 4: Nếu cần tính health check row 57/58, nhập Nam/Nữ tháng 12.
Bước 5: Bấm "Lưu 12 tháng".
Bước 6: Chạy tính toán lại.

Tệp lưu dữ liệu:
raw/headcount_manual.csv

Lưu ý:
- Nếu sửa số người trực tiếp trong FORM, lần chạy sau có thể bị ghi đè.
- Hãy nhập/chốt headcount bằng màn hình này hoặc bằng headcount_manual.csv.

7. NHẬP SỰ KIỆN THIẾU DỮ LIỆU
Dùng cho các khoản chương trình không thể tự biết số thật, ví dụ:
- Xe bus JP/VN.
- Quà cho người không đi du lịch.
- My Episode.
- Kỷ niệm 10 năm.
- Kỷ niệm thành lập công ty.
- VISA/Passport/GPLD/NNN nếu phải ghi vào row khác row 137.

Cách nhập:
Bước 1: Bấm "Nhập sự kiện thiếu dữ liệu".
Bước 2: Chọn CC và tháng ghi chi phí. Ví dụ 202705 là tháng 5 FY2027.
Bước 3: Nhập tên sự kiện, ví dụ 社員旅行 Du lịch công ty.
Bước 4: Chọn loại sự kiện. Với event phát sinh riêng theo tháng, dùng month_specific_driver.
Bước 5: Nếu biết số người/số lượng, nhập count.
Bước 6: Nếu muốn tự nhập đơn giá, nhập unit_price; đơn giá nhập tay sẽ được ưu tiên.
Bước 7: Nếu muốn chương trình tự lấy đơn giá từ FY2027配賦額一覧, nhập unit_price_key, ví dụ 社員旅行.
Bước 8: Có thể bỏ trống account_code nếu nhập account_jp_name/account_name, ví dụ 福利厚生費.
Bước 9: Nếu biết row FORM cần ghi, nhập row/form_row, ví dụ 66 cho 社員旅行.
Bước 10: Nếu chỉ biết tổng tiền, nhập amount_vnd.
Bước 11: Ghi note/description để kiểm toán lại nguồn số liệu, rồi bấm "Thêm/Cập nhật" và "Lưu tệp".

Tệp lưu dữ liệu:
docs/MP2027/event_drivers_manual.csv

8. CHI PHÍ ĐẶC BIỆT THEO ROW FORM
Nếu có chi phí cần ghi đúng một row FORM nhưng chưa có parser tự động, dùng:
docs/MP2027/special_costs_manual.csv

Ví dụ:
- Passport/VISA/GPLD cần row khác row 137.
- Một khoản NNN cần tách riêng theo row đã được finance xác nhận.

Không nhập form_row nếu chưa chắc row đích.

9. CÁCH ĐỌC DASHBOARD KIỂM TOÁN
- XANH: CC có dữ liệu nền tảng và chưa có cảnh báo cơ bản.
- VÀNG: CC có dữ liệu nhưng còn điểm cần người dùng xem/chốt.
- ĐỎ: CC chưa có dữ liệu tính toán sau lần chạy gần nhất.

Khi thấy VÀNG hoặc ĐỎ:
Bước 1: Chọn dòng CC.
Bước 2: Đọc cột "Lý do".
Bước 3: Xem bảng "Việc cần người dùng chốt".
Bước 4: Nếu thiếu sự kiện, bấm "Nhập dữ liệu thiếu".
Bước 5: Nếu thiếu nhân sự, bấm "Nhập nhân sự thủ công".
Bước 6: Chạy lại và kiểm tra file kết quả.

Lưu ý:
XANH không có nghĩa là số liệu đã đúng 100%. XANH chỉ nghĩa là chương trình chưa thấy thiếu input cơ bản.
Người dùng vẫn cần kiểm tra công thức và nguồn dữ liệu trước khi gửi chính thức.

10. FILE KẾT QUẢ
Sau khi chạy, kiểm tra thư mục:
OUTPUT_FY2027

Các file thường gặp:
- MP_CC_<mã CC>.xlsx: kết quả theo từng Cost Center.
- MP2027_MISSING_INPUTS.csv: danh sách dữ liệu còn cần người dùng xem/chốt.
- MP2027_AUDIT_REPORT.md: báo cáo kiểm toán nếu pipeline sinh ra.

11. LỖI THƯỜNG GẶP
- Lỗi "Không được dùng FORM.xlsx...":
  Tệp mẫu đang trỏ nhầm FORM ở thư mục gốc hoặc bản FORM cũ.
  Hãy chọn docs/MP2027/FORM.xlsx.

- Mở source_file_order.csv bị lỗi font:
  Không dùng CSV để chỉnh. Hãy dùng nút "Thứ tự file nguồn" hoặc mở source_file_order.xlsx.

- Dashboard vẫn VÀNG:
  Đây không phải lỗi chương trình. Nghĩa là còn dữ liệu cần người dùng xác nhận.

- Nhập xong nhưng kết quả chưa đổi:
  Kiểm tra đã bấm "Lưu tệp" hoặc "Lưu 12 tháng", rồi chạy tính toán lại.

- Không thấy file output cho một CC:
  Có thể CC đó chưa có dữ liệu fact để export batch. Hãy chạy riêng CC đó hoặc kiểm tra Dashboard.

12. KHUYẾN NGHỊ VẬN HÀNH
- Chạy thử một CC trước khi xuất hàng loạt.
- Luôn mở Dashboard sau khi chạy.
- Luôn kiểm tra file Excel kết quả trước khi gửi.
- Không nhập số ước lượng nếu chưa chắc.
- Khi thêm file nguồn mới, cập nhật bằng nút "Thứ tự file nguồn" trước khi chạy.
- Khi bàn giao bản onefile, luôn bàn giao cả thư mục docs/MP2027 cạnh exe.
""".strip()


class MPManagerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MP2027 Manager - Quản lý Ngân sách")
        self.root.geometry("980x720")

        self.fiscal_year = tk.StringVar(value="2027")
        self.cc_code_filter = tk.StringVar(value="")
        self.template_path = tk.StringVar(value=_default_template_path())
        self.source_dir = tk.StringVar(value=_default_source_dir())
        self.last_excel_mtime = 0.0
        self.syncing_master = False

        self.setup_styles()
        self.setup_ui()
        self.set_icon()
        self.root.after(300, self.load_cc_list)

    def set_icon(self):
        icon_path = resource_path(os.path.join("assets", "app_icon.ico"))
        if os.path.exists(icon_path):
            try:
                # Windows specific icon loading
                self.root.iconbitmap(icon_path)
            except Exception as e:
                print(f"Error loading icon: {e}")


    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Header.TLabel", font=("Segoe UI", 15, "bold"))
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=10)

    def setup_ui(self):
        container = ttk.Frame(self.root, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(container, text="Tính toán Ngân sách MP2027", style="Header.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 16)
        )

        ttk.Label(container, text="Năm tài chính").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(container, textvariable=self.fiscal_year, width=20).grid(row=1, column=1, sticky="w")

        ttk.Label(container, text="Trung tâm chi phí (Tùy chọn)").grid(row=2, column=0, sticky="w", pady=4)
        cc_frame = ttk.Frame(container)
        cc_frame.grid(row=2, column=1, sticky="w")
        
        self.cc_combo = ttk.Combobox(cc_frame, textvariable=self.cc_code_filter, width=40, state="readonly")
        self.cc_combo.pack(side="left")
        
        self.refresh_btn = ttk.Button(cc_frame, text="🔄", width=3, command=self.auto_init_master_data)
        self.refresh_btn.pack(side="left", padx=2)
        
        ttk.Label(container, text="Để trống để xuất toàn bộ").grid(row=2, column=2, sticky="w", padx=8)

        ttk.Label(container, text="Tệp mẫu FORM").grid(row=3, column=0, sticky="w", pady=(14, 4))
        ttk.Entry(container, textvariable=self.template_path, width=70).grid(row=3, column=1, sticky="w")
        ttk.Button(container, text="Chọn...", command=self.browse_template).grid(row=3, column=2, sticky="w")

        ttk.Label(container, text="Thư mục nguồn").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Entry(container, textvariable=self.source_dir, width=70).grid(row=4, column=1, sticky="w")
        ttk.Button(container, text="Chọn...", command=self.browse_source_dir).grid(row=4, column=2, sticky="w")

        ttk.Button(
            container,
            text="Nhập nhân sự thủ công",
            command=self.open_headcount_editor_v2,
        ).grid(row=5, column=1, sticky="w", pady=(8, 0))

        ttk.Button(
            container,
            text="Nhập sự kiện thiếu dữ liệu",
            command=self.open_event_driver_editor,
        ).grid(row=5, column=1, sticky="w", padx=(170, 0), pady=(8, 0))

        ttk.Button(
            container,
            text="Thứ tự file nguồn",
            command=self.open_source_order_editor,
        ).grid(row=5, column=1, sticky="w", padx=(340, 0), pady=(8, 0))

        ttk.Button(
            container,
            text="Hướng dẫn sử dụng chi tiết",
            command=self.open_user_guide,
        ).grid(row=5, column=2, sticky="w", pady=(8, 0))

        ttk.Separator(container, orient=tk.HORIZONTAL).grid(row=6, column=0, columnspan=3, sticky="ew", pady=16)

        self.start_btn = ttk.Button(
            container,
            text="CHẠY TÍNH TOÁN",
            style="Primary.TButton",
            command=self.start_pipeline,
        )
        self.start_btn.grid(row=7, column=0, columnspan=3, sticky="w")
        ttk.Button(
            container,
            text="Dashboard kiểm toán",
            command=self.open_audit_dashboard,
        ).grid(row=8, column=1, sticky="w", padx=(170, 0))

        ttk.Label(container, text="Nhật ký xử lý").grid(row=9, column=0, sticky="w", pady=(16, 4))
        self.log_widget = scrolledtext.ScrolledText(container, height=16, state=tk.DISABLED, font=("Consolas", 9))
        self.log_widget.grid(row=10, column=0, columnspan=3, sticky="nsew")

        container.rowconfigure(10, weight=1)
        container.columnconfigure(1, weight=1)

    def log(self, message: str):
        self.log_widget.configure(state=tk.NORMAL)
        self.log_widget.insert(tk.END, f"{datetime.now().strftime('[%H:%M:%S]')} {message}\n")
        self.log_widget.see(tk.END)
        self.log_widget.configure(state=tk.DISABLED)
        self.root.update_idletasks()

    def browse_template(self):
        path = filedialog.askopenfilename(filetypes=[("Tệp Excel", "*.xlsx")])
        if path:
            if _is_legacy_root_template(path):
                messagebox.showerror(
                    "Lỗi",
                    "Không được dùng FORM.xlsx ở thư mục gốc vì tệp này còn công thức mẫu cũ. Hãy chọn docs/MP2027/FORM.xlsx.",
                )
                return
            self.template_path.set(path)

    def browse_source_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.source_dir.set(path)

    def open_source_order_editor(self):
        source_dir = self.source_dir.get() or BASE_DIR
        os.makedirs(source_dir, exist_ok=True)
        try:
            manifest_path = ensure_source_manifest(source_dir)
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không tạo được tệp thứ tự nguồn:\n{exc}")
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
                "Người dùng có thể đổi thứ tự, chọn lại file hoặc tắt dòng không dùng. "
                "Tệp cấu hình Excel: source_file_order.xlsx"
            ),
            wraplength=900,
        ).grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 10))

        columns = ("order", "category", "filename", "enabled", "description")
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=14)
        tree.heading("order", text="Thứ tự")
        tree.heading("category", text="Loại nguồn")
        tree.heading("filename", text="Tên file")
        tree.heading("enabled", text="Dùng")
        tree.heading("description", text="Ghi chú")
        tree.column("order", width=60, anchor="center")
        tree.column("category", width=130)
        tree.column("filename", width=430)
        tree.column("enabled", width=60, anchor="center")
        tree.column("description", width=250)
        tree.grid(row=1, column=0, columnspan=6, sticky="nsew")

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.grid(row=1, column=6, sticky="ns")
        tree.configure(yscrollcommand=scrollbar.set)

        form = ttk.Frame(frame)
        form.grid(row=2, column=0, columnspan=6, sticky="ew", pady=(10, 0))
        ttk.Label(form, text="Loại nguồn").grid(row=0, column=0, sticky="w")
        category_var = tk.StringVar()
        category_combo = ttk.Combobox(
            form,
            textvariable=category_var,
            values=list(DEFAULT_DESCRIPTIONS.keys()),
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
                rows.append(
                    {
                        "order": str(index),
                        "category": str(values[1]),
                        "filename": str(values[2]),
                        "enabled": str(values[3]),
                        "description": str(values[4]),
                    }
                )
            return rows

        def refresh_order_numbers() -> None:
            for index, item_id in enumerate(tree.get_children(), start=1):
                values = list(tree.item(item_id, "values"))
                values[0] = str(index)
                tree.item(item_id, values=values)

        def load_rows() -> None:
            for item_id in tree.get_children():
                tree.delete(item_id)
            for row in read_source_manifest(source_dir, include_missing=True):
                tree.insert(
                    "",
                    tk.END,
                    values=(
                        row.get("order", ""),
                        row.get("category", ""),
                        row.get("filename", ""),
                        row.get("enabled", "1"),
                        row.get("description", ""),
                    ),
                )
            refresh_order_numbers()

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
                filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
            )
            if not path:
                return
            try:
                filename_var.set(os.path.relpath(path, source_dir))
            except ValueError:
                filename_var.set(os.path.basename(path))

        def add_or_update() -> None:
            category = category_var.get().strip()
            filename = filename_var.get().strip()
            if not category or not filename:
                messagebox.showwarning("Thiếu dữ liệu", "Hãy chọn loại nguồn và tên file.")
                return
            description = description_var.get().strip() or DEFAULT_DESCRIPTIONS.get(category, "")
            enabled = "1" if enabled_var.get() else "0"
            item_id = selected_item()
            if item_id:
                order = tree.item(item_id, "values")[0]
                tree.item(item_id, values=(order, category, filename, enabled, description))
            else:
                tree.insert("", tk.END, values=("", category, filename, enabled, description))
            refresh_order_numbers()

        def remove_selected() -> None:
            item_id = selected_item()
            if item_id:
                tree.delete(item_id)
                refresh_order_numbers()

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
            except Exception as exc:
                messagebox.showerror("Lỗi", f"Không lưu được thứ tự file nguồn:\n{exc}")

        tree.bind("<<TreeviewSelect>>", fill_form_from_selection)
        load_rows()

        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=6, sticky="w", pady=(10, 0))
        ttk.Button(buttons, text="Thêm/Cập nhật", command=add_or_update).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(buttons, text="Xóa dòng", command=remove_selected).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(buttons, text="Lên", command=lambda: move_selected(-1)).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(buttons, text="Xuống", command=lambda: move_selected(1)).grid(row=0, column=3, padx=(0, 6))
        ttk.Button(buttons, text="Lưu", command=save_manifest).grid(row=0, column=4, padx=(0, 6))
        ttk.Button(buttons, text="Đóng", command=editor.destroy).grid(row=0, column=5, padx=(0, 6))

        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)

    def load_cc_list(self):
        db_path = os.path.join(BASE_DIR, "mp2027.db")
        
        # Smart Check on Startup
        template = self.template_path.get()
        if os.path.exists(template):
            mtime = os.path.getmtime(template)
            if mtime > self.last_excel_mtime:
                self.last_excel_mtime = mtime
                self.auto_init_master_data()
                return

        if not os.path.exists(db_path):
            self.auto_init_master_data()
            return

        try:
            conn = get_connection(db_path)
            rows = conn.execute("SELECT code, name_jp FROM dim_cost_centers ORDER BY code").fetchall()
            if not rows:
                conn.close()
                self.auto_init_master_data()
                return
            
            self.cc_combo["values"] = [f"{row['code']} - {row['name_jp']}" for row in rows]
            conn.close()
        except Exception as exc:
            self.log(f"Lỗi khi nạp danh sách CC: {exc}")

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
                db_path = os.path.join(BASE_DIR, "mp2027.db")
                load_all(db_path=db_path, template_path=template)
                self.log("Tự động nạp dữ liệu Master THÀNH CÔNG.")
                self.root.after(100, self.load_cc_list)
            except Exception as e:
                self.log(f"Tự động nạp dữ liệu thất bại: {e}")
            finally:
                self.syncing_master = False

        threading.Thread(target=run_sync, daemon=True).start()

    def _get_cc_choices(self):
        db_path = os.path.join(BASE_DIR, "mp2027.db")
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
        guide.title("Hướng dẫn sử dụng chi tiết")
        guide.geometry("860x640")

        frame = ttk.Frame(guide, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text="Hướng dẫn sử dụng chi tiết",
            style="Header.TLabel",
        ).pack(anchor="w", pady=(0, 8))

        ttk.Label(
            frame,
            text="Tài liệu này hướng dẫn từng bước thao tác trên giao diện hiện tại.",
        ).pack(anchor="w", pady=(0, 8))

        guide_text = scrolledtext.ScrolledText(
            frame,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            height=28,
        )
        guide_text.pack(fill=tk.BOTH, expand=True)
        guide_text.insert("1.0", USER_GUIDE_TEXT_LATEST)
        guide_text.configure(state=tk.DISABLED)

        ttk.Button(frame, text="Đóng", command=guide.destroy).pack(anchor="e", pady=(10, 0))

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
            db_path = os.path.join(BASE_DIR, "mp2027.db")
            conn = get_connection(db_path)
            try:
                create_schema(conn)
                result = parse_manual_headcount(conn, source_dir=source_dir)
            finally:
                conn.close()
            self.log(
                "Đã lưu nhân sự thủ công: {rows} hàng -> {path}; DB inserted={inserted}, errors={errors}".format(
                    rows=len(rows),
                    path=csv_path,
                    inserted=result.get("inserted", 0),
                    errors=result.get("errors", 0),
                )
            )
            messagebox.showinfo(
                "Đã lưu",
                "Đã lưu {rows} hàng. DB inserted={inserted}, errors={errors}.".format(
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

    def open_headcount_editor_v2(self):
        try:
            fiscal_year = int(self.fiscal_year.get())
        except Exception:
            fiscal_year = 2027

        source_dir = resolve_manual_headcount_source_dir(self.source_dir.get() or BASE_DIR, base_dir=BASE_DIR)
        os.makedirs(source_dir, exist_ok=True)
        csv_path = ensure_manual_headcount_template(source_dir, fiscal_year)
        bus_csv_path = ensure_manual_bus_headcount_template(source_dir)

        editor = tk.Toplevel(self.root)
        editor.title("Nh\u1eadp li\u1ec7u nh\u00e2n s\u1ef1 12 th\u00e1ng")
        editor.geometry("1120x760")

        frame = ttk.Frame(editor, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=f"Tệp lưu dữ liệu: {csv_path}", font=("Segoe UI", 9, "italic")).grid(
            row=0, column=0, columnspan=8, sticky="w"
        )
        ttk.Label(
            frame,
            text=(
                "Nh\u1eadp 1 CC cho \u0111\u1ee7 12 th\u00e1ng. Th\u00e1ng 12 c\u00f3 th\u00eam Nam/N\u1eef "
                "\u0111\u1ec3 ph\u1ee5c v\u1ee5 chi ph\u00ed kh\u00e1m s\u1ee9c kh\u1ecfe."
            ),
        ).grid(row=1, column=0, columnspan=8, sticky="w", pady=(4, 10))

        cc_var = tk.StringVar()
        bus_expat_count_var = tk.StringVar(value="0")
        bus_vietnamese_count_var = tk.StringVar(value="0")
        bus_description_var = tk.StringVar()
        cc_choices = self._get_cc_choices()
        periods = get_required_headcount_periods(fiscal_year)
        fiscal_months = set(get_fy_months(fiscal_year))
        label_by_period = {
            period: (
                f"Baseline T3 ({period})"
                if period not in fiscal_months
                else f"Th\u00e1ng {int(period[-2:])}"
            )
            for period in periods
        }

        ttk.Label(frame, text="M\u00e3 CC").grid(row=2, column=0, sticky="w", pady=(0, 8))
        cc_combo = ttk.Combobox(frame, textvariable=cc_var, values=cc_choices, width=42, state="readonly")
        cc_combo.grid(row=2, column=1, sticky="w", pady=(0, 8))

        bus_frame = ttk.LabelFrame(frame, text="Th\u00f4ng tin xe bus - d\u00f9ng chung cho 12 th\u00e1ng")
        bus_frame.grid(row=3, column=0, columnspan=8, sticky="ew", pady=(0, 10))
        ttk.Label(bus_frame, text="Ng\u01b0\u1eddi bi\u1ec7t ph\u00e1i \u0111i xe bus").grid(
            row=0, column=0, sticky="w", padx=(8, 4), pady=(8, 4)
        )
        ttk.Entry(bus_frame, textvariable=bus_expat_count_var, width=12).grid(
            row=0, column=1, sticky="w", padx=(0, 12), pady=(8, 4)
        )
        ttk.Label(bus_frame, text="Ng\u01b0\u1eddi Vi\u1ec7t Nam \u0111i xe bus").grid(
            row=0, column=2, sticky="w", padx=(8, 4), pady=(8, 4)
        )
        ttk.Entry(bus_frame, textvariable=bus_vietnamese_count_var, width=12).grid(
            row=0, column=3, sticky="w", padx=(0, 12), pady=(8, 4)
        )
        ttk.Label(bus_frame, text="Ghi ch\u00fa").grid(row=0, column=4, sticky="w", padx=(8, 4), pady=(8, 4))
        ttk.Entry(bus_frame, textvariable=bus_description_var, width=42).grid(
            row=0, column=5, sticky="ew", padx=(0, 8), pady=(8, 4)
        )
        ttk.Label(
            bus_frame,
            text="S\u1ed1 l\u01b0\u1ee3ng n\u00e0y \u0111\u01b0\u1ee3c s\u1eed d\u1ee5ng chung cho 12 th\u00e1ng FY.",
            font=("Segoe UI", 9, "italic"),
        ).grid(row=1, column=0, columnspan=6, sticky="w", padx=8, pady=(0, 8))
        bus_frame.columnconfigure(5, weight=1)

        table = ttk.Frame(frame)
        table.grid(row=4, column=0, columnspan=8, sticky="nsew")
        frame.rowconfigure(4, weight=1)
        frame.columnconfigure(7, weight=1)

        headers = [
            ("K\u1ef3", 0),
            ("Nh\u00e2n vi\u00ean", 1),
            ("C\u00f4ng nh\u00e2n", 2),
            ("Nam (T12)", 3),
            ("N\u1eef (T12)", 4),
            ("Ghi ch\u00fa", 5),
        ]
        for text, column_index in headers:
            ttk.Label(table, text=text).grid(row=0, column=column_index, sticky="w", padx=4, pady=(0, 6))

        month_vars = {}
        for row_index, period in enumerate(periods, start=1):
            vars_for_period = {
                "staff": tk.StringVar(),
                "worker": tk.StringVar(),
                "male": tk.StringVar(),
                "female": tk.StringVar(),
                "description": tk.StringVar(),
            }
            month_vars[period] = vars_for_period

            ttk.Label(table, text=label_by_period[period]).grid(row=row_index, column=0, sticky="w", padx=4, pady=3)
            ttk.Entry(table, textvariable=vars_for_period["staff"], width=12).grid(row=row_index, column=1, sticky="w", padx=4, pady=3)
            ttk.Entry(table, textvariable=vars_for_period["worker"], width=12).grid(row=row_index, column=2, sticky="w", padx=4, pady=3)
            male_entry = ttk.Entry(table, textvariable=vars_for_period["male"], width=12)
            female_entry = ttk.Entry(table, textvariable=vars_for_period["female"], width=12)
            male_entry.grid(row=row_index, column=3, sticky="w", padx=4, pady=3)
            female_entry.grid(row=row_index, column=4, sticky="w", padx=4, pady=3)
            ttk.Entry(table, textvariable=vars_for_period["description"], width=52).grid(row=row_index, column=5, sticky="ew", padx=4, pady=3)

            if not period.endswith("12"):
                male_entry.state(["disabled"])
                female_entry.state(["disabled"])

        table.columnconfigure(5, weight=1)

        def parse_cc_code(text: str) -> str:
            raw = (text or "").strip()
            if " - " in raw:
                raw = raw.split(" - ")[0].strip()
            return raw

        def clear_table():
            for vars_for_period in month_vars.values():
                for field_var in vars_for_period.values():
                    field_var.set("")
            bus_expat_count_var.set("0")
            bus_vietnamese_count_var.set("0")
            bus_description_var.set("")

        def validate_non_negative_int(raw, label):
            text = str(raw or "").strip()
            if not text:
                raise ValueError(f"{label} ph\u1ea3i l\u00e0 s\u1ed1 nguy\u00ean kh\u00f4ng \u00e2m.")
            if not text.isdecimal():
                raise ValueError(f"{label} ph\u1ea3i l\u00e0 s\u1ed1 nguy\u00ean kh\u00f4ng \u00e2m.")
            return str(int(text))

        def load_selected_cc(*_args):
            clear_table()
            cc_code = parse_cc_code(cc_var.get())
            if not cc_code:
                return
            bus_row_map = {
                str(row.get("cc_code", "")).strip(): row
                for row in self._read_manual_bus_headcount_rows(bus_csv_path)
            }
            bus_row = bus_row_map.get(cc_code)
            if bus_row:
                bus_expat_count_var.set(str(bus_row.get("bus_expat_count", "")).strip() or "0")
                bus_vietnamese_count_var.set(str(bus_row.get("bus_vietnamese_count", "")).strip() or "0")
                bus_description_var.set(str(bus_row.get("description", "")).strip())
            row_map = {
                (str(row.get("cc_code", "")).strip(), str(row.get("period", "")).strip()): row
                for row in self._read_manual_headcount_rows(csv_path)
            }
            for period in periods:
                row = row_map.get((cc_code, period))
                if not row:
                    continue
                month_vars[period]["staff"].set(str(row.get("headcount_staff", "")).strip())
                month_vars[period]["worker"].set(str(row.get("headcount_worker", "")).strip())
                month_vars[period]["male"].set(str(row.get("headcount_male", "")).strip())
                month_vars[period]["female"].set(str(row.get("headcount_female", "")).strip())
                month_vars[period]["description"].set(str(row.get("description", "")).strip())

        def save_current_cc():
            cc_code = parse_cc_code(cc_var.get())
            if not cc_code:
                messagebox.showerror("Lỗi", "Hãy chọn mã CC trước khi lưu.")
                return

            try:
                int(float(cc_code))
            except Exception:
                messagebox.showerror("Lỗi", "Mã CC không hợp lệ.")
                return

            def show_save_errors(errors):
                details = format_headcount_save_errors(errors)
                if details:
                    details = "\n\n" + details
                message = f"Lưu chưa hoàn tất cho CC {cc_code}. Không có thay đổi nào được áp dụng.{details}"
                self.log(message)
                messagebox.showerror("Lưu chưa hoàn tất", message)

            try:
                bus_expat_count = validate_non_negative_int(
                    bus_expat_count_var.get(), "Ng\u01b0\u1eddi bi\u1ec7t ph\u00e1i \u0111i xe bus"
                )
                bus_vietnamese_count = validate_non_negative_int(
                    bus_vietnamese_count_var.get(), "Ng\u01b0\u1eddi Vi\u1ec7t Nam \u0111i xe bus"
                )
            except ValueError as exc:
                show_save_errors(
                    [
                        _headcount_save_error(
                            "bus",
                            "bus_expat_count/bus_vietnamese_count",
                            f"{bus_expat_count_var.get()}/{bus_vietnamese_count_var.get()}",
                            "INTEGER_GTE_0",
                            str(exc),
                        )
                    ]
                )
                return

            existing_rows = self._read_manual_headcount_rows(csv_path)
            existing_bus_rows = self._read_manual_bus_headcount_rows(bus_csv_path)
            month_inputs = {
                period: {
                    "staff": month_vars[period]["staff"].get(),
                    "worker": month_vars[period]["worker"].get(),
                    "male": month_vars[period]["male"].get() if period.endswith("12") else "",
                    "female": month_vars[period]["female"].get() if period.endswith("12") else "",
                    "description": month_vars[period]["description"].get(),
                }
                for period in periods
            }
            period_rows, validation_errors = validate_headcount_save_period_rows(
                periods,
                month_inputs,
                label_by_period,
            )
            if validation_errors:
                show_save_errors(validation_errors)
                return

            new_rows = [row for row in existing_rows if str(row.get("cc_code", "")).strip() != cc_code]
            new_bus_rows = [row for row in existing_bus_rows if str(row.get("cc_code", "")).strip() != cc_code]
            new_bus_rows.append(
                {
                    "cc_code": cc_code,
                    "bus_expat_count": bus_expat_count,
                    "bus_vietnamese_count": bus_vietnamese_count,
                    "description": bus_description_var.get().strip(),
                }
            )
            saved_count = len(period_rows)

            for row in period_rows:
                new_rows.append(
                    {
                        "cc_code": cc_code,
                        "period": row["period"],
                        "headcount_staff": row["headcount_staff"],
                        "headcount_worker": row["headcount_worker"],
                        "headcount_male": row["headcount_male"],
                        "headcount_female": row["headcount_female"],
                        "description": row["description"],
                    }
                )

            new_rows.sort(key=lambda row: (str(row.get("cc_code", "")), str(row.get("period", ""))))
            new_bus_rows.sort(key=lambda row: str(row.get("cc_code", "")))

            valid_cc_codes = {parse_cc_code(choice) for choice in cc_choices if parse_cc_code(choice)}
            candidate_rows = []
            for row_number, row in enumerate(new_rows, start=2):
                candidate = dict(row)
                candidate["_csv_row"] = row_number
                candidate_rows.append(candidate)
            import_validation = validate_manual_headcount_rows(candidate_rows, valid_cc_codes, fiscal_year)
            if import_validation.get("errors", 0):
                show_save_errors(import_validation.get("error_details", []))
                return
            bus_validation_errors = validate_bus_headcount_save_rows(new_bus_rows, valid_cc_codes)
            if bus_validation_errors:
                show_save_errors(bus_validation_errors)
                return

            self._write_manual_headcount_rows(csv_path, new_rows)
            self._write_manual_bus_headcount_rows(bus_csv_path, new_bus_rows)
            db_path = os.path.join(BASE_DIR, "mp2027.db")
            conn = get_connection(db_path)
            try:
                create_schema(conn)
                result = parse_manual_headcount(conn, source_dir=source_dir)
            finally:
                conn.close()
            self.log(
                "Lưu nhân sự theo kỳ: CC={cc}, số dòng={rows}, tệp={path}; bus_file={bus_path}; DB inserted={inserted}, bus_inserted={bus_inserted}, errors={errors}".format(
                    cc=cc_code,
                    rows=saved_count,
                    path=csv_path,
                    bus_path=bus_csv_path,
                    inserted=result.get("inserted", 0),
                    bus_inserted=result.get("bus_inserted", 0),
                    errors=result.get("errors", 0),
                )
            )
            if result.get("errors", 0):
                show_save_errors(result.get("error_details", []))
                return
            messagebox.showinfo(
                "Đã lưu",
                "Đã lưu đầy đủ {rows} kỳ cho CC {cc}.\nCSV rows written={rows}; DB rows imported={inserted}; bus drivers written={bus_inserted}; errors=0.".format(
                    rows=saved_count,
                    cc=cc_code,
                    inserted=result.get("inserted", 0),
                    bus_inserted=result.get("bus_inserted", 0),
                ),
            )

        button_row = ttk.Frame(frame)
        button_row.grid(row=5, column=0, columnspan=8, sticky="w", pady=(12, 0))
        ttk.Button(button_row, text="Tải dữ liệu CC", command=load_selected_cc).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(button_row, text="Lưu 12 tháng", command=save_current_cc).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(button_row, text="Đóng", command=editor.destroy).grid(row=0, column=2, padx=(0, 6))

        cc_combo.bind("<<ComboboxSelected>>", load_selected_cc)
        if cc_choices:
            cc_var.set(cc_choices[0])
            load_selected_cc()

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
                "Có thể nhập account_jp_name để tự resolve account_code và unit_price_key để tự lấy đơn giá từ FY2027配賦額一覧. "
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
                "target_month/period = tháng ghi chi phí, ví dụ 202705 là tháng 5 FY2027.  "
                "event_type có thể dùng month_specific_driver cho event theo tháng riêng.  "
                "Nếu nhập unit_price thì đơn giá nhập tay được ưu tiên; nếu bỏ trống unit_price, nhập unit_price_key/allocation_content để tự lấy đơn giá từ FY2027配賦額一覧.  "
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
        tree.grid(row=8, column=0, columnspan=8, sticky="nsew", pady=(12, 0))
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
        button_row.grid(row=7, column=0, columnspan=8, sticky="w", pady=(10, 0))
        ttk.Button(button_row, text="Thêm/Cập nhật", command=add_or_update).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(button_row, text="Xóa đã chọn", command=remove_selected).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(button_row, text="Lưu tệp", command=save_file).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(button_row, text="Đóng", command=editor.destroy).grid(row=0, column=3, padx=(0, 6))

        def refresh_event_help(*_args):
            selected = event_var.get().strip()
            event_help_var.set(event_help.get(selected, "Gợi ý: hãy nhập số thật từ người phụ trách nghiệp vụ. Không nhập số ước lượng nếu chưa được chốt."))

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
        return os.path.join(os.getcwd(), f"OUTPUT_FY{self._current_fiscal_year()}")

    def _current_fiscal_year(self) -> int:
        try:
            return int(self.fiscal_year.get())
        except Exception:
            return 2027

    def _read_missing_inputs(self) -> list[dict[str, str]]:
        missing_path = os.path.join(self._audit_output_dir(), "MP2027_MISSING_INPUTS.csv")
        return self._read_csv_rows(missing_path)

    def _manual_event_ccs(self) -> set[str]:
        source_dir = self.source_dir.get() or BASE_DIR
        path = ensure_manual_event_drivers_template(source_dir, self._current_fiscal_year())
        return {
            str(row.get("cc_code", "")).strip()
            for row in self._read_csv_rows(path)
            if str(row.get("cc_code", "")).strip()
        }

    def _dashboard_cc_rows(self):
        db_path = os.path.join(BASE_DIR, "mp2027.db")
        if not os.path.exists(db_path):
            return []

        source_dir = self.source_dir.get() or BASE_DIR
        conn = get_connection(db_path)
        try:
            rows = conn.execute(
                """
                SELECT
                    cc.code,
                    cc.name_jp,
                    COALESCE(fid.fact_rows, 0) AS fact_rows,
                    COALESCE(fid.birthday_rows, 0) AS birthday_rows,
                    COALESCE(fid.nnn_rows, 0) AS nnn_rows,
                    COALESCE(fid.manual_event_rows, 0) AS manual_event_rows,
                    COALESCE(hc.manual_headcount_rows, 0) AS manual_headcount_rows
                FROM dim_cost_centers cc
                LEFT JOIN (
                    SELECT
                        CAST(cc_code AS TEXT) AS cc_code,
                        COUNT(*) AS fact_rows,
                        SUM(CASE WHEN source = 'birthday_workbook' THEN 1 ELSE 0 END) AS birthday_rows,
                        SUM(CASE WHEN source = 'nnn_paperwork' THEN 1 ELSE 0 END) AS nnn_rows,
                        SUM(CASE WHEN source = 'manual_event_driver' THEN 1 ELSE 0 END) AS manual_event_rows
                    FROM fact_input_data
                    GROUP BY CAST(cc_code AS TEXT)
                ) fid ON fid.cc_code = CAST(cc.code AS TEXT)
                LEFT JOIN (
                    SELECT CAST(cc_code AS TEXT) AS cc_code, COUNT(*) AS manual_headcount_rows
                    FROM fact_monthly_headcount
                    WHERE source = 'manual'
                    GROUP BY CAST(cc_code AS TEXT)
                ) hc ON hc.cc_code = CAST(cc.code AS TEXT)
                ORDER BY cc.code
                """
            ).fetchall()
        finally:
            conn.close()

        result = []
        for row in rows:
            fact_rows = int(row["fact_rows"] or 0)
            manual_hc = int(row["manual_headcount_rows"] or 0)
            manual_event = int(row["manual_event_rows"] or 0)
            if fact_rows <= 0:
                status = "ĐỎ"
                reason = "Chưa có dữ liệu tính toán sau lần chạy gần nhất"
            elif manual_event <= 0:
                status = "VÀNG"
                reason = "Cần rà soát sự kiện riêng; chưa có dữ liệu sự kiện nhập tay cho CC này"
            elif manual_hc <= 0:
                status = "VÀNG"
                reason = "Chưa có dữ liệu nhân sự nhập tay riêng cho CC này"
            else:
                status = "XANH"
                reason = "Có dữ liệu và không có cảnh báo cơ bản"
            result.append(
                (
                    status,
                    str(row["code"]),
                    str(row["name_jp"] or ""),
                    fact_rows,
                    manual_hc,
                    int(row["birthday_rows"] or 0),
                    int(row["nnn_rows"] or 0),
                    manual_event,
                    reason,
                )
            )
        return result

    def _preview_formula_rows(self, cc_code: str | None):
        if not cc_code:
            cc_code = self._parse_selected_cc_code()
        if not cc_code:
            return []
        path = os.path.join(self._audit_output_dir(), f"MP_CC_{cc_code}.xlsx")
        if not os.path.exists(path):
            return []

        try:
            import openpyxl

            wb = openpyxl.load_workbook(path, data_only=False)
            try:
                ws = wb["内訳ﾘｽﾄ(4～3月)"] if "内訳ﾘｽﾄ(4～3月)" in wb.sheetnames else wb[wb.sheetnames[0]]
                result = []
                for row_index in [44, 45, 59, 75, 97, 98, 137]:
                    result.append(
                        (
                            row_index,
                            ws.cell(row_index, 19).value or "",
                            ws.cell(row_index, 6).value or "",
                            ws.cell(row_index, 7).value or "",
                            ws.cell(row_index, 17).value or "",
                            ws.cell(row_index, 18).value or "",
                        )
                    )
                return result
            finally:
                wb.close()
        except Exception:
            return []

    def open_audit_dashboard(self):
        dashboard = tk.Toplevel(self.root)
        dashboard.title("Dashboard kiểm toán - MP2027")
        dashboard.geometry("1280x820")

        frame = ttk.Frame(dashboard, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Dashboard kiểm toán", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            frame,
            text=(
                "Mục tiêu: nhìn một lần là biết CC nào dùng được, CC nào cần kiểm tra, CC nào chưa có dữ liệu. "
                "Chương trình không tự bịa số; chỗ nào thiếu sẽ yêu cầu người dùng nhập/chốt."
            ),
            wraplength=1180,
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(4, 6))

        legend = ttk.LabelFrame(frame, text="Cách đọc đèn")
        legend.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(0, 8))
        ttk.Label(legend, text="XANH: có thể mở tệp kết quả để kiểm tra công thức.").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        ttk.Label(legend, text="VÀNG: có dữ liệu nhưng còn việc cần người dùng chốt.").grid(row=0, column=1, sticky="w", padx=18, pady=4)
        ttk.Label(legend, text="ĐỎ: chưa có dữ liệu tính toán cho CC này.").grid(row=0, column=2, sticky="w", padx=18, pady=4)

        summary_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=summary_var, font=("Segoe UI", 10, "bold")).grid(row=3, column=0, columnspan=4, sticky="w", pady=(0, 8))

        cc_columns = ("status", "cc_code", "name", "fact_rows", "manual_hc", "birthday", "nnn", "manual_event", "reason")
        cc_tree = ttk.Treeview(frame, columns=cc_columns, show="headings", height=14)
        for col, width, text in [
            ("status", 70, "Đèn"),
            ("cc_code", 110, "CC"),
            ("name", 230, "Tên phòng"),
            ("fact_rows", 95, "Dòng dữ liệu"),
            ("manual_hc", 110, "Dòng nhân sự"),
            ("birthday", 95, "Sinh nhật"),
            ("nnn", 65, "NNN"),
            ("manual_event", 115, "Sự kiện nhập tay"),
            ("reason", 360, "Lý do"),
        ]:
            cc_tree.heading(col, text=text)
            cc_tree.column(col, width=width, anchor="w")
        cc_tree.tag_configure("XANH", background="#e8f5e9")
        cc_tree.tag_configure("VÀNG", background="#fff8dc")
        cc_tree.tag_configure("ĐỎ", background="#fdecea")
        cc_tree.grid(row=4, column=0, columnspan=4, sticky="nsew")
        cc_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=cc_tree.yview)
        cc_tree.configure(yscrollcommand=cc_scroll.set)
        cc_scroll.grid(row=4, column=4, sticky="ns")

        ttk.Label(frame, text="Việc cần người dùng chốt").grid(row=5, column=0, sticky="w", pady=(12, 4))
        missing_columns = ("severity", "cc_code", "period", "area", "action")
        missing_tree = ttk.Treeview(frame, columns=missing_columns, show="headings", height=6)
        for col, width, text in [
            ("severity", 85, "Mức"),
            ("cc_code", 120, "CC"),
            ("period", 180, "Kỳ"),
            ("area", 180, "Hạng mục"),
            ("action", 650, "Cần làm"),
        ]:
            missing_tree.heading(col, text=text)
            missing_tree.column(col, width=width, anchor="w")
        missing_tree.grid(row=6, column=0, columnspan=4, sticky="nsew")

        ttk.Label(frame, text="Xem trước công thức trong tệp kết quả của CC đã chọn").grid(row=7, column=0, sticky="w", pady=(12, 4))
        preview_columns = ("row", "description", "F", "G", "Q", "R")
        preview_tree = ttk.Treeview(frame, columns=preview_columns, show="headings", height=8)
        for col, width, text in [
            ("row", 60, "Dòng"),
            ("description", 360, "Nội dung"),
            ("F", 210, "F"),
            ("G", 210, "G"),
            ("Q", 210, "Q"),
            ("R", 160, "Tổng"),
        ]:
            preview_tree.heading(col, text=text)
            preview_tree.column(col, width=width, anchor="w")
        preview_tree.grid(row=8, column=0, columnspan=4, sticky="nsew")

        frame.rowconfigure(4, weight=2)
        frame.rowconfigure(6, weight=1)
        frame.rowconfigure(8, weight=1)
        frame.columnconfigure(3, weight=1)

        def selected_dashboard_cc():
            selected = cc_tree.selection()
            if selected:
                return str(cc_tree.item(selected[0], "values")[1])
            return self._parse_selected_cc_code()

        def refresh_dashboard():
            for tree in (cc_tree, missing_tree, preview_tree):
                for item in tree.get_children():
                    tree.delete(item)

            rows = self._dashboard_cc_rows()
            counts = {"XANH": 0, "VÀNG": 0, "ĐỎ": 0}
            for row in rows:
                counts[row[0]] = counts.get(row[0], 0) + 1
                cc_tree.insert("", tk.END, values=row, tags=(row[0],))
            summary_var.set(
                f"XANH={counts.get('XANH', 0)} | VÀNG={counts.get('VÀNG', 0)} | ĐỎ={counts.get('ĐỎ', 0)} | Tổng CC={len(rows)}"
            )

            for row in self._read_missing_inputs():
                missing_tree.insert(
                    "",
                    tk.END,
                    values=(
                        row.get("severity", ""),
                        row.get("cc_code", ""),
                        row.get("period", ""),
                        row.get("area", ""),
                        row.get("action", ""),
                    ),
                )

            refresh_preview()

        def refresh_preview(*_args):
            for item in preview_tree.get_children():
                preview_tree.delete(item)
            cc_code = selected_dashboard_cc()
            for row in self._preview_formula_rows(cc_code):
                preview_tree.insert("", tk.END, values=row)

        def open_audit_report():
            self._open_path(os.path.join(self._audit_output_dir(), "MP2027_AUDIT_REPORT.md"))

        def open_missing_csv():
            self._open_path(os.path.join(self._audit_output_dir(), "MP2027_MISSING_INPUTS.csv"))

        def open_output_workbook():
            cc_code = selected_dashboard_cc()
            if not cc_code:
                messagebox.showwarning("Chưa chọn CC", "Hãy chọn CC trên Dashboard trước.")
                return
            self._open_path(os.path.join(self._audit_output_dir(), f"MP_CC_{cc_code}.xlsx"))

        button_row = ttk.Frame(frame)
        button_row.grid(row=9, column=0, columnspan=4, sticky="w", pady=(12, 0))
        ttk.Button(button_row, text="Tải lại Dashboard", command=refresh_dashboard).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(button_row, text="Nhập dữ liệu thiếu", command=self.open_event_driver_editor).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(button_row, text="Mở báo cáo kiểm toán", command=open_audit_report).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(button_row, text="Mở danh sách thiếu", command=open_missing_csv).grid(row=0, column=3, padx=(0, 6))
        ttk.Button(button_row, text="Mở tệp kết quả CC", command=open_output_workbook).grid(row=0, column=4, padx=(0, 6))
        ttk.Button(button_row, text="Đóng", command=dashboard.destroy).grid(row=0, column=5, padx=(0, 6))

        cc_tree.bind("<<TreeviewSelect>>", refresh_preview)
        refresh_dashboard()

    def start_pipeline(self):
        try:
            fiscal_year = int(self.fiscal_year.get())
            exchange_rate = float(EXCHANGE_RATE_USD_VND)

            cc_raw = self.cc_code_filter.get().strip()
            target_cc = None
            if cc_raw:
                target_cc = cc_raw.split(" - ")[0].strip() if " - " in cc_raw else cc_raw

            template = self.template_path.get()
            source = self.source_dir.get()
            if not os.path.exists(template) or not os.path.exists(source):
                messagebox.showerror("Lỗi", "Đường dẫn tệp mẫu hoặc thư mục nguồn không hợp lệ.")
                return

            if _is_legacy_root_template(template):
                messagebox.showerror(
                    "Lỗi",
                    "Không được dùng FORM.xlsx ở thư mục gốc vì tệp này còn công thức mẫu cũ. Hãy dùng docs/MP2027/FORM.xlsx.",
                )
                return

            # Ensure master data is in sync only after the selected paths are validated.
            self.auto_init_master_data()
            self.start_btn.configure(state=tk.DISABLED)
            self.log("--- BẮT ĐẦU TÍNH TOÁN ---")
            self.log(f"Tệp mẫu xác nhận chạy: {template}")
            self.log(f"Thư mục nguồn xác nhận chạy: {source}")
            threading.Thread(
                target=self.run_process,
                args=(fiscal_year, template, source, exchange_rate, target_cc),
                daemon=True,
            ).start()
        except Exception as exc:
            messagebox.showerror("Lỗi nhập liệu", str(exc))

    def run_process(self, fiscal_year: int, template: str, source: str, rate: float, target_cc: int | None):
        success, result = run_universal_pipeline(
            fiscal_year=fiscal_year,
            template_path=template,
            source_dir=source,
            exchange_rate=rate,
            target_cc=target_cc,
            log_callback=self.log,
        )
        if success:
            self.log(f"THÀNH CÔNG. Kết quả: {result}")
            self.root.after(100, self.load_cc_list)
            messagebox.showinfo("Hoàn tất", f"Quá trình xuất dữ liệu hoàn tất.\n\nKết quả: {result}")
        else:
            self.log(f"THẤT BẠI: {result}")
            messagebox.showerror("Thất bại", str(result))
        self.start_btn.configure(state=tk.NORMAL)


if __name__ == "__main__":
    root = tk.Tk()
    app = MPManagerApp(root)
    root.mainloop()
