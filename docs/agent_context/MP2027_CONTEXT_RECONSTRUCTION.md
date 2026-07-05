# MP2027 Manager — Context Reconstruction

## 1. Tóm tắt 10 dòng cho agent mới

1. MP2027 Manager là ứng dụng desktop Windows bằng Python/Tkinter để lập budget MP FY2027 theo Cost Center.
2. Chương trình gom dữ liệu từ nhiều workbook Excel nguồn, manual CSV, FORM template và master account/cost center.
3. Người dùng chính là người phụ trách lập/nghiệm thu budget, kiểm missing input và audit trail.
4. Output chính là workbook FORM theo từng Cost Center: `OUTPUT_FY2027/MP_CC_<cost_center>.xlsx`.
5. Chương trình phải giữ format/formula FORM, không paste số chết nếu yêu cầu là công thức.
6. Workbook canonical `raw/requirements/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026.xlsx` là nguồn nghiệp vụ cao nhất.
7. Markdown trong `docs/` là derived/handover, hữu ích để tra cứu nhưng không thắng workbook canonical.
8. Code hiện có parser cho facility, fixed assets, IT system cost, GA/admin, birthday, NNN paperwork và manual CSV.
9. Thiếu dữ liệu phải fail-closed: để trống, ghi missing input/audit, hoặc yêu cầu owner xác nhận.
10. Không được tự bịa số liệu, không fallback từ Cost Center khác, không biến blank thành zero.

## 2. Mục tiêu nghiệp vụ

- Người dùng muốn tự động hóa việc nhập dữ liệu chi phí chung từ nhiều file Excel vào file Master Plan/FORM FY2027.
- Excel/FORM hiện tại gây đau vì phải lọc Cost Center, tra account theo nhóm `製造/一般/販売`, copy dữ liệu tháng, giữ format/formula và kiểm tra thủ công nhiều nguồn.
- Output cuối cùng cần là FORM theo từng Cost Center, đúng dòng/cột tháng, đúng account, đúng công thức, có audit trace và missing-input report.
- Chương trình không thay owner quyết định nghiệp vụ: phần chưa đủ bằng chứng phải ghi rõ thiếu/chưa xác nhận.

## 3. Source of truth

Thứ tự ưu tiên khi có mâu thuẫn:

1. Workbook canonical `raw/requirements/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026.xlsx`.
2. Docs requirements/handover trong `docs/`, đặc biệt `docs/requirements/cai_tien_nhap_du_lieu_chung.md` và `docs/HANDOVER_FOR_NEXT_AGENT.md`.
3. Code parser/engine/exporter hiện tại.
4. Tests hiện tại.
5. README/handover derived.

Ghi chú: canonical workbook yêu cầu tồn tại local tại `raw/requirements/...09.06.2026.xlsx`.

## 4. Input chính

