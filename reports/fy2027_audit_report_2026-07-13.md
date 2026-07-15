# Walkthrough — FY2027 simulation and reference audit

> **LIFECYCLE (2026-07-16): `HISTORICAL`.** Keep the fixed-assets comparison evidence. The old gas identity blocker is superseded by the current account+token resolver/writer; its regression tests currently stop at the FY2027 headcount integrity guard before gas assertions, so output acceptance remains open in `docs/handover/CURRENT_OPEN_ITEMS.md`.

## Kết quả chạy

Audit được thực hiện hoàn toàn trên:

- DB cô lập: `audit_outputs/FY2027/audit.db` — runtime local, không commit.
- Evidence portable: [fy2027_audit_evidence](fy2027_audit_evidence/)
- Nguồn đối chiếu: **65 workbook / 65 CC**
- Tỷ giá audit: **25.450 VND/USD**
- Tỷ giá reference: **26.273 VND/USD**

| Trạng thái | Số CC | Ý nghĩa |
|---|---:|---|
| `Observed` | 3 | Có baseline T3 nguồn thật |
| `Simulated` | 58 | T3 được sao chép từ T4 và gắn `SIMULATED_BASELINE_T3_FROM_T4` |
| `Blocked` | 4 | Thiếu dữ liệu staffing/time ngoài T3; không giả lập |
| **Tổng chạy được** | **61/65** | Không dùng reference để bổ sung đầu vào |

Bốn CC bị chặn đã được ánh xạ trực tiếp từ `B5` của 65 reference:

- `1412000034`
- `1412000070`
- `1412000106`
- `1412000108`

> [!IMPORTANT]
> Production `mp2027.db` có **0** dòng simulation. Audit DB có đúng **58** dòng provenance. Thư mục reference vẫn có đúng **65 workbook**. Các database này là runtime local và không được commit.

## Đối chiếu tài sản cố định

Nguồn fixed-assets chứa:

- **1.141 tài sản** thuộc phạm vi parser.
- **22 CC** có coverage.
- `machinery_equipment`: 99 tài sản.
- `vehicles`: 15 tài sản.
- `mold`: 490 tài sản.
- `tools_furniture_fixtures`: 533 tài sản.
- `other_tangible_fixed_assets`: 4 tài sản.
- 125 dòng bị bỏ qua vì category ngoài phạm vi.
- 1 dòng thiếu depreciation CC.

Audit DB có **14.238 fixed-asset facts**. Comparator tạo **1.145 tổ hợp CC × category × tháng**:

| Phân loại | Số dòng | Diễn giải |
|---|---:|---|
| `MATCH_VND` | 24 | Khớp VND trực tiếp |
| `FX_RATE_ONLY` | 244 | Khớp theo USD; chỉ khác do 25.450 so với 26.273 |
| `SOURCE_OR_SCOPE_GAP` | 474 | Chỉ có ở một phía; không được xem là lỗi tính |
| `AMOUNT_MISMATCH` | 403 | Có dữ liệu hai phía nhưng khác số; cần điều tra chronology/scope |

Phân rã theo loại:

| Loại | Match | FX only | Scope gap | Mismatch |
|---|---:|---:|---:|---:|
| Depreciation | 12 | 148 | 127 | 323 |
| Interest | 12 | 96 | 347 | 80 |

### Kết luận fixed-assets

1. **244 dòng chứng minh phép tính USD → VND đang đúng**, khác reference đúng bằng tỷ giá.
2. **24 dòng khớp trực tiếp bằng VND**.
3. **474 dòng không đủ điều kiện đánh giá thuật toán** vì thiếu scope ở một phía.
4. **403 mismatch không nên kết luận ngay là lỗi parser/schedule**.

Reference có các lớp chi phí riêng như:

- `(Tháng n) FIX ASSETS`
- `(Tháng n-1) FIX ASSETS`
- `(Tháng n-2) 金型償却費`

Trong khi audit dùng snapshot source `2025.11`. Ví dụ CC `1412000005` có cả ba lớp mold trong reference; chênh lớn chủ yếu phản ánh carry-over/chronology chưa có trong source audit, không phải cộng trùng dòng tổng hợp và chi tiết.

Ngoài ra có **148 dòng interest reference** không thể gán duy nhất vào một category từ description. Các dòng này được giữ riêng thay vì ép ghép sai.

> [!WARNING]
> Chưa thể xác nhận placement/formula trong workbook do export bị chặn bởi lỗi FORM không nhận diện duy nhất dòng `gas`. Kết luận hiện tại chỉ áp dụng cho DB calculation facts và reference cached values.

