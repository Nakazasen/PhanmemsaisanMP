# Phase 42N3H Source Notice

Current canonical requirement: `raw/requirements/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026.xlsx`. If a raw-root copy exists at `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026.xlsx`, it may be used as the same current requirement.
Current visual support: `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026_ảnh.xlsx`.
Versioned full-coverage duplicate: `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026_ảnh_FULL_COVERAGE.xlsx`, retained only as a byte-identical duplicate and never above the official visual-support path.
Obsolete incomplete visual: `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026_ảnh_LEGACY_INCOMPLETE.xlsx`, retained only for historical comparison and not for active requirement interpretation.
Obsolete old visual requirement: `raw/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026_ảnh.xlsx`; do not use it.
If there is any conflict, the canonical workbook wins over the visual snapshot, Markdown, audit history, and derived descriptions.

# MP Saisan Business Knowledge Base

Tài liệu này là bản kiến thức nghiệp vụ cô đọng để upload lên NotebookLM. Mục tiêu là giúp hệ thống hiểu đúng cách dự án MP2027 đang sinh file MP Saisan FY2027, phân biệt nguồn dữ liệu thật, file tham khảo, skeleton, và các kết luận gap.

## 1. Executive summary

MP Saisan trong project này là workflow sinh file Master Plan FY2027 cho từng cost center/phòng ban. Trọng tâm hiện tại là cost center `1412000040` / `電気製造技術課`.

Mục tiêu kỹ thuật là sinh workbook MP FY2027 có sheet nghiệp vụ như `内訳ﾘｽﾄ(4～3月)`, đúng thứ tự file nguồn, đúng nhóm chi phí, đúng công thức/giá trị theo tháng, và không làm thay đổi default export nếu chưa bật flag rõ ràng.

Điểm quan trọng: **không được hiểu gap dòng là thiếu dữ liệu thật** nếu chưa phân loại rõ file nào là raw source, file nào là reference/skeleton, và dòng nào là source-derived hay reference-assisted. Physical row-count gap là sự thật đếm dòng, nhưng không tự động bằng “thiếu source”.

## 2. Canonical requirement sources

Các nguồn requirement chính:

- Current canonical: `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026.xlsx`
- Current visual support: `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026_ảnh.xlsx`
- Versioned full-coverage duplicate: `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026_ảnh_FULL_COVERAGE.xlsx` (byte-identical duplicate; official path remains the visual-support path)
- Obsolete incomplete visual: `raw/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026_ảnh_LEGACY_INCOMPLETE.xlsx` (historical 34-image artifact; not for active requirement interpretation)
- Obsolete visual support: `raw/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026_ảnh.xlsx`
- `docs/requirements/cai_tien_nhap_du_lieu_chung.md`

Quy tắc ưu tiên:

1. Excel gốc là source of truth chính.
2. Excel ảnh/OCR dùng để audit visual hoặc kiểm lại nội dung requirement. Each canonical source drawing is fully contained in at least one capture; overall coverage is 159/159.
3. Markdown derived chỉ dùng để search/phụ trợ.
4. Nếu Excel conflict với visual snapshot, Markdown, audit history, hoặc derived descriptions, **Excel gốc thắng**.

Không dùng các bản legacy/tên cũ làm source chính nếu user không yêu cầu rõ.

## 3. Source order rule

Requirement nói rõ cách điền dữ liệu theo thứ tự file:

- “Điền dữ liệu theo thứ tự dưới đây”.
- “chạy theo thứ tự file là được”.
- “không nhất thiết phải vào row nào cả”.
- “chạy xong 1 file thì cách 1 dòng”.

Ý nghĩa: file-order mode được phép sinh dòng theo thứ tự nguồn thay vì bám row number cũ của primary. Sau mỗi file/source group nên có blank separator row nếu requirement yêu cầu.

Các file source-order quan trọng gồm:

1. `施設課　MPFY2027.xlsx`
2. `固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx`
3. `システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls`
4. `システム課金金額(Simulation)_FY2027 July.2026 ~ Dec.2026(Change AMS & PLM price).xls`
5. `システム課金金額(Simulation)_FY2027 Jan.2027 ~ March.2027(Change SAP price).xls`
6. `総務課 FY2027 MP 振替予定.xlsx`
7. `Sinh nhật MP FY2027.xlsx`
8. `FY2027配賦額一覧 (2025.12.29).xlsx`
9. `Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx`
10. `event_drivers_manual.csv`
11. `special_costs_manual.csv`
12. `headcount_manual.csv`

## 4. File roles

Dựa trên inventory 42N2D, các file phải được phân loại theo vai trò trước khi kết luận gap:

### Raw input

Raw input là file có thể chứa dữ liệu nguồn nghiệp vụ, ví dụ facility, fixed assets, system cost simulation, admin/GA allocation, birthday, NNN paperwork. Raw input vẫn cần mapping cụ thể: workbook, sheet, row/cell, account, cost center, Apr-Mar values/formulas.

### Manual CSV

Manual CSV là input rõ ràng do project cung cấp để bổ sung dữ liệu có cấu trúc, ví dụ:

- `event_drivers_manual.csv`
- `special_costs_manual.csv`
- `headcount_manual.csv`

Nếu file chỉ có header hoặc chưa có row cho gap group thì không được bịa dữ liệu.

### Template

Template như `raw/FORM.xlsx` dùng cho cấu trúc output/sheet/formula style, không tự động là source amount.

### Primary reference

Primary reference là output chuẩn tham khảo cho phòng ban đang so:

- `reference_outputs/primary/16.KDTVN 電気製造技術課_MP FY2027_各予定(Ver01).xlsx`

Primary có thể dùng để hiểu skeleton, formula, expected row/order, nhưng không tự coi là raw source amount nếu chưa có chỉ định/provenance.

### Secondary reference pool

Secondary FY2027 pool nằm dưới:

- `reference_outputs/secondary/FY2027/`

42N2D inventory cho thấy secondary có nhiều workbook giống generated output/reference hoặc skeleton. Chúng hữu ích để học row patterns, formula shapes, order, account layout, nhưng không được claim là source-derived amount proof nếu chưa tìm upstream raw source.

### Requirement files

Requirement files định nghĩa rule, thứ tự file, và ý định nghiệp vụ. Chúng không thay thế raw amount source.

## 5. Primary/secondary reference explanation

Primary reference là file chuẩn để đối chiếu output của cost center `1412000040`. Không sửa primary. Không coi primary là raw source amount nếu không có provenance.

Secondary FY2027 files chủ yếu là generated output references hoặc skeleton references. Có thể dùng chúng để:

- học thứ tự row;
- học description/account pattern;
- học công thức và cấu trúc tháng F:Q;
- hỗ trợ reference-assisted fill nếu có label provenance rõ.

Không được dùng secondary như bằng chứng source-derived amount nếu chưa chứng minh upstream source workbook/sheet/row/cell.

## 6. Implemented v1 behavior

File-order export v1 đã được release-ready/useable ở mức flag explicit.

Flag chính:

- `--file-order-export-v1`

Hành vi v1:

- Default export không đổi nếu không bật flag.
- v1 bật các writer đã được chấp nhận như Facility, Admin consumables, System cost.
- Facility rows trong output v1 gồm vùng khoảng rows `200-205`, bao gồm các dòng như building/land depreciation/interest và utility rows.
- `電気代` tương ứng generated Facility `electricity` / `Điện`.
- `水道代` tương ứng generated Facility `water` / `Nước`.
- Có blank rows/separator theo file-order mode.
- Admin consumables đã có explicit export flag và được master flag v1 bật.
- System cost đã có explicit export flag và được master flag v1 bật.

Không được thay đổi default export hoặc sinh thêm dòng nếu chưa có flag/provenance rõ.

## 7. Gap accounting

Invariant accounting 42N2B sửa lỗi phương pháp so gap bằng description/fuzzy text.

Kết luận hiện tại:

- Physical row-count gap = `136`.
- Đây là counting fact giữa primary và generated v1.
- False gaps đã xác nhận: `電気代`, `水道代`.
- `電気代` đã được generated dưới Facility `electricity`.
- `水道代` đã được generated dưới Facility `water`.
- Real source-derived gap chưa final.
- Không được kết luận “thiếu dữ liệu/source” chung chung.

