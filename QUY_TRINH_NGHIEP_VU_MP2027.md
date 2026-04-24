# MP2027 Manager - Quy trình nghiệp vụ, vận hành và handover kỹ thuật

Ngày cập nhật: `2026-04-24`

Tài liệu này là nguồn thông tin Markdown duy nhất của dự án. Mục tiêu là để người dùng không chuyên kỹ thuật hiểu quy trình lập Master Plan FY2027, để lập trình viên kiểm tra workflow, và để AI agent khác có đủ bối cảnh khi tiếp tục code.

## 1. Mục tiêu chương trình

MP2027 Manager là ứng dụng Windows desktop dùng Python/Tkinter để tự động tổng hợp dữ liệu ngân sách MP FY2027 từ nhiều file Excel nguồn, tính phân bổ chi phí theo rule, rồi xuất ra file FORM theo từng Cost Center.

Chương trình thay thế thao tác nhập tay lặp lại vào FORM, nhưng không tự bịa số liệu. Khoản nào không thể suy luận an toàn từ file nguồn thì phải do người dùng nhập hoặc xác nhận qua CSV/panel nhập liệu.

Yêu cầu gốc của người dùng nằm ở workbook:

`docs/MP2027/Cải tiến nhập dữ liệu chung vào file MPnew.xlsx`

Các sheet yêu cầu chính trong workbook này gồm:

- `Sheet1`: tổng quan yêu cầu nhập dữ liệu tự động vào file MP.
- `Hạng mục cần cải tiến`: các điểm cần bỏ nhập, đổi cột, giữ công thức, nhập đủ nhân sự 12 tháng, thêm driver sự kiện.
- `Chi phí hệ thống`: lấy dữ liệu IT Simulation, tính công thức số người nhân đơn giá, quy đổi tỷ giá.
- `Chi phí khấu hao, lãi nhà đất`: khấu hao/lãi nhà đất, điện nước.
- `Chi phí tài sản cố định`: lịch khấu hao/lãi tài sản cố định.
- `Chi phí làm giấy tờ cho NNN`: lấy chi phí giấy tờ NNN/VISA/GPLD/Passport theo tháng.
- `Chi phí sinh nhật`: lấy số người sinh nhật theo tháng, nhân đơn giá.
- `Chi phí phân bổ từ hành chính`: gas, vệ sinh, sự kiện, health check, quà, bus, các khoản cần driver riêng.
- `勘定科目`: master account.
- `原価センタ`: master Cost Center.

## 2. Trạng thái hiện tại

Mức đáp ứng hiện tại: khoảng `85-90%` về kỹ thuật. Phần đã làm được đủ tốt cho các luồng nguồn chính, nhưng chưa thể gọi là 100% vì còn thiếu dữ liệu nghiệp vụ thật cho một số driver sự kiện và một số mapping row/account chưa được người dùng xác nhận.

Đã hoàn thành:

- Runtime mặc định dùng `docs/MP2027`.
- FORM chuẩn runtime là `docs/MP2027/FORM.xlsx`.
- Tỷ giá USD/VND đọc từ `FORM.xlsx!B2`.
- Loader đọc master Cost Center, account, allocation rule từ FORM/rule workbook.
- Parser đã có cho Facility, Fixed Assets, IT Simulation, GA, Birthday, NNN paperwork.
- CSV nhập tay đã có cho headcount, special cost, manual event driver.
- Export giữ công thức ở mức có thể kiểm tra: `=amount`, `=count*unit_price`, `=ROUND(...*$B$2,0)`.
- Fixed row mapping của FORM MP2027 đã được sửa theo layout mới.
- Không auto-allocation sai cho NNN/VISA/GPLD/Passport khi thiếu driver.
- Dashboard kiểm toán có trạng thái XANH/VÀNG/ĐỎ, missing-input table và preview công thức.
- GUI đã Việt hóa phần lớn visible text, ngoại lệ cho từ `Dashboard`.
- Có file `docs/MP2027/source_file_order.xlsx` để quy định thứ tự file nguồn. Người dùng có thể chỉnh file này bằng Excel hoặc bằng nút `Thứ tự file nguồn` trên GUI.

Chưa hoàn tất:

- Cần dữ liệu thật cho JP/VN bus, quà không đi du lịch, My Episode, sự kiện 10 năm, kỷ niệm thành lập công ty, VISA/Passport/GPLD nếu không đi row 137.
- Cần xác nhận headcount theo CC/tháng, đặc biệt Nam/Nữ tháng 12 cho health-check row 57/58.
- Cần xác nhận row đích cho `Company anniversary` và `Quà tặng cho CNV không thể tham gia du lịch`.
- Cần audit account code theo 3 nhóm Cost Center `製造`, `一般`, `販売` cho các item hành chính.
- Một số nội dung trong workbook yêu cầu nằm trong ảnh/annotation nên openpyxl không đọc được ý nghĩa; cần người dùng chỉ rõ cell/row nếu muốn map 100%.

## 3. Nguồn dữ liệu chuẩn

Thư mục runtime chuẩn:

`docs/MP2027`

Các file quan trọng:

| File | Vai trò |
|---|---|
| `FORM.xlsx` | Template FORM MP2027 chuẩn để load master, đọc tỷ giá và export output. |
| `source_file_order.xlsx` | Danh sách thứ tự file nguồn do chương trình ưu tiên đọc, không bị lỗi font khi mở bằng Excel. |
| `source_file_order.csv` | Fallback kỹ thuật dạng UTF-8-BOM; không khuyến nghị người dùng chỉnh trực tiếp. |
| `施設課　MPFY2027.xlsx` | Facility: khấu hao/lãi nhà đất, điện nước. |
| `固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx` | Fixed Assets: lịch khấu hao/lãi tài sản cố định. |
| `システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls` | IT Simulation tháng 4-6. |
| `システム課金金額(Simulation)_FY2027_July.2026 ~ Dec.2026(Change AMS & PLM price).xls` | IT Simulation tháng 7-12. |
| `システム課金金額(Simulation)_FY2027_Jan.2027 ~ March.2027(Change SAP price).xls` | IT Simulation tháng 1-3. |
| `総務課 FY2027 MP 振替予定.xlsx` | GA/Admin: đơn giá, ngày làm việc, headcount nếu đọc được. |
| `Sinh nhật MP FY2027.xlsx` | Birthday: số người sinh nhật theo CC/tháng. |
| `FY2027配賦額一覧 (2025.12.29).xlsx` | Rule phân bổ, account theo nhóm CC, đơn giá, posting month. |
| `Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx` | NNN paperwork, hiện map vào row 137. |
| `headcount_manual.csv` | Người dùng nhập/chốt nhân sự theo CC/tháng. |
| `event_drivers_manual.csv` | Người dùng nhập driver sự kiện không suy luận được. |
| `special_costs_manual.csv` | Người dùng nhập chi phí đặc biệt theo exact FORM row. |

Không dùng runtime:

- `FORM.xlsx` ở thư mục gốc dự án hoặc cạnh exe nếu khác bản chuẩn.
- `docs/MP2027/FORM_old.xlsx`, nếu còn tồn tại, chỉ dùng đối chiếu lịch sử.
- `docs/MP2026` chỉ dùng tham chiếu nghiệp vụ, không copy số liệu FY2026 sang FY2027 nếu chưa được xác nhận.

## 4. Trường hợp đóng gói PyInstaller OneFile

Khi chạy dev, `BASE_DIR` là root dự án. Khi đóng gói onefile, `BASE_DIR` là thư mục chứa file `.exe`.

Thứ tự chương trình tìm FORM:

1. `.\docs\MP2027\FORM.xlsx` nằm cạnh file `.exe`.
2. FORM được bundle bên trong onefile tại `docs/MP2027/FORM.xlsx`.
3. Fallback cuối cùng là `.\FORM.xlsx`, nhưng đường này có guard chặn nếu là root FORM cũ/khác bản chuẩn.

Khuyến nghị khi bàn giao onefile:

- Đặt file exe tại một thư mục bàn giao, ví dụ `MP2027_App`.
- Bên cạnh exe phải có thư mục `docs\MP2027`.
- Trong `docs\MP2027` đặt `FORM.xlsx`, các workbook nguồn, các CSV manual và `source_file_order.xlsx`.

