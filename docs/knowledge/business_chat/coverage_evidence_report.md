# MP2027 RAG Coverage, Traceability, and Semantic Report

- **Overall Audit Status**: `SEMANTIC_COVERAGE_COMPLETE`
- **Traceability Status**: `TRACEABILITY_COMPLETE`
- **Citation Metadata Status**: `CITATION_METADATA_COMPLETE`
- **Semantic Coverage Status**: `SEMANTIC_COVERAGE_COMPLETE`

## Summary Metrics

| Metric | Count | Description |
| :--- | :---: | :--- |
| **Total Inventory Items** | **481** | All headings and entry models scanned across 38 project files |
| Covered (Confirmed Rules) | 194 | Official business rules mapped to RAG topics |
| Reference with Caveat | 12 | Internal reference items with explicit confidence level |
| Technical Excluded | 226 | Dev setup, code, tests, database schemas, playbooks |
| Historical Excluded | 49 | Superseded specs, legacy documents |
| Needs Owner Review | 0 | Unclassified headings (must be 0) |
| **Searchable Items** | **206** | Items eligible for AI retrieval (`covered` + `reference_with_caveat`) |
| **With Exact Evidence Ref** | **206** | Items with verifiable, hash-matched source evidence in RAG topics |
| **Missing Evidence Items** | **0** | Unclaimed searchable items (must be 0 for completion) |
| **Traceability Coverage** | **100.0%** | Percentage of searchable items backed by real evidence |
| **Total Evidence References** | **221** | Evidence references embedded across curated packs & catalog |
| **Refs with Multilingual Summary (VI/EN/JA)** | **221** | Evidence refs with verified `display_title`, `heading_title`, and `supported_summary` |
| **Invalid Anchors Count** | **0** | Evidence references missing valid section body anchor text |
| **Template Summaries Count** | **0** | References containing forbidden generic template phrases |
| **Heading Translations Copied** | **0** | References where EN/JA heading is a duplicate of VI |
| **Semantic Coverage** | **100.0%** | Percentage of evidence references with verified semantics |
