# QUY TRINH NGHIEP VU MP2027

Tai lieu nay mo ta workflow nghiep vu thuc te cua du an MP2027, theo cach dung de ban giao cho nguoi dung, nguoi van hanh, va nguoi tiep tuc phat trien chuong trinh.

No dong thoi phan biet ro:
- `Mong muon nghiep vu`
- `Nguon du lieu goc`
- `Workflow xu ly dung`
- `Trang thai trien khai hien tai`
- `Van de con ton tai can lam ro khi ban giao`

Ngay doi chieu tai lieu nay: `2026-03-23`.

## 1. Muc tieu nghiep vu

Muc tieu cua he thong MP2027 la tu dong dua cac chi phi chung vao file `FORM.xlsx`, de tao bo file Master Plan cho tung Cost Center trong ky tai chinh `FY2027`.

Ky tai chinh duoc tinh theo chu ky:
- Thang 4 nam truoc den thang 3 nam sau
- Luu tru noi bo theo dinh dang `YYYYMM`
- Vi du `FY2027` tuong ung chu ky `202604` den `202703`

He thong can thay the quy trinh lam tay:
- mo nhieu file Excel nguon
- loc theo Cost Center
- doi chieu tai khoan
- tinh chi phi theo cong thuc
- nhap vao sheet hub cua `FORM.xlsx`
- giu nguyen cong thuc va format cua file mau

## 2. Nguon yeu cau nghiep vu goc

Nguon yeu cau goc khong nam trong code, ma nam trong workbook:
- file huong dan nghiep vu tong `Cai tien nhap du lieu chung vao file MP.xlsx`

Workbook nay mo ta mong muon cua nguoi dung cho 4 nhom du lieu:
- `Chi phi he thong`
- `Chi phi khau hao, lai nha dat, dien nuoc`
- `Chi phi tai san co dinh`
- `Chi phi phan bo tu hanh chinh`

Ngoai ra, cac workbook du lieu nguon duoc dung de tong hop la:
- `FORM.xlsx`
- file quy tac phan bo FY2027
- file Facility MPFY2027
- file GA FY2027 MP
- file Fixed Assets Information 2025.11 - Nov
- 3 file IT Simulation cho cac giai doan Apr-Jun, Jul-Dec, Jan-Mar

## 3. Dich vu nghiep vu can thuc hien

### 3.1. Master data

He thong phai doc tu `FORM.xlsx`:
- danh muc Cost Center
- danh muc tai khoan
- sheet hub de ghi du lieu
- ty gia USD/VND tai o `B2`
- so ngay lam viec tieu chuan theo thang neu can doi chieu

Y nghia nghiep vu:
- `FORM.xlsx` la file dich
- mapping tai khoan va Cost Center phai nhat quan voi file nay
- ty gia B2 duoc xem la nguon su that cho quy doi USD sang VND

### 3.2. Chi phi he thong

Nguon: 3 file IT Simulation `.xls`.

Mong muon nghiep vu:
- doc chi phi theo tung he thong nhu VPN, Mail, R3, MES, PLM, AMS
- lay dung Cost Center va tai khoan chi phi
- tong hop theo tung giai doan thang:
  - `202604-202606`
  - `202607-202612`
  - `202701-202703`

### 3.3. Chi phi khau hao, lai nha dat, dien nuoc

Nguon: file Facility MPFY2027.

Mong muon nghiep vu:
- khau hao nha va dat: quy doi USD sang VND theo `FORM.xlsx!B2`
- lai nha dat: quy doi USD sang VND theo `FORM.xlsx!B2`
- dien nuoc: copy gia tri VND
- ap dung cho tat ca thang trong FY

Luu y nghiep vu tu workbook huong dan:
- khi loc bang tay co the bi mat dong dat hoac dong lai dat
- khi tu dong hoa can tranh logic loc qua chat lam roi dong

### 3.4. Chi phi tai san co dinh

Nguon: file Fixed Assets Information 2025.11 - Nov.

Mong muon nghiep vu:
- loc theo `code phong chiu chi phi`
- lay chi phi khau hao va lai
- quy doi USD sang VND theo `FORM.xlsx!B2`
- xet `thang khau hao cuoi cung`

