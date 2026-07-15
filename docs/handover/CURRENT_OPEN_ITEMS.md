# MP2027 — Current Open Items

As of: `2026-07-16`  
Canonical requirement: `raw/Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx`

> [!IMPORTANT]
> Đây là **sổ trạng thái hiện hành duy nhất** cho backlog/handover. Audit cũ vẫn là evidence lịch sử nhưng không tự tạo backlog mới. Mỗi mục còn mở bên dưới có đúng một next action.

## Status vocabulary

| Status | Meaning |
|---|---|
| `CLOSED` | Có evidence hiện hành đủ để không còn là việc cần làm. |
| `SUPERSEDED` | Kết luận/next phase cũ đã bị audit hoặc canonical source mới hơn thay thế. |
| `HISTORICAL` | Giữ lại làm provenance; không phải work hiện hành. |
| `IMPLEMENTED_PENDING_ACCEPTANCE` | Code/test đã có nhưng chưa được accept bằng input/output thực tế. |
| `BLOCKED_BY_INPUT` | Luồng đã fail-closed; cần dữ liệu hoặc quyết định nghiệp vụ thật. |
| `OPEN_DEFECT` | Có triệu chứng lỗi hiện hành và chưa có evidence đóng. |
| `OPEN_DECISION` | Không được tự chọn vì ảnh hưởng quy tắc kế toán hoặc governance. |
| `OPEN_AUDIT` | Có code nhưng chưa có current-output evidence đủ để claim complete. |
| `MAINTENANCE_BACKLOG` | Việc cải thiện quy trình; không chặn product operation hiện tại. |

## Active work register

| ID | Status | Scope/evidence | Single next action |
|---|---|---|---|
| FA-OPEN | `OPEN_AUDIT` | Fixed-assets chưa đủ evidence để claim complete; handover hiện hành là `docs/handover/FIXED_ASSETS_DEEP_AUDIT_HANDOVER_2026-07-16.md`. Audit GAP 15.07 chỉ là provenance, không phải bảng quyết định hiện hành. | Cross-trace canonical → source/calculation MP2026/MP2027 → reference outputs → code/tests, lập asset ledger và decision matrix; chỉ hỏi nghiệp vụ cho phần còn mâu thuẫn/thiếu sau audit. |
| HC-1412000040 | `BLOCKED_BY_INPUT` | `phase42n3y` found zero canonical monthly headcount rows for target CC. New-hire logic now fails closed instead of fabricating amounts. | Cung cấp baseline `202603` và periods `202604..202703` cho CC `1412000040`, rồi regenerate acceptance. |
| HEALTH-DEC | `BLOCKED_BY_INPUT` | Health-check rows 57/58 need real December male/female and/or recruitment drivers where the canonical rule applies. | Cung cấp/chốt driver thật cho health-check trước khi audit output rows 57/58. |
| EVENT-REAL | `BLOCKED_BY_INPUT` | Manual event channel exists, but no-trip gift, My Episode, 10-year event, company anniversary and any unparsed event need confirmed rows. | Điền schema-valid rows in `docs/MP2027/event_drivers_manual.csv` (or explicitly confirm none). |
| NNN-SCOPE | `OPEN_DECISION` | Row 137 is current verified NNN path; Passport/VISA/GPLD outside that path must not be guessed. | Accounting/MP xác nhận row/account cho any requirement outside row 137. |
| GUI-FREEZE | `IMPLEMENTED_PENDING_ACCEPTANCE` | Current code uses a UI queue and runs the heavy pipeline in `subprocess.Popen`, but no later frozen-state capture or successful manual Windows session closes the 2026-07-10 report. | Reproduce once on Windows current `main`; capture stack only if `Responding=False`, otherwise record a successful GUI run. |
| MOD-OUTPUT-AUDIT | `OPEN_AUDIT` | Several modules are implemented but latest acceptance verified only written-block spacing, not full source-derived amount completeness against canonical 10.07. | Run one canonical 10.07 output audit by module/CC after required real inputs are available. |
| DATA-GOV | `OPEN_DECISION` | Tracked `.brain`, output reports, raw workbooks and reference outputs may contain operational/private data. | Owner approves a public/push data-governance checklist before publishing repository data. |
| NLM-GROUND | `MAINTENANCE_BACKLOG` | `.brain/grounding_queue.json` records an old `MCP_UNAVAILABLE`; this is knowledge maintenance, not a product blocker. | Retry grounding only when NotebookLM sync is intentionally resumed. |

## Closed or superseded items

| ID | Status | Closure evidence |
|---|---|---|
| OUT-EMPTY-42N3Q | `SUPERSEDED` | Empty-output observation in `phase42n3q` was superseded by non-empty generation in `phase42n3s` and later acceptance in `phase42n3y`. |
| NEW-HIRE-DUP | `CLOSED` | `phase42n3y`: no duplicate/misaligned stationery formulas; allocation is safely suppressed when drivers are incomplete. Real-amount acceptance remains under `HC-1412000040`. |
| NEW-HIRE-TOTAL-HC | `CLOSED` | `phase42n3y`: no total-headcount multiplier patterns; missing delta series fails closed. |
| COLUMN-S | `CLOSED` | `phase42n3y`: cost+blank-S = 0 and no-cost+nonblank-S = 0 from row 30 onward. |
| REF-GARBAGE-213 | `CLOSED` | `phase42n3y`: zero business rows from row 213 onward; 130 unscoped reference rows quarantined. |
| BLOCK-SPACING | `CLOSED` | Scoped closure: `phase42n3y` proved every adjacent populated source block had exactly one blank row. Number of populated blocks remains input-dependent, not a spacing defect. |
| BUS-JP-VN | `CLOSED` | GUI/parser/DB flow uses independent JP/VN scalar bus passenger drivers; it is no longer a generic pending event. |
| GAS-IDENTITY-20260713 | `SUPERSEDED` | Current code resolves gas by account `5005056281` + identity token, fails on zero/multiple matches, and writes to the resolved row. Regression tests encode row-46/native-parser expectations, but the current run is blocked before those assertions by the FY2027 headcount integrity guard; retain gas under `MOD-OUTPUT-AUDIT`, not as the old identity defect. |
| REQ-04-06 | `SUPERSEDED` | Workbook 04.06 was replaced by 09.06 and then by user-confirmed canonical 10.07. |
| REQ-09-06 | `HISTORICAL` | Audits based on 09.06 remain evidence for their run but cannot override canonical 10.07. |
| FIXED-ASSET-OLD-NEXT | `SUPERSEDED` | Legacy mapping/extraction phases and the 15 July “ask Accounting first” workflow are replaced by `FIXED_ASSETS_DEEP_AUDIT_HANDOVER_2026-07-16.md`; workbook evidence must be exhausted before business escalation. |

## Closure rule

Do not close an active row merely because output is blank. Move it to `CLOSED` only when one of these exists:

1. reproducible code/test/output evidence against current code and applicable canonical input;
2. user/Accounting acceptance for data-dependent behavior; or
3. a newer source/evidence explicitly supersedes the old claim.

When status changes, update this register first, then synchronize the top-level handover, process guide, requirement mapping and project memory.