Phương pháp đúng phải ưu tiên invariant keys:

1. cost center;
2. account code;
3. business/source family;
4. month vector F:Q;
5. formula/value pattern;
6. known aliases;
7. description token chỉ là phụ trợ.

## 8. Known blockers

Nhóm blocker lớn nhất hiện biết là account `5005026371`.

- Có `75` primary rows thuộc account `5005026371`.
- Nhóm này liên quan fixed-assets/detail expense.
- Fixed asset workbook có master/reference và CC evidence.
- Nhưng chưa đủ mapping source-derived từng row: source workbook/sheet/row/cell + Apr-Mar monthly values/formulas.
- Không được code đoán monthly values.

Điều này không có nghĩa là công ty thiếu dữ liệu. Có thể blocker nằm ở parser coverage, file-role mapping, hoặc cần reference-assisted/skeleton strategy.

## 9. Provenance policy

Mỗi output row nên có provenance rõ:

- `SOURCE_DERIVED`: có raw source workbook/sheet/row/cell và month values/formulas proven.
- `REFERENCE_ASSISTED`: sinh dựa trên primary/secondary reference skeleton hoặc formula guide, có label rõ, không claim raw source.
- `SKELETON_REFERENCE`: row/formula/order skeleton để tham khảo, chưa có amount proof.
- `MANUAL_INPUT`: dữ liệu từ manual CSV/user-provided table.
- `UNKNOWN/NEEDS_MAPPING`: chưa đủ mapping, không code đoán.

Nếu dùng reference-assisted fill, report phải nói rõ dòng nào không phải source-derived.

## 10. Recommended path

Recommended: **HYBRID PATH**.

1. Dùng secondary references làm skeleton/formula/order guide.
2. Dùng reference-assisted fill với provenance label rõ ràng.
3. Chỉ implement source parsers khi chứng minh được source workbook/sheet/row/cell/month values.
4. Giữ default export unchanged; mọi hành vi mới phải qua explicit flag.

Hybrid path nhanh nhất vì có thể giảm physical row-count gap minh bạch mà không nói dối rằng mọi dòng đều source-derived.

## 11. Glossary

### CC 1412000040

Cost center của `電気製造技術課`, phòng ban đang là target chính trong các phase hiện tại.

### Account code

Mã tài khoản kế toán, ví dụ `5005026371`, `5005066281`, `5005066282`. Đây là invariant key quan trọng hơn description.

### 内訳ﾘｽﾄ(4～3月)

Sheet chi tiết tháng 4 đến tháng 3 trong workbook MP FY2027. Thường chứa account, item/description, và month columns F:Q.

### Source-derived

Dòng có chứng minh từ raw source: workbook, sheet, row/cell, account, CC, Apr-Mar values/formulas.

### Reference-assisted

Dòng được hỗ trợ bởi primary/secondary reference skeleton hoặc formula/order guide, có label rõ và không claim raw source.

### File-order mode

Mode sinh output theo thứ tự file nguồn trong requirement, không bắt buộc bám row number primary.

### Blank separator row

Dòng trống giữa các source groups/files theo requirement “chạy xong 1 file thì cách 1 dòng”.

### Primary reference

File output chuẩn tham khảo cho target department. Dùng để so skeleton/expected result, không tự động là raw source.

### Secondary reference

Pool FY2027 của nhiều department. Dùng để học pattern/skeleton/formula/order, không tự động là raw source amount.

## Source documents used

- `docs/requirements/cai_tien_nhap_du_lieu_chung.md`
- `docs/audits/phase42n2d_all_saisan_file_role_inventory.md`
- `docs/audits/phase42n2b_invariant_gap_accounting.md`
- `docs/audits/phase42n2a_exact_source_rows_verification.md`
- `docs/audits/phase42n2c_fixed_assets_detail_5005026371_mapping.md`
- `docs/audits/phase42n1w_auto_file_order_v1_rc_check.md`
- `docs/audits/phase42n1x_a_file_order_v1_release_readiness.md`
