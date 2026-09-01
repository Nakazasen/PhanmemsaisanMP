"""Kế hoạch và Fixture kiểm thử CI-safe cho dịch vụ trường hợp vận hành (Operations Case Service).

Kế hoạch này đảm bảo 100% môi trường kiểm thử là tổng hợp (synthetic), chỉ sử dụng thư mục
tạm thời (tmp_path), không đọc/ghi file Excel thật của doanh nghiệp, không sử dụng dữ liệu
người dùng và không kết nối mạng.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any
import pytest

from src.services.operations_case_service import (
    EvidenceReference,
    OperationalCase,
    assemble_operational_case,
    assemble_unclassified_operational_case,
    load_failure_traceback_evidence,
    load_pipeline_stage_evidence,
    load_preflight_report_evidence,
    load_run_manifest_evidence,
    lookup_terminal_run_catalog_record,
    validate_workspace_evidence_path,
)


def init_synthetic_history_db(history_root: Path) -> Path:
    """Khởi tạo cơ sở dữ liệu danh mục SQLite tổng hợp planning_runs trong history_root."""
    history_root.mkdir(parents=True, exist_ok=True)
    db_path = history_root / "run_history.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS planning_runs (
                run_id TEXT PRIMARY KEY,
                fiscal_year INTEGER NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                selected_cost_center TEXT,
                source_paths_json TEXT NOT NULL DEFAULT '{}',
                source_checksums_json TEXT NOT NULL DEFAULT '{}',
                template_checksum TEXT,
                exchange_rate REAL NOT NULL,
                exchange_rate_source TEXT,
                output_path TEXT,
                database_path TEXT,
                error_summary TEXT,
                application_version TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


def insert_synthetic_catalog_row(
    history_root: Path,
    *,
    run_id: str,
    fiscal_year: int = 2028,
    status: str = "FAILED",
    started_at: str = "2026-09-01T09:00:00Z",
    finished_at: str = "2026-09-01T09:00:05Z",
    selected_cost_center: str | None = "1412000040",
    source_paths: dict[str, list[str]] | None = None,
    source_checksums: dict[str, list[dict[str, str]]] | None = None,
    template_checksum: str = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    exchange_rate: float = 25000.0,
    exchange_rate_source: str = "GA",
    output_path: str | None = None,
    database_path: str | None = None,
    error_summary: str | None = None,
    application_version: str = "0.1.6",
) -> None:
    """Thêm một bản ghi tổng hợp vào bảng planning_runs."""
    db_path = init_synthetic_history_db(history_root)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO planning_runs (
                run_id, fiscal_year, status, started_at, finished_at,
                selected_cost_center, source_paths_json, source_checksums_json,
                template_checksum, exchange_rate, exchange_rate_source,
                output_path, database_path, error_summary, application_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                fiscal_year,
                status,
                started_at,
                finished_at,
                selected_cost_center,
                json.dumps(source_paths or {}, ensure_ascii=False),
                json.dumps(source_checksums or {}, ensure_ascii=False),
                template_checksum,
                exchange_rate,
                exchange_rate_source,
                output_path,
                database_path,
                error_summary,
                application_version,
                started_at,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def create_synthetic_workspace(
    history_root: Path,
    *,
    fiscal_year: int,
    run_id: str,
    manifest_payload: dict[str, Any] | None = None,
    stage_evidence_payload: dict[str, Any] | None = None,
    preflight_report_payload: dict[str, Any] | None = None,
    failure_traceback_content: str | None = None,
) -> Path:
    """Tạo không gian làm việc tổng hợp <history_root>/FY<fiscal_year>/<run_id>."""
    workspace = history_root / f"FY{fiscal_year}" / run_id
    reports_dir = workspace / "reports"
    outputs_dir = workspace / "outputs"
    reports_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    # 1. run.db SQLite trống
    conn = sqlite3.connect(workspace / "run.db")
    conn.close()

    # 2. run_manifest.json
    manifest = manifest_payload or {
        "run_id": run_id,
        "fiscal_year": fiscal_year,
        "fiscal_periods": [f"{fiscal_year - 1}04", f"{fiscal_year}03"],
        "baseline_period": f"{fiscal_year - 1}03",
        "template_path": str(workspace / "FORM.xlsx"),
        "source_dir": str(workspace / "sources"),
        "headcount_source_dir": str(workspace / "headcount"),
        "output_dir": str(history_root / f"OUTPUT_FY{fiscal_year}"),
        "exchange_rate": 25000.0,
        "exchange_rate_source": "GA",
        "history_root": str(history_root),
        "workspace_dir": str(workspace),
        "database_path": str(workspace / "run.db"),
        "resolved_sources": {},
        "source_checksums": {},
        "template_checksum": "synthetic-template-sha256",
        "application_version": "0.1.6",
    }
    (workspace / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 3. reports/pipeline_stage_evidence.json
    stage_evidence = stage_evidence_payload or {
        "schema_version": 1,
        "run_id": run_id,
        "status": "FAILED",
        "started_at": "2026-09-01T09:00:00Z",
        "finished_at": "2026-09-01T09:00:05Z",
        "total_elapsed_seconds": 5.0,
        "current_stage": None,
        "error_summary": "Lỗi tổng hợp trong kiểm thử",
        "stages": [
            {
                "name": "preflight",
                "status": "FAIL",
                "elapsed_seconds": 1.2,
                "finished_at": "2026-09-01T09:00:01Z",
                "error_summary": "Lỗi kiểm tra tiền trạm tổng hợp",
            }
        ],
    }
    (reports_dir / "pipeline_stage_evidence.json").write_text(
        json.dumps(stage_evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 4. reports/preflight_report.json (nếu có)
    if preflight_report_payload is not None:
        (reports_dir / "preflight_report.json").write_text(
            json.dumps(preflight_report_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (reports_dir / "preflight_report.md").write_text(
            "# Preflight Report (Synthetic)\n", encoding="utf-8"
        )

    # 5. reports/failure_traceback.txt (nếu có)
    if failure_traceback_content is not None:
        (reports_dir / "failure_traceback.txt").write_text(
            failure_traceback_content, encoding="utf-8"
        )

    return workspace


# ---------------------------------------------------------------------------
# Fixture Builders cho 3 nhóm lỗi được phê duyệt + 1 nhóm chưa biết
# ---------------------------------------------------------------------------

def make_fixture_missing_staffing_baseline(history_root: Path, run_id: str = "run-missing-staffing") -> Path:
    """Fixture cho lỗi thiếu headcount baseline ở bước kiểm tra trước (PRECHECK_FAILED)."""
    preflight = {
        "fiscal_year": 2028,
        "ok": False,
        "can_continue_incomplete": False,
        "issues": [
            {
                "category": "headcount",
                "selected_path": "headcount_manual.csv",
                "detected_fiscal_year": 2028,
                "expected_fiscal_year": 2028,
                "status": "FAILED",
                "code": "SOURCE_VALIDATION_FAILED",
                "severity": "BLOCKING",
                "impact": "Không thể bảo đảm kết quả tính toán chính xác.",
                "checksum": None,
                "sheet": None,
                "period_coverage": [],
                "reason": "Thiếu dữ liệu nhân sự baseline tháng 202703 cho CC 1412000040",
                "required_action": "Bổ sung dữ liệu baseline tháng 03 rồi kiểm tra lại.",
            }
        ],
        "checks": [],
        "resolved_sources": {},
        "usable_sources": {},
        "skipped_categories": [],
        "incomplete_run": False,
    }
    stage_evidence = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "PRECHECK_FAILED",
        "started_at": "2026-09-01T09:00:00Z",
        "finished_at": "2026-09-01T09:00:02Z",
        "total_elapsed_seconds": 2.0,
        "current_stage": None,
        "error_summary": "Thiếu dữ liệu nhân sự baseline",
        "stages": [
            {
                "name": "preflight",
                "status": "FAIL",
                "elapsed_seconds": 1.5,
                "finished_at": "2026-09-01T09:00:01Z",
                "error_summary": "Thiếu dữ liệu nhân sự baseline",
            }
        ],
    }
    ws = create_synthetic_workspace(
        history_root,
        fiscal_year=2028,
        run_id=run_id,
        stage_evidence_payload=stage_evidence,
        preflight_report_payload=preflight,
    )
    insert_synthetic_catalog_row(
        history_root,
        run_id=run_id,
        fiscal_year=2028,
        status="PRECHECK_FAILED",
        database_path=str(ws / "run.db"),
        error_summary="Thiếu dữ liệu nhân sự baseline",
    )
    return ws


def make_fixture_validate_staffing_baseline_error(
    history_root: Path, run_id: str = "run-staffing-baseline-fail"
) -> Path:
    """Fixture cho lỗi validate_staffing thiếu Tổng số người tháng 03 (missing_staffing_baseline)."""
    preflight = {
        "fiscal_year": 2028,
        "ok": True,
        "can_continue_incomplete": False,
        "issues": [],
        "checks": [],
        "resolved_sources": {},
        "usable_sources": {},
        "skipped_categories": [],
        "incomplete_run": False,
    }
    stage_evidence = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "FAILED",
        "started_at": "2026-09-01T09:00:00Z",
        "finished_at": "2026-09-01T09:00:04Z",
        "total_elapsed_seconds": 4.0,
        "current_stage": None,
        "error_summary": "Chưa có tổng số người tháng 03/2027 cho Cost Center 1412000040",
        "stages": [
            {"name": "preflight", "status": "PASS", "elapsed_seconds": 1.0, "finished_at": "2026-09-01T09:00:01Z"},
            {"name": "initialize_database", "status": "PASS", "elapsed_seconds": 1.0, "finished_at": "2026-09-01T09:00:02Z"},
            {"name": "import_sources", "status": "PASS", "elapsed_seconds": 1.0, "finished_at": "2026-09-01T09:00:03Z"},
            {
                "name": "validate_staffing",
                "status": "FAIL",
                "elapsed_seconds": 1.0,
                "finished_at": "2026-09-01T09:00:04Z",
                "error_summary": "Chưa có tổng số người tháng 03/2027 cho Cost Center 1412000040",
            },
        ],
    }
    ws = create_synthetic_workspace(
        history_root,
        fiscal_year=2028,
        run_id=run_id,
        stage_evidence_payload=stage_evidence,
        preflight_report_payload=preflight,
        failure_traceback_content=(
            "ValueError: Chưa có tổng số người tháng 03/2027 cho Cost Center 1412000040\n"
        ),
    )
    insert_synthetic_catalog_row(
        history_root,
        run_id=run_id,
        fiscal_year=2028,
        status="FAILED",
        database_path=str(ws / "run.db"),
        error_summary="Chưa có tổng số người tháng 03/2027 cho Cost Center 1412000040",
    )
    return ws


def make_fixture_locked_output_error(history_root: Path, run_id: str = "run-locked-output") -> Path:
    """Fixture cho lỗi Windows lock file Excel đầu ra (blocked_output_file_lock)."""
    traceback_content = (
        "OutputPublicationLockedError: Không thể cập nhật thư mục kết quả vì Windows đang khóa tệp.\n\n"
        "Traceback (most recent call last):\n"
        '  File "src/services/run_history.py", line 76, in _rename_with_retry\n'
        "    source.rename(destination)\n"
        "PermissionError: [WinError 5] Access is denied\n"
    )
    stage_evidence = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "FAILED",
        "started_at": "2026-09-01T09:00:00Z",
        "finished_at": "2026-09-01T09:00:10Z",
        "total_elapsed_seconds": 10.0,
        "current_stage": None,
        "error_summary": "OutputPublicationLockedError: Windows đang khóa file",
        "stages": [
            {"name": "preflight", "status": "PASS", "elapsed_seconds": 1.0, "finished_at": "2026-09-01T09:00:01Z"},
            {"name": "initialize_database", "status": "PASS", "elapsed_seconds": 1.0, "finished_at": "2026-09-01T09:00:02Z"},
            {"name": "import_sources", "status": "PASS", "elapsed_seconds": 1.0, "finished_at": "2026-09-01T09:00:03Z"},
            {"name": "validate_staffing", "status": "PASS", "elapsed_seconds": 1.0, "finished_at": "2026-09-01T09:00:04Z"},
            {"name": "allocation", "status": "PASS", "elapsed_seconds": 1.0, "finished_at": "2026-09-01T09:00:05Z"},
            {"name": "export_workbooks", "status": "PASS", "elapsed_seconds": 1.0, "finished_at": "2026-09-01T09:00:06Z"},
            {"name": "audit_reports", "status": "PASS", "elapsed_seconds": 1.0, "finished_at": "2026-09-01T09:00:07Z"},
            {"name": "publication", "status": "FAIL", "elapsed_seconds": 3.0, "finished_at": "2026-09-01T09:00:10Z",
             "error_summary": "OutputPublicationLockedError"},
        ],
    }
    preflight = {
        "fiscal_year": 2028,
        "ok": True,
        "can_continue_incomplete": False,
        "issues": [],
        "checks": [],
        "resolved_sources": {},
        "usable_sources": {},
        "skipped_categories": [],
        "incomplete_run": False,
    }
    ws = create_synthetic_workspace(
        history_root,
        fiscal_year=2028,
        run_id=run_id,
        stage_evidence_payload=stage_evidence,
        preflight_report_payload=preflight,
        failure_traceback_content=traceback_content,
    )
    insert_synthetic_catalog_row(
        history_root,
        run_id=run_id,
        fiscal_year=2028,
        status="FAILED",
        database_path=str(ws / "run.db"),
        error_summary="OutputPublicationLockedError",
    )
    return ws


def make_fixture_preflight_source_validation_failure(
    history_root: Path, run_id: str = "run-source-invalid"
) -> Path:
    """Fixture cho lỗi kiểm tra tiền trạm file nguồn (preflight_source_validation_failure)."""
    preflight = {
        "fiscal_year": 2028,
        "ok": False,
        "can_continue_incomplete": False,
        "issues": [
            {
                "category": "facility",
                "selected_path": "Facility_2028.xlsx",
                "detected_fiscal_year": 2028,
                "expected_fiscal_year": 2028,
                "status": "FAILED",
                "code": "SOURCE_VALIDATION_FAILED",
                "severity": "BLOCKING",
                "impact": "Không thể bảo đảm kết quả tính toán chính xác.",
                "checksum": None,
                "sheet": None,
                "period_coverage": [],
                "reason": "Cấu trúc cột trong workbook Facilities không hợp lệ: thiếu cột 'Tên thiết bị'",
                "required_action": "Sửa workbook nguồn rồi kiểm tra lại.",
            }
        ],
        "checks": [],
        "resolved_sources": {},
        "usable_sources": {},
        "skipped_categories": [],
        "incomplete_run": False,
    }
    stage_evidence = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "PRECHECK_FAILED",
        "started_at": "2026-09-01T09:00:00Z",
        "finished_at": "2026-09-01T09:00:01Z",
        "total_elapsed_seconds": 1.0,
        "current_stage": None,
        "error_summary": "Báo cáo tiền trạm phát hiện lỗi cấu trúc file nguồn",
        "stages": [
            {"name": "preflight", "status": "FAIL", "elapsed_seconds": 0.8, "finished_at": "2026-09-01T09:00:01Z"}
        ],
    }
    ws = create_synthetic_workspace(
        history_root,
        fiscal_year=2028,
        run_id=run_id,
        stage_evidence_payload=stage_evidence,
        preflight_report_payload=preflight,
    )
    insert_synthetic_catalog_row(
        history_root,
        run_id=run_id,
        fiscal_year=2028,
        status="PRECHECK_FAILED",
        database_path=str(ws / "run.db"),
        error_summary="Lỗi cấu trúc file nguồn",
    )
    return ws


def make_fixture_succeeded_run(history_root: Path, run_id: str = "run-succeeded") -> Path:
    """Fixture cho lần chạy thành công hoàn toàn (SUCCEEDED)."""
    stage_evidence = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "SUCCEEDED",
        "started_at": "2026-09-01T09:00:00Z",
        "finished_at": "2026-09-01T09:00:08Z",
        "total_elapsed_seconds": 8.0,
        "current_stage": None,
        "stages": [
            {"name": "preflight", "status": "PASS", "elapsed_seconds": 1.0, "finished_at": "2026-09-01T09:00:01Z"},
            {"name": "initialize_database", "status": "PASS", "elapsed_seconds": 1.0, "finished_at": "2026-09-01T09:00:02Z"},
            {"name": "import_sources", "status": "PASS", "elapsed_seconds": 1.0, "finished_at": "2026-09-01T09:00:03Z"},
            {"name": "validate_staffing", "status": "PASS", "elapsed_seconds": 1.0, "finished_at": "2026-09-01T09:00:04Z"},
            {"name": "allocation", "status": "PASS", "elapsed_seconds": 1.0, "finished_at": "2026-09-01T09:00:05Z"},
            {"name": "export_workbooks", "status": "PASS", "elapsed_seconds": 1.0, "finished_at": "2026-09-01T09:00:06Z"},
            {"name": "audit_reports", "status": "PASS", "elapsed_seconds": 1.0, "finished_at": "2026-09-01T09:00:07Z"},
            {"name": "publication", "status": "PASS", "elapsed_seconds": 1.0, "finished_at": "2026-09-01T09:00:08Z"},
        ],
    }
    preflight = {
        "fiscal_year": 2028,
        "ok": True,
        "can_continue_incomplete": False,
        "issues": [],
        "checks": [],
        "resolved_sources": {},
        "usable_sources": {},
        "skipped_categories": [],
        "incomplete_run": False,
    }
    ws = create_synthetic_workspace(
        history_root,
        fiscal_year=2028,
        run_id=run_id,
        stage_evidence_payload=stage_evidence,
        preflight_report_payload=preflight,
    )
    insert_synthetic_catalog_row(
        history_root,
        run_id=run_id,
        fiscal_year=2028,
        status="SUCCEEDED",
        database_path=str(ws / "run.db"),
    )
    return ws


# ---------------------------------------------------------------------------
# Test xác thực tính hợp lệ và CI-safe của Fixture Generators (T003 Test Plan)
# ---------------------------------------------------------------------------

def test_synthetic_fixture_plan_creates_isolated_run_history(tmp_path: Path) -> None:
    """Kiểm tra fixture plan tạo đúng cấu trúc SQLite và workspace độc lập dưới tmp_path."""
    history_root = tmp_path / "SYNTHETIC_RUN_HISTORY"

    # 1. Tạo 3 fixture lỗi + 1 fixture thành công
    ws_staffing = make_fixture_missing_staffing_baseline(history_root)
    ws_lock = make_fixture_locked_output_error(history_root)
    ws_source = make_fixture_preflight_source_validation_failure(history_root)
    ws_ok = make_fixture_succeeded_run(history_root)

    for workspace in (ws_staffing, ws_lock, ws_source, ws_ok):
        assert workspace.is_relative_to(tmp_path)

    # 2. Xác thực SQLite catalog
    db_path = history_root / "run_history.db"
    assert db_path.is_file()
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT run_id, status FROM planning_runs ORDER BY run_id").fetchall()
        run_dict = dict(rows)
        assert run_dict["run-missing-staffing"] == "PRECHECK_FAILED"
        assert run_dict["run-locked-output"] == "FAILED"
        assert run_dict["run-source-invalid"] == "PRECHECK_FAILED"
        assert run_dict["run-succeeded"] == "SUCCEEDED"
    finally:
        conn.close()

    # 3. Xác thực file bằng chứng trong từng workspace
    assert (ws_staffing / "run_manifest.json").is_file()
    assert (ws_staffing / "reports" / "pipeline_stage_evidence.json").is_file()
    assert (ws_staffing / "reports" / "preflight_report.json").is_file()
    assert not (ws_staffing / "reports" / "failure_traceback.txt").exists()

    assert (ws_lock / "reports" / "failure_traceback.txt").is_file()
    trace_text = (ws_lock / "reports" / "failure_traceback.txt").read_text(encoding="utf-8")
    assert "OutputPublicationLockedError" in trace_text

    assert (ws_source / "reports" / "preflight_report.json").is_file()
    preflight_json = json.loads((ws_source / "reports" / "preflight_report.json").read_text(encoding="utf-8"))
    assert preflight_json["ok"] is False
    assert preflight_json["issues"][0]["category"] == "facility"
    assert preflight_json["issues"][0]["severity"] == "BLOCKING"
    assert preflight_json["issues"][0]["selected_path"] == "Facility_2028.xlsx"
    assert preflight_json["issues"][0]["required_action"]

    assert (ws_ok / "reports" / "pipeline_stage_evidence.json").is_file()
    ok_stages = json.loads((ws_ok / "reports" / "pipeline_stage_evidence.json").read_text(encoding="utf-8"))
    assert ok_stages["status"] == "SUCCEEDED"
    assert [stage["name"] for stage in ok_stages["stages"]] == [
        "preflight",
        "initialize_database",
        "import_sources",
        "validate_staffing",
        "allocation",
        "export_workbooks",
        "audit_reports",
        "publication",
    ]


# ---------------------------------------------------------------------------
# T004: Unit Tests for EvidenceReference and OperationalCase Data Classes
# ---------------------------------------------------------------------------

def test_evidence_reference_constructor_and_immutability() -> None:
    """Xác thực khởi tạo và tính bất biến (frozen) của EvidenceReference."""
    ref = EvidenceReference(
        type="preflight_report",
        local_path="reports/preflight_report.json",
        locator="issues[0]",
        summary="Thiếu dữ liệu nhân sự baseline tháng 202703",
        verification="verified",
    )

    assert ref.type == "preflight_report"
    assert ref.local_path == "reports/preflight_report.json"
    assert ref.locator == "issues[0]"
    assert ref.summary == "Thiếu dữ liệu nhân sự baseline tháng 202703"
    assert ref.verification == "verified"

    # Kiểm tra tính bất biến (frozen=True)
    with pytest.raises(FrozenInstanceError):
        ref.local_path = "other/path.json"  # type: ignore[misc]


def test_evidence_reference_default_verification_and_validation() -> None:
    """Xác thực giá trị mặc định của verification và validate trường bắt buộc."""
    ref = EvidenceReference(
        type="run_manifest",
        local_path="run_manifest.json",
        locator="resolved_sources",
        summary="Cấu hình nguồn đầu vào",
    )
    assert ref.verification == "verified"

    with pytest.raises(ValueError, match="EvidenceReference.type không được để trống"):
        EvidenceReference(
            type="",
            local_path="run_manifest.json",
            locator="",
            summary="",
        )

    with pytest.raises(ValueError, match="EvidenceReference.local_path không được để trống"):
        EvidenceReference(
            type="run_manifest",
            local_path="",
            locator="",
            summary="",
        )

    with pytest.raises(ValueError, match="EvidenceReference.locator"):
        EvidenceReference(
            type="run_manifest",
            local_path="run_manifest.json",
            locator="",
            summary="Nguồn dữ liệu",
        )

    with pytest.raises(ValueError, match="EvidenceReference.summary"):
        EvidenceReference(
            type="run_manifest",
            local_path="run_manifest.json",
            locator="resolved_sources",
            summary="",
        )

    with pytest.raises(ValueError, match="EvidenceReference.verification"):
        EvidenceReference(
            type="run_manifest",
            local_path="run_manifest.json",
            locator="resolved_sources",
            summary="Nguồn dữ liệu",
            verification="unverified",
        )


def test_operational_case_constructor_and_immutability() -> None:
    """Xác thực khởi tạo và tính bất biến (frozen) của OperationalCase."""
    ref1 = EvidenceReference(
        type="stage_evidence",
        local_path="reports/pipeline_stage_evidence.json",
        locator="stages[0]",
        summary="Bước preflight thất bại",
    )
    case = OperationalCase(
        case_id="case-run-2028-a",
        run_id="run-2028-a",
        fiscal_year=2028,
        cost_center_scope="1412000040",
        status="PRECHECK_FAILED",
        stage="preflight",
        classification="missing_staffing_baseline",
        confidence="confirmed",
        summary="Thiếu nhân sự baseline cho CC 1412000040",
        evidence=(ref1,),
        guidance=("Bổ sung dòng nhân sự tháng 202703 vào headcount_manual.csv",),
    )

    assert case.case_id == "case-run-2028-a"
    assert case.run_id == "run-2028-a"
    assert case.fiscal_year == 2028
    assert case.cost_center_scope == "1412000040"
    assert case.status == "PRECHECK_FAILED"
    assert case.stage == "preflight"
    assert case.classification == "missing_staffing_baseline"
    assert case.confidence == "confirmed"
    assert len(case.evidence) == 1
    assert case.evidence[0] == ref1
    assert len(case.guidance) == 1

    # Kiểm tra tính bất biến (frozen=True)
    with pytest.raises(FrozenInstanceError):
        case.status = "SUCCEEDED"  # type: ignore[misc]


def test_operational_case_defaults_and_sequence_normalization() -> None:
    """Xác thực giá trị mặc định của evidence/guidance và chuẩn hóa sequence thành tuple."""
    ref = EvidenceReference(
        type="failure_traceback",
        local_path="reports/failure_traceback.txt",
        locator="line:1",
        summary="Ngoại lệ khóa tệp",
    )
    # Truyền list thay vì tuple, post_init phải tự động ép sang tuple bất biến
    case = OperationalCase(
        case_id="case-run-lock",
        run_id="run-lock",
        fiscal_year=2028,
        cost_center_scope="ALL",
        status="FAILED",
        stage="publication",
        classification="blocked_output_file_lock",
        confidence="confirmed",
        summary="Tệp Excel đầu ra bị khóa",
        evidence=[ref],  # type: ignore[arg-type]
        guidance=["Đóng tệp Excel đang mở và thử lại"],  # type: ignore[arg-type]
    )

    assert isinstance(case.evidence, tuple)
    assert isinstance(case.guidance, tuple)
    assert case.evidence == (ref,)
    assert case.guidance == ("Đóng tệp Excel đang mở và thử lại",)

    # Case với mặc định trống
    minimal_case = OperationalCase(
        case_id="case-minimal",
        run_id="run-minimal",
        fiscal_year=2028,
        cost_center_scope="ALL",
        status="SUCCEEDED",
        stage="unavailable",
        classification="unknown",
        confidence="unknown",
        summary="Lần chạy thành công",
    )
    assert minimal_case.evidence == ()
    assert minimal_case.guidance == ()


def test_operational_case_validation_rejects_invalid_inputs() -> None:
    """Xác thực từ chối các tham số rỗng hoặc không hợp lệ."""
    with pytest.raises(ValueError, match="OperationalCase.case_id"):
        OperationalCase(
            case_id="",
            run_id="run-1",
            fiscal_year=2028,
            cost_center_scope="ALL",
            status="FAILED",
            stage="preflight",
            classification="unknown",
            confidence="unknown",
            summary="",
        )

    with pytest.raises(ValueError, match="OperationalCase.run_id"):
        OperationalCase(
            case_id="case-1",
            run_id="",
            fiscal_year=2028,
            cost_center_scope="ALL",
            status="FAILED",
            stage="preflight",
            classification="unknown",
            confidence="unknown",
            summary="",
        )

    with pytest.raises(ValueError, match="OperationalCase.fiscal_year"):
        OperationalCase(
            case_id="case-1",
            run_id="run-1",
            fiscal_year=1999,
            cost_center_scope="ALL",
            status="FAILED",
            stage="preflight",
            classification="unknown",
            confidence="unknown",
            summary="",
        )

    invalid = {
        "case_id": "case-1",
        "run_id": "run-1",
        "fiscal_year": 2028,
        "cost_center_scope": "ALL",
        "status": "FAILED",
        "stage": "preflight",
        "classification": "unknown",
        "confidence": "unknown",
        "summary": "Không rõ nguyên nhân.",
    }
    with pytest.raises(ValueError, match="cost_center_scope"):
        OperationalCase(**{**invalid, "cost_center_scope": ""})
    with pytest.raises(ValueError, match="status"):
        OperationalCase(**{**invalid, "status": "RUNNING"})
    with pytest.raises(ValueError, match="confidence"):
        OperationalCase(**{**invalid, "confidence": "certain"})
    with pytest.raises(ValueError, match="summary"):
        OperationalCase(**{**invalid, "summary": ""})
    with pytest.raises(ValueError, match="evidence"):
        OperationalCase(**{**invalid, "evidence": ("not-evidence",)})  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="guidance"):
        OperationalCase(**{**invalid, "guidance": ("",)})


# ---------------------------------------------------------------------------
# T005: Unit Tests for validate_workspace_evidence_path
# ---------------------------------------------------------------------------

def test_validate_workspace_evidence_path_valid_files(tmp_path: Path) -> None:
    """Xác thực đường dẫn hợp lệ (cả tương đối và tuyệt đối) bên trong workspace."""
    history_root = tmp_path / "RUN_HISTORY"
    ws = make_fixture_succeeded_run(history_root, run_id="run-valid-path")

    # 1. Đường dẫn tương đối
    rel_path = "reports/pipeline_stage_evidence.json"
    validated = validate_workspace_evidence_path(ws, rel_path)
    assert validated == (ws / rel_path).resolve()
    assert validated.is_file()

    # 2. Đường dẫn tuyệt đối
    abs_path = ws / "run_manifest.json"
    validated_abs = validate_workspace_evidence_path(ws, abs_path)
    assert validated_abs == abs_path.resolve()
    assert validated_abs.is_file()

    # 3. Tệp trong thư mục con nhiều tầng
    deep_dir = ws / "reports" / "nested"
    deep_dir.mkdir(parents=True, exist_ok=True)
    deep_file = deep_dir / "audit_log.txt"
    deep_file.write_text("ok", encoding="utf-8")

    validated_deep = validate_workspace_evidence_path(ws, "reports/nested/audit_log.txt")
    assert validated_deep == deep_file.resolve()


def test_validate_workspace_evidence_path_missing_files(tmp_path: Path) -> None:
    """Xác thực xử lý tệp không tồn tại với must_exist=True và must_exist=False."""
    history_root = tmp_path / "RUN_HISTORY"
    ws = make_fixture_succeeded_run(history_root, run_id="run-missing-check")

    missing_rel = "reports/failure_traceback.txt"

    # must_exist=True (mặc định) -> Phải ném FileNotFoundError
    with pytest.raises(FileNotFoundError, match="Tệp bằng chứng không tồn tại"):
        validate_workspace_evidence_path(ws, missing_rel)

    # must_exist=False -> Trả về resolved Path mà không ném lỗi
    resolved = validate_workspace_evidence_path(ws, missing_rel, must_exist=False)
    assert resolved == (ws / missing_rel).resolve()
    assert not resolved.exists()


def test_validate_workspace_evidence_path_rejects_path_traversal(tmp_path: Path) -> None:
    """Chặn triệt để mọi hành vi Path Traversal ('..') trỏ ra ngoài workspace."""
    history_root = tmp_path / "RUN_HISTORY"
    ws = make_fixture_succeeded_run(history_root, run_id="run-traversal-guard")

    # Tạo tệp ngoài workspace
    outside_file = tmp_path / "secret.txt"
    outside_file.write_text("secret", encoding="utf-8")

    traversal_cases = [
        "../outside.txt",
        "reports/../../outside.txt",
        "reports/../../../secret.txt",
        "..",
        ws / ".." / "outside.txt",
    ]

    for bad_path in traversal_cases:
        with pytest.raises(ValueError, match="nằm ngoài phạm vi workspace"):
            validate_workspace_evidence_path(ws, bad_path, must_exist=False)


def test_validate_workspace_evidence_path_rejects_sibling_workspace_and_other_fy(
    tmp_path: Path,
) -> None:
    """Chặn truy cập vào workspace của lần chạy khác (cùng FY hoặc khác FY)."""
    history_root = tmp_path / "RUN_HISTORY"
    ws_target = make_fixture_succeeded_run(history_root, run_id="run-target-2028")
    ws_sibling = make_fixture_succeeded_run(history_root, run_id="run-sibling-2028")

    # Tạo workspace khác FY (2027)
    ws_other_fy = create_synthetic_workspace(history_root, fiscal_year=2027, run_id="run-2027-a")

    # 1. Trỏ sang run khác cùng FY
    sibling_manifest = ws_sibling / "run_manifest.json"
    with pytest.raises(ValueError, match="nằm ngoài phạm vi workspace"):
        validate_workspace_evidence_path(ws_target, sibling_manifest)

    # 2. Trỏ sang workspace của FY khác
    other_fy_manifest = ws_other_fy / "run_manifest.json"
    with pytest.raises(ValueError, match="nằm ngoài phạm vi workspace"):
        validate_workspace_evidence_path(ws_target, other_fy_manifest)


def test_validate_workspace_evidence_path_rejects_invalid_inputs(tmp_path: Path) -> None:
    """Xác thực từ chối các tham số rỗng hoặc thư mục workspace không tồn tại."""
    history_root = tmp_path / "RUN_HISTORY"
    ws = make_fixture_succeeded_run(history_root, run_id="run-valid-inputs")

    with pytest.raises(ValueError, match="workspace_dir không được để trống"):
        validate_workspace_evidence_path("", "run_manifest.json")

    with pytest.raises(ValueError, match="candidate_path không được để trống"):
        validate_workspace_evidence_path(ws, "")

    non_existent_ws = tmp_path / "NON_EXISTENT_WORKSPACE"
    with pytest.raises(FileNotFoundError, match="Thư mục workspace không tồn tại"):
        validate_workspace_evidence_path(non_existent_ws, "run_manifest.json")


# ---------------------------------------------------------------------------
# T006: Unit Tests for lookup_terminal_run_catalog_record (Read-only SQLite Lookup)
# ---------------------------------------------------------------------------

def _file_sha256(path: Path) -> str:
    """Tính mã băm SHA-256 của tệp để kiểm tra tính bất biến tuyệt đối."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_lookup_terminal_run_catalog_record_valid(tmp_path: Path) -> None:
    """Xác thực tra cứu đúng và đầy đủ các trường của một lần chạy kết thúc hợp lệ."""
    history_root = tmp_path / "RUN_HISTORY"

    # Tạo các run với các trạng thái kết thúc khác nhau
    make_fixture_missing_staffing_baseline(history_root, run_id="run-precheck-fail")
    make_fixture_locked_output_error(history_root, run_id="run-pipe-fail")
    make_fixture_succeeded_run(history_root, run_id="run-succ")

    # 1. Kiểm tra PRECHECK_FAILED
    rec_precheck = lookup_terminal_run_catalog_record(history_root, "run-precheck-fail")
    assert rec_precheck["run_id"] == "run-precheck-fail"
    assert rec_precheck["fiscal_year"] == 2028
    assert rec_precheck["status"] == "PRECHECK_FAILED"
    assert rec_precheck["error_summary"] == "Thiếu dữ liệu nhân sự baseline"
    assert rec_precheck["exchange_rate"] == 25000.0

    # 2. Kiểm tra FAILED
    rec_failed = lookup_terminal_run_catalog_record(history_root, "run-pipe-fail")
    assert rec_failed["run_id"] == "run-pipe-fail"
    assert rec_failed["status"] == "FAILED"
    assert "OutputPublicationLockedError" in str(rec_failed["error_summary"])

    # 3. Kiểm tra SUCCEEDED
    rec_succ = lookup_terminal_run_catalog_record(history_root, "run-succ")
    assert rec_succ["run_id"] == "run-succ"
    assert rec_succ["status"] == "SUCCEEDED"


