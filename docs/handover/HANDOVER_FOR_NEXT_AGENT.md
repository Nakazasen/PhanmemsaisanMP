# Bàn giao MP2027 cho nhà phát triển hoặc AI tiếp theo

## Bắt đầu từ đây

1. Đọc [README.md](../../README.md).
2. Đọc [kiến trúc hệ thống](../architecture/system_architecture.md).
3. Đọc [danh mục tính năng](../architecture/feature_registry.md).
4. Đọc [từ điển dữ liệu](../database/data_dictionary.md).
5. Đọc [quy trình phát hành/cập nhật](release_update_playbook.md).
6. Sinh lại baseline tĩnh:

```powershell
py scripts/generate_quality_baseline.py
```

## Trạng thái đã xác minh hiện tại

- Quality baseline hiện thu thập **638 test**, quét **145** tệp Python/**45.649** dòng và có 0 phát hiện Nghiêm trọng, 0 Cao, 5 Trung bình đã phân loại.
- Full regression cuối đạt `636 passed, 1 skipped, 1 deselected, 6 subtests passed` trong 525,45 giây; acceptance pipeline thật đạt riêng `1 passed` trong 147,89 giây.
- Các quy tắc nội dung đang hoạt động có chữ ký được xác minh lại theo metadata phát hành bất biến và được gộp theo giao dịch vào luồng nạp phân bổ cho cả CLI lẫn GUI.
- Người dùng cài `.mpcontent` hoặc `.mpupdate` offline mà không nhập/chọn/xác nhận khóa; năm tài chính, mục đích, chữ ký, hash và schema được kiểm tra trước khi kích hoạt nguyên tử.
- Quy trình đóng gói dùng PyInstaller onedir riêng cho ứng dụng và launcher. App onedir đo **164,97 MB**; install bundle đo **180,33 MB**.
- Setup 0.1.0 đã biên dịch bằng Inno Setup 6.7.3, kích thước **70,40 MB**, SHA-256 `a1b356dd38367288113234c01afd437a672a41bfbac430a39f0dde246be0f4cc`.
- Wizard cài/gỡ dùng duy nhất `installer/languages/Vietnamese.isl` được ghim theo upstream `jrsoftware/issrc`; audit có 296/296 key, 0 key thiếu và contract test bảo vệ không fallback tiếng Anh.
- Smoke Setup cuối đạt cài/health/gỡ với exit code 0; cold health xuyên launcher mất 57,04 giây, dữ liệu runtime nằm ngoài install root và dữ liệu người dùng sống sót sau uninstall.
- Shortcut Start Menu/Desktop được yêu cầu tồn tại và trỏ đúng launcher trước health-check; uninstall xóa shortcut và app nhưng không xóa runtime data.
- `release.json` là tài nguyên `_internal` bắt buộc; `trusted_signing_keys` hiện trống nên gói có chữ ký production bị từ chối an toàn.
- Setup hiện `NotSigned`; cần certificate Authenticode để giảm cảnh báo SmartScreen trên máy lạ.
- Smoke hiện tại chạy trên máy build có Python/Inno Setup, chưa thay thế bằng chứng trên Windows sạch thật không có Python/compiler/repository.

## Quy trình thay đổi an toàn

1. Xác định ranh giới tính năng trong danh mục.
2. Trước tiên thêm hoặc cập nhật một test hồi quy tập trung.
3. Thực hiện thay đổi triển khai nhỏ nhất.
4. Chạy test nhanh và Ruff.
5. Chạy kiểm tra sức khỏe runtime từ source nếu thay đổi đường dẫn/cơ sở dữ liệu.
6. Sinh lại tài liệu kiểm toán/schema khi áp dụng.
7. Chạy build đóng gói và kiểm tra sức khỏe bản đóng gói trước khi tuyên bố sẵn sàng phát hành.
8. Kiểm tra trạng thái Git và loại trừ artifact riêng tư/runtime/sinh tự động không được phê duyệt.

## Không được làm

- Không thay đổi công thức kế toán chỉ vì số dòng Excel thay đổi.
- Không dùng một trung tâm chi phí khác làm dữ liệu dự phòng mà không thông báo.
- Không phân phối các tệp `.py` rời làm bản cập nhật cho người dùng.
- Không lưu dữ liệu người dùng thay đổi được dưới cây `_internal`/`_MEIPASS` đã đóng gói.
- Không commit cơ sở dữ liệu, kết quả sinh ra, log, workbook riêng tư hoặc khóa ký.
- Không gọi baseline tĩnh là test nghiệm thu nghiệp vụ.

## Công việc phát hành còn lại

1. Provision khóa công khai Ed25519 production trong `release.json`; giữ khóa riêng ngoài repository và mọi artifact phân phối.
2. Ký Authenticode cho Setup bằng certificate phát hành và xác minh timestamp/signature trên máy đích.
3. Smoke bản Setup đã ký trên Windows sạch thật không có Python, compiler, Inno Setup hoặc repository; xác minh Start Menu/Desktop và một lượt tạo kết quả nhỏ.
4. Diễn tập kích hoạt/rollback N-1 → N bằng `.mpupdate` có chữ ký production thật.
5. Xác định endpoint/channel governance trước khi thêm kiểm tra/tải cập nhật online tùy chọn.
