# Hướng dẫn Setup Inno Setup và Auto-update chuẩn của MP2027 Manager

Tài liệu này mô tả cách MP2027 Manager đang được đóng gói, cài đặt lần đầu và
tự cập nhật. Đây là hướng dẫn vận hành dựa trên mã nguồn hiện tại cùng
`docs/handover/release_update_playbook.md`.

> Chính sách phát hành: `HASH_ONLY_LAN`. Gói cập nhật **không dùng chữ ký số,
> private/public key, `manifest.sig`, `key_id` hay `trusted_signing_keys`**.
> Thư mục LAN do công ty kiểm soát là ranh giới tin cậy; tính toàn vẹn được bảo
> vệ bằng SHA-256, kích thước, manifest, giải nén an toàn và health-check.

## 1. Hai phương thức phân phối

| Phương thức | Dùng khi | Artifact | Nơi publish |
|---|---|---|---|
| Setup Inno Setup | Cài mới, chuyển máy hoặc khôi phục thủ công | `MP2027_Manager_Setup_<version>.exe` | Thư mục phần mềm LAN `MP Saisan` |
| Auto-update | Nâng cấp bản cài MP2027 hiện có | `MP2027_Manager-<version>.mpupdate` + `latest.json` | `MP Saisan\release_update` |

Yêu cầu “đóng gói theo tiêu chuẩn update”, “làm bản update” hoặc “phát hành
update” luôn có nghĩa là làm **cả hai**: Setup trên thư mục phần mềm LAN và
package/catalog trong `release_update`. Chỉ yêu cầu “tạo Setup” thì không tự
tạo `.mpupdate`.

## 2. Thành phần và cấu trúc chính

| Thành phần | Vai trò |
|---|---|
| `release.json` | Metadata bất biến được đóng vào portable app: version, channel, schema tương thích. |
| `installer/MP2027_Manager.iss` | Kịch bản Inno Setup cài bundle ban đầu. |
| `MP2027_Portable.spec` | PyInstaller spec cho app onedir; đưa assets, `release.json`, nguồn update mặc định, FORM và seed data vào app. Runtime state, database, log và backup bị loại trừ. |
| `MP2027_Manager.spec` | PyInstaller spec cho launcher ổn định. |
| `scripts/package_app.py` | Build app/launcher, health-check, ghép install bundle, tạo `.mpupdate` và publish atomically. |
| `scripts/update_launcher.py` | Launcher đọc `current.json`, kiểm hash `manifest.json` rồi khởi chạy app version đang active. |
| `src/services/update_delivery.py` | Nạp nguồn update, đọc catalog, phát hiện bản mới và tải vào cache local. |
| `src/services/app_updates.py` | Kiểm tra package, stage, health-check, backup database, kích hoạt hoặc rollback. |
| `src/services/update_security.py` | Kiểm tra schema/hash/đường dẫn, safe extraction và giới hạn dung lượng. |

Bundle cài đặt ban đầu có dạng:

```text
<install-root>/
├── MP2027_Launcher.exe
├── current.json
└── apps/
    └── <version>/
        ├── MP2027_Portable.exe
        ├── manifest.json
        └── _internal/...
```

`current.json` chứa version, entrypoint và SHA-256 của `manifest.json`; launcher
không chạy app nếu pointer hoặc manifest không khớp.

## 3. Nguồn update chuẩn và trust boundary

Hai endpoint LAN được phê duyệt:

```text
Thư mục Setup:
\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan

Thư mục auto-update:
\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan\release_update
```

`update_sources.default.json` được đóng trong app và hiện dùng đúng folder
`release_update` với `startup_check: true`. Ứng dụng nạp cấu hình theo thứ tự
tăng dần ưu tiên:

1. Default được đóng trong app: `update_sources.default.json`.
2. Override của người dùng: `<runtime-root>/update_sources.json`.
3. Company policy: `%PROGRAMDATA%\MPManager\update_sources.json`.

Mỗi file cấu hình phải có đúng cấu trúc sau:

```json
{
  "schema": 1,
  "startup_check": true,
  "sources": [
    {
      "type": "folder",
      "location": "\\\\server\\share\\release_update",
      "enabled": true
    }
  ]
}
```

Client cũng hỗ trợ nguồn `https` hợp lệ (không cho credentials trong URL), nhưng
luồng phát hành hiện hành của MP2027 là `HASH_ONLY_LAN`, dùng folder LAN nêu trên.

## 4. Quy tắc version và điều kiện trước phát hành

Nguồn sự thật duy nhất để chọn version là:

```text
<release_update>\latest.json
```

