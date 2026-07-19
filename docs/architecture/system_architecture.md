# MP2027 Manager — Bản đồ kiến trúc kỹ thuật

Đây là bản đồ bàn giao phản ánh trạng thái hiện tại, không phải yêu cầu tái cấu trúc các quy tắc nghiệp vụ.

## Phạm vi hệ thống

MP2027 Manager là ứng dụng desktop Windows đọc các nguồn Excel/CSV đã được chọn lọc, xác định đầu vào theo năm tài chính, nạp dữ liệu chuẩn hóa vào SQLite, tính toán phân bổ và ghi các workbook FORM theo từng trung tâm chi phí.

```mermaid
flowchart LR
    User["Người vận hành"] --> UI["Giao diện Tkinter: universal_app.py"]
    UI --> Config["ProjectConfig: đường dẫn trong project.json"]
    UI --> Preflight["Kiểm tra trước năm tài chính: fiscal_run.py"]
    Preflight --> Parsers["Bộ đọc đầu vào: src/parsers"]
    Parsers --> DBLoad["Bộ nạp cơ sở dữ liệu"]
    DBLoad --> SQLite[("Cơ sở dữ liệu vận hành SQLite")]
    SQLite --> Engine["Bộ máy phân bổ: src/engine"]
    Engine --> Export["Bộ ghi/xuất FORM"]
    Export --> Output["Kết quả và báo cáo kiểm toán"]
    Output --> User
    Update["Gói cập nhật/nội dung có chữ ký"] --> Security["An toàn chữ ký và ZIP"]
    Security --> Launcher["Trình khởi chạy/cập nhật bên ngoài"]
    Launcher --> UI
```

## Trách nhiệm của các thành phần

| Khối | Vị trí chính | Trách nhiệm | Không được phụ trách |
|---|---|---|---|
| Giao diện / lớp vỏ | `src/universal_app.py` | Thao tác người dùng, hộp thoại, điều phối lượt chạy | Công thức mới không có test bộ máy |
| Cấu hình dự án/đường dẫn | `src/services/project_config.py` | Đường dẫn tương đối và vai trò lưu trữ | Quyết định phân bổ |
| Kiểm tra trước năm tài chính | `src/services/fiscal_run.py` | Bằng chứng nguồn/năm tài chính; từ chối an toàn | Tự tạo dữ liệu nguồn còn thiếu |
| Bộ đọc dữ liệu | `src/parsers/` | Đọc cấu trúc workbook/CSV | Định dạng kết quả |
| Cơ sở dữ liệu | `src/db/` | Schema, migration, nhập dữ liệu | Quyết định giao diện |
| Bộ máy nghiệp vụ | `src/engine/` | Driver, ánh xạ tài khoản, phân bổ, bộ ghi | Đường dẫn phụ thuộc máy |
| Dịch vụ | `src/services/` | Lịch sử, kiểm tra sức khỏe, cập nhật, nhân sự | Dữ liệu dự phòng chưa được xác minh |
| Công cụ kiểm toán | `src/audit/`, `scripts/` | Bằng chứng và xác minh | Mặc định làm thay đổi kết quả |
| Đóng gói | `packaging/`, `scripts/package_app.py` | PyInstaller onedir và cổng kiểm tra sức khỏe | Dữ liệu runtime trong gói |
| Test | `tests/` | Bằng chứng hồi quy và hợp đồng | Là đặc tả nghiệp vụ duy nhất |

## Lượt chạy thông thường

1. Mở giao diện qua `run_MP2027.bat` hoặc tệp thực thi đã đóng gói.
2. Xác định vùng lưu trữ qua `project.json` và thư mục gốc runtime ổn định.
3. Chạy kiểm tra trước đối với loại nguồn, bằng chứng năm tài chính và đầu vào còn thiếu.
4. Đọc nguồn và nạp dữ liệu chuẩn hóa vào SQLite.
5. Tính driver, ánh xạ tài khoản và phân bổ.
6. Giữ nguyên cấu trúc FORM và xuất workbook theo từng trung tâm chi phí.
7. Xem báo cáo kiểm toán và đầu vào còn thiếu trước khi chấp nhận kết quả.

## Luồng cập nhật

