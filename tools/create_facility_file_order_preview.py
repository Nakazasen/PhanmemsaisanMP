"""Create an explicit Facility file-order preview workbook."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.engine.facility_file_order_writer import write_facility_file_order_preview_workbook


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a Facility file-order preview workbook without changing default export behavior.",
    )
    parser.add_argument("--template", required=True, help="Path to FORM template workbook, e.g. FORM.xlsx")
    parser.add_argument("--facility-source", required=True, help="Path to Facility source workbook")
    parser.add_argument("--output", required=True, help="Explicit output workbook path")
    parser.add_argument("--cost-center", default="1412000040", help="Cost center code to preview")
    parser.add_argument("--start-row", type=int, default=200, help="First row for Facility preview group")
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
    except Exception as exc:  # pragma: no cover - CLI boundary
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
