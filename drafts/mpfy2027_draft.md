# Draft Knowledge: 施設課　MPFY2027

- source_id: ingest-1ae1945dcc2b904e
- raw_file: raw/施設課　MPFY2027.xlsx
- status: draft
- ingest_mode: local
- confidence: 0.17
- promotion_status: review_needed
- review_reason: low_confidence
- perception_version: enterprise_ingest_perception_v2
- document_type: spreadsheet
- document_purpose: general_knowledge_source

## Business Summary
AA5: Administrator: Lãi tháng 5.2026 còn 196,991.77 USD AF5: Administrator: Lãi tháng 5.2026 còn 196,991.77 USD AK5: Administrator: Lãi tháng 5.2026 còn 196,991.77 USD

## Document Purpose
- purpose: general_knowledge_source
- confidence: 0.35
- signals: none

## Key Topics
- administrator
- depreciation
- building
- water
- land

## Extracted Knowledge Signals
### Entities
- Electric
- Water
- Depreciation
- C2
- E2
- USD
- I2
- M2

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
- explain 施設課　MPFY2027
- summarize 施設課　MPFY2027
- what is administrator
- what is depreciation
- what is building

## Extracted Source Text
Sheets: - 減価償却費（Depreciation） - 固定資産金利（Interest） - 水道光熱費（Electric & Water） - B&L - E&W Cells: - 減価償却費（Depreciation）!C2: Depreciation - 減価償却費（Depreciation）!E2: USD - 減価償却費（Depreciation）!I2: USD - 減価償却費（Depreciation）!M2: USD - 減価償却費（Depreciation）!A3: 部署 ブショ - 減価償却費（Depreciation）!C3: 減価償却費 ゲンカ ショウキャク ヒ - 減価償却費（Depreciation）!D3: 46113 - 減価償却費（Depreciation）!E3: 46143 - 減価償却費（Depreciation）!F3: 46174 - 減価償却費（Depreciation）!G3: 46204 - 減価償却費（Depreciation）!H3: 46235 - 減価償却費（Depreciation）!I3: 46266 - 減価償却費（Depreciation）!J3: 46296 - 減価償却費（Depreciation）!K3: 46327 - 減価償却費（Depreciation）!L3: 46357 - 減価償却費（Depreciation）!M3: 46388 - 減価償却費（Depreciation）!N3: 46419 - 減価償却費（Depreciation）!O3: 46447 - 減価償却費（Depreciation）!A4: 振替総額 フリカエ ソウガク - 減価償却費（Depreciation）!C4: 建物 Building タテモノ - 減価償却費（Depreciation）!D4: 324649.60000000009 - 減価償却費（Depreciation）!E4: 324649.59999999998 - 減価償却費（Depreciation）!F4: 324649.59999999998 - 減価償却費（Depreciation）!G4: 324649.60000000009 - 減価償却費（Depreciation）!H4: 324649.60000000003 - 減価償却費（Depreciation）!I4: 324649.60000000003 - 減価償却費（Depreciation）!J4: 324649.59999999992 - 減価償却費（Depreciation）!K4: 324649.60000000009 - 減価償却費（Depreciation）!L4: 324649.59999999986 - 減価償却費（Depreciation）!M4: 324649.60000000009 - 減価償却費（Depreciation）!N4: 324649.59999999998 - 減価償却費（Depreciation）!O4: 324649.60000000009 - 減価償却費（Depreciation）!C5: 土地 Land トチ - 減価償却費（Depreciation）!D5: 21912.570000000011 - 減価償却費（Depreciation）!E5: 21912.570000000007 - 減価償却費（Depreciation）!F5: 21912.57 - 減価償却費（Depreciation）!G5: 21912.57 - 減価償却費（Depreciation）!H5: 21912.569999999996 - 減価償却費（Depreciation）!I5: 21912.570000000003 -...

## Provenance
Raw extraction trace kept separate from business summary.
- sheets: method=xlsx_workbook_parse; confidence=0.72; evidence=5 sheet names; ref=xl/workbook.xml
- cells: method=xlsx_visible_cell_parse; confidence=0.78; evidence=11956 visible cell values; refs=減価償却費（Depreciation）!C2, 減価償却費（Depreciation）!E2, 減価償却費（Depreciation）!I2, 減価償却費（Depreciation）!M2, 減価償却費（Depreciation）!A3, 減価償却費（Depreciation）!C3, 減価償却費（Depreciation）!D3, 減価償却費（Depreciation）!E3, 減価償却費（Depreciation）!F3, 減価償却費（Depreciation）!G3, 減価償却費（Depreciation）!H3, 減価償却費（Depreciation）!I3; ref=xl/worksheets/*.xml
- comments: method=xlsx_comment_parse; confidence=0.70; evidence=40 comments; refs=E5, J5, L5, M5, O5, Q5, T5, V5, Y5, AA5, AD5, AF5; ref=xl/comments*.xml
- textboxes: method=xlsx_drawing_text_parse; confidence=0.20; evidence=0 drawing text blocks; ref=xl/drawings/drawing*.xml
- charts: method=xlsx_chart_title_parse; confidence=0.20; evidence=0 chart titles; ref=xl/charts/chart*.xml

## Trust Notice
This draft is not trusted wiki knowledge until explicitly approved or promoted by governed workflow.
