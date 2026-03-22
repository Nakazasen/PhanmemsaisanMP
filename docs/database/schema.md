# Đặc tả Cơ sở Dữ liệu - MP2027 Manager

Hệ thống sử dụng SQLite 3 làm database trung tâm. Cấu trúc gồm 6 bảng chính được chuẩn hóa.

## 1. Bảng dim_cost_centers (Danh mục Bộ phận)
Lưu thông tin các Cost Center và định mức nhân sự.
- **code**: Mã CC (PK).
- **staff_count**: Nhân sự văn phòng.
- **worker_count**: Công nhân G7.
- **saisan_type**: Loại hình sản xuất/gián tiếp.

## 2. Bảng dim_accounts (Danh mục Tài khoản)
Lưu mã tài khoản kế toán và phân nhóm lợi nhuận.
- **code**: Mã tài khoản (PK).
- **mfg_code**: Mã kế toán cho khối Sản xuất.
- **ga_code**: Mã kế toán cho khối Hành chính.
- **sales_code**: Mã kế toán cho khối Bán hàng.

## 3. Bảng map_allocation_rules (Quy tắc Phân bổ)
Lưu các định mức chi phí và logic phân bổ.
- **unit_price**: Đơn giá (VND/USD).
- **driver_type**: Loại hình driver (`headcount_all`, `headcount_staff`, `headcount_worker`, `working_days`, `fixed_ratio`).

## 4. Bảng fact_input_data (Dữ liệu Ghi chép - Hub)
Bảng trung tâm chứa toàn bộ giao dịch tài chính.
- **period**: Kỳ kế toán (YYYYMM).
- **amount_vnd**: Số tiền quy đổi.
- **cc_code / account_code**: Các mã đã được mapping.

## 5. Bảng fact_allocation_log (Nhật ký Phân bổ)
Lưu vết chi tiết quá trình engine tính toán để phục vụ Audit.
- **rule_id**: Luật được áp dụng.
- **driver_value / driver_total**: Các tham số đầu vào của phép tính phân bổ.

## 6. Bảng sys_params (Tham số Hệ thống)
Lưu các biến cấu hình: `exchange_rate_usd_vnd`, `fiscal_year`, `fy_start`, `fy_end`.