Không suy version từ tên artifact local, commit, nhánh, thư mục release cũ hoặc
release note. Trước khi thay đổi version/build/publish phải:

1. Đọc `latest.json`; kiểm schema, version, package, SHA-256 và size.
2. Đọc package mà catalog trỏ tới và xác nhận hash/size thực tế khớp catalog.
3. Chọn patch kế tiếp. Ví dụ catalog `0.1.6` thì mặc định phát hành `0.1.7`.
4. Kiểm `release.json` và `installer/MP2027_Manager.iss` đang cùng version.
5. Kiểm `update_sources.default.json` vẫn trỏ đúng `release_update` đã duyệt.
6. Kiểm tra Setup/package cùng version dự kiến ở local và LAN. Nếu cùng tên có
   hash khác, dừng; không ghi đè, đổi tên tùy ý hoặc xóa artifact cũ.
7. Xác minh cả hai endpoint LAN đọc được. Ngay trước publish, tạo một probe file
   tên duy nhất trong `release_update`, xác minh ghi được rồi chỉ xóa probe đó.

Chuẩn bị source:

```powershell
git pull --ff-only
git status --short --branch
py -m pytest tests/test_app_updates.py tests/test_update_delivery.py tests/test_content_packs.py tests/test_update_security.py tests/test_packaging_entrypoint.py tests/test_repo_handover_docs.py -q
```

Không publish nếu test/health-check lỗi, LAN không đọc/ghi được, catalog không
đọc được/không nhất quán, version không phải patch kế tiếp, hoặc worktree có thay
đổi không liên quan có nguy cơ bị ghi đè. Không tự `commit`/`push` chỉ vì phát
hành, trừ khi chủ sở hữu yêu cầu riêng.

Khi chuẩn bị release, cập nhật đồng bộ:

```text
release.json
installer/MP2027_Manager.iss
docs/handover/releases/<version>.md
```

## 5. Build portable app và launcher

Lệnh chuẩn thực hiện toàn bộ build local:

```powershell
py scripts/package_app.py
```

Nó thực hiện tuần tự:

1. Dùng PyInstaller `--clean --noconfirm` build `MP2027_Portable.spec` thành
   `dist/MP2027_Portable/`.
2. Kiểm các tài nguyên bắt buộc: executable, icon, `FORM.xlsx`, `release.json`
   và `update_sources.default.json`.
3. Chạy `MP2027_Portable.exe --health-check` với `LOCALAPPDATA` cô lập.
4. Build `MP2027_Manager.spec` thành `dist/MP2027_Launcher/`.
5. Ghép `release_artifacts/install_bundle/`: portable dưới
   `apps/<version>/`, launcher ở root, tạo `apps/<version>/manifest.json` và
   `current.json`.
6. Chạy launcher `--health-check`, trong đó launcher resolve pointer và gọi
   portable app của version active.

Health-check của portable xác nhận metadata release, thư mục runtime ghi được,
seed FORM tồn tại và SQLite hợp lệ. Không bỏ qua health-check hoặc dùng bundle
chưa qua health-check để làm Setup/package update.

## 6. Đóng gói Setup bằng Inno Setup

### 6.1 Cách Setup được cấu hình

`installer/MP2027_Manager.iss`:

- Dùng `AppVersion` phải khớp `release.json`.
- Lấy toàn bộ `release_artifacts/install_bundle` vào `{app}`.
- Cài per-user tại `{localappdata}\MP2027 Manager`, với
  `PrivilegesRequired=lowest`.
- Tạo shortcut trỏ tới `MP2027_Launcher.exe`, không trỏ trực tiếp portable app.
- Có ngôn ngữ tiếng Việt từ `installer/languages/Vietnamese.isl`.
- Dùng nén `lzma2`, output
  `release_artifacts/MP2027_Manager_Setup_<version>.exe`.
- Chỉ xóa `.staging` khi uninstall; không xóa runtime/project/user data.

### 6.2 Compiler Inno Setup