Evidence:

- [fixed_assets_comparison.csv](fy2027_audit_evidence/fixed_assets_comparison.csv)
- [fixed_assets_reference_rows.csv](fy2027_audit_evidence/fixed_assets_reference_rows.csv)
- [fixed_assets_unresolved_interest_rows.csv](fy2027_audit_evidence/fixed_assets_unresolved_interest_rows.csv)
- [audit_summary.json](fy2027_audit_evidence/audit_summary.json)

## Điều tra chi phí đồng phục

Đã trích xuất **146 dòng đồng phục từ 48 CC**, tất cả dùng account `5004086291`:

| Pattern | Số dòng |
|---|---:|
| Hardcoded amount | 46 |
| Recipient count × unit price | 32 |
| Other formula | 3 |
| Công thức/text bằng 0 | 40 |
| Blank | 25 |

Có **121 dòng có dữ liệu hoặc công thức**, 25 dòng trống.

Các pattern thực tế bao gồm:

- Đồng phục cho người mới: số người nhận × đơn giá mùa hè/mùa đông.
- Đổi đồng phục/giày/mũ bị hỏng: budget định kỳ hoặc số phân phối thực tế.
- Công thức chuyển đổi USD bằng `$B$2`.
- Công thức cộng riêng từng thành phần áo/quần/mũ/giày.
- Dòng zero/blank có chủ đích.

### Kết luận đồng phục

Logic hiện tại **đúng khi không tự suy diễn chi phí đồng phục từ biến động headcount**. Dữ liệu cần thiết là:

- số người thực nhận theo CC/tháng;
- loại phân phối: new hire, replacement, định kỳ;
- mùa/loại đồng phục;
- số bộ/người;
- đơn giá hiệu lực;
- account và provenance của quyết định phân phối.

Không nên dùng `headcount delta` hoặc số tuyển mới làm đại diện cho `配布数`, vì replacement và người nhận cụ thể không thể suy ra từ headcount.

Evidence: [uniform_reference_rows.csv](fy2027_audit_evidence/uniform_reference_rows.csv)

## Thay đổi mã nguồn

### Pipeline audit cô lập

Đã cập nhật [run_e2e.py](../scripts/run_e2e.py):

- Cho phép custom `db_path` và `output_dir`.
- Mô phỏng T3 từ T4 bằng canonical period `202603`/`202604`.
- Không ghi đè baseline thật.
- Gắn provenance `SIMULATED_BASELINE_T3_FROM_T4`.
- Cho phép loại CC thiếu đủ 12 tháng staffing/time trong audit.
- Preflight và batch scope tôn trọng danh sách `Blocked`.
- Thêm fail-fast guard: audit flags bị từ chối nếu không truyền DB cô lập hoặc trỏ tới production `mp2027.db`.

### UI Cost Center

[universal_app.py](../src/universal_app.py) đã có hành vi:

1. Nếu `dim_cost_centers` có dữ liệu, chỉ refresh combobox.
2. Nếu rỗng, nạp master từ FORM được chọn.
3. Xác nhận số CC nạp được.
4. Hiển thị lỗi rõ ràng nếu thất bại.
5. Nút được đổi thành `Nạp lại CC từ FORM`.

## Verification

```text
py -m py_compile scripts/run_e2e.py
py -m pytest tests/test_headcount_time_source.py tests/test_template_validation.py -q
```

Kết quả: **16 passed in 8.26s**.

Coverage mới xác nhận:

- canonical FY period cho baseline simulation;
- provenance simulation;
- không ghi đè baseline Observed;
- loại đúng CC thiếu staffing/time;
- preflight không kéo CC Blocked trở lại từ cost facts;
- audit flags không thể chạy trên production DB;
- reload 65 CC từ FORM và refresh-only khi master đã có.

## Blocker còn lại

`HubBuilder._find_recurring_admin_rows()` yêu cầu FORM có đúng một dòng `gas` theo account/tokens. FORM hiện tại không có match, nên export workbook dừng trước khi kiểm tra placement fixed-assets.

> [!IMPORTANT]
> Bước tiếp theo hợp lý là sửa identity mapping của dòng gas dựa trên FORM nghiệp vụ thật, rồi chạy lại export 61 CC. Không nên bỏ qua validation hoặc tạo một dòng gas giả vì có thể làm lệch vị trí/formula của các hạng mục tiếp theo.
