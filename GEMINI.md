# MP2027 Manager - Trạng thái hiện tại và Ghi chú bàn giao

Lần cập nhật cuối: 2026-03-24

Tệp này được viết bằng văn bản an toàn với ASCII để tránh các vấn đề về console Windows CP932/Shift-JIS và lỗi hiển thị (mojibake).

## Đã xác minh hoạt động (tính đến 2026-03-23)

- Nhập (Imports): Các module cốt lõi được nạp mà không có lỗi cú pháp hoặc import.
- Kiểm thử (Tests): Lệnh `py -m pytest tests\\test_src_v2_logic.py -q` đã vượt qua.
- E2E: Lệnh `py scripts\\run_e2e.py --fy 2027 --template FORM.xlsx --source .` hoàn thành và tạo ra các tệp đầu ra trong thư mục `OUTPUT_FY2027`.

## Những gì đang hoạt động đầu-cuối (End-to-End)

- Dữ liệu Master được nạp từ `FORM.xlsx`:
  - Trung tâm chi phí (`dim_cost_centers`)
  - Tài khoản (`dim_accounts`)
  - Tỷ giá USD/VND nguồn chuẩn (SSOT) từ `FORM.xlsx!B2`
- Các bộ phân tích chi phí trực tiếp ghi vào `fact_input_data`:
  - facility (cơ sở hạ tầng)
  - fixed_assets (tài sản cố định)
  - it_sim (mô phỏng IT)
  - ga_unit_price (đơn giá GA)
- Xuất dữ liệu (Export) ghi vào sheet hub trong `FORM.xlsx` và tạo ra các tệp kết quả cho từng trung tâm chi phí (CC).

## Nhập nhân sự thủ công (Dành cho người dùng)

Khi không có nguồn dữ liệu nhân sự cấp trung tâm chi phí (CC) đáng tin cậy, người dùng có thể nhập nhân sự hàng tháng theo cách thủ công:

- Giao diện (GUI): `src/universal_app.py` cung cấp cửa sổ "Nhập nhân sự thủ công".
- CSV: Ghi vào `headcount_manual.csv` (UTF-8 có BOM) và nạp vào bảng `fact_monthly_headcount` với nguồn `source='manual'`.
- Độ ưu tiên: Nhân sự nhập thủ công sẽ ghi đè lên nhân sự từ GA cho cùng cặp `(cc_code, period)`.

Tài liệu: `docs/MANUAL_HEADCOUNT_INPUT.md`

## Các khoảng cách hiện có (Chưa được xác minh 100% về độ chính xác nghiệp vụ)

- Kết quả phân bổ quản lý (Administrative allocation) vẫn còn thiếu:
  - Sau khi chạy E2E, không có hàng nào có `source like 'alloc_%'` trong bảng `fact_input_data`.
- Nhân sự hàng tháng từ GA có thể không khớp với định dạng mã trung tâm chi phí trong `FORM.xlsx`:
  - Ví dụ thực tế: `1136`, `40237000` so với mã chuẩn như `1412000004`.
- Các quy tắc nghiệp vụ cho `posting_month` (tháng hạch toán) chưa được triển khai đầy đủ hoặc được khóa bởi các test case.
- `working_days` (ngày làm việc) là một tham số (driver) riêng biệt và không nên được tra cứu qua logic nhân sự.
- Việc nạp `map_allocation_rules` không có tính nhất quán (dữ liệu bị tích lũy qua các lần chạy).

## Các bước tiếp theo (Thứ tự đề xuất)

1. Sửa/chuẩn hóa việc trích xuất mã trung tâm chi phí cho dữ liệu nhân sự GA (hoặc dựa vào nhập liệu thủ công).
2. Triển khai và xác minh logic `posting_month` cho từng loại quy tắc bằng các unit test tập trung.
3. Triển khai việc tra cứu driver `working_days` từ bảng `sys_params` (không phải từ nhân sự).
4. Làm cho việc nạp `map_allocation_rules` có tính nhất quán (xóa/thay thế trước khi nạp).
5. Đối chiếu kết quả theo từng quy tắc với file `FY2027配賦額一覧` và file "Cải tiến nhập dữ liệu chung...".

