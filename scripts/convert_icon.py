import argparse
from pathlib import Path
import sys

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.cli import VietnameseArgumentParser

ICON_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def main(argv: list[str] | None = None) -> int:
    parser = VietnameseArgumentParser(description="Chuyển ảnh PNG thành biểu tượng ứng dụng Windows có nhiều kích thước.")
    parser.add_argument("input", type=Path, help="Ảnh PNG nguồn")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "assets" / "app_icon.ico",
        help="Đường dẫn ICO kết quả (mặc định: assets/app_icon.ico)",
    )
    args = parser.parse_args(argv)
    source = args.input.expanduser().resolve()
    target = args.output.expanduser().resolve()
    if not source.is_file():
        parser.error(f"Ảnh đầu vào không tồn tại: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image.save(target, sizes=ICON_SIZES)
    print(f"Đã lưu biểu tượng tại {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
