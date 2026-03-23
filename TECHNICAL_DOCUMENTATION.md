# TECHNICAL DOCUMENTATION - MP2027 Manager

Tai lieu nay mo ta he thong o goc nhin ky thuat, dong thoi ghi ro cac gioi han da duoc xac minh thuc te. Muc tieu la de nguoi bao tri hieu dung trang thai code, thay vi dua vao mo ta "da hoan tat" khong con phu hop.

## 1. Kien truc tong quan

He thong gom 5 lop:

### 1. GUI Layer

File chinh:

- `src/universal_app.py`

Nhiem vu:

- nhan tham so tu nguoi dung
- goi pipeline E2E
- hien log

### 2. Orchestration Layer

File chinh:

- `scripts/run_e2e.py`

Nhiem vu:

- tao va khoi tao database
- load master data
- chay parsers
- chay allocation
- export ra file MP theo tung Cost Center

### 3. Ingestion Layer

Thu muc:

- `src/parsers/`

Module:

- `facility.py`
- `fixed_assets.py`
- `it_sim.py`
- `ga.py`
- `manual_headcount.py`

Nhiem vu:

- doc workbook nguon
- chuyen du lieu ve bang chung trong SQLite
- quy doi USD/VND neu can
- dua cac direct costs vao `fact_input_data`
- dua driver phan bo vao cac bang helper
- cho phep nguoi dung nhap `headcount_staff/headcount_worker` bang file CSV thu cong

Tai lieu thao tac:

- `docs/MANUAL_HEADCOUNT_INPUT.md`

### 4. Logic Layer

Thu muc:

- `src/engine/`

Module:

- `allocator.py`
- `hub_builder.py`

Nhiem vu:

- map direct cost vao tai khoan dich
- tinh allocation theo rule
- tong hop va ghi ra sheet hub cua `FORM.xlsx`

### 5. Storage Layer

File:

- `data/mp2027.db`

Bang quan trong:

- `dim_cost_centers`
- `dim_accounts`
- `map_allocation_rules`
- `fact_input_data`
- `fact_monthly_headcount`
- `sys_params`

## 2. Data flow hien tai

Data flow dung theo thu tu:

1. `run_e2e.py`
2. `load_all()`
3. `parse_facility()`
4. `parse_ga()`
5. `parse_it_simulation()`
6. `parse_fixed_assets()`
7. `AllocationEngine.run_allocation()`
8. `HubBuilder.export_to_template()`

## 3. Nhung gi da duoc xac minh la chay

Tại thoi diem doi chieu `2026-03-23`, da xac minh:

- import smoke cua module chinh pass
- `py -m pytest tests\\test_src_v2_logic.py -q` pass
- `py scripts\\run_e2e.py --fy 2027 --template FORM.xlsx --source .` pass
- pipeline sinh `62` file trong `OUTPUT_FY2027`

So lieu log mot lan chay:

- `Loaded 62 cost centers`
- `Loaded 239 accounts`
- `Loaded 50 allocation rules`
- `Facility total: 4584 records inserted`
- `IT Simulation total: 1992 records`
- `Mapped 14971 direct cost records`

## 4. Known gaps da xac minh

Day la phan quan trong nhat cua tai lieu nay.

### 4.1. Allocation nghiep vu hanh chinh chua xac minh thanh cong

Quan sat database sau khi chay E2E cho thay:

- `fact_input_data` khong co dong `source like 'alloc_%'`

Y nghia:

- allocation rule hien chua tao ra output thuc su
- direct-cost pipeline van chay
- nhung business rule tu file quy tac phan bo FY2027 chua duoc the hien day du trong ket qua

### 4.2. GA monthly headcount chua match master Cost Center

Da thay monthly headcount ghi vao DB voi ma nhu:

- `1136`
- `40237000`

Trong khi `dim_cost_centers` dung ma nhu:

- `1412000004`
- `1412000005`

Y nghia:

- allocator khong the join dung headcount theo CC dich

### 4.3. `posting_month` la rule nghiep vu bat buoc nhung chua duoc ton trong day du

Workbook rule co cac gia tri:

- moi thang
- thang vao lam
- thang phat/cap
- thang tiep theo sau vao lam
- thang co dinh `7`, `10`, `11`, `12`, `2`
- thang ghi nhan tai san
- thang de nghi

Neu code khong ton trong truong nay, output co the sai du gia tri tong van nhin co ve hop ly.

### 4.4. `working_days` can duoc xu ly rieng

Trong nghiep vu, `working_days` khong phai headcount.
Neu he thong tinh `working_days` thong qua ham lay headcount, phep tinh sai ban chat.

### 4.5. `map_allocation_rules` chua idempotent

Bang rule dang bi tich luy qua nhieu lan chay.

Da xac minh:

- tong so dong trong DB: `1350`
- so signature khac nhau: `50`

Nguyen nhan:

- moi lan load lai rules, code insert them
- `run_e2e.py` khong xoa bang `map_allocation_rules` truoc khi load

## 5. Huong dan danh gia trang thai he thong

Khi nguoi doc can danh gia xem he thong da san sang hay chua, khong nen hoi:

- pipeline co chay hay khong

Ma phai hoi dong thoi:

- direct cost da vao dung chua
- allocation da sinh ra dung chua
- posting month da dung chua
- working days da dung driver chua
- headcount da join dung master CC chua

Neu chi E2E pass ma cac cau hoi tren chua pass, khong duoc ket luan la dung nghiep vu 100%.

## 6. Thu tu sua ky thuat de dong gap

1. Sua parser GA de xac dinh dung khoa Cost Center.
2. Sua allocator de xu ly `posting_month`.
3. Tach driver `working_days` khoi logic headcount.
4. Lam `map_allocation_rules` idempotent.
5. Viet test bao phu cho allocation theo thang va theo driver.

## 7. Quy uoc cap nhat tai lieu

Moi khi danh dau mot muc la `verified`, can co:

- command da chay
- workbook da doi chieu
- ket qua DB hoac output file da kiem

Neu khong co 3 thanh phan tren, chi nen ghi:

- `implemented`
- `partially verified`
- hoac `pending validation`
