# Bàn giao hiện hành — MP2027 Manager

Ngày chốt lại: `2026-08-07`

> [!IMPORTANT]
> Chính sách hiện hành thay thế mọi ghi chú cũ về public/private key, chữ ký hoặc trust bootstrap trong tài liệu này: đọc `release_update_playbook.md` và `AGENTS.md`. MP2027 dùng `HASH_ONLY_LAN`; không tạo hay yêu cầu khóa để phát hành/cập nhật.

Đây là **handover hiện hành duy nhất**. Các audit cũ chỉ là bằng chứng lịch sử;
không lấy phần “next step”, “open item” hoặc “recommended phase” trong audit cũ
làm công việc hiện hành.

## Mục tiêu đang thực hiện

Đóng gói MP2027 Manager với cơ chế tự phát hiện cập nhật qua thư mục LAN/UNC
của công ty. WAN chưa có và tạm thời không thuộc phạm vi bản đóng gói này.

Code Auto-update đã được triển khai ở commit `c7fd76b` (`feat: add LAN and
HTTPS update delivery`). Luồng LAN/WAN không còn chờ phát triển. Nguồn LAN thật
đã được người dùng cung cấp và ghi vào cấu hình mặc định; bước tiếp theo là kiểm
tra cấu hình, chuẩn bị trust bootstrap và build bộ cài pilot.

## Phần đã được xác minh

- Ứng dụng đọc `update_sources.default.json` được bundle trong `_internal`.
- Có thể dò nền khi khởi động từ nguồn `folder` hoặc `https`.
- GUI chỉ hỏi **Cập nhật ngay / Để sau**; không tự cài im lặng.
- Gói tải/copy về vẫn phải qua xác minh chữ ký Ed25519, manifest, hash, schema,
  phiên bản và health-check trước khi kích hoạt.
- Publisher ghi package trước và `latest.json` sau cùng để client không thấy
  bản phát hành chưa hoàn chỉnh.
- Bản `0.1.2` hiển thị phiên bản trong tiêu đề và phần đầu giao diện. Bản `0.1.3`
  nâng giới hạn manifest dùng chung cho dò nền, kiểm tra gói và đóng gói lên 1 MiB.
  Builder từ chối gói vượt giới hạn trước khi phát hành. Client `0.1.1` vẫn dùng
  giới hạn cũ 256 KiB nên không thể tự dò các gói hiện có có manifest 261,83 KiB;
  cần cài thủ công `0.1.3` đúng một lần để làm cầu nối.
- Bản `0.1.4` thêm người phụ trách vào title và dùng `latest.json` của LAN để popup
  tự cập nhật hiển thị nội dung phát hành, đồng thời đối chiếu version, hash và
  dung lượng của gói trước khi đề nghị cài.
- Bản `0.1.5` đặt nhật ký xử lý cố định ở đáy cửa sổ, cho phần biểu mẫu cuộn được
  trên màn hình thấp, và tự bật lại duy nhất mẫu manifest cũ đã nhận loại nguồn
  nhưng vô tình lưu cờ TẮT. Các file người dùng chủ động **Bỏ qua** vẫn không đổi.
- Bản `0.1.6` khôi phục công thức tài sản cố định; chỉ sinh khám sức khỏe ở tháng
  sau khi headcount tăng; tính du lịch tháng 5 theo tổng headcount tháng 5 và bánh
  Trung Thu tháng 9 theo tổng headcount tháng 9. Gói cập nhật và Setup đều đã được
  publish lên LAN.
- Bộ test nghiệp vụ Excel, update/packaging và handover đạt `189 passed, 3 subtests
  passed` trước khi tạo pilot `0.1.6`:

```powershell
py -m pytest tests/test_update_delivery.py tests/test_app_updates.py `
  tests/test_content_packs.py tests/test_update_security.py `
  tests/test_packaging_entrypoint.py tests/test_repo_handover_docs.py -q
```

## Cấu hình đã được người dùng chốt

- Nguồn duy nhất: LAN/UNC.
- Đường dẫn:

```text
\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan\release_update
```

- `startup_check: true`.
- Channel hiện giữ `pilot` để đóng gói và diễn tập trước.
- WAN/HTTPS: chưa có, tạm thời bỏ qua; không thêm source HTTPS giả hoặc placeholder.

Không đặt username, password, token hoặc khóa riêng trong đường dẫn, repository
hoặc bộ cài.

## Prompt thực hiện cho agent tiếp theo

> Dùng nguồn LAN đã được chốt trong `update_sources.default.json`; không hỏi lại
> endpoint và không thêm WAN. Với client `0.1.5`, mở lại app để xác nhận tự phát
> hiện `0.1.6`, hiển thị đúng nội dung phát hành và hỏi **Cập nhật ngay**.
> Xác nhận app/launcher chạy version mới, dữ liệu runtime còn nguyên, rồi diễn tập
> rollback về N-1. Ghi lại version, hash, thời gian và
> kết quả. Không tuyên bố production-ready nếu chưa có clean-Windows smoke,
> rollback evidence và Authenticode.

