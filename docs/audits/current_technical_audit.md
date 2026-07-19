# Kiểm toán kỹ thuật hiện tại của MP2027

Thời điểm tạo: `2026-07-19T16:20:30+00:00`

> Đây chỉ là đường cơ sở tĩnh nhanh: không mở tệp Excel riêng tư, cơ sở dữ liệu runtime hoặc pipeline nghiệp vụ.

## Tóm tắt

- Số tệp Python: **145**
- Số dòng Python: **45649**
- Số kiểm thử thu thập được: **638**
- Phát hiện: nghiêm trọng=0, cao=0, trung bình=5, thấp=0

## Quyết định đóng gói

> **ĐÃ ĐẠT CỔNG KIỂM TRA TĨNH:** vẫn phải kiểm tra vận hành và nghiệm thu nghiệp vụ.

## Các phát hiện

| Mức độ | Quy tắc | Vị trí | Thông báo |
|---|---|---|---|
| trung bình | module có kích thước lớn | `scripts/run_e2e.py:1` | Có 1679 dòng; cần kiểm thử bảo vệ trước khi tách module theo từng giai đoạn. |
| trung bình | module có kích thước lớn | `src/engine/allocator.py:1` | Có 1541 dòng; cần kiểm thử bảo vệ trước khi tách module theo từng giai đoạn. |
| trung bình | module có kích thước lớn | `src/engine/hub_builder.py:1` | Có 1770 dòng; cần kiểm thử bảo vệ trước khi tách module theo từng giai đoạn. |
| trung bình | module có kích thước lớn | `src/universal_app.py:1` | Có 3723 dòng; cần kiểm thử bảo vệ trước khi tách module theo từng giai đoạn. |
| trung bình | module có kích thước lớn | `tests/test_headcount_and_export.py:1` | Có 5422 dòng; cần kiểm thử bảo vệ trước khi tách module theo từng giai đoạn. |

## Tạo lại báo cáo

```powershell
py scripts/generate_quality_baseline.py
```

Kết quả dành cho máy đọc: `reports/quality_baseline.json`.
