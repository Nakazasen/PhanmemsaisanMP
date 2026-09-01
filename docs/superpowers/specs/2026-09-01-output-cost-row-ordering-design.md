# Sắp xếp dòng chi phí trên file MP — Thiết kế

## Mục tiêu

Người dùng có một nút riêng để mở một file `MP_CC_<CC>.xlsx` đã xuất, xem các
dòng chi phí trong bảng, đổi thứ tự toàn bộ dòng chi phí và lưu lại.  Không
thay đổi cách chạy MP hiện tại đối với người không dùng nút này.

Việc đổi vị trí không được làm chương trình nhầm chi phí chung với chi phí
riêng khi chạy lại cùng FY hoặc tạo FY mới.

## Quy tắc nghiệp vụ đã chốt

1. Chi phí chung được tính lại từ nguồn dữ liệu của FY đang chạy.
2. Chạy lại **cùng FY** giữ nguyên toàn bộ nội dung chi phí riêng do người dùng
   nhập, gồm số tiền, công thức, định dạng và thứ tự đã lưu.
3. Tạo **FY mới** chỉ kế thừa chi phí riêng theo mã, mô tả và thứ tự đã lưu.
   Các ô số tiền và công thức liên quan đến tiền được xoá.
4. Người dùng có thể đặt dòng riêng giữa các dòng chung.  Vị trí hiển thị không
   được dùng để suy luận dòng thuộc loại nào.
5. Dòng chi phí chung mới chưa có trong thứ tự năm trước nằm cuối danh sách CC
   và được báo là dòng mới.
6. Không dùng nút sắp xếp vẫn giữ luồng cũ: vùng riêng liền sau vùng chung được
   tạo và đánh dấu tự động; file cũ chưa có dấu mốc vẫn cần khai báo một lần
   `CC:dòng_bắt_đầu`.

## Phạm vi giao diện

Thêm nút **Sắp xếp dòng chi phí** cạnh các thao tác kết quả hiện có.  Nút mở hộp
thoại để chọn một workbook kết quả trong thư mục OUTPUT hiện tại.  Hộp thoại
hiển thị bảng chỉ gồm các dòng chi phí thực tế (mã, mô tả, tháng/tổng); tiêu đề
FORM, dòng tổng, hướng dẫn và dòng kết cấu không phải dòng chi phí bị khoá.

Người dùng chọn một hoặc nhiều dòng và dùng kéo-thả, hoặc nút Lên/Xuống dự
phòng, rồi bấm Lưu thứ tự.  Lưu ghi trực tiếp vào workbook đã chọn sau khi kiểm
tra; không tạo file FY trước mới và không tự mở Excel bên ngoài.

## Nhận dạng và metadata ẩn

Workbook có thêm sheet `veryHidden` `_mp2027_output_cost_row_order` với một
bản ghi cho mỗi dòng chi phí:

- CC và sheet;
- `row_id` ổn định;
- `row_kind`: `common` hoặc `manual`;
- chữ ký dòng chung (mã + mô tả + số thứ tự lặp);
- `sort_order` và dòng Excel hiện hành.

Metadata này là nguồn phân loại.  Nó không hiển thị cho người dùng và không
thay đổi số liệu Excel.  Sheet metadata vùng riêng cũ vẫn được đọc để chuyển
đổi tương thích: khi lần đầu lưu thứ tự, những dòng trong vùng riêng được gắn
`manual`, các dòng còn lại được gắn `common`.

## Luồng lưu thứ tự

1. Đọc workbook, metadata thứ tự (nếu có) và metadata vùng riêng cũ.
2. Xác định tập dòng chi phí hợp lệ.  Nếu workbook cũ không có cả hai loại
   metadata, dừng với thông báo yêu cầu xác nhận dòng bắt đầu chi phí riêng;
   không tự đoán.
3. Di chuyển ảnh chụp đầy đủ của dòng (giá trị, công thức, định dạng, chiều cao
   và trạng thái ẩn) theo thứ tự người dùng chọn.
4. Dịch công thức tương đối theo vị trí dòng mới, cập nhật metadata, và lưu
   workbook.

Các dòng phi chi phí không nằm trong tập kéo-thả nên công thức/kết cấu FORM
không bị người dùng di chuyển nhầm.

## Luồng chạy lại và tạo FY mới

Trước khi export có thể thay workbook hiện có, pipeline chụp file nguồn như
hiện tại.  Nếu nguồn có metadata thứ tự mới, pipeline lấy toàn bộ dòng `manual`
ở bất kỳ vị trí nào, cùng thứ tự tổng thể đã lưu.  Sau khi phần chung FY mới
được tạo, pipeline ghép:

- dòng chung còn tồn tại: đặt theo vị trí đã lưu;
- dòng riêng: giữ đầy đủ khi cùng FY; với FY mới chỉ giữ mã/mô tả/định dạng
  không phải tiền và xoá các ô F:R chứa số tiền/công thức tiền;
- dòng chung mới: thêm cuối danh sách và báo số lượng.

Metadata được ghi lại theo vị trí mới.  Không sửa workbook FY trước.

Nếu metadata sai CC, thiếu sheet, trùng `row_id` hoặc không thể nhận dạng an
danh dòng chung, pipeline dừng CC đó với thông báo cụ thể, thay vì xuất một
file có nguy cơ ghi đè chi phí riêng.

## Kiểm thử và nghiệm thu

- Di chuyển dòng riêng lên giữa các dòng chung, chạy lại cùng FY: số tiền,
  công thức, định dạng và thứ tự vẫn còn.
- Tạo FY mới từ bố cục xen kẽ: mã/mô tả/thứ tự dòng riêng còn, tiền và công
  thức tiền bị xoá.
- Phần chung kéo dài/ngắn đi không ghi đè phần riêng.
- Dòng chung mới được thêm cuối và có trong thông báo.
- Workbook cũ không có metadata yêu cầu xác nhận; workbook có metadata vùng
  riêng cũ được chuyển đổi đúng.
- Kiểm tra một CC, xuất hàng loạt và các chuỗi Việt/Anh/Nhật.