def test_lookup_terminal_run_catalog_record_rejects_unknown_run_id(tmp_path: Path) -> None:
    """Xác thực từ chối (ném KeyError) khi run_id không tồn tại trong danh mục."""
    history_root = tmp_path / "RUN_HISTORY"
    make_fixture_succeeded_run(history_root, run_id="run-existing")

    with pytest.raises(KeyError, match="Không tìm thấy lần chạy với run_id='run-non-existent'"):
        lookup_terminal_run_catalog_record(history_root, "run-non-existent")


def test_lookup_terminal_run_catalog_record_rejects_running_status(tmp_path: Path) -> None:
    """Xác thực từ chối (ném ValueError) khi lần chạy chưa kết thúc (RUNNING)."""
    history_root = tmp_path / "RUN_HISTORY"
    init_synthetic_history_db(history_root)
    insert_synthetic_catalog_row(
        history_root,
        run_id="run-in-progress",
        fiscal_year=2028,
        status="RUNNING",
    )

    with pytest.raises(ValueError, match="đang ở trạng thái không kết thúc"):
        lookup_terminal_run_catalog_record(history_root, "run-in-progress")


def test_lookup_terminal_run_catalog_record_preserves_db_hash_and_readonly(tmp_path: Path) -> None:
    """Xác thực mã băm SHA-256 của run_history.db hoàn toàn không thay đổi trước và sau khi tra cứu."""
    history_root = tmp_path / "RUN_HISTORY"
    make_fixture_succeeded_run(history_root, run_id="run-hash-check")
    db_file = history_root / "run_history.db"

    hash_before = _file_sha256(db_file)

    # Thực hiện tra cứu nhiều lần
    record = lookup_terminal_run_catalog_record(history_root, "run-hash-check")
    assert record["run_id"] == "run-hash-check"

    hash_after = _file_sha256(db_file)
    assert hash_before == hash_after, "Mã băm SHA-256 của SQLite catalog bị thay đổi sau khi tra cứu!"


