# MP2027 Audit Report

- Fiscal year: `FY2027`
- Target CC: `1412000040`
- Source folder: `C:\Users\Admin\AppData\Local\Temp\pytest-of-Vinh\pytest-498\test_complete_mode_default_off0`
- Output folder: `D:\Sandbox\MP2027\OUTPUT_FY2027`

## Nguyên tắc an toàn

- Chương trình không tự bịa số liệu.
- Nếu có file nguồn máy đọc được, chương trình lấy từ file nguồn và để lại công thức trong FORM khi có thể.
- Nếu thiếu số liệu không thể suy luận, chương trình dựa vào danh sách cần người dùng nhập/chốt.

## Dữ liệu đã nạp

| Nguồn | Số record | Số CC | Ghi chú |
|---|---:|---:|---|
| `manual_event_driver` | 0 | 0 | Dữ liệu người dùng nhập cho sự kiện không thể suy luận. |
| `nnn_paperwork` | 0 | 0 | Workbook NNN/VISA/GPLD/Passport FY2027 vào row 137. |
| `birthday_workbook` | 0 | 0 | Workbook sinh nhật vào row 59, công thức count*152000. |
| `manual_special_cost` | 0 | 0 | Override thủ công theo form_row. |
| `it_sim` | 0 | 0 | Chi phí hệ thống. |
| `facility` | 0 | 0 | Khấu hao/lãi nhà đất/điện/nước. |
| `fixed_assets` | 0 | 0 | Tài sản cố định. |

## Kết quả parser

| Parser | Inserted | Skipped | Errors | File |
|---|---:|---:|---:|---|
| `facility` | 0 | 0 | 0 | `` |
| `fixed_assets` | 0 | 0 | 0 | `` |
| `it_simulation` | 0 | 0 | 0 | `` |
| `ga` | 0 | 0 | 0 | `` |
| `birthday_workbook` | 0 | 0 | 0 | `` |
| `manual_headcount` | 0 | 0 | 0 | `C:\Users\Admin\AppData\Local\Temp\pytest-of-Vinh\pytest-498\test_complete_mode_default_off0\headcount_manual.csv` |
| `manual_special_costs` | 0 | 0 | 0 | `C:\Users\Admin\AppData\Local\Temp\pytest-of-Vinh\pytest-498\test_complete_mode_default_off0\special_costs_manual.csv` |
| `manual_event_drivers` | 0 | 0 | 0 | `C:\Users\Admin\AppData\Local\Temp\pytest-of-Vinh\pytest-498\test_complete_mode_default_off0\event_drivers_manual.csv` |
| `nnn_paperwork` | 0 | 0 | 0 | `` |

## Cần người dùng xem/chốt

| Mức độ | CC | Kỳ | Khu vực | Cần làm |
|---|---|---|---|---|
| `action` | `1412000040` | `202603` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202603` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202604` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202604` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202605` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202605` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202606` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202606` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202607` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202607` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202608` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202608` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202609` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202609` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202610` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202610` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202611` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202611` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202612` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202612` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202701` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202701` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202702` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202702` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202703` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `action` | `1412000040` | `202703` | headcount_series | Provide baseline 202603 and FY monthly headcount for both headcount_staff and headcount_worker in headcount_manual.csv or the GUI. |
| `review` | `1412000040` | `` | headcount | Nếu CC này cần tính theo số người thực tế từng tháng, nhập vào headcount_manual.csv. |
| `review` | `1412000040` | `202612` | health_check_gender_split | Nếu CC này cần tính khám sức khỏe theo Nam/Nữ, nhập headcount_male/headcount_female tháng 12 trong headcount_manual.csv. |
| `action` | `1412000040` | `202604,202605,202606,202607,202608,202609,202610,202611,202612,202701,202702,202703` | manual_event_driver | Nếu có JP/VN bus, quà không đi du lịch, kỷ niệm 10 năm, company anniversary, VISA/Passport row khác 137..., hãy nhập vào event_drivers_manual.csv. |

## File liên quan

- Missing-input CSV: `D:\Sandbox\MP2027\OUTPUT_FY2027\MP2027_MISSING_INPUTS.csv`
- Manual event input: `C:\Users\Admin\AppData\Local\Temp\pytest-of-Vinh\pytest-498\test_complete_mode_default_off0\event_drivers_manual.csv`
