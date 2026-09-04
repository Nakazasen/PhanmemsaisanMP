# Feature Specification: So Sánh Biến Động Chi Phí MP Giữa Các Năm (YoY Cost Variance Analysis)

**Feature Branch**: `001-yoy-cost-variance`

**Created**: 2026-08-17

**Status**: Ready for Planning

**Input**: User description: "sau khi người dùng xuất ra chi phí chung trong chương trình, người dùng sẽ tự nhập thêm chi phí riêng của phòng mình, người dùng muốn có 1 nút để so sánh dữ liệu file MP FY năm nay với file MP FY năm ngoái có gì sai khác, có chi phí gì biến động(thay đổi lên hoặc xuống)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - So sánh đối chiếu biến động chi phí của 1 phòng ban / Cost Center (Priority: P1)

Sau khi hệ thống xuất file FORM MP năm tài chính hiện tại (chứa các chi phí chung phân bổ) và người dùng phòng ban đã tự nhập bổ sung toàn bộ các khoản mục chi phí riêng của phòng mình, người dùng muốn mở tính năng so sánh, chọn file MP năm nay và file MP năm ngoái tương ứng của phòng ban đó để kiểm tra tức thì các chênh lệch và biến động chi phí giữa hai năm.

**Why this priority**: Đây là luồng nghiệp vụ cốt lõi (MVP) giúp người lập ngân sách phòng ban và kế toán kiểm soát ngay các khoản mục tăng đột biến hoặc giảm sâu trước khi chốt nộp ngân sách chính thức.

**Independent Test**: Có thể kiểm thử độc lập bằng cách nạp 1 file MP năm nay (đã có chi phí chung + chi phí riêng) và 1 file MP năm ngoái của cùng một Cost Center, nhấn nút "So sánh biến động" và kiểm tra bảng kết quả đối chiếu hiển thị chính xác các dòng chi phí: giá trị năm ngoái, giá trị năm nay, chênh lệch số tiền (+/-) và tỷ lệ % biến động.

**Acceptance Scenarios**:

1. **Given** người dùng chọn đúng 1 file MP FY năm nay và 1 file MP FY năm ngoái của cùng một Cost Center, **When** người dùng nhấn nút "So sánh", **Then** hệ thống hiển thị bảng chi tiết từng khoản mục chi phí kèm số tiền năm ngoái, số tiền năm nay, độ lệch tuyệt đối ($\Delta$) và tỷ lệ % thay đổi.
2. **Given** có khoản mục chi phí năm ngoái không có phát sinh ($0$ hoặc trống) nhưng năm nay có phát sinh ($> 0$), **When** hệ thống đối chiếu, **Then** khoản mục này được đánh dấu trạng thái "Mới phát sinh" (New Item) và hiển thị rõ số tiền tăng mới.
3. **Given** có khoản mục năm ngoái có chi phí nhưng năm nay bằng $0$ hoặc bị xóa bỏ, **When** hệ thống đối chiếu, **Then** khoản mục này được đánh dấu trạng thái "Đã cắt giảm" (Discontinued/Removed) với tỷ lệ giảm $-100\%$.
4. **Given** một khoản mục có tỷ lệ tăng hoặc giảm vượt ngưỡng quy định ($\ge \pm 10\%$ hoặc $\ge 50.000.000$ VNĐ), **When** hiển thị kết quả, **Then** dòng đó được làm nổi bật trực quan (đổi màu cảnh báo Vàng/Đỏ) để người dùng chú ý giải trình.

---

### User Story 2 - Xuất báo cáo giải trình biến động chi phí ra bảng tính Excel (Priority: P2)

Sau khi xem bảng đối chiếu biến động trên màn hình, người dùng muốn xuất toàn bộ kết quả phân tích biến động này ra 1 tệp bảng tính Excel có định dạng chuẩn báo cáo quản trị, bao gồm các công thức tính toán, tỷ lệ %, phân loại biến động và có sẵn cột để người dùng điền ghi chú/lý do giải trình biến động chi phí.

**Why this priority**: File báo cáo này là tài liệu bàn giao bắt buộc để nộp cho ban giám đốc/kế toán trưởng giải trình lý do tại sao chi phí phòng ban tăng/giảm so với năm trước.

**Independent Test**: Nhấn nút "Xuất báo cáo biến động ra Excel", kiểm tra file Excel sinh ra có đầy đủ các cột thông tin (Mã tài khoản, Tên khoản mục, Số tiền Năm trước, Số tiền Năm nay, Chênh lệch, % Biến động, Cột ghi chú giải trình), công thức tính toán toàn vẹn và định dạng số tiền rõ ràng.