Cấu trúc đúng:

```text
MP2027_App/
  MP2027_Manager.exe
  docs/
    MP2027/
      FORM.xlsx
      source_file_order.xlsx
      headcount_manual.csv
      event_drivers_manual.csv
      special_costs_manual.csv
      施設課　MPFY2027.xlsx
      固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx
      システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls
      システム課金金額(Simulation)_FY2027_July.2026 ~ Dec.2026(Change AMS & PLM price).xls
      システム課金金額(Simulation)_FY2027_Jan.2027 ~ March.2027(Change SAP price).xls
      総務課 FY2027 MP 振替予定.xlsx
      Sinh nhật MP FY2027.xlsx
      FY2027配賦額一覧 (2025.12.29).xlsx
      Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx
```

Có thể bundle `docs/MP2027/FORM.xlsx` vào onefile, nhưng không nên phụ thuộc vào bản bundle nếu người dùng cần sửa FORM hoặc CSV. Onefile extract resource vào thư mục tạm, không phải nơi người dùng nên chỉnh dữ liệu. Với dữ liệu vận hành, luôn ưu tiên thư mục `docs\MP2027` đặt cạnh exe.

## 5. Thứ tự file nguồn và phương án dự phòng

Chương trình ưu tiên `docs/MP2027/source_file_order.xlsx`.

Đây là workbook Excel để tránh lỗi font khi người dùng mở file có tên tiếng Nhật/tiếng Việt. CSV `source_file_order.csv` chỉ còn là fallback kỹ thuật cho script, không phải file người dùng nên chỉnh.

Format trong sheet `source_file_order`:

```text
order,category,filename,enabled,description
1,facility,施設課　MPFY2027.xlsx,1,Facility depreciation interest electric water source
2,fixed_assets,固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx,1,Fixed assets source
3,it_simulation,システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls,1,IT simulation Apr-Jun source
```

Ý nghĩa:

- `order`: thứ tự nghiệp vụ/log khi chạy.
- `category`: loại file mà parser dùng. Các giá trị hiện có: `facility`, `fixed_assets`, `it_simulation`, `ga`, `birthday`, `allocation_rules`, `nnn_paperwork`.
- `filename`: tên file trong `docs/MP2027`.
- `enabled`: `1` để dùng, `0` để bỏ qua.
- `description`: ghi chú cho người vận hành.

Nếu sau này người dùng bổ sung file hoặc đổi thứ tự:

- Cách dễ nhất là mở chương trình và bấm `Thứ tự file nguồn`.
- Có thể chọn lại file cho từng dòng, bấm `Lên`/`Xuống`, bật/tắt dòng rồi bấm `Lưu`.
- Nếu là file cùng loại đã có parser, thêm dòng mới hoặc đổi `filename`.
- Nếu muốn tạm bỏ một file, đặt `enabled=0`.
- Nếu là loại dữ liệu mới chưa có parser, phải thêm parser/code mới và thêm `category` tương ứng.
- Nếu không có manifest hoặc file trong manifest thiếu, parser vẫn có fallback auto-detect cũ để giảm rủi ro.

## 6. Luồng chạy nghiệp vụ

1. Người dùng đặt toàn bộ nguồn vào `docs/MP2027`.
2. Người dùng kiểm tra `source_file_order.xlsx` hoặc bấm `Thứ tự file nguồn` nếu có đổi tên file/thứ tự.
3. Chương trình load `FORM.xlsx` để lấy tỷ giá, Cost Center, Account.
4. Chương trình load allocation rules từ workbook `FY2027配賦額一覧`.
5. Chương trình parse từng nguồn:
   - Facility.
   - Fixed Assets.
   - IT Simulation.
   - GA/Admin.
   - Birthday.
   - Manual headcount.
   - Manual special cost.
   - Manual event driver.
   - NNN paperwork.
6. Dữ liệu được đưa vào SQLite `mp2027.db`.
7. Allocation engine tính chi phí phân bổ.
8. HubBuilder export ra `OUTPUT_FY2027/MP_CC_<cc>.xlsx`.
9. Pipeline sinh audit report và missing-input CSV.
10. Người dùng mở Dashboard để xem trạng thái XANH/VÀNG/ĐỎ, bổ sung dữ liệu nếu cần, rồi chạy lại.

