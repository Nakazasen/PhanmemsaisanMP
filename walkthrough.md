# Thiết kế và Xây dựng Hệ thống MP2027 Manager (Refactor Mode V4.1.0)

Hệ thống tự động hóa lập ngân sách MP2027 đã hoàn thành MVP. Tuy nhiên, qua rà soát thực tế, hệ thống đang được tái cấu trúc để khớp với yêu cầu nghiệp vụ sát sườn hơn.

## Cấu trúc luồng xử lý (End-to-End Workflow)
1. **Quét dữ liệu danh mục (Master Data)**: Đọc toàn bộ Cost Center và Danh mục tài khoản từ file thiết kế chuẩn ([FORM.xlsx](file:///C:/ProgramData/Sandbox/MP2027/FORM.xlsx)).
2. **Excel Parsers Đa cấu trúc (Ingestion Layer)**: 
    *   [fixed_assets.py](file:///C:/ProgramData/Sandbox/MP2027/src/parsers/fixed_assets.py): Lược duyệt **~1,270 dòng** khấu hao mỗi tháng (ví dụ sheet '2025.11') một cách chính xác. **Cần bổ sung logic kiểm tra Tháng khấu hao cuối cùng.**
    *   [facility.py](file:///C:/ProgramData/Sandbox/MP2027/src/parsers/facility.py): Chuyển đổi chuẩn USD -> VND và bóc tách dữ liệu điện, nước, toà nhà. **Lấy tỷ giá động từ ô B2 của file Hub.**
    *   [it_sim.py](file:///C:/ProgramData/Sandbox/MP2027/src/parsers/it_sim.py): Tổng hợp chi phí phần mềm theo các giai đoạn giá khác nhau.
    *   [ga.py](file:///C:/ProgramData/Sandbox/MP2027/src/parsers/ga.py): Đọc các định mức đơn giá (Gas: 39,309, VPN: 3.19...) và số ngày làm việc.
3. **Allocation Engine (Logic Layer - Đang Refactor)**:
    *   Mapping dữ liệu vào đúng mã tài khoản kế toán dựa trên phân loại CC: **製造**, **一般**, **販売**.
    *   Xử lý phân bổ qua các nhánh driver: Staff, Worker, và tổng nhân sự. **Cần hỗ trợ biến động nhân sự hàng tháng.**
4. **Hub Builder (Export Layer)**: Đổ dữ liệu vào sheet **内訳ﾘｽﾄ(4～3月)** của file [FORM.xlsx](file:///C:/ProgramData/Sandbox/MP2027/FORM.xlsx).

## Báo Cáo Đối Chiếu (Validation & Testing)

### 1. Chi phí Khấu hao (Depreciation)
*   **Logic mới**: Hệ thống phải so sánh tháng hiện tại với Last Depreciation Month. Nếu vượt quá, chi phí phải về 0.
*   **Dữ liệu thực tế**: ~1,270 dòng/tháng.

### 2. Chi phí xe Bus & Gas
*   **Đơn giá**: Phải khớp với file Cải tiến nhập dữ liệu chung vào file MP.xlsx (Ví dụ Gas: 39,309).
*   **Driver**: Số lượng người (Staff/Worker) phải lấy theo từng tháng để xử lý biến động.

### 3. Xác nhận sinh tồn của Công thức (Formula Intactness)
*   **Kết quả kiểm định**: ✅ PASS
*   **Sửa lỗi #N/A (Update V3.1.0)**: Đã khắc phục triệt để lỗi #N/A bằng cách đồng bộ hóa Header tháng (4, 5, ..., 3).

---
> **Trạng thái**: Đang trong quá trình Refactor theo đặc tả REFACTORING_SPEC_V4.md.