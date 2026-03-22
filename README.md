# Hướng dẫn sử dụng hệ thống MP2027 Manager

Hệ thống **MP2027 Manager** được thiết kế để hoàn toàn tự động hóa quy trình phân bổ tài chính. Để sử dụng phiên bản cuối cùng này, bạn chỉ cần làm theo 3 bước vô cùng đơn giản sau đây:

## 📂 Bước 1: Chuẩn bị File nguồn
Kéo thả tất cả các **file Excel nguồn** và file **form mẫu** (FORM.xlsx) vào chung thư mục `C:\ProgramData\Sandbox\MP2027`.
Các file bắt buộc phải có trong thư mục này gồm:
- `FORM.xlsx` (File gốc để Master Data và báo cáo trống)
- `施設課 MPFY2027.xlsx` (File Facility)
- `総務課 FY2027 MP 振替予定.xlsx` (File GA)
- `固定資産情報_Fixed_Assets...xlsx` (File Fixed Assets)
- Các file `.xls` thuộc hệ thống IT Simulation.
- `FY2027配賦額一覧 (2025.12.29).xlsx` (File chứa Master Allocation Rules)

*Hệ thống được thiết kế linh hoạt, đọc tự động mọi file có chứa keyword tương ứng, nên bạn có thể cập nhật data file thoải mái không sợ lỗi tên.*

## 🚀 Bước 2: Kích hoạt hệ thống
Chỉ cần **nhấn đúp chuột (Double-click)** vào file **`run_MP2027.bat`** nằm trong cùng thư mục này.
Hệ thống sẽ bật lên một màn hình console màu xanh, tự động thực hiện:
1. Nạp và dọn dẹp Database.
2. Đọc file qua Excel Parsers (Stream tốc độ cao).
3. Đẩy vào lõi Allocation Engine phân bổ hàng nghìn quy tắc.
4. Xuất kết quả qua Hub Builder.

*Quá trình này chỉ mất chưa tới 15 giây.*

## 📈 Bước 3: Lấy báo cáo kết quả
Sau khi cửa sổ `.bat` báo "HOAN THANH", hãy mở file **`FORM_GENERATED_FY2027.xlsx`** vừa mới xuất hiện.
* Lưu ý: Khi mở lên, Excel có thể mất thêm 1 giây để load lại các `SUMIF`, hãy tin tưởng vào các số liệu ở sheet `採算表(VND)` và `採算表(USD)` vì chúng đã được kết nối chuẩn với lõi `内訳ﾘｽﾄ(4～3月)`.

**Chúc bạn sử dụng phần mềm hiệu quả!** 🚀
