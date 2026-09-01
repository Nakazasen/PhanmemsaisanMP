"""Dịch vụ lắp ráp và quản lý trường hợp vận hành (Operational Case Service) cho trợ lý hỗ trợ.

Mô-đun này cung cấp các mô hình dữ liệu bất biến (frozen dataclasses) đại diện cho
trường hợp hỗ trợ vận hành (OperationalCase) và tham chiếu bằng chứng (EvidenceReference).
Toàn bộ dữ liệu là chỉ đọc (read-only) và cục bộ (local-only).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import sqlite3
from typing import Any

from src.services.operations_knowledge import (
    ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK,
    ERROR_CODE_MISSING_STAFFING_BASELINE,
    ERROR_CODE_PREFLIGHT_SOURCE_VALIDATION_FAILURE,
    GuidancePresentation,
    SUPPORTED_LANGUAGES,
    get_knowledge_entry,
    is_blocked_output_file_lock_match,
    is_missing_staffing_baseline_match,
    is_preflight_source_validation_failure_match,
)


_EVIDENCE_VERIFICATIONS = frozenset({"verified", "missing", "mismatch"})
_TERMINAL_RUN_STATUSES = frozenset({
    "FAILED",
    "PRECHECK_FAILED",
    "SUCCEEDED_INCOMPLETE",
    "SUCCEEDED",
    "LEGACY_FY2027",
})
_CASE_CONFIDENCES = frozenset({"confirmed", "possible", "unknown"})


@dataclass(frozen=True)
class EvidenceReference:
    """Tham chiếu đến một nguồn bằng chứng cụ thể thuộc lần chạy hoặc tài liệu chuẩn."""

    type: str  # "catalog_row" | "run_manifest" | "preflight_report" | "stage_evidence" | "failure_traceback" | "documentation"
    local_path: str  # Đường dẫn tệp bằng chứng cục bộ
    locator: str  # Vị trí định vị: JSON key, tên cột bảng hoặc dòng lỗi
    summary: str  # Diễn giải ngắn gọn về bằng chứng này
    verification: str = "verified"  # "verified" | "missing" | "mismatch"

    def __post_init__(self) -> None:
        if not isinstance(self.type, str) or not self.type.strip():
            raise ValueError("EvidenceReference.type không được để trống.")
        if not isinstance(self.local_path, str) or not self.local_path.strip():
            raise ValueError("EvidenceReference.local_path không được để trống.")
        if not isinstance(self.locator, str) or not self.locator.strip():
            raise ValueError("EvidenceReference.locator không được để trống.")
        if not isinstance(self.summary, str) or not self.summary.strip():
            raise ValueError("EvidenceReference.summary không được để trống.")
        if self.verification not in _EVIDENCE_VERIFICATIONS:
            raise ValueError("EvidenceReference.verification không hợp lệ.")


@dataclass(frozen=True)
class OperationalCase:
    """Trường hợp hỗ trợ vận hành chỉ đọc được lắp ráp từ bằng chứng của một lần chạy."""

    case_id: str  # Định danh duy nhất: "case-<run_id>"
    run_id: str  # Mã lần chạy (run_id) từ catalog/workspace
    fiscal_year: int  # Năm tài chính (FY)
    cost_center_scope: str  # Mã Cost Center (ví dụ "1412000040") hoặc "ALL"
    status: str  # Trạng thái kết thúc: "FAILED" | "PRECHECK_FAILED" | "SUCCEEDED" | "SUCCEEDED_INCOMPLETE"
    stage: str  # Giai đoạn lỗi/cuối cùng theo evidence, hoặc "unavailable"
    classification: str  # Mã phân loại lỗi hoặc "unknown"
    confidence: str  # Mức độ tin cậy: "confirmed" | "possible" | "unknown"
    summary: str  # Tóm tắt nguyên nhân/tình trạng bằng ngôn ngữ tự nhiên
    evidence: tuple[EvidenceReference, ...] = field(default_factory=tuple)  # Danh sách bằng chứng đã xác minh
    guidance: tuple[str, ...] = field(default_factory=tuple)  # Các bước hướng dẫn thủ công an toàn
    presentation: GuidancePresentation | None = None  # Nội dung hiển thị đầy đủ theo ngôn ngữ đang dùng

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id.strip():
            raise ValueError("OperationalCase.case_id không được để trống.")
        if not isinstance(self.run_id, str) or not self.run_id.strip():
            raise ValueError("OperationalCase.run_id không được để trống.")
        if type(self.fiscal_year) is not int or self.fiscal_year <= 2000:
            raise ValueError(f"OperationalCase.fiscal_year không hợp lệ: {self.fiscal_year}")
        if not isinstance(self.cost_center_scope, str) or not self.cost_center_scope.strip():
            raise ValueError("OperationalCase.cost_center_scope không được để trống.")
        if self.status not in _TERMINAL_RUN_STATUSES:
            raise ValueError("OperationalCase.status phải là trạng thái kết thúc hợp lệ.")
        if not isinstance(self.stage, str) or not self.stage.strip():
            raise ValueError("OperationalCase.stage không được để trống.")
        if not isinstance(self.classification, str) or not self.classification.strip():
            raise ValueError("OperationalCase.classification không được để trống.")
        if self.confidence not in _CASE_CONFIDENCES:
            raise ValueError("OperationalCase.confidence không hợp lệ.")
        if not isinstance(self.summary, str) or not self.summary.strip():
            raise ValueError("OperationalCase.summary không được để trống.")

        # Tự động chuẩn hóa sequence sang tuple nếu người dùng truyền list
        if not isinstance(self.evidence, tuple):
            object.__setattr__(self, "evidence", tuple(self.evidence))
        if not isinstance(self.guidance, tuple):
            object.__setattr__(self, "guidance", tuple(self.guidance))
        if not all(isinstance(item, EvidenceReference) for item in self.evidence):
            raise ValueError("OperationalCase.evidence chỉ được chứa EvidenceReference.")
        if not all(isinstance(item, str) and item.strip() for item in self.guidance):
            raise ValueError("OperationalCase.guidance chỉ được chứa hướng dẫn không rỗng.")
        if self.presentation is not None and not isinstance(self.presentation, GuidancePresentation):
            raise ValueError("OperationalCase.presentation phải là GuidancePresentation hoặc None.")


def validate_workspace_evidence_path(
    workspace_dir: str | Path,
    candidate_path: str | Path,
    *,
    must_exist: bool = True,
) -> Path:
    """Xác thực đường dẫn bằng chứng nằm hoàn toàn bên trong thư mục workspace của lần chạy.

    Quy tắc an toàn:
    1. workspace_dir không được rỗng, phải tồn tại và là một thư mục trên đĩa.
    2. candidate_path (tương đối hoặc tuyệt đối) sau khi resolve() phải nằm bên
       trong workspace_dir (chống Path Traversal '..', symbolic links trỏ ra ngoài).
    3. Ngăn chặn tuyệt đối việc tham chiếu sang workspace của FY khác hoặc run_id khác.
    4. Nếu must_exist=True (mặc định), tệp/đường dẫn phải tồn tại thực sự trên đĩa.
    """
    if not workspace_dir or (isinstance(workspace_dir, str) and not workspace_dir.strip()):
        raise ValueError("workspace_dir không được để trống.")
    if not candidate_path or (isinstance(candidate_path, str) and not candidate_path.strip()):
        raise ValueError("candidate_path không được để trống.")

    ws_root = Path(workspace_dir).resolve()
    if not ws_root.is_dir():
        raise FileNotFoundError(f"Thư mục workspace không tồn tại: {ws_root}")

    candidate = Path(candidate_path)
    if not candidate.is_absolute():
        resolved_candidate = (ws_root / candidate).resolve()
    else:
        resolved_candidate = candidate.resolve()

    try:
        resolved_candidate.relative_to(ws_root)
    except ValueError as exc:
        raise ValueError(
            f"Đường dẫn bằng chứng nằm ngoài phạm vi workspace của lần chạy: "
            f"candidate='{candidate_path}', workspace='{ws_root}'"
        ) from exc

    if must_exist and not resolved_candidate.exists():
        raise FileNotFoundError(f"Tệp bằng chứng không tồn tại: {resolved_candidate}")

    return resolved_candidate


def lookup_terminal_run_catalog_record(
    history_root: str | Path,
    run_id: str,
) -> dict[str, Any]:
    """Tra cứu bản ghi một lần chạy kết thúc trong <history_root>/run_history.db ở chế độ chỉ đọc.

    Quy tắc an toàn:
    1. Không tự tạo thư mục history_root hoặc tệp run_history.db nếu chưa tồn tại.
    2. Bắt buộc mở kết nối SQLite ở chế độ chỉ đọc tuyệt đối (URI mode=ro).
    3. Chỉ chấp nhận các lần chạy có trạng thái kết thúc (terminal):
       FAILED, PRECHECK_FAILED, SUCCEEDED_INCOMPLETE, SUCCEEDED, LEGACY_FY2027.
    4. Từ chối lần chạy đang chạy (RUNNING) hoặc trạng thái không hợp lệ.
    5. Không làm thay đổi nội dung hoặc mã băm SHA-256 của run_history.db.
    """
    if not history_root or (isinstance(history_root, str) and not history_root.strip()):
        raise ValueError("history_root không được để trống.")
    if not run_id or (isinstance(run_id, str) and not run_id.strip()):
        raise ValueError("run_id không được để trống.")

    history_path = Path(history_root).resolve()
    db_path = history_path / "run_history.db"
    if not db_path.is_file():
        raise FileNotFoundError(
            f"Cơ sở dữ liệu danh mục lịch sử không tồn tại: {db_path}"
        )

    db_uri = f"{db_path.as_uri()}?mode=ro"
    conn = sqlite3.connect(db_uri, uri=True)
    try:
        cursor = conn.execute(
            "SELECT * FROM planning_runs WHERE run_id = ?", (run_id.strip(),)
        )
        row = cursor.fetchone()
        if row is None:
            raise KeyError(
                f"Không tìm thấy lần chạy với run_id='{run_id}' trong danh mục {db_path}."
            )

        columns = [desc[0] for desc in cursor.description]
        record = dict(zip(columns, row))
    finally:
        conn.close()

    status = str(record.get("status") or "")
    if status not in _TERMINAL_RUN_STATUSES:
        raise ValueError(
            f"Lần chạy '{run_id}' đang ở trạng thái không kết thúc ({status}). "
            "Trợ lý vận hành chỉ hỗ trợ các lần chạy đã kết thúc."
        )

    return record


# ---------------------------------------------------------------------------
# T007: Read-Only Evidence Loaders for Run Workspace
# ---------------------------------------------------------------------------

def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_valid_run_manifest_payload(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    return (
        _is_nonempty_string(payload.get("run_id"))
        and type(payload.get("fiscal_year")) is int
        and _is_nonempty_string(payload.get("workspace_dir"))
        and isinstance(payload.get("resolved_sources"), dict)
        and isinstance(payload.get("source_checksums"), dict)
        and _is_nonempty_string(payload.get("template_path"))
        and _is_nonempty_string(payload.get("template_checksum"))
        and isinstance(payload.get("exchange_rate"), (int, float))
        and not isinstance(payload.get("exchange_rate"), bool)
        and _is_nonempty_string(payload.get("exchange_rate_source"))
    )


def _is_valid_preflight_report_payload(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    return (
        type(payload.get("fiscal_year")) is int
        and type(payload.get("ok")) is bool
        and type(payload.get("can_continue_incomplete")) is bool
        and isinstance(payload.get("issues"), list)
        and isinstance(payload.get("checks"), list)
        and isinstance(payload.get("resolved_sources"), dict)
        and isinstance(payload.get("usable_sources"), dict)
        and type(payload.get("incomplete_run")) is bool
        and isinstance(payload.get("skipped_categories"), list)
    )


def _is_valid_pipeline_stage_payload(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    if not (
        type(payload.get("schema_version")) is int
        and payload.get("schema_version") == 1
        and _is_nonempty_string(payload.get("run_id"))
        and _is_nonempty_string(payload.get("status"))
        and _is_nonempty_string(payload.get("started_at"))
        and payload.get("current_stage") in (None, "")
        and isinstance(payload.get("stages"), list)
    ):
        return False
    if payload.get("status") != "RUNNING" and not (
        _is_nonempty_string(payload.get("finished_at"))
        and isinstance(payload.get("total_elapsed_seconds"), (int, float))
        and not isinstance(payload.get("total_elapsed_seconds"), bool)
    ):
        return False
    return all(
        isinstance(stage, dict)
        and _is_nonempty_string(stage.get("name"))
        and stage.get("status") in {"PASS", "FAIL"}
        and isinstance(stage.get("elapsed_seconds"), (int, float))
        and not isinstance(stage.get("elapsed_seconds"), bool)
        and _is_nonempty_string(stage.get("finished_at"))
        for stage in payload["stages"]
    )

def load_run_manifest_evidence(
    workspace_dir: str | Path,
) -> tuple[EvidenceReference, dict[str, Any] | None]:
    """Tải và xác thực bằng chứng tệp cấu hình lần chạy (run_manifest.json)."""
    rel_path = "run_manifest.json"
    resolved_path = validate_workspace_evidence_path(
        workspace_dir, rel_path, must_exist=False
    )

    if not resolved_path.is_file():
        return (
            EvidenceReference(
                type="run_manifest",
                local_path=rel_path,
                locator="file",
                summary="Tệp run_manifest.json không tồn tại trong workspace",
                verification="missing",
            ),
            None,
        )

    try:
        raw_text = resolved_path.read_text(encoding="utf-8")
        payload = json.loads(raw_text)
        if not _is_valid_run_manifest_payload(payload):
            raise TypeError("Nội dung run_manifest.json không phải là JSON Object.")
    except Exception:
        return (
            EvidenceReference(
                type="run_manifest",
                local_path=rel_path,
                locator="file",
                summary="Tệp run_manifest.json bị hỏng hoặc không đúng định dạng JSON",
                verification="mismatch",
            ),
            None,
        )

    fy = payload.get("fiscal_year")
    run_id = payload.get("run_id")
    summary = (
        f"Cấu hình lần chạy FY{fy} (run_id: {run_id})"
        if fy and run_id
        else "Cấu hình lần chạy run_manifest.json"
    )
    return (
        EvidenceReference(
            type="run_manifest",
            local_path=rel_path,
            locator="file",
            summary=summary,
            verification="verified",
        ),
        payload,
    )


def load_preflight_report_evidence(
    workspace_dir: str | Path,
) -> tuple[EvidenceReference, dict[str, Any] | None]:
    """Tải và xác thực bằng chứng báo cáo tiền trạm (reports/preflight_report.json)."""
    rel_path = "reports/preflight_report.json"
    resolved_path = validate_workspace_evidence_path(
        workspace_dir, rel_path, must_exist=False
    )

    if not resolved_path.is_file():
        return (
            EvidenceReference(
                type="preflight_report",
                local_path=rel_path,
                locator="file",
                summary="Báo cáo kiểm tra tiền trạm reports/preflight_report.json không tồn tại",
                verification="missing",
            ),
            None,
        )

    try:
        raw_text = resolved_path.read_text(encoding="utf-8")
        payload = json.loads(raw_text)
        if not _is_valid_preflight_report_payload(payload):
            raise TypeError("Nội dung preflight_report.json không phải là JSON Object.")
    except Exception:
        return (
            EvidenceReference(
                type="preflight_report",
                local_path=rel_path,
                locator="file",
                summary="Tệp reports/preflight_report.json bị hỏng hoặc không đúng định dạng JSON",
                verification="mismatch",
            ),
            None,
        )

    valid_flag = payload["ok"]
    issues = payload.get("issues")
    issues_count = len(issues) if isinstance(issues, list) else 0
    status_label = "Hợp lệ" if valid_flag else "Phát hiện lỗi/cảnh báo"
    summary = f"Báo cáo tiền trạm: {status_label} ({issues_count} vấn đề)"

    return (
        EvidenceReference(
            type="preflight_report",
            local_path=rel_path,
            locator="file",
            summary=summary,
            verification="verified",
        ),
        payload,
    )


def load_pipeline_stage_evidence(
    workspace_dir: str | Path,
) -> tuple[EvidenceReference, dict[str, Any] | None]:
    """Tải và xác thực bằng chứng tiến trình các bước pipeline (reports/pipeline_stage_evidence.json)."""
    rel_path = "reports/pipeline_stage_evidence.json"
    resolved_path = validate_workspace_evidence_path(
        workspace_dir, rel_path, must_exist=False
    )

    if not resolved_path.is_file():
        return (
            EvidenceReference(
                type="stage_evidence",
                local_path=rel_path,
                locator="file",
                summary="Bằng chứng các bước pipeline reports/pipeline_stage_evidence.json không tồn tại",
                verification="missing",
            ),
            None,
        )

    try:
        raw_text = resolved_path.read_text(encoding="utf-8")
        payload = json.loads(raw_text)
        if not _is_valid_pipeline_stage_payload(payload):
            raise TypeError("Nội dung pipeline_stage_evidence.json không phải là JSON Object.")
    except Exception:
        return (
            EvidenceReference(
                type="stage_evidence",
                local_path=rel_path,
                locator="file",
                summary="Tệp reports/pipeline_stage_evidence.json bị hỏng hoặc không đúng định dạng JSON",
                verification="mismatch",
            ),
            None,
        )

    status = str(payload.get("status") or "unknown")
    stages = payload.get("stages")
    stages_count = len(stages) if isinstance(stages, list) else 0
    summary = f"Tiến trình pipeline: trạng thái {status} ({stages_count} bước thực hiện)"

    return (
        EvidenceReference(
            type="stage_evidence",
            local_path=rel_path,
            locator="file",
            summary=summary,
            verification="verified",
        ),
        payload,
    )


def load_failure_traceback_evidence(
    workspace_dir: str | Path,
) -> tuple[EvidenceReference, str | None]:
    """Tải và xác thực bằng chứng dấu vết ngoại lệ lỗi (reports/failure_traceback.txt)."""
    rel_path = "reports/failure_traceback.txt"
    resolved_path = validate_workspace_evidence_path(
        workspace_dir, rel_path, must_exist=False
    )

    if not resolved_path.is_file():
        return (
            EvidenceReference(
                type="failure_traceback",
                local_path=rel_path,
                locator="file",
                summary="Không có tệp dấu vết lỗi reports/failure_traceback.txt (lần chạy không phát sinh ngoại lệ chưa bắt)",
                verification="missing",
            ),
            None,
        )

    try:
        content = resolved_path.read_text(encoding="utf-8")
    except Exception:
        return (
            EvidenceReference(
                type="failure_traceback",
                local_path=rel_path,
                locator="file",
                summary="Tệp reports/failure_traceback.txt bị lỗi đọc hoặc mã hóa ký tự",
                verification="mismatch",
            ),
            None,
        )

    first_line = content.strip().splitlines()[0] if content.strip() else ""
    if not first_line or ":" not in first_line:
        return (
            EvidenceReference(
                type="failure_traceback",
                local_path=rel_path,
                locator="file",
                summary="Tệp reports/failure_traceback.txt không đúng định dạng exception traceback",
                verification="mismatch",
            ),
            None,
        )
    summary = f"Dấu vết ngoại lệ: {first_line[:120]}"

    return (
        EvidenceReference(
            type="failure_traceback",
            local_path=rel_path,
            locator="file",
            summary=summary,
            verification="verified",
        ),
        content,
    )


# ---------------------------------------------------------------------------
# T008 & T014: Assemble Operational Case
# ---------------------------------------------------------------------------


def _has_required_verified_evidence(
    error_code: str,
    evidence: tuple[EvidenceReference, ...],
) -> bool:
    """Return whether every evidence type required by an approved rule is verified.

    Match predicates prove that the observed signals fit a rule.  This separate
    gate prevents a partial set of files from being presented as a confirmed
    diagnosis when the rule itself requires more evidence.
    """
    entry = get_knowledge_entry(error_code)
    if entry is None:
        return False
    verified_types = {item.type for item in evidence if item.verification == "verified"}
    return set(entry.evidence_requirements).issubset(verified_types)

def assemble_operational_case(
    history_root: str | Path,
    run_id: str,
    language: str = "vi",
) -> OperationalCase:
    """Lắp ráp một trường hợp vận hành chưa phân loại (unclassified OperationalCase) từ một lần chạy đã kết thúc.

    Quy trình và ràng buộc an toàn:
    1. Tra cứu bản ghi danh mục qua lookup_terminal_run_catalog_record(history_root, run_id).
    2. Xác định đường dẫn workspace: <history_root>/FY<fiscal_year>/<run_id>.
    3. Tải 4 bằng chứng workspace qua các loader T007.
    4. Đối chiếu tính nhất quán (Consistency Guard):
       - Nếu run_manifest.json hoặc pipeline_stage_evidence.json có run_id hoặc fiscal_year
         mâu thuẫn với catalog/workspace -> từ chối assembly (ném ValueError).
    5. Xác định stage:
       - Stage bị lỗi ("FAIL") đầu tiên trong pipeline_stage_evidence.json nếu có.
       - Nếu không có FAIL, lấy stage cuối cùng.
       - Nếu stage evidence missing/mismatch hoặc rỗng, gán stage="unavailable".
    6. Sắp xếp thứ tự bằng chứng cố định (5 items):
       catalog_row -> run_manifest -> preflight_report -> stage_evidence -> failure_traceback.
    7. Đối chiếu các quy tắc tri thức đã duyệt (Knowledge Matching) theo language ('vi', 'en', 'ja').
    8. Trả về OperationalCase với classification, confidence, summary và guidance tương ứng.
    """
    lang = str(language).strip().lower() if language else ""
    if lang not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Ngôn ngữ '{language}' không được hỗ trợ. Các ngôn ngữ hợp lệ: {sorted(SUPPORTED_LANGUAGES)}"
        )

    catalog_record = lookup_terminal_run_catalog_record(history_root, run_id)

    fiscal_year = int(catalog_record["fiscal_year"])
    status = str(catalog_record["status"])
    cost_center_scope = str(catalog_record.get("selected_cost_center") or "ALL")
    error_summary = str(catalog_record.get("error_summary") or "").strip()
    case_id = f"case-{run_id}"

    # 1. Bằng chứng danh mục (catalog_row)
    ref_catalog = EvidenceReference(
        type="catalog_row",
        local_path="run_history.db",
        locator=f"planning_runs.run_id={run_id}",
        summary=f"Bản ghi danh mục: trạng thái {status}, FY{fiscal_year}, CC={cost_center_scope}",
        verification="verified",
    )

    # 2. Xác định workspace và nạp 4 bằng chứng
    history_path = Path(history_root).resolve()
    workspace_dir = history_path / f"FY{fiscal_year}" / run_id

    if not workspace_dir.is_dir():
        ref_manifest = EvidenceReference(
            type="run_manifest",
            local_path="run_manifest.json",
            locator="file",
            summary="Thư mục workspace hoặc tệp run_manifest.json không tồn tại",
            verification="missing",
        )
        manifest_payload = None
        ref_preflight = EvidenceReference(
            type="preflight_report",
            local_path="reports/preflight_report.json",
            locator="file",
            summary="Báo cáo kiểm tra tiền trạm reports/preflight_report.json không tồn tại",
            verification="missing",
        )
        preflight_payload = None
        ref_stage = EvidenceReference(
            type="stage_evidence",
            local_path="reports/pipeline_stage_evidence.json",
            locator="file",
            summary="Bằng chứng các bước pipeline reports/pipeline_stage_evidence.json không tồn tại",
            verification="missing",
        )
        stage_payload = None
        ref_trace = EvidenceReference(
            type="failure_traceback",
            local_path="reports/failure_traceback.txt",
            locator="file",
            summary="Không có tệp dấu vết lỗi reports/failure_traceback.txt",
            verification="missing",
        )
        trace_text = None
    else:
        ref_manifest, manifest_payload = load_run_manifest_evidence(workspace_dir)
        ref_preflight, preflight_payload = load_preflight_report_evidence(workspace_dir)
        ref_stage, stage_payload = load_pipeline_stage_evidence(workspace_dir)
        ref_trace, trace_text = load_failure_traceback_evidence(workspace_dir)

    # 3. Kiểm tra tính nhất quán (Consistency Guard / Mismatch Detection)
    if ref_manifest.verification == "verified" and isinstance(manifest_payload, dict):
        m_run_id = manifest_payload.get("run_id")
        m_fy = manifest_payload.get("fiscal_year")
        if m_run_id is not None and str(m_run_id).strip() != run_id:
            raise ValueError(
                f"Mâu thuẫn run_id giữa run_manifest.json ('{m_run_id}') và danh mục ('{run_id}')."
            )
        if m_fy is not None and int(m_fy) != fiscal_year:
            raise ValueError(
                f"Mâu thuẫn fiscal_year giữa run_manifest.json ({m_fy}) và danh mục ({fiscal_year})."
            )
        manifest_workspace = Path(str(manifest_payload["workspace_dir"])).resolve()
        if manifest_workspace != workspace_dir.resolve():
            raise ValueError(
                "Mâu thuẫn workspace_dir giữa run_manifest.json và workspace của danh mục."
            )

    if ref_preflight.verification == "verified" and isinstance(preflight_payload, dict):
        preflight_fy = int(preflight_payload["fiscal_year"])
        if preflight_fy != fiscal_year:
            raise ValueError(
                f"Mâu thuẫn fiscal_year giữa preflight_report.json ({preflight_fy}) và danh mục ({fiscal_year})."
            )

    if ref_stage.verification == "verified" and isinstance(stage_payload, dict):
        # pipeline_stage_evidence.json v1 does not carry fiscal_year; its run_id
        # is the available identity field to cross-check against the catalog.
        s_run_id = stage_payload.get("run_id")
        if s_run_id is not None and str(s_run_id).strip() != run_id:
            raise ValueError(
                f"Mâu thuẫn run_id giữa pipeline_stage_evidence.json ('{s_run_id}') và danh mục ('{run_id}')."
            )

    # 4. Xác định stage từ pipeline_stage_evidence
    stage = "unavailable"
    if ref_stage.verification == "verified" and isinstance(stage_payload, dict):
        stages = stage_payload.get("stages")
        if isinstance(stages, list) and len(stages) > 0:
            failed_stages = [
                s for s in stages if isinstance(s, dict) and str(s.get("status")).upper() == "FAIL"
            ]
            if failed_stages:
                stage = str(failed_stages[0].get("name") or "unavailable")
            else:
                last_stage = stages[-1]
                if isinstance(last_stage, dict):
                    stage = str(last_stage.get("name") or "unavailable")
                else:
                    stage = "unavailable"

    # 5. Thứ tự evidence cố định
    evidence = (ref_catalog, ref_manifest, ref_preflight, ref_stage, ref_trace)

    # 6. Đối chiếu kiến thức đã duyệt (Knowledge Matching)
    matched_codes: list[str] = []

    # Quy tắc 1: missing_staffing_baseline
    # The approved rule also requires a recorded failure trace; the generic
    # evidence gate below enforces that contract rather than merely matching a
    # phrase in a single report.
    if (
        is_missing_staffing_baseline_match(stage_payload, error_summary=error_summary)
        and _has_required_verified_evidence(ERROR_CODE_MISSING_STAFFING_BASELINE, evidence)
    ):
        matched_codes.append(ERROR_CODE_MISSING_STAFFING_BASELINE)

    # Quy tắc 2: blocked_output_file_lock
    # Yêu cầu: stage_evidence verified, failure_traceback verified hoặc có trace_text,
    # và is_blocked_output_file_lock_match
    if (
        is_blocked_output_file_lock_match(
            stage_payload,
            traceback_text=trace_text or "",
            error_summary=error_summary,
        )
        and _has_required_verified_evidence(ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK, evidence)
    ):
        matched_codes.append(ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK)

    # Quy tắc 3: preflight_source_validation_failure
    # Yêu cầu: preflight_report verified và is_preflight_source_validation_failure_match
    if (
        is_preflight_source_validation_failure_match(preflight_payload)
        and _has_required_verified_evidence(
            ERROR_CODE_PREFLIGHT_SOURCE_VALIDATION_FAILURE, evidence
        )
    ):
        matched_codes.append(ERROR_CODE_PREFLIGHT_SOURCE_VALIDATION_FAILURE)

    # 7. Xử lý phân loại (Confirmed khi khớp đúng 1 quy tắc)
    if len(matched_codes) == 1:
        matched_code = matched_codes[0]
        entry = get_knowledge_entry(matched_code)
        if entry and lang in entry.translations:
            presentation = entry.translations[lang]
            return OperationalCase(
                case_id=case_id,
                run_id=run_id,
                fiscal_year=fiscal_year,
                cost_center_scope=cost_center_scope,
                status=status,
                stage=stage,
                classification=matched_code,
                confidence="confirmed",
                summary=presentation.title,
                evidence=evidence,
                guidance=presentation.what_to_do,
                presentation=presentation,
            )

    # 8. Không khớp, mơ hồ (>1 quy tắc) hoặc thiếu bằng chứng: fallback unknown
    presentation = _create_unknown_fallback_presentation(
        lang, fiscal_year, cost_center_scope=cost_center_scope, status=status
    )

    return OperationalCase(
        case_id=case_id,
        run_id=run_id,
        fiscal_year=fiscal_year,
        cost_center_scope=cost_center_scope,
        status=status,
        stage=stage,
        classification="unknown",
        confidence="unknown",
        summary=presentation.title,
        evidence=evidence,
        guidance=presentation.what_to_do,
        presentation=presentation,
    )


def _create_unknown_fallback_presentation(
    language: str,
    fiscal_year: int,
    cost_center_scope: str = "ALL",
    status: str = "",
) -> GuidancePresentation:
    """Tạo đối tượng GuidancePresentation chuẩn tắc cho trường hợp chưa xác nhận (unknown/unconfirmed).

    Được áp dụng khi:
    - Không khớp quy tắc tri thức nào;
    - Thiếu / hỏng / bất đồng bộ (mismatch) bằng chứng;
    - Nhiều hơn một quy tắc cùng khớp (ambiguous).
    """
    lang = str(language).strip().lower() if language else "vi"
    cc_label = (
        str(cost_center_scope).strip()
        if cost_center_scope and cost_center_scope != "ALL"
        else ""
    )

    # A successful run has no failure cause to diagnose.  Keeping it under the
    # same read-only case path is useful, but describing it as an unconfirmed
    # problem would create a false alarm for the user.
    if str(status).upper() == "SUCCEEDED":
        if lang == "vi":
            scope_desc = f"năm tài chính FY{fiscal_year}"
            if cc_label:
                scope_desc += f", phòng ban {cc_label}"
            return GuidancePresentation(
                language="vi",
                title="Lần chạy đã hoàn tất",
                what_happened=(
                    f"Lần chạy tính toán thuộc {scope_desc} đã hoàn tất. "
                    "Bằng chứng hiện có không ghi nhận lỗi cần xử lý."
                ),
                why_it_happened=(
                    "Không có vấn đề nào trong lần chạy này cần xác nhận nguyên nhân."
                ),
                what_to_do=(
                    "1. Mở và kiểm tra các tệp kết quả đã xuất.",
                    "2. Nếu số liệu chưa như mong đợi, đối chiếu lại dữ liệu đầu vào và kết quả.",
                    "3. Nếu vẫn cần hỗ trợ, liên hệ quản trị vận hành và cung cấp thông tin lần chạy này.",
                ),
                confidence_label="Không có lỗi được ghi nhận",
                evidence_label="Bằng chứng và nhật ký vận hành",
                technical_details_label="Chi tiết kỹ thuật từ hệ thống",
            )
        if lang == "en":
            scope_desc = f"fiscal year FY{fiscal_year}"
            if cc_label:
                scope_desc += f", Cost Center {cc_label}"
            return GuidancePresentation(
                language="en",
                title="Calculation Run Completed",
                what_happened=(
                    f"The calculation run for {scope_desc} completed. "
                    "The available evidence records no error requiring action."
                ),
                why_it_happened=(
                    "There is no issue in this run whose cause needs to be confirmed."
                ),
                what_to_do=(
                    "1. Open and review the exported result files.",
                    "2. If a value is unexpected, compare the input data with the result.",
                    "3. If you still need help, contact the operations support team and provide this run information.",
                ),
                confidence_label="No recorded error",
                evidence_label="Operational evidence and logs",
                technical_details_label="System technical details",
            )
        if lang == "ja":
            scope_desc = f"FY{fiscal_year}年度"
            if cc_label:
                scope_desc += f"、コストセンター {cc_label}"
            return GuidancePresentation(
                language="ja",
                title="計算処理は完了しました",
                what_happened=(
                    f"{scope_desc}の計算処理は完了しました。"
                    "確認できる記録には、対応が必要なエラーはありません。"
                ),
                why_it_happened=(
                    "この実行では、原因の確認が必要な問題は記録されていません。"
                ),
                what_to_do=(
                    "1. 出力された結果ファイルを開いて確認してください。",
                    "2. 想定と異なる数値がある場合は、入力データと結果を照合してください。",
                    "3. さらに支援が必要な場合は、この実行情報を添えて運用管理者に連絡してください。",
                ),
                confidence_label="記録されたエラーはありません",
                evidence_label="運用証拠とログ",
                technical_details_label="システム技術詳細",
            )

    if lang == "vi":
        scope_desc = f"năm tài chính FY{fiscal_year}"
        if cc_label:
            scope_desc += f", phòng ban {cc_label}"
        return GuidancePresentation(
            language="vi",
            title="Chưa thể xác nhận chính xác nguyên nhân xử lý",
            what_happened=(
                f"Lần chạy tính toán thuộc {scope_desc} đã kết thúc nhưng hệ thống "
                "chưa thể xác định chính xác nguyên nhân cụ thể từ các bằng chứng hiện có."
            ),
            why_it_happened=(
                "Các dấu hiệu lỗi trong lần chạy này không khớp hoàn toàn với các mẫu lỗi "
                "đã được chuẩn hóa hoặc thiếu bằng chứng xác thực để đưa ra kết luận chắc chắn."
            ),
            what_to_do=(
                "1. Mở phần Chi tiết kỹ thuật từ hệ thống bên dưới để xem lại thông tin chi tiết của lần chạy.",
                "2. Kiểm tra lại các tệp bảng tính nguồn và dữ liệu đầu vào xem có điểm bất thường nào không.",
                "3. Nếu cần hỗ trợ thêm, hãy liên hệ đội ngũ quản trị vận hành và cung cấp thông tin lần chạy này.",
            ),
            confidence_label="Chưa xác nhận",
            evidence_label="Bằng chứng và nhật ký vận hành",
            technical_details_label="Chi tiết kỹ thuật từ hệ thống",
        )
    elif lang == "en":
        scope_desc = f"fiscal year FY{fiscal_year}"
        if cc_label:
            scope_desc += f", Cost Center {cc_label}"
        return GuidancePresentation(
            language="en",
            title="Unable to Confirm the Root Cause",
            what_happened=(
                f"The calculation run for {scope_desc} completed with an unconfirmed "
                "status because the available evidence does not match a known issue pattern."
            ),
            why_it_happened=(
                "The operational evidence from this run does not uniquely match any approved "
                "error class or the required verification evidence was incomplete."
            ),
            what_to_do=(
                "1. Expand the System technical details section below to review run details.",
                "2. Manually check your input workbooks and parameters for unexpected values or structure.",
                "3. If the issue persists, contact the operations support team and provide this run information.",
            ),
            confidence_label="Unconfirmed",
            evidence_label="Operational Evidence and Logs",
            technical_details_label="System technical details",
        )
    elif lang == "ja":
        scope_desc = f"FY{fiscal_year}年度"
        if cc_label:
            scope_desc += f"（コストセンター: {cc_label}）"
        return GuidancePresentation(
            language="ja",
            title="処理結果の原因を確定できません",
            what_happened=(
                f"{scope_desc}の計算処理が終了しましたが、利用可能な証跡から具体的な原因を確定できませんでした。"
            ),
            why_it_happened=(
                "この実行の証跡は承認済みの既知エラーパターンと完全に一致しないか、原因を特定するための証跡が不足しています。"
            ),
            what_to_do=(
                "1. 下記の「システム技術詳細」を開いて、実行ログの詳細を確認してください。",
                "2. 入力元データファイルおよび設定内容に誤りや異常がないか手動で確認してください。",
                "3. 解決しない場合は、この実行情報を運用サポート窓口に共有してお問い合わせください。",
            ),
            confidence_label="未確定",
            evidence_label="運用証跡およびログ",
            technical_details_label="システム技術詳細",
        )
    else:
        raise ValueError(
            f"Ngôn ngữ '{language}' không được hỗ trợ. Các ngôn ngữ hợp lệ: {sorted(SUPPORTED_LANGUAGES)}"
        )


def assemble_unclassified_operational_case(
    history_root: str | Path,
    run_id: str,
) -> OperationalCase:
    """Lắp ráp một trường hợp vận hành chưa phân loại (unclassified OperationalCase).

    Hàm này duy trì tương thích cho các kiểm thử ban đầu (T008-T009), luôn trả về
    classification='unknown', confidence='unknown', guidance=().
    """
    case = assemble_operational_case(history_root, run_id, language="vi")
    return OperationalCase(
        case_id=case.case_id,
        run_id=case.run_id,
        fiscal_year=case.fiscal_year,
        cost_center_scope=case.cost_center_scope,
        status=case.status,
        stage=case.stage,
        classification="unknown",
        confidence="unknown",
        summary=case.summary,
        evidence=case.evidence,
        guidance=(),
        presentation=None,
    )