**Acceptance Scenarios**:

1. **Given** bảng kết quả so sánh đang hiển thị trên giao diện, **When** người dùng chọn "Xuất báo cáo Excel", **Then** hệ thống tạo ra một file Excel báo cáo biến động lưu tại thư mục chỉ định hoặc thư mục báo cáo kiểm tra.
2. **Given** file Excel báo cáo vừa được tạo, **When** mở file, **Then** cấu trúc bao gồm tiêu đề rõ ràng (Cost Center, Năm so sánh), định dạng số tiền chuẩn, tô màu trực quan các dòng biến động lớn và có cột "Ghi chú / Lý do giải trình" để trống cho người dùng nhập tay.

---

### User Story 3 - So sánh hàng loạt biến động cho toàn bộ danh sách phòng ban (Priority: P3)

Người quản lý ngân sách tổng thể công ty (hoặc kế toán tổng hợp) muốn so sánh tự động tất cả các file Cost Center của năm nay với các file tương ứng của năm ngoái trong một lần thao tác, tạo ra một báo cáo tổng hợp toàn công ty.

**Why this priority**: Tăng năng suất cho cấp quản lý tổng hợp khi phải duyệt hàng chục Cost Center cùng lúc, nhưng không phải điều kiện tiên quyết cho từng phòng ban đơn lẻ (Story 1 & 2 đã đáp ứng nhu cầu cốt lõi).

**Independent Test**: Chỉ định thư mục chứa các file MP năm nay và thư mục chứa các file MP năm ngoái, hệ thống tự động ghép cặp theo Mã Cost Center và xuất báo cáo tổng hợp biến động toàn diện.

**Acceptance Scenarios**:

1. **Given** người dùng chọn 2 thư mục chứa file MP của 2 năm, **When** kích hoạt so sánh hàng loạt, **Then** hệ thống tự động nhận diện từng Cost Center, ghép cặp file chính xác và xử lý lần lượt.
2. **Given** có Cost Center xuất hiện ở năm nay nhưng không có file năm ngoái (Cost Center mới thành lập), **When** chạy đối chiếu, **Then** hệ thống ghi nhận Cost Center này là "Cost Center mới" và ghi vào danh sách lưu ý trong báo cáo tổng hợp.

---

### Edge Cases

- **Mâu thuẫn cấu trúc dòng giữa hai năm:** File FORM năm nay có thể có thêm hoặc bớt dòng/tài khoản so với FORM năm ngoái do thay đổi danh mục kế toán. Hệ thống đối chiếu dựa trên khóa nhận diện thống nhất (Mã tài khoản & Tên khoản mục) để đảm bảo độ chính xác ngay cả khi thứ tự dòng bị xáo trộn.
- **Giá trị ô chứa công thức hoặc ô trống:** Các ô không có dữ liệu (blank) không được tự ý coi là số liệu sai lệch, mà phải xử lý tương đương giá trị $0$ khi tính chênh lệch số học nhưng vẫn giữ nguyên tính chất hiển thị không phát sinh.
- **Mẫu số bằng 0 khi tính % biến động:** Khi chi phí năm ngoái là $0$ và năm nay $> 0$, tỷ lệ % không thể chia cho $0$; hệ thống hiển thị quy ước rõ ràng là `+100% (Mới)` hoặc `N/A (Mới)` thay vì gây lỗi tính toán (`#DIV/0!`).
- **File bị khóa hoặc mở dở trong Excel:** Nếu người dùng đang mở file MP trong ứng dụng Excel khi nhấn so sánh, hệ thống đọc file ở chế độ chỉ đọc an toàn (read-only) mà không bị lỗi crash do khóa tệp.
- **Chọn nhầm file không đúng định dạng FORM MP:** Nếu người dùng chọn file Excel bất kỳ không đúng cấu trúc FORM MP của hệ thống, chương trình báo lỗi từ chối rõ ràng và hướng dẫn người dùng chọn lại.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống PHẢI cung cấp giao diện người dùng cho phép chọn/nạp 2 file MP để so sánh: File MP năm tài chính hiện tại (đã nhập chi phí riêng) và File MP năm tài chính trước đó.
- **FR-002**: Hệ thống PHẢI tự động trích xuất và ánh xạ các khoản mục chi phí giữa hai file dựa trên khóa định danh kết hợp: **Mã tài khoản (Account Code) + Tên khoản mục (Item Name)**. Trường hợp phát sinh dòng trùng lặp mã và tên, hệ thống áp dụng vị trí số dòng bổ sung để phân biệt.
- **FR-003**: Hệ thống PHẢI tính toán chính xác cho từng khoản mục:
  - Giá trị ngân sách năm ngoái ($V_{\text{last}}$) và năm nay ($V_{\text{curr}}$).
  - Độ chênh lệch tuyệt đối: $\Delta = V_{\text{curr}} - V_{\text{last}}$.
  - Tỷ lệ phần trăm biến động: $\% = \frac{V_{\text{curr}} - V_{\text{last}}}{V_{\text{last}}} \times 100\%$ (với quy tắc khi $V_{\text{last}} = 0$ và $V_{\text{curr}} > 0$ thì gán $+100\%$, khi $V_{\text{last}} = 0$ và $V_{\text{curr}} = 0$ thì gán $0\%$).
