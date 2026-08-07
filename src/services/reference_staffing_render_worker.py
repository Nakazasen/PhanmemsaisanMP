"""Tiến trình COM Excel tách biệt để dựng sổ nhân sự tham chiếu.

Tiến trình cha vẫn chọn nguồn nghiệp vụ, đối chiếu, kiểm tra sau khi dựng, tạo
danh mục và công bố. Tiến trình phụ này chỉ quản lý vòng đời dựng dựa trên Excel.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from src.services.reference_staffing_extractor import (
    ExtractedDepartment,
    _CompanyFormRenderer,
)

PROTOCOL_VERSION = 1


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _write_status(
    path: Path,
    *,
    state: str,
    current_file: str = "",
    completed_files: list[str] | None = None,
) -> None:
    _atomic_write_json(
        path,
        {
            "protocol_version": PROTOCOL_VERSION,
            "state": state,
            "current_file": current_file,
            "completed_files": list(completed_files or []),
        },
    )


def run_worker(request_path: Path, response_path: Path, status_path: Path) -> int:
    """Render all requested workbooks and write a fail-closed response."""
    completed: list[str] = []
    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
        if request.get("protocol_version") != PROTOCOL_VERSION:
            raise ValueError("Giao thức worker không được hỗ trợ")

        template_path = Path(request["template_path"]).resolve()
        stage_dir = Path(request["stage_dir"]).resolve()
        fiscal_year = int(request["fiscal_year"])
        items = [ExtractedDepartment(**payload) for payload in request["items"]]
        if not items:
            raise ValueError("Yêu cầu worker không chứa bộ phận nào")

        _write_status(status_path, state="starting")
        with _CompanyFormRenderer() as renderer:
            for item in items:
                filename = Path(item.output_path).name
                _write_status(
                    status_path,
                    state="processing",
                    current_file=filename,
                    completed_files=completed,
                )
                renderer.render(
                    item,
                    template_path,
                    stage_dir / filename,
                    fiscal_year,
                )
                completed.append(filename)
                _write_status(
                    status_path,
                    state="processing",
                    completed_files=completed,
                )

        _atomic_write_json(
            response_path,
            {
                "protocol_version": PROTOCOL_VERSION,
                "success": True,
                "rendered_files": completed,
            },
        )
        _write_status(status_path, state="completed", completed_files=completed)
        return 0
    except BaseException as exc:
        # The parent supplies the user-facing message. This response is retained
        # only as a diagnostic contract and is never trusted as a successful render.
        try:
            _atomic_write_json(
                response_path,
                {
                    "protocol_version": PROTOCOL_VERSION,
                    "success": False,
                    "rendered_files": completed,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            _write_status(status_path, state="failed", completed_files=completed)
        except Exception:
            pass
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--request", required=True)
    parser.add_argument("--response", required=True)
    parser.add_argument("--status", required=True)
    args = parser.parse_args(argv)
    return run_worker(Path(args.request), Path(args.response), Path(args.status))


if __name__ == "__main__":
    raise SystemExit(main())
