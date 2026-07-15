# Fixed Assets — GAP Audit and Implementation Plan (2026-07-15)

Status: `HISTORICAL_PROVENANCE_SUPERSEDED_BY_EVIDENCE_DRIVEN_HANDOVER`

> [!WARNING]
> Snapshot này giữ nguyên finding lịch sử, nhưng workflow “hỏi Accounting/MP trước” và bảng `Chưa chốt` không còn là điểm bắt đầu hiện hành. Successor bắt buộc: `docs/handover/FIXED_ASSETS_DEEP_AUDIT_HANDOVER_2026-07-16.md`. Phải cross-trace canonical, source/calculation MP2026/MP2027 và reference outputs trước; chỉ escalation phần còn mâu thuẫn hoặc thiếu evidence.

## 1. Mục đích

Lưu lại ngoài lịch sử chat:

- quy tắc nghiệp vụ tài sản cố định;
- code hiện tại đang làm gì;
- những phần đã đúng;
- GAP còn lại;
- quyết định cần hỏi Accounting/MP;
- kế hoạch audit và sửa tiếp tại công ty.

## 2. Nguồn bằng chứng

### Yêu cầu canonical

- `raw/Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx`
- Sheet `Chi phí tài sản cố định`

Quy tắc chính trong sheet:

1. Lọc theo code phòng chịu chi phí.
2. Kiểm tra `Last Depreciation Month` có nằm trong FY hay không.
3. Nếu không nằm trong FY: khấu hao và lãi chạy cho toàn bộ FY.
4. Nếu nằm trong FY: tháng trước dùng số thường, tháng cuối dùng `Last Month Depr`, sau tháng cuối để trống.
5. Tháng 4 dùng lãi April; tháng 5 trở đi dùng lãi May onward.
6. Công thức VND dùng dạng `ROUND(USD * tỷ giá, 0)` và phải giữ công thức.

### Source fixed-assets

- `raw/固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx`
- Sheet hiện quan sát: `2025.11`
- Header row: 4; data bắt đầu từ row 5

Các cột quan trọng:

| Cột | Ý nghĩa |
|---|---|
| B | Category |
| C | Asset number |
| D | Asset text |
| H | Control Cost Center |
| J | Depreciation Cost Center / cost-bearing CC |
| L | Monthly depreciation USD |
| P | Last depreciation month |
| Q | Last-month depreciation USD |
| V | Interest in April USD |
| W | Interest from May onward USD |

### Kết quả thủ công của công ty

- `reference_outputs/secondary/FY2026`: 64 workbook
- `reference_outputs/secondary/FY2027`: 65 workbook
- Tổng dòng đã quét: 1,551; lỗi đọc: 0
- Tỷ giá quan sát: FY2026 `25,390`; FY2027 `26,273`

Các file thủ công là bằng chứng hành vi quan trọng, nhưng có cả `ROUND`, `ROUNDUP`, công thức liên kết, công thức cộng dồn và số nhập tay. Không được tự động coi mọi công thức thủ công là quy tắc chuẩn nếu chưa được Accounting xác nhận.

## 3. Code hiện tại

Các file chính:

- `src/parsers/fixed_assets.py`
- `src/engine/hub_builder.py`
- `src/engine/complete_v1_source_order_writer.py`
- `src/audit/fixed_assets_coverage.py`
- `scripts/run_e2e.py`
- `tests/test_src_v2_logic.py`
- `tests/test_fixed_assets_parser_coverage.py`
- `tests/test_complete_v1_source_order_writer.py`

Code hiện tại đã hỗ trợ:

- lọc theo Depreciation Cost Center;
- 5 nhóm tài sản chính: `5006016242`, `5006016243`, `5006016244`, `5006016247`, `5005036246`;
- lãi tài sản cố định `9114120007`;
- tháng 4 và tháng 5 trở đi dùng hai input lãi khác nhau;
- dừng khấu hao/lãi sau tháng cuối;
- dùng `Last Month Depr` khi có;
- xuất công thức gắn với `$B$2`;
- đặt block động trong complete-v1, bắt đầu từ row 30.

## 4. GAP register