def test_lookup_terminal_run_catalog_record_rejects_missing_db_without_creating_it(
    tmp_path: Path,
) -> None:
    """Xác thực từ chối khi thiếu run_history.db và tuyệt đối không tự tạo thư mục/file rác."""
    empty_history_root = tmp_path / "ABSENT_HISTORY_FOLDER"
    assert not empty_history_root.exists()

    with pytest.raises(FileNotFoundError, match="Cơ sở dữ liệu danh mục lịch sử không tồn tại"):
        lookup_terminal_run_catalog_record(empty_history_root, "run-any")

    # Kiểm tra đảm bảo không bị tự động tạo thư mục hoặc file
    assert not empty_history_root.exists(), "Thư mục không được phép tự tạo khi tra cứu thất bại!"


def test_lookup_terminal_run_catalog_record_rejects_invalid_inputs(tmp_path: Path) -> None:
    """Xác thực từ chối các tham số rỗng hoặc không hợp lệ."""
    history_root = tmp_path / "RUN_HISTORY"
    make_fixture_succeeded_run(history_root, run_id="run-valid")

    with pytest.raises(ValueError, match="history_root không được để trống"):
        lookup_terminal_run_catalog_record("", "run-valid")

    with pytest.raises(ValueError, match="run_id không được để trống"):
        lookup_terminal_run_catalog_record(history_root, "")


