# Draft Knowledge: FORM

- source_id: ingest-d98dd6f6bff32688
- raw_file: raw/FORM.xlsx
- status: draft
- ingest_mode: local
- confidence: 0.82
- promotion_status: candidate_promoted
- review_reason: high_confidence
- perception_version: enterprise_ingest_perception_v2
- document_type: spreadsheet
- document_purpose: general_knowledge_source

## Business Summary
F17: 責任者：76h Leo: 75h PF,DP外製：27h 既存機残業：25h ●メカ2: Haiさんの分：40h 既存機残業：40h Iris PRT 50h G17: 責任者：72h Leo: 75h 既存機残業：25h ●メカ2: Haiさんの分：38h 既存機残業：40h Iris PRT 70h H17: 責任者：84h Leo:90h 既存機残業：25h ●メカ2: Haiさんの分：44ｈ 既存機残業：40h Iris PRT 50h

## Document Purpose
- purpose: general_knowledge_source
- confidence: 0.35
- signals: none

## Key Topics
- huong
- iris
- nhung
- fy2027

## Extracted Knowledge Signals
### Entities
- USD
- C1
- MP
- F9
- Mai
- Le Thi Mai Huong
- G9
- H9

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
- explain FORM
- summarize FORM
- what is huong
- what is iris
- what is nhung

## Extracted Source Text
Sheets: - 採算表(USD) - 採算表(VND) - 内訳ﾘｽﾄ(4～3月) - 設備投資計画 - 勘定科目 - 原価センタ - 稼働日 Cells: - 採算表(USD)!B1: 組織名 - 採算表(USD)!C1: MP FY2027_各予定 - 採算表(USD)!N1: 26273 - 採算表(USD)!B2: メカ製造技術1課 - 採算表(USD)!B4: 項目 ＼ 部門 - 採算表(USD)!C4: 4 - 採算表(USD)!D4: 5 - 採算表(USD)!E4: 6 - 採算表(USD)!F4: 7 - 採算表(USD)!G4: 8 - 採算表(USD)!H4: 9 - 採算表(USD)!I4: 10 - 採算表(USD)!J4: 11 - 採算表(USD)!K4: 12 - 採算表(USD)!L4: 1 - 採算表(USD)!M4: 2 - 採算表(USD)!N4: 3 - 採算表(USD)!O4: 合計 - 採算表(USD)!B5: 総出荷 - 採算表(USD)!C5: 0 - 採算表(USD)!D5: 0 - 採算表(USD)!E5: 0 - 採算表(USD)!F5: 0 - 採算表(USD)!G5: 0 - 採算表(USD)!H5: 0 - 採算表(USD)!I5: 0 - 採算表(USD)!J5: 0 - 採算表(USD)!K5: 0 - 採算表(USD)!L5: 0 - 採算表(USD)!M5: 0 - 採算表(USD)!N5: 0 - 採算表(USD)!O5: 0 - 採算表(USD)!B6: 社外出荷 シャガイ シュッカ - 採算表(USD)!C6: 0 - 採算表(USD)!D6: 0 - 採算表(USD)!E6: 0 - 採算表(USD)!F6: 0 - 採算表(USD)!G6: 0 - 採算表(USD)!H6: 0 - 採算表(USD)!I6: 0 - 採算表(USD)!J6: 0 - 採算表(USD)!K6: 0 - 採算表(USD)!L6: 0 - 採算表(USD)!M6: 0 - 採算表(USD)!N6: 0 - 採算表(USD)!O6: 0 - 採算表(USD)!B7: 販売支援 ハンバイ シエン - 採算表(USD)!C7: 0 - 採算表(USD)!D7: 0 - 採算表(USD)!E7: 0 - 採算表(USD)!F7: 0 - 採算表(USD)!G7: 0 - 採算表(USD)!H7: 0 - 採算表(USD)!I7: 0 - 採算表(USD)!J7: 0 - 採算表(USD)!K7: 0 - 採算表(USD)!L7: 0 - 採算表(USD)!M7: 0 - 採算表(USD)!N7: 0 - 採算表(USD)!O7: 0 Comments: - E3: ご注意 ： 3行目にCHECK場所で 経費➝少数点 になると経費の数字は少数点がある 経費➝NG になると採算科目（D列）場所で確認してください 時間➝NG になると時間分は0.25とか0.5の倍数では無い - F9: Lê Thị Mai Hương(Le Thi Mai Huong): 有休：10日 時短者：1名（Nhungさん） - G9: Lê Thị Mai Hương(Le Thi Mai Huong): 有休：10日 時短者：1名（Nhungさん） - H9: Lê Thị Mai Hương(Le Thi Mai Huong): 有休：10日 時短者：1名（Nhungさん） - I9: Lê Thị Mai Hương(Le Thi Mai Huong): 有休：10日 時短者：1名（Nhungさん） - J9: Lê Thị Mai Hương(Le Thi Mai Huong): 有休：10日 時短者：1...

## Provenance
Raw extraction trace kept separate from business summary.
- sheets: method=xlsx_workbook_parse; confidence=0.72; evidence=7 sheet names; ref=xl/workbook.xml
- cells: method=xlsx_visible_cell_parse; confidence=0.78; evidence=5845 visible cell values; refs=採算表(USD)!B1, 採算表(USD)!C1, 採算表(USD)!N1, 採算表(USD)!B2, 採算表(USD)!B4, 採算表(USD)!C4, 採算表(USD)!D4, 採算表(USD)!E4, 採算表(USD)!F4, 採算表(USD)!G4, 採算表(USD)!H4, 採算表(USD)!I4; ref=xl/worksheets/*.xml
- comments: method=xlsx_comment_parse; confidence=0.70; evidence=30 comments; refs=E3, F9, G9, H9, I9, J9, K9, L9, M9, N9, O9, P9; ref=xl/comments*.xml
- textboxes: method=xlsx_drawing_text_parse; confidence=0.20; evidence=0 drawing text blocks; ref=xl/drawings/drawing*.xml
- charts: method=xlsx_chart_title_parse; confidence=0.20; evidence=0 chart titles; ref=xl/charts/chart*.xml

## Trust Notice
This draft is not trusted wiki knowledge until explicitly approved or promoted by governed workflow.
