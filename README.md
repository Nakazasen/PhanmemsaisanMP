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

> **Nguyên tắc:** workbook `raw/requirements/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026.xlsx` là nguồn nghiệp vụ canonical cao nhất nếu có trong local/repo. Markdown chỉ là tài liệu diễn giải/handover.

## Output chính

Output runtime mặc định không nên commit:

- `OUTPUT_FY2027/MP_CC_<cost_center>.xlsx`
- `OUTPUT_FY2027/MP2027_AUDIT_REPORT.md`
- `OUTPUT_FY2027/MP2027_MISSING_INPUTS.csv`

## Nguyên tắc nghiệp vụ an toàn

- Không tự bịa dữ liệu.
- Canonical workbook ngày `09.06.2026` thắng mọi mô tả Markdown.
- Thiếu input thì fail-closed: để trống, ghi missing input, hoặc yêu cầu người dùng xác nhận.
- Không fallback bừa từ Cost Center khác.
- Không tự biến blank thành zero.
- Giữ format/formula của FORM; chỉ thay đổi logic tính toán khi có test/bằng chứng bảo vệ.

## Cài môi trường Windows

```powershell
py -m venv .venv
.\.venv\Scripts\activate
py -m pip install -U pip
pip install -r requirements.txt
```

Nếu máy có lệnh `python` trỏ sai Microsoft Store, dùng `py` như các ví dụ trên.

## Cách chạy

### GUI/launcher chính

```powershell
run_MP2027.bat
```

Batch này gọi `py src/universal_app.py`.

### Pipeline E2E cho developer

```powershell
py scripts/run_e2e.py --target-cc 1412000040
```

CLI E2E là developer smoke/integration path. Nó có thể cần `docs/MP2027/FORM.xlsx` và source workbook thật; nếu thiếu, chương trình phải báo lỗi rõ thay vì tạo dữ liệu giả.

## Cách test

```powershell
py -m compileall src scripts packaging
py -m pytest
```

CI GitHub Actions chạy compileall và pytest an toàn, không được phụ thuộc dữ liệu công ty/private ngoài repo.

## Cấu trúc thư mục quan trọng

- `src/`: code app, parser, engine, DB schema và UI.
- `scripts/run_e2e.py`: entrypoint pipeline E2E/developer.
- `packaging/`: entrypoint đóng gói portable.
- `tests/`: test regression/smoke.
- `docs/requirements/`: requirement và mapping nghiệp vụ đọc được bằng máy.
- `docs/knowledge/`: knowledge base/handover nghiệp vụ derived.
- `docs/MP2027/`: template/source curated nếu repo đang version hóa.
- `raw/requirements/`: workbook requirement canonical.
- `OUTPUT_FY2027/`: output runtime, không commit file sinh mới.

## Không được commit

- DB runtime: `mp2027.db`, `*.db`, `*.sqlite`, `*.sqlite3`.
- Output export mới trong `OUTPUT_FY2027/`.
- Source Excel công ty/private chưa được xác nhận là curated input.
- File tạm/cache/build: `__pycache__`, `.pytest_cache`, `.venv`, `build`, `dist`, `~$*`, `*.tmp`, `*.bak`.
- Secret: `.env`, key/token/credential file.

## Tài liệu nghiệp vụ cần đọc trước

- [Quy trình nghiệp vụ MP2027](QUY_TRINH_NGHIEP_VU_MP2027.md)
- [Cải tiến nhập dữ liệu chung](docs/requirements/cai_tien_nhap_du_lieu_chung.md)
- [Knowledge base MP saisan](docs/knowledge/mp_saisan_business_knowledge_base_v2.md)
- [Requirement mapping YAML](docs/requirements/requirement_mapping.yaml)

## Troubleshooting

- Thiếu `FORM.xlsx`: kiểm tra `docs/MP2027/FORM.xlsx`; không dùng root `FORM.xlsx` cũ làm fallback nếu code đã chặn.
- Thiếu source workbook: đặt đúng file trong `docs/MP2027` hoặc chọn lại source trong GUI.
- Thiếu headcount/bus/event/special cost: bổ sung CSV manual tương ứng, không để hệ thống tự đoán.
- Output có missing input: đọc `OUTPUT_FY2027/MP2027_MISSING_INPUTS.csv` và audit report trước khi gửi budget.
- Packaging không tìm thấy `docs/MP2027`: kiểm tra portable bundle đã include thư mục docs/source cần thiết.
