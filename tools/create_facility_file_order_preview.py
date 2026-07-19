"""Tạo workbook xem trước tường minh theo thứ tự tệp Facility."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.engine.facility_file_order_writer import write_facility_file_order_preview_workbook
from src.utils.cli import VietnameseArgumentParser


def build_parser() -> argparse.ArgumentParser:
    parser = VietnameseArgumentParser(
        description="Tạo workbook xem trước theo thứ tự tệp Facility mà không thay đổi cách xuất mặc định.",
    )
    parser.add_argument("--template", required=True, help="Đường dẫn workbook mẫu FORM, ví dụ FORM.xlsx")
    parser.add_argument("--facility-source", required=True, help="Đường dẫn workbook nguồn Facility")
    parser.add_argument("--output", required=True, help="Đường dẫn workbook kết quả tường minh")
    parser.add_argument("--cost-center", default="1412000040", help="Mã bộ phận cần xem trước")
    parser.add_argument("--start-row", type=int, default=200, help="Dòng đầu tiên của nhóm xem trước Facility")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        output = write_facility_file_order_preview_workbook(
            template_path=args.template,
            facility_source_path=args.facility_source,
            output_path=args.output,
            cost_center=args.cost_center,
            start_row=args.start_row,
        )
    except Exception:  # pragma: no cover - CLI boundary
        print("Lỗi: Không thể tạo workbook xem trước Facility.", file=sys.stderr)
        return 1
    print(f"Đã tạo workbook: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