- **FR-004**: Hệ thống PHẢI phân loại và gán nhãn trạng thái biến động cho từng dòng: "Tăng" (Increase), "Giảm" (Decrease), "Không đổi" (No Change), "Mới phát sinh" (New Item), "Cắt giảm hoàn toàn" (Removed).
- **FR-005**: Hệ thống PHẢI hỗ trợ bộ lọc và đánh dấu trực quan (Highlight màu cảnh báo) các khoản mục có biến động vượt ngưỡng mặc định: **$\ge \pm 10\%$ HOẶC chênh lệch tuyệt đối $\ge 50.000.000$ VNĐ**, đồng thời cung cấp ô nhập liệu trên giao diện để người dùng có thể tùy chỉnh lại ngưỡng này theo nhu cầu.
- **FR-006**: Hệ thống PHẢI cho phép xuất bảng kết quả đối chiếu ra file Excel (`.xlsx`) hoàn chỉnh, giữ nguyên định dạng số tiền, có dòng tổng cộng và có cột ghi chú giải trình.
- **FR-007**: Hệ thống PHẢI hiển thị giao diện đối chiếu dưới dạng một **Tab độc lập riêng: "📊 So sánh biến động MP (YoY)"** trên thanh điều hướng chính của ứng dụng MP2027 Manager.
- **FR-008**: Hệ thống PHẢI tuân thủ nguyên tắc không chỉnh sửa hay ghi đè làm thay đổi nội dung của hai file MP gốc trong suốt quá trình đọc và so sánh.

---

### Key Entities

- **MP Comparison Pair**: Cặp dữ liệu đối chiếu gồm thông tin Cost Center, Năm tài chính cơ sở (năm trước), Năm tài chính so sánh (năm nay), đường dẫn 2 tệp nguồn.
- **Cost Line Variance**: Bản ghi biến động của từng dòng chi phí, bao gồm: Mã tài khoản, Tên hạng mục, Số tiền năm trước (12 tháng + Tổng năm), Số tiền năm nay (12 tháng + Tổng năm), Giá trị chênh lệch, Tỷ lệ % biến động, Trạng thái phân loại biến động, Cảnh báo vượt ngưỡng.
- **Variance Summary Report**: Báo cáo tổng hợp biến động toàn diện theo Cost Center hoặc theo toàn bộ doanh nghiệp, bao gồm tổng chi phí năm trước, tổng chi phí năm nay, tổng chênh lệch tăng/giảm ròng.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Người dùng hoàn thành thao tác chọn 2 file và nhận được bảng kết quả so sánh biến động chi phí trong thời gian dưới 3 giây cho 1 Cost Center thông thường.
- **SC-002**: 100% các khoản mục chi phí có trong 2 file đều được ánh xạ chính xác, không bỏ sót bất kỳ dòng chi phí riêng nào do người dùng tự nhập thêm.
- **SC-003**: File báo cáo Excel xuất ra có công thức tính toán và số liệu khớp đúng 100% với số liệu hiển thị trên giao diện đối chiếu.
- **SC-004**: Người dùng có thể lọc nhanh danh sách các khoản mục biến động lớn chỉ bằng 1 thao tác click chuột.

---

## Assumptions

- File MP năm nay và năm ngoái đều được tạo từ cấu trúc FORM chuẩn của hệ thống MP Manager (có các cột tháng từ Tháng 4 đến Tháng 3 năm sau theo năm tài chính chuẩn của công ty).
- Người dùng đã hoàn thành việc nhập chi phí riêng của phòng mình vào file MP năm nay trước khi thực hiện so sánh.
- Các khoản mục chi phí được bảo toàn nguyên vẹn về mã tài khoản hoặc tên khoản mục giữa các kỳ tài chính.
- Thao tác so sánh hoàn toàn chạy offline trên máy người dùng, không phụ thuộc vào kết nối mạng hay dịch vụ bên ngoài.
