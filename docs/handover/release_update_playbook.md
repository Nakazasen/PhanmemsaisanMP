# Quy trình phát hành, cập nhật và rollback MP2027

Tài liệu này phân tách rõ phần có thể sử dụng hiện nay và phần việc phát hành còn lại. Đối tượng đọc là người bảo trì chuẩn bị bản phát hành, không phải người vận hành thông thường.

## Những gì người dùng thông thường nhận được

### Cài đặt lần đầu

Gửi một tệp setup duy nhất được build từ định nghĩa Inno Setup. Bố cục đã cài đặt là PyInstaller **onedir**, vì vậy máy đích không cần Python, pip hoặc trình biên dịch.

Bộ cài hoạt động theo từng người dùng và đặt ứng dụng dưới `%LOCALAPPDATA%`. Không cần quyền quản trị. Dữ liệu dự án người dùng được lưu riêng dưới `%LOCALAPPDATA%\MPManager\Projects\MP2027` và không bị xóa khi gỡ cài đặt.

### Cập nhật code sau này

Artifact được hỗ trợ là một gói `.mpupdate` có chữ ký. Không gửi riêng từng tệp `.py`, `.dll` hoặc tệp thực thi thay thế. Từ phiên bản `0.1.8`, khi người dùng chọn **Cài bản cập nhật...**, ứng dụng tự quét các nguồn cập nhật đã cấu hình, chọn bản mới nhất và xin xác nhận cài; không yêu cầu người dùng tự tìm tệp. Ứng dụng âm thầm xác định khóa của gói từ `release.json` bất biến đi kèm, xác minh chữ ký và khả năng tương thích, chuẩn bị phiên bản onedir mới, chạy kiểm tra sức khỏe bản đóng gói, sao lưu cơ sở dữ liệu runtime và cập nhật `current.json` theo cách nguyên tử. Từ phiên bản `0.1.7`, sau khi kích hoạt update, chương trình lên lịch mở phiên bản mới, đóng giao diện/tiến trình phiên bản cũ; executable mới chờ PID cũ kết thúc rồi mới nạp GUI để người dùng không tiếp tục làm việc trên code cũ. Phiên bản cũ vẫn được giữ để rollback.

Người dùng thông thường không bao giờ nhập, chọn, phê duyệt hoặc quản lý khóa ký. Gói bị can thiệp, không tương thích hoặc không đáng tin cậy sẽ bị từ chối an toàn và chỉ tạo một lỗi ngắn gọn. Ứng dụng có thể dò nền khi khởi động từ thư mục LAN/UNC hoặc HTTPS đã cấu hình, sau đó chỉ hỏi **Cập nhật ngay / Để sau**; không tự cài đặt im lặng. File `.mpupdate` tải/copy về vẫn phải qua toàn bộ xác minh chữ ký, manifest, hash, schema và health-check như luồng chọn file offline.

> [!IMPORTANT]
> Không công bố khả năng tự cập nhật production cho đến khi khóa công khai phát hành thật được provision trong `release.json`, bộ cài mới build được xác minh và diễn tập kích hoạt/rollback từ N-1 lên N thành công trên profile Windows sạch.

### Chi phí hoặc quy tắc mới riêng cho bộ phận

Artifact được hỗ trợ là một gói `.mpcontent` có chữ ký, chỉ chứa dữ liệu quy tắc. Gói nội dung không được chứa Python, tệp thực thi, script, DLL hoặc đường dẫn ẩn. Người dùng chọn **Cài gói quy tắc...**; ứng dụng âm thầm xác minh tin cậy bất biến cho mục đích nội dung, năm tài chính, chữ ký, hash, schema và khả năng tương thích trước khi kích hoạt nguyên tử. Quy tắc đang hoạt động được xác minh lại cho mỗi lượt chạy năm tài chính và được gộp theo giao dịch vào luồng nạp phân bổ của cả CLI lẫn GUI. Người dùng thông thường không bao giờ thấy hoặc quản lý khóa ký.

## Điều kiện tiên quyết của máy phát hành

