"""CLI: extract departmental staffing truth from FY reference workbooks."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from src.services.reference_staffing_extractor import extract_reference_staffing_sources


def main() -> int:
    parser = argparse.ArgumentParser(description="Trích xuất nguồn nhân sự/thời gian có provenance từ workbook FY")
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--official-source")
    parser.add_argument("--fy", type=int, default=2027)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    result = extract_reference_staffing_sources(args.source, args.output, args.fy, args.official_source, args.overwrite)
    print(f"Đã quét {result['files']} file: READY={result['ready']}, SPLIT_REQUIRED={result['split_required']}, ERROR={len(result['errors'])}")
    print(f"Manifest: {result['manifest_path']}")
    for item in result["errors"]: print(f"LỖI {Path(item.source_path).name}: {'; '.join(item.errors)}")
    return 1 if result["errors"] else 0

if __name__ == "__main__": raise SystemExit(main())
