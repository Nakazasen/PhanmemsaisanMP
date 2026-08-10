"""Quét file text do Git quản lý để phát hiện lỗi mojibake có thể tái hiện."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


TEXT_SUFFIXES = {
    ".bat",
    ".cfg",
    ".csv",
    ".css",
    ".html",
    ".ini",
    ".isl",
    ".iss",
    ".js",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".sql",
    ".toml",
    ".tsv",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
ALLOW_MARKER = "mojibake-allow"
SUSPICIOUS_PATTERNS = {
    "replacement_character": re.compile(r"\ufffd"),
    "c1_control": re.compile(r"[\u0080-\u009f]"),
    "private_use_cp932": re.compile(r"[\uf8f0-\uf8ff]"),
    "latin1_utf8_mojibake": re.compile(
        r"(?:\u00c3[\u0080-\u00bf]|\u00c2[\u0080-\u00bf]|"
        r"\u00e2[\u0080-\u00bf]{1,2}|\u00ef\u00bb\u00bf|\u00f0\u0178)"
    ),
    "known_cp932_mojibake": re.compile(
        r"(?:\u8b41|\u7e67|\u8757|\u862f|\u76fb|\u7ab6|"
        r"\u9aee\uff7b|\u8708\uff65|\u8c4e\uff7a\u894d)"
    ),
}


@dataclass(frozen=True)
class MojibakeIssue:
    path: str
    line: int
    kind: str
    excerpt: str


def tracked_text_paths(root: Path) -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root
    ).decode("utf-8")
    return [
        root / name
        for name in output.split("\0")
        if name and Path(name).suffix.casefold() in TEXT_SUFFIXES
    ]


def _decode_text(path: Path) -> str:
    data = path.read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    return data.decode("utf-8-sig")


def _roundtrip_candidate(line: str) -> str | None:
    for codec in ("cp932", "cp1252", "latin1"):
        try:
            repaired = line.encode(codec).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if repaired != line:
            return codec
    return None


def scan_repository(root: Path | str = ".") -> list[MojibakeIssue]:
    root_path = Path(root).resolve()
    issues: list[MojibakeIssue] = []
    for path in tracked_text_paths(root_path):
        relative = path.relative_to(root_path).as_posix()
        try:
            text = _decode_text(path)
        except UnicodeDecodeError as exc:
            issues.append(MojibakeIssue(relative, 0, "invalid_text_encoding", str(exc)))
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            if ALLOW_MARKER in line:
                continue
            for kind, pattern in SUSPICIOUS_PATTERNS.items():
                if pattern.search(line):
                    issues.append(MojibakeIssue(relative, line_number, kind, line[:240]))
            codec = _roundtrip_candidate(line)
            if codec is not None:
                issues.append(
                    MojibakeIssue(relative, line_number, f"reversible_{codec}", line[:240])
                )
    return issues


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    issues = scan_repository()
    if not issues:
        print("Không phát hiện mojibake trong file text do Git quản lý.")
        return 0
    for issue in issues:
        print(f"{issue.path}:{issue.line}: {issue.kind}: {issue.excerpt}")
    print(f"Phát hiện {len(issues)} vấn đề mojibake/encoding.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
