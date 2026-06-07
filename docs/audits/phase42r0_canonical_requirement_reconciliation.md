# Phase 42R0 - Canonical Requirement Reconciliation

## Scope

Phase này chỉ khóa lại cách hiểu requirement từ 3 nguồn canonical:

1. `raw/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026.xlsx`
2. `raw/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026_ảnh.xlsx`
3. `docs/requirements/cai_tien_nhap_du_lieu_chung.md`

Không sửa business logic, parser, exporter, FORM template, generated output, hoặc strict compare hiện tại trong phase này.

> Excel gốc là source of truth. Excel ảnh dùng để xác minh vùng ảnh/mũi tên/khung màu. MD chỉ là index phụ trợ.

## Files inspected

| File | Status | Role |
|---|---|---|
| `raw/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026.xlsx` | FOUND | Source of truth |
| `raw/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026_ảnh.xlsx` | FOUND | Visual audit |
| `raw/requirements/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026.xlsx` | FOUND | Duplicate canonical copy |
| `raw/requirements/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026_ảnh.xlsx` | FOUND, untracked in current status | Duplicate visual canonical copy |
| `docs/MP2027/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026.xlsx` | FOUND | Duplicate canonical copy |
| `docs/MP2027/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026_ảnh.xlsx` | FOUND | Duplicate visual canonical copy |
| `docs/requirements/cai_tien_nhap_du_lieu_chung.md` | FOUND | Derived searchable MD |

## Workbook structure observed

Excel gốc và Excel ảnh đều có các sheet:

- `Sheet1`
- `Hạng mục cần cải tiến`
- `Chi phí hệ thống`
- `Chi phí khấu hao, lãi nhà đất`
- `Chi phí tài sản cố định`
- `Chi phí làm giấy tờ cho NNN`
- `Chi phí sinh nhật`
- `Chi phí phân bổ từ hành chính `
- `勘定科目`
- `原価センタ`

Excel ảnh chủ yếu chứa ảnh chụp ở các sheet nghiệp vụ. Excel gốc chứa text/cell/hyperlink/notes dùng để khóa requirement.

## Canonical requirement lock

