# Manual Special Cost Inheritance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve direct Excel entries for manual special costs per CC across reruns and fiscal years.

**Architecture:** A workbook-local, very-hidden metadata sheet identifies the manual section. The export pipeline regenerates only common costs, then restores an exact manual-row snapshot below the new dynamic common-cost end.

**Tech Stack:** Python 3.13, openpyxl, pytest, Tkinter.

---

### Task 1: Workbook manual-section contract

- [x] Add test-first coverage for legacy capture, metadata capture, dynamic relocation and safety failures.
- [x] Implement workbook snapshot/restore and hidden metadata in a focused engine module.
- [x] Verify snapshot preserves formulas, values, styles, row order and source workbook immutability.

### Task 2: Pipeline integration

- [x] Add the optional per-FY inheritance directory and legacy start map to project/run configuration.
- [x] Restore a current-FY manual section first; otherwise use configured prior-FY source; otherwise create an empty protected section.
- [x] Run restoration only after the complete-v1 common-cost writer and before publication.

### Task 3: User interaction and localization

- [x] Add Vietnamese, Japanese and English text for inheritance settings and result summaries.
- [x] Add a configuration control for the optional previous-FY result folder and a per-CC legacy-start entry.

### Task 4: Acceptance

- [x] Run focused unit/integration tests and the relevant export suite.
- [x] Only after passing, mark `Hạng mục cần cải tiến!B856:C858` green in the user-provided workbook.