- Máy phát hành Windows x64.
- Repository ở commit phát hành đã được review.
- Đã cài các phụ thuộc phát triển Python được khóa phiên bản.
- PyInstaller có sẵn qua các phụ thuộc dự án.
- Inno Setup 6 để biên dịch tệp setup.
- Khóa ký Ed25519 riêng được giữ ngoài Git và ngoài gói cài.

Không bao giờ đặt khóa riêng trong source control, `dist`, `build`, `release_artifacts` hoặc gói dành cho người dùng. Ứng dụng chỉ chứa khóa công khai tương ứng.

## Quy trình tạo bộ cài ban đầu

1. Chạy các cổng source thông thường:

   ```powershell
   py -m compileall -q src scripts packaging
   py -m pytest -m "not requires_raw_excel and not real_pipeline_acceptance and not performance" -q
   ```

2. Build ứng dụng, cổng kiểm tra sức khỏe bản đóng gói, trình khởi chạy và gói cài:

   ```powershell
   py scripts/package_app.py
   ```

3. Xác nhận bố cục sau tồn tại:

   ```text
   release_artifacts/install_bundle/
   ├── MP2027_Launcher.exe
   ├── current.json
   ├── _internal/
   └── apps/<version>/
       ├── MP2027_Portable.exe
       ├── manifest.json
       └── _internal/
   ```

4. Xác minh `installer/languages/Vietnamese.isl` có provenance/commit/hash trong README cùng thư mục và đủ toàn bộ key của `Default.isl` thuộc compiler đang dùng.
5. Biên dịch `installer/MP2027_Manager.iss` bằng Inno Setup 6. Wizard phải dùng duy nhất ngôn ngữ `vietnamese`.
6. Cài trên một profile người dùng Windows sạch không có Python.
7. Khởi chạy từ menu Start và lối tắt màn hình nền.
8. Xác nhận lúc khởi động chỉ tạo/ghi dữ liệu runtime dưới thư mục gốc dự án MPManager.
9. Tạo một kết quả nhỏ đã được phê duyệt và review báo cáo kiểm toán/đầu vào thiếu.

Bộ cài ban đầu là ranh giới tin cậy khởi tạo. `current.json` cố định hash manifest ban đầu. Việc xác minh `.mpupdate` có chữ ký là bắt buộc cho các phiên bản ứng dụng tiếp theo.

### Bằng chứng build 0.1.0 trước commit LAN/WAN

Các số liệu dưới đây là snapshot lịch sử trước commit `c7fd76b`; không dùng để
tuyên bố HEAD hiện tại đã qua full regression hoặc đã được đóng gói lại.

| Cổng | Kết quả |
|---|---|
| Full regression | `636 passed, 1 skipped, 1 deselected, 6 subtests passed` |
| Acceptance pipeline thật | `1 passed` |
| Baseline tĩnh | 638 test thu thập; 0 nghiêm trọng, 0 cao, 5 trung bình |
| App onedir | 164,97 MB; 2.017 file |
| Install bundle | 180,33 MB; 2.031 file |
| Setup | 70,40 MB; SHA-256 `a1b356dd38367288113234c01afd437a672a41bfbac430a39f0dde246be0f4cc` |
| Bản dịch Inno | 296/296 key; 0 key thiếu; tiếng Việt là ngôn ngữ duy nhất |
| Cài/health/gỡ | Exit code `0/0/0`; cold health 57,04 giây |
| Dữ liệu runtime | Nằm ngoài install root; sống sót sau uninstall |
| Shortcut | Start Menu/Desktop tồn tại, trỏ launcher; được xóa khi uninstall |
| Authenticode | `NotSigned` |

> [!WARNING]
> Đây là bằng chứng trên máy build có Python và Inno Setup, chưa phải nghiệm thu Windows sạch thật. Không dùng bảng này để tuyên bố “mọi máy” cho đến khi hoàn thành smoke clean-machine và ký Authenticode.

## Hợp đồng cập nhật ứng dụng

Tệp nén phát hành `.mpupdate` phải chứa chính xác:

```text
manifest.json
manifest.sig
<every file listed by manifest.files>
```

Manifest ứng dụng yêu cầu các trường artifact dùng chung cùng với:

