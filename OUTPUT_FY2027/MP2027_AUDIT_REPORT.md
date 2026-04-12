# MP2027 Audit Report

- Fiscal year: `FY2027`
- Target CC: `1412000006`
- Source folder: `docs\MP2027`
- Output folder: `D:\Sandbox\MP2027\OUTPUT_FY2027`

## Nguyên tắc an toàn

- Chương trình không tự bịa số liệu.
- Nếu có file nguồn máy đọc được, chương trình lấy từ file nguồn và để lại công thức trong FORM khi có thể.
- Nếu thiếu số liệu không thể suy luận, chương trình dựa vào danh sách cần người dùng nhập/chốt.

## Dữ liệu đã nạp

| Nguồn | Số record | Số CC | Ghi chú |
|---|---:|---:|---|
| `manual_event_driver` | 0 | 0 | Dữ liệu người dùng nhập cho sự kiện không thể suy luận. |
| `nnn_paperwork` | 54 | 30 | Workbook NNN/VISA/GPLD/Passport FY2027 vào row 137. |
| `birthday_workbook` | 556 | 61 | Workbook sinh nhật vào row 59, công thức count*152000. |
| `manual_special_cost` | 0 | 0 | Override thủ công theo form_row. |
| `it_sim` | 3948 | 60 | Chi phí hệ thống. |
| `facility` | 4584 | 62 | Khấu hao/lãi nhà đất/điện/nước. |
| `fixed_assets` | 9846 | 28 | Tài sản cố định. |

## Kết quả parser

| Parser | Inserted | Skipped | Errors | File |
|---|---:|---:|---:|---|
| `facility` | 4584 | 0 | 0 | `` |
| `ga` | 72 | 0 | 0 | `` |
| `manual_headcount` | 16 | 0 | 0 | `docs\MP2027\headcount_manual.csv` |
| `manual_special_costs` | 0 | 0 | 0 | `docs\MP2027\special_costs_manual.csv` |
| `manual_event_drivers` | 0 | 0 | 0 | `docs\MP2027\event_drivers_manual.csv` |
| `nnn_paperwork` | 54 | 9 | 0 | `docs\MP2027\Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx` |
| `birthday_workbook` | 556 | 1 | 0 | `docs\MP2027\Sinh nhật MP FY2027.xlsx` |
| `it_simulation` | 3948 | 0 | 0 | `` |
| `fixed_assets` | 9846 | 0 | 0 | `` |

## Cần người dùng xem/chốt

| Mức độ | CC | Kỳ | Khu vực | Cần làm |
|---|---|---|---|---|
| `review` | `1412000006` | `202612` | health_check_gender_split | Nếu CC này cần tính khám sức khỏe theo Nam/Nữ, nhập headcount_male/headcount_female tháng 12 trong headcount_manual.csv. |
| `action` | `1412000006` | `202704,202705,202706,202707,202708,202709,202710,202711,202712,202701,202702,202703` | manual_event_driver | Nếu có JP/VN bus, quà không đi du lịch, kỷ niệm 10 năm, company anniversary, VISA/Passport row khác 137..., hãy nhập vào event_drivers_manual.csv. |

## File liên quan

- Missing-input CSV: `D:\Sandbox\MP2027\OUTPUT_FY2027\MP2027_MISSING_INPUTS.csv`
- Manual event input: `docs\MP2027\event_drivers_manual.csv`