| Input | Vai trò | Đọc bởi module nào | Rủi ro nếu thiếu |
|---|---|---|---|
| `docs/MP2027/FORM.xlsx` | Template FORM, tỷ giá `B2`, master Cost Center/account, format/formula | `scripts/run_e2e.py`, `src/universal_app.py`, `src/engine/hub_builder.py` | Không export được FORM đúng chuẩn; root `FORM.xlsx` cũ không được dùng làm fallback nếu code đã chặn |
| `docs/MP2027/source_file_order.xlsx` / `.csv` | Manifest thứ tự file nguồn khi export source-order | `src/utils/source_manifest.py`, GUI source-order editor, writer/export flow | Sai thứ tự block output hoặc thiếu blank separator |
| `raw/headcount_manual.csv` | Headcount manual canonical; staff/worker/male/female theo CC/period | `src/parsers/manual_headcount.py`, GUI headcount editor, allocator | Thiếu driver cho new-hire, health check, allocation; phải missing input, không tự fill zero |
| `raw/bus_headcount_manual.csv` | Scalar bus passenger drivers theo CC: expat/Japanese và Vietnamese | `src/parsers/manual_headcount.py`, allocator bus logic | Không tính được bus cost; thiếu price/driver phải fail-closed |
| `docs/MP2027/event_drivers_manual.csv` | Manual event drivers cho event chưa suy luận được | `src/parsers/manual_event_drivers.py` | Event không có driver không được generate guessed rows |
| `docs/MP2027/special_costs_manual.csv` | Manual special costs khi có amount/row/account rõ | `src/parsers/manual_special_costs.py` | Nếu thiếu hoặc row/account chưa rõ thì không được nhập bừa |
| Facility workbook | Khấu hao/lãi nhà đất, điện, nước | `src/parsers/facility.py`, facility file-order preview/writer | Missing workbook/month/CC làm thiếu 6 khoản facility; cần audit |
| Fixed assets workbook | TSCĐ, depreciation/interest schedule | `src/parsers/fixed_assets.py` | Không được đoán schedule; unparseable period/month phải auditable |
| IT simulation workbooks | System cost theo 3 giai đoạn FY | `src/parsers/it_sim.py`, `src/engine/system_cost_preview.py`, `system_cost_writer.py` | Thiếu file kỳ nào có thể thiếu month vector; không infer month từ lân cận |
| GA/Admin workbook | Unit price, admin allocation, working days, bus unit prices | `src/parsers/ga.py`, `src/engine/allocator.py` | Thiếu driver/unit price gây missing input; bus cần price từ sheet `FY2027予定` |
| Birthday workbook | Sinh nhật, số người/đơn giá theo tháng | `src/parsers/birthday.py` | Target row có lịch sử mâu thuẫn; cần đối chiếu canonical/current output |
| NNN paperwork workbook | Chi phí làm giấy tờ cho người nước ngoài | `src/parsers/nnn_paperwork.py` | Target row 137 đã biết nhưng source row/month cần audit khi thay đổi |

## 5. Output chính

- `OUTPUT_FY2027/MP_CC_<cost_center>.xlsx`: workbook FORM theo Cost Center.
- `OUTPUT_FY2027/MP2027_AUDIT_REPORT.md`: audit report cho pipeline/export.
- `OUTPUT_FY2027/MP2027_MISSING_INPUTS.csv`: danh sách missing input/fail-closed evidence.
- `mp2027.db`: SQLite runtime DB, không nên commit.
- Các file temp/quarantine trong `OUTPUT_FY2027/` nếu có: runtime/reference evidence, không tự commit nếu chưa xác nhận.

## 6. Luồng xử lý end-to-end

```text
FORM/source order/manual inputs
→ parsers
→ database
→ allocation engine
→ exporter
→ audit
→ missing input report
```

Chi tiết hiện tại:

1. `run_MP2027.bat` gọi `py src/universal_app.py` để mở GUI.
2. E2E/developer CLI chạy `py scripts/run_e2e.py --target-cc 1412000040`.
3. Portable entry `packaging/mp2027_portable_entry.py` gọi `scripts.run_e2e.main()`.
4. Pipeline load FORM/template và source dir mặc định `docs/MP2027`.
5. Parser đọc facility, fixed assets, IT simulation, GA/admin, birthday, manual headcount, special costs, event drivers, NNN paperwork.
6. Dữ liệu staging vào SQLite `mp2027.db`.
7. `AllocationEngine.run_allocation()` map direct costs và xử lý allocation rules, event deltas, bus drivers, missing inputs.
8. `HubBuilder.export_to_template()` copy FORM, ghi row/series/công thức và xuất workbook theo CC.
9. `write_pipeline_audit_report()` sinh audit markdown và missing input CSV.

## 7. Bản đồ module nghiệp vụ