# ---------------------------------------------------------------------------
# T007: Unit Tests for Workspace Evidence Loaders
# ---------------------------------------------------------------------------

def test_load_workspace_evidence_valid_files(tmp_path: Path) -> None:
    """Xác thực tải và đọc chính xác 4 tệp bằng chứng hợp lệ trong workspace."""
    history_root = tmp_path / "RUN_HISTORY"
    ws = make_fixture_locked_output_error(history_root, run_id="run-t007-valid")

    # 1. run_manifest.json
    ref_manifest, manifest_payload = load_run_manifest_evidence(ws)
    assert ref_manifest.type == "run_manifest"
    assert ref_manifest.verification == "verified"
    assert "FY2028" in ref_manifest.summary
    assert manifest_payload is not None
    assert manifest_payload["run_id"] == "run-t007-valid"

    # 2. reports/preflight_report.json
    ref_preflight, preflight_payload = load_preflight_report_evidence(ws)
    assert ref_preflight.type == "preflight_report"
    assert ref_preflight.verification == "verified"
    assert preflight_payload is not None
    assert preflight_payload.get("fiscal_year") == 2028

    # 3. reports/pipeline_stage_evidence.json
    ref_stage, stage_payload = load_pipeline_stage_evidence(ws)
    assert ref_stage.type == "stage_evidence"
    assert ref_stage.verification == "verified"
    assert stage_payload is not None
    assert stage_payload["status"] == "FAILED"
    assert len(stage_payload["stages"]) == 8

    # 4. reports/failure_traceback.txt
    ref_trace, trace_text = load_failure_traceback_evidence(ws)
    assert ref_trace.type == "failure_traceback"
    assert ref_trace.verification == "verified"
    assert trace_text is not None
    assert "OutputPublicationLockedError" in trace_text


