# Hướng dẫn nhập nhân sự thủ công

Tài liệu này dành cho người dùng cần nhập/chốt số nhân sự theo từng CC khi tệp nguồn chưa đủ tin cậy ở mức CC/tháng.

## Khi nào cần nhập

- Dashboard báo VÀNG vì CC chưa có dữ liệu nhân sự nhập tay.
- Cần tính các khoản theo số người như gas, hand wash, toilet paper, cleaning.
- Cần tính khám sức khỏe row 57/58 và phải có Nam/Nữ tháng 12.

## Cách nhập trên giao diện

1. Mở chương trình.
2. Kiểm tra `Năm tài chính`.
3. Bấm `Nhập nhân sự thủ công`.
4. Chọn CC.
5. Nhập số nhân viên và công nhân cho từng tháng.
6. Nếu có dữ liệu Nam/Nữ tháng 12, nhập vào dòng tháng 12.
7. Bấm `Lưu 12 tháng`.
8. Chạy lại tính toán và mở Dashboard kiểm toán để kiểm tra lại.

## Cách nhập bằng tệp

File cần sửa là:

```text
docs/MP2027/headcount_manual.csv
```

Cột dữ liệu:

- `cc_code`: mã CC.
- `period`: tháng dạng `YYYYMM`.
- `headcount_staff`: số nhân viên.
- `headcount_worker`: số công nhân.
- `headcount_male`: số Nam, dùng cho health-check nếu có.
- `headcount_female`: số Nữ, dùng cho health-check nếu có.
- `description`: ghi chú nguồn dữ liệu.

Ví dụ:

```csv
cc_code,period,headcount_staff,headcount_worker,headcount_male,headcount_female,description
1412000004,202704,21,180,,,baseline
1412000004,202712,21,182,120,83,gender split for health check
```

Không nhập số ước lượng nếu chưa được chốt. Nếu chưa chắc, hãy để trống và ghi chú để kiểm toán lại.
