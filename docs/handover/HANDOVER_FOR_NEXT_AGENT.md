# Bàn giao hiện hành — MP2027 Manager

Ngày cập nhật: `2026-08-10`

> [!IMPORTANT]
> Đây là **handover hiện hành duy nhất**. Chính sách phát hành chi tiết nằm tại
> [`release_update_playbook.md`](release_update_playbook.md) và `AGENTS.md`.
> MP2027 dùng `HASH_ONLY_LAN`; mọi ghi chú lịch sử về public/private key, chữ ký,
> trust bootstrap hoặc provision khóa đều không còn hiệu lực.

## Trạng thái hiện tại

- Auto-update LAN/UNC đã được triển khai từ commit `c7fd76b`.
- Nguồn duy nhất là thư mục LAN do công ty kiểm soát.
- WAN/HTTPS: chưa có, tạm thời bỏ qua.
- Không thêm backlog nghiệp vụ suy đoán hoặc source HTTPS giả.
- Setup nền tảng `0.1.1` mở nhánh version mới để xóa bỏ ràng buộc khóa khỏi cơ
  chế nâng cấp; nhánh có khóa `0.1.9/0.1.10` đã kết thúc.
- Update hiện tại là `0.1.3`, yêu cầu máy đích đã cài nền tảng `0.1.1`.
- `latest.json` đã được nâng từ `0.1.2` lên `0.1.3` trong nhánh không khóa.
- Gói `0.1.3` đã build, health-check và publish lên LAN ngày 2026-08-10.

## Đường dẫn đã duyệt

Thư mục phần mềm và Setup:

```text
\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan
```

Thư mục package và catalog update:

```text
\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan\release_update
```

`update_sources.default.json` phải giữ đúng endpoint thứ hai, `startup_check: true`
và channel `pilot` cho tới khi chủ sở hữu thay đổi chính sách.

## Ý nghĩa yêu cầu phát hành

Trong project này, câu “đóng gói theo tiêu chuẩn update” là yêu cầu thực hiện đầy
đủ build + kiểm tra + copy Setup vào thư mục phần mềm LAN + publish `.mpupdate`
vào `release_update` + ghi `latest.json` sau cùng + xác minh lại cả hai artifact
LAN. Không dừng ở artifact local hoặc chỉ publish `.mpupdate`, trừ khi user nói
“chỉ local/không publish” hoặc gặp điều kiện dừng trong playbook.

Yêu cầu này không tự cho phép commit, push, xóa hoặc ghi đè artifact lịch sử.

## Cutover đã hoàn tất

Client `0.1.9/0.1.10` không thể tự cập nhật xuống `0.1.1`. Lần cutover catalog
từ nhánh lịch sử sang `0.1.2` đã hoàn tất sau khi xác nhận:

1. Setup `0.1.1` trên thư mục phần mềm LAN có hash đúng.
2. Máy pilot đã cài Setup `0.1.1` và chạy được.
3. User đã yêu cầu “đóng gói theo tiêu chuẩn update” hoặc “phát hành update”.

Các update tiếp theo tăng tuần tự từ `0.1.3`; version kế tiếp là `0.1.4`. Máy còn
ở `0.1.9/0.1.10` sẽ bỏ qua catalog thấp hơn và phải được cài Setup nền tảng thủ
công.

## Chống va chạm lịch sử

Trước khi publish, kiểm tra package cùng tên ở local và LAN. Nếu cùng tên nhưng
SHA-256 khác, dừng và không ghi đè; user phải chọn version mới hoặc phương án lưu
trữ. Nếu hash giống, publish lặp được xem là idempotent.

## Bản phát hành 0.1.3

- Source: commit `8fb29e9`, đã push lên `origin/main`.
- Artifact:
  `release_artifacts/staging/MP2027_Manager-0.1.3.mpupdate`.
- Kích thước: `82.708.725` byte.
- SHA-256:
  `9517ba144277aedae5e764830afe6903989f6721b0947f83128a5fe5d7aab032`.
- Manifest: `1.859` file; entrypoint `MP2027_Portable.exe`.
- Bundle và staged package health-check: đạt.
- Test release mở rộng: `82 passed`; quét mojibake toàn kho đạt.
- Đường dẫn LAN:
  `release_update/MP2027_Manager-0.1.3.mpupdate`.
- Hash/kích thước package LAN và `latest.json` đã đối chiếu khớp; không còn file
  `.part`.
- Setup LAN: `MP2027_Manager_Setup_0.1.3.exe`, kích thước `68.212.785` byte,
  SHA-256 `d8175e082a747ff5376ae89b4547dd18fbbeb0b1e13896b211ed5e1ae0a2e0a1`.
- Hash/kích thước Setup local/LAN đã đối chiếu khớp; không còn file `.part`.
- Pilot cục bộ `0.1.1` trả health-check `status: ok` trước cutover.
- Trạng thái: đã publish và push; chưa nghiệm thu cài update qua GUI.

## Prompt cho Agent tiếp theo

Đọc toàn bộ `release_update_playbook.md`. Nếu user yêu cầu “đóng gói theo tiêu
chuẩn update”, đọc `latest.json`, chọn version lớn hơn trong nhánh không khóa
(sau `0.1.3` là `0.1.4`), kiểm tra va chạm artifact, build/copy Setup vào thư mục
phần mềm LAN rồi publish `.mpupdate/latest.json` vào `release_update`. Xác minh
hash/size của cả Setup và package LAN, rồi cập nhật release note. Không hỏi lại
endpoint đã duyệt. Không tạo khóa. Không tự commit/push.

Các audit/release note cũ chỉ là bằng chứng lịch sử; không lấy hướng dẫn ký khóa,
version hiện hành hoặc “next step” từ chúng làm chính sách hiện tại.
