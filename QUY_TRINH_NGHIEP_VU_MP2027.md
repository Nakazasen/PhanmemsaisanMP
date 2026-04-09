# QUY TRINH NGHIEP VU MP2027

Ngay cap nhat: `2026-04-09`

Tai lieu nay phan anh dung trang thai hien tai sau khi:
- doc lai workbook yeu cau `docs/MP2027/Cai tien nhap du lieu chung vao file MP.xlsx`
- doi chieu 3 sheet mau do:
  - `Hang muc can cai tien`
  - `Chi phi phan bo tu hanh chinh `
  - `Chi phi lam giay to cho NNN`
- doi chieu them bo tham chieu da duoc kiem duyet trong `docs/MP2026`
- chay lai test, E2E va dong goi lai chuong trinh

## 0. Tom tat doi thuong de nguoi moi doc la hieu

Neu bo qua het phan ky thuat, co the hieu chuong trinh nay rat don gian nhu sau:

- Dau vao la mot bo file Excel nghiep vu ma cac bo phan dang dung de lap Master Plan.
- Dau ra la file MP cho tung Cost Center, duoc dien san vao dung `FORM.xlsx`.
- Muc tieu cua chuong trinh la giam nhap tay, nhung van giu nguyen bo cuc, cong thuc va format cua file MP goc.

No dang lam 4 viec chinh:

1. Doc cac file nguon
- file facility
- file fixed assets
- file he thong IT
- file hanh chinh / tong vu
- file rules

2. Chuan hoa du lieu
- dua tat ca vao database tam de tinh toan
- doi chieu Cost Center, account code, thang phat sinh

3. Tinh chi phi
- co nhom lay truc tiep tu file nguon
- co nhom tinh theo quy tac nhu `so nguoi * don gia`
- co nhom tinh theo thang phat sinh nhu `thang 5`, `thang 9`, `thang 2`
- co nhom phai cho du lieu su kien thuc te, khong duoc tu do tinh

4. Do vao FORM
- ghi vao dung row co dinh neu da biet row dich
- neu chua biet row dich thi tam append xuong duoi
- tuyet doi khong duoc pha cong thuc va format san co cua FORM

### Chuong trinh da lam duoc den muc nao

Den hien tai, phan mem da lam duoc phan lon xuong pipeline:
- doc dung bo nguon `docs/MP2027`
- xuat duoc file MP cho CC mau
- da sua duoc cong thuc chi phi he thong
- da lam duoc nhom chi phi hanh chinh recurring theo dau nguoi
- da lam duoc khung xu ly cho chi phi giay to nguoi nuoc ngoai

Noi ngan gon:
- engine da san sang
- van con mot so cho trong output vi thieu du lieu that cua nguoi dung nghiep vu

### Vi sao chua the goi la xong 100 phan tram

Khong phai vi code chua biet lam, ma chu yeu vi thieu 3 loai thong tin:

1. Headcount that theo 12 thang cua mot so CC
- khong co thi cac dong tinh theo `so nguoi * don gia` se khong ra so dung

2. Chi phi su kien thuc te cho nguoi nuoc ngoai
- visa
- passport
- GPLD
- the tam tru
- cac chi phi giay to lien quan

3. Xac nhan nghiep vu cho vai hang muc chua ro row dich
- `Company anniversary`
- `Qua tang cho CNV khong the tham gia du lich`

### Neu la lap trinh vien moi tiep quan du an

Chi can nho 5 y:

1. Dung `docs/MP2027` lam nguon chuan, khong dung `FORM.xlsx` o root repo.
2. `QUY_TRINH_NGHIEP_VU_MP2027.md` la file doc tong quan truoc.
3. `TODO_MP2027_OPEN_ITEMS.md` la file xem viec con ton.
4. Neu mot chi phi la nghiep vu su kien thuc te, khong duoc tu y suy ra tu headcount.
5. Uu tien dung row co dinh cua FORM; chi append khi chua co row dich duoc xac nhan.

## 1. Nguon chuan phai dung

Tu dot cap nhat nay, chuong trinh coi `docs/MP2027` la bo nguon chuan:
- `docs/MP2027/FORM.xlsx`
- `docs/MP2027/FY2027配賦額一覧 (2025.12.29).xlsx`
- `docs/MP2027/総務課 FY2027 MP 振替予定.xlsx`
- `docs/MP2027/システム課金金額(Simulation)_*.xls`
- `docs/MP2027/headcount_manual.csv`
- `docs/MP2027/special_costs_manual.csv`

Bo `docs/MP2026` chi dung lam nguon doi chieu nghiep vu da duoc kiem duyet, khong phai bo input runtime.