- `kind: "application"`
- `database_schema`
- `entrypoint`
- `health_check: "--health-check"`
- `key_id`

Mỗi file được liệt kê có `path`, SHA-256 và kích thước byte. File ngoài dự kiến, đường dẫn không an toàn, hash/kích thước sai, chữ ký sai, schema không được hỗ trợ hoặc phiên bản không tương thích phải bị từ chối an toàn trước khi chuẩn bị hoặc kích hoạt. `manifest.key_id` là đầu vào tra cứu không đáng tin cậy; khóa công khai Ed25519 thực tế phải lấy từ danh sách cho phép `trusted_signing_keys` bất biến đi kèm phiên bản đang chạy, với mục đích `"application"`.

## Hợp đồng gói nội dung

Tệp nén `.mpcontent` chứa chính xác:

```text
manifest.json
manifest.sig
rules.json
```

`rules.json` có dạng:

```json
{
  "schema": 1,
  "rules": [
    {
      "source_dept": "GA",
      "item_name": "Example approved cost",
      "unit_price": 100000,
      "driver_type": "headcount_all"
    }
  ]
}
```

Các trường quy tắc bắt buộc là `source_dept`, `item_name`, `unit_price` và `driver_type`. Các trường tùy chọn chỉ giới hạn ở tên/mã tài khoản, tháng ghi sổ, đơn vị và mô tả driver raw. Các driver được phép:

- `headcount_all`
- `headcount_staff`
- `headcount_worker`
- `headcount_male`
- `headcount_female`
- `working_days`
- `fixed_ratio`

Loại driver mới hoặc hành vi thực thi là bản cập nhật code ứng dụng, không phải gói nội dung. Vẫn cần phê duyệt kế toán và bằng chứng hồi quy; chữ ký số hợp lệ chứng minh nguồn gốc/tính toàn vẹn, không chứng minh tính đúng đắn nghiệp vụ.

## Diễn tập rollback trước khi phát hành

1. Cài hoặc chuẩn bị phiên bản N-1.
2. Tạo và giữ lại một mẫu dự án/kết quả nhỏ đã được phê duyệt.
3. Chuẩn bị phiên bản N có chữ ký và chạy kiểm tra sức khỏe bản đóng gói.
4. Kích hoạt N và xác nhận trình khởi chạy xác định N.
5. Xác nhận dự án runtime và cơ sở dữ liệu hiện có vẫn đọc được.
6. Kích hoạt rollback và xác nhận trình khởi chạy xác định N-1.
7. Xác nhận dữ liệu dự án người dùng không bị xóa hoặc sao chép vào bất kỳ phiên bản ứng dụng nào.
8. Ghi lại lệnh, hash, phiên bản và kết quả trong bằng chứng phát hành.

## Checklist nghiệm thu phát hành

- [ ] Cổng compile/source và full regression local đạt trên commit phát hành.
- [ ] Test an toàn cho CI đạt trên cả Windows và Linux ở commit phát hành.
- [x] Contract hiệu năng/đường nóng liên quan đạt; benchmark opt-in chỉ chạy khi code đường nóng thay đổi.
- [x] `--health-check` bản đóng gói trả exit code 0.
- [x] Trình khởi chạy ổn định mở phiên bản do `current.json` chọn.
- [x] Setup cài theo từng người dùng trên máy build, không yêu cầu quyền quản trị và runtime không gọi Python ngoài.
- [x] Wizard cài/gỡ chỉ dùng tiếng Việt và file dịch không thiếu key.
- [x] Shortcut Start Menu/Desktop được tạo đúng và dọn khi uninstall.
- [ ] Test nhanh trên Windows sạch thật/không Python thành công.
- [ ] Setup được ký Authenticode bằng certificate phát hành.
- [ ] Diễn tập kích hoạt và rollback từ N-1 lên N bằng khóa production thành công.
- [x] Không có DB, workbook kết quả, workbook nguồn riêng tư, log hoặc khóa riêng trong gói đã smoke.
- [ ] Ghi chú phát hành cuối nêu rõ thay đổi quy tắc nghiệp vụ và schema.

