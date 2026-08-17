# Chiến lược test và các profile phát hành MP2027

## Danh mục hiện tại

Số lượng chính thức được sinh lại bằng quality baseline tĩnh và quá trình collection của pytest thay vì duy trì thủ công. Bộ test bao gồm hồi quy source/bộ đọc, hành vi bộ máy, test có xử lý Excel, migration, sức khỏe runtime, hợp đồng đóng gói và test an toàn cho gói cập nhật/nội dung dựa trên hash.

## Các profile test

| Profile | Lệnh | Mục đích | Chính sách dữ liệu runtime |
|---|---|---|---|
| Nhanh | `py -m pytest -m "not requires_raw_excel and not real_pipeline_acceptance and not performance" -q` | Phản hồi cho pull request | Không dùng workbook raw riêng tư |
| An toàn cho CI | `py -m pytest -m "not requires_raw_excel and not real_pipeline_acceptance and not performance" -q` | Cổng CI Linux/Windows | Cho phép fixture tích hợp tổng hợp |
| Đầy đủ tại máy cục bộ | `py -m pytest -m "not performance" -q` | Hồi quy thông thường đầy đủ | Dùng các đầu vào raw đã chọn lọc/riêng tư nếu có |
| Nghiệm thu | `py -m pytest -m real_pipeline_acceptance -q` | Nghiệm thu CLI/nghiệp vụ thực | Chạy rõ ràng, chậm, chỉ tại máy cục bộ |
| Hiệu năng | `$env:MP_MANAGER_RUN_PERFORMANCE='1'; py -m pytest -m performance -q` | Ngân sách hiệu năng chạy rõ ràng | Chỉ dùng dữ liệu tổng hợp |
| Đóng gói | `py scripts/package_app.py` | Build ứng dụng/trình khởi chạy onedir, kiểm tra sức khỏe bản đóng gói, tạo gói cài | Thư mục runtime test nhanh cách ly |
| Kiểm toán tĩnh | `py scripts/generate_quality_baseline.py` | Danh mục code và phát hiện tĩnh | Không bao giờ mở dữ liệu runtime |

## Chính sách phân loại test

- `unit`: hàm thuần hoặc thành phần cách ly; mục tiêu dưới 1 giây.
- `integration`: nhiều thành phần nguồn/cơ sở dữ liệu với fixture tổng hợp.
- `requires_raw_excel`: cần workbook cục bộ/riêng tư và không an toàn cho CI.
- `real_pipeline_acceptance`: gọi CLI thực với đầu vào được chỉ định rõ.
- `performance`: benchmark bật theo yêu cầu; không thuộc phản hồi thông thường cho developer.

Các marker hiện có tiếp tục là nguồn chính thức cho đến khi từng test được chuyển đổi. Công việc mới phải dùng marker hẹp nhất mô tả đúng nhu cầu dữ liệu và thời gian chạy.

## Kỳ vọng hồi quy cố định

Các hành vi sau được bảo vệ ở cấp phát hành:

- đường dẫn dự án tương đối được xác định từ `project.json`, không phải thư mục làm việc hiện tại;
- dữ liệu runtime đã đóng gói có thể ghi bên ngoài `_MEIPASS`;
- thiếu dữ liệu nguồn phải từ chối an toàn và tạo kết quả đầu vào thiếu có thể kiểm toán;
- kiểm tra sức khỏe hằng năm và các quy tắc phân bổ khác dùng driver thực, không dùng số dòng;
- việc tạo schema không phá dữ liệu và cơ sở dữ liệu cũ được migration an toàn;
- artifact có hash sai, đường dẫn không an toàn, file ngoài dự kiến và kích thước không khớp;
- xác minh gói bắt buộc có tài nguyên và chạy `--health-check` của bản đóng gói.

## Ma trận đặc trưng hóa quy tắc nghiệp vụ

Ma trận này ghi nhận lớp bảo vệ có thể thực thi, không khẳng định mọi workbook có thể có đều đã được nghiệm thu. “Được bảo vệ” nghĩa là test tổng hợp/đã chọn lọc khóa quy tắc hiện tại; “Cần nghiệm thu” nghĩa là workbook/kết quả năm tài chính thực vẫn cần được nghiệp vụ xem xét.

