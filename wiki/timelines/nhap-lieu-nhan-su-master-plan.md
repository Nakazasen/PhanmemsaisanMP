---
id: "nhap-lieu-nhan-su-master-plan"
title: "Nhập liệu nhân sự Master Plan"
type: timeline
aliases: ["nhap_lieu_nhan_su"]
status: draft
sources:
  - ref: "processed/manifest.jsonl#line-1"
    type: xlsx
    title: "Cải tiến nhập dữ liệu chung vào file MPnew.xlsx"
    accessed_at: "2026-05-22T10:31:58Z"
grounding:
  engine: none
  notebook_id: ""
  query_used: ""
  grounded_at: ""
  confidence_note: "NotebookLM MCP unavailable during ingestion, marked as draft"
confidence: low
created_at: "2026-05-22T10:31:58Z"
updated_at: "2026-05-22T10:31:58Z"
tags: ["nhan-su", "timeline", "nhap-lieu", "master-plan"]
related: ["cai-tien-nhap-lieu-chi-phi-chung"]
contradictions: []
---

## Summary

Tài liệu này mô tả các yêu cầu thay đổi cách thức nhập liệu số người (nhân sự) trong Master Plan phục vụ cho việc tính toán phân bổ các loại chi phí chung đặc thù. Thay vì duy trì cơ chế nhập số người tĩnh cho cả 12 tháng như trước, hệ thống mới sẽ hỗ trợ nhập các trường dữ liệu động và đặc thù theo các mốc thời gian quy định.

## Details

Các thay đổi chi tiết về cấu trúc thời gian và số lượng nhân sự nhập liệu [src:processed/manifest.jsonl#line-1]:

### 1. Dữ liệu nhân sự dùng chung cho cả 12 tháng
- **Số người JP (xe bus)**: Số lượng người Nhật Bản đăng ký đi xe bus chung. Giá trị này áp dụng thống nhất cho cả 12 tháng trong kỳ tài chính [src:processed/manifest.jsonl#line-1].
- **Số người VN (xe bus)**: Số lượng người Việt Nam đăng ký đi xe bus chung. Giá trị này áp dụng thống nhất cho cả 12 tháng trong kỳ tài chính [src:processed/manifest.jsonl#line-1].

### 2. Dữ liệu nhân sự đặc thù theo từng tháng
- **Tháng 3 (FY cũ)**: Nhập số người để tính chi phí triết lý kinh doanh (My Episode - Giải thưởng thực hành triết lý) [src:processed/manifest.jsonl#line-1].
- **Tháng 4**: Nhập số người tham gia Tiệc chúc mừng sau buổi phát biểu phương châm bộ phận [src:processed/manifest.jsonl#line-1].
- **Tháng 5**: Nhập số người tham gia du lịch công ty (để tính chi phí phân bổ du lịch) [src:processed/manifest.jsonl#line-1].
- **Tháng 6**: Nhập số người không đi du lịch nhưng nhận được quà tặng từ công ty [src:processed/manifest.jsonl#line-1].
- **Tháng 10**: Nhập số người phục vụ cho 2 hạng mục kỷ niệm thành lập:
  - Số người nhận quà kỷ niệm 10 năm gắn bó [src:processed/manifest.jsonl#line-1].
  - Số người tham gia Tiệc kỷ niệm 10 năm gắn bó [src:processed/manifest.jsonl#line-1].
- **Tháng 12 (Đã có sẵn trường dữ liệu phân rã)**:
  - Số lượng Nam (phục vụ tính chi phí khám sức khỏe nam) [src:processed/manifest.jsonl#line-1].
  - Số lượng Nữ (phục vụ tính chi phí khám sức khỏe nữ) [src:processed/manifest.jsonl#line-1].

### 3. Hạng mục cần xóa bỏ
- Xóa các trường nội dung không còn cần thiết hoặc không được liệt kê trong danh sách mốc thời gian cải tiến trên [src:processed/manifest.jsonl#line-1].
- Điều chỉnh nhãn định danh từ định dạng tĩnh (ví dụ: `202704`, `202705`) sang nhãn động thân thiện hơn dạng chữ: `Tháng 4`, `Tháng 5`, ... để đảm bảo phần mềm có thể tái sử dụng lâu dài qua các năm [src:processed/manifest.jsonl#line-1].

## Evidence

- Grounded: Không có (NotebookLM MCP offline).
- Gaps: Xác nhận cấu trúc các cột nhập liệu trong file FORM.xlsx tương ứng có sẵn các dòng/cột để map với các mốc thời gian này chưa.

## Related

- [Cải tiến nhập liệu chi phí chung](cai-tien-nhap-lieu-chi-phi-chung.md)

## Change Log

| Date | Change | By |
|------|--------|----|
| 2026-05-22 | Khởi tạo tài liệu draft từ SRC-20260522-0001 | ingest-wiki |