| requirement_id | business_item | source_excel_cell_or_hyperlink | source_visual_anchor_or_image_note | md_section_if_present | canonical_decision | conflict_status | implementation_impact | test_impact |
|---|---|---|---|---|---|---|---|---|
| 42R0-A1 | Global FORM rules | MD lines 103-117 mirrors Excel requirement flow | Visual sheets show FORM formatting/colored targets | `## 1. Mục tiêu tổng thể` | Output phải giữ format/màu/font/border/filter, để lại công thức, không paste số chết khi requirement yêu cầu formula | OK | Exporter must preserve template formatting/formulas | Tests should check formulas and style preservation where feasible |
| 42R0-A2 | Old HR data | MD lines 29-33 | N/A | `0.1` | Không điền 2 dữ liệu nhân sự cũ | OK | Do not resurrect old HR fields | Regression test should ensure absent old fields |
| 42R0-A3 | Output order mode | `Hạng mục cần cải tiến!A179:B180` per MD | Visual row areas in Hạng mục sheet | `0.3` | Nếu không có row cố định thì output theo thứ tự file; chừa 1 dòng trống sau mỗi file nguồn | OK | Detail exporters must support file-order mode | Tests must not assume fixed row when requirement says file order |
| 42R0-B1 | Cost Center vs account | `原価センタ`, `勘定科目`; MD lines 58-74 | Master sheets visible in both workbooks | `3.1`, `3.2`, `3.3` | `1412...` là Cost Center, không phải account. Account là `500/600/700/911...` | OK | Parser/model names must not treat 1412 as account code | Tests should separate cost_center and account_code |
| 42R0-B2 | Account resolver | `原価センタ` -> `原価区分`; `勘定科目` columns `製造/一般/販売` | Master sheets | `3.3` | Dùng Cost Center tra `原価区分`, rồi dùng JP_Name tra account theo cột `製造/一般/販売` | OK | Master resolver must use `原価区分` | Unit tests for cost center with `採算区分` != `原価区分` |
| 42R0-B3 | Do not use 採算区分 | MD lines 212-219 | Master sheet | `3.3` | Không dùng `採算区分` để chọn account group | OK | Prevent account mapping drift | Account resolver tests |
| 42R0-C1 | NNN paperwork target | `Chi phí làm giấy tờ cho NNN!K19` says `F137 => Q137` | Visual image in NNN sheet at row anchor near 2/25 | `0.1`, `0.2` | Target FORM is `F137:Q137` | OK | NNN exporter writes row 137 months | Test row 137 formulas/values |
| 42R0-C2 | NNN filter | Text examples use `1412...` as chịu chi phí | Visual examples | `0.2` | Filter by Cost Center, not account code; sum multiple people/months | OK | Parser filters source by cost center | Multi-person/month test |
| 42R0-D1 | Birthday row conflict | `Chi phí sinh nhật!B24` says row 63 `G63:Q63`; `I24` says row 59 `F59:Q59` | Visual image in birthday sheet anchors around 3 and 26 | `0.1`, `0.2`, birthday section | Accepted target should remain `F59:Q59` if image/source confirms current FORM target; row 63 is conflict/old/intermediate instruction | MD_INTERPRETATION_RISK | Do not rely on row 63 without FORM check | Test must lock row 59 and document conflict |
| 42R0-D2 | Birthday formula | `Chi phí sinh nhật!B22`, `B47`; FY2027配賦額一覧 unit price note | Visual birthday examples | Birthday section | Formula is `(birthday_count + new_joiner_count) * unit_price` | OK | Parser must combine birthday people and new joiners | Tests for birthday + new joiner count |
| 42R0-E1 | System Cost hyperlink/target | MD records `Hạng mục cần cải tiến!K186 -> Chi phí hệ thống!A89`; `Chi phí hệ thống!A83/A89 area` | Visual system images anchors 1/54/106 | `0.3`, System Cost section | System Cost is gộp detail thành 1 dòng duy nhất | OK | Do not expand system details into many FORM rows | Test one output row for system cost |
| 42R0-E2 | System Cost formula | MD line 39; sheet text says formula issue | Visual detail sheets | System Cost section | Keep formula `ROUND((detail USD sum)*$B$2,0)`, not dead number | OK | Export formulas, not values | Formula test |
| 42R0-E3 | System account by KDC | Master resolver rules | N/A | Master resolver section | Account code chosen by `原価区分` | OK | System cost resolver uses master | Account mapping test |
| 42R0-F1 | Facility hyperlink | MD records `Hạng mục cần cải tiến!H182 -> Chi phí khấu hao, lãi nhà đất!J65` | Visual facility images anchors 1/54/107/160 | `0.3`, Facility section | “6 chi phí” means six Facility items, not one row | OK | Facility exporter must not collapse all facility into one row | Tests for six item categories |
| 42R0-F2 | Facility six items | `Chi phí khấu hao, lãi nhà đất!A1/A2/B64:B67` and later sections | Visual red boxes show khấu hao/lãi/điện/nước sections | Facility section | Six items: khấu hao nhà, khấu hao đất, lãi nhà, lãi đất, điện, nước | OK | Parser/exporter scans all rows and item types | Tests include land/interest/electric/water |
| 42R0-F3 | Facility no filter loss | `Chi phí khấu hao, lãi nhà đất!B62` warns filter can lose land depreciation row | Visual red boxes | Facility section | Scan full relevant table; do not lose land/interest rows by naive filter | OK | Parser must avoid filtering away đất/lãi đất | Test missing-line prevention |
| 42R0-G1 | Fixed asset depreciation | MD lines 45-50; `Chi phí tài sản cố định!B43:B49` | Visual fixed asset images anchors 3/54 | Fixed Assets section | Depreciation target `F38:Q38` | NEED_FORM_TEMPLATE_CHECK | Fixed asset exporter target row 38 if FORM confirms | Test row 38 after identity/layout reconciliation |
| 42R0-G2 | Fixed asset interest | MD lines 45-50; fixed asset rules same sheet | Visual fixed asset images | Fixed Assets section | Interest target `F42:Q42` | NEED_FORM_TEMPLATE_CHECK | Fixed asset interest exporter target row 42 if FORM confirms | Test row 42 after identity/layout reconciliation |
| 42R0-G3 | Last depreciation month | `Chi phí tài sản cố định!B43:B49`, examples C47/C50/C59/E53/E62 | Visual fixed asset examples | Fixed Assets section | Must handle last depreciation month inside FY; current phase does not prioritize code before Admin/NNN | OK | Parser/exporter must handle last month branching | Tests for last-month cases |
| 42R0-H1 | Admin allocation priority | `Chi phí phân bổ từ hành chính` sheet has many image anchors and merged instruction areas | Visual anchors rows 4/38/71/99/125/178/196 | Admin allocation section | Administrative allocation is high priority and complex | OK | Prioritize Admin after requirement lock | Tests by subtype |
| 42R0-H2 | 12-month common cost | Admin sheet notes per-person/unit price sections | Visual pink unit price images | Admin section | 12-month common cost uses previous month headcount, except April uses April | OK | Allocation engine must use month-specific headcount rule | Tests April vs other months |
| 42R0-H3 | Event by month | Admin sheet event sections | Visual examples | Admin section | Event costs allocated by event month | OK | Event parser maps month directly | Month test |
| 42R0-H4 | Periodic health check | Admin sheet unit price note around C176; gender-specific note | Visual health check image anchors around 178 | Admin section | Periodic health check month 12, split male/female | OK | Do not mix with hiring medical | Tests male/female December |
| 42R0-H5 | Notebook staff/worker | MD lines 50-52 | Admin visual examples | Admin section | Staff notebook row 97, worker row 98 | OK | Keep identity-based compare for these rows | Tests rows 97/98 |
| 42R0-H6 | Hiring medical check | MD lines 50-52 | Admin visual examples | Admin section | Hiring medical check row 58, shifted to next month | OK | Parser shifts hiring medical to next month | Test next-month shift |
| 42R0-H7 | Do not confuse health types | Admin sheet has separate periodic/hiring sections | Visual separate anchors | Admin section | Hiring medical != periodic health check | OK | Separate categories in parser/exporter | Tests both types |

