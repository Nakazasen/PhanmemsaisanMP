# Xuất FORM động theo thứ tự nguồn

## Nguyên tắc

Luồng production chỉ ghi workbook một lần. Dữ liệu được nhận diện bằng nhóm
nguồn, mã hạng mục và tài khoản; vị trí Excel không phải là định danh nghiệp vụ.
Cột `form_row` trong cơ sở dữ liệu chỉ được giữ để tương thích khi đọc dữ liệu
cũ và không được bộ xuất mới sử dụng.

Thứ tự logic lấy từ `source_file_order.xlsx`: Cơ sở vật chất, Tài sản cố định,
Hệ thống, Phân bổ hành chính, Sinh nhật, Master phân bổ và Giấy tờ NNN. Nhiều
tệp Hệ thống thuộc cùng một block. Chỉ các block có dữ liệu mới được ghi và giữa
hai block luôn có đúng một dòng trắng.

Các tệp Hệ thống khai báo `period_start` và `period_end` trong manifest. Ba
khoảng phải phủ đúng 12 tháng tài chính và không được chồng nhau; chương trình
dừng nếu cấu hình sai. Manifest đã lưu là nguồn sự thật, vì vậy tên tệp có thể
đổi mà không cần sửa Python hay phụ thuộc quy tắc đoán từ tên tệp.

## Metadata của FORM

Workbook chuẩn có hai tên vùng:

- `MP_OUTPUT_AREA`: toàn bộ vùng kết quả có thể xóa và ghi lại.
- `MP_OUTPUT_ROW_TEMPLATE`: dòng mẫu dùng để sao chép định dạng và công thức.

Các tên vùng được tạo bằng `scripts/configure_form_output.py`. Script tự nhận
diện sheet, tiêu đề, tháng, tài khoản, mô tả và WBS; không nhận tọa độ dòng/cột.
Nếu thiếu hoặc trùng tiêu đề, chương trình dừng trước khi ghi file kết quả.

Trước khi xuất, vùng output trên bản sao được làm sạch. FORM nguồn không bị sửa
trong quá trình tính toán. Các cột tài khoản, mô tả và WBS trong FORM trên repo
phải để trống trong toàn bộ vùng output.

## Dữ liệu và truy vết

`fact_input_data` lưu `source_group`, `source_file`, `source_sheet`, `source_row`,
`item_key` và `item_order`. Sheet ẩn `_mp2027_output_audit` trong file kết quả
ghi lại nguồn của từng dòng. Tài khoản được tra cứu theo mã/tên nghiệp vụ và loại
Cost Center; thiếu hoặc mơ hồ thì dừng, không dùng tài khoản hay đơn giá mặc định.

Các tham số CLI đặt dòng của writer cũ đã bị xóa. Lời gọi Python cũ truyền các
tham số này nhận thông báo rằng chế độ dòng cố định không còn được hỗ trợ.
