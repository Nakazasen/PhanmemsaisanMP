# Handover for next agent

## Repo đang làm gì

MP2027 Manager là app Python/Tkinter cho Windows để gom dữ liệu budget MP FY2027 từ nhiều Excel source, tính phân bổ hiện có, export FORM theo Cost Center và sinh audit/missing input.

## 1. Đọc theo thứ tự này

1. `docs/handover/CURRENT_OPEN_ITEMS.md` — backlog/handover hiện hành duy nhất
2. `docs/handover/FIXED_ASSETS_DEEP_AUDIT_HANDOVER_2026-07-16.md` — bắt buộc nếu làm fixed-assets; có evidence order và prompt tiếp quản
3. `docs/audits/AUDIT_STATUS_INDEX.md` — lifecycle và successor của audit cũ
4. `raw/Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx` — canonical cao nhất
5. `docs/requirements/requirement_mapping.yaml`
6. `docs/requirements/cai_tien_nhap_du_lieu_chung.md`
7. `QUY_TRINH_NGHIEP_VU_MP2027.md`
8. `docs/knowledge/mp_saisan_business_knowledge_base_v2.md`

Nếu Markdown mâu thuẫn workbook canonical ngày 10.07.2026, dùng workbook. Audit cũ không tự tạo backlog mới; trạng thái live chỉ lấy từ `CURRENT_OPEN_ITEMS.md`.

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

## 5. Trạng thái work hiện hành

Nguồn chi tiết: `docs/handover/CURRENT_OPEN_ITEMS.md`.

- `OPEN_DECISION`: NNN row/account ngoài row 137; data governance trước public/push.
- `BLOCKED_BY_INPUT`: headcount thật CC `1412000040`; December male/female và recruitment health-check drivers; các event driver chưa có source ổn định.
- `IMPLEMENTED_PENDING_ACCEPTANCE`: GUI đã chuyển heavy pipeline sang child process/UI queue nhưng chưa có current Windows acceptance.
- `OPEN_AUDIT`: fixed-assets phải cross-trace đủ canonical/source/reference/code trước khi hỏi policy còn thiếu; các module implemented khác cần audit output hiện hành đối chiếu canonical 10.07 sau khi đủ input thật.
- `CLOSED/SUPERSEDED`: empty output cũ, duplicate new-hire, total-headcount fallback, Column S, reference garbage, spacing giữa written blocks, bus generic event backlog và gas blocker 13.07 không còn là hạng mục mở độc lập.

## 6. Hướng phát triển

- Không re-open “recommended next phase” trong audit cũ nếu `AUDIT_STATUS_INDEX.md` đã chỉ ra successor.
- Fixed-assets tiếp tục theo `docs/handover/FIXED_ASSETS_DEEP_AUDIT_HANDOVER_2026-07-16.md`; audit GAP 15.07 chỉ là provenance.
- Không hỏi Accounting/MP cho fixed-assets trước khi đã cross-trace canonical, source/calculation MP2026/MP2027 và reference outputs; chỉ escalation phần còn mâu thuẫn hoặc thiếu evidence.
- Mọi thay đổi phải thêm regression test trước hoặc cùng lúc.