Quy tac dung:
- neu `thang khau hao cuoi cung` nam sau ky FY, thi cac thang trong FY van ghi binh thuong
- neu `thang khau hao cuoi cung` nam trong ky FY:
  - cac thang truoc thang cuoi cung: ghi gia tri binh thuong
  - tai thang cuoi cung: ghi gia tri cot `chi phi khau hao cua thang cuoi cung`
  - sau thang cuoi cung: khong ghi nua
- doi voi lai:
  - thang 4 dung cot lai thang 4
  - tu thang 5 tro di dung cot lai tu thang 5 tro di
  - sau thang cuoi cung: khong ghi nua

### 3.5. Chi phi phan bo tu hanh chinh

Nguon nghiep vu:
- file huong dan nghiep vu tong
- file quy tac phan bo FY2027
- file GA FY2027 MP

Day la nhom nghiep vu phuc tap nhat.

He thong can ho tro:
- phan bo theo `tong so nguoi`
- phan bo theo `staff`
- phan bo theo `worker`
- phan bo theo `so ngay lam viec`
- phan bo theo `thang phat sinh`

`Thang phat sinh` trong file rule khong chi la `moi thang`, ma con co:
- thang vao lam
- thang phat/cap
- thang tiep theo sau thang vao lam
- moi thang
- thang co dinh nhu `7`, `10`, `11`, `12`, `2`
- cac gia tri dac thu khac nhu thang ghi nhan tai san, thang de nghi, hoac khong co thang co dinh

Y nghia nghiep vu:
- khong phai moi rule deu sinh chi phi cho du 12 thang
- he thong phai ton trong `posting_month`
- mot so rule can theo so nguoi bien dong theo thang
- mot so rule can theo `working_days`
- mot so rule can tach `staff` va `worker` vi don gia khac nhau

## 4. Workflow nghiep vu dung tu dau den cuoi

### Buoc 1. Nap master

Doc tu `FORM.xlsx`:
- Cost Center
- tai khoan
- ty gia B2
- cau truc sheet hub

### Buoc 2. Nap du lieu direct cost

Doc cac workbook nguon:
- Facility
- IT Simulation
- Fixed Assets
- GA don gia thang

Nap vao database staging voi `account_code = 0` neu chua map ngay.

### Buoc 3. Map direct cost vao tai khoan dich

Can map theo:
- loai chi phi
- nhom tai khoan
- loai Cost Center nhan chi phi

Va chon dung cot:
- `mfg_code`
- `ga_code`
- `sales_code`

### Buoc 4. Nap driver phan bo

Can co du lieu:
- monthly headcount theo CC
- tach `headcount_all`, `headcount_staff`, `headcount_worker`
- working days theo thang

### Buoc 5. Chay allocation rule

Voi tung rule trong file quy tac phan bo FY2027:
- xac dinh `driver_type`
- xac dinh `posting_month`
- xac dinh CC nhan chi phi
- tinh `amount = driver x don gia`
- ghi vao hub data

### Buoc 6. Export ra file MP

Lay du lieu da map va allocation tu database, ghi vao:
- sheet hub `Noi yaku list 4-3` cua `FORM.xlsx`

Yeu cau:
- khong pha format
- khong sua cong thuc o cac sheet bao cao
- chi ghi vao hub sheet

## 5. Trang thai trien khai hien tai da xac minh

Kiem chung thuc te ngay `2026-03-23` cho thay:

### Da xac minh la chay duoc

- import smoke cua cac module chinh pass
- test hien co pass:
  - `tests/test_src_v2_logic.py`
- pipeline chay het:
  - `py scripts/run_e2e.py --fy 2027 --template FORM.xlsx --source .`
- ket qua:
  - load `62` Cost Centers
  - load `239` accounts
  - load `50` allocation rules trong mot lan chay
  - parser `facility` sinh `4584` dong
  - parser `it_sim` sinh `1992` dong
  - parser `fixed_assets` sinh `9846` dong
  - parser `ga_unit_price` sinh `72` dong
  - export batch duoc `62` file trong `OUTPUT_FY2027`

