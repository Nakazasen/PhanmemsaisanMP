# Implementation Plan: So Sánh Biến Động Chi Phí MP Giữa Các Năm

**Branch**: `001-yoy-cost-variance` | **Date**: 2026-08-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-yoy-cost-variance/spec.md`

## Summary

Tính năng này cung cấp một công cụ trực quan (Tab So sánh) trong ứng dụng MP2027 Manager cho phép người dùng nạp hai file Excel FORM MP của 2 năm tài chính (năm trước và năm nay). Hệ thống sẽ bóc tách các dòng chi phí (ánh xạ bằng Mã tài khoản + Tên khoản mục), tính toán giá trị chênh lệch tuyệt đối, tỷ lệ % biến động, và gắn nhãn trạng thái (Tăng, Giảm, Mới, Đã cắt). Người dùng có thể xuất kết quả đối chiếu này ra một file Excel báo cáo giải trình kèm cảnh báo (highlight) các biến động vượt ngưỡng cho phép ($\ge 10\%$ hoặc $\ge 50$M VNĐ).

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `tkinter` (UI), `pandas` (Data matching & manipulation), `openpyxl` (Excel parsing & writing). Tất cả đều đã có sẵn trong `requirements/runtime.lock`.

**Storage**: N/A (Chỉ xử lý In-Memory trên các DataFrames, không ghi vào DB SQLite của MP2027 nhằm tuân thủ nguyên tắc read-only file nguồn).

**Testing**: `pytest` (Cần tạo test case unit cho Data Engine và test case tích hợp cho UI/xuất báo cáo).

**Target Platform**: Windows Desktop (Đóng gói PyInstaller onedir).

**Project Type**: Desktop Application.

**Performance Goals**: Xử lý, ánh xạ và hiển thị kết quả so sánh cho 1 cặp file MP trong vòng dưới 3 giây.

**Constraints**: Mọi xử lý phải là offline-capable. Quá trình đọc file MP không được phép sửa đổi file MP gốc (Read-Only access). Khi mở file Excel bị khóa (đang mở trong Excel khác), phải có cơ chế đọc an toàn.

**Scale/Scope**: Tối đa hàng trăm dòng chi phí cho mỗi Cost Center. Giao diện trực quan cần xử lý Treeview/Grid mượt mà.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Financial Data and Evidence Integrity**: Pass. Chỉ đọc và đối chiếu, không thay đổi số liệu hay giả định số liệu trống (Blanks được xử lý thành 0 khi tính toán số học nhưng vẫn giữ nguyên nhãn không phát sinh).
- **II. Excel Template and Output Fidelity**: Pass. Báo cáo xuất ra không đè lên file nguồn gốc, được tạo mới theo format báo cáo kiểm tra.
- **III. Layered, Testable Python Architecture**: Pass. Business logic (đọc, ánh xạ, tính toán chênh lệch) sẽ được tách riêng vào thư mục `src/engine/` hoặc `src/services/` (ví dụ: `variance_analyzer.py`), trong khi giao diện nằm ở `src/ui/`.
- **IV. Verification Before Trust**: Pass. Sẽ viết unit tests chuyên biệt cho logic tính % biến động và edge cases (chia cho 0).
- **V. Secure, Reproducible Delivery**: Pass. Sẽ xuất file báo cáo tạm vào `OUTPUT_FY2027/BAO_CAO_KIEM_TRA/`, không lưu trong working tree của git.

## Project Structure

### Documentation (this feature)

```text
specs/001-yoy-cost-variance/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── engine/
│   └── variance_analyzer.py       # (NEW) Logic lõi: Đọc 2 files, DataFrame merge, tính toán biến động
├── ui/
│   └── tabs/
│       └── variance_tab.py        # (NEW) Giao diện UI Tab So sánh (chọn file, Treeview kết quả, bộ lọc)
├── universal_app.py               # (MODIFY) Thêm VarianceTab vào thanh menu / điều hướng chính
└── utils/
    └── excel_variance_writer.py   # (NEW) Logic xuất báo cáo Excel giải trình biến động (có màu mè/công thức)

