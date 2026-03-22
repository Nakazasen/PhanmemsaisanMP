# Refactor Khấu Hao, Tỷ Giá, và GA cho MP2027

## Summary
- Refactor theo đúng workbook thật và spec V4, không dùng số hardcode cho tỷ giá, cột tháng, hay logic tháng cuối khấu hao.
- `FORM.xlsx` sheet [`内訳ﾘｽﾄ(4～3月)`](/c:/ProgramData/Sandbox/MP2027/FORM.xlsx) ô `B2` là nguồn tỷ giá duy nhất cho toàn pipeline.
- Fixed Assets phải đọc từ workbook `固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx`, sheet `2025.11`, dùng đúng các cột:
  `H/8` CC, `L/12` monthly depreciation, `P/16` last depreciation month, `Q/17` last month depreciation, `V/22` interest April 2026, `W/23` interest from May 2026.
- GA nằm trong phạm vi refactor, nhưng phân bổ đúng xuống từng CC theo tháng chỉ được triển khai khi có nguồn HR headcount theo `CC x month`; không dùng fallback bịa từ dữ liệu tĩnh hiện có.

## Implementation Changes
- Thêm một helper đọc tỷ giá từ `FORM.xlsx` hub sheet `内訳ﾘｽﾄ(4～3月)!B2`, parse numeric an toàn, và dùng helper này ở mọi điểm đang nhận/seed tỷ giá:
  `src/db/loader.py`, `scripts/run_e2e.py`, `src/parsers/facility.py`, `src/parsers/fixed_assets.py`, `src/engine/allocator.py`, và UI/CLI.
- Giữ chữ ký hàm cũ để giảm blast radius, nhưng `exchange_rate` truyền vào chỉ còn vai trò hiển thị/log; giá trị thực tế luôn nạp từ workbook và ghi lại vào `sys_params.exchange_rate_usd_vnd`.
- Refactor `src/parsers/fixed_assets.py` để bỏ cách đọc “12 cột tháng có sẵn” hiện tại. Parser phải:
  đọc từng asset row từ sheet `2025.11`,
  chuẩn hóa `Last Depreciation Month` về `YYYYMM`,
  expand ra 12 kỳ FY bằng thuật toán:
  `curr < last_month` => dùng `November 2025 Depreciation`,
  `curr == last_month` => dùng `Last Month Depr`,
  `curr > last_month` => không insert record nào cho depreciation.
- Trong cùng parser FA, sinh riêng records interest:
  `202604` dùng cột `Interest in April 2026`,
  `202605..202703` dùng cột `Interest from May 2026`,
  chỉ insert đến hết `Last Depreciation Month`; sau đó không insert.
- Gắn `amount_usd` cho mọi dòng FA nguồn USD và `amount_vnd = ROUND(usd * exchange_rate, 0)` trước khi insert vào `fact_input_data`.
- Chuẩn hóa description/source của FA để allocator map được riêng depreciation và interest nếu cần audit, ví dụ theo nhóm `fixed_assets_depr` và `fixed_assets_interest`.
- Cập nhật `src/engine/allocator.py` để:
  bỏ default hardcoded `25450` khỏi logic nghiệp vụ,
  map cost type theo đúng thuật ngữ thực tế `製造 / 一般 / 販売`,
  không tính lại số FA đã được parser expand đúng tháng,
  chỉ làm phần account mapping và allocation cho các nguồn cần phân bổ.
- Refactor GA theo hướng dữ liệu thật:
  parser GA chỉ đọc authoritative monthly unit prices / monthly working days / monthly total headcount từ workbook tổng vụ,
  không dùng `dim_cost_centers.staff_count/worker_count` hiện tại làm nguồn sự thật.
- Bổ sung một input source mới cho HR headcount theo `cc_code + period`, rồi allocator GA dùng nguồn này để tính `amount = monthly_unit_price * monthly_driver_by_cc`.
- Với GA, xử lý merged-cell CC bằng forward fill trước khi tính; các mục “12 tháng giống nhau”, “đơn giá theo tháng”, và “tháng đặc thù” phải lấy trực tiếp từ workbook, không hardcode.
- Giữ export hub-centric hiện tại; không đổi model ghi vào `内訳ﾘｽﾄ(4～3月)` ngoài việc bảo đảm các tháng không có record sẽ lên hub thành `0`.

## Public Interfaces / Data Contracts
- `run_universal_pipeline(...)` và UI vẫn giữ tham số tỷ giá để tương thích, nhưng pipeline luôn override bằng `FORM.xlsx!内訳ﾘｽﾄ(4～3月)!B2`.
- `sys_params.exchange_rate_usd_vnd` trở thành mirror của workbook thay vì cấu hình nhập tay.
- Thêm contract dữ liệu mới cho GA headcount theo CC-tháng:
  tối thiểu gồm `period`, `cc_code`, `headcount_all` và nếu cần `headcount_staff`, `headcount_worker`.
- `fact_input_data` tiếp tục là fact table đích; không thêm schema mới cho FA nếu parser đã expand đủ 12 kỳ trước khi insert.

## Test Plan
- Thêm unit tests cho helper đọc tỷ giá:
  đọc đúng `B2` từ hub sheet,
  fail rõ ràng nếu sheet hub hoặc `B2` không hợp lệ.
- Thêm unit tests cho hàm expand depreciation:
  asset No.3 có `Last Depreciation Month = 202605`:
  `202604` dùng monthly depreciation,
  `202605` dùng last month depreciation,
  `202606+` bằng `0`.
- Thêm unit tests cho asset No.23:
  `202604..202610` dùng monthly depreciation,
  `202611` dùng last month depreciation,
  `202612..202703` bằng `0`.
- Thêm unit tests interest:
  `202604` lấy từ cột April,
  `202605+` lấy từ cột May onward,
  mọi tháng sau `Last Depreciation Month` bằng `0`.
- Thêm integration test pipeline tối thiểu:
  chạy parse/load/allocate/export với fixture FA + FORM,
  xác nhận hub cho asset kết thúc khấu hao tháng `11/2026` có giá trị tháng `12/2026` là `0 VND`.
- Thêm test hồi quy tỷ giá:
  đổi `B2` trong fixture `FORM.xlsx`, chạy pipeline lại, xác nhận mọi dòng USD đổi kết quả tương ứng.
- Với GA, thêm test parser cho monthly unit price/working days/headcount total và test allocator dùng fixture HR-by-CC-tháng để chứng minh số người biến động theo tháng làm thay đổi amount.

## Assumptions
- `FORM.xlsx!内訳ﾘｽﾄ(4～3月)!B2` là vị trí tỷ giá chính thức cần đọc.
- Sheet FA chuẩn cho FY2027 là `2025.11`; header row là dòng 4 và dữ liệu bắt đầu từ dòng 5.
- Các tháng sau khi asset hết khấu hao/lãi được biểu diễn bằng việc không insert record, để pivot/export tự ra `0`.
- GA phân bổ đúng theo CC-tháng yêu cầu một nguồn HR headcount theo CC; repo hiện tại chưa có nguồn này, nên implementer phải tích hợp source đó trước khi coi phần GA là hoàn tất.
- Không giữ bất kỳ fallback hardcoded nào cho tỷ giá, monthly depreciation, interest, hay driver GA.
