# MP2027: Đặc tả Kỹ thuật & Kế hoạch Phát triển Ứng dụng (V2.0)

## 1. Mục tiêu Hệ thống
Xây dựng công cụ tự động hóa việc tổng hợp dữ liệu từ các phòng ban (Facility, GA, IT) vào file Master Plan (MP FY2027), thay thế việc nhập liệu thủ công, đảm bảo tính chính xác của việc phân bổ chi phí (Allocation) và hỗ trợ mô phỏng kịch bản (Simulation).

## 2. Luồng dữ liệu Chi tiết (Data Mapping)

### A. Nguồn đầu vào (Input Sources):
1.  **Facility (施設課):**
    *   Data: Khấu hao (Depreciation), Lãi vay (Interest), Điện nước (E&W).
    *   Logic: Ánh xạ theo CC_Code và Account_Code vào sheet tương ứng trong FORM.xlsx.
2.  **General Affairs (総務課):**
    *   Data: Xe bus, Gas, Vệ sinh, Tuyển dụng.
    *   Logic: Tính toán dựa trên số ngày làm việc (Working Days) và Số người (Headcount).
3.  **System/IT Simulation:**
    *   Data: SAP, PLM, AMS fees.
    *   Logic: Xử lý quy đổi USD/VND và ánh xạ theo kịch bản giá.

### B. Quy tắc Phân bổ (Allocation Engine):
*   **Nguồn phân bổ:** Các chi phí chung (Common Costs) từ các CC hỗ trợ.
*   **Tiêu chí phân bổ (Drivers):**
    *   Headcount (Số người).
    *   Working Days (Số ngày làm việc).
    *   Fixed Ratio (Tỷ lệ cố định quy định trong file `FY2027配賦額一覧`).
*   **Công thức:** `Chi phí Bộ phận = Tổng chi phí chung * (Driver của bộ phận / Tổng Driver)`.

## 3. Cấu trúc Database (Technical Schema)

### Tables:
*   `dim_cost_centers`: (code, name_jp, name_vn, dept, expense_type [製造/一般/販促])
*   `dim_accounts`: (code, name_jp, name_vn, group_id)
*   `fact_input_data`: (source, period, amount_vnd, amount_usd, cc_code, account_code, scenario_id)
*   `map_allocation_rules`: (source_cc, dest_cc, account_code, ratio_percent, driver_type)
*   `sys_params`: (exchange_rate_usd_vnd, fiscal_year)

## 4. Yêu cầu Chức năng cho Agent Lập trình

### Module 1: Excel Parser (Surgical Accuracy)
*   Phải đọc được dữ liệu từ các file có cấu trúc không đồng nhất (nhiều header, merge cell).
*   Tự động nhận diện Tháng (T4 -> T3) từ cột/sheet.

### Module 2: Allocation Processor
*   Thực hiện tính toán phân bổ 2 bước (Step-down allocation) nếu cần.
*   Lưu kết quả trung gian vào database để truy xuất (Audit trail).

### Module 3: Report Generator
*   Sử dụng thư viện (như `openpyxl`) để ghi dữ liệu vào đúng cell trong `FORM.xlsx` mà không làm hỏng định dạng/công thức có sẵn của file mẫu.

## 5. Danh sách Kiểm tra Hoàn thiện (Definition of Done)
1. [ ] Đọc được dữ liệu từ 5 file nguồn tiêu biểu.
2. [ ] Thực hiện đúng logic phân bổ trong `FY2027配賦額一覧`.
3. [ ] Quy đổi được tỷ giá USD/VND theo tham số cấu hình.
4. [ ] Xuất ra file `FORM.xlsx` trùng khớp số liệu tổng hợp.
5. [ ] Có chức năng so sánh giữa Scenario thực tế và Simulation.