```mermaid
sequenceDiagram
    participant U as Người dùng
    participant L as Trình khởi chạy
    participant S as Bộ xác minh chữ ký
    participant A as Bộ cập nhật ứng dụng
    participant H as Kiểm tra sức khỏe
    U->>L: Mở ứng dụng
    L->>S: Xác minh manifest và tệp nén
    S-->>L: Hợp lệ hoặc không hợp lệ
    L-->>U: Cập nhật ngay hoặc để sau nếu hợp lệ
    L->>A: Chuẩn bị phiên bản onedir bất biến
    A->>H: Chạy cổng kiểm tra sức khỏe
    H-->>A: Đạt hoặc không đạt
    A->>L: Kích hoạt con trỏ theo cách nguyên tử
    L-->>U: Chạy phiên bản mới hoặc giữ phiên bản cũ
```

Người dùng thông thường không thao tác với khóa ký. Chữ ký hợp lệ được kiểm tra âm thầm; chỉ gói không hợp lệ, không tương thích hoặc hỏng mới tạo cảnh báo ngắn gọn.

## Các mô-đun rủi ro cao

- `src/universal_app.py`: bề mặt giao diện/điều phối lớn; chỉ thay đổi theo từng điểm nối nhỏ.
- `src/engine/allocator.py`: hành vi phân bổ trung tâm; phải được bảo vệ bằng test đặc trưng hóa.
- `src/engine/hub_builder.py`: bề mặt điều phối dựng/xuất lớn.
- `src/services/fiscal_run.py`: chính sách nguồn và năm tài chính từ chối an toàn.
- `src/db/schema.py` và `src/db/migrations.py`: ranh giới tương thích lưu trữ.

## Bất biến đóng gói

- Không có dữ liệu thay đổi được dưới `_MEIPASS` của PyInstaller.
- Thư mục gốc mặc định khi đóng gói: `%LOCALAPPDATA%\MPManager\Projects\MP2027`.
- Chế độ portable phải được bật rõ ràng bằng `MP_MANAGER_PORTABLE_MODE=1`.
- Bản phân phối dùng onedir, không dùng onefile.
- Cổng đóng gói xác minh tài nguyên và chạy `--health-check`.
- Kết quả, cơ sở dữ liệu, log, bí mật và khóa ký riêng không phải là artifact nguồn phát hành.

## Bố cục phát hành

```text
<install-root>/
├── MP2027_Launcher.exe
├── current.json
├── _internal/
└── apps/<version>/
    ├── manifest.json
    ├── MP2027_Portable.exe
    └── _internal/
```

Trình khởi chạy ổn định đọc `current.json` được bảo vệ tính toàn vẹn, xác định phiên bản bất biến đang hoạt động và chạy tệp thực thi đó mà không cần Python. Định nghĩa Inno Setup cài cây thư mục này theo từng người dùng dưới `%LOCALAPPDATA%` để bản cập nhật có chữ ký có thể chuẩn bị và chuyển phiên bản theo cách nguyên tử mà không cần quyền quản trị. Dữ liệu dự án thay đổi được nằm riêng trong thư mục gốc dự án MPManager và không thuộc phạm vi rollback phiên bản. Bộ cài đầu tiên là ranh giới tin cậy ban đầu; các gói `.mpupdate` tiếp theo bắt buộc có chữ ký Ed25519.

## Chính sách VC++ runtime

PyInstaller mang theo Python runtime và các phụ thuộc nhị phân được phát hiện trong gói onedir. Bộ cài không âm thầm tải hoặc cài VC++ redistributable. Việc xác minh phát hành phải chạy trên một bản Windows sạch được hỗ trợ; nếu kiểm tra phụ thuộc hoặc phép thử đó chứng minh cần redistributable, hãy cố định phiên bản và đóng kèm bản redistributable offline được Microsoft hỗ trợ.

## Khoảng trống đã biết

1. Khóa công khai phát hành thật chưa được provision; giao diện đã có thao tác **Cài gói quy tắc...** và xác minh gói `.mpcontent` theo cơ chế tin cậy runtime.
2. Bộ tạo `.mpupdate` có chữ ký và tái lập đã tồn tại, nhưng luồng kiểm tra/cài đặt qua kênh truyền tải chưa được nối vào giao diện.
3. Máy build hiện tại chưa cài Inno Setup 6 nên vẫn còn bước biên dịch bộ cài.
4. Vẫn phải xác minh trên Windows sạch/không có Python và diễn tập rollback từ N-1.

## Bằng chứng đóng gói hiện tại

Bản build onedir cho ứng dụng/trình khởi chạy bằng PyInstaller hiện đã hoàn tất, bao gồm `--health-check` ở môi trường đóng gói cách ly và việc tạo `release_artifacts/install_bundle`. Điều này chứng minh hợp đồng trên máy build, chưa chứng minh khả năng tương thích với máy sạch.