def test_load_failure_traceback_evidence_missing_on_succeeded_run(tmp_path: Path) -> None:
    """Xác thực tệp failure_traceback.txt vắng mặt trên run thành công được biểu diễn là missing, không ném lỗi."""
    history_root = tmp_path / "RUN_HISTORY"
    ws = make_fixture_succeeded_run(history_root, run_id="run-t007-succeeded")

    ref_trace, trace_text = load_failure_traceback_evidence(ws)
    assert ref_trace.type == "failure_traceback"
    assert ref_trace.verification == "missing"
    assert trace_text is None
    assert "không có tệp dấu vết lỗi" in ref_trace.summary.lower()


def test_load_workspace_evidence_missing_files_in_empty_workspace(tmp_path: Path) -> None:
    """Xác thực toàn bộ 4 loader trả về verification='missing' khi thư mục workspace trống rỗng."""
    empty_ws = tmp_path / "EMPTY_WORKSPACE"
    empty_ws.mkdir(parents=True, exist_ok=True)

    ref_m, pay_m = load_run_manifest_evidence(empty_ws)
    assert ref_m.verification == "missing"
    assert pay_m is None

    ref_p, pay_p = load_preflight_report_evidence(empty_ws)
    assert ref_p.verification == "missing"
    assert pay_p is None

    ref_s, pay_s = load_pipeline_stage_evidence(empty_ws)
    assert ref_s.verification == "missing"
    assert pay_s is None

    ref_t, pay_t = load_failure_traceback_evidence(empty_ws)
    assert ref_t.verification == "missing"
    assert pay_t is None


def test_load_workspace_evidence_corrupt_json_creates_mismatch(tmp_path: Path) -> None:
    """Xác thực toàn bộ các tệp JSON hỏng/sai định dạng đều chuyển sang verification='mismatch' (fail-closed)."""
    history_root = tmp_path / "RUN_HISTORY"
    ws = make_fixture_succeeded_run(history_root, run_id="run-t007-corrupt")

    # Ghi đè file JSON bằng nội dung hỏng
    (ws / "run_manifest.json").write_text("{corrupt json content...", encoding="utf-8")
    (ws / "reports" / "preflight_report.json").write_text("[1, 2, 3]", encoding="utf-8")  # Array thay vì Object
    (ws / "reports" / "pipeline_stage_evidence.json").write_bytes(b"\x80\x81\x82 invalid binary")
    (ws / "reports" / "failure_traceback.txt").write_bytes(b"\xff\xfe\x00\x00\x80\x90")  # Invalid UTF-8

    ref_m, pay_m = load_run_manifest_evidence(ws)
    assert ref_m.verification == "mismatch"
    assert pay_m is None

    ref_p, pay_p = load_preflight_report_evidence(ws)
    assert ref_p.verification == "mismatch"
    assert pay_p is None

    ref_s, pay_s = load_pipeline_stage_evidence(ws)
    assert ref_s.verification == "mismatch"
    assert pay_s is None

    ref_t, pay_t = load_failure_traceback_evidence(ws)
    assert ref_t.verification == "mismatch"
    assert pay_t is None


def test_load_workspace_evidence_rejects_wrong_schema_and_retired_preflight_key(tmp_path: Path) -> None:
    """JSON parse được nhưng thiếu/sai contract vẫn phải là mismatch, không dùng fallback cũ."""
    history_root = tmp_path / "RUN_HISTORY"
    ws = make_fixture_succeeded_run(history_root, run_id="run-t007-wrong-schema")

    (ws / "run_manifest.json").write_text(
        json.dumps({"run_id": "run-t007-wrong-schema"}), encoding="utf-8"
    )
    (ws / "reports" / "preflight_report.json").write_text(
        json.dumps({"fiscal_year": 2028, "valid": True, "issues": []}), encoding="utf-8"
    )
    (ws / "reports" / "pipeline_stage_evidence.json").write_text(
        json.dumps({"schema_version": 2, "run_id": "run-t007-wrong-schema"}), encoding="utf-8"
    )
    (ws / "reports" / "failure_traceback.txt").write_text("", encoding="utf-8")

    ref_m, pay_m = load_run_manifest_evidence(ws)
    ref_p, pay_p = load_preflight_report_evidence(ws)
    ref_s, pay_s = load_pipeline_stage_evidence(ws)
    ref_t, pay_t = load_failure_traceback_evidence(ws)

    assert (ref_m.verification, pay_m) == ("mismatch", None)
    assert (ref_p.verification, pay_p) == ("mismatch", None)
    assert (ref_s.verification, pay_s) == ("mismatch", None)
    assert (ref_t.verification, pay_t) == ("mismatch", None)


def test_load_workspace_evidence_preserves_workspace_hashes(tmp_path: Path) -> None:
    """Xác thực mã băm SHA-256 của toàn bộ tệp trong workspace không thay đổi sau khi load."""
    history_root = tmp_path / "RUN_HISTORY"
    ws = make_fixture_locked_output_error(history_root, run_id="run-t007-hash-check")

    files_before = {p: _file_sha256(p) for p in ws.rglob("*") if p.is_file()}

    # Thực hiện gọi toàn bộ 4 loader nhiều lần
    load_run_manifest_evidence(ws)
    load_preflight_report_evidence(ws)
    load_pipeline_stage_evidence(ws)
    load_failure_traceback_evidence(ws)

    files_after = {p: _file_sha256(p) for p in ws.rglob("*") if p.is_file()}

    assert files_before == files_after, "Mã băm của tệp trong workspace bị thay đổi sau khi load bằng chứng!"


# ---------------------------------------------------------------------------
# T008: Unit Tests for assemble_unclassified_operational_case
# ---------------------------------------------------------------------------

def test_assemble_unclassified_operational_case_success_run(tmp_path: Path) -> None:
    """Xác thực lắp ráp OperationalCase hoàn chỉnh cho lần chạy thành công."""
    history_root = tmp_path / "RUN_HISTORY"
    ws = make_fixture_succeeded_run(history_root, run_id="run-t008-succeeded")

    case = assemble_unclassified_operational_case(history_root, "run-t008-succeeded")

    assert case.case_id == "case-run-t008-succeeded"
    assert case.run_id == "run-t008-succeeded"
    assert case.fiscal_year == 2028
    assert case.cost_center_scope == "1412000040"
    assert case.status == "SUCCEEDED"
    assert case.stage == "publication"  # Stage cuối cùng trong pipeline_stage_evidence
    assert case.classification == "unknown"
    assert case.confidence == "unknown"
    assert case.guidance == ()
    assert case.presentation is None  # legacy helper retains its original minimal shape

    # Kiểm tra thứ tự cố định của 5 nguồn bằng chứng
    assert len(case.evidence) == 5
    evidence_types = [e.type for e in case.evidence]
    assert evidence_types == [
        "catalog_row",
        "run_manifest",
        "preflight_report",
        "stage_evidence",
        "failure_traceback",
    ]

    assert case.evidence[0].verification == "verified"
    assert case.evidence[1].verification == "verified"
    assert case.evidence[2].verification == "verified"  # make_fixture_succeeded_run tạo preflight report hợp lệ
    assert case.evidence[3].verification == "verified"
    assert case.evidence[4].verification == "missing"  # run thành công không có failure_traceback.txt


