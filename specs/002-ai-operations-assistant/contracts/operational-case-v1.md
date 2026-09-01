# Internal Contract: Operational Case v1

> **Contract Identifier**: `contracts/operational-case-v1.md`  
> **Schema Version**: `1.0.0`  
> **Target Service**: `src/services/operations_case_service.py`  
> **Safety Boundary**: Read-only, Local-only, Fail-closed. No runtime code changes.

---

## 1. Input Specification

| Parameter | Type | Mandatory | Description & Validation |
|---|---|:---:|---|
| `history_root` | `str \| Path` | Yes | Path to the project `RUN_HISTORY` directory containing `run_history.db`. Must exist. |
| `run_id` | `str` | Yes | Terminal run identifier. Must exist in `planning_runs` table of `run_history.db`. |
| `language` | `str` | Yes | UI language code: `"vi"` (default), `"en"`, or `"ja"`. |

---

## 2. Consumed SQLite Fields (`run_history.db` -> `planning_runs`)

The service opens `<history_root>/run_history.db` in **read-only** mode (`sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)` or standard read query) and extracts:

| Field Name | SQLite Type | Consumed By | Purpose / Invariants |
|---|---|---|---|
| `run_id` | `TEXT` | `OperationalCase.run_id` | Primary key; exact match required. |
| `fiscal_year` | `INTEGER` | `OperationalCase.fiscal_year` | Year of run; must match workspace folder name `FY<fiscal_year>`. |
| `status` | `TEXT` | `OperationalCase.status` | Must be terminal: `FAILED`, `PRECHECK_FAILED`, `SUCCEEDED_INCOMPLETE`, `SUCCEEDED`, or `LEGACY_FY2027`. Non-terminal `RUNNING` is rejected. |
| `started_at` | `TEXT` | `OperationalCase.evidence` | ISO 8601 UTC timestamp. |
| `finished_at` | `TEXT` | `OperationalCase.evidence` | ISO 8601 UTC timestamp. |
| `selected_cost_center` | `TEXT` | `OperationalCase.cost_center_scope` | Specific CC (e.g. `"1412000040"`) or `None`/`"ALL"`. Never inferred from another run. |
| `source_paths_json` | `TEXT` | `EvidenceReference` | Parsed as `dict[str, list[str]]`. Paths must resolve within project boundary. |
| `source_checksums_json` | `TEXT` | `EvidenceReference` | Parsed as `dict[str, list[dict[str, str]]]`. Contains `{"path": ..., "sha256": ...}`. |
| `template_checksum` | `TEXT` | `EvidenceReference` | SHA-256 hash of `FORM.xlsx` template. |
| `exchange_rate` | `REAL` | `OperationalCase.evidence` | Effective FX rate recorded for the run. |
| `exchange_rate_source` | `TEXT` | `OperationalCase.evidence` | Provenance of the effective FX rate. |
| `output_path` | `TEXT` | `OperationalCase.evidence` | Destination folder path (e.g. `OUTPUT_FY2027`). |
| `database_path` | `TEXT` | `OperationalCase.evidence` | Workspace DB path (`<workspace>/run.db`). |
| `error_summary` | `TEXT` | `OperationalCase.summary` | High-level failure description if available. |
| `application_version` | `TEXT` | `OperationalCase.evidence` | Version string (e.g. `"0.1.6"`). |
| `created_at` | `TEXT` | `OperationalCase.evidence` | Catalog record creation timestamp. |

---

## 3. Consumed Workspace Files & Fields (`<history_root>/FY<FY>/<run_id>/`)

All files are read from `<workspace_dir>`: `<history_root>/FY<fiscal_year>/<run_id>/`.

