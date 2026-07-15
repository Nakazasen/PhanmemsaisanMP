# Handover — Deep audit và hoàn thiện tài sản cố định không hardcode

**Ngày lập:** 2026-07-16  
**Trạng thái:** `READY_FOR_INDEPENDENT_DEEP_AUDIT`  
**Phạm vi:** fixed-assets depreciation/interest → asset → category/account → FORM  
**Không phải:** bằng chứng rằng implementation đã hoàn tất

> [!IMPORTANT]
> Đây là handover hiện hành cho fixed-assets. Nó thay thế cách tiếp cận “hỏi Accounting trước” trong kế hoạch GAP ngày 15.07.2026. AI tiếp quản phải đọc và đối chiếu đủ evidence hiện có trước; chỉ chuyển thành câu hỏi nghiệp vụ khi evidence thật sự mâu thuẫn hoặc không đủ.

## 1. Chỉ đạo trực tiếp của người dùng

Người dùng yêu cầu không được tiếp tục coi các quy tắc fixed-assets là chưa biết khi dự án đã có:

1. workbook hướng dẫn canonical;
2. output tham khảo FY2026 và FY2027;
3. workbook tính toán/source thật của công ty cho FY2026 và FY2027;
4. code, test và audit hiện tại.

Chỉ đạo bắt buộc:

> **CẤM HARDCODE vì còn phải dùng để làm cho những FY sau nữa.**

Do đó không được hardcode:

- `FY2027`, `202604`, `202703`;
- tỷ giá FY2026/FY2027 hoặc fallback rate;
- tên file/sheet source chứa năm/tháng cụ thể;
- output row/staging row làm business identity;
- category/account chỉ vì đã thấy ở một FY;
- hành vi xóa toàn bộ lịch sử fixed-assets khi import một FY.

## 2. Thứ tự authority và evidence bắt buộc

### Tầng 1 — Canonical requirement

- `raw/Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx`
- Sheet `Chi phí tài sản cố định`

### Tầng 2 — Source/calculation workbook của công ty

- `docs/MP2026/固定資産情報_Fixed_Assets_Information_2024.12 - December.xlsx`
- `docs/MP2027/固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx`
- FORM và source liên quan trong `docs/MP2026` và `docs/MP2027`

### Tầng 3 — Reference output

- `reference_outputs/secondary/FY2026`
- `reference_outputs/secondary/FY2027`

### Tầng 4 — Current implementation và tests

- `src/parsers/fixed_assets.py`
- `src/engine/hub_builder.py`
- `src/engine/complete_v1_source_order_writer.py`
- `src/engine/output_mode.py`
- `src/engine/account_resolver.py`
- `src/utils/source_manifest.py`
- `src/utils/fiscal_periods.py`
- `src/db/schema.py`
- `src/audit/fixed_assets_coverage.py`
- các test fixed-assets/source-order liên quan

### Tầng 5 — Derived documents

- `docs/requirements/cai_tien_nhap_du_lieu_chung.md`
- `docs/knowledge/mp_saisan_business_knowledge_base_v2.md`
- `docs/audits/fixed_assets_gap_and_implementation_plan_2026-07-15.md`
- audit/report lịch sử

> [!WARNING]
> Markdown và audit là derived evidence. Không dùng wording cũ “Chưa chốt” để bỏ qua việc đọc workbook. Reference output là behavioral evidence rất mạnh nhưng không tự override canonical nếu chứa manual carry-over/adjustment không truy được nguồn.

## 3. Quy tắc đã được xác định

Các điểm sau đã có canonical và/hoặc xác nhận trực tiếp của người dùng:

### Fiscal calendar

- FY của công ty chạy từ tháng 4 năm trước đến tháng 3 của fiscal year.
- Ví dụ FY2027 là `202604..202703`.
- Production logic phải sinh period từ fiscal year runtime; ví dụ chỉ dùng để audit, không nhúng literal vào code.

### Depreciation theo từng asset

