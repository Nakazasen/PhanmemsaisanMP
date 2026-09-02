# MP2027 Business Chat Knowledge — Tiếng Việt

Schema version: 2.0

Tài liệu này được tạo tự động từ knowledge_catalog.json và source_registry.json.
Đây là curated local retrieval; chưa phải vector/embedding RAG và chưa đọc tài liệu gốc lúc runtime.
Gemini là lớp soạn câu trả lời bên ngoài khi khả dụng.
Không chỉnh sửa trực tiếp — cập nhật catalog rồi tạo lại tài liệu.

---

## bck_locked_file: Tệp kết quả đang bị khóa

**Status**: active | **Review**: approved
**Source**: Hướng dẫn nghiệp vụ MP2027 đã duyệt

Khi tệp Excel kết quả đang được mở bởi người khác hoặc ứng dụng khác, chương trình không thể ghi đè để lưu kết quả mới.

1. Đóng tất cả tệp Excel đang mở trong thư mục kết quả.
2. Đóng cửa sổ File Explorer nếu đang mở thư mục kết quả.
3. Chờ vài giây rồi bấm Chạy tính toán lại.

Keywords: khóa, file khóa, excel khóa, không ghi được, đang mở, bị khóa, locked, không lưu được

---

## bck_missing_baseline: Thiếu dữ liệu nhân sự mốc tháng 3

**Status**: active | **Review**: approved
**Source**: Hướng dẫn nghiệp vụ MP2027 đã duyệt

Chương trình cần có số lượng nhân sự tháng 3 (tháng mốc đầu kỳ) để tính phân bổ chi phí cho cả năm tài chính. Nếu thiếu dữ liệu này, quá trình tính toán sẽ dừng lại.

1. Bấm nút Nhập nhân sự thủ công trên giao diện chính.
2. Chọn phòng ban cần nhập và nhập tổng số người của tháng 3.
3. Bấm Lưu nhân sự & thời gian, sau đó bấm Chạy tính toán.

Keywords: nhân sự, mốc, tháng 3, baseline, thiếu nhân sự, chưa có tổng số người, dữ liệu mốc

---

## bck_source_validation: Tệp nguồn đầu vào chưa đúng yêu cầu

**Status**: active | **Review**: approved
**Source**: Hướng dẫn nghiệp vụ MP2027 đã duyệt

Trước khi tính toán, chương trình kiểm tra tất cả tệp nguồn đầu vào. Nếu tệp thiếu trang tính, sai năm tài chính hoặc cấu trúc cột không đúng, chương trình sẽ báo lỗi và không cho chạy.

1. Đọc thông báo lỗi để biết tệp nào bị sai và lỗi gì.
2. Mở tệp bảng tính đó, sửa theo hướng dẫn rồi lưu lại.
3. Bấm Quét kỹ lại nội dung rồi bấm Chạy tính toán.

Keywords: nguồn, tệp nguồn, kiểm tra nguồn, đầu vào, sai cấu trúc, thiếu trang tính, source, lỗi nguồn

---

## bck_fiscal_year_mismatch: Năm tài chính không khớp

**Status**: active | **Review**: approved
**Source**: Hướng dẫn nghiệp vụ MP2027 đã duyệt

Tệp mẫu FORM và các tệp nguồn phải cùng một năm tài chính. Nếu năm tài chính trên giao diện không khớp với năm trong tệp nguồn, chương trình sẽ từ chối chạy.

1. Kiểm tra năm tài chính trên giao diện chính có đúng năm cần tính không.
2. Kiểm tra tệp mẫu FORM và các thư mục nguồn có đúng năm tương ứng.
3. Nếu sai, chọn lại tệp FORM và thư mục nguồn đúng năm rồi bấm Quét kỹ lại nội dung.

Keywords: năm, năm tài chính, sai năm, không khớp năm, fiscal year, FY

---

## bck_cost_center_selection: Cách chọn trung tâm chi phí (phòng ban)

**Status**: active | **Review**: approved
**Source**: Hướng dẫn nghiệp vụ MP2027 đã duyệt

Trước khi chạy tính toán, bạn cần chọn phòng ban (trung tâm chi phí) cần xuất kết quả. Có thể chọn một, nhiều hoặc tất cả phòng ban.

1. Bấm nút Chọn phòng trên giao diện chính.
2. Đánh dấu phòng ban cần tính hoặc bấm Chọn tất cả.
3. Bấm Xác nhận để quay lại giao diện chính, rồi bấm Chạy tính toán.

Keywords: phòng ban, trung tâm chi phí, CC, chọn phòng, cost center, chọn CC

---

## bck_data_entry_manual: Cách nhập dữ liệu bổ sung thủ công

**Status**: active | **Review**: approved
**Source**: Hướng dẫn nghiệp vụ MP2027 đã duyệt

Một số khoản chi phí không có trong tệp nguồn tự động và cần người dùng nhập thủ công, ví dụ: chi phí du lịch công ty, cốc xếp, kỷ niệm, xe buýt.

1. Bấm nút Nhập sự kiện thiếu dữ liệu trên giao diện chính.
2. Chọn loại sự kiện, nhập số lượng hoặc số tiền theo thực tế.
3. Bấm Lưu để ghi nhận, sau đó bấm Chạy tính toán.

Keywords: nhập tay, nhập thủ công, nhập liệu, sự kiện, bổ sung, manual input, event driver

---

## bck_rerun_calculation: Cách chạy lại tính toán sau khi sửa dữ liệu

**Status**: active | **Review**: approved
**Source**: Hướng dẫn nghiệp vụ MP2027 đã duyệt

Sau khi bạn sửa tệp nguồn, nhập dữ liệu bổ sung hoặc khắc phục lỗi, bạn cần quét lại nội dung rồi chạy tính toán lại để có kết quả mới nhất.