### A. `run_manifest.json`
- **Location**: `<workspace_dir>/run_manifest.json`
- **Required Fields**:
  - `run_id` (`str`): Must match SQLite `run_id`.
  - `fiscal_year` (`int`): Must match SQLite `fiscal_year`.
  - `workspace_dir` (`str`): Canonical workspace path.
  - `resolved_sources` (`dict[str, list[str]]`): Source file list per category.
  - `source_checksums` (`dict[str, list[dict[str, str]]]`): Verified source file SHA-256 list.
  - `template_path` (`str`): Path to template FORM.
  - `template_checksum` (`str`): Template hash.
  - `exchange_rate` (`float`) & `exchange_rate_source` (`str`): FX parameters.

### B. `reports/pipeline_stage_evidence.json`
- **Location**: `<workspace_dir>/reports/pipeline_stage_evidence.json`
- **Required Fields**:
  - `schema_version` (`int`): Version integer (expected `1`).
  - `run_id` (`str`): Must match `run_id`.
  - `status` (`str`): Pipeline terminal status.
  - `started_at` (`str`): Stage-evidence creation timestamp.
  - `current_stage` (`str | None`): Active stage; must be empty for a terminal run.
  - `finished_at` (`str`): Present for a terminal run.
  - `total_elapsed_seconds` (`float`): Total run duration.
  - `error_summary` (`str`, optional): Overall pipeline error summary; absent when no error was recorded.
  - `stages` (`list[dict]`): Ordered stage list. For each stage:
    - `name` (`str`): Stage identifier currently emitted by the pipeline, such as `"preflight"`, `"initialize_database"`, `"import_sources"`, `"validate_staffing"`, `"allocation"`, `"export_workbooks"`, `"audit_reports"`, or `"publication"`.
    - `status` (`str`): `"PASS"` or `"FAIL"`.
    - `elapsed_seconds` (`float`): Stage duration.
    - `finished_at` (`str`): Timestamp.
    - `details` (`dict`, optional): Additional evidence emitted for a passed stage.
    - `error_summary` (`str`, optional): Specific failure message when `status == "FAIL"`.

### C. `reports/preflight_report.json`
- **Location**: `<workspace_dir>/reports/preflight_report.json`
- **Required Fields**:
  - `fiscal_year` (`int`): Fiscal year.
  - `ok` (`bool`): True only when `issues` is empty.
  - `can_continue_incomplete` (`bool`): True when no blocking issue exists but at least one source is explicitly skipped.
  - `issues` (`list[dict]`): Validation findings. Each issue contains:
    - `category` (`str`): Source category key.
    - `selected_path` (`str`): Selected source path, possibly empty.
    - `detected_fiscal_year` (`int | None`) and `expected_fiscal_year` (`int`): FY evidence.
    - `status` (`str`) and `code` (`str`): Source-validation outcome and stable error code.
    - `severity` (`str`): `"BLOCKING"` or `"SOURCE_SKIPPED"`.
    - `impact` (`str`), `reason` (`str`), and `required_action` (`str`): User-facing problem and required correction.
    - `checksum` (`str | None`), `sheet` (`str | None`), and `period_coverage` (`list[str]`): Additional source evidence.
  - `checks` (`list[dict]`): Source checks using the same source-evidence keys, including `expected_fiscal_year` and no issue-only `code`/`impact` fields.
  - `resolved_sources` (`dict[str, list[str]]`): All sources resolved by preflight.
  - `usable_sources` (`dict[str, list[str]]`): Sources approved for this run after preflight.
  - `incomplete_run` (`bool`): Flag for incomplete source category runs.
  - `skipped_categories` (`list[str]`): Categories omitted from calculation.

### D. `reports/failure_traceback.txt`
- **Location**: `<workspace_dir>/reports/failure_traceback.txt`
- **Status**: Optional (present only when pipeline encounters an unhandled exception or explicit error).
- **Format**:
  - Line 1: `<ExceptionClass>: <ErrorMessage>`
  - Lines 3+: Python traceback stack.
- **Consumption**: Parsed to extract exception class name (e.g. `OutputPublicationLockedError`, `FileNotFoundError`, `KeyError`) and root cause line.