| Khu vực quy tắc | Hợp đồng có thể thực thi hiện tại | Bằng chứng chính | Trạng thái |
|---|---|---|---|
| Cách ly năm tài chính và dự án | Năm tài chính đã chọn không bao giờ rơi về năm khác; đường dẫn vẫn portable sau khi di chuyển dự án; nguồn mơ hồ/không khớp bị từ chối an toàn | `test_fiscal_run_context.py` | Được bảo vệ |
| Nhân sự/đầu vào thủ công | Vùng lưu trữ hằng năm được cách ly theo năm tài chính; hành vi số 0 rõ ràng, trống, không hợp lệ và cách ly không xóa dữ liệu trung tâm chi phí hoặc xe đưa đón không liên quan | `test_headcount_and_export.py`, `test_run_history.py` | Được bảo vệ |
| Chi phí hành khách xe đưa đón | Số người JP/VN độc lập và được nhân với đơn giá GA hằng tháng rõ ràng; thiếu giá không tạo số tiền phỏng đoán | `test_headcount_and_export.py`, `test_gui_bus_passenger_inputs.py` | Được bảo vệ |
| Khám sức khỏe hằng năm | Dòng nam và nữ dùng số lượng giới tính tháng 12 tương ứng và vẫn là các khoản riêng biệt | `TestHealthCheckAllocation.test_health_check_rules_use_gender_specific_counts` | Được bảo vệ bằng dữ liệu tổng hợp; cần nghiệm thu đầu vào/kết quả giới tính năm tài chính thực |
| Khám sức khỏe tuyển dụng | Dùng mức tăng nhân sự mới dương thay vì tổng nhân sự và yêu cầu giá nguồn rõ ràng; không có mức tăng dương thì không tạo số tiền | `test_posting_month_logic.py`, `test_headcount_and_export.py` | Được bảo vệ bằng dữ liệu tổng hợp; cần nghiệm thu sự kiện/kết quả thực |
| Chi phí sinh nhật và sự kiện | Hành vi bộ đọc/số lượng và ghi sổ dùng đầu vào sự kiện rõ ràng; kết quả theo thứ tự nguồn giữ sinh nhật trong nhóm nguồn chuẩn | `test_headcount_and_export.py`, `test_manual_event_drivers.py`, `test_source_order_output.py` | Được bảo vệ bằng dữ liệu tổng hợp/đã chọn lọc |
| Đồng phục và cốc gấp | Điều kiện hưởng, áo loại trừ lẫn nhau, thời điểm cấp, cốc cho công nhân mới, số 0 rõ ràng, tính lũy đẳng và từ chối an toàn khi mơ hồ đều được khóa | `test_uniform_cup_allocation.py` | Được bảo vệ |
| Tài sản cố định | Làm tròn theo từng tài sản, tháng kết thúc, số 0 rõ ràng và bỏ qua sau tháng kết thúc là các hợp đồng ngữ nghĩa | `test_fixed_assets_output.py`, `test_fixed_assets_parser_coverage.py` | Được bảo vệ; nghiệm thu cuối bằng bộ so sánh nghiệp vụ vẫn còn mở |
| Chi phí NNN, IT, cơ sở vật chất và hệ thống | Hợp đồng bộ đọc/bộ ghi bao phủ các bố cục được hỗ trợ và hành vi lỗi rõ ràng | các test `test_*parser.py`, `test_*writer.py`, bản xem trước và cờ xuất tương ứng | Được bảo vệ cho các bố cục đã ghi nhận; bố cục nhà cung cấp mới cần fixture mới |
| Kết quả/thứ tự nguồn | Snapshot ngữ nghĩa bảo vệ vị trí dòng, dòng phân cách, fallback nguồn không rõ và thứ tự chuẩn mà không phụ thuộc so sánh Excel từng byte dễ vỡ | `test_release_contracts.py`, `test_complete_v1_source_order_writer.py` | Được bảo vệ |
| An toàn schema và cập nhật | Tính tương thích migration, hash, đường dẫn tệp nén, chuẩn bị, kích hoạt và rollback đều từ chối an toàn | `test_schema_migrations.py`, `test_update_security.py`, `test_app_updates.py` | Được bảo vệ |
| Đường dẫn bản phát hành đóng gói | Dữ liệu runtime nằm ngoài binary có phiên bản; sức khỏe ứng dụng và trình khởi chạy phải đạt trong khi đóng gói onedir | `test_packaged_raw_resolution.py`, `test_packaging_entrypoint.py`, test nhanh gói | Được bảo vệ trên máy build; cần nghiệm thu máy sạch |

Khi một quy tắc thay đổi, hãy cập nhật test đặc trưng hóa hẹp nhất được liệt kê và ma trận này. Không thay assertion ngữ nghĩa bằng snapshot Excel nhị phân toàn phần: cách đó chậm, dễ vỡ giữa các phiên bản thư viện và khó giải thích lỗi nghiệp vụ.

## Kỷ luật hiệu năng

Không đưa phép quét toàn workbook hoặc pipeline thực vào unit test mặc định. Benchmark dùng workbook/SQLite/dòng thuần tổng hợp, ghi hoặc in kết quả có giới hạn và chỉ chạy khi `MP_MANAGER_RUN_PERFORMANCE=1`. Ngân sách đầu tiên xử lý 10.000 dòng thứ tự nguồn trong dưới 2 giây. Hồi quy hiệu năng là rủi ro phát hành khi làm thay đổi đáng kể thời gian khởi động giao diện, kiểm tra trước hoặc xuất thông thường.