1. Bấm Quét kỹ lại nội dung (hoặc Kiểm tra thay đổi nhanh) để chương trình đọc lại tệp.
2. Kiểm tra trạng thái màu xanh (đủ nguồn) trên giao diện.
3. Bấm Chạy tính toán để xuất kết quả mới.

Keywords: chạy lại, tính toán lại, recalculate, chạy tính toán, rerun, chạy lại sau sửa

---

## bck_excel_format_error: Lỗi định dạng hoặc cấu trúc tệp Excel

**Status**: active | **Review**: approved
**Source**: Hướng dẫn nghiệp vụ MP2027 đã duyệt

Nếu tệp Excel nguồn bị sai định dạng, thiếu trang tính bắt buộc hoặc cột dữ liệu không đúng, chương trình sẽ không đọc được và báo lỗi khi kiểm tra.

1. Xem lại thông báo lỗi để biết tên tệp và trang tính bị thiếu hoặc sai.
2. Mở tệp Excel đó, bổ sung trang tính hoặc cột theo đúng mẫu.
3. Lưu tệp rồi bấm Quét kỹ lại nội dung.

Keywords: excel, định dạng, cấu trúc, cột, trang tính, sheet, format, lỗi excel

---

## bck_headcount_input: Cách nhập dữ liệu nhân sự 12 tháng

**Status**: active | **Review**: approved
**Source**: Hướng dẫn nghiệp vụ MP2027 đã duyệt

Dữ liệu nhân sự 12 tháng gồm số nhân viên, công nhân và biệt phái của từng tháng trong năm tài chính. Chương trình dùng dữ liệu này để phân bổ chi phí nhân sự.

1. Bấm nút Nhập nhân sự thủ công, chọn mã phòng ban (CC) cần nhập.
2. Nhập số nhân viên, công nhân cho từng tháng. Ô để trống sẽ được lưu là 0.
3. Bấm Lưu nhân sự & thời gian.

Keywords: nhân sự, 12 tháng, headcount, số người, nhập nhân sự, nhân viên, công nhân

---

## bck_workflow_overview: Quy trình 5 bước chạy tính toán MP2027

**Status**: active | **Review**: approved
**Source**: Hướng dẫn nghiệp vụ MP2027 đã duyệt

Quy trình chạy MP2027 gồm 5 bước: (1) Chọn năm tài chính, (2) Chọn tệp FORM và thư mục nguồn, (3) Kiểm tra trạng thái nguồn, (4) Bổ sung dữ liệu nhập tay nếu cần, (5) Bấm Chạy tính toán.

1. Chọn đúng năm tài chính, tệp mẫu FORM và thư mục nguồn chi phí, nhân sự.
2. Bấm Quét kỹ lại nội dung và kiểm tra trạng thái màu trên giao diện.
3. Nếu trạng thái xanh, bấm Chạy tính toán. Nên thử 1 phòng trước khi chạy tất cả.

Keywords: quy trình, 5 bước, workflow, hướng dẫn, bắt đầu, cách dùng, từ đầu

---

## bck_account_lookup_rules: Quy tắc tra cứu mã tài khoản kế toán

**Status**: active | **Review**: approved
**Source**: Hướng dẫn nghiệp vụ MP2027 đã duyệt

Mã tài khoản không được tra trực tiếp theo tên dòng mô tả mà phải đi theo chuỗi 5 bước nghiệp vụ: (1) Phòng ban, (2) Bảng 原価センタ, (3) Phân loại chi phí 原価区分, (4) Chọn cột Sản xuất/Chung/Bán hàng, (5) Lấy mã tài khoản chính xác.

1. Xác định mã phòng ban (Cost Center) cần tính.
2. Tra bảng danh mục để biết phân loại chi phí của phòng ban đó.
3. Chọn đúng cột chi phí tương ứng rồi đối chiếu lấy mã tài khoản.

Keywords: tài khoản, mã tài khoản, account, nghiệp vụ, phòng ban, phân loại chi phí, nguyên tắc

---

## bck_special_cost_manual: Cách xử lý và nhập các khoản chi phí đặc thù

**Status**: active | **Review**: approved
**Source**: Hướng dẫn nghiệp vụ MP2027 đã duyệt

Các khoản chi phí phát sinh đặc thù không nằm trong luồng phân bổ tự động có thể được khai báo qua kênh nhập chi phí thủ công theo định dạng quy chuẩn.

1. Mở màn hình nhập chi phí bổ sung hoặc kiểm tra bảng kê chi phí.
2. Nhập đầy đủ mã phòng ban, mã tài khoản và số tiền theo từng tháng.
3. Bấm Lưu dữ liệu và thực hiện Quét lại nội dung.

Keywords: chi phí đặc thù, chi phí đặc biệt, special cost, bổ sung chi phí, điều chỉnh, manual cost

---

## bck_update_rollback_procedure: Quy trình cập nhật phần mềm và khôi phục phiên bản

**Status**: active | **Review**: approved
**Source**: Hướng dẫn nghiệp vụ MP2027 đã duyệt

Hệ thống hỗ trợ cập nhật an toàn qua thư mục mạng LAN nội bộ. Trước khi cập nhật, chương trình luôn kiểm tra tính toàn vẹn (mã SHA-256) và tự động tạo bản sao lưu để khôi phục khi cần.

1. Đảm bảo máy tính có kết nối đến thư mục chia sẻ nội bộ của công ty.
2. Thực hiện cập nhật theo thông báo trên màn hình.
3. Nếu gặp sự cố sau khi cập nhật, liên hệ quản trị viên để hoàn tác về bản sao lưu gần nhất.

Keywords: cập nhật, update, khôi phục, rollback, phiên bản, bản mới, mạng LAN

---