## Trình tự thực hiện

1. Với máy cài mới, chạy `MP2027_Manager_Setup_0.1.6.exe` từ thư mục LAN.
2. Xác nhận app cài có public key `mp2027-prod-2026` và nguồn LAN trong
   `_internal`.
3. Trên client `0.1.5`, đóng hẳn app rồi mở qua launcher; xác nhận popup `0.1.6`,
   nội dung phát hành và cập nhật thành công.
4. Xác nhận dữ liệu runtime còn nguyên và rollback `0.1.6` → `0.1.5` thành công.
5. Lưu evidence; chỉ ký Authenticode khi certificate phát hành được cung cấp.

## Artifact pilot đã tạo

| Artifact | Version | SHA-256 |
|---|---:|---|
| `release_artifacts/MP2027_Manager_Setup_0.1.0.exe` | bootstrap | `a6101229f76d524f28599b89eb70ea209c36f71bd621ab021d6f61efe9c40c64` |
| `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan\release_update\MP2027_Manager-0.1.1.mpupdate` | pilot trước đó | `66a699cdf765d5602224b3cb6444bf90bd69dd66418b45803447a80ca0ab35b9` |
| `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan\release_update\MP2027_Manager-0.1.2.mpupdate` | pilot trước đó | `0c35cf19fc6ebaaac3667820cbbc0640941c03a54f306c3bba2b265d384a4c1a` |
| `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan\release_update\MP2027_Manager-0.1.3.mpupdate` | pilot trước đó | `91a45ff0c526d71ba25e56897a5ff9e83a25b753a87edff3e2723d76f3b40dee` |
| `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan\release_update\MP2027_Manager-0.1.4.mpupdate` | pilot trước đó | `f1e010f8c07afd2a4f3ff3a3cf2e33e665a1ec15a18ff898d7a8c9ef0dd4c019` |
| `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan\release_update\MP2027_Manager-0.1.5.mpupdate` | pilot trước đó | `fa2780c9a24538d95a0f265bd88c2b1c11a98e7d301a0f3a4c2bc17bf1adea6d` |
| `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan\release_update\MP2027_Manager-0.1.6.mpupdate` | pilot N hiện hành | `d0315d38648ab4bec9fbd484a57620f661d23fef21a6ec1ca921077f14302f88` |
| `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan\release_update\MP2027_Manager_Setup_0.1.6.exe` | Setup hiện hành | `555d9687dd8351a6ad978b194f7c4f1ad30ab1b179ac22890f2fe2a700ae61a0` |
| Cùng thư mục LAN: `latest.json` | catalog | trỏ tới đúng hash/size/ghi chú của `0.1.6` |

Chi tiết lệnh và hợp đồng artifact nằm trong
[`release_update_playbook.md`](release_update_playbook.md). Các profile test nằm
trong [`test_strategy_and_profiles.md`](test_strategy_and_profiles.md).

## Những điều chưa được tuyên bố

- Nguồn LAN đã được cấu hình, các gói pilot `0.1.1` đến `0.1.6` đã được ký/publish.
  Setup `0.1.6` đã được build và copy lên LAN. `latest.json` hiện trỏ tới `0.1.6`;
  manifest nằm dưới giới hạn dùng chung 1 MiB,
  dưới giới hạn dùng chung 1 MiB. Client `0.1.1`
  không tự dò được gói này vì giới hạn cũ 256 KiB, nhưng vẫn có thể cài thủ công vì
  kiểm tra gói của nó cho phép 512 KiB. Chữ ký, manifest, min version và hash đã
  được kiểm tra trực tiếp.
- Chưa có WAN/HTTPS; đây là chủ ý của đợt pilot, không phải lỗi còn mở.
- `release.json` có public key `mp2027-prod-2026`; private key nằm ngoài repo.
- Chưa nghiệm thu update/rollback qua GUI trên Windows sạch/pilot thật.
- Setup chưa được ký Authenticode.
- Full suite trên HEAD đạt `620 passed, 2 skipped, 6 subtests passed`; 35 test còn
  lại không chạy được vì thiếu các workbook mẫu tiếng Nhật dưới `raw/`. Ba test
  nghiệp vụ cũ mâu thuẫn với quyết định headcount tháng đã được cập nhật và chạy lại.

## Quy tắc bàn giao

- Không thêm backlog nghiệp vụ suy đoán vào file này.
- Không sao chép “open items” từ audit lịch sử.
- Chỉ ghi trạng thái có thể tái kiểm tra bằng code, config, test hoặc artifact.
- Khi nguồn update thay đổi, cập nhật handover này ngay trong cùng thay đổi với
  config/build evidence.
