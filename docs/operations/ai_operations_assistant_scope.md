# Phạm vi tính năng: Trợ lý Vận hành & Xử lý Lỗi (AI Operations Assistant - MVP Read-only)

> **Document Control**:  
> - Owner: MP Engineering & AI Operations  
> - Status: Draft Scope Boundary — pending owner approval  
> - Feature Branch: `002-ai-operations-assistant`  
> - Effective Date: `2026-09-01`  
> - Reference Specs: [`specs/002-ai-operations-assistant/spec.md`](../../specs/002-ai-operations-assistant/spec.md), [`specs/002-ai-operations-assistant/plan.md`](../../specs/002-ai-operations-assistant/plan.md)

> **Approval note**: This document defines a planning boundary only. It must not be marked `Approved` until the product owner explicitly accepts the MVP scope and its local-only/read-only limits.

---

## 1. Tôn chỉ cốt lõi & Ranh giới an toàn (Safety Boundary)

Tính năng **AI Operations Assistant (Phiên bản MVP)** được thiết kế như một công cụ hỗ trợ người vận hành đọc hiểu nguyên nhân lỗi và nhận hướng dẫn xử lý thủ công an toàn từ các lần chạy đã lưu.

> [!IMPORTANT]
> **Ranh giới an toàn bất biến (Fail-Closed Safety Envelopes):**
> 1. **Chỉ đọc và cục bộ 100% (Local-only / Read-only)**: Trợ lý chỉ đọc dữ liệu bằng chứng từ thư mục workspace của một lần chạy đã kết thúc (terminal run) trên máy cục bộ.
> 2. **Loại trừ hoàn toàn việc tự động sửa đổi (Automated Repair is EXCLUDED)**: Trợ lý tuyệt đối **KHÔNG** tự động sửa file Excel/CSV, không sửa database SQLite, không can thiệp file cấu hình `project.json`, mã nguồn hoặc artifact phát hành.
> 3. **Không kết nối mạng / Không gọi API AI bên ngoài**: Hoạt động hoàn toàn độc lập, không yêu cầu API key, token bí mật hay truyền gửi dữ liệu kinh doanh ra ngoài máy trạm.
> 4. **Không tự ý chạy lại pipeline**: Trợ lý không kích hoạt tính toán hoặc chạy lại quy trình xuất dữ liệu.

---

## 2. Các chức năng trong phạm vi (In-Scope for MVP)

- **Trích xuất bằng chứng có căn cứ (Evidence-based Case Extraction)**:
  - Đọc từ các file báo cáo của lần chạy được chọn: `run_manifest.json`, `reports/preflight_report.json`, `reports/pipeline_stage_evidence.json`, `reports/failure_traceback.txt`.
  - Xác định rõ ràng phạm vi: Năm tài chính (FY), Cost Center (CC), giai đoạn lỗi (stage), mã lỗi (error code).
  - Phân định minh bạch 3 trạng thái: Thông tin đã xác nhận (`confirmed`), Suy đoán có thể (`possible`), và Bằng chứng không khả dụng (`unavailable`).
- **Kho tri thức lỗi chuẩn tắc tất định (Deterministic Knowledge Catalog)**:
  - Khớp lỗi chính xác dựa trên điều kiện bằng chứng của 3 nhóm lỗi phổ biến:
    1. Thiếu dữ liệu nhân sự / baseline headcount (`missing_staffing_baseline`).
    2. File Excel đầu ra bị khóa bởi tiến trình khác (`blocked_output_file_lock`).
    3. Kiểm tra tiền trạm thất bại / file nguồn sai định dạng (`preflight_source_validation_failure`).
- **Hướng dẫn xử lý thủ công đa ngôn ngữ (Multilingual Manual Guidance)**:
  - Trình bày giải thích và các bước khắc phục thủ công cho người dùng bằng 3 ngôn ngữ: Tiếng Việt (VI), Tiếng Anh (EN), Tiếng Nhật (JA).
  - Khi gặp lỗi lạ (`unknown` / `ambiguous`): Nêu rõ "Chưa xác nhận nguyên nhân", liệt kê bằng chứng hiện có và dẫn hướng người dùng sang kênh kiểm tra thủ công tiêu chuẩn, tuyệt đối không bịa đặt giải pháp.
- **An toàn giao diện (UI Safety)**:
  - Hộp thoại hiển thị thông tin chỉ đọc (Read-only Presentation Dialog).
  - Cơ chế Singleton Window: Không mở trùng lặp cửa sổ trợ lý.

---

## 3. Các hạng mục ngoài phạm vi & Hoãn lại (Explicitly Out-of-Scope & Deferred)

Các tính năng sau **bị nghiêm cấm** trong phạm vi MVP và chỉ được xem xét trong các giai đoạn tương lai khi có đặc tả an toàn riêng biệt:

- ❌ Tự động sửa chữa dữ liệu hoặc cấu hình (Automated repair proposals & auto-fix execution).
- ❌ Tự động chạy lại quy trình (Auto re-run pipeline).
- ❌ Kết nối LLM trực tiếp tại runtime qua internet (Live runtime LLM connectivity / Cloud AI services).
- ❌ Quản lý hay yêu cầu khóa ký số, credentials hoặc token bí mật.
- ❌ Ghi đè hoặc chỉnh sửa lịch sử chạy của các lần chạy trước đó.

---

## 4. Tiêu chí nghiệm thu & Kiểm chứng (Verification & Acceptance Criteria)

1. **Bảo toàn dữ liệu (No-write Invariant)**: Mã băm SHA-256 của toàn bộ file bằng chứng trong thư mục `RUN_HISTORY` phải hoàn toàn giữ nguyên trước và sau khi trợ lý khởi tạo và đọc dữ liệu.
2. **Khả năng kiểm thử cô lập (CI-Safe Fixtures)**: 100% kiểm thử sử dụng fixture tạm thời trong môi trường kiểm thử, không phụ thuộc file Excel nội bộ thực tế của doanh nghiệp.
3. **Trung thực & Minh bạch**: Đối với mọi lỗi không nằm trong danh mục đã duyệt, hệ thống từ chối đưa ra kết luận khẳng định và thông báo trạng thái `unconfirmed`.
