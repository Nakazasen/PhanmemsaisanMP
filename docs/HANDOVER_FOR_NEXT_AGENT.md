# Handover for next agent

## Repo đang làm gì

MP2027 Manager là app Python/Tkinter cho Windows để gom dữ liệu budget MP FY2027 từ nhiều Excel source, tính phân bổ hiện có, export FORM theo Cost Center và sinh audit/missing input.

## File nghiệp vụ đọc đầu tiên

1. `raw/Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx` — canonical hiện tại, được người dùng xác nhận là bản mới nhất ngày 11.07.2026.
2. `docs/requirements/cai_tien_nhap_du_lieu_chung.md`.
3. `QUY_TRINH_NGHIEP_VU_MP2027.md`.
4. `docs/knowledge/mp_saisan_business_knowledge_base_v2.md`.
5. `docs/requirements/requirement_mapping.yaml`.

## Lệnh kiểm tra nhanh

```powershell
git status -sb
py -m compileall src scripts packaging
py -m pytest
```

## Quy tắc không bịa dữ liệu

- Thiếu dữ liệu thì để trống, ghi missing input, hoặc hỏi user.
- Không fallback Cost Center khác nếu không có rule rõ.
- Không biến blank thành zero.
- Markdown là derived; workbook canonical 10.07.2026 thắng.

## Phần chưa chắc cần user xác nhận

- Governance của tracked `.brain`, `OUTPUT_FY2027`, `raw`, `docs/MP2027`, `reference_outputs`.
- Mapping row/form chính xác cho một số nhóm nếu chưa đối chiếu output hiện tại và workbook canonical.
- Full E2E trên dữ liệu production/private.

## Hướng phát triển tiếp theo

- Tách runtime/dev requirements nếu repo muốn packaging chuyên nghiệp hơn.
- Thêm test đọc `requirement_mapping.yaml` bằng PyYAML nếu sau này dependency đã có.
- Tăng coverage cho fail-closed/missing input theo từng business area.
- Lập data governance checklist trước khi publish/push repo có workbook thật.
