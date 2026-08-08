# MP2027 Manager

MP2027 Manager là phần mềm desktop Windows viết bằng Python/Tkinter để gom dữ liệu budget MP FY2027 từ nhiều workbook Excel, tính các phần phân bổ đã có trong code, rồi xuất FORM theo từng Cost Center.

## Ai dùng chương trình này

- Người phụ trách lập/nghiệm thu budget MP FY2027.
- Người kiểm tra dữ liệu đầu vào, missing input và audit trail.
- Developer/agent tiếp quản repo nhưng không được tự thay đổi nghiệp vụ kế toán khi chưa có bằng chứng.

## Luồng sử dụng chính

1. Mở app bằng `run_MP2027.bat`.
2. Chọn FORM/template chính.
3. Upload hoặc đặt source workbook đúng thư mục `docs/MP2027`.
4. Kiểm tra missing input trước khi tin output.
5. Export FORM theo Cost Center.
6. Đọc audit report và missing input CSV.

## Input chính

Các input đang được repo kỳ vọng gồm:

- `docs/MP2027/FORM.xlsx`: template FORM cần giữ format/formula.
- `docs/MP2027/source_file_order.xlsx` hoặc `source_file_order.csv`: thứ tự source canonical khi export.
- `raw/headcount_manual.csv` và `docs/MP2027/headcount_manual.csv`: headcount nhập tay.
- `raw/bus_headcount_manual.csv` và `docs/MP2027/bus_headcount_manual.csv`: driver bus nhập tay.
- `docs/MP2027/event_drivers_manual.csv`: driver event nhập tay.
- `docs/MP2027/special_costs_manual.csv`: special costs nhập tay.
- Các source workbook trong `docs/MP2027`: facility, fixed assets, IT/system cost, GA/admin, birthday, NNN paperwork và các workbook liên quan.

> **Nguyên tắc:** workbook `raw/Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx` là nguồn nghiệp vụ canonical cao nhất. File này được người dùng xác nhận là bản mới nhất ngày 11.07.2026. Markdown chỉ là tài liệu diễn giải/handover.
>
> Bộ nguồn ngày `09.06.2026` được giữ như mốc lịch sử/legacy để truy vết yêu cầu; khi có khác biệt, workbook canonical `10.07.2026` được ưu tiên.

## Output chính

Output runtime mặc định không nên commit:

- `OUTPUT_FY2027/MP_CC_<cost_center>.xlsx`
- `OUTPUT_FY2027/BAO_CAO_KIEM_TRA/BAO_CAO_LAN_CHAY.xlsx`
- `OUTPUT_FY2027/BAO_CAO_KIEM_TRA/DU_LIEU_CON_THIEU.xlsx`
- `OUTPUT_FY2027/BAO_CAO_KIEM_TRA/KIEM_TRA_TY_GIA.xlsx`

Lịch sử audit riêng của tài sản cố định được lưu append-only tại
[`docs/audits/history/fixed_assets`](docs/audits/history/fixed_assets). Lịch sử này được tạo khi chạy
`py scripts/classify_fixed_assets_mismatches.py`; lần chạy GUI thông thường không tự chạy comparator này.

## Nguyên tắc nghiệp vụ an toàn

- Không tự bịa dữ liệu.
- Canonical workbook ngày `10.07.2026` thắng mọi mô tả Markdown.
- Thiếu input thì fail-closed: để trống, ghi missing input, hoặc yêu cầu người dùng xác nhận.
- Không fallback bừa từ Cost Center khác.
- Không tự biến blank thành zero.
- Giữ format/formula của FORM; chỉ thay đổi logic tính toán khi có test/bằng chứng bảo vệ.

## Cài môi trường Windows sau khi clone

```powershell
git clone https://github.com/Nakazasen/PhanmemsaisanMP
Set-Location PhanmemsaisanMP
py -m venv .venv
.\.venv\Scripts\activate
py -m pip install -U pip
pip install -r requirements.txt
py -m compileall src scripts packaging
py -m pytest -m "not requires_raw_excel and not real_pipeline_acceptance and not performance" -q
```

Fresh clone phải có trực tiếp workbook canonical:

```text
raw/Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx
```

Không cần sao chép `build/`, `dist/`, CSDL local hoặc output từ máy cũ.
Nếu máy có lệnh `python` trỏ sai Microsoft Store, dùng `py` như các ví dụ trên.

## Cách chạy