| Nhóm nghiệp vụ | Input | Parser/module | Target FORM | Rule chính | Test liên quan | Trạng thái |
|---|---|---|---|---|---|---|
| facility | Facility workbook trong `docs/MP2027` | `src/parsers/facility.py`, `facility_file_order_*` | Rows facility hoặc source-order area; historical rows 36/37/40/41/44/45 và 200-205 cần mode rõ | 6 khoản: khấu hao nhà/đất, lãi nhà/đất, điện, nước; USD có thể quy đổi bằng `B2` theo rule | `test_facility_*`, source-order tests | Implemented nhưng exact row/mode cần audit khi thay đổi |
| fixed_assets | Fixed assets workbook | `src/parsers/fixed_assets.py` | Known target rows 38 depreciation, 42 interest; source-order/detail còn cần audit | Expand depreciation/interest theo schedule và last month | `test_src_v2_logic.py`, `test_fixed_assets_reference_skeleton.py` | Implemented with tests; completeness theo raw source cần xác nhận |
| it_system_cost | 3 IT simulation `.xls` theo kỳ | `src/parsers/it_sim.py`, `system_cost_preview.py`, `system_cost_writer.py` | Combined/source-order row; writer tests có row 211/blank 212 | Gộp system cost, tháng lấy đúng file kỳ Apr-Jun/Jul-Dec/Jan-Mar; không infer missing month | `test_it_sim_parser.py`, `test_system_cost_*` | Implemented; default/export flag cần chú ý |
| ga_admin_allocation | GA/admin workbook | `src/parsers/ga.py`, `src/engine/allocator.py` | Admin rows, new-hire rows 97/98, health-check row 58, bus rows 53/54 theo docs | Driver/headcount/unit price; account theo CC → `原価区分` → account column | `test_admin_consumables_*`, allocator-related tests | Partly pass/fail-closed; nhiều driver cần input thật |
| birthday | Birthday workbook | `src/parsers/birthday.py` | Known docs nói row 59; lịch sử có xung đột row 63 | `number_of_people * unit_price` theo tháng; cần source proof | Không thấy test chuyên biệt rõ ngoài export/reference | Implemented nhưng needs current audit |
| nnn_paperwork | NNN paperwork workbook | `src/parsers/nnn_paperwork.py` | Known row 137 `F137:Q137` | Filter Cost Center chịu chi phí; lấy chi phí tháng vào FORM | `test_nnn_paperwork.py` | Implemented; source mapping cần audit khi thay đổi |
| manual_headcount | `raw/headcount_manual.csv` | `src/parsers/manual_headcount.py`, GUI | Driver, không phải amount row trực tiếp | Periods `202603`, `202604`-`202703`; staff/worker/male/female; blank giữ blank | `test_phase42n66_*`, `test_headcount_and_export.py` | Implemented; target CC 1412000040 còn blocker input trong docs |
| bus | `raw/bus_headcount_manual.csv`, GA unit price | `manual_headcount.py`, `AllocationEngine._process_bus_headcount_drivers` | Docs nói rows 53/54; cần output audit | Scalar count x monthly unit price từ GA `FY2027予定` B9:M10; missing price/driver fail-closed | `test_gui_bus_passenger_inputs.py` | PASS theo handover nhưng vẫn cần dữ liệu thật |
| event_drivers | `docs/MP2027/event_drivers_manual.csv` | `src/parsers/manual_event_drivers.py` | Event/manual rows theo schema | Chỉ generate từ rows schema-valid; supports posting rule/current/next month | `test_manual_event_drivers.py`, event fixture tests | Channel implemented; business events nhiều phần cần owner chốt |
| special_costs | `docs/MP2027/special_costs_manual.csv` | `src/parsers/manual_special_costs.py` | Explicit form row/account/month nếu có | Dùng khi có amount và row FORM rõ; không đoán | Export/reference tests gián tiếp | Channel implemented; needs confirmed data |

## 8. Nguyên tắc an toàn nghiệp vụ

