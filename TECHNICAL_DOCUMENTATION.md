# TECHNICAL DOCUMENTATION — MP2027 Manager

Tài liệu này hướng dẫn cách mở rộng và bảo trì hệ thống MP2027 Manager dành cho lập trình viên (hoặc người dùng có kiến thức cơ bản về Python).

---

## 1. Cách thêm một Parser mới (Nguồn dữ liệu mới)

Nếu có một phòng ban mới (ví dụ: Phòng Kinh doanh) cung cấp file Excel ngân sách riêng, hãy thực hiện các bước sau:

### Bước 1: Tạo file Parser mới
Tạo file `src/parsers/sales.py`. Cấu trúc chuẩn của một hàm parse nên như sau:

```python
import pandas as pd
import sqlite3
import os
from src.utils.excel_helpers import extract_cc_code, get_fy_months

def parse_sales(conn: sqlite3.Connection, source_dir: str):
    # 1. Tìm file trong source_dir
    # 2. Đọc Excel bằng pandas
    # 3. Lặp qua các dòng và trích xuất dữ liệu
    
    cursor = conn.cursor()
    # Định dạng bản ghi chuẩn để insert vào fact_input_data:
    # (source, period, amount_vnd, cc_code, account_code, scenario_id, description)
    # Ghi chú: Để account_code = 0 để Allocation Engine tự động map theo keyword.
    
    cursor.execute("INSERT INTO fact_input_data ...")
    conn.commit()
```

### Bước 2: Đăng ký vào Pipeline trung tâm
Mở file `scripts/run_e2e.py`, import hàm mới và gọi nó trong bước 4:

```python
from src.parsers.sales import parse_sales  # Thêm dòng này

def run_universal_pipeline(...):
    # ... các bước trước ...
    
    # 4. Run Parsers
    parse_sales(conn, source_dir=source_dir)  # Đăng ký tại đây
    
    # ... các bước sau ...
```

---

## 2. Cách thêm hoặc sửa Luật phân bổ (Allocation Rule)

Hệ thống được thiết kế để thay đổi logic phân bổ mà **KHÔNG cần sửa code**, chỉ cần cập nhật Database.

### Cấu trúc bảng `map_allocation_rules`
Bảng này nằm trong `data/mp2027.db`, bao gồm các cột chính:
- `item_name`: Tên loại chi phí (VD: Tiền Bus, Tiền Vệ sinh).
- `unit_price`: Đơn giá (VND/đơn vị).
- `driver_type`: Tiêu chí chia. Gồm:
    - `headcount_all`: Chia đều theo tổng nhân sự (Staff + Worker).
    - `headcount_worker`: Chỉ chia theo số công nhân G7.
    - `headcount_staff`: Chỉ chia theo số nhân viên văn phòng.
    - `working_days`: Chia theo số ngày làm việc của tháng đó.
- `mfg_account / ga_account / sales_account`: Mã tài khoản đích tùy theo loại Cost Center nhận chi phí.

### Cách thêm luật mới (Ví dụ: Chia theo diện tích)
Nếu bạn muốn thêm luật chia theo diện tích (Square Meters), bạn cần:
1.  Mở Database (bằng công cụ như SQLite Browser).
2.  Thêm cột `area_sqm` vào bảng `dim_cost_centers`.
3.  Trong code `src/engine/allocator.py`, bổ sung một khối `elif driver_type == 'area': driver_val = cc['area_sqm']` (Đây là phần duy nhất cần chạm vào code nếu driver hoàn toàn mới).
4.  Thêm dòng dữ liệu mới vào bảng `map_allocation_rules` với `driver_type = 'area'`.

---

## 3. Sơ đồ luồng dữ liệu (Data Flow)

Hệ thống hoạt động theo mô hình tuyến tính để đảm bảo tính toàn vẹn đặc biệt của file Excel Master:

1.  **Extract (Trích xuất)**: Các module trong `src/parsers/` đọc dữ liệu từ các file Excel rời rạc của phòng ban.
2.  **Transform (Chuyển đổi)**:
    *   Toàn bộ dữ liệu thô được đổ vào bảng `fact_input_data` (Hub) trong SQLite.
    *   **Allocation Engine**: Quét Hub, áp dụng các luật từ `map_allocation_rules` để sinh ra các bản ghi chi phí phân bổ chi tiết.
    *   **Mapping**: Tự động gán mã tài khoản (Account Code) dựa trên từ khóa trong mô tả và loại CC đích.
3.  **Load (Nạp)**:
    *   **Hub Builder**: Lấy dữ liệu đã xử lý từ Database, xoay trục (Pivot) thành 12 tháng.
    *   Ghi đè dữ liệu vào đúng sheet `内訳ﾘｽﾄ` của file `FORM.xlsx`.
    *   Excel tự động tính toán lại các sheet `採算表` nhờ các công thức có sẵn.

---

## 💡 Nguyên tắc "Vàng" khi bảo trì
- **Tuyệt đối không hard-code năm**: Luôn lấy `fiscal_year` từ bảng `sys_params`.
- **Dùng `py` thay vì `python`**: Để tương thích với môi trường Windows của người dùng.
- **Log everything**: Luôn dùng `log_callback` trong pipeline để người dùng thấy tiến độ trên GUI.