## 7. Cách chạy cho người dùng

Mở app:

- Chạy `run_MP2027.bat`, hoặc
- Chạy `py src/universal_app.py` khi ở môi trường dev.

Trên màn hình chính:

- Năm tài chính: nhập `2027`.
- Tệp mẫu FORM: kiểm tra đang là `docs/MP2027/FORM.xlsx`.
- Thư mục nguồn: kiểm tra đang là `docs/MP2027`.
- Cost Center: để trống nếu muốn export batch; chọn một CC nếu chỉ muốn kiểm tra nhanh.
- Bấm `CHẠY TÍNH TOÁN`.

Sau khi chạy:

- Mở Dashboard kiểm toán.
- Mở file output theo CC trong `OUTPUT_FY2027`.
- Xem `MP2027_MISSING_INPUTS.csv` để biết phần cần bổ sung.

## 8. Cách đọc Dashboard

Dashboard là lớp kiểm toán cho người dùng tài chính.

| Trạng thái | Ý nghĩa |
|---|---|
| XANH | CC có dữ liệu nền tảng và chưa có cảnh báo cơ bản. |
| VÀNG | CC có dữ liệu nhưng còn thiếu input/chưa chốt dữ liệu cần người dùng xem. |
| ĐỎ | CC chưa có dữ liệu tính toán sau lần chạy gần nhất. |

Lưu ý: XANH không có nghĩa là số liệu đã đúng 100%. XANH chỉ có nghĩa chương trình chưa thấy thiếu input cơ bản. Người dùng vẫn cần kiểm tra công thức, nguồn dữ liệu và audit report trước khi dùng chính thức.

Điểm cần cải thiện sau này: `has_event_driver_rows` trong Dashboard từng có rủi ro là global flag; nếu có event driver cho một CC thì có thể làm mờ cảnh báo ở CC khác. Nên nâng cấp thành kiểm tra theo CC nếu tiếp tục cải thiện Dashboard.

## 9. Mapping FORM MP2027 quan trọng

Các row đang được code bảo vệ bằng test hoặc mapping rõ:

| Row | Nội dung | Cách ghi hiện tại |
|---:|---|---|
| 36 | Khấu hao nhà | `=ROUND(usd*$B$2,0)` |
| 37 | Khấu hao đất | `=ROUND(usd*$B$2,0)` |
| 38 | Khấu hao thiết bị | `=ROUND(usd*$B$2,0)` từ fixed assets nếu có |
| 40 | Lãi nhà | `=ROUND(usd*$B$2,0)` |
| 41 | Lãi đất | `=ROUND(usd*$B$2,0)` |
| 42 | Lãi thiết bị | `=ROUND(usd*$B$2,0)` từ fixed assets nếu có |
| 44 | Điện | `=amount` vì nguồn facility chỉ có tổng tiền |
| 45 | Nước | `=amount` vì nguồn facility chỉ có tổng tiền |
| 46 | Gas | `=SUM(headcount)*unit_price` |
| 48 | Hand wash | `=SUM(headcount)*unit_price` |
| 49 | Toilet paper | `=SUM(headcount)*unit_price` |
| 51 | Cleaning | `=SUM(headcount)*unit_price` |
| 57 | Health check hằng năm | cần male/female December headcount và unit price |
| 58 | Health check tuyển dụng | cần event/new-hire driver |
| 59 | Birthday | `=count*152000` |
| 75 | IT system cost | `=ROUND((component sum)*$B$2,0)` |
| 97 | Sổ tay nhân viên mới | cần driver staff mới |
| 98 | Sổ tay công nhân mới | cần driver worker mới |
| 137 | Chi phí giấy tờ NNN | parser NNN workbook hoặc manual special cost |

## 10. Quy tắc công thức output

Người dùng yêu cầu giữ công thức để double-check.

Quy tắc hiện tại:

- Nếu nguồn chỉ có tổng tiền: ghi dạng `=123456`.
- Nếu là USD: ghi `=ROUND(usd*$B$2,0)`.
- Nếu là Birthday: ghi `=count*152000`.
- Nếu là IT: ghi `=ROUND((qty*unit+...)*$B$2,0)`.
- Nếu là manual event driver có count/unit_price: ghi `=count*unit_price`.
- Nếu là manual event driver chỉ có amount_vnd: ghi `=amount_vnd`.
- Nếu source workbook có formula breakdown như NNN, giữ breakdown khi có thể.

Không được paste số chết nếu có thể tạo công thức kiểm tra được.

## 11. Headcount và số người

Người dùng có thể thấy vùng số người trong FORM, ví dụ row `出向社員(人)` và `ローカル社員(人)`. Chương trình hiện xem FORM là template/layout và output target, không xem việc sửa tay trên FORM là kênh nhập headcount chính.

Kênh nhập ổn định:

`docs/MP2027/headcount_manual.csv`

Cột:

- `cc_code`: mã Cost Center.
- `period`: tháng dạng `YYYYMM`.
- `headcount_staff`: nhân viên.
- `headcount_worker`: công nhân.
- `headcount_male`: nam, dùng cho health check nếu có.
- `headcount_female`: nữ, dùng cho health check nếu có.
- `description`: ghi chú nguồn.

Nếu người dùng sửa trực tiếp số người trong FORM rồi chạy lại, output có thể bị ghi đè vì chương trình copy template và export theo database. Vì vậy cần hướng người dùng sửa `headcount_manual.csv` hoặc nhập qua GUI.

## 12. Dữ liệu sự kiện không được tự suy luận

Các khoản cần người dùng nhập/chốt:

- JP/VN bus.
- Số người tháng 3 FY cũ nếu rule yêu cầu.
- Sự kiện tháng 4/5/6/10.
- Quà không đi du lịch.
- My Episode.
- Kỷ niệm 10 năm.
- Kỷ niệm thành lập công ty.
- VISA/Passport/GPLD nếu cần row khác row 137.
- Health check nếu cần male/female hoặc driver tuyển dụng riêng.

Kênh nhập:

`docs/MP2027/event_drivers_manual.csv`

Cột:

- `cc_code`
- `period`
- `event_name`
- `count`
- `unit_price`
- `amount_vnd`
- `account_code`
- `form_row`
- `description`

Nguyên tắc: nếu không có dữ liệu thật thì để trống và để Dashboard/audit báo VÀNG, không tự bịa.

## 13. Special costs theo row FORM

Khi có chi phí phải vào chính xác một row FORM nhưng chưa có parser nguồn, dùng:

`docs/MP2027/special_costs_manual.csv`

Ví dụ dùng cho Passport/VISA/GPLD/NNN nếu người dùng xác nhận phải đi row khác `137`.

Cột quan trọng:

- `cc_code`
- `period`
- `amount_vnd`
- `account_code`
- `form_row`
- `description`

Nếu `form_row` rõ, exporter ghi trực tiếp vào row đó. Nếu không rõ row thì không nên nhập bừa.

## 14. MP2026 chỉ là tham chiếu

MP2026 là dữ liệu người dùng đã làm thật, có thể dùng để đối chiếu nghiệp vụ. Nhưng không được copy máy móc row hoặc số liệu sang FY2027 vì layout MP2027 đã đổi.

Hai fallback đã được áp dụng:

| Khoản | Tham chiếu MP2026 | Cách dùng FY2027 |
|---|---|---|
| Moon cake | row 71, đơn giá `56,000` | chỉ dùng khi rule FY2027 có unit_price bằng 0 |
| Sports day | row 67, đơn giá `107,000` | chỉ dùng khi rule FY2027 có unit_price bằng 0 |

Các khoản Passport/GPLD/VISA chỉ dùng MP2026 để hiểu loại chi phí và row tham khảo. FY2027 vẫn cần người dùng chốt row/account/amount nếu khác row 137.

## 15. Kiến trúc kỹ thuật

Stack:

- Python 3.13.x.
- GUI: Tkinter.
- Excel: openpyxl, pandas, xlrd.
- Database: SQLite.
- Đóng gói: PyInstaller OneFile.

Module chính:

| Module | Vai trò |
|---|---|
| `src/universal_app.py` | GUI, default path, Dashboard, editor nhập tay. |
| `scripts/run_e2e.py` | Orchestration pipeline. |
| `src/db/loader.py` | Load FORM master, account, allocation rules, tỷ giá. |
| `src/parsers/facility.py` | Facility workbook. |
| `src/parsers/fixed_assets.py` | Fixed Assets workbook. |
| `src/parsers/it_sim.py` | IT Simulation `.xls`. |
| `src/parsers/ga.py` | GA/Admin workbook. |
| `src/parsers/birthday.py` | Birthday workbook. |
| `src/parsers/nnn_paperwork.py` | NNN paperwork workbook. |
| `src/parsers/manual_headcount.py` | `headcount_manual.csv`. |
| `src/parsers/manual_event_drivers.py` | `event_drivers_manual.csv`. |
| `src/parsers/manual_special_costs.py` | `special_costs_manual.csv`. |
| `src/engine/allocator.py` | Tính allocation. |
| `src/engine/hub_builder.py` | Export công thức và dữ liệu vào FORM. |
| `src/audit/pipeline_audit.py` | Sinh audit report và missing-input CSV. |
| `src/utils/source_manifest.py` | Đọc/ghi `source_file_order.xlsx`, fallback `source_file_order.csv`. |

## 16. Database

SQLite file chính:

`mp2027.db`

Các bảng chính:

| Bảng | Vai trò |
|---|---|
| `dim_cost_centers` | Danh mục Cost Center từ FORM. |
| `dim_accounts` | Danh mục Account từ FORM. |
| `map_allocation_rules` | Rule phân bổ từ workbook FY2027. |
| `fact_input_data` | Staging hub cho tất cả nguồn chi phí. Có `source`, `period`, `cc_code`, `account_code`, `amount_vnd`, `amount_usd`, `form_row`. |
| `fact_monthly_headcount` | Headcount theo tháng/CC, gồm all/staff/worker/male/female. |
| `fact_allocation_log` | Trace allocation. |
| `sys_params` | Tỷ giá, fiscal year, working days. |

Các key kỹ thuật như `cc_code`, `account_code`, `form_row`, `staff`, `worker`, `period` không được Việt hóa trong code/data.

## 17. Các thay đổi gần nhất

Ngày `2026-04-24`:

- Sửa GUI default để ưu tiên `docs/MP2027/FORM.xlsx`, không tự chọn nhầm `FORM.xlsx` ở root.
- Sửa default source dir để ưu tiên `docs/MP2027`.
- Thêm `docs/MP2027/source_file_order.xlsx` làm cấu hình người dùng và `source_file_order.csv` làm fallback kỹ thuật.
- Thêm `src/utils/source_manifest.py`.
- Parser/loader ưu tiên manifest trước, fallback auto-detect sau.
- `scripts/run_e2e.py` log thứ tự file nguồn và chạy parser theo thứ tự mới.
- Đã xác nhận `_default_template_path()` trả về `D:\Sandbox\MP2027\docs\MP2027\FORM.xlsx`.
- E2E một CC `1412000006` chạy OK trong thư mục tạm vì `OUTPUT_FY2027` ở workspace từng bị Windows khóa quyền tạo/xóa.
- Unit test liên quan chạy OK: 23 tests.

Lưu ý: trong git status hiện có thể thấy `mp2027.db` và output thay đổi do E2E/test. Không revert nếu không có yêu cầu rõ.

## 18. Kiểm chứng nên chạy

