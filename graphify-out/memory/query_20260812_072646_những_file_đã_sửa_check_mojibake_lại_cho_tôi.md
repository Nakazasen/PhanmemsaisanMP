---
type: "query"
date: "2026-08-12T07:26:46.203312+00:00"
question: "những file đã sửa check mojibake lại cho tôi"
contributor: "graphify"
outcome: "useful"
source_nodes: ["In Unicode mà không làm hỏng luồng vận hành nếu console có encoding cũ.", "complete_v1_source_order_writer.py", "universal_app.py", "excel_helpers.py"]
---

# Q: những file đã sửa check mojibake lại cho tôi

## Answer

Expanded from original query via graph vocab: [unicode, encoding, writer, baseline, manual, source, template, allocator, export, excel, release, installer, universal, headcount]. Audited 17 dirty text files: all decode as strict UTF-8, all are NFC, no replacement characters, hidden controls, or common mojibake sequences in whole files or added diff lines. Non-ASCII additions are valid Vietnamese/Japanese; half-width Katakana token is intentional source matching. git diff --check, Python compile, and release.json parsing passed. No source changes required.

## Outcome

- Signal: useful

## Source Nodes

- In Unicode mà không làm hỏng luồng vận hành nếu console có encoding cũ.
- complete_v1_source_order_writer.py
- universal_app.py
- excel_helpers.py