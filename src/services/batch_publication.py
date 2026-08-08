"""Atomic publication of a selected multi-cost-center GUI batch.

Individual cost-center runs remain in immutable history workspaces. This module
prepares a complete overlay privately and swaps it into the public output only
after every requested workbook has been staged successfully.
"""

from __future__ import annotations

from pathlib import Path
import shutil
from uuid import uuid4

from src.services.run_history import _remove_tree_with_retry, _rename_with_retry


class BatchPublicationError(RuntimeError):
    """Raised when a selected-CC batch cannot be safely published."""


def publish_selected_cc_batch(
    public_output_dir: str | Path,
    staged_output_dir: str | Path,
    selected_cost_centers: tuple[str, ...],
) -> str:
    """Atomically overlay exactly *selected_cost_centers* from one batch stage.

    No public file changes until every requested workbook has been verified in
    ``staged_output_dir`` and the complete prepared snapshot is ready.
    """
    destination = Path(public_output_dir)
    source = Path(staged_output_dir)
    if not source.is_dir():
        raise BatchPublicationError(f"Không có thư mục staging batch: {source}")
    expected = {f"MP_CC_{str(cc).strip()}.xlsx" for cc in selected_cost_centers if str(cc).strip()}
    if not expected:
        raise BatchPublicationError("Batch công bố cần ít nhất một cost center.")
    staged = {path.name for path in source.glob("MP_CC_*.xlsx")}
    if staged != expected:
        missing = sorted(expected - staged)
        unexpected = sorted(staged - expected)
        details = []
        if missing:
            details.append("thiếu: " + ", ".join(missing))
        if unexpected:
            details.append("không thuộc batch: " + ", ".join(unexpected))
        raise BatchPublicationError("Staging batch không toàn vẹn (" + "; ".join(details) + ").")

    destination.parent.mkdir(parents=True, exist_ok=True)
    token = uuid4().hex
    prepared = destination.parent / f".{destination.name}.{token}.batch-publishing"
    backup = destination.parent / f".{destination.name}.{token}.batch-backup"
    moved_current = False
    published = False
    publication_complete = False
    try:
        if destination.exists():
            shutil.copytree(destination, prepared, ignore=shutil.ignore_patterns("BAO_CAO_KIEM_TRA"))
        else:
            prepared.mkdir()
        for name in expected:
            shutil.copy2(source / name, prepared / name)
        staged_reports = source / "BAO_CAO_KIEM_TRA"
        if staged_reports.is_dir():
            shutil.copytree(staged_reports, prepared / "BAO_CAO_KIEM_TRA")
        if destination.exists():
            _rename_with_retry(destination, backup)
            moved_current = True
        _rename_with_retry(prepared, destination)
        published = True
        publication_complete = True
    except Exception:
        if published and destination.exists():
            _remove_tree_with_retry(destination)
        if moved_current and backup.exists():
            _rename_with_retry(backup, destination)
        raise
    finally:
        if prepared.exists():
            _remove_tree_with_retry(prepared)
        if backup.exists() and publication_complete and destination.exists():
            try:
                _remove_tree_with_retry(backup)
            except PermissionError:
                pass
        elif backup.exists() and not destination.exists():
            _rename_with_retry(backup, destination)
    return str(destination)
