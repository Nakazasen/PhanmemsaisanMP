# Draft Knowledge: Cải tiến nhập dữ liệu chung vào file MPnew

- source_id: ingest-c14b7fe5ca509fcb
- raw_file: raw/Cải tiến nhập dữ liệu chung vào file MPnew.xlsx
- status: draft
- ingest_mode: local
- confidence: 0.17
- promotion_status: review_needed
- review_reason: low_confidence
- perception_version: enterprise_ingest_perception_v2
- document_type: spreadsheet
- document_purpose: operations_report

## Business Summary
Chi phí hệ thống!A43: Ví dụ: Chi tiết chi phí VPN Sheet chi phí điện-nước Sheet chi phí lãi nhà, đất Sheet chi phí khấu hao nhà, đất Code phòng chịu chi phí Tháng tương ứng với từng cột (tứ tháng 4~3_kỳ FY) Khấu hao nhà Khấu hao đất Code phòng chịu chi phí Tháng tương ứng với từng cột (tứ tháng 4~3_kỳ FY) Lãi nhà Lãi đất Code phòng chịu chi phí Tháng tương ứng với từng cột (tứ tháng 4~3_kỳ FY) Tiền điện Tiền nước Code tài khoản chi phí Tháng tương ứng với từng cột (tứ tháng 4~3_kỳ FY) Nội dun...

## Document Purpose
- purpose: operations_report
- confidence: 0.47
- signals: q4

## Key Topics
- file
- code
- sheet
- sheet1
- form

## Extracted Knowledge Signals
### Entities
- Chi
- NNN Chi
- Sheet1
- A1
- Master Plan Sheet1
- A3
- A39
- B40

### Modules
- none

### Errors
- none

### Processes
- none

## Perception Pipeline
- document_type: spreadsheet
- document_type_confidence: 0.77
- signals: xlsx_container, cells, charts, comments, sheets, textboxes
- native_structured: confidence=0.78
- ocr: confidence=0.00
- vision_layout: confidence=0.00
- document_classifier: confidence=0.77
- provider_semantic: confidence=0.00

## Provider Assistance
- used=False; status=skipped; selected=; fail_count=0; latency_ms=0; token_estimate=0

## Possible Queries
- explain Cải tiến nhập dữ liệu chung vào file MPnew
- summarize Cải tiến nhập dữ liệu chung vào file MPnew
- what is file
- what is code
- what is sheet

## Extracted Source Text
Sheets: - Sheet1 - Hạng mục cần cải tiến - Chi phí hệ thống - Chi phí khấu hao, lãi nhà đất - Chi phí tài sản cố định - Chi phí làm giấy tờ cho NNN - Chi phí sinh nhật - Chi phí phân bổ từ hành chính - 勘定科目 - 原価センタ Cells: - Sheet1!A1: Cải tiến nhập tự động dữ liệu chung từ các file được cung cấp sẵn vào file Master Plan - Sheet1!A3: 1. Tổng quan file - Sheet1!A39: 2. Các file dữ liệu chi phí chung được cung cấp - Sheet1!B40: Chi phí hệ thống - Sheet1!B42: Chi phí khấu hao, lãi nhà đất, điện n ư ớc - Sheet1!B44: Chi phí tài sản cố định - Sheet1!B46: Chi phí phân bổ từ hành chính - Sheet1!A50: 3. Nhập dữ liệu lấy từ các file vào ô cần điền trong file MP - Sheet1!B52: Hình dung cách làm: - Sheet1!B53: ① Filter "code phòng chịu chi phí" trong các file chi phí chung - Sheet1!B54: ② Filter "code tài khoản chịu chi phí", "tên tài khoản chịu chi phí", "ghi chú" trong file MP đối tượng - Sheet1!B55: ③ Nhập dữ liệu từ mục ① vào ② (theo công thức hoặc paster nguyên số) - Hạng mục cần cải tiến!A1: Những hạng mục cần cải tiến - Hạng mục cần cải tiến!A2: 1. Không cần điền 2 dữ liệu dưới vào file - Hạng mục cần cải tiến!A16: 2. Đẩy các cột dữ liệu ghi dưới về cột chỉ mũi tên ghi dưới - Hạng mục cần cải tiến!A37: 3. Bôi lại đúng màu, đúng định dạng như FORM vốn có - Hạng mục cần cải tiến!A44: 4. Để lại tất cả các công thức tính - Hạng mục cần cải tiến!A45: Chi tiết đã ghi ở từng sheet - Hạng mục cần cải tiến!A46: VD: - Hạng mục cần cải tiến!A70: 5. Sai code chi phí hệ thống - Hạng mục cần cải tiến!A90: 6. Nhập đồng thời số người của 12 tháng, riêng tháng 12 hiển thị nhập số lượng Nam, N...

## Provenance
Raw extraction trace kept separate from business summary.
- sheets: method=xlsx_workbook_parse; confidence=0.72; evidence=10 sheet names; ref=xl/workbook.xml
- cells: method=xlsx_visible_cell_parse; confidence=0.78; evidence=2106 visible cell values; refs=Sheet1!A1, Sheet1!A3, Sheet1!A39, Sheet1!B40, Sheet1!B42, Sheet1!B44, Sheet1!B46, Sheet1!A50, Sheet1!B52, Sheet1!B53, Sheet1!B54, Sheet1!B55; ref=xl/worksheets/*.xml
- comments: method=xlsx_comment_parse; confidence=0.20; evidence=0 comments; refs=none; ref=xl/comments*.xml
- textboxes: method=xlsx_drawing_text_parse; confidence=0.66; evidence=7 drawing text blocks; ref=xl/drawings/drawing*.xml
- charts: method=xlsx_chart_title_parse; confidence=0.20; evidence=0 chart titles; ref=xl/charts/chart*.xml

## Trust Notice
This draft is not trusted wiki knowledge until explicitly approved or promoted by governed workflow.