tests/
└── engine/
    └── test_variance_analyzer.py  # (NEW) Unit test logic ánh xạ và tính % (bao gồm edge cases)
```

**Structure Decision**: Tính năng thuộc dạng tiện ích kiểm toán độc lập (Audit utility). Do đó, giao diện được phân tách thành class riêng `VarianceTab` nhúng vào UI chính, và nghiệp vụ phân tích được đưa vào `src/engine/variance_analyzer.py` thay vì phình to các hàm phân bổ hiện tại. Export dùng `utils/excel_variance_writer.py`.

## Complexity Tracking

## Correction / Hardening Plan (2026-08-17)

### Audit baseline

The first implementation is not ready for acceptance despite all 26 tasks being
checked. The audit found a UI-to-engine column-index type error, a packaged
application dependency risk, incomplete batch pairing, duplicate-key inflation,
silent batch failures, and an export contract mismatch (values are written rather
than formulas). Correction work is required before release or publish.

### Scope boundary

In scope: the YoY engine, its Tkinter window, Excel writers, batch pairing,
packaging imports, tests, and feature documentation.

Out of scope: baseline T3, allocation rules, fiscal-run persistence, existing MP
workbook writers, updater behavior, and release publication. Existing financial
workflows must not be refactored as part of this correction.

### Ordered implementation phases

1. **P0 execution path and packaging safety**
   - Establish one explicit column-reference contract and normalize FORM input;
     add a regression test for the exact UI call with integer column indices.
   - Resolve the Manager package dependency risk: the new UI is imported at
     startup while `MP2027_Manager.spec` excludes pandas. Choose either deliberate
     bundling or a safe deferred import with an actionable error, then prove it
     with a package smoke test.

2. **P1 data correctness and input contract**
   - Normalize rows without mutating caller DataFrames or source workbooks.
   - Define duplicate `(account_code, item_name)` behavior: deterministic
     aggregation with diagnostics, or fail-closed rejection. Never permit a
     many-to-many merge to inflate financial totals.
   - Validate workbook type, required structure, numeric cells, blanks, and locked
     files. Only advertise formats the parser really supports.
   - Decide and document whether one canonical sheet or both FORM 1/FORM 2 are
     read; do not claim both until covered by tests.

3. **P1 batch behavior**
   - Extract Cost Center identifiers using a documented filename rule and pair by
     identifier, independent of year-specific prefixes/suffixes.
   - Return structured unmatched/invalid/error diagnostics; do not silently drop
     failed files.
   - Sanitize and uniquify Excel sheet names, including invalid characters and
     collisions.

4. **P2 export fidelity**
   - Align report metadata, totals, statuses, alerts, and user-notes with the
     specification.
   - Choose and document either real Excel formulas or value snapshots. The
     walkthrough must not claim formulas unless formulas are present.
   - Add workbook assertions for headers, formulas/values, number formats, colors,
     sheet names, and round-trip equality.

5. **P2 UI quality and encoding**
   - Repair mojibake in new user-facing strings and test encoding.
   - Validate thresholds and provide actionable errors.
   - Verify opening/canceling the separate window does not alter main-window state.

6. **Verification and release gate**
   - Add a regression test for every discovered defect.
   - Run affected tests, compile checks, CI-safe pytest, and package smoke tests.
   - Record skipped real-workbook checks and residual risk.
   - Update handover/quickstart with evidence. Do not build or publish until the
     owner explicitly requests release work and the release playbook is followed.

### Definition of done

- UI comparison succeeds with representative `.xlsx` fixtures.
- Duplicate, new/removed, blank/zero, malformed, and unmatched cases have
  deterministic tested outcomes.
- Existing MP tests and packaged Manager startup smoke test pass.
- Export satisfies the agreed formula/value contract and source files remain
  unchanged.
- Walkthrough claims match observed behavior and test evidence.

> **Fill ONLY if Constitution Check has violations that must be justified**

*(Không có vi phạm Constitution Check nào cần giải trình)*