def test_assemble_unclassified_operational_case_failed_precheck_run(tmp_path: Path) -> None:
    """Xác thực trích xuất stage FAIL cho lần chạy thất bại ở precheck (PRECHECK_FAILED)."""
    history_root = tmp_path / "RUN_HISTORY"
    ws = make_fixture_missing_staffing_baseline(history_root, run_id="run-t008-precheck-fail")

    case = assemble_unclassified_operational_case(history_root, "run-t008-precheck-fail")

    assert case.status == "PRECHECK_FAILED"
    assert case.stage == "preflight"  # Stage bị FAIL
    assert case.cost_center_scope == "1412000040"
    assert case.classification == "unknown"
    assert case.confidence == "unknown"
    assert case.evidence[2].verification == "verified"  # preflight_report.json tồn tại


def test_assemble_unclassified_operational_case_failed_pipeline_stage_run(tmp_path: Path) -> None:
    """Xác thực trích xuất stage FAIL cho lần chạy thất bại trong pipeline (FAILED)."""
    history_root = tmp_path / "RUN_HISTORY"
    ws = make_fixture_locked_output_error(history_root, run_id="run-t008-pipe-fail")

    case = assemble_unclassified_operational_case(history_root, "run-t008-pipe-fail")

    assert case.status == "FAILED"
    assert case.stage == "publication"  # Stage bị FAIL trong make_fixture_locked_output_error
    assert case.evidence[4].verification == "verified"  # failure_traceback.txt tồn tại


def test_assemble_unclassified_operational_case_missing_workspace(tmp_path: Path) -> None:
    """Xác thực lắp ráp case an toàn khi thư mục workspace hoàn toàn vắng mặt."""
    history_root = tmp_path / "RUN_HISTORY"
    init_synthetic_history_db(history_root)
    insert_synthetic_catalog_row(
        history_root,
        run_id="run-ghost",
        fiscal_year=2028,
        status="FAILED",
        selected_cost_center="1412000099",
    )

    case = assemble_unclassified_operational_case(history_root, "run-ghost")

    assert case.run_id == "run-ghost"
    assert case.cost_center_scope == "1412000099"
    assert case.stage == "unavailable"
    assert len(case.evidence) == 5

    assert case.evidence[0].type == "catalog_row"
    assert case.evidence[0].verification == "verified"

    for i in range(1, 5):
        assert case.evidence[i].verification == "missing"


def test_assemble_unclassified_operational_case_rejects_mismatched_manifest_or_stage(
    tmp_path: Path,
) -> None:
    """Xác thực từ chối lắp ráp (ném ValueError) khi có mâu thuẫn run_id hoặc FY giữa manifest/stage và catalog."""
    history_root = tmp_path / "RUN_HISTORY"

    # 1. Manifest có run_id khác catalog
    ws_bad_id = make_fixture_succeeded_run(history_root, run_id="run-mismatch-id")
    manifest_data = json.loads((ws_bad_id / "run_manifest.json").read_text(encoding="utf-8"))
    manifest_data["run_id"] = "OTHER_RUN_ID"
    (ws_bad_id / "run_manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")

    with pytest.raises(ValueError, match="Mâu thuẫn run_id giữa run_manifest.json"):
        assemble_unclassified_operational_case(history_root, "run-mismatch-id")

    # 2. Manifest có fiscal_year khác catalog
    ws_bad_fy = make_fixture_succeeded_run(history_root, run_id="run-mismatch-fy")
    manifest_data = json.loads((ws_bad_fy / "run_manifest.json").read_text(encoding="utf-8"))
    manifest_data["fiscal_year"] = 2027
    (ws_bad_fy / "run_manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")

    with pytest.raises(ValueError, match="Mâu thuẫn fiscal_year giữa run_manifest.json"):
        assemble_unclassified_operational_case(history_root, "run-mismatch-fy")

    # 3. Stage evidence có run_id khác catalog
    ws_bad_stage = make_fixture_succeeded_run(history_root, run_id="run-mismatch-stage")
    stage_data = json.loads((ws_bad_stage / "reports" / "pipeline_stage_evidence.json").read_text(encoding="utf-8"))
    stage_data["run_id"] = "OTHER_STAGE_RUN_ID"
    (ws_bad_stage / "reports" / "pipeline_stage_evidence.json").write_text(json.dumps(stage_data), encoding="utf-8")

    with pytest.raises(ValueError, match="Mâu thuẫn run_id giữa pipeline_stage_evidence.json"):
        assemble_unclassified_operational_case(history_root, "run-mismatch-stage")

    # 4. Preflight có FY khác catalog
    ws_bad_preflight = make_fixture_succeeded_run(history_root, run_id="run-mismatch-preflight-fy")
    preflight_data = json.loads((ws_bad_preflight / "reports" / "preflight_report.json").read_text(encoding="utf-8"))
    preflight_data["fiscal_year"] = 2027
    (ws_bad_preflight / "reports" / "preflight_report.json").write_text(
        json.dumps(preflight_data), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="Mâu thuẫn fiscal_year giữa preflight_report.json"):
        assemble_unclassified_operational_case(history_root, "run-mismatch-preflight-fy")

    # 5. Manifest trỏ sang workspace khác dù run_id/FY nhìn có vẻ khớp
    ws_bad_workspace = make_fixture_succeeded_run(history_root, run_id="run-mismatch-workspace")
    manifest_data = json.loads((ws_bad_workspace / "run_manifest.json").read_text(encoding="utf-8"))
    manifest_data["workspace_dir"] = str(history_root / "FY2028" / "other-run")
    (ws_bad_workspace / "run_manifest.json").write_text(
        json.dumps(manifest_data), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="Mâu thuẫn workspace_dir"):
        assemble_unclassified_operational_case(history_root, "run-mismatch-workspace")


def test_assemble_unclassified_operational_case_preserves_hashes(tmp_path: Path) -> None:
    """Xác thực mã băm SHA-256 của SQLite catalog và toàn bộ workspace không thay đổi sau khi assemble."""
    history_root = tmp_path / "RUN_HISTORY"
    ws = make_fixture_locked_output_error(history_root, run_id="run-t008-hash-check")

    db_file = history_root / "run_history.db"
    db_hash_before = _file_sha256(db_file)
    ws_hashes_before = {p: _file_sha256(p) for p in ws.rglob("*") if p.is_file()}

    # Thực hiện assemble case nhiều lần
    case1 = assemble_unclassified_operational_case(history_root, "run-t008-hash-check")
    case2 = assemble_unclassified_operational_case(history_root, "run-t008-hash-check")
    assert case1.case_id == case2.case_id

    db_hash_after = _file_sha256(db_file)
    ws_hashes_after = {p: _file_sha256(p) for p in ws.rglob("*") if p.is_file()}

    assert db_hash_before == db_hash_after, "Mã băm của run_history.db bị thay đổi sau khi assemble case!"
    assert ws_hashes_before == ws_hashes_after, "Mã băm của các tệp trong workspace bị thay đổi sau khi assemble case!"


# ---------------------------------------------------------------------------
# T009: Strict No-Write Regression Test across Failed and Succeeded Runs
# ---------------------------------------------------------------------------

def _take_complete_inventory_snapshot(history_root: Path) -> dict[str, str]:
    """Chụp toàn bộ danh mục và mã băm SHA-256 của tất cả các tệp trong history_root.

    Bao gồm cả các tệp tạm SQLite sidecar (-wal, -shm, -journal, .tmp) nếu có phát sinh.
    """
    snapshot: dict[str, str] = {}
    for path in sorted(history_root.rglob("*")):
        if path.is_file():
            rel_posix = path.relative_to(history_root).as_posix()
            snapshot[rel_posix] = _file_sha256(path)
    return snapshot


def test_strict_no_write_regression_across_all_terminal_run_types(tmp_path: Path) -> None:
    """Kiểm tra hồi quy nghiêm ngặt: Tuyệt đối không có bất kỳ thao tác ghi/sửa/xóa nào trên đĩa."""
    history_root = tmp_path / "STRICT_NO_WRITE_RUN_HISTORY"

    # 1. Khởi tạo ít nhất một run FAILED và một run SUCCEEDED
    ws_failed_lock = make_fixture_locked_output_error(history_root, run_id="run-t009-failed-lock")
    ws_failed_precheck = make_fixture_missing_staffing_baseline(history_root, run_id="run-t009-failed-precheck")
    ws_succeeded = make_fixture_succeeded_run(history_root, run_id="run-t009-succeeded")

    # 2. Chụp snapshot trạng thái và inventory trước khi gọi dịch vụ
    inventory_before = _take_complete_inventory_snapshot(history_root)
    assert len(inventory_before) > 0, "Inventory ban đầu phải có tệp!"

    # Xác nhận ban đầu không có file sidecar / temporary nào
    for file_path in inventory_before:
        assert not file_path.endswith(("-wal", "-shm", "-journal", ".tmp")), (
            f"Phát hiện file sidecar/temp trước kiểm thử: {file_path}"
        )

    # 3. Thực hiện gọi liên tiếp nhiều lần dịch vụ assembly trên toàn bộ các run
    for _ in range(5):
        case_lock = assemble_unclassified_operational_case(history_root, "run-t009-failed-lock")
        assert case_lock.status == "FAILED"

        case_precheck = assemble_unclassified_operational_case(history_root, "run-t009-failed-precheck")
        assert case_precheck.status == "PRECHECK_FAILED"

        case_succ = assemble_unclassified_operational_case(history_root, "run-t009-succeeded")
        assert case_succ.status == "SUCCEEDED"

        # Tra cứu catalog và từng loader riêng lẻ
        lookup_terminal_run_catalog_record(history_root, "run-t009-failed-lock")
        load_run_manifest_evidence(ws_failed_lock)
        load_preflight_report_evidence(ws_failed_precheck)
        load_pipeline_stage_evidence(ws_succeeded)
        load_failure_traceback_evidence(ws_failed_lock)

    # 4. Chụp snapshot sau khi thực thi
    inventory_after = _take_complete_inventory_snapshot(history_root)

    # 5. Đối chiếu nghiêm ngặt
    # a. Danh sách tệp không được thay đổi (không tạo thêm, không xóa, không đổi tên)
    created_files = set(inventory_after.keys()) - set(inventory_before.keys())
    deleted_files = set(inventory_before.keys()) - set(inventory_after.keys())
    assert not created_files, f"Phát hiện tệp mới bị tạo trái phép: {created_files}"
    assert not deleted_files, f"Phát hiện tệp bị xóa trái phép: {deleted_files}"

    # b. Tuyệt đối không có file rác / sidecar phát sinh
    for file_path in inventory_after:
        assert not file_path.endswith(("-wal", "-shm", "-journal", ".tmp")), (
            f"Phát hiện file rác/sidecar phát sinh sau khi gọi service: {file_path}"
        )

    # c. Mã băm SHA-256 của từng tệp phải khớp 100%
    modified_files = [
        path for path in inventory_before
        if inventory_before[path] != inventory_after[path]
    ]
    assert not modified_files, f"Phát hiện tệp bị thay đổi nội dung (hash mismatch): {modified_files}"

    # d. Khẳng định toàn bộ snapshot khớp tuyệt đối
    assert inventory_before == inventory_after


