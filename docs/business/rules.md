# Business Rules - MP2027 Manager

Tai lieu nay tach bach 2 khia canh:
- `Business rule mong muon`
- `Implementation status hien tai`

Muc tieu la tranh nham lan giua "quy tac nghiep vu dung" va "code hien tai da lam duoc gi".

Ngay cap nhat: `2026-03-23`.

## 1. Fiscal year

### Business rule

- Ky tai chinh bat dau tu thang `4` va ket thuc vao thang `3` nam sau.
- Moi du lieu theo thang phai duoc quy ve period `YYYYMM`.

### Current status

- Da implemented.
- Da duoc dung trong parsers va export.

## 2. Cost center classification

### Business rule

Tai khoan dich phai duoc chon theo `cost_type` cua Cost Center:
- nhom san xuat dung `mfg_code`
- nhom gian tiep/van phong dung `ga_code`
- nhom ban hang dung `sales_code`

### Current status

- Da implemented cho direct-cost mapping.
- Chua du bang chung de ket luan allocation phan bo hanh chinh da di den dung CC dich trong moi truong hop.

## 3. Direct-cost ingestion

### Business rule

Can lay du lieu tu:
- Facility
- IT Simulation
- Fixed Assets
- GA don gia co san

Sau do map vao hub data de export vao `FORM.xlsx`.

### Current status

- Da implemented.
- Da chay duoc trong E2E.
- Da xac minh co du lieu thuc te trong `fact_input_data`.

## 4. Fixed assets month-end rule

### Business rule

Voi chi phi tai san co dinh:
- cac thang truoc `last depreciation month`: ghi gia tri binh thuong
- tai `last depreciation month`: ghi gia tri cot thang cuoi cung
- sau thang cuoi cung: khong ghi

Voi lai:
- thang 4 dung cot lai thang 4
- tu thang 5 tro di dung cot lai tu thang 5 tro di
- sau thang cuoi cung: khong ghi

### Current status

- Da co implementation trong parser fixed assets.
- Can tiep tuc doi chieu chi tiet voi workbook nghiep vu de xac nhan khong sot case ngoai le.

## 5. Administrative allocation drivers

### Business rule

He thong phai ho tro cac driver:
- `headcount_all`
- `headcount_staff`
- `headcount_worker`
- `working_days`

`headcount_staff` va `headcount_worker` la bat buoc vi co nhieu rule don gia khac nhau cho staff va worker.

### Current status

- Driver da duoc load mot phan vao DB.
- Chua duoc xac minh thong suot tu workbook GA den allocation output.
- Gap lon hien tai: monthly headcount tu GA chua match khoa Cost Center master.

## 6. Posting month

### Business rule

Khong phai moi allocation rule deu ap dung cho tat ca 12 thang.

He thong phai ton trong `posting_month`, bao gom cac gia tri:
- moi thang
- thang vao lam
- thang phat/cap
- thang tiep theo sau vao lam
- thang co dinh `7`, `10`, `11`, `12`, `2`
- thang ghi nhan tai san
- thang de nghi
- khong co thang co dinh

### Current status

- Rule da duoc load vao `map_allocation_rules`.
- Chua duoc xac minh la allocator dang ton trong `posting_month`.
- Ket qua kiem DB sau E2E cho thay allocation rows chua xuat hien trong output cuoi.

## 7. Working days

### Business rule

Mot so rule phai tinh theo so ngay lam viec thuc te cua tung thang.

Nguon su that:
- GA workbook
- doi chieu voi sheet working days trong `FORM.xlsx` neu can

### Current status

- Gia tri `working_days_YYYYMM` da duoc nap vao `sys_params`.
- Chua co bang chung day du rang allocator dang dung gia tri nay nhu mot driver rieng.

## 8. Excel integrity

### Business rule

He thong chi duoc ghi du lieu vao sheet hub cua `FORM.xlsx`.

Khong duoc:
- pha format
- xoa cong thuc
- ghi de vao cac sheet bao cao tong hop

### Current status

- Da implemented theo huong hub-and-spoke.
- E2E da export duoc file.
- Chua co bo test tu dong de kiem tra formula integrity sau moi lan thay doi code.

## 9. Idempotency

### Business rule

Chay lai pipeline nhieu lan phai cho ra ket qua nhat quan, khong nhan ban du lieu master hay allocation.

### Current status

- `fact_input_data` duoc xoa truoc khi parse lai trong E2E.
- `map_allocation_rules` chua idempotent qua nhieu lan chay.
- Day la gap can sua som.

## 10. Rule for status labeling

Chi duoc gan nhan `verified` khi:
- da co workbook doi chieu
- da co command/test da chay
- da co bang chung trong DB hoac output file

Neu thieu mot trong ba dieu kien tren, nen dung:
- `implemented`
- `partially verified`
- `pending verification`
