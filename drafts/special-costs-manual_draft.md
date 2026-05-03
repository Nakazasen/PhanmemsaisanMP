# Draft Knowledge: special_costs_manual

- source_id: ingest-9a838349bf57b802
- raw_file: raw/special_costs_manual.csv
- status: draft
- ingest_mode: local
- confidence: 0.65
- promotion_status: review_needed
- review_reason: low_confidence
- perception_version: enterprise_ingest_perception_v2
- document_type: text_document
- document_purpose: general_knowledge_source

## Business Summary
cc_code, period, form_row, account_code, amount_vnd, description

## Document Purpose
- purpose: general_knowledge_source
- confidence: 0.35
- signals: none

## Key Topics
- period
- form_row
- description
- cc_code
- amount_vnd

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
- explain special_costs_manual
- summarize special_costs_manual
- what is period
- what is form_row
- what is description

## Extracted Source Text
cc_code, period, form_row, account_code, amount_vnd, description

## Provenance
Raw extraction trace kept separate from business summary.
- text: method=csv_parse; confidence=0.65; evidence=1 readable rows

## Trust Notice
This draft is not trusted wiki knowledge until explicitly approved or promoted by governed workflow.