# ---------------------------------------------------------------------------
# T014: Integration Tests cho Phân loại Tri thức (assemble_operational_case)
# ---------------------------------------------------------------------------

def test_assemble_operational_case_confirmed_missing_staffing_baseline(tmp_path: Path) -> None:
    """Xác thực phân loại confirmed cho lỗi thiếu baseline nhân sự (vi/en/ja)."""
    history_root = tmp_path / "run_history"
    init_synthetic_history_db(history_root)
    make_fixture_validate_staffing_baseline_error(history_root, "run-staffing-1")

    # 1. Tiếng Việt (vi)
    case_vi = assemble_operational_case(history_root, "run-staffing-1", language="vi")
    assert case_vi.classification == "missing_staffing_baseline"
    assert case_vi.confidence == "confirmed"
    assert case_vi.stage == "validate_staffing"
    assert case_vi.summary == "Thiếu dữ liệu nhân sự mốc ban đầu (Baseline tháng 03)"
    assert len(case_vi.guidance) >= 4
    assert any("nhân sự" in step.lower() for step in case_vi.guidance)
    assert case_vi.presentation is not None
    assert case_vi.presentation.language == "vi"
    assert case_vi.presentation.what_happened
    assert case_vi.presentation.why_it_happened
    # Khẳng định không có raw traceback/exception/JSON trong summary/guidance
    assert "Traceback" not in case_vi.summary
    assert "Error" not in case_vi.summary

    # 2. Tiếng Anh (en)
    case_en = assemble_operational_case(history_root, "run-staffing-1", language="en")
    assert case_en.classification == "missing_staffing_baseline"
    assert case_en.confidence == "confirmed"
    assert case_en.summary == "Missing Baseline Staffing Data (March Baseline)"
    assert len(case_en.guidance) >= 4
    assert case_en.presentation is not None
    assert case_en.presentation.language == "en"

    # 3. Tiếng Nhật (ja)
    case_ja = assemble_operational_case(history_root, "run-staffing-1", language="ja")
    assert case_ja.classification == "missing_staffing_baseline"
    assert case_ja.confidence == "confirmed"
    assert case_ja.summary == "人員配置の基準データ（3月ベースライン）の不足"
    assert len(case_ja.guidance) >= 4
    assert case_ja.presentation is not None
    assert case_ja.presentation.language == "ja"


def test_assemble_operational_case_confirmed_blocked_output_file_lock(tmp_path: Path) -> None:
    """Xác thực phân loại confirmed cho lỗi khóa tệp Excel đầu ra (vi/en/ja)."""
    history_root = tmp_path / "run_history"
    init_synthetic_history_db(history_root)
    make_fixture_locked_output_error(history_root, "run-lock-1")

    # 1. Tiếng Việt (vi)
    case_vi = assemble_operational_case(history_root, "run-lock-1", language="vi")
    assert case_vi.classification == "blocked_output_file_lock"
    assert case_vi.confidence == "confirmed"
    assert case_vi.stage == "publication"
    assert case_vi.summary == "Tệp Excel đầu ra đang bị khóa hoặc mở bởi ứng dụng khác"
    assert len(case_vi.guidance) >= 4
    assert "OutputPublicationLockedError" not in case_vi.summary

    # 2. Tiếng Anh (en)
    case_en = assemble_operational_case(history_root, "run-lock-1", language="en")
    assert case_en.classification == "blocked_output_file_lock"
    assert case_en.confidence == "confirmed"
    assert case_en.summary == "Output Excel Workbook is Locked by Another Application"

    # 3. Tiếng Nhật (ja)
    case_ja = assemble_operational_case(history_root, "run-lock-1", language="ja")
    assert case_ja.classification == "blocked_output_file_lock"
    assert case_ja.confidence == "confirmed"
    assert case_ja.summary == "出力先Excelファイルが他のアプリケーションによりロックされています"


def test_assemble_operational_case_confirmed_preflight_source_validation_failure(tmp_path: Path) -> None:
    """Xác thực phân loại confirmed cho lỗi kiểm tra tiền trạm file nguồn (vi/en/ja)."""
    history_root = tmp_path / "run_history"
    init_synthetic_history_db(history_root)
    make_fixture_preflight_source_validation_failure(history_root, "run-preflight-1")

    # 1. Tiếng Việt (vi)
    case_vi = assemble_operational_case(history_root, "run-preflight-1", language="vi")
    assert case_vi.classification == "preflight_source_validation_failure"
    assert case_vi.confidence == "confirmed"
    assert case_vi.stage == "preflight"
    assert case_vi.summary == "Tệp dữ liệu nguồn đã chọn chưa thể dùng để tính toán"
    assert len(case_vi.guidance) >= 5

    # 2. Tiếng Anh (en)
    case_en = assemble_operational_case(history_root, "run-preflight-1", language="en")
    assert case_en.classification == "preflight_source_validation_failure"
    assert case_en.confidence == "confirmed"
    assert case_en.summary == "A Selected Source File Cannot Be Used for This Calculation"

    # 3. Tiếng Nhật (ja)
    case_ja = assemble_operational_case(history_root, "run-preflight-1", language="ja")
    assert case_ja.classification == "preflight_source_validation_failure"
    assert case_ja.confidence == "confirmed"
    assert case_ja.summary == "入力元データファイルの形式または構造が不正です"


def test_assemble_operational_case_unknown_for_unmatched_and_succeeded_runs(tmp_path: Path) -> None:
    """Xác thực case thành công hoặc lỗi không xác định trả về fallback presentation chuẩn tắc."""
    history_root = tmp_path / "run_history"
    init_synthetic_history_db(history_root)
    make_fixture_succeeded_run(history_root, "run-succ-1")

    case = assemble_operational_case(history_root, "run-succ-1", language="vi")
    assert case.classification == "unknown"
    assert case.confidence == "unknown"
    assert case.presentation is not None
    assert case.presentation.language == "vi"
    assert case.summary == case.presentation.title
    assert case.guidance == case.presentation.what_to_do
    assert len(case.guidance) >= 3
    assert case.summary == "Lần chạy đã hoàn tất"
    assert case.presentation.confidence_label == "Không có lỗi được ghi nhận"
    assert "nguyên nhân" not in case.presentation.title.lower()


def test_assemble_operational_case_succeeded_run_is_not_presented_as_a_failure(tmp_path: Path) -> None:
    """A completed run must not be described as an unconfirmed error in any UI language."""
    history_root = tmp_path / "run_history"
    init_synthetic_history_db(history_root)
    make_fixture_succeeded_run(history_root, "run-succeeded-language-check")

    expected_titles = {
        "vi": "Lần chạy đã hoàn tất",
        "en": "Calculation Run Completed",
        "ja": "計算処理は完了しました",
    }
    for language, expected_title in expected_titles.items():
        case = assemble_operational_case(history_root, "run-succeeded-language-check", language=language)
        assert case.status == "SUCCEEDED"
        assert case.classification == "unknown"
        assert case.presentation is not None
        assert case.presentation.title == expected_title
        assert "confirm the root cause" not in case.presentation.what_happened.lower()


def test_assemble_operational_case_unknown_on_corrupt_or_missing_evidence(tmp_path: Path) -> None:
    """Xác thực bằng chứng bị hỏng (mismatch) hoặc thiếu (missing) sẽ hạ bậc về unknown kèm fallback presentation."""
    history_root = tmp_path / "run_history"
    init_synthetic_history_db(history_root)
    ws = make_fixture_locked_output_error(history_root, "run-lock-corrupt")

    # Làm hỏng JSON pipeline_stage_evidence.json
    (ws / "reports" / "pipeline_stage_evidence.json").write_text("{corrupt json", encoding="utf-8")

    case = assemble_operational_case(history_root, "run-lock-corrupt", language="vi")
    assert case.classification == "unknown"
    assert case.confidence == "unknown"
    assert case.presentation is not None
    assert case.summary == case.presentation.title
    assert case.guidance == case.presentation.what_to_do
    ref_stage = [e for e in case.evidence if e.type == "stage_evidence"][0]
    assert ref_stage.verification == "mismatch"


