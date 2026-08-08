"""Coordination boundary for a single cost-center workbook export.

The adapter preserves ``HubBuilder`` as the compatible domain façade while
separating output lifecycle coordination from its query and layout operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class WorkbookExportOwner(Protocol):
    def _export_to_template_legacy(self, template_path: str, output_path: str, cc_code: object | None = None, sheet_name: str | None = None, start_row: int = 168) -> bool: ...


@dataclass(frozen=True)
class WorkbookExportRequest:
    template_path: str
    output_path: str
    cc_code: object | None = None
    sheet_name: str | None = None
    start_row: int = 168


class WorkbookExportService:
    """Execute one validated workbook export through its domain owner."""

    def export(self, owner: WorkbookExportOwner, request: WorkbookExportRequest) -> bool:
        return owner._export_to_template_legacy(
            request.template_path,
            request.output_path,
            cc_code=request.cc_code,
            sheet_name=request.sheet_name,
            start_row=request.start_row,
        )