## Các điểm đang chặn tuyên bố tự cập nhật production

1. Provision khóa công khai Ed25519 production trong `release.json` bất biến; giữ khóa riêng ngoài Git và mọi artifact.
2. Ký Authenticode cho Setup và timestamp bằng certificate phát hành.
3. Hoàn thành nghiệm thu Windows sạch thật/không Python và kích hoạt/rollback N-1 → N bằng gói có chữ ký production.
4. Xác minh endpoint LAN đã cấu hình có thể truy cập từ máy pilot và giữ channel `pilot` trong đợt diễn tập.

## Cấu hình tự phát hiện update LAN/WAN tại công ty

> [!IMPORTANT]
> `update_sources.default.json` đã được cấu hình với thư mục LAN do người dùng
> xác nhận. Phải giữ đúng cấu hình này khi build Setup để mọi máy cài mới nhận
> cùng một nguồn. Cấu hình được bundle vào `_internal` của app.

### 1. Chọn một nguồn phát hành

**Nguồn LAN/Domain đã chốt:**

```json
{
  "schema": 1,
  "startup_check": true,
  "sources": [
    {
      "type": "folder",
      "location": "\\\\fstvn01\\Data\\00_KDTVN Common(KDTVN共通)\\⑤Production Engineering(製造技術)\\Hang muc can luu\\Vinh\\MP Saisan\\release_update",
      "enabled": true
    }
  ]
}
```

**HTTPS/WAN chưa có và tạm thời không cấu hình.** Mẫu dưới đây chỉ dùng trong
tương lai khi người dùng cung cấp URL gốc chứa `latest.json` và package:

```json
{
  "schema": 1,
  "startup_check": true,
  "sources": [
    {
      "type": "https",
      "location": "https://updates.congty.example/mp2027",
      "enabled": true
    }
  ]
}
```

Chỉ `https://` được chấp nhận cho WAN. Không đưa username/password vào URL.
Không đưa domain mẫu ở trên vào bản phát hành hiện tại.

Có thể dùng `%PROGRAMDATA%\MPManager\update_sources.json` làm policy cao nhất
cho một máy/nhóm máy đã cài. Policy thay thế toàn bộ config mặc định và user
config; nó chỉ quyết định **nơi dò**, không thể thay thế yêu cầu ký Ed25519.

### Trạng thái pilot cập nhật ngày 21.07.2026

- Bootstrap Setup `0.1.0` đã được build với public key
  `mp2027-prod-2026` và nguồn LAN trong `_internal`.
- Gói pilot `0.1.1` đã được cài thủ công thành công. Gói cập nhật `0.1.9` đã được
  ký/publish; Setup `0.1.9` đã được build và copy lên LAN; `latest.json` hiện trỏ
  tới `0.1.9`.
- Bản `0.1.2` hiển thị phiên bản ứng dụng trên giao diện. Bản `0.1.3` dùng chung
  giới hạn manifest 1 MiB cho dò nền, kiểm tra gói và builder; builder từ chối gói
  vượt giới hạn trước khi publish. Manifest thực tế là 261,83 KiB. Client `0.1.1`
  còn giới hạn dò nền 256 KiB nên không tự thấy gói; dùng **Cài bản cập nhật...**
  để cài trực tiếp `0.1.5` một lần. Bản `0.1.4` hiển thị người phụ trách trong
  title và dùng `latest.json` để popup tự động hiển thị nội dung phát hành. Sau khi
  chạy `0.1.5`, các bản tiếp theo dùng giới hạn mới và có thể được dò tự động.
  Bản `0.1.5` cho phần biểu mẫu cuộn được để Nhật ký xử lý luôn thấy trên màn hình
  thấp và tự bật mẫu manifest cũ đã nhận diện đúng nhưng vô tình bị để TẮT.
  Bản `0.1.6` sửa công thức tài sản cố định, thời điểm khám sức khỏe tuyển dụng,
  đồng thời tính du lịch tháng 5 và bánh Trung Thu tháng 9 theo tổng headcount của
  chính tháng phát sinh.
  Bản `0.1.7` đưa dữ liệu Nam/Nữ nhập thủ công vào snapshot chạy để tính đủ chi
  phí khám sức khỏe định kỳ tháng 12, loại bỏ màu đỏ staging tồn dư ở dòng 58 và
  tự đóng bản cũ/tự mở bản mới sau khi cập nhật.
  Bản `0.1.8` dọn dữ liệu phân bổ cũ theo vùng payload thực tế thay vì chặn cứng
  ở dòng 199; nút cài cập nhật tự quét nguồn công ty và chọn bản mới nhất; Hướng
  dẫn trực quan có tìm kiếm nhanh không phân biệt dấu.
  Bản `0.1.9` thay FORM chính thức bằng bản QLLN ngày 21.07.2026, bảo toàn dòng
  30~37 và chuyển điểm bắt đầu chi phí chung sang dòng 38; đồng thời sửa lookup
  account theo cost type và bảo đảm chi phí sự kiện thành lập công ty được cộng
  thêm mà không loại mất hạng mục cũ.