### Chua du dieu kien ket luan la dung 100%

Ly do:
- direct-cost pipeline da chay
- nhung allocation theo nghiep vu hanh chinh chua duoc xac minh la da di vao output dung cach

## 6. Van de nghiep vu dang gap da xac minh

### 6.1. Allocation rule hien tai chua di vao output

Sau khi chay full pipeline, database khong co dong nao co `source like 'alloc_%'`.

Y nghia:
- direct costs co trong ket qua
- nhung cac chi phi phan bo tu hanh chinh tu file rule chua thuc su dong gop vao output cuoi

Anh huong:
- nhom nghiep vu trong sheet `Chi phi phan bo tu hanh chinh` chua duoc thuc hien day du

### 6.2. Monthly headcount tu GA dang lech khoa Cost Center

Da ghi nhan headcount `source='ga'` voi cac ma nhu:
- `1136`
- `40237000`

Trong khi master Cost Center cua `FORM.xlsx` la ma 10 chu so nhu:
- `1412000004`
- `1412000005`

Y nghia:
- headcount khong join duoc voi danh muc Cost Center dich
- allocation theo driver nhan su co the khong sinh du lieu hoac sinh sai

### 6.3. Posting month chua duoc mo ta va xu ly dung muc

Nghiep vu goc yeu cau:
- co rule chi phat sinh vao 1 thang cu the
- co rule phat sinh vao thang vao lam
- co rule phat sinh vao thang tiep theo

Neu code phan bo khong ton trong `posting_month`, ket qua co the:
- rai deu 12 thang sai nghiep vu
- hoac bo sot hoan toan rule

### 6.4. Working days la driver rieng, khong the coi nhu headcount

Nghiep vu yeu cau mot so rule tinh theo so ngay lam viec.

Neu he thong dung chung ham lay headcount cho `working_days`, ket qua se sai ban chat phep tinh.

### 6.5. Rule master chua idempotent qua nhieu lan chay

Trong mot lan chay E2E, log bao load `50` rules.

Nhung DB thuc te da ghi nhan tong `1350` dong rule, trong khi chi co `50` signature khac nhau.

Y nghia:
- bang rule dang bi tich luy qua nhieu lan chay
- de gay nham lan khi debug va doi chieu nghiep vu

## 7. Cach hieu dung khi ban giao

Khong nen mo ta he thong la:
- `da hoan tat 100%`
- `clean & verified`
- `san sang dong goi chinh thuc`

Cach mo ta dung hon:
- parser direct cost da chay va export batch duoc
- pipeline E2E da thong
- nhung phan allocation nghiep vu hanh chinh van con gap can xu ly tiep

## 8. Thu tu uu tien khi sua tiep

1. Chuan hoa khoa Cost Center trong parser GA de match voi `FORM.xlsx`.
2. Xu ly dung `posting_month` trong allocation engine.
3. Tach driver `working_days` khoi logic lay headcount.
4. Lam `map_allocation_rules` idempotent qua moi lan chay.
5. Chay doi chieu ket qua theo tung sheet nghiep vu trong workbook huong dan.

## 9. Tieu chuan de duoc coi la ban giao dung

Chi nen ket luan la `ban giao dung` khi dong thoi dat du cac dieu kien sau:
- pipeline E2E chay thanh cong
- direct cost khop workbook nguon
- allocation hanh chinh sinh du lieu that vao output
- `posting_month` duoc ton trong dung
- rule `working_days` tinh theo so ngay lam viec that
- headcount GA join dung voi master Cost Center
- ket qua doi chieu dat voi workbook huong dan nghiep vu tong

## 10. Ghi chu cho nguoi tiep nhan

Neu can trao doi voi nguoi dung hoac nguoi viet chuong trinh tiep theo, nen dung tai lieu nay lam moc chung:
- day la workflow nghiep vu dung
- day la rang buoc nghiep vu goc
- day la phan da chay
- day la phan con gap

Muc tieu cua tai lieu nay khong phai de to mau trang thai du an, ma de lam ro su that ky thuat va nghiep vu de ban giao dung.
