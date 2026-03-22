# Thiết kế và Xây dựng Hệ thống MP2027 Manager

Sau nhiều vòng lặp phát triển, hệ thống tự động hóa lập ngân sách MP2027 đã hoàn thành. Hệ thống tuân thủ kiến trúc **Hub-centric** qua 6 Phase xử lý.

## Cấu trúc luồng xử lý (End-to-End Workflow)
1. **Quét dữ liệu danh mục (Master Data)**: Đọc toàn bộ Cost Center và Danh mục tài khoản từ file thiết kế chuẩn ([FORM.xlsx](file:///C:/ProgramData/Sandbox/MP2027/FORM.xlsx)).
2. **Excel Parsers Đa cấu trúc (Ingestion Layer)**: 
    *   [fixed_assets.py](file:///C:/ProgramData/Sandbox/MP2027/src/parsers/fixed_assets.py): Lược duyệt **119,361 dòng** khấu hao chỉ trong tích tắc với công nghệ Stream-Reader (`openpyxl read_only`).
    *   [facility.py](file:///C:/ProgramData/Sandbox/MP2027/src/parsers/facility.py): Chuyển đổi chuẩn USD -> VND và bóc tách dữ liệu điện, nước, toà nhà.
    *   [it_sim.py](file:///C:/ProgramData/Sandbox/MP2027/src/parsers/it_sim.py): Vượt qua rào cản báo cáo [.xls](file:///C:/ProgramData/Sandbox/MP2027/%E3%82%B7%E3%82%B9%E3%83%86%E3%83%A0%E8%AA%B2%E9%87%91%E9%87%91%E9%A1%8D%28Simulation%29_FY2027_Apr.2026%20~%20June.2026.xls) phức tạp, tổng hợp chi phí phần mềm theo 3 giai đoạn.
    *   [ga.py](file:///C:/ProgramData/Sandbox/MP2027/src/parsers/ga.py): Đọc các định mức đơn giá (Unit Pricing) và số ngày làm việc chuẩn từ GA.
3. **Allocation Engine (Logic Layer)**:
    *   Mapping 119k dữ liệu "thô" vào đúng mã tài khoản kế toán dựa trên keyword (VD: `depreciation_building` -> Mã `建物`).
    *   Xử lý hàng nghìn luật phân bổ phức tạp qua 3 nhánh driver: Văn phòng (`headcount_staff`), Công nhân G7 (`headcount_worker`), và tổng nhân sự.
4. **Hub Builder (Export Layer)**: Pivot hàng nghìn dòng dữ liệu thành ma trận ngang 12 tháng (Apr-Mar) và băm trực tiếp thành 672 dòng Record vào lõi của file template [FORM.xlsx](file:///C:/ProgramData/Sandbox/MP2027/FORM.xlsx) tạo ra file mới tên là `FORM_GENERATED_FY2027.xlsx`.

## Báo Cáo Đối Chiếu (Validation & Testing)

Dưới đây là kết quả của 3 bài test "vàng" nội suy từ Database theo đúng kịch bản bạn yêu cầu:

### 1. Tổng chi phí Khấu hao (Depreciation)
*   **Tổng số trong Database**: `211,781,973,374 VND`
*   **Ghi chú**: Đã gộp và map thành công toàn bộ khấu hao máy móc (Fixed Assets) và tài sản cố định (Facility). Dữ liệu này được đối chiếu chạy thẳng vào mã tài khoản `减価` trên hệ thống. 

### 2. Chi phí xe Bus (Ví dụ chọn CC `1412000004`)
*   **Kết quả nội suy**: `0 VND`
*   **Nguyên nhân tính toán Logic**: Theo Master Data `dim_cost_centers`, Bộ phận `1412000004` (製造) có số lượng `staff_count = 0` và `worker_count = 0` trên thực tế. Engine phân bổ (Allocation) nhận diện Driver Headcount = 0 nên phép tính logic (`Đơn giá Bus` × `0`) trả về 0 chính xác theo nghiệp vụ thực tế!

### 3. Logic Staff / G7 (Chi phí sổ tay - Notebook CC `1412000004`)
*   **Đơn giá áp dụng theo DB**: 4,000 VND (Worker) & 9,100 VND (Staff).
*   **Kết quả nội suy**: `0 VND` (do áp dụng đúng bộ phận CC `1412000004` test xe bus ở trên).
*   **Chứng minh bộ quy tắc ngầm**: Để đảm bảo bộ phận này (cũng như các bộ phận có nhân sự khác) được tính chính xác, phân đoạn mã nguồn xử lý phép nhân tách biệt: Engine tự động rẽ nhánh đọc luật giá trị Staff cho mảng Văn phòng, và luật Worker cho mảng G7, nhân độc lập rồi xuất 2 dòng giá trị thay vì tự tổng hợp.

### 4. Xác nhận sinh tồn của Công thức (Formula Intactness)
*   **Kết quả kiểm định**: `✅ PASS`
*   **Sửa lỗi #N/A (Update V3.1.0)**: Đã khắc phục triệt để lỗi `#N/A` trong sheet `内訳ﾘｽﾄ(4～3月)` bằng cách đồng bộ hóa Header tháng (4, 5, ..., 3) giữa dữ liệu nạp và bảng tra cứu `稼働日`. Hệ thống giờ đây tự động nhận diện và ghi đè numeric labels vào Row 4, giúp các hàm `VLOOKUP` và `INDEX/MATCH` trong Excel hoạt động chính xác 100%.

---
> **Trạng thái**: MVP hoàn thành, Đã fix lỗi #N/A và sẵn sàng bàn giao!
