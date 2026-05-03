# Draft Knowledge: 固定資産情報_Fixed_Assets_Information_2025.11 - Nov

- source_id: ingest-ce9923444ba146d7
- raw_file: raw/固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx
- status: draft
- ingest_mode: local
- confidence: 0.17
- promotion_status: review_needed
- review_reason: low_confidence
- perception_version: enterprise_ingest_perception_v2
- document_type: spreadsheet
- document_purpose: operations_report

## Business Summary
2025.11!U3: For FY2027 Master Plan 2025.11!I4: 管理責任原価センタ名 Control Cost Centre Name 2025.11!K4: 償却計上原価センタ名 Depreciation Cost Centre Name

## Document Purpose
- purpose: operations_report
- confidence: 0.47
- signals: q4

## Key Topics
- depreciation
- interest
- cost
- useful
- life

## Extracted Knowledge Signals
### Entities
- Fixed
- KDTVN
- Useful
- Calculate Depr
- Interest FA Planned Depreciation
- B1
- FIXED ASSET DEPRECIATION
- U3

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
- explain 固定資産情報_Fixed_Assets_Information_2025.11   Nov
- summarize 固定資産情報_Fixed_Assets_Information_2025.11   Nov
- what is depreciation
- what is interest
- what is cost

## Extracted Source Text
Sheets: - 2025.11 - Fixed assets list - Sheet1 - KDTVN - useful life - Useful life - Calculate Depr&Interest FA - Planned Depreciation Cells: - 2025.11!A1: 45991 - 2025.11!B1: FIXED ASSET DEPRECIATION - 2025.11!B2: AS AT 30.11.2025 - 2025.11!U3: For FY2027 Master Plan - 2025.11!A4: No - 2025.11!B4: 区分 Category - 2025.11!C4: 資産№ Assets No - 2025.11!D4: 資産テキスト Text - 2025.11!E4: 品目コード Material Code - 2025.11!F4: 取得日 - 2025.11!G4: 耐用年数 Useful life - 2025.11!H4: 管理責任原価センタ Control Cost Center - 2025.11!I4: 管理責任原価センタ名 Control Cost Centre Name - 2025.11!J4: 償却計上原価センタ Depreciation Cost Center - 2025.11!K4: 償却計上原価センタ名 Depreciation Cost Centre Name - 2025.11!L4: 11月償却費実 November 2025 Depreciation - 2025.11!M4: 固定資産金利 Interest in December 2025 (Plan) - 2025.11!N4: 取得価格 / FY2026期首簿価 Acquistion Amount /FY2026 Beginning balance - 2025.11!O4: 区分 Asset Class - 2025.11!P4: 償却最終月 Last Depreciation Month - 2025.11!Q4: 最終月の償却金額 Last Month Depr - 2025.11!R4: 配賦情報 Allocation Info. - 2025.11!S4: WBS要素 Mã WBS - 2025.11!U4: 取得価格 / FY2027期首簿価 Acquistion Amount /FY2027 Beginning balance - 2025.11!V4: 2026年4月の固定資産金利/ Interest in April 2026 - 2025.11!W4: 固定資産金利2026年5月から/ Interest from May 2026 - 2025.11!A5: 1 - 2025.11!B5: MFG)MACHINERY AND EQUIPMENT - 2025.11!C5: 140000070-1 - 2025.11!D5: MAY HAN LID MEBIUS BK (BLACK) - 2025.11!F5: 44872 - 2025.11!G5: 005 - 2025.11!H5: 1412000034 - 2025.11!I5: T Manufacturing Sect - 2025.11!J5: 1412000034 - 2025.11!K5: T Manufacturing Sect - 2025.11!L5: 141.91 - 2025.11!M5: 13.2 - 2025.11!N5: 4399.3500000000004 - 2025.11!O5: Z1400 - 2025.11!P5: 46721 - 2025.11!Q5:...

## Provenance
Raw extraction trace kept separate from business summary.
- sheets: method=xlsx_workbook_parse; confidence=0.72; evidence=7 sheet names; ref=xl/workbook.xml
- cells: method=xlsx_visible_cell_parse; confidence=0.78; evidence=483365 visible cell values; refs=2025.11!A1, 2025.11!B1, 2025.11!B2, 2025.11!U3, 2025.11!A4, 2025.11!B4, 2025.11!C4, 2025.11!D4, 2025.11!E4, 2025.11!F4, 2025.11!G4, 2025.11!H4; ref=xl/worksheets/*.xml
- comments: method=xlsx_comment_parse; confidence=0.20; evidence=0 comments; refs=none; ref=xl/comments*.xml
- textboxes: method=xlsx_drawing_text_parse; confidence=0.20; evidence=0 drawing text blocks; ref=xl/drawings/drawing*.xml
- charts: method=xlsx_chart_title_parse; confidence=0.20; evidence=0 chart titles; ref=xl/charts/chart*.xml

## Trust Notice
This draft is not trusted wiki knowledge until explicitly approved or promoted by governed workflow.
