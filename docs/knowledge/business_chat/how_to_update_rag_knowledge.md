# Hướng dẫn Cập nhật Kiến thức AI theo Năm Tài chính (MP2027)

Tài liệu này hướng dẫn người vận hành và chuyên viên nghiệp vụ cách bổ sung, cập nhật quy tắc nghiệp vụ cho Trợ lý AI nội bộ khi bước sang năm tài chính mới (FY2028, FY2029...) hoặc khi có thay đổi biểu mẫu chi phí.

---

## 1. Nguyên tắc Cốt lõi & Ranh giới An toàn

1. **Hồ sơ năm cũ được bảo tồn nguyên vẹn**:
   - Tài liệu nghiệp vụ của năm tài chính cũ (FY2027) là hồ sơ đã đóng. Hệ thống chỉ đọc và tuyệt đối không bao giờ sửa đổi, ghi đè hoặc xóa các tài liệu này.
2. **Ưu tiên quy tắc mới nhất**:
   - Khi có quy tắc mới đã xác nhận của năm tài chính mới (ví dụ FY2028), Trợ lý AI sẽ tự động ưu tiên quy tắc mới hơn quy tắc cũ cho cùng một nội dung chi phí, đồng thời dẫn nguồn rõ ràng (ví dụ: `Nguồn tham khảo: Cập nhật nghiệp vụ FY2028 — Phân bổ chi phí nhà xưởng`).
3. **Phân định rõ mức độ tin cậy**:
   - **Đã xác nhận (Confirmed)**: Quy tắc chính thức, AI khẳng định chắc chắn và ưu tiên hàng đầu.
   - **Tham khảo nội bộ (Internal Reference / 社内参考)**: Hướng dẫn đang trong giai đoạn dự thảo hoặc rà soát. AI vẫn trả lời được nhưng gắn kèm nhãn cảnh báo rõ ràng.
4. **Không tự suy diễn từ Excel**:
   - Hệ thống không tự động đoán công thức hay quy tắc từ số liệu bảng tính; người vận hành cần mô tả thay đổi nghiệp vụ bằng lời dễ hiểu.
5. **Cơ chế Xuất bản An toàn (Fail-Closed)**:
   - Mọi bản cập nhật đều được kiểm tra tính hợp lệ tự động. Nếu phát hiện lỗi hoặc nội dung chưa đủ điều kiện, hệ thống sẽ tự động hủy bỏ và giữ nguyên toàn bộ kiến thức hiện hành mà không gây gián đoạn.

---

## 2. Khi nào cần Cập nhật Kiến thức AI?

- **Khi sang năm tài chính mới (FY2028, FY2029...)**: Cần áp dụng quy chế phân bổ mới, định mức tiêu hao mới hoặc thêm phòng ban mới.
- **Khi biểu mẫu chi phí thay đổi**: Cần hướng dẫn người dùng vị trí cột mới hoặc cách điền dữ liệu.
- **Khi phát hiện lỗi vận hành mới**: Bổ sung nguyên nhân và các bước khắc phục để AI có thể tự động hướng dẫn người dùng khi gặp sự cố tương tự.

---

## 3. Các bước Thực hiện trên Giao diện

### Bước 1: Mở Hộp thoại Cập nhật Kiến thức
1. Trong cửa sổ **Hỏi AI nội bộ (Business Chat Assistant)**, bấm nút **✨ Cập nhật kiến thức AI...** ở góc trên bên phải.
2. Cửa sổ **"Cập nhật kiến thức AI theo năm tài chính"** sẽ xuất hiện.

### Bước 2: Điền thông tin Nghiệp vụ
1. **Năm tài chính áp dụng**: Nhập năm áp dụng (ví dụ: `FY2028`, `FY2029`).
2. **Loại cập nhật**: Chọn loại phù hợp từ danh sách:
   - *Thay đổi quy tắc / công thức phân bổ*
   - *Quy tắc chi phí mới*
   - *Lỗi thường gặp & cách khắc phục*
   - *Thay đổi cấu trúc file Excel*
   - *Hướng dẫn vận hành mới*
3. **Tiêu đề thay đổi**: Đặt tên ngắn gọn, dễ hiểu (ví dụ: `Cập nhật phân bổ tiền điện xưởng sản xuất`).
4. **Mô tả thay đổi nghiệp vụ**: Viết câu mô tả rõ ràng, phi kỹ thuật về nội dung thay đổi.
5. **Người vận hành / người dùng cần làm gì**: Ghi rõ các bước người dùng cần thực hiện (ví dụ: `Kiểm tra số đo đồng hồ tại cột F trước khi chạy tính toán`).
6. **Phạm vi áp dụng & Tài liệu nguồn**: Ghi rõ phòng ban áp dụng và tên văn bản/chứng từ nguồn để tiện tra cứu đối chiếu.

### Bước 3: Xem Cấu trúc Tệp Excel Tham khảo (Tùy chọn)
- Nếu có file Excel mới, bấm **📊 Xem cấu trúc file Excel...** để xem danh sách trang tính và tiêu đề cột. Điều này giúp bạn ghi chú chính xác tên cột trong phần hướng dẫn.

### Bước 4: Chọn Mức Tin cậy & Kiểm tra Xem trước (Live Preview)
- Chọn mức tin cậy: **Đã xác nhận** hoặc **Tham khảo nội bộ**.
- Nhìn vào khung **Xem trước câu trả lời và trích dẫn của Chatbot**: Bạn sẽ thấy chính xác câu trả lời và trích dẫn nguồn mà người dùng sẽ nhận được khi hỏi Chatbot.

### Bước 5: Lưu nháp hoặc Xuất bản
- Bấm **Lưu nháp** nếu bạn muốn lưu lại để rà soát thêm sau này.
- Bấm **✦ Đưa vào kiến thức AI** để cập nhật ngay lập tức vào hệ thống tri thức của Trợ lý AI.

---

## 4. Quản lý & Vô hiệu hóa Bản cập nhật

- Mọi bản cập nhật được lưu trữ có cấu trúc theo từng năm tài chính tại thư mục:
  `docs/knowledge/business_chat/updates/FYxxxx/`
- Nếu cần tạm dừng áp dụng một quy tắc, người vận hành có thể vô hiệu hóa bản ghi qua dịch vụ quản lý hoặc chuyển trạng thái sang `draft`.

---

## 5. Hỗ trợ Đa ngôn ngữ (VI / EN / JA)

Khi người vận hành nhập nội dung bằng tiếng Việt, hệ thống tự động hỗ trợ truy xuất và đối chiếu trên cả 3 ngôn ngữ giao diện (Tiếng Việt, Tiếng Anh, Tiếng Nhật). Nhãn dẫn nguồn và mức độ tin cậy luôn được hiển thị chuẩn mực theo ngôn ngữ mà người dùng đang lựa chọn:
- **Tiếng Việt**: `Nguồn tham khảo: Cập nhật nghiệp vụ FY2028 — [chủ đề]` | `Mức tin cậy: Đã xác nhận`
- **English**: `Source Reference: FY2028 Business Update — [topic]` | `Confidence Level: Confirmed`
- **日本語**: `参照元: FY2028 業務更新 — [topic]` | `信頼度: 確定`