def test_assemble_operational_case_requires_every_rule_evidence(tmp_path: Path) -> None:
    """A matching phrase alone must not confirm a rule whose trace evidence is absent; returns unknown with presentation."""
    history_root = tmp_path / "run_history"
    init_synthetic_history_db(history_root)
    ws = make_fixture_validate_staffing_baseline_error(history_root, "run-staffing-no-trace")
    (ws / "reports" / "failure_traceback.txt").unlink()

    case = assemble_operational_case(history_root, "run-staffing-no-trace", language="vi")
    assert case.classification == "unknown"
    assert case.confidence == "unknown"
    assert case.presentation is not None
    assert case.presentation.language == "vi"
    assert case.summary == case.presentation.title
    assert case.guidance == case.presentation.what_to_do
    trace_ref = next(item for item in case.evidence if item.type == "failure_traceback")
    assert trace_ref.verification == "missing"


def test_assemble_operational_case_returns_unknown_for_ambiguous_rules(tmp_path: Path) -> None:
    """Two independently verified rules must remain unknown instead of guessing one cause, using unknown presentation."""
    history_root = tmp_path / "run_history"
    init_synthetic_history_db(history_root)
    ws = make_fixture_validate_staffing_baseline_error(history_root, "run-ambiguous")
    report_path = ws / "reports" / "preflight_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["ok"] = False
    report["issues"] = [{
        "category": "facility",
        "selected_path": "Facility_2028.xlsx",
        "detected_fiscal_year": 2028,
        "expected_fiscal_year": 2028,
        "status": "FAILED",
        "code": "SOURCE_VALIDATION_FAILED",
        "severity": "BLOCKING",
        "impact": "Kết quả chưa thể được xác nhận.",
        "checksum": None,
        "sheet": None,
        "period_coverage": [],
        "reason": "Thiếu cột bắt buộc trong file nguồn.",
        "required_action": "Sửa file nguồn rồi kiểm tra lại.",
    }]
    report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

    case = assemble_operational_case(history_root, "run-ambiguous", language="vi")
    assert case.classification == "unknown"
    assert case.confidence == "unknown"
    assert case.presentation is not None
    assert case.summary == case.presentation.title
    assert case.guidance == case.presentation.what_to_do
    assert len(case.guidance) >= 3


def test_assemble_operational_case_unknown_fallback_presentation_multilingual(tmp_path: Path) -> None:
    """Xác thực presentation fallback unknown đầy đủ cho vi/en/ja và không chứa forbidden tokens."""
    history_root = tmp_path / "run_history"
    init_synthetic_history_db(history_root)
    ws = make_fixture_validate_staffing_baseline_error(history_root, "run-unknown-lang")
    (ws / "reports" / "failure_traceback.txt").unlink()

    for lang, expected_title, expected_conf_label in [
        ("vi", "Chưa thể xác nhận chính xác nguyên nhân xử lý", "Chưa xác nhận"),
        ("en", "Unable to Confirm the Root Cause", "Unconfirmed"),
        ("ja", "処理結果の原因を確定できません", "未確定"),
    ]:
        case = assemble_operational_case(history_root, "run-unknown-lang", language=lang)
        assert case.classification == "unknown"
        assert case.confidence == "unknown"
        assert case.presentation is not None
        assert case.presentation.language == lang
        assert case.presentation.title == expected_title
        assert case.presentation.confidence_label == expected_conf_label
        assert len(case.presentation.what_happened) > 0
        assert len(case.presentation.why_it_happened) > 0
        assert len(case.presentation.what_to_do) >= 3
        assert case.summary == case.presentation.title
        assert case.guidance == case.presentation.what_to_do

        # Khẳng định không có raw traceback/exception/JSON/internal status trong nội dung chính
        for text_val in (
            case.presentation.title,
            case.presentation.what_happened,
            case.presentation.why_it_happened,
            *case.presentation.what_to_do,
        ):
            assert "Traceback" not in text_val
            assert "Error" not in text_val
            assert "Exception" not in text_val
            assert "FAILED" not in text_val
            assert "PRECHECK_FAILED" not in text_val
            assert "pipeline_stage_evidence" not in text_val
            assert "{" not in text_val
            assert "}" not in text_val


def test_assemble_operational_case_rejects_unsupported_language(tmp_path: Path) -> None:
    """Xác thực từ chối ngôn ngữ không được hỗ trợ (không tự ý fallback)."""
    history_root = tmp_path / "run_history"
    init_synthetic_history_db(history_root)
    make_fixture_succeeded_run(history_root, "run-succ-lang")

    with pytest.raises(ValueError, match="không được hỗ trợ"):
        assemble_operational_case(history_root, "run-succ-lang", language="fr")


# ---------------------------------------------------------------------------
# T016: Multilingual Presentation Contract Test across Live Case Types
# ---------------------------------------------------------------------------

def test_multilingual_presentation_contract_across_all_operational_case_types(tmp_path: Path) -> None:
    """Khóa chất lượng toàn diện của hợp đồng trình bày đa ngôn ngữ (VI/EN/JA) trên mọi case thực tế."""
    history_root = tmp_path / "contract_run_history"
    init_synthetic_history_db(history_root)

    # Khởi tạo 5 fixture đại diện đầy đủ cho 3 lỗi confirmed + 1 unknown failure + 1 succeeded run
    make_fixture_validate_staffing_baseline_error(history_root, "case-staffing")
    make_fixture_locked_output_error(history_root, "case-lock")
    make_fixture_preflight_source_validation_failure(history_root, "case-source")
    
    ws_unconfirmed = make_fixture_validate_staffing_baseline_error(history_root, "case-unconfirmed")
    (ws_unconfirmed / "reports" / "failure_traceback.txt").unlink()
    
    make_fixture_succeeded_run(history_root, "case-succeeded")

    cases_to_test = [
        ("case-staffing", "missing_staffing_baseline", "confirmed", False),
        ("case-lock", "blocked_output_file_lock", "confirmed", False),
        ("case-source", "preflight_source_validation_failure", "confirmed", False),
        ("case-unconfirmed", "unknown", "unknown", False),
        ("case-succeeded", "unknown", "unknown", True),
    ]

    for run_id, expected_classification, expected_confidence, is_succeeded in cases_to_test:
        for lang in ("vi", "en", "ja"):
            case = assemble_operational_case(history_root, run_id, language=lang)

            # 1. Trạng thái phân loại và độ tin cậy
            assert case.classification == expected_classification
            assert case.confidence == expected_confidence

            # 2. Hợp đồng Presentation
            assert case.presentation is not None
            pres = case.presentation
            assert pres.language == lang

            # 3. Đầy đủ 7 trường bắt buộc không rỗng
            assert len(pres.title.strip()) > 0
            assert len(pres.what_happened.strip()) > 0
            assert len(pres.why_it_happened.strip()) > 0
            assert len(pres.what_to_do) >= 3
            for step in pres.what_to_do:
                assert len(step.strip()) > 0
            assert len(pres.confidence_label.strip()) > 0
            assert len(pres.evidence_label.strip()) > 0
            assert len(pres.technical_details_label.strip()) > 0

            # 4. Đồng bộ giữa OperationalCase và GuidancePresentation
            assert case.summary == pres.title
            assert case.guidance == pres.what_to_do

            # 5. Khẳng định không chứa bất kỳ forbidden tokens nào trong nội dung chính
            for text_val in (
                pres.title,
                pres.what_happened,
                pres.why_it_happened,
                *pres.what_to_do,
            ):
                assert "Traceback" not in text_val
                assert "Error" not in text_val
                assert "Exception" not in text_val
                assert "FAILED" not in text_val
                assert "PRECHECK_FAILED" not in text_val
                assert "pipeline_stage_evidence" not in text_val
                assert "preflight_report" not in text_val
                assert "run_manifest" not in text_val
                assert "failure_traceback" not in text_val
                assert "{{" not in text_val
                assert "}}" not in text_val
                assert "i18n." not in text_val
                assert "translation_key" not in text_val
                assert "TODO" not in text_val
                assert "TBD" not in text_val
                assert "{" not in text_val
                assert "}" not in text_val

            # 6. Kiểm tra ngữ nghĩa đặc thù của từng loại case
            if is_succeeded:
                # Succeeded run: khẳng định thông báo hoàn tất, không nói về root cause hay unconfirmed cause
                assert "root cause" not in pres.title.lower()
                assert "root cause" not in pres.what_happened.lower()
                assert "unconfirmed cause" not in pres.what_happened.lower()
                assert "chưa xác nhận nguyên nhân" not in pres.title.lower()
                assert "chưa xác nhận nguyên nhân" not in pres.what_happened.lower()
                if lang == "vi":
                    assert "hoàn tất" in pres.title.lower() or "hoàn tất" in pres.what_happened.lower()
                elif lang == "en":
                    assert "completed" in pres.title.lower() or "completed" in pres.what_happened.lower()
                elif lang == "ja":
                    assert "完了" in pres.title or "完了" in pres.what_happened
            elif expected_classification == "unknown":
                # Unknown failure: phải nói rõ nguyên nhân chưa được xác nhận
                if lang == "vi":
                    assert "chưa thể xác nhận" in pres.title.lower() or "chưa thể xác định" in pres.what_happened.lower()
                elif lang == "en":
                    assert "unable to confirm" in pres.title.lower() or "unconfirmed" in pres.what_happened.lower()
                elif lang == "ja":
                    assert "確定できません" in pres.title or "確定できません" in pres.what_happened