Với mỗi asset:

- `L`: khấu hao thường mỗi tháng;
- `P`: terminal/Last Depreciation Month;
- `Q`: khấu hao riêng tại terminal month.

Nếu terminal month nằm trong FY:

- tháng trước P: `ROUND(L × rate, 0)`;
- đúng tháng P: `ROUND(Q × rate, 0)`;
- tháng sau P: **blank**, không phải `0`.

Nếu asset không kết thúc trong FY hoặc terminal month sau FY:

- dùng L đủ các tháng của FY.

### Interest theo từng asset

- tháng đầu FY dùng `V`;
- các tháng tiếp theo dùng `W`;
- interest vẫn có tại terminal month;
- sau terminal month để blank.

### Aggregate/output

- Tính theo **từng asset trước**.
- Sau đó cộng vào dòng FORM theo tháng theo category/account phù hợp.
- Output có thể là summary theo category/account, nhưng phải giữ audit trail truy ngược từng asset.
- Nếu công thức quá dài, output tổng phải đi kèm sheet/report audit chi tiết từng asset.

### FX và rounding

- Công thức canonical VND là `ROUND(USD × tỷ giá, 0)`.
- Tỷ giá hiệu lực phải đến từ FORM/runtime source đã kiểm chứng; công thức output tham chiếu `$B$2`.
- Giá trị quan sát FY2026/FY2027 chỉ dùng làm baseline audit, không phải constants trong code.

### Lưu dữ liệu

- Thiết kế phải hỗ trợ nhiều FY/snapshot; import FY mới không được xóa history FY khác.

## 4. Điểm chưa được phép biến thành kết luận

### Terminal month trước FY

Người dùng chưa xác nhận trực tiếp quy tắc “terminal trước FY = blank toàn FY”. Wording canonical “Last Depreciation Month không nằm trong FY thì chạy toàn FY” có thể bị đọc theo hai nghĩa.

AI tiếp quản phải:

1. tìm asset có terminal month trước FY trong source MP2026/MP2027;
2. trace asset đó sang reference output;
3. đọc formula/calculation sheet tương ứng;
4. chỉ kết luận sau khi có evidence.

Không hỏi Accounting trước khi thực hiện bốn bước trên.

### Formula thủ công và manual carry-over

Reference output có thể chứa:

- `ROUND`;
- `ROUNDUP`;
- liên kết dòng/sheet;
- công thức cộng dồn;
- constants/adjustment nhập tay.

Không mặc định mọi formula thủ công là canonical. Phải phân loại:

- canonical calculation;
- source-derived exception;
- manual carry-over;
- unexplained adjustment;
- formatting artifact.

### Adjustment âm, thiếu Q và category phạm vi

Không được chọn policy chỉ để code chạy. Nhưng cũng không được đẩy thẳng cho Accounting. Trước hết phải thống kê toàn corpus:

- có adjustment âm thật hay không, ở source hay output, formula/provenance nào;
- asset terminal trong FY có Q thiếu hay không, output công ty xử lý thế nào;
- tất cả category/source class và account đích quan sát ở hai FY.

Chỉ phần vẫn mâu thuẫn sau cross-trace mới mang đi review.

## 5. Code hiện tại chưa đáp ứng yêu cầu

Đây là finding từ đọc code, không phải suy đoán:

### `src/parsers/fixed_assets.py`

- fallback rate `25450.0`;
- fallback fiscal year `FY2027`;
- `CATEGORY_SPECS` và account mapping được ghi cứng;
- source fallback phụ thuộc chuỗi tên `Fixed_Assets_Information`;
- chỉ đọc `data_only=True`;
- thiếu Q tại terminal month fallback âm thầm về L;
- amount `<= 0` bị loại;
- import chạy `DELETE ... WHERE source='fixed_assets'`, xóa mọi FY.

### `src/engine/hub_builder.py`

