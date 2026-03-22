# Business Rules - MP2027 Manager

## 1. Trục thời gian (Fiscal Year)
- Năm tài chính bắt đầu từ **Tháng 4** và kết thúc vào **Tháng 3** năm sau.
- Toàn bộ dữ liệu được lưu trữ theo định dạng Period `YYYYMM`.

## 2. Phân loại Cost Center (CC)
Dựa vào cột `cost_type` trong `dim_cost_centers`:
- **Sản xuất (製造)**: Dùng mã tài khoản Mfg.
- **Bán hàng (販売)**: Dùng mã tài khoản Sales.
- **Gián tiếp/Văn phòng (一般/間接)**: Dùng mã tài khoản GA.

## 3. Quy tắc Phân bổ (Allocation)
- **Headcount Staff**: Chỉ tính dựa trên số lượng nhân viên văn phòng.
- **Headcount Worker**: Chỉ tính dựa trên số lượng công nhân G7.
- **Headcount All**: Tính tổng Staff + Worker.
- **Working Days**: Tính dựa trên số ngày làm việc chuẩn của tháng (từ GA data).

## 4. Bảo toàn Excel (Formula Integrity)
- Hệ thống chỉ ghi đè dữ liệu vào sheet `内訳ﾘｽﾄ`.
- Tuyệt đối không xóa hay thay đổi format/công thức tại các sheet báo cáo `採算表`.
- Sử dụng nguyên tắc kế toán bảo thủ: Doanh thu làm tròn xuống (Rounddown), Chi phí làm tròn lên (Roundup) khi quy đổi sang USD.
