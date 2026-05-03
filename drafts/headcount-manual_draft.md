# Draft Knowledge: headcount_manual

- source_id: ingest-e0d8ce7ee56d80bd
- raw_file: raw/headcount_manual.csv
- status: draft
- ingest_mode: local
- confidence: 0.18
- promotion_status: review_needed
- review_reason: low_confidence
- perception_version: enterprise_ingest_perception_v2
- document_type: text_document
- document_purpose: general_knowledge_source

## Business Summary
1412000004, 202704, 21, 180, Example row - update numbers before run 1412000004, 202705, 21, 182, Month-by-month update 1412000004, 202712, 21, 182, 95, 108, December health-check split

## Document Purpose
- purpose: general_knowledge_source
- confidence: 0.35
- signals: none

## Key Topics
- update
- example
- split
- period
- numbers

## Extracted Knowledge Signals
### Entities
- Example
- Month-by-month
- December
- Admin

### Modules
- none

### Errors
- none

### Processes
- none

## Perception Pipeline
- document_type: text_document
- document_type_confidence: 0.58
- signals: text_file, text
- native_structured: confidence=0.18
- ocr: confidence=0.00
- vision_layout: confidence=0.00
- document_classifier: confidence=0.58
- provider_semantic: confidence=0.00

## Provider Assistance
- used=False; status=skipped; selected=; fail_count=0; latency_ms=0; token_estimate=0

## Possible Queries
- explain headcount_manual
- summarize headcount_manual
- what is update
- what is example
- what is split

## Extracted Source Text
cc_code, period, headcount_staff, headcount_worker, headcount_male, headcount_female, description 1412000004, 202704, 21, 180, Example row - update numbers before run 1412000004, 202705, 21, 182, Month-by-month update 1412000004, 202712, 21, 182, 95, 108, December health-check split 1412000006, 202701, 28, 0 1412000006, 202702, 28, 0 1412000006, 202703, 28, 0 1412000006, 202704, 22, 0 1412000006, 202705, 22, 0 1412000006, 202706, 26, 0 1412000006, 202707, 27, 0 1412000006, 202708, 27, 0 1412000006, 202709, 27, 0 1412000006, 202710, 27, 0 1412000006, 202711, 27, 0 1412000006, 202712, 27, 0, 25, 2 1412000025, 202704, 35, 0, Admin department example

## Provenance
Raw extraction trace kept separate from business summary.
- text: method=csv_parse; confidence=0.18; evidence=17 readable rows

## Trust Notice
This draft is not trusted wiki knowledge until explicitly approved or promoted by governed workflow.