| ID | Ưu tiên | GAP | Rủi ro |
|---|---|---|---|
| FA-G01 | P0 | Code đang cộng USD theo category rồi mới `ROUND` | Có thể khác cách làm tròn từng tài sản trong file thủ công |
| FA-G02 | P0 | Chưa kiểm soát chặt tỷ giá FY, DB và FORM `$B$2` | Có thể tính đúng công thức nhưng dùng sai rate |
| FA-G03 | P1 | Output nhìn thấy đang gom theo category, không phải từng tài sản | Khó truy vết asset number/text và đối chiếu từng dòng |
| FA-G04 | P1 | Không giữ công thức thủ công gốc | Không tái tạo được `ROUNDUP`, link dòng và điều chỉnh tay |
| FA-G05 | P1 | Chỉ hỗ trợ một số category | Category mới có thể bị bỏ qua hoặc làm import dừng |
| FA-G06 | P1 | Coverage audit mới kiểm tra có series, chưa kiểm tra đủ số tiền | Có thể không phát hiện thiếu asset/period |
| FA-G07 | P1 | Đọc source với `data_only=True` | Công thức chưa có cached value có thể thành blank/zero |
| FA-G08 | P2 | Thiếu `Last Month Depr` có thể fallback về monthly thường | Có thể che lỗi dữ liệu nguồn |
| FA-G09 | P2 | Lọc số dương có thể làm mất adjustment âm | Không phản ánh reversal/credit nếu công ty có dùng |
| FA-G10 | P2 | Alias header lãi có thể bind nhầm April/May | Sai cột input khi header tiếng Việt mơ hồ |
| FA-G11 | P2 | Import xóa toàn bộ fixed-assets facts trước khi nạp lại | Không giữ lịch sử nhiều FY trong cùng DB |
| FA-G12 | P2 | Python `round` có thể khác Excel `ROUND` tại .5 | Sai lệch nhỏ trong audit VND |
| FA-G13 | P3 | Vẫn có khái niệm row 38/42 làm staging | Tăng coupling, khó bảo trì dù output cuối đã dynamic |

## 5. Quyết định phải chốt tại công ty

> [!WARNING]
> Không được tự chọn các mục dưới đây chỉ để làm code chạy. Đây là quyết định ảnh hưởng trực tiếp đến số liệu kế toán.

| Nội dung | Các lựa chọn | Quyết định công ty |
|---|---|---|
| Mức chi tiết output | từng asset / từng category / hybrid | Chưa chốt |
| Điểm làm tròn | từng asset rồi cộng / cộng USD rồi làm tròn | Chưa chốt |
| Chính sách công thức | công thức canonical mới / tái tạo công thức thủ công | Chưa chốt |
| Tỷ giá FY2026 | xác nhận `25,390` hoặc rate được duyệt | Chưa chốt |
| Tỷ giá FY2027 | xác nhận `26,273` hoặc rate được duyệt | Chưa chốt |
| Adjustment âm | cho phép / không cho phép / review thủ công | Chưa chốt |
| Thiếu Last Month Depr | fail / fallback có warning / quy tắc khác | Chưa chốt |
| Phạm vi category | duyệt danh sách in-scope/out-of-scope | Chưa chốt |
| Lưu nhiều FY | DB một FY / lưu lịch sử nhiều FY | Chưa chốt |

## 6. Kế hoạch thực hiện theo thứ tự

### Phase A — Khóa baseline

1. Chạy parser và test hiện tại trước khi sửa.
2. Lưu source row, asset identity, CC, category, month, USD, VND, last month và trạng thái formula/cache.
3. Chọn tối thiểu 3 CC đại diện: có terminal month, nhiều category, có interest/manual adjustment.
4. Lưu evidence theo từng lần chạy; không commit DB, workbook private hay output runtime.

### Phase B — Chốt nghiệp vụ

1. Điền bảng quyết định ở mục 5 với người phụ trách Accounting/MP.
2. Lấy expected result theo asset và từng tháng cho 3 CC đại diện.
3. Xác định rõ khác biệt nào là do tỷ giá, chronology/carry-over, rounding hay manual adjustment.

### Phase C — Sửa parser/control