- `_write_fx_formula_series()` bỏ amount `<= 0`;
- fixed-assets aggregate query chỉ lấy `amount_usd > 0`;
- aggregate USD theo category rồi mới `ROUND`, trong khi requirement yêu cầu tính theo asset trước;
- `values_usd.get(period, 0.0)` làm mất phân biệt missing/blank/zero;
- source file lấy qua vị trí cứng trong `CANONICAL_SOURCE_FILE_ORDER`.

### `src/engine/output_mode.py` và source-order layer

- default source filenames chứa FY2027 và tháng/năm cụ thể;
- business identity còn coupling với thứ tự/vị trí nguồn cứng.

### `src/db/schema.py`

`fact_input_data` chưa đủ structured provenance cho:

- fiscal year/import snapshot;
- asset number/text;
- source sheet/row;
- category/kind;
- terminal period;
- input/formula status.

## 6. Những gì đã đọc và những gì chưa hoàn tất

Đã thực hiện:

- đọc trực tiếp canonical sheet `Chi phí tài sản cố định`;
- inventory reference: FY2026 có 64 workbook, FY2027 có 65 workbook;
- đọc code parser/writer/schema/period helpers;
- xác định workbook source fixed-assets thật của cả MP2026 và MP2027;
- quan sát source FY2027 có các sheet dữ liệu và sheet hướng dẫn/tính như `Calculate Depr&Interest FA`, `Planned Depreciation`;
- quan sát reference có cả category summary và asset/manual rows;
- xác định fiscal-period helper đã có khả năng sinh FY động, nhưng fixed-assets layer chưa dùng an toàn.

Chưa được claim đã hoàn tất:

- chưa tạo cross-trace toàn corpus asset → source formula → output FY2026/FY2027;
- chưa khóa quy tắc terminal trước FY bằng evidence;
- chưa phân loại toàn bộ adjustment âm/manual layers;
- chưa chứng minh category/account mapping đầy đủ;
- chưa sửa production code;
- chưa có targeted test suite xanh theo contract mới;
- chưa có comparator true-amount xuyên hai FY.

> [!CAUTION]
> Một scan workbook trước đó bị lỗi khi giả định sheet name/date pattern. AI sau phải resolve sheet/header theo nội dung, không dựa vào tên `2025.11`, `2024.12` hoặc column letter cố định.

## 7. Quy trình audit không thiên lệch

### Bước A — Chụp baseline

1. `git status -sb` và ghi commit đang audit.
2. Chạy targeted tests hiện tại; ghi rõ pass/fail, không gọi failure là pre-existing nếu không có baseline.
3. Inventory workbook/sheet/header/formula/cache cho cả hai FY.
4. Không sửa code trong bước discovery.

### Bước B — Lập asset ledger

Tạo ledger read-only có tối thiểu:

- FY, source file, sheet, row;
- asset number/text;
- category/class;
- control CC và depreciation CC;
- L, P, Q, V, W;
- raw formula và cached value;
- expected monthly USD/status theo rule;
- reference workbook/row/formula/value tương ứng;
- account/category đích;
- mismatch classification.

### Bước C — Cross-trace và phân loại

Phân loại từng mismatch:

- `EXACT_MATCH`;
- `FX_ONLY`;
- `ROUNDING_ORDER`;
- `TERMINAL_OR_BLANK`;
- `FORMULA_CACHE_GAP`;
- `CATEGORY_ACCOUNT_GAP`;
- `SOURCE_SCOPE_GAP`;
- `MANUAL_CARRY_OVER`;
- `NEGATIVE_ADJUSTMENT`;
- `TRUE_AMOUNT_MISMATCH`;
- `UNDECIDABLE_AFTER_EVIDENCE`.

### Bước D — Decision matrix

Mỗi câu hỏi cũ phải được chuyển thành một trong:

- `DETERMINED_FROM_CANONICAL_AND_EVIDENCE`;
- `OBSERVED_EXCEPTION_OR_MANUAL_LAYER`;
- `INCONSISTENT_REQUIRES_REVIEW`;
- `GENUINELY_UNDECIDABLE`.