## Conflicts and risks

| Item | Conflict/Risk | Decision |
|---|---|---|
| Birthday row 63 vs row 59 | Excel gốc has both `B24` row 63 and `I24` row 59 instruction | Treat row 59 as accepted target only after FORM/template check; row 63 is conflict/old/intermediate instruction |
| Fixed Assets row 38/42 | Requirement says target rows, but recent primary-reference strict compare showed row-number mismatch risk | Requirement target can be locked, but compare to primary must still be identity-aware |
| 42N1D/42N1E reports | They inferred missing snapshot from fixed row numbers | Deprecated for user/source-owner requests |
| MD as source | MD is useful and mostly matches, but not source of truth | Use Excel gốc first, image second, MD third |

## Implementation impact summary

- Resume compare methodology only after requirement lock is accepted.
- Do not ask source owner for rows 38/40/42/59 by fixed primary row number.
- For implementation priority, Admin allocation and NNN are safer to fix before deep Fixed Assets if code work resumes.
- Facility must remain six separate items, not one merged row.
- System Cost must be one row with formula.

## Recommendation

1. **Do not resume 42N1G-2 immediately as commit work.** First use this requirement lock to refine compare categories.
2. **First module to fix after approval:** Admin allocation / NNN, because requirement is clearer and high-priority.
3. **Compare methodology:** keep identity-based comparison for business rows whose primary ordering can differ; keep layout/header rows separate.
4. **Do not use deprecated request packs:** Phase 42N1D/42N1E missing snapshot reports should not be sent to source owner.

## Gate status

Gate commands were run after creating this report:

- `py -m compileall tools tests scripts`
- `git diff --check`

See final chat report for pass/fail result.
