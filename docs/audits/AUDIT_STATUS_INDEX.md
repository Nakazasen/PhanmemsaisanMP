# MP2027 — Chỉ mục vòng đời audit

Ngày dọn lại: `2026-07-20`

Tài liệu trong `docs/audits` và `reports` là **bằng chứng lịch sử**, không phải
handover hoặc backlog. Handover hiện hành duy nhất là
`docs/handover/HANDOVER_FOR_NEXT_AGENT.md`.

## Bằng chứng còn có giá trị tham khảo

| Nhóm bằng chứng | Phạm vi chắc chắn | Giới hạn |
|---|---|---|
| `fixed_assets_cross_trace_audit_2026-07-16.*` và các CSV/JSON cùng ngày | Ghi lại kết quả comparator tại thời điểm chạy | Không tự cho phép đổi công thức hay ghi đè lớp manual/snapshot |
| `history/fixed_assets/` | Nhật ký append-only của các lần phân loại | Không phải danh sách công việc hiện hành |
| `phase42n3y_final_user_claims_acceptance_audit.md` | Bằng chứng của run dùng workbook 09.06 | Không phải acceptance đầy đủ cho canonical 10.07 |
| `reports/fy2027_audit_report_2026-07-13.md` | So sánh và quan sát tại thời điểm 13.07 | Các blocker/next step trong báo cáo đã cũ |
| `repo_handover_hardening_audit.md` | Lịch sử đợt hardening repository | Cấu trúc handover của đợt đó đã bị thay thế |

## Audit đã superseded

- `phase42n3q_post_fix_user_claims_full_audit.md`;
- `phase42n3s_reaudit_user_claims_on_nonempty_output.md`;
- `phase42r0_canonical_requirement_reconciliation.md`;
- các báo cáo `phase42n1*`, `phase42n2*` và `phase42n3*` khác;
- `fixed_assets_gap_and_implementation_plan_2026-07-15.md`.

Giữ các file này để truy vết, nhưng không thực hiện phần “recommended next
phase”, “open item” hoặc “blocker” của chúng nếu handover hiện hành không yêu
cầu rõ.

## Quy tắc bảo trì

1. Audit mới phải ghi commit, input và thời điểm chạy.
2. Kết luận chỉ có hiệu lực trong đúng phạm vi evidence đã chạy.
3. Audit không được tự tạo backlog.
4. Chỉ cập nhật handover hiện hành khi trạng thái có thể kiểm chứng bằng code,
   config, test, artifact hoặc xác nhận trực tiếp của người dùng.