Mỗi kết luận phải có file/sheet/cell hoặc source row/reference row làm evidence.

### Bước E — Plan implementation

Chỉ sau khi decision matrix hoàn tất:

1. viết failing tests cho contract;
2. tách domain policy khỏi parser;
3. sửa parser/source resolver;
4. sửa schema/provenance và import scope;
5. sửa aggregate/rounding/blank/negative handling;
6. bỏ filename/FY/rate hardcode;
7. chạy regression trên FY2026, FY2027 và một FY tương lai tổng hợp.

## 8. Acceptance bắt buộc

Chỉ claim fixed-assets complete khi:

- không có fallback rate/FY hardcode;
- source được resolve bằng manifest/header, không dựa vào FY filename;
- fiscal calendar được sinh động;
- tính/round từng asset trước rồi mới aggregate;
- terminal month đúng L/Q và post-terminal thật sự blank;
- missing khác zero;
- adjustment âm không bị mất âm thầm;
- missing formula cache không thành zero;
- mọi parsed/excluded asset có provenance/reason;
- mapping category/account đủ hoặc unknown fail-closed có report;
- import FY mới không xóa FY cũ;
- comparator FY2026/FY2027 phân loại mọi mismatch;
- true mismatch bằng 0 hoặc có review/acceptance rõ ràng;
- fixture FY tương lai chạy mà không sửa production code.

## 9. Deliverable của AI tiếp quản

AI sau phải tạo/cập nhật:

1. evidence matrix/ledger;
2. audit report với citations file/sheet/cell;
3. decision matrix thay bảng “Chưa chốt” cũ;
4. implementation plan đã được evidence dẫn dắt;
5. targeted tests và code chỉ sau khi plan được duyệt;
6. comparator output cho FY2026/FY2027;
7. cập nhật `CURRENT_OPEN_ITEMS.md`, audit lifecycle và knowledge base.

## 10. Prompt copy-paste cho AI tiếp quản

