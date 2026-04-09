# TODO MP2027 Open Items

Ngay cap nhat: `2026-04-09`

Quy uoc:
- `P1`: anh huong truc tiep den output nghiep vu
- `P2`: xac nhan/mo rong
- `P3`: tai lieu, package, ban giao

## 1. Audit 109-137

- [x] `P1` Dong `117` - chi phi he thong da chuyen sang cong thuc tong hop
Code dich: `src/parsers/it_sim.py`, `src/engine/hub_builder.py`

- [x] `P1` Dong `127` - recurring admin da dung cong thuc theo dau nguoi
Code dich: `src/parsers/ga.py`, `src/engine/allocator.py`, `src/engine/hub_builder.py`
Ghi chu: da xong cho `Gas`, `Hand wash`, `Toilet paper`, `Cleaning`

- [x] `P1` Dong `127` - fixed-row export da co cho nhom hanh chinh chinh
Code dich: `src/engine/hub_builder.py`, `src/engine/allocator.py`

- [x] `P1` Dong `133` - da mo rong engine cho chi phi giay to NNN
Code dich: `src/parsers/manual_special_costs.py`, `src/engine/allocator.py`, `src/engine/hub_builder.py`
Ghi chu: engine san sang, con thieu du lieu that

## 2. Da xong trong dot nay

- [x] `P1` Uu tien `docs/MP2027` lam bo input/runtime chuan
- [x] `P1` Sua loader parse duoc unit price dang `145$`
- [x] `P1` Nang rule loader len `66` rule
- [x] `P1` Sua token posting month `入社月`, `配布月`, `申請月`, `取得月`, `翌月`
- [x] `P1` Chan auto-allocation sai cho NNN/VISA/GPLD/Passport
- [x] `P1` Nang parser IT doc tong va component `VPN/Mail/R3/MES/PLM/QLIK/VPS/AMS`
- [x] `P1` Sua row `75` thanh cong thuc tong hop IT
- [x] `P1` Clear sample rows `38-90`, `93-109`, `111-152`
- [x] `P1` Ghi recurring admin vao row co dinh:
  - `42` Gas
  - `44` Cleaning
  - `93` Hand wash
  - `94` Toilet paper
- [x] `P1` Ghi fixed-row cho nhom:
  - `Company trip`
  - `Kickoff party`
  - `Kyocera festival`
  - `Moon cake`
  - `Sports day`
  - `Year-end party subsidy`
  - `New year gift`
  - `Health check male/female`
  - `employee card/photo/philosophy/card case/pen/note`
- [x] `P1` Bo sung parser `special_costs_manual.csv`
- [x] `P1` Bo sung export theo `form_row` ro rang trong FORM
- [x] `P2` Chay lai unit test
- [x] `P2` Chay lai E2E
- [x] `P3` Cap nhat `QUY_TRINH_NGHIEP_VU_MP2027.md`
- [x] `P3` Cap nhat `.brain`
- [x] `P3` Dong goi lai `dist/MP2027_Manager.exe`

## 3. P1 con mo that su

- [ ] `P1` Bo sung du lieu that cho `docs/MP2027/headcount_manual.csv`
Can co:
  - CC `1412000089`
  - 12 thang `headcount_staff`
  - 12 thang `headcount_worker`
  - neu can health check: `headcount_male`, `headcount_female`
Anh huong:
  - neu khong co, cac row hanh chinh tinh theo so nguoi cua CC nay van de trong

- [ ] `P1` Bo sung du lieu that cho `docs/MP2027/special_costs_manual.csv`
Can co:
  - `cc_code, period, form_row, account_code, amount_vnd, description`
Anh huong:
  - neu khong co, row NNN/VISA/GPLD/Passport trong FORM se trong

- [ ] `P1` Chot row dich cho `Company anniversary`
Code dich: `src/engine/hub_builder.py`, `src/engine/allocator.py`
Ly do con mo:
  - workbook yeu cau va bo MP2026 khong cho quy tac text/row map day du

- [ ] `P1` Chot row dich cho `Qua tang cho CNV khong the tham gia du lich`
Code dich: `src/engine/hub_builder.py`
Ly do con mo:
  - hien item nay van append o vung `200+`
  - chua co row FORM duoc xac nhan bang tai lieu

- [ ] `P1` Chot 2 muc chi mo ta bang hinh trong sheet `Hang muc can cai tien`
Code dich: `src/engine/hub_builder.py`
Hai muc:
  - `Khong can dien 2 du lieu duoi vao file`
  - `Day cac cot du lieu ve dung cot chi mui ten`
Ly do con mo:
  - chua co bang map text 1-1, hien chi thay mo ta/anh

## 4. P2 con mo

- [ ] `P2` Neu nguoi dung muon IT bung theo tung he thong thay vi row tong `75`, can cung cap map row dich ro rang tren FORM
Code dich: `src/parsers/it_sim.py`, `src/engine/hub_builder.py`

- [ ] `P2` Neu can "boi lai dung mau", can chi ro nhung o/row nao phai repaint
Code dich: `src/engine/hub_builder.py`

## 5. Kiem chung moi nhat

- [x] `P2` `python -m unittest tests.test_src_v2_logic tests.test_posting_month_logic tests.test_headcount_and_export`
- [x] `P2` `python scripts\\run_e2e.py --fy 2027 --template docs\\MP2027\\FORM.xlsx --source docs\\MP2027 --target-cc 1412000089`
- [x] `P2` Query DB xac nhan khong con allocation `alloc_%` nao cho `VISA/Passport/GPLD/NNN`
- [x] `P3` `python scripts\\package_app.py`

## 6. File ban giao hien tai

- [x] `P3` Output moi: `OUTPUT_FY2027/MP_CC_1412000089.xlsx`
- [x] `P3` EXE moi: `dist/MP2027_Manager.exe`