- Header phải unique; không bind mơ hồ April/May.
- Đọc cả formula và cached value; cảnh báo formula không có cache.
- Lập báo cáo category unknown/out-of-scope.
- Áp dụng chính sách Last Month Depr đã duyệt.
- Xử lý adjustment âm theo quyết định.
- Dùng rounding tương thích Excel cho persisted audit value.
- Chỉ xóa/import đúng phạm vi FY hoặc import key đã duyệt.

### Phase D — Sửa aggregation/output

- Implement đúng điểm rounding đã duyệt.
- Giữ asset-level provenance dù output vẫn summary.
- Kiểm tra rate trong FORM `$B$2` trước export.
- Giữ tháng sau terminal month là blank.
- Kiểm tra formula vẫn còn sau source-order relocation.

### Phase E — Nâng audit comparator

Comparator phải phân loại theo CC, asset, category, month và cost type:

- match USD/VND;
- FX-only;
- rounding-order difference;
- source/scope gap;
- chronology/carry-over;
- category/account mapping;
- missing formula cache;
- unresolved manual adjustment;
- true amount mismatch.

### Phase F — Acceptance

- targeted tests pass;
- E2E 3 CC đại diện pass;
- mở bằng Excel để formula tính thật;
- Accounting/MP ký expected result;
- mở rộng toàn bộ FY2026/FY2027;
- true mismatch bằng 0 hoặc được chấp thuận bằng văn bản.

## 7. Test tối thiểu

```powershell
$env:PYTHONIOENCODING='utf-8'
py -m pytest tests/test_src_v2_logic.py tests/test_fixed_assets_parser_coverage.py tests/test_complete_v1_source_order_writer.py
```

Cần có test cho:

- Control CC khác Depreciation CC;
- terminal month trước/trong/sau FY và blank;
- Last Month Depr;
- April/May interest;
- post-final blank;
- rounding từng asset so với rounding tổng;
- Excel half-up rounding;
- formula không có cache;
- duplicate header;
- unknown category;
- adjustment âm;
- rate khác giữa FY và FORM B2;
- dynamic placement, formula preservation, blank separator.

## 8. Tiêu chí hoàn tất

Chỉ đánh dấu complete khi:

- mọi category in-scope đã có mapping;
- không formula nào bị biến thành zero âm thầm vì thiếu cache;
- rate được duyệt khớp FORM B2;
- rounding policy được duyệt và test;
- terminal-month examples khớp expected;
- mọi asset parsed có source identity;
- mọi asset excluded có lý do;
- mọi CC cần xuất đều được export;
- 3 CC đại diện khớp kết quả công ty;
- toàn bộ mismatch được phân loại;
- công thức và layout bắt buộc vẫn được giữ.

## 9. Khi đến công ty: bắt tay lại như thế nào

1. Mở file này trước.
2. Chạy `git status -sb`, sau đó `git pull --ff-only origin main` nếu worktree sạch.
3. Kiểm tra workbook canonical, source và reference outputs có ở máy công ty.
4. Nhờ Accounting/MP điền mục 5.
5. Không refactor lớn ngay.
6. Chạy baseline, chọn 3 CC đại diện.
7. Viết failing test trước mỗi thay đổi logic kế toán.
8. Làm P0 trước: rounding và FX.
9. Chạy targeted test, E2E từng CC và đối chiếu Excel thủ công.
10. Sau mỗi phase, lưu evidence và cập nhật Change Log.

## 10. Tài liệu lịch sử

- `docs/audits/phase42n3k_fixed_asset_cc_full_data_audit.md`
- `reports/fy2027_audit_report_2026-07-13.md`
- `reports/fy2027_audit_evidence/`

Thứ tự ưu tiên bằng chứng:

1. Quyết định đã duyệt và workbook canonical 10.07.2026.
2. Code hiện tại, test và output tái lập được.
3. Tài liệu này.
4. Audit lịch sử theo workbook cũ.
5. File thủ công dùng làm behavioral evidence, không tự coi là source truth tuyệt đối.

## Change Log

| Date | Change |
|---|---|
| 2026-07-15 | Tạo GAP register, kế hoạch triển khai và checklist tiếp tục từ canonical 10.07, code hiện tại và reference FY2026/FY2027. |