- Không tự bịa số liệu, source, row, account hoặc driver.
- Không lấy dữ liệu từ CC khác nếu không có rule explicit.
- Không tự biến blank thành zero; blank khác zero.
- Thiếu input thì để trống, ghi `fact_missing_inputs`, audit report hoặc yêu cầu owner xác nhận.
- Giữ format/formula FORM, chỉ ghi vùng cần thiết.
- Không làm mất dữ liệu gốc, không xóa workbook/source/reference.
- Không commit runtime/private raw nếu chưa xác nhận governance.
- Account code không phải Cost Center: mã `1412...` là Cost Center; account thường dạng `500.../600.../700.../911...`.
- Khi tra account phải dùng `Cost Center -> 原価センタ -> 原価区分 -> 勘定科目 column 製造/一般/販売 -> account_code`.
- Workbook canonical 09.06.2026 thắng Markdown nếu conflict.

## 9. Những điểm đã ổn

- Có README tiếng Việt và handover cho agent kế tiếp.
- Có canonical requirement workbook local và docs derived giải thích yêu cầu.
- Có DB schema cho `dim_cost_centers`, `dim_accounts`, `map_allocation_rules`, `fact_input_data`, `fact_monthly_headcount`, `fact_bus_headcount_drivers`, `fact_allocation_log`, `fact_missing_inputs`, `sys_params` và các bảng helper.
- Có parser cho facility, fixed assets, IT simulation, GA/admin, birthday, NNN paperwork, manual headcount, manual event drivers, manual special costs.
- Có allocation engine xử lý direct costs, allocation rules, bus drivers, event deltas và missing inputs.
- Có exporter/hub builder giữ FORM và export per Cost Center.
- Có audit pipeline sinh report và missing input CSV.
- Có tests CI-safe và marker `requires_raw_excel`; GitHub CI dự kiến chạy `py -m pytest -m "not requires_raw_excel"`.
- Có packaging entrypoint đã import `scripts.run_e2e.main()`.

## 10. Những điểm còn rủi ro/chưa chắc

- CI có thể fail nếu vô tình chạy tests cần raw Excel thật; cần giữ tách `requires_raw_excel`.
- Raw Excel/source/reference/output có thể chứa dữ liệu công ty; không dump chi tiết và không push nếu chưa xác nhận.
- `requirement_mapping.yaml` có nhiều `needs_confirmation` / `REQUIRES_CURRENT_OUTPUT_AUDIT`.
- Một số row mapping có lịch sử/mode-dependent: rows 200-212, row 59 vs 63 birthday, system cost row 211, fixed rows vs source-order area.
- CC `1412000040` theo docs còn thiếu chuỗi headcount thật đủ cho một số claim/new-hire delta.
- Full E2E cần kiểm chứng bằng output thật nhưng không nên chạy nếu có thể sinh runtime output khi chưa được yêu cầu.
- Tracked `.brain`, `OUTPUT_FY2027`, `raw`, `docs/MP2027`, `reference_outputs` cần owner xác nhận governance.
- `mp2027.db` là runtime DB local, không nên commit.

## 11. Việc tiếp theo nên làm

### P0 — Không làm sai

- Bảo vệ raw/company data; không dump bảng Excel chi tiết ra báo cáo.
- Tách CI-safe tests khỏi raw Excel integration tests nếu chưa xong.
- Không merge khi CI đỏ.
- Không chạy E2E/export nếu không được yêu cầu rõ.
- Không đổi nghiệp vụ kế toán/phân bổ nếu chưa có bằng chứng workbook canonical và test.

### P1 — Cần làm ngay

- Xác nhận CI strategy: GitHub chỉ chạy `py -m pytest -m "not requires_raw_excel"`.
- Xác nhận raw fixture policy: workbook nào public-safe/curated, workbook nào private/runtime.
- Kiểm tra output cho CC `1412000040` bằng owner-approved run khi cần.
- Kiểm tra `MP2027_MISSING_INPUTS.csv` và audit report trước khi accept output.
- Rà lại các mapping `needs_confirmation` trong `requirement_mapping.yaml` với workbook canonical.

