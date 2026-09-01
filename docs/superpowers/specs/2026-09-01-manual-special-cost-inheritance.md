# Kế thừa chi phí riêng theo CC

## Mục tiêu

Mỗi workbook kết quả của một Trung tâm chi phí (CC) có hai vùng độc lập:

- Chi phí chung do chương trình tạo lại từ nguồn của năm tài chính hiện tại.
- Chi phí riêng do người dùng nhập trực tiếp trên workbook, được giữ nguyên khi chạy lại và được kế thừa sang năm tài chính tiếp theo.

## Quy tắc đã chốt

1. Không có số dòng ranh giới dùng chung giữa các CC.
2. Số tiền, công thức, định dạng, mô tả và thứ tự của chi phí riêng được giữ nguyên.
3. Workbook nguồn của năm trước chỉ được đọc, không bị sửa.
4. Vùng riêng của workbook kết quả được đặt ngay sau vùng chung mới, ngăn bằng một dòng phân cách.
5. Workbook cũ không có metadata chỉ được đọc bằng dòng bắt đầu do người dùng xác nhận cho đúng CC; chương trình không đoán từ dòng trống.

## Thiết kế

Mỗi workbook kết quả có sheet rất ẩn `_mp2027_manual_special_cost_meta`. Metadata ghi phiên bản, tên sheet, mã CC, dòng cuối chi phí chung và hai đầu của vùng chi phí riêng.

Khi xuất, chương trình tạo hoàn chỉnh vùng chung trên workbook tạm. Sau đó nó đọc snapshot vùng riêng của workbook kết quả hiện có cùng FY; nếu chưa có thì đọc workbook từ thư mục kế thừa FY trước. Snapshot được đặt xuống dưới dòng chi phí chung mới. Chỉ sau khi workbook tạm hợp lệ, cơ chế publication hiện hữu mới thay thế kết quả công khai.

Nếu chưa có dữ liệu riêng, metadata vẫn được ghi để lần chạy sau xác định được vùng người dùng bắt đầu nhập. Khi dùng dữ liệu cũ không có metadata, cần một `legacy_start_row` theo CC.

## Không thuộc phạm vi

- Không suy diễn mã hoặc số tiền chi phí riêng từ các nguồn chi phí chung.
- Không tự lấy workbook bất kỳ của FY trước khi người dùng chưa cấu hình thư mục kế thừa.