Import check không ghi bytecode:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONIOENCODING='utf-8'
py -B -c "import src.universal_app, scripts.run_e2e, src.utils.source_manifest"
```

Unit tests:

```powershell
$env:PYTHONIOENCODING='utf-8'
py -m unittest tests.test_src_v2_logic tests.test_posting_month_logic tests.test_headcount_and_export
```

E2E một CC:

```powershell
$env:PYTHONIOENCODING='utf-8'
py scripts\run_e2e.py --fy 2027 --template docs\MP2027\FORM.xlsx --source docs\MP2027 --target-cc 1412000006
```

Nếu `OUTPUT_FY2027` bị Windows khóa, chạy từ thư mục tạm nhưng dùng template/source tuyệt đối:

```powershell
New-Item -ItemType Directory -Force -Path "$env:TEMP\mp2027_e2e_check" | Out-Null
Set-Location "$env:TEMP\mp2027_e2e_check"
$env:PYTHONIOENCODING='utf-8'
py D:\Sandbox\MP2027\scripts\run_e2e.py --fy 2027 --template D:\Sandbox\MP2027\docs\MP2027\FORM.xlsx --source D:\Sandbox\MP2027\docs\MP2027 --target-cc 1412000006
```

Kết quả kiểm chứng gần nhất:

- Import check: OK.
- E2E CC `1412000006`: OK.
- Unit tests: `Ran 23 tests`, `OK`.

## 19. Việc ưu tiên tiếp theo

P1:

- Thu thập/chốt `event_drivers_manual.csv` cho các event chưa có nguồn máy đọc.
- Thu thập/chốt headcount theo CC/tháng, nhất là Nam/Nữ tháng 12 cho row 57/58.
- Chốt row/account cho Passport/VISA/GPLD/NNN nếu khác row 137.
- Audit account code cho nhóm `製造`, `一般`, `販売`.
- Chốt row cho `Company anniversary` và `Quà tặng cho CNV không thể tham gia du lịch`.

P2:

- Cải thiện Dashboard để event driver check theo CC thay vì global.
- Thêm audit warning riêng cho health-check thiếu male/female December split.
- Nếu finance yêu cầu export cả CC không có fact data, sửa batch export để export tất cả `dim_cost_centers`, không chỉ CC có `fact_input_data.account_code > 0`.
- Kiểm tra GUI thực tế trên Windows sau khi Việt hóa và sau khi đổi default path.

P3:

- Nếu cần style FORM 100%, tạo test so sánh style/fill/border theo vùng managed rows.
- Nếu muốn IT bung theo từng hệ thống thay vì row tổng 75, cần người dùng cung cấp row đích rõ.

## 20. Quy tắc an toàn khi tiếp tục code

- Không dùng root `FORM.xlsx` làm runtime.
- Không dùng `FORM_old.xlsx` làm runtime.
- Không copy row number MP2026 sang MP2027 nếu chưa xác nhận layout.
- Không tự tạo số liệu sự kiện khi thiếu driver.
- Không Việt hóa key kỹ thuật trong schema/CSV/code.
- Khi sửa parser mới, phải giữ khả năng ghi công thức nếu có thể.
- Khi thêm nguồn mới, ưu tiên cập nhật `source_file_order.xlsx` bằng GUI và parser tương ứng.
- Khi chạy test/E2E có thể làm đổi `mp2027.db` và `OUTPUT_FY2027`; chỉ commit output nếu thật sự muốn bàn giao output mới.
- PowerShell có thể hiển thị mojibake với tiếng Việt/Nhật do codepage, nhưng file UTF-8 vẫn có thể đúng. Dùng `$env:PYTHONIOENCODING='utf-8'` khi chạy script/log có Unicode.

## 21. Tóm tắt cho AI agent tiếp theo

Bạn đang làm trong dự án `D:\Sandbox\MP2027`.

Mục tiêu hiện tại là hoàn thiện MP2027 Manager theo workbook yêu cầu gốc `docs/MP2027/Cải tiến nhập dữ liệu chung vào file MPnew.xlsx`.

Trạng thái code mới nhất:

- FORM runtime mặc định: `docs/MP2027/FORM.xlsx`.
- Source dir mặc định: `docs/MP2027`.
- OneFile cần thư mục `docs\MP2027` cạnh `.exe` nếu muốn người dùng sửa dữ liệu.
- Thứ tự file nguồn được điều khiển bởi `docs/MP2027/source_file_order.xlsx`; GUI có nút `Thứ tự file nguồn` để người dùng chỉnh.
- Helper manifest: `src/utils/source_manifest.py`.
- Parser/loader đã đọc manifest: facility, fixed_assets, it_simulation, ga, birthday, allocation_rules, nnn_paperwork.
- Test gần nhất: 23 unit tests OK; E2E một CC OK trong temp output.

Không nên bắt đầu bằng refactor lớn. Việc có giá trị nhất là bổ sung dữ liệu/mapping còn thiếu hoặc cải thiện audit Dashboard theo các P1/P2 ở trên.
