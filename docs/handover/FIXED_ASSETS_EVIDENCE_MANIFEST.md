# Fixed-assets — Portable evidence manifest

**Ngày lập:** 2026-07-16
**Mục đích:** bảo đảm máy khác clone repository có đủ corpus tối thiểu để tiếp tục deep audit fixed-assets mà không phụ thuộc ổ đĩa, artifact chat hoặc file chỉ tồn tại trên máy người lập handover.

> [!IMPORTANT]
> Mọi đường dẫn trong tài liệu này là tương đối từ **repository root**. Chạy kiểm tra trước khi đọc workbook hoặc kết luận evidence bị thiếu.

## 1. Lệnh bootstrap và kiểm tra

Từ repository root:

```powershell
py scripts/verify_fixed_assets_handover.py
py scripts/verify_fixed_assets_handover.py --extract-reference
```

- Lệnh đầu kiểm tra file bắt buộc, SHA-256, tính toàn vẹn ZIP và số workbook reference.
- Lệnh thứ hai đồng thời giải nén `reference_outputs/secondary/FY2027.zip` thành `reference_outputs/secondary/FY2027/`.
- Thư mục FY2027 sau giải nén là local bootstrap output và bị `.gitignore`; nguồn có thẩm quyền trong Git là file ZIP.

## 2. Corpus bắt buộc được Git track

| Vai trò | Repository path | SHA-256 / kiểm tra |
|---|---|---|
| Canonical requirement | `raw/Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx` | `426207927e42b19c113f26f9d63ec564a434b5758a43ac71ac52803badbae661` |
| Company fixed-assets source FY2026 | `docs/MP2026/固定資産情報_Fixed_Assets_Information_2024.12 - December.xlsx` | `cb5e01bc631002408b6756449b114bfd30bfea932648e2a28e7f500426e7b028` |
| Company fixed-assets source FY2027 | `docs/MP2027/固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx` | `5c82bca709499f69248cf5994a209514e8b5a9b9888ea684fadbaa12a54dbaa8` |
| Reference output FY2026 | `reference_outputs/secondary/FY2026/` | 64 workbook `.xlsx` được Git track trực tiếp |
| Reference output FY2027 | `reference_outputs/secondary/FY2027.zip` | `fb0f2f637395e8c45373041013685829889ddda30824457eee546c165024d12b`; ZIP hợp lệ, 82 workbook `.xlsx`, root `FY2027/` |
| Active handover | `docs/handover/FIXED_ASSETS_DEEP_AUDIT_HANDOVER_2026-07-16.md` | Bắt buộc đọc |
| Live backlog | `docs/handover/CURRENT_OPEN_ITEMS.md` | Bắt buộc đọc |
| Audit lifecycle | `docs/audits/AUDIT_STATUS_INDEX.md` | Bắt buộc đọc |

Current implementation, tests, requirement markdown, knowledge base và audit provenance đều là file source/text được Git track trong các path ghi tại active handover.

## 3. FORM và source-order context

Các file context đã được Git track và phải đọc khi trace output:

- `docs/MP2026/FORM.xlsx`
- `docs/MP2027/FORM.xlsx`
- `docs/MP2027/source_file_order.csv`
- `src/parsers/fixed_assets.py`
- `src/engine/hub_builder.py`
- `src/engine/complete_v1_source_order_writer.py`
- `src/engine/output_mode.py`
- `src/engine/account_resolver.py`
- `src/utils/source_manifest.py`
- `src/utils/fiscal_periods.py`
- `src/db/schema.py`
- `src/audit/fixed_assets_coverage.py`

Không cần toàn bộ workbook vận hành trong `docs/MP2026`/`docs/MP2027` để bắt đầu fixed-assets audit. Nếu quá trình cross-trace chứng minh cần thêm file ngoài corpus trên, ghi chính xác file/sheet/cell và cập nhật manifest thay vì dựa vào file local im lặng.

## 4. Authority và giới hạn sử dụng

1. Canonical workbook là authority nghiệp vụ cao nhất.
2. Hai company source workbook là evidence cho dữ liệu và calculation layer của từng FY.
3. Reference outputs là behavioral evidence; không tự override canonical khi có manual carry-over hoặc unexplained adjustment.
4. Source code/tests cho biết implementation hiện hành, không tự chứng minh business rule đúng.
5. Markdown/audit là derived evidence.

Không dùng checksum để kết luận nghiệp vụ; checksum chỉ chứng minh máy tiếp quản đang đọc đúng binary corpus đã được bàn giao.

## 5. Clone-readiness acceptance

Chỉ bắt đầu deep audit khi script trả exit code `0` và báo:

- 4 file binary bắt buộc khớp SHA-256;
- FY2026 có 64 workbook `.xlsx`;
- FY2027 ZIP không hỏng, có 82 workbook `.xlsx`, root `FY2027/`;
- nếu dùng `--extract-reference`, thư mục FY2027 đã có đủ 82 workbook `.xlsx`.

Nếu bất kỳ check nào fail:

- không thay bằng file gần giống theo tên;
- không sửa checksum để làm check xanh;
- ghi missing/corrupt path vào audit report;
- phục hồi đúng file từ Git/remote trước khi tiếp tục.