- Còn bắt buộc: nghiệm thu GUI trên Windows sạch/pilot, cập nhật N-1 → N,
  rollback và lưu evidence.

### 2. Tạo trust bootstrap trước khi phát hành `.mpupdate`

`release.json` của 0.1.0 đang không có trusted signing key, nên chưa thể nhận
update production. Chỉ chạy một lần tại máy phát hành an toàn; private key phải
nằm ngoài repository, OneDrive đồng bộ công khai, `dist`, Setup và máy client:

```powershell
py scripts/provision_update_key.py `
  --private-key-output "D:\MP2027-Secrets\mp2027-prod-2026.key" `
  --key-id "mp2027-prod-2026"
```

Lệnh thêm **public key** vào `release.json`; hãy review diff, backup private key
theo quy định công ty, rồi build một Setup bootstrap mới. Nếu 0.1.0 đã được phát
rộng rãi, client phải cài bootstrap Setup này một lần trước khi có thể tin
`.mpupdate` đã ký bằng key mới.

### 3. Build Setup mang nguồn mặc định và public key

```powershell
py -m pytest tests\test_update_delivery.py tests\test_app_updates.py tests\test_packaging_entrypoint.py -q
py scripts/package_app.py
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer\MP2027_Manager.iss
```

Xác nhận `dist\MP2027_Portable\_internal\update_sources.default.json` đúng
đường dẫn công ty và `release.json` chứa public key production trước khi phân
phối Setup.

### 4. Tạo và publish update

Tăng `release.json.version`, build onedir mới, rồi tạo/publish bằng một lệnh:

```powershell
py scripts/package_app.py --build-update `
  --private-key-file "D:\MP2027-Secrets\mp2027-prod-2026.key" `
  --key-id "mp2027-prod-2026" `
  --min-app-version "0.1.0" `
  --publish-dir "\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan\release_update" `
  --release-notes "Mô tả ngắn thay đổi đã duyệt"
```

Publisher copy package sang tên `.part`, kiểm tra hash, rename package nguyên tử,
rồi mới thay `latest.json`. Vì vậy client chỉ nhìn thấy update đã hoàn chỉnh.
LAN chỉ cần `.mpupdate`; HTTPS dùng thêm `latest.json` theo
`schemas/update-catalog.schema.json`.

### 5. Diễn tập bắt buộc

1. Cài bootstrap Setup vào một client pilot không có Python.
2. Chạy app; UI phải hiện bình thường ngay cả khi share/HTTPS tạm mất kết nối.
3. Publish một bản N mới hơn vào nguồn đã chọn.
4. Mở lại app, xác nhận hiện prompt phiên bản N; chọn **Cập nhật ngay**.
5. Chờ health-check xong; xác nhận bản cũ tự đóng, launcher tự mở lại và phiên bản N hoạt động.
6. Xác nhận dữ liệu `%LOCALAPPDATA%\MPManager\Projects\MP2027` còn nguyên.
7. Thử rollback N → N-1 theo thủ tục release và lưu evidence/hash.

Không công bố auto-update production trước khi cả diễn tập N-1 → N → rollback,
smoke Windows sạch và Authenticode Setup được hoàn tất.
