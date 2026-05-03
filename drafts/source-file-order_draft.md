# Draft Knowledge: source_file_order

- source_id: ingest-5cbbce9923c1e246
- raw_file: raw/source_file_order.xlsx
- status: draft
- ingest_mode: local
- confidence: 0.82
- promotion_status: candidate_promoted
- review_reason: high_confidence
- perception_version: enterprise_ingest_perception_v2
- document_type: spreadsheet
- document_purpose: general_knowledge_source

## Business Summary
source_file_order!C5: システム課金金額(Simulation)_FY2027_July.2026 ~ Dec.2026(Change AMS & PLM price).xls source_file_order!C6: システム課金金額(Simulation)_FY2027_Jan.2027 ~ March.2027(Change SAP price).xls source_file_order!C10: Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx

## Document Purpose
- purpose: general_knowledge_source
- confidence: 0.35
- signals: none

## Key Topics
- source_file_order
- source
- xlsx
- simulation
- fy2027

## Extracted Knowledge Signals
### Entities
- A1
- B1
- C1
- D1
- E1
- B2
- C2
- MPFY2027

### Modules
- none

### Errors
- E10: NNN paperwork source

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
- explain source_file_order
- summarize source_file_order
- what is source_file_order
- what is source
- what is xlsx

## Extracted Source Text
Sheets: - source_file_order Cells: - source_file_order!A1: order - source_file_order!B1: category - source_file_order!C1: filename - source_file_order!D1: enabled - source_file_order!E1: description - source_file_order!A2: 1 - source_file_order!B2: facility - source_file_order!C2: 施設課 MPFY2027.xlsx - source_file_order!D2: 1 - source_file_order!E2: Facility depreciation interest electric water source - source_file_order!A3: 2 - source_file_order!B3: fixed_assets - source_file_order!C3: 固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx - source_file_order!D3: 1 - source_file_order!E3: Fixed assets source - source_file_order!A4: 3 - source_file_order!B4: it_simulation - source_file_order!C4: システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls - source_file_order!D4: 1 - source_file_order!E4: IT simulation Apr-Jun source - source_file_order!A5: 4 - source_file_order!B5: it_simulation - source_file_order!C5: システム課金金額(Simulation)_FY2027_July.2026 ~ Dec.2026(Change AMS & PLM price).xls - source_file_order!D5: 1 - source_file_order!E5: IT simulation Jul-Dec source - source_file_order!A6: 5 - source_file_order!B6: it_simulation - source_file_order!C6: システム課金金額(Simulation)_FY2027_Jan.2027 ~ March.2027(Change SAP price).xls - source_file_order!D6: 1 - source_file_order!E6: IT simulation Jan-Mar source - source_file_order!A7: 6 - source_file_order!B7: ga - source_file_order!C7: 総務課 FY2027 MP 振替予定.xlsx - source_file_order!D7: 1 - source_file_order!E7: General affairs source - source_file_order!A8: 7 - source_file_order!B8: birthday - source_file_order!C8: Sinh nhật MP FY2027.xlsx -...

## Provenance
Raw extraction trace kept separate from business summary.
- sheets: method=xlsx_workbook_parse; confidence=0.72; evidence=1 sheet names; ref=xl/workbook.xml
- cells: method=xlsx_visible_cell_parse; confidence=0.78; evidence=50 visible cell values; refs=source_file_order!A1, source_file_order!B1, source_file_order!C1, source_file_order!D1, source_file_order!E1, source_file_order!A2, source_file_order!B2, source_file_order!C2, source_file_order!D2, source_file_order!E2, source_file_order!A3, source_file_order!B3; ref=xl/worksheets/*.xml
- comments: method=xlsx_comment_parse; confidence=0.20; evidence=0 comments; refs=none; ref=xl/comments*.xml
- textboxes: method=xlsx_drawing_text_parse; confidence=0.20; evidence=0 drawing text blocks; ref=xl/drawings/drawing*.xml
- charts: method=xlsx_chart_title_parse; confidence=0.20; evidence=0 chart titles; ref=xl/charts/chart*.xml

## Trust Notice
This draft is not trusted wiki knowledge until explicitly approved or promoted by governed workflow.