Luu y quan trong:
- `docs/MP2027/FORM.xlsx` trung SHA voi `docs/MP2026/FORM.xlsx`
- `FORM.xlsx` o root repo la ban cu hon, con sample/formula gia o mot so row; khong duoc dung lam template chuan nua

## 2. Pham vi nghiep vu dang theo

Theo xac nhan moi nhat cua nguoi dung:
- Sheet `Hang muc can cai tien`:
  - cac dong toi `108` duoc coi la da dung
  - can audit lai cac dong `109-137`
- Hai sheet moi can xu ly nghiep vu:
  - `Chi phi phan bo tu hanh chinh `
  - `Chi phi lam giay to cho NNN`

## 3. Trang thai ky thuat hien tai

### 3.1. Loader va master data

- `src/db/loader.py` da uu tien nap file trong `docs/MP2027`
- Rule loader da parse duoc don gia dang:
  - so thuong
  - so co dau phay
  - chuoi co hau to `$` nhu `145$`
- So rule hien dang nap duoc: `66`

### 3.2. Allocation engine

- `src/engine/allocator.py` da:
  - xu ly dung cac token posting month nghiep vu nhu `入社月`, `配布月`, `申請月`, `取得月`, `翌月`
  - xu ly driver `headcount_all`, `staff`, `worker`, `male`, `female`, `working_days`
  - bo qua cac item NNN/VISA/GPLD/Passport can nguon su kien thu cong
- Muc dich cua viec bo qua tren:
  - tranh auto-allocate sai cac chi phi `取得月`
  - tranh xuat row passport/VISA/GPLD bang cong thuc headcount khong dung nghiep vu

### 3.3. Export FORM

- `src/engine/hub_builder.py` da:
  - dung `docs/MP2027/FORM.xlsx` lam template mac dinh
  - clear sample formula/so mau o cac vung row duoc quan ly:
    - `38-90`
    - `93-109`
    - `111-152`
  - chi ghi lai neu co du lieu that
  - ho tro ghi thang vao `form_row` cu the tu `fact_input_data`
  - khong append lai cac muc da co row dich ro rang

### 3.4. Bo parser bo sung

- `src/parsers/it_sim.py`
  - doc duoc `system total`
  - doc duoc chi tiet `VPN`, `Mail`, `R3`, `MES`, `PLM`, `QLIK`, `VPS`, `AMS`
- `src/parsers/manual_special_costs.py`
  - doc file thu cong `docs/MP2027/special_costs_manual.csv`
  - cho phep nap truc tiep chi phi vao row dich cu the trong FORM
- `scripts/run_e2e.py` va `src/universal_app.py`
  - deu da uu tien `docs/MP2027` lam template/source mac dinh

## 4. Audit ket qua cho dong 109-137

### 4.1. Dong 117 - "Chi phi he thong chua lay duoc cong thuc, van la dang so"

Trang thai: `DA XONG`

Da lam duoc:
- parser IT doc duoc tong he thong va tung component
- row `75` trong output khong con la so chep phang
- row `75` duoc ghi bang cong thuc tong hop tu component IT

Ket luan:
- yeu cau "khong de dang so, phai co cong thuc" da dat
- phan chua lam 100% chi con neu muon bung IT thanh nhieu row rieng tren FORM; workbook yeu cau hien khong cho bang map row dich 1-1 cho tung he thong

### 4.2. Dong 127 - "Sua lai doi tuong ap dung va cong thuc tinh tien phan bo tu hanh chinh"

Trang thai: `DA LAM DUOC PHAN LON, CON BLOCKER DU LIEU`

Da lam duoc:
- `Gas`, `Cleaning`, `Hand wash`, `Toilet paper` da xuat theo cong thuc `so nguoi * don gia`
- cong thuc da dung headcount thang truoc theo huong dan hanh chinh; rieng thang 4 dung thang 4
- da co fixed-row export cho cac nhom chinh:
  - `Company trip`
  - `Kickoff party`
  - `Kyocera festival`
  - `Moon cake`
  - `Sports day`
  - `Year-end party subsidy`
  - `New year gift`
  - `Health check male/female`
  - `employee card/photo/philosophy/card case/pen/note`
- da co headcount manual 12 thang va driver `Nam/Nu` cho health check
- da co posting-month override cho cac item co thang phat sinh dac thu

Con block:
- `docs/MP2027/headcount_manual.csv` chua co dong nao cho CC `1412000089`
  - he qua: cac row hanh chinh tinh theo so nguoi cua CC nay van trong
- rules workbook hien tai co `unit_price = 0` cho:
  - `Moon cake`
  - `Sports day`
- chua tim thay quy tac text day du cho:
  - `Company anniversary`
  - row co dinh cua `Qua tang cho CNV khong the tham gia du lich`
