---
id: "cai-tien-nhap-lieu-chi-phi-chung"
title: "Cải tiến nhập liệu chi phí chung"
type: concept
aliases: ["cai_tien_chi_phi_chung"]
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
tags: ["chi-phi", "cai-tien", "master-plan", "nhap-lieu"]
related: ["nhap-lieu-nhan-su-master-plan"]
contradictions: []
---

## Summary

Tài liệu này chi tiết các yêu cầu cải tiến quy trình nhập tự động các khoản chi phí chung từ các file nguồn dữ liệu thô vào file Master Plan (MPnew.xlsx). Quy trình cải tiến nhằm mục đích bảo toàn công thức tính toán, định dạng màu sắc gốc của FORM mẫu, và tự động hóa việc lọc trung tâm chi phí (cost centers).

## Details

Hệ thống chi phí chung cần cải tiến bao gồm 7 hạng mục chi phí chính [src:processed/manifest.jsonl#line-1]:

### 1. Chi phí hệ thống (System Cost)
- **Vấn đề**: Hiện tại chi phí hệ thống chưa lấy được công thức tự động, vẫn ở dạng giá trị số tĩnh. Công thức tính tổng tiền bị sai lệch so với dữ liệu thực tế do IT cung cấp [src:processed/manifest.jsonl#line-1].
- **Giải pháp**: Nhập vào một dòng duy nhất.
- **Công thức yêu cầu**: 
  `= ROUND(Tổng các chi phí hệ thống thành phần * Tỷ giá USD (ô B2 trong file MP), 0)`
- **Ví dụ**: Với phòng code `1412000006`, công thức là:
  `= ROUND((11*3.19 + 12*11.51 + 1*153.91 + 2*2114.25 + 12*2.25) * 26273, 0) = 120,399,175` (lệch tối đa 1 đồng do tỷ giá so với sheet tổng) [src:processed/manifest.jsonl#line-1].

### 2. Chi phí khấu hao và lãi nhà đất (Depreciation & Land Interest)
- **Vấn đề**: Việc lọc (filter) code phòng chịu chi phí có nguy cơ làm mất dòng khấu hao đất hoặc lãi đất, do đó quy trình tự động hóa cần xử lý cẩn thận mà không làm mất dòng dữ liệu [src:processed/manifest.jsonl#line-1].
- **Công thức yêu cầu**:
  - **Khấu hao nhà (Thứ tự 1)**: `= ROUND(Khấu hao nhà * Tỷ giá USD, 0)` [src:processed/manifest.jsonl#line-1]
  - **Khấu hao đất (Thứ tự 2)**: `= ROUND(Khấu hao đất * Tỷ giá USD, 0)` [src:processed/manifest.jsonl#line-1]
  - **Lãi nhà (Thứ tự 3)**: `= ROUND(Lãi nhà * Tỷ giá USD, 0)` [src:processed/manifest.jsonl#line-1]
  - **Lãi đất (Thứ tự 4)**: `= ROUND(Lãi đất * Tỷ giá USD, 0)` [src:processed/manifest.jsonl#line-1]
  - **Tiền điện (Thứ tự 5)** và **Tiền nước (Thứ tự 6)**: Sao chép/dán dữ liệu trực tiếp [src:processed/manifest.jsonl#line-1].
- Yêu cầu nhập đầy đủ cho cả 12 tháng.

### 3. Chi phí tài sản cố định (Fixed Assets)
- **Cách làm**:
  - Lọc "code phòng chịu chi phí" [src:processed/manifest.jsonl#line-1].
  - Xác nhận "Tháng khấu hao cuối cùng" có nằm trong kỳ tài chính FY đó hay không:
    - Nếu không nằm trong kỳ: Nhập khấu hao theo công thức `= ROUND(Khấu hao * Tỷ giá, 0)` vào dòng 38 và Lãi theo `= ROUND(Lãi * Tỷ giá, 0)` vào dòng 42 cho toàn bộ các tháng [src:processed/manifest.jsonl#line-1].
    - Nếu nằm trong kỳ: Các tháng trước tháng cuối cùng điền bình thường. Tại tháng khấu hao cuối cùng, lấy giá trị trong cột "tháng khấu hao cuối cùng" [src:processed/manifest.jsonl#line-1]. Kể từ tháng tiếp theo trở đi, để trống chi phí [src:processed/manifest.jsonl#line-1].
- **Lưu ý**: Hạng mục này tương đối phức tạp và người dùng cho phép ưu tiên xử lý sau [src:processed/manifest.jsonl#line-1].

### 4. Chi phí làm giấy tờ cho người nước ngoài (Foreigners Paperwork Costs)
- **Đặc điểm**: Đây là loại chi phí mới được bổ sung [src:processed/manifest.jsonl#line-1].
- **Cách làm**: Lọc mã tài khoản cần thiết tại cột "Code tài khoản chịu chi phí" và nhập số tiền tương ứng vào các tháng xuất hiện rải rác trong file nguồn vào dòng 137 (F137 -> Q137) của file FORM [src:processed/manifest.jsonl#line-1].

### 5. Chi phí sinh nhật (Birthday Costs)
- **Cách làm**: Lọc code tài khoản chịu chi phí, lấy số người tương ứng từng tháng, lọc nội dung "誕生日会 Tiệc sinh nhật" trong file "FY2027配賦額一覧", và nhập vào dòng 59 (F59 -> Q59) trong file FORM [src:processed/manifest.jsonl#line-1].
- **Công thức yêu cầu**: `= Số người * Đơn giá` [src:processed/manifest.jsonl#line-1].
- **Trường hợp có nhân viên mới**: Cộng thêm người mới vào tháng đó. Ví dụ: Tháng 6 có 2 người sinh nhật + 1 người mới = 3 người sinh nhật. Công thức: `= (2 + 1) * 152,000` [src:processed/manifest.jsonl#line-1].

### 6. Chi phí phân bổ từ hành chính (Administrative Allocation Costs)
- **Chi phí phân bổ 12 tháng**: Áp dụng cho tiền gas, nước rửa tay, giấy vệ sinh, chi phí làm sạch.
  - **Công thức**: `= Số người * Chi phí tương ứng` [src:processed/manifest.jsonl#line-1].
  - **Số người**: Lấy tổng số người của tháng trước. Riêng tháng 4 (không có dữ liệu tháng 3 của kỳ trước) vẫn lấy tổng số người của tháng 4 [src:processed/manifest.jsonl#line-1].
- **Chi phí phân bổ đặc thù từng tháng**: (Du lịch tháng 5, Tiệc chúc mừng tháng 4, Quà không đi du lịch tháng 6, Bánh trung thu tháng 9, Tiệc 10 năm tháng 10, Quà kỉ niệm 10 năm tháng 10, Lịch bỏ túi tháng 11, Thể thao tháng 11, Tất niên tháng 2, Lì xì tháng 2, Khám sức khỏe nam/nữ tháng 12) [src:processed/manifest.jsonl#line-1].
  - Quy trình tự động cần tra bảng phân loại phòng ban (製造 - Manufacturing, 一般 - General, 販売 - Selling) để lấy đúng mã tài khoản tương ứng [src:processed/manifest.jsonl#line-1].
  - **Công thức**: `= Số người * Đơn giá` [src:processed/manifest.jsonl#line-1].
- **Chi phí nhân sự mới**:
  - Sổ nhân viên mới: `= Số người nhân viên mới * Đơn giá (9,100 VND)` [src:processed/manifest.jsonl#line-1].
  - Sổ công nhân mới: `= Số người công nhân mới * Đơn giá (4,000 VND)` [src:processed/manifest.jsonl#line-1].
  - Khám sức khỏe tuyển dụng: Phân bổ vào tháng tiếp theo tháng tuyển dụng. Ví dụ: Tuyển dụng tháng 6, chi phí phân bổ vào tháng 7 dòng 58 file FORM [src:processed/manifest.jsonl#line-1].

## Evidence

- Grounded: Không có (Do NotebookLM MCP offline, dữ liệu được trích xuất thủ công an toàn từ Excel thô).
- Gaps: Công thức tính toán chi phí tài sản cố định cần được kiểm định thực tế sau khi viết code tự động hóa.

## Related

- [Tài liệu thay đổi cách nhập nhân sự](nhap-lieu-nhan-su-master-plan.md)

## Change Log

| Date | Change | By |
|------|--------|----|
| 2026-05-22 | Khởi tạo tài liệu draft từ SRC-20260522-0001 | ingest-wiki |
