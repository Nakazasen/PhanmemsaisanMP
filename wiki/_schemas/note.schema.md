# Wiki Note Schema

> Version: 1.0.0 | Hybrid ABW
> All `.md` files in `wiki/entities/`, `wiki/concepts/`, `wiki/timelines/`, and `wiki/sources/` should follow this schema.

---

## YAML Frontmatter

```yaml
---
id: "concept-unique-slug"
title: "Display Name"
type: entity | concept | timeline | source
aliases: []
status: draft | grounded | verified | stale | disputed
sources:
  - ref: "processed/manifest.jsonl#line-1"
    type: pdf | url | text | drive | notebooklm
    title: "Original source title"
    accessed_at: "2026-04-14T00:00:00+07:00"
grounding:
  engine: notebooklm | manual | none
  notebook_id: ""
  query_used: ""
  grounded_at: ""
  confidence_note: ""
confidence: high | medium | low | unverified
created_at: "2026-04-14T00:00:00+07:00"
updated_at: "2026-04-14T00:00:00+07:00"
tags: []
related: []
contradictions: []
---
```

## Body Structure

```markdown
## Summary

Short grounded summary with source references.

## Details

Main content with inline citations such as `[src:manifest-line-1]`.

## Evidence

- Grounded: <verified evidence>
- Gaps: <missing or uncertain evidence>

## Related

- <related note links>

## Change Log

| Date | Change | By |
|------|--------|----|
| 2026-04-14 | Created | ingest-wiki |
```

## Validation Rules

| Rule | Severity |
|------|----------|
| `id` is unique across `wiki/` | ERROR |
| `status` is one of `draft`, `grounded`, `verified`, `stale`, `disputed` | ERROR |
| `sources` is non-empty for knowledge notes | ERROR |
| `confidence` is one of `high`, `medium`, `low`, `unverified` | ERROR |
| `grounding.engine` is not `none` when `status=grounded` | WARNING |
| Paths in `related` exist | WARNING |