Ưu tiên compiler chuẩn:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "installer\MP2027_Manager.iss"
```

Trên máy phát hành hiện tại, nếu compiler chuẩn không có, fallback đã xác minh là
Inno Setup đi kèm Antigravity IDE:

```powershell
& "C:\Users\tvn183660\AppData\Local\Programs\Antigravity IDE\resources\app\node_modules\innosetup\bin\ISCC.exe" "installer\MP2027_Manager.iss"
```

Chỉ dùng fallback khi `ISCC.exe` tồn tại. Sau compiler, kiểm tra exit code,
kích thước và SHA-256 của Setup local.

### 6.3 Publish Setup an toàn

Setup thuộc thư mục phần mềm LAN, **không** thuộc `release_update`. Quy trình:

1. Xác minh `MP2027_Manager_Setup_<version>.exe` local và file đích chưa va chạm.
2. Copy Setup lên LAN với tên `<setup>.part`.
3. Đọc lại file `.part` trên LAN; so SHA-256 và size với local.
4. Chỉ khi khớp mới rename `.part` thành `.exe` chính thức.
5. Đọc lại `.exe` cuối cùng, so hash/size lần nữa và xác nhận không còn `.part`.

Không ghi đè hoặc xóa Setup lịch sử. Với cài mới/máy sạch, kiểm thử Setup hoặc
bundle trên profile Windows sạch trước khi coi là phát hành hoàn tất.

## 7. Tạo `.mpupdate` chuẩn

`.mpupdate` là ZIP có `manifest.json` và toàn bộ file của portable onedir. Hàm
`build_hash_checked_update` tạo inventory deterministic, có path tương đối,
SHA-256 và size cho từng file. Nó từ chối symlink, file vượt ranh giới app,
`manifest.json` trùng, thiếu `MP2027_Portable.exe`, version sai định dạng hoặc
artifact quá giới hạn.

Manifest application có các trường chính:

```json
{
  "schema": 1,
  "kind": "application",
  "id": "MP2027_Manager",
  "version": "x.y.z",
  "min_app_version": "x.y.z",
  "database_schema": 1,
  "health_check": "--health-check",
  "entrypoint": "MP2027_Portable.exe",
  "files": [
    {"path": "...", "sha256": "<64 hex>", "size": 123}
  ]
}
```

Lệnh đầy đủ tạo package và publish package/catalog bằng một lệnh:

```powershell
py scripts/package_app.py --build-update `
  --min-app-version "0.1.1" `
  --publish-dir "\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan\release_update" `
  --release-notes "- Mô tả ngắn thay đổi cho người dùng"
```

`--min-app-version` là version cũ nhất tương thích với update này, không mặc
định là `0.1.1`; chọn theo thay đổi schema/khả năng tương thích thực tế. Release
notes trong catalog là chuỗi tối đa 2.000 ký tự.

Khi publish, code thực hiện:

1. Copy local package tới `<package>.part` trong publish directory.
2. So SHA-256 của `.part` và local package.
3. Rename atomically `.part` thành `.mpupdate`.
4. Tạo catalog `latest.json.part`.
5. Rename atomically thành `latest.json` **sau cùng**.

Do `latest.json` được xuất bản sau package, client không bao giờ thấy catalog
trỏ vào một package copy dở. Preflight collision ở mục 4 là bắt buộc trước lệnh
này để bảo vệ artifact lịch sử khỏi một file cùng tên nhưng khác hash.

Catalog chuẩn có đúng các field:

```json
{
  "schema": 1,
  "channel": "pilot",
  "version": "x.y.z",
  "package": "MP2027_Manager-x.y.z.mpupdate",
  "sha256": "<64 hex>",
  "size": 123,
  "notes": "- Thay đổi dành cho người dùng"
}
```

Không copy tay `latest.json` trước package hoặc thay catalog bằng cách không
atomic. Không thêm tham số key/signing vào lệnh đóng gói.

## 8. Runtime auto-update hoạt động như thế nào

### 8.1 Discovery và download

1. Client nạp config nguồn update, bỏ qua nguồn disable/lỗi.
2. Với folder LAN, client ưu tiên `latest.json`: validate đủ field, version,
   filename an toàn, SHA-256 64 hex và size. Nếu catalog có, package phải có
   version bên trong, hash và size khớp catalog.
3. Nếu một folder legacy không có `latest.json`, code có thể quét các
   `*.mpupdate`; nhưng đây không phải chuẩn publish MP2027 vì không có notes và
   không cung cấp catalog atomic. Luồng hiện hành luôn publish `latest.json`.
4. Các candidate chỉ được chọn khi version lớn hơn version hiện tại; client chọn
   candidate lớn nhất.
5. Package được copy/tải vào `<runtime-root>/.updates/downloads/` qua file tạm,
   kiểm size và SHA-256 rồi mới rename vào cache.

### 8.2 Kiểm tra, stage và kích hoạt

`install_runtime_application_update` thực hiện theo thứ tự fail-closed:

1. Đọc version của app hiện tại từ `release.json` đã được bundle cùng app.
2. Mở `.mpupdate`, đọc/validate manifest. Target phải mới hơn current,
   current phải không thấp hơn `min_app_version`, database schema không được hạ,
   health command phải là `--health-check`, entrypoint phải an toàn và có trong
   manifest.
