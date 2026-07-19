"""Tiện ích console và argparse tiếng Việt dùng chung cho các CLI MP2027."""
from __future__ import annotations

import argparse
import re
import sys
from typing import TextIO


class _NullTextIO:
    """Nhận output an toàn khi ứng dụng đóng gói kiểu windowed không có console."""

    encoding = "utf-8"

    def write(self, text: object) -> int:
        return len(str(text))

    def flush(self) -> None:
        return None

    def isatty(self) -> bool:
        return False


def configure_utf8_console() -> None:
    """Giữ tiếng Việt đọc được trên các code page Windows và chế độ windowed."""
    if sys.stdout is None:
        sys.stdout = _NullTextIO()  # type: ignore[assignment]
    if sys.stderr is None:
        sys.stderr = _NullTextIO()  # type: ignore[assignment]
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, TypeError, ValueError):
                pass


def _vietnamese_argparse_message(message: str) -> str:
    """Dịch các lỗi chuẩn thường gặp do argparse tự sinh; giữ nguyên cờ/giá trị."""
    replacements = (
        (r"^the following arguments are required: ", "bắt buộc phải có các đối số: "),
        (r"^one of the arguments ", "phải có một trong các đối số "),
        (r"^unrecognized arguments: ", "đối số không được nhận diện: "),
        (r"^ambiguous option: ", "tùy chọn không rõ ràng: "),
        (r"expected one argument$", "cần một giá trị"),
        (r"expected at least one argument$", "cần ít nhất một giá trị"),
        (r"expected at most one argument$", "chỉ được có tối đa một giá trị"),
        (r"invalid choice: ", "lựa chọn không hợp lệ: "),
        (r"invalid int value: ", "giá trị số nguyên không hợp lệ: "),
        (r"invalid float value: ", "giá trị số không hợp lệ: "),
        (r"not allowed with argument ", "không được dùng cùng đối số "),
        (r"ignored explicit argument ", "bỏ qua đối số tường minh "),
        (r"expected (\d+) arguments?$", r"cần \1 giá trị"),
    )
    translated = message
    for pattern, replacement in replacements:
        translated = re.sub(pattern, replacement, translated)
    translated = translated.replace("argument ", "đối số ", 1)
    return translated


class VietnameseArgumentParser(argparse.ArgumentParser):
    """ArgumentParser có heading, trợ giúp và lỗi mặc định hoàn toàn bằng tiếng Việt."""

    def __init__(self, *args, **kwargs) -> None:
        configure_utf8_console()
        super().__init__(*args, **kwargs)
        self._positionals.title = "đối số vị trí"
        self._optionals.title = "tùy chọn"
        for action in self._actions:
            if isinstance(action, argparse._HelpAction):
                action.help = "hiển thị trợ giúp này và thoát"

    def format_usage(self) -> str:
        usage = super().format_usage()
        return usage.replace("usage: ", "cách dùng: ", 1)

    def format_help(self) -> str:
        help_text = super().format_help()
        return help_text.replace("usage: ", "cách dùng: ", 1)

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        localized = _vietnamese_argparse_message(message)
        self.exit(2, f"{self.prog}: lỗi: {localized}\n")


ArgumentParser = VietnameseArgumentParser


def safe_print(message: object, *, file: TextIO | None = None, flush: bool = False) -> None:
    """In Unicode mà không làm hỏng luồng vận hành nếu console có encoding cũ."""
    configure_utf8_console()
    target = file or sys.stdout
    try:
        print(str(message), file=target, flush=flush)
    except UnicodeEncodeError:
        encoding = getattr(target, "encoding", None) or "utf-8"
        fallback = str(message).encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(fallback, file=target, flush=flush)