---

## 4. OperationalCase Output Data Structure

```python
@dataclass(frozen=True)
class EvidenceReference:
    type: str          # "catalog_row" | "run_manifest" | "preflight_report" | "stage_evidence" | "failure_traceback"
    local_path: str    # Absolute/relative path to evidence file
    locator: str       # JSON key, table column, or line range
    summary: str       # Short summary of what this evidence establishes
    verification: str  # "verified" | "missing" | "mismatch"

@dataclass(frozen=True)
class OperationalCase:
    case_id: str                          # Format: "case-<run_id>"
    run_id: str                           # Target run ID
    fiscal_year: int                      # Target FY
    cost_center_scope: str                # CC code or "ALL"
    status: str                           # Terminal status
    stage: str                            # Failing stage or "none"
    classification: str                   # Error classification code or "unknown"
    confidence: str                       # "confirmed" | "possible" | "unknown"
    summary: str                          # Localized plain-language summary
    evidence: tuple[EvidenceReference, ...] # Ordered verified evidence
    guidance: tuple[str, ...]             # Ordered localized safe manual next steps
    presentation: GuidancePresentation | None # Complete current-language primary presentation
```

---

## 5. Deterministic Error Classification & Guidance Rules

| Classification Code | Trigger Conditions (from verified evidence) | Confidence | Required Evidence | Standard Guidance Summary |
|---|---|:---:|---|---|
| `missing_staffing_baseline` | A failed `"validate_staffing"` stage contains the verified missing-manual-baseline signal (for example, `"chưa có Tổng số người tháng"`). The preflight report alone must not match this error. | `confirmed` | `pipeline_stage_evidence.json`, `failure_traceback.txt` | Hướng dẫn dùng “Nhập nhân sự thủ công” trong MP2027 để nhập Tổng số người tháng 03, lưu lại, quét lại và chạy tính toán. |
| `blocked_output_file_lock` | Exception class == `OutputPublicationLockedError` OR traceback contains `PermissionError` during output publication | `confirmed` | `failure_traceback.txt`, `pipeline_stage_evidence.json` | Hướng dẫn đóng các tệp Excel đang mở, cửa sổ File Explorer tại thư mục `OUTPUT_FY*` và thử lại. |
| `preflight_source_validation_failure` | Preflight `ok == false` with `severity == "BLOCKING"` issue(s) in source workbooks (`facility`, `fixed_assets`, etc.) | `confirmed` | `preflight_report.json` | Hướng dẫn kiểm tra file nguồn tương ứng theo `selected_path`, `reason`, và `required_action` trong báo cáo tiền trạm. |
| `unknown` | Any failure not matching the above approved conditions, or missing critical evidence | `unknown` | Available evidence items | Nêu rõ nguyên nhân chưa được xác nhận, liệt kê bằng chứng hiện có và hướng dẫn kiểm tra nhật ký thủ công. |

---

## 6. Safety Envelopes & Rejection Invariants

1. **Strict No-Write Policy**:
   - The service MUST NOT create, modify, delete, or overwrite any file on disk.
   - SHA-256 hashes of all workspace files before case assembly must match hashes after case assembly.
2. **Path Traversal & Boundary Guard**:
   - All referenced file paths must reside strictly within `<workspace_dir>` or the verified project directory.
   - Any path resolving outside `<workspace_dir>` (except approved static project docs) must be flagged with `verification="mismatch"` and rejected from diagnostic consideration.
3. **Missing File Handling**:
   - Missing files (e.g. absent `failure_traceback.txt` on successful runs) MUST NOT trigger runtime exceptions. They must be recorded as `EvidenceReference(verification="missing")`.
4. **No Made-Up Repair Actions**:
   - Guidance items must ONLY contain manual user inspection steps. They MUST NOT contain executable shell commands, code modifications, or automatic rerun triggers.
