"""CLI trích xuất nguồn sự thật nhân sự theo bộ phận từ các tệp Excel tham chiếu FY."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from src.services.reference_staffing_extractor import extract_reference_staffing_sources
from src.utils.cli import VietnameseArgumentParser


def main() -> int:
    parser = VietnameseArgumentParser(description="Trích xuất nguồn nhân sự/thời gian có thông tin nguồn gốc từ tệp Excel FY")
    parser.add_argument("--source", required=True, help="Thư mục hoặc tệp nguồn tham chiếu")
    parser.add_argument("--output", required=True, help="Thư mục ghi kết quả trích xuất")
    parser.add_argument("--official-source", help="Đường dẫn nguồn chính thức nếu có")
    parser.add_argument("--fy", type=int, default=2027, help="Năm tài chính cần xử lý")
    parser.add_argument("--overwrite", action="store_true", help="Cho phép ghi đè kết quả đã có")
    args = parser.parse_args()
    result = extract_reference_staffing_sources(args.source, args.output, args.fy, args.official_source, args.overwrite)
    print(f"Đã quét {result['files']} tệp: READY={result['ready']}, SPLIT_REQUIRED={result['split_required']}, ERROR={len(result['errors'])}")
    print(f"Tệp kê khai: {result['manifest_path']}")
    for item in result["errors"]:
        print(f"LỖI {Path(item.source_path).name}: Không thể trích xuất nguồn nhân sự/thời gian.")
    return 1 if result["errors"] else 0

if __name__ == "__main__": raise SystemExit(main())
