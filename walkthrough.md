# MP2027 Manager - Walkthrough and Current Status

Tai lieu nay tom tat trang thai thuc te cua du an sau dot doi chieu workbook nghiep vu, code hien tai, va ket qua chay thu ngay `2026-03-23`.

No khong phai tai lieu marketing. Muc tieu la de nguoi doc nhin thay ro:

- he thong dang lam duoc gi
- he thong chua lam duoc gi
- can sua tiep o dau

## 1. Ket qua xac minh thuc te

Da thuc hien cac buoc sau:

- doc workbook yeu cau tong
- doc cac workbook nguon thuc te trong thu muc project
- doi chieu voi code hien tai trong `src/`
- chay test:
  - `py -m pytest tests\\test_src_v2_logic.py -q`
- chay E2E:
  - `py scripts\\run_e2e.py --fy 2027 --template FORM.xlsx --source .`

Ket qua:

- `3` test hien co pass
- import smoke cua cac module chinh pass
- E2E chay het
- sinh `62` file trong `OUTPUT_FY2027`

## 2. Nhung gi da hoat dong

### Master data

- doc duoc `62` Cost Centers tu `FORM.xlsx`
- doc duoc `239` accounts tu `FORM.xlsx`
- doc ty gia USD/VND tu `FORM.xlsx!B2`

### Direct-cost parsers

Sau mot lan chay E2E:

- `facility`: `4584` dong
- `fixed_assets`: `9846` dong
- `it_sim`: `1992` dong
- `ga_unit_price`: `72` dong

### Export

- batch export sinh duoc `62` file MP theo Cost Center
- file dich la `FORM.xlsx`
- sheet hub duoc ghi de Excel cong thuc tinh tiep

## 3. Nhung gi chua dung voi yeu cau 100%

### Allocation tu hanh chinh chua di vao output

Sau khi chay full E2E, `fact_input_data` khong co dong nao co `source like 'alloc_%'`.

Y nghia:

- direct-cost da vao
- nhung chi phi phan bo theo rule hanh chinh chua duoc tao thanh ket qua cuoi

### Monthly headcount GA dang lech khoa Cost Center

Da ghi nhan monthly headcount voi cac ma khong match master, vi du:

- `1136`
- `40237000`

Trong khi master tai `FORM.xlsx` dung ma 10 chu so nhu `1412000004`.

Y nghia:

- driver nhan su khong join duoc voi master CC
- allocation theo nhan su co the mat tac dung

### Posting month chua duoc xac minh la duoc ton trong

Workbook rule co cac gia tri `posting_month` nhu:

- moi thang
- thang vao lam
- thang phat/cap
- thang tiep theo sau vao lam
- thang co dinh `7`, `10`, `11`, `12`, `2`

Neu allocator khong xu ly dung gia tri nay, ket qua nghiep vu van sai du pipeline chay xong.

### Driver `working_days` can duoc xu ly rieng

Trong nghiep vu goc, mot nhom chi phi tinh theo so ngay lam viec.
Neu phan nay bi truot sang logic headcount, phep tinh se sai ban chat.

### Rule master chua idempotent

Trong log cua mot lan chay:

- `Loaded 50 allocation rules.`

Nhung database hien tai ghi nhan:

- `1350` dong `map_allocation_rules`
- chi co `50` signature thuc su khac nhau

Y nghia:

- bang rule dang bi tich luy qua nhieu lan chay

## 4. Cach dien giai dung khi ban giao

Khong nen mo ta he thong hien tai la:

- `100% complete`
- `clean & verified`
- `ready for production handover`

Nen mo ta dung hon:

- direct-cost ingestion da chay va export duoc
- E2E pipeline da thong
- allocation nghiep vu hanh chinh chua duoc xac minh dat yeu cau goc
- can xu ly tiep khoa CC, posting month, working-days driver, va idempotency cua rule table

## 5. Thu tu sua tiep de dong gap

1. Sua parser GA de khoa Cost Center trung voi `FORM.xlsx`.
2. Sua allocator de ton trong `posting_month`.
3. Xu ly `working_days` nhu mot driver rieng.
4. Lam `map_allocation_rules` idempotent qua nhieu lan chay.
5. Chay doi chieu theo tung sheet trong workbook huong dan nghiep vu tong.

## 6. Trang thai de xuat hien tai

Trang thai de xuat:

- `E2E runnable`
- `Direct-cost pipeline verified`
- `Administrative allocation incomplete`
- `Business-rule alignment pending`

Day la cach ghi trang thai sat thuc te nhat o thoi diem hien tai.