```text
Bạn đang tiếp quản deep audit fixed-assets của project MP2027 tại D:\Sandbox\MP2027.

Mục tiêu: điều tra độc lập, nối đầy đủ requirement → source/calculation workbook → reference output → current code/tests → FORM output; sau đó mới đề xuất/sửa implementation. Không làm mất mạch, không bị wording audit cũ dẫn dắt, không hỏi Accounting trước khi đọc đủ evidence.

BẮT BUỘC đọc theo thứ tự:
1. docs/handover/CURRENT_OPEN_ITEMS.md
2. docs/handover/FIXED_ASSETS_DEEP_AUDIT_HANDOVER_2026-07-16.md
3. docs/audits/AUDIT_STATUS_INDEX.md
4. raw/Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx, sheet Chi phí tài sản cố định
5. docs/MP2026 và docs/MP2027, đặc biệt hai workbook 固定資産情報_Fixed_Assets_Information_*.xlsx, FORM và calculation sheets
6. reference_outputs/secondary/FY2026 và reference_outputs/secondary/FY2027
7. src/parsers/fixed_assets.py, src/engine/hub_builder.py, src/engine/output_mode.py, src/engine/account_resolver.py, src/utils/source_manifest.py, src/utils/fiscal_periods.py, src/db/schema.py, src/audit/fixed_assets_coverage.py và tests liên quan
8. docs/audits/fixed_assets_gap_and_implementation_plan_2026-07-15.md chỉ như provenance, không coi bảng Chưa chốt là ground truth.

Chỉ đạo người dùng: CẤM HARDCODE vì phải dùng cho FY sau. Không hardcode FY2027, periods, FX, source filename/sheet, row identity, category/account theo một FY, hoặc xóa toàn bộ fixed-assets history.

Các rule đã xác định:
- FY chạy April–March và phải sinh từ fiscal_year runtime.
- Tính theo từng asset trước rồi mới cộng category/account vào FORM.
- Với terminal month trong FY: tháng trước dùng L; terminal month dùng Q; sau đó blank, không ghi 0.
- Interest: tháng đầu FY dùng V, các tháng sau dùng W; có đến terminal month; sau đó blank.
- Terminal sau FY/không kết thúc trong FY: L chạy đủ FY.
- VND dùng Excel ROUND(USD × rate, 0); output tham chiếu FORM $B$2; rate quan sát FY cũ không phải constant.
- Phải giữ asset-level provenance dù output summary.
- DB/import phải hỗ trợ nhiều FY/snapshot.

Không được tự kết luận terminal month trước FY = blank hoặc full FY. Hãy tìm asset thật có trường hợp này trong source MP2026/MP2027, trace sang reference output và calculation formula, rồi mới chốt.

Không được tự coi mọi ROUNDUP/link/constant trong reference là canonical. Phải phân loại canonical, source-derived exception, manual carry-over, unexplained adjustment và formatting artifact.

Nhiệm vụ discovery/audit trước khi sửa code:
A. Chụp baseline commit/tests; không gọi failure pre-existing nếu không có baseline.
B. Resolve workbook sheet/header bằng nội dung, không dùng tên năm/tháng hoặc column letter cố định.
C. Tạo asset ledger: FY, source file/sheet/row, asset, category, control/depreciation CC, L/P/Q/V/W, raw formula, cached value, expected monthly schedule, reference row/formula/value, account đích và mismatch class.
D. Cross-trace toàn corpus FY2026/FY2027.
E. Phân loại EXACT_MATCH, FX_ONLY, ROUNDING_ORDER, TERMINAL_OR_BLANK, FORMULA_CACHE_GAP, CATEGORY_ACCOUNT_GAP, SOURCE_SCOPE_GAP, MANUAL_CARRY_OVER, NEGATIVE_ADJUSTMENT, TRUE_AMOUNT_MISMATCH, UNDECIDABLE_AFTER_EVIDENCE.
F. Chuyển từng câu hỏi cũ thành DETERMINED_FROM_CANONICAL_AND_EVIDENCE, OBSERVED_EXCEPTION_OR_MANUAL_LAYER, INCONSISTENT_REQUIRES_REVIEW hoặc GENUINELY_UNDECIDABLE, có citation file/sheet/cell/row.
G. Chỉ sau đó lập implementation plan. Không sửa code kế toán khi decision matrix chưa đủ hoặc chưa được user duyệt.

Current code findings phải kiểm chứng lại trên HEAD:
- fixed_assets.py có fallback 25450/FY2027, category/account cứng, data_only=True, Q→L fallback, lọc <=0 và DELETE toàn source.
- hub_builder.py lọc amount_usd >0, gom USD trước ROUND, đồng nhất missing với 0 và dùng source-order vị trí cứng.
- output_mode/source-order có FY2027 filenames cứng.
- schema thiếu fixed-assets structured provenance/multi-FY import identity.

Deliverable đầu tiên: audit/evidence matrix, không phải patch. Báo rõ điều đã chứng minh, điều chưa chứng minh, contradictions và next action. Chỉ hỏi người dùng/Accounting những điểm còn mâu thuẫn hoặc thiếu sau cross-trace. Khi đề xuất implementation phải có tests cho FY2026, FY2027 và một FY tương lai tổng hợp để chứng minh không hardcode.
```

## 11. Liên kết lifecycle

- Live register: `docs/handover/CURRENT_OPEN_ITEMS.md`
- Audit lifecycle: `docs/audits/AUDIT_STATUS_INDEX.md`
- Audit GAP tiền nhiệm: `docs/audits/fixed_assets_gap_and_implementation_plan_2026-07-15.md`
- Top-level handover: `docs/HANDOVER_FOR_NEXT_AGENT.md`

Khi fixed-assets đổi trạng thái, cập nhật bốn tài liệu này cùng knowledge base. Không tạo thêm một backlog song song.