### GUI/launcher chính

```powershell
run_MP2027.bat
```

Batch này gọi `py src/universal_app.py` khi phát triển từ source.

### Bản đóng gói Windows cho người dùng

Bản phát hành dùng PyInstaller **onedir**, không dùng one-file. Máy người dùng
không cần cài Python hoặc compiler. Build và kiểm tra health xuyên suốt bằng:

```powershell
py scripts/package_app.py
```

Bundle được tạo trong `release_artifacts/install_bundle/`; người dùng luôn mở
`MP2027_Launcher.exe`, không mở executable nằm trực tiếp trong `apps/<version>/`.
Code immutable nằm trong `%LOCALAPPDATA%\MP2027 Manager`, còn DB/log/output và
input chỉnh sửa được nằm trong `%LOCALAPPDATA%\MPManager\Projects\MP2027`.

Biên dịch Setup sau khi build bundle:

```powershell
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer\MP2027_Manager.iss
```

Wizard cài/gỡ dùng duy nhất bản dịch tiếng Việt được ghim tại
`installer/languages/Vietnamese.isl`; contract test kiểm tra đủ 296 message key.
Bản build 0.1.0 đã đo: app onedir 164,97 MB, install bundle 180,33 MB và Setup
70,40 MB. Đây là bằng chứng trên máy build; vẫn phải smoke trên Windows sạch thật
không có Python/compiler trước khi tuyên bố tương thích mọi máy. Setup hiện chưa ký
Authenticode nên máy lạ vẫn có thể hiển thị cảnh báo SmartScreen.

Xem checklist phát hành và giới hạn clean-machine tại
[release_update_playbook.md](docs/handover/release_update_playbook.md).

### Pipeline E2E cho developer

```powershell
py scripts/run_e2e.py --target-cc 1412000040
```

CLI E2E là developer smoke/integration path. Nó có thể cần `docs/MP2027/FORM.xlsx` và source workbook thật; nếu thiếu, chương trình phải báo lỗi rõ thay vì tạo dữ liệu giả.

### Kiểm chứng output sau refactor

Khi cần chứng minh refactor không làm thay đổi output, chạy cùng một input snapshot
ở commit baseline và code hiện tại. Lệnh dưới đây tự tạo Git worktree cho baseline,
sao chép SQLite sang hai workspace riêng, chạy pipeline tách biệt, rồi so sánh từng
`MP_CC_<mã>.xlsx`:

```powershell
py tools/verify_refactor_output.py --run-pipelines `
  --baseline-ref ca2bc52 `
  --fy 2027 `
  --template D:/evidence/input/FORM.xlsx `
  --source D:/evidence/input/source `
  --headcount-source D:/evidence/input/headcount `
  --operational-db D:/evidence/input/mp2027.db `
  --manual-input-store D:/evidence/input/manual_inputs.db `
  --report-dir D:/evidence/refactor-check
```

Kết quả terminal báo từng CC với số dòng payload từ dòng 38 và kiểm tra tuyệt đối
vùng `B31:T36`, bao gồm công thức và ô trống. `PASS` chỉ khi cả hai điều kiện đều
khớp. Evidence được ghi ở `refactor_output_verification.json` và
`refactor_output_verification.xlsx` trong `--report-dir`; log hai lần pipeline cũng
được giữ tại đó. Lệnh không ghi vào database, output hay lịch sử run vận hành.

Nếu đã có sẵn hai thư mục output, chỉ cần so sánh mà không chạy pipeline:

```powershell
py tools/verify_refactor_output.py `
  --baseline-output D:/evidence/baseline-output `
  --candidate-output D:/evidence/refactor-output `
  --report-dir D:/evidence/refactor-check
