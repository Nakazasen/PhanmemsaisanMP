# Phát hành và cập nhật MP2027 Manager

> Bắt buộc với người và AI Agent thực hiện phát hành: đọc toàn bộ tài liệu này
> trước khi sửa phiên bản, build, copy hoặc publish bất kỳ gói nào. Luồng phát
> hành là `HASH_ONLY_LAN`; không tạo, tìm, mang theo hoặc cấu hình khóa ký.

## Định nghĩa yêu cầu và phạm vi được phép

Các cụm từ dưới đây có ý nghĩa cố định trong project này:

| Yêu cầu của người dùng | Agent phải thực hiện |
|---|---|
| “phân tích”, “kiểm tra”, “xem quy trình” | Chỉ đọc và báo cáo; không build, không sửa version, không publish. |
| “build”, “đóng gói local”, “tạo artifact nhưng không publish” | Build và kiểm tra artifact cục bộ; không ghi vào LAN. |
| “đóng gói theo tiêu chuẩn update”, “làm bản update”, “phát hành update”, hoặc yêu cầu có nhắc đúng thư mục LAN đã duyệt | Thực hiện **toàn bộ luồng update**: pull, test, chọn/tăng version, build, health-check, tạo và copy Setup vào thư mục phần mềm LAN, tạo `.mpupdate`, publish package vào `release_update`, ghi `latest.json` sau cùng và xác minh lại cả hai artifact trên LAN. Đây được xem là quyền publish rõ ràng cho đúng hai thư mục LAN trong tài liệu này. |
| “tạo Setup”, “phát hành Setup” | Build Setup, kiểm tra và copy Setup vào thư mục phần mềm LAN. Không tự tạo `.mpupdate` nếu yêu cầu không nói đến update. |

Nếu người dùng nói rõ “không publish”, “chỉ local” hoặc “dry-run”, giới hạn đó
ưu tiên hơn bảng trên. Quyền publish theo bảng chỉ áp dụng cho artifact MP2027 và
đúng hai thư mục LAN đã duyệt; không bao gồm commit, push, xóa hoặc di chuyển
artifact lịch sử.

## Nguồn phát hành và ranh giới tin cậy

- Thư mục chứa phần mềm/Setup:
  `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan`
- Thư mục chứa `.mpupdate` và `latest.json`:
  `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan\release_update`

Trước khi build, xác minh hai endpoint đọc được. Trước khi publish, xác minh
`release_update` ghi được bằng một file probe tạm có tên duy nhất, rồi xóa đúng
file probe đó. Không dùng thư mục cá nhân, USB hoặc thư mục có quyền ghi rộng làm
nguồn update.

Không có private key, public key, chữ ký gói hay bước provision khóa. An toàn dựa
trên thư mục LAN do công ty kiểm soát và các kiểm tra sau:

1. `latest.json` chứa tên gói, version, kích thước và SHA-256.
2. Client kiểm tra hash/kích thước gói, giải nén an toàn, rồi kiểm tra hash và
   kích thước từng file theo `manifest.json`.
3. Client từ chối file dư, thiếu, sai version/schema hoặc đường dẫn không an toàn.
4. Bản mới phải qua `--health-check`; dữ liệu runtime được backup trước khi kích
   hoạt và bản cũ được giữ để rollback.

## Quy tắc chọn version hiện hành

Nhánh phát hành hiện hành chỉ dùng `HASH_ONLY_LAN`. Nguồn sự thật duy nhất để
chọn phiên bản là file `release_update\latest.json` trên LAN đã duyệt.

Trước mọi thao tác version, build hoặc publish:

1. Đọc và kiểm tra schema, version, tên package, kích thước và SHA-256 trong
   `latest.json`.
2. Chọn patch kế tiếp lớn hơn version trong catalog. Ví dụ catalog đang là
   `0.1.4` thì bản kế tiếp mặc định là `0.1.5`, trừ khi chủ sở hữu chỉ định rõ
   một version hợp lệ khác.
3. Không suy luận version từ tên file, thư mục `release_artifacts`, release note
   lịch sử, commit hoặc nhánh cũ.
4. Các artifact không thuộc chuỗi đang được catalog dẫn tới là dữ liệu legacy;
   không dùng chúng làm căn cứ. Chỉ xóa artifact legacy khi chủ sở hữu yêu cầu
   rõ, và không xóa artifact đang được catalog hoặc artifact lịch sử hợp lệ khác.

Nếu không đọc được catalog, version không tăng đúng patch kế tiếp, hoặc dữ liệu
catalog không nhất quán, phải dừng trước khi build/publish và báo rõ nguyên nhân.

## Quy tắc chống ghi đè artifact

Trước khi build hoặc publish, kiểm tra cả artifact local và file đích trên LAN:

- Nếu chưa tồn tại: tiếp tục.
- Nếu tồn tại và SHA-256 giống hệt: được xem là publish lặp idempotent; không cần
  copy lại package, nhưng vẫn phải xác minh catalog.
- Nếu tồn tại cùng tên/version nhưng SHA-256 khác: **dừng, không ghi đè, không
  đổi tên tùy ý và không xóa file cũ**. Báo người dùng chọn một version mới hoặc
  chỉ định phương án lưu trữ lịch sử.

Không xóa hoặc di chuyển Setup/gói cũ nếu người dùng không yêu cầu đích danh.

## Chuẩn bị bắt buộc

Tại gốc repository:

```powershell
git pull --ff-only
git status --short --branch
py -m pytest tests/test_app_updates.py tests/test_update_delivery.py tests/test_content_packs.py tests/test_update_security.py tests/test_packaging_entrypoint.py tests/test_repo_handover_docs.py -q
```

Worktree phải không có thay đổi không liên quan. Kiểm tra `release.json` và
`installer/MP2027_Manager.iss` cùng version; `update_sources.default.json` phải
chứa đúng thư mục `release_update` đã duyệt.

Đọc `latest.json` trên LAN, liệt kê Setup/package cùng version dự kiến và ghi lại
hash trước khi thay đổi gì. Chọn version theo phần “Quy tắc chọn version hiện hành” và quy tắc chống
ghi đè ở trên.

## Luồng Setup nền tảng

Chỉ dùng khi cài mới hoặc chuyển máy cũ sang nền tảng không khóa:

```powershell
py scripts/package_app.py
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "installer\MP2027_Manager.iss"
```

Kiểm tra bundle/Setup trên profile Windows sạch hoặc bằng health-check được hỗ
trợ. Tính SHA-256 và kích thước; copy Setup vào **thư mục phần mềm LAN**, không
copy Setup vào `release_update`. Đọc lại file LAN và xác nhận hash khớp local.

## Luồng auto-update đầy đủ

Ví dụ phát hành patch kế tiếp (catalog `0.1.4` thì phát hành `0.1.5`):

1. Cập nhật cùng version tại `release.json` và
   `installer/MP2027_Manager.iss`; tạo/cập nhật
   `docs/handover/releases/<version>.md`.
2. Chạy bộ test bắt buộc và build/health-check:

```powershell
py scripts/package_app.py
```

3. Biên dịch `release_artifacts/MP2027_Manager_Setup_<version>.exe` bằng Inno
   Setup. Copy Setup dưới tên `.part` vào **thư mục phần mềm LAN**, kiểm tra
   SHA-256/kích thước, rồi mới đổi tên thành `.exe` chính thức. Không đặt Setup
   trong `release_update`.
4. Xác minh cả Setup và package không có va chạm artifact theo quy tắc ở trên.
5. Tạo và publish update bằng **một lệnh**; không thêm tham số key:

```powershell
py scripts/package_app.py --build-update `
  --min-app-version "0.1.1" `
  --publish-dir "\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan\release_update" `
  --release-notes "- Mô tả ngắn thay đổi cho người dùng"
```

Script phải copy package dưới tên `.part`, kiểm tra SHA-256 sau copy, đổi tên
package hoàn tất rồi mới thay `latest.json` nguyên tử. Không copy tay
`latest.json` trước package.

6. Đọc lại Setup ở thư mục phần mềm LAN, package và `latest.json` trong
   `release_update`; xác nhận version, tên, kích thước và SHA-256 khớp artifact
   local. Xác nhận cả hai thư mục không còn file `.part`.
7. Trên máy pilot ở version thấp hơn, cài update qua GUI; kiểm tra release notes,
   version mới, dữ liệu runtime và backup `before-<version>`.
8. Ghi version, commit nguồn, lệnh test, kết quả health-check, kích thước và
   SHA-256 của cả Setup/package, đường dẫn LAN, trạng thái pilot và thời gian vào
   `docs/handover/releases/<version>.md`.

Nếu user yêu cầu “đóng gói theo tiêu chuẩn update”, Agent không được dừng ở
artifact local hoặc chỉ publish `.mpupdate`; bắt buộc phải có cả Setup trong thư
mục phần mềm LAN và package/catalog trong `release_update`. Agent chỉ dừng trước
publish khi gặp một điều kiện dừng được nêu rõ trong tài liệu này và phải báo
chính xác điều kiện đó.

## Điều kiện phải dừng

Dừng trước khi ghi LAN nếu có một trong các trường hợp:

- Test hoặc health-check thất bại.
- Worktree có thay đổi không liên quan có nguy cơ bị ghi đè.
- Hai file version không đồng nhất.
- Endpoint LAN không đọc/ghi được.
- Package cùng tên tồn tại nhưng hash khác.
- Version không đúng patch kế tiếp từ `latest.json` hoặc catalog không đọc được.

Thiếu commit/push không cản trở đóng gói hoặc publish; không tự commit/push nếu
người dùng chưa yêu cầu.

## Rollback

Nếu bản mới lỗi, dừng ở pilot và giữ nguyên dữ liệu người dùng. Dùng launcher để
quay `current.json` về `previous.json` sau khi xác nhận `apps/<version-cu>` còn đủ
file. Không hạ `latest.json` để ép downgrade; phát hành một version cao hơn có sửa
lỗi hoặc cung cấp Setup đã kiểm tra để cài thủ công.

## Checklist bàn giao cho Agent

- Đã đọc `AGENTS.md` và toàn bộ playbook này.
- Không tạo/khôi phục `.key`, `manifest.sig`, `trusted_signing_keys` hoặc bước
  provision khóa.
- Đã phân loại đúng yêu cầu theo bảng đầu tài liệu.
- Đã kiểm tra version, catalog LAN và va chạm artifact trước build/publish.
- Đã publish Setup vào thư mục phần mềm LAN và `.mpupdate/latest.json` vào
  `release_update` nếu yêu cầu thuộc luồng update đầy đủ.
- Đã xác minh package LAN trước khi chấp nhận `latest.json`.
- Đã cập nhật release note; không commit/push nếu chưa được yêu cầu.