- hai muc trong sheet yeu cau chi mo ta bang hinh, chua co map text 1-1:
  - `Khong can dien 2 du lieu duoi vao file`
  - `Day cac cot du lieu ve dung cot chi mui ten`

### 4.3. Dong 133 - "Bo sung them 1 loai chi phi moi: Chi phi lam giay to cho nguoi nuoc ngoai"

Trang thai: `ENGINE DA SAN SANG, THIEU DU LIEU NGUON`

Da lam duoc:
- engine khong con auto-allocate sai cac chi phi NNN/VISA/GPLD theo headcount
- da bo sung parser `manual_special_costs`
- da bo sung co che ghi vao row dich cu the trong FORM thong qua cot `form_row`
- `docs/MP2027/special_costs_manual.csv` da duoc tao san lam file nhap ngu lieu

Con thieu:
- hien chua co du lieu thuc te FY2027 de nap vao `special_costs_manual.csv`
- sheet `Chi phi lam giay to cho NNN` chi mo ta cach tinh, khong chua bang chi phi event thuc te

File dang can nguoi dung/nguon du lieu bo sung:
- `docs/MP2027/special_costs_manual.csv`

Dinh dang can nhap:
- `cc_code`
- `period`
- `form_row`
- `account_code`
- `amount_vnd`
- `description`

## 5. MP2026 da giup xac nhan duoc gi

Bo `docs/MP2026` da xac nhan them:
- cong thuc recurring admin cua `Gas`, `Hand wash`, `Toilet paper`, `Cleaning` la nghiep vu phan bo theo dau nguoi/ngay
- `docs/MP2026/FORM.xlsx` giong `docs/MP2027/FORM.xlsx`

Bo `docs/MP2026` KHONG cung cap them:
- du lieu su kien NNN/VISA/GPLD cho FY2027
- row dich ro rang cho `Company anniversary`
- row dich ro rang cho `Qua tang cho CNV khong the tham gia du lich`

## 6. Kiem chung moi nhat

Da chay:

```bash
python -m unittest tests.test_src_v2_logic tests.test_posting_month_logic tests.test_headcount_and_export
python scripts\run_e2e.py --fy 2027 --template docs\MP2027\FORM.xlsx --source docs\MP2027 --target-cc 1412000089
python scripts\package_app.py
```

Ket qua:
- `16 tests OK`
- load `62` cost centers
- load `239` accounts
- load `66` allocation rules
- manual headcount: co file template nhung chua co du lieu that cho CC `1412000089`
- manual special cost: parser chay duoc, hien inserted `0` vi chua co data that
- E2E xuat thanh cong:
  - `OUTPUT_FY2027/MP_CC_1412000089.xlsx`
- Dong goi thanh cong:
  - `dist/MP2027_Manager.exe`

Kiem tra them tren DB:
- khong con `alloc_%` nao cho mo ta `VISA/Passport/GPLD/NNN`
- ket qua query hien tai: `0 rows`

## 7. Blocker du lieu con lai

### 7.1. Headcount that cho CC 1412000089

File thieu du lieu:
- `docs/MP2027/headcount_manual.csv`

Can bo sung:
- 12 thang `headcount_staff`
- 12 thang `headcount_worker`
- neu can health check thi can them:
  - `headcount_male`
  - `headcount_female`

### 7.2. Chi phi lam giay to cho NNN

File thieu du lieu:
- `docs/MP2027/special_costs_manual.csv`

Can bo sung:
- tung su kien thuc te FY2027 theo CC, thang, row FORM, account, so tien

Neu khong dung file CSV thu cong thi can workbook nguon chinh thuc co cung thong tin tren.

## 8. Ket luan thuc te

Khong duoc noi la "da xong 100%" vi van con blocker du lieu that.

Mo ta dung trang thai hien tai:
- da hoan tat phan nen ky thuat cho 3 sheet mau do
- da xong phan cong thuc he thong
- da xong phan lon logic hanh chinh
- da mo san duong nap du lieu cho NNN
- cac phan chua xuat day du hien nay chu yeu do thieu du lieu nguon hoac thieu map row text ro rang tu workbook yeu cau

## 9. File can mo dau tien neu tiep tuc

Thu tu doc lai de tiep tuc:
1. `QUY_TRINH_NGHIEP_VU_MP2027.md`
2. `TODO_MP2027_OPEN_ITEMS.md`
3. `docs/MP2027/Cai tien nhap du lieu chung vao file MP.xlsx`
4. `docs/MP2027/FORM.xlsx`
5. `OUTPUT_FY2027/MP_CC_1412000089.xlsx`