```

## Cách test

```powershell
py -m compileall src scripts packaging
py -m pytest -m "not requires_raw_excel and not real_pipeline_acceptance and not performance" -q
py -m pytest -m "not performance" -q
```

GitHub Actions chạy profile CI-safe không cần workbook Excel thật trong `raw/`:

```powershell
py -m pytest -m "not requires_raw_excel and not real_pipeline_acceptance and not performance" -q
```

Local full validation trên máy có dữ liệu `raw/` thật chạy regression thông thường,
nhưng benchmark vẫn là opt-in:

```powershell
py -m pytest -m "not performance" -q
```

Xem toàn bộ profile fast/CI/acceptance/performance/package tại
[test_strategy_and_profiles.md](docs/handover/test_strategy_and_profiles.md).


Các test được đánh dấu `requires_raw_excel` cần workbook thật trong `raw/` và không chạy trên GitHub CI. Nếu các workbook này tồn tại local, test phải chạy thật và không được skip âm thầm để che lỗi nghiệp vụ.

## Cấu trúc thư mục quan trọng

- `src/`: code app, parser, engine, DB schema và UI.
- `scripts/run_e2e.py`: entrypoint pipeline E2E/developer.
- `packaging/`: entrypoint đóng gói portable.
- `tests/`: test regression/smoke.
- `docs/requirements/`: requirement và mapping nghiệp vụ đọc được bằng máy.
- `docs/knowledge/`: knowledge base/handover nghiệp vụ derived.
- `docs/MP2027/`: template/source curated nếu repo đang version hóa.
- `raw/`: workbook requirement canonical và các file nhập tay dùng chung.
- `OUTPUT_FY2027/`: output runtime, không commit file sinh mới.

## Không được commit

- DB runtime: `mp2027.db`, `*.db`, `*.sqlite`, `*.sqlite3`.
- Mọi output runtime trong `OUTPUT_FY2027/`.
- Source Excel công ty/private chưa được xác nhận là curated input.
- File tạm/cache/build: `__pycache__`, `.pytest_cache`, `.venv`, `.tmp_test_artifacts`, `build`, `dist`, `~$*`, `*.tmp`, `*.bak`.
- Script điều tra dùng một lần ở root: `.inspect_*.py`, `.compare_*.py`.
- Secret: `.env`, key/token/credential file.

## Dọn artifact local an toàn

Các thư mục/file sau được tái tạo tự động và có thể xóa khi cần giải phóng dung lượng:

```powershell
Remove-Item -Recurse -Force build, dist, .tmp_test_artifacts -ErrorAction SilentlyContinue
Remove-Item -Force mp2027.db, mp2027_before_optimization.db -ErrorAction SilentlyContinue
```

Sau khi dọn, source code và input canonical trong Git không bị ảnh hưởng.

## Tài liệu bàn giao cần đọc trước

1. [HANDOVER_FOR_NEXT_AGENT.md](docs/handover/HANDOVER_FOR_NEXT_AGENT.md) — trạng thái và thứ tự đọc.
2. [system_architecture.md](docs/architecture/system_architecture.md) — kiến trúc và sơ đồ Mermaid.
3. [feature_registry.md](docs/architecture/feature_registry.md) — các khối tính năng và owner code.
4. [data_dictionary.md](docs/database/data_dictionary.md) — schema, ERD, migration và ownership dữ liệu.
5. [test_strategy_and_profiles.md](docs/handover/test_strategy_and_profiles.md) — test/audit/performance gates.
6. [release_update_playbook.md](docs/handover/release_update_playbook.md) — đóng gói, update và rollback.
7. [Quy trình nghiệp vụ MP2027](QUY_TRINH_NGHIEP_VU_MP2027.md).
8. [Cải tiến nhập dữ liệu chung](docs/requirements/cai_tien_nhap_du_lieu_chung.md).
9. [Knowledge base MP saisan](docs/knowledge/mp_saisan_business_knowledge_base_v2.md).
10. [Requirement mapping YAML](docs/requirements/requirement_mapping.yaml).

Graph tương tác `.understand-anything/knowledge-graph.json` là artifact tùy chọn,
được tạo bằng workflow `/understand` sau khi review `.understandignore`; không coi
workspace state/generated graph là nguồn nghiệp vụ canonical.


## Troubleshooting

- Thiếu `FORM.xlsx`: kiểm tra `docs/MP2027/FORM.xlsx`; không dùng root `FORM.xlsx` cũ làm fallback nếu code đã chặn.
- Thiếu source workbook: đặt đúng file trong `docs/MP2027` hoặc chọn lại source trong GUI.
- Thiếu headcount/bus/event/special cost: bổ sung CSV manual tương ứng, không để hệ thống tự đoán.
- Output có missing input: đọc `OUTPUT_FY2027/BAO_CAO_KIEM_TRA/DU_LIEU_CON_THIEU.xlsx` và
  `BAO_CAO_LAN_CHAY.xlsx` trước khi gửi budget.
- Packaging không tìm thấy `docs/MP2027`: kiểm tra portable bundle đã include thư mục docs/source cần thiết.
