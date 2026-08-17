# Bàn giao hiện hành — MP2027 Manager

Ngày cập nhật: `2026-08-12`

> [!IMPORTANT]
> Đây là **handover hiện hành duy nhất**. Chính sách phát hành chi tiết nằm tại
> [`release_update_playbook.md`](release_update_playbook.md) và `AGENTS.md`.
> MP2027 dùng `HASH_ONLY_LAN`; không tạo, tìm, khôi phục hoặc cấu hình khóa ký.

## Trạng thái hiện tại

- Auto-update LAN/UNC đã được triển khai từ commit `c7fd76b`.
- Nguồn duy nhất là thư mục LAN do công ty kiểm soát.
- WAN/HTTPS: chưa có, tạm thời bỏ qua.
- Không thêm backlog nghiệp vụ suy đoán hoặc source HTTPS giả.
- Catalog LAN hiện tại là `0.1.6`.
- Version kế tiếp mặc định là `0.1.7`, được chọn bằng cách đọc lại
  `release_update/latest.json`; không lấy version từ artifact hoặc tài liệu
  lịch sử.

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

## Quy tắc version

- `release_update/latest.json` trên LAN là nguồn sự thật duy nhất.
- Version mới mặc định là patch kế tiếp; catalog `0.1.4` dẫn tới mục tiêu `0.1.5`.
- Không dùng tên file, artifact local, release note cũ, commit hoặc nhánh cũ để
  suy ra version.
- Không đưa lại các artifact/tài liệu của nhánh cũ vào quy trình mới.
- Nếu catalog không đọc được, version không tăng đúng patch hoặc có va chạm hash,
  dừng trước publish và báo rõ.

## Bàn giao sau phát hành

Bản `0.1.6` đã build, health-check và publish thành công; bằng chứng đầy đủ nằm
trong [`releases/0.1.6.md`](releases/0.1.6.md). Lần phát hành kế tiếp phải đọc
lại `latest.json` trước khi chọn version.

Không commit/push nếu chưa được yêu cầu. Không tạo, tìm, khôi phục hoặc cấu hình khóa ký; không thêm chữ ký gói hoặc bước provision khóa.
