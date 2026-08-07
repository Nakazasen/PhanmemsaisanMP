# Phát hành và cập nhật MP2027 Manager

> Bắt buộc với người và AI Agent thực hiện phát hành: đọc toàn bộ tài liệu này trước khi sửa phiên bản, build, copy hoặc publish bất kỳ gói nào. Không tạo, tìm, mang theo hoặc cấu hình khóa ký. Luồng phát hành là `HASH_ONLY_LAN`.

## Phạm vi và ranh giới tin cậy

MP2027 Manager cập nhật từ thư mục LAN được công ty kiểm soát:

- Thư mục chứa phần mềm/Setup: `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan`
- Thư mục chứa gói tự cập nhật: `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan\release_update`

Xác minh endpoint LAN đã cấu hình có thể đọc trước khi phát hành; chỉ kiểm tra quyền ghi khi người phát hành đã được phép publish.

Không có private key, public key, chữ ký gói hay bước provision khóa. Tính an toàn còn lại là:

1. `latest.json` chứa tên gói, phiên bản, kích thước và SHA-256.
2. Client kiểm tra hash/kích thước sau khi tải; giải nén an toàn; kiểm tra hash/kích thước từng file theo `manifest.json`; từ chối file dư, thiếu hoặc sai phiên bản/schema.
3. Bản mới phải qua `--health-check` trước khi trỏ launcher sang bản đó. Dữ liệu runtime được sao lưu trước khi kích hoạt và bản cũ vẫn giữ để rollback.

SHA-256 phát hiện lỗi copy, file dở dang và hỏng dữ liệu, nhưng không chứng minh người tạo gói. Vì vậy chỉ nhóm phát hành được quyền ghi vào hai thư mục LAN trên; người dùng thông thường chỉ có quyền đọc. Không dùng thư mục cá nhân, USB hoặc thư mục có quyền ghi rộng làm nguồn update.

## Trạng thái nền tảng: 0.1.1

Phiên bản mã nguồn và Setup nền tảng hiện là `0.1.1`. Đây là mốc đổi sang luồng không khóa.

Client đang ở `0.1.9` hoặc `0.1.10` không thể tự cập nhật “lùi” về `0.1.1`, vì client luôn chỉ nhận phiên bản mới hơn. Cần cài thủ công Setup `0.1.1` một lần từ thư mục phần mềm. Sau đó, mọi auto-update mới phải tăng dần: `0.1.2`, `0.1.3`, … Không publish `latest.json` trỏ về phiên bản thấp hơn bản đã cài.

## Chuẩn bị môi trường phát hành

Tại gốc repository:

```powershell
git pull --ff-only
py -m pytest tests/test_app_updates.py tests/test_update_delivery.py tests/test_content_packs.py tests/test_update_security.py tests/test_packaging_entrypoint.py -q
```

Nếu có thay đổi không liên quan trong worktree, dừng lại và không ghi đè chúng. Kiểm tra `release.json`, `installer/MP2027_Manager.iss` và `update_sources.default.json` có cùng phiên bản/đường dẫn mong muốn.

## Phát hành Setup nền tảng 0.1.1

Chỉ dùng khi cài mới hoặc chuyển các máy cũ sang nền tảng không khóa.

1. Xác nhận `release.json` và `installer/MP2027_Manager.iss` cùng là `0.1.1`.
2. Build bundle và kiểm tra sức khỏe:

```powershell
py scripts/package_app.py
```

3. Biên dịch Inno Setup:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "installer\MP2027_Manager.iss"
```

4. Chạy `release_artifacts\MP2027_Manager_Setup_0.1.1.exe --health-check` nếu có hỗ trợ, hoặc cài thử trên profile Windows sạch. Sau đó copy Setup đã kiểm tra tới thư mục phần mềm LAN bằng thao tác được phép của người phát hành.

Không xóa bản Setup cũ hoặc gói update cũ chỉ để dọn thư mục; giữ chúng cho rollback/truy vết, trừ khi chủ sở hữu dữ liệu yêu cầu rõ ràng.

## Phát hành một auto-update mới

Ví dụ phát hành `0.1.2` từ nền tảng `0.1.1`:

1. Tăng **cùng một số phiên bản** tại `release.json` và `installer/MP2027_Manager.iss`.
2. Cập nhật ghi chú phát hành và chạy test phù hợp.
3. Build onedir và bundle:

```powershell
py scripts/package_app.py
```

4. Tạo gói và publish. Không thêm tham số key nào:

```powershell
py scripts/package_app.py --build-update `
  --min-app-version "0.1.1" `
  --publish-dir "\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan\release_update" `
  --release-notes "- Mô tả ngắn thay đổi cho người dùng"
```

Lệnh sẽ tạo `.mpupdate`, copy trước dưới tên `.part`, kiểm tra SHA-256 sau copy, đổi tên gói hoàn tất, rồi ghi `latest.json` **sau cùng**. Không tự copy tay `latest.json` trước gói.

5. Trên một máy pilot đang ở phiên bản thấp hơn, nhấn **Cài bản cập nhật...**; kiểm tra hiển thị ghi chú, phiên bản mới khởi động được, dữ liệu vẫn có, và có thư mục backup `before-<version>`.
6. Lưu SHA-256, kết quả test và ghi chú vào `docs/handover/releases/<version>.md`. Chỉ sau pilot thành công mới thông báo rộng.

## Rollback

Nếu bản mới không sử dụng được, không thay dữ liệu của người dùng.

1. Dừng tại máy pilot và lưu lỗi.
2. Dùng chức năng rollback/launcher để quay `current.json` về `previous.json` sau khi xác nhận thư mục `apps/<version-cu>` còn đủ file.
3. Không trỏ `latest.json` về một phiên bản thấp hơn để ép downgrade tự động. Nếu cần rollback hàng loạt, phát hành một phiên bản **mới hơn** có sửa lỗi, hoặc cung cấp Setup đã kiểm tra để cài thủ công.

## Việc AI Agent phải làm lần sau

1. Đọc `AGENTS.md` ở gốc repo và tài liệu này.
2. Không khôi phục cơ chế ký, file `.key`, `manifest.sig`, `trusted_signing_keys` hoặc script provision khóa nếu không có yêu cầu bảo mật mới được chủ sở hữu xác nhận.
3. Không publish lên LAN, commit hoặc push khi người dùng chỉ yêu cầu phân tích/build; xin hoặc nhận quyền rõ ràng cho các hành động đó.
4. Giữ đúng hai đường dẫn LAN trong tài liệu và `update_sources.default.json`; nếu đường dẫn cần thay đổi, cập nhật cả hai trong cùng thay đổi và kiểm tra quyền đọc/ghi thực tế.