3. Kiểm tra archive có đúng tập file được manifest kê khai: không thiếu/không dư.
4. Giải nén vào thư mục tạm dưới `<install-root>/.staging/`; cấm absolute path,
   `..`, path ẩn/mơ hồ và ghi ra ngoài target. Có giới hạn tổng artifact 512 MB.
5. So hash và size của từng file giải nén với manifest.
6. Đổi tên thư mục stage thành `<install-root>/apps/<target-version>`.
7. Chạy executable đã stage với `--health-check` trong profile `LOCALAPPDATA`
   cô lập, timeout 60 giây.
8. Backup tất cả `.db`, `.sqlite`, `.sqlite3` của runtime vào
   `<install-root>/backups/before-<target-version>/`; `backup.json` ghi inventory
   hash/size.
9. Nếu có `current.json`, sao nó vào `previous.json` atomically. Sau đó ghi
   `current.json` atomically, gồm version, entrypoint và manifest SHA-256.

Nếu lỗi trước activation, staging/version mới được dọn và `current.json` cũ vẫn
giữ nguyên. Launcher chỉ resolve version từ `current.json` khi hash manifest
khớp; do đó app bị sửa/xóa sẽ không được chạy.

### 8.3 Rollback

`rollback_activation` không tải hay hạ `latest.json`. Nó kiểm tra `previous.json`
và đủ executable của version cũ, rồi swap atomically `current.json`/`previous.json`.

Khi bản pilot lỗi: dừng pilot, giữ dữ liệu người dùng và dùng rollback launcher.
Để sửa bản đã phát hành, tạo version cao hơn; không phát hành catalog downgrade để
ép máy người dùng hạ version.

## 9. Checklist hoàn tất một bản update

- [ ] Đã đọc `docs/handover/release_update_playbook.md` trước khi build/publish.
- [ ] Catalog LAN hiện tại hợp lệ; version mới là patch kế tiếp hợp lệ.
- [ ] `release.json`, `.iss` và release note cùng version.
- [ ] Test bắt buộc đạt; portable và launcher health-check đạt.
- [ ] Setup local được biên dịch, kiểm hash/size và publish bằng `.part` vào
      thư mục phần mềm LAN.
- [ ] `.mpupdate` local được tạo từ dist đã kiểm và publish bằng `.part` vào
      `release_update`; `latest.json` được ghi sau cùng.
- [ ] Setup, package và catalog trên LAN đã được đọc lại; version/name/size/hash
      khớp artifact local; không còn `.part` ở hai folder.
- [ ] Pilot từ version thấp hơn cập nhật qua GUI: kiểm notes, version, data,
      backup `before-<version>` và rollback path.
- [ ] `docs/handover/releases/<version>.md` ghi lệnh test, kết quả health-check,
      commit nguồn (nếu có), artifact hash/size, đường dẫn LAN, thời điểm và
      trạng thái pilot.

## 10. Các lỗi không được bỏ qua

| Tình huống | Xử lý đúng |
|---|---|
| Không đọc được `latest.json` | Dừng trước build/publish; không đoán version. |
| Version local và `.iss` khác nhau | Sửa cho khớp rồi chạy lại preflight. |
| File target cùng tên/version có hash khác | Dừng; không overwrite, rename tùy ý hay xóa lịch sử. |
| LAN không ghi được hoặc probe lỗi | Dừng trước publish. |
| Test/health-check lỗi | Dừng; không đưa artifact dở lên LAN. |
| Còn `.part` | Điều tra và dọn đúng file dở theo quy trình; không ghi `latest.json` mới. |
| Pilot lỗi sau activation | Roll back local pointer, giữ data, phát hành bản sửa version cao hơn. |

## 11. Lệnh kiểm tra nhanh sau đóng gói

```powershell
# Portable health-check
& ".\dist\MP2027_Portable\MP2027_Portable.exe" --health-check

# Launcher health-check trên bundle local
& ".\release_artifacts\install_bundle\MP2027_Launcher.exe" --health-check

# Hash và kích thước artifact local
Get-FileHash ".\release_artifacts\MP2027_Manager_Setup_<version>.exe" -Algorithm SHA256
Get-FileHash ".\release_artifacts\MP2027_Manager-<version>.mpupdate" -Algorithm SHA256
Get-Item ".\release_artifacts\MP2027_Manager_Setup_<version>.exe", ".\release_artifacts\MP2027_Manager-<version>.mpupdate" |
  Select-Object Name, Length
```

Tài liệu này là hướng dẫn quy trình. Với mọi lần phát hành thực tế, playbook
`docs/handover/release_update_playbook.md` vẫn là tài liệu kiểm soát bắt buộc.
