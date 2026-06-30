# Audit repo handover hardening

## Trạng thái audit

- Branch gốc trước khi sửa: `main`.
- Commit gốc trước khi sửa: `85292fb` (`Clean stale artifacts and harden export pipeline`).
- Working tree ban đầu sạch theo `git status -sb`.
- Branch làm việc: `codex/repo-handover-hardening`.

## Repo hiện có gì tốt

- Có nhiều test regression cho parser/writer/export behavior.
- Có source-order policy và các test bảo vệ thứ tự file/blank separator.
- Có audit pipeline sinh `MP2027_AUDIT_REPORT.md` và `MP2027_MISSING_INPUTS.csv`.
- `.gitignore` đã ignore phần lớn Excel/runtime/build/cache và có ngoại lệ cho requirement workbook curated.
- Code đã có guard không fallback về root `FORM.xlsx` cũ trong `_default_template_path()`.

## Điểm rủi ro đang thấy

- `packaging/mp2027_portable_entry.py` import `main` từ `scripts.run_e2e`, nhưng `scripts/run_e2e.py` chưa có `def main()` trước hardening này.
- Một số test/workflow dùng workbook thật trong repo; CI cần tránh phụ thuộc dữ liệu private ngoài repo.
- Có tracked `.brain` và một số output/reference/raw file; cần review governance định kỳ để phân biệt public-safe knowledge và runtime/private.
- Một số file Python có BOM; công cụ AST đơn giản báo parse error nếu đọc bằng `utf-8` thay vì `utf-8-sig`.
- `python` không khả dụng trên máy audit, cần dùng launcher `py`.

## Source of truth nghiệp vụ

1. Canonical cao nhất: `raw/requirements/Cải tiến nhập dữ liệu chung vào file MPnew 09.06.2026.xlsx` nếu tồn tại.
2. Derived/handover: `docs/requirements/cai_tien_nhap_du_lieu_chung.md`.
3. Derived/handover: `QUY_TRINH_NGHIEP_VU_MP2027.md`.
4. Derived/handover: `docs/knowledge/mp_saisan_business_knowledge_base_v2.md`.

Markdown không được override workbook canonical.

## Entry point

- GUI/launcher: `run_MP2027.bat` -> `py src/universal_app.py`.
- E2E/developer CLI: `scripts/run_e2e.py`.
- Portable packaging entry: `packaging/mp2027_portable_entry.py` -> `scripts.run_e2e.main()`.

## Test hiện có

- Pytest tests trong `tests/` cho parser, fixed assets, system cost, admin consumables, source-order export, runtime save/load, reference compare.
- Một số test cần workbook fixture thật đang có trong repo; không nên tạo dữ liệu giả để pass.

## Thay đổi làm trong branch này

- Nâng cấp README tiếng Việt cho người vận hành và agent tiếp quản.
- Tạo `docs/requirements/requirement_mapping.yaml` dạng máy đọc được.
- Thêm `docs/development_setup.md`.
- Thêm `docs/HANDOVER_FOR_NEXT_AGENT.md`.
- Thêm `main()` cho `scripts/run_e2e.py` và giữ behavior `py scripts/run_e2e.py`.
- Thêm smoke tests cho README/mapping/entrypoint.
- Thêm GitHub Actions CI đơn giản.
- Củng cố `.gitignore` với SQLite/env/temp patterns an toàn.

## Cố ý không làm để tránh drift

- Không đổi công thức, số liệu, rule phân bổ hoặc fallback nghiệp vụ.
- Không xóa tracked data/reference/output vì có rủi ro mất dữ liệu hoặc phá fixture hiện có.
- Không normalize/format đại trà các file parser/engine có BOM nếu không cần cho mục tiêu entrypoint.
- Không chạy pipeline sinh output mới rồi coi là validation nghiệp vụ.

## Potential data governance review needed

- `.brain/*` đang có tracked knowledge/runtime state lẫn lộn; cần owner xác nhận phần nào public-safe.
- `OUTPUT_FY2027/MP2027_AUDIT_REPORT.md` và `OUTPUT_FY2027/MP2027_MISSING_INPUTS.csv` đang tracked; cần xác nhận đây là curated reference hay runtime output.
- `raw/*`, `docs/MP2027/*`, `reference_outputs/*` có workbook/csv thật; không tự xóa, chỉ review trước khi public/push.