### P2 — Cải thiện

- Tạo fixture mẫu không nhạy cảm cho parser/unit tests.
- Tăng unit tests cho parser birthday/NNN/facility/GA edge cases.
- Tách UI khỏi engine nếu cần maintainability.
- Bổ sung requirement mapping chi tiết theo từng sheet/row/cell nhưng không chứa raw company data nhạy cảm.
- Viết data governance checklist cho tracked raw/reference/output.

## 12. Lệnh vận hành an toàn

Cài môi trường:

```powershell
py -m venv .venv
.\.venv\Scripts\activate
py -m pip install -U pip
pip install -r requirements.txt
```

Chạy compileall:

```powershell
py -m compileall src scripts packaging
```

Chạy CI-safe pytest:

```powershell
py -m pytest -m "not requires_raw_excel"
```

Chạy full local pytest, chỉ khi máy có đủ raw Excel/fixture hợp lệ:

```powershell
py -m pytest
```

Chạy E2E nếu có raw Excel và owner đồng ý sinh output runtime:

```powershell
py scripts/run_e2e.py --target-cc 1412000040
```

Mở GUI:

```powershell
run_MP2027.bat
```

## 13. Prompt ngắn cho agent lần sau

```text
Bạn đang làm trong repo D:\Sandbox\MP2027, project MP2027 Manager.
Đây là app Python/Tkinter gom dữ liệu budget MP FY2027 từ nhiều Excel/CSV, tính allocation, export FORM theo Cost Center.
Không sửa code nghiệp vụ nếu chưa có yêu cầu rõ.
Không commit/push/merge/xóa file.
Không chạy E2E/export nếu user chưa cho phép vì có thể sinh output runtime.
Source of truth cao nhất là raw/requirements/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026.xlsx.
Docs trong docs/ là derived; code/tests thấp hơn workbook canonical khi conflict.
Không bịa số, không fallback CC khác, không đổi blank thành zero.
Thiếu dữ liệu thì để trống, ghi missing input/audit hoặc hỏi owner.
Đọc trước README.md, QUY_TRINH_NGHIEP_VU_MP2027.md, docs/HANDOVER_FOR_NEXT_AGENT.md.
Đọc docs/requirements/cai_tien_nhap_du_lieu_chung.md và requirement_mapping.yaml.
Đọc docs/agent_context/MP2027_CONTEXT_RECONSTRUCTION.md nếu tồn tại.
Entrypoint GUI: run_MP2027.bat -> py src/universal_app.py.
Entrypoint E2E: scripts/run_e2e.py.
Portable entry: packaging/mp2027_portable_entry.py.
Pipeline: FORM/source order/manual inputs -> parsers -> SQLite -> AllocationEngine -> HubBuilder -> audit/missing CSV.
Quan trọng: Cost Center 1412... không phải account code; account code thường 500/600/700/911...
Account lookup phải đi Cost Center -> 原価センタ -> 原価区分 -> 勘定科目 製造/一般/販売.
Input chính: docs/MP2027/FORM.xlsx, source_file_order, raw/headcount_manual.csv, raw/bus_headcount_manual.csv, event/special CSV, facility/fixed assets/IT/GA/birthday/NNN workbooks.
Output runtime: OUTPUT_FY2027/MP_CC_<cc>.xlsx, MP2027_AUDIT_REPORT.md, MP2027_MISSING_INPUTS.csv, mp2027.db.
Không commit runtime/private raw nếu chưa xác nhận governance.
Validation an toàn: py -m compileall src scripts packaging; py -m pytest -m "not requires_raw_excel".
Full pytest/E2E chỉ chạy khi có raw Excel và user đồng ý.
Nếu thông tin mâu thuẫn, ghi “chưa xác nhận” hoặc “cần owner xác nhận”.
```
