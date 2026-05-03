# Draft Knowledge: event_drivers_manual

- source_id: ingest-3cb4f6e82f501ac3
- raw_file: raw/event_drivers_manual.csv
- status: draft
- ingest_mode: local
- confidence: 0.65
- promotion_status: review_needed
- review_reason: low_confidence
- perception_version: enterprise_ingest_perception_v2
- document_type: text_document
- document_purpose: general_knowledge_source

## Business Summary
cc_code, period, event_name, count, unit_price, amount_vnd, account_code, form_row, description

## Document Purpose
- purpose: general_knowledge_source
- confidence: 0.35
- signals: none

## Key Topics
- unit_price
- period
- form_row
- event_name
- description

## Extracted Knowledge Signals
### Entities
- none

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
- native_structured: confidence=0.65
- ocr: confidence=0.00
- vision_layout: confidence=0.00
- document_classifier: confidence=0.58
- provider_semantic: confidence=0.00

## Provider Assistance
- used=False; status=skipped; selected=; fail_count=0; latency_ms=0; token_estimate=0

## Possible Queries
- explain event_drivers_manual
- summarize event_drivers_manual
- what is unit_price
- what is period
- what is form_row

## Extracted Source Text
cc_code, period, event_name, count, unit_price, amount_vnd, account_code, form_row, description

## Provenance
Raw extraction trace kept separate from business summary.
- text: method=csv_parse; confidence=0.65; evidence=1 readable rows

## Trust Notice
This draft is not trusted wiki knowledge until explicitly approved or promoted by governed workflow.
