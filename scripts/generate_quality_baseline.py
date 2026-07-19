"""Tạo đường cơ sở chất lượng kỹ thuật MP2027 nhanh và có thể tái lập."""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.cli import VietnameseArgumentParser

SCAN_ROOTS = ("src", "scripts", "packaging", "tests")
ABSOLUTE_WINDOWS_PATH = re.compile(r"(?<![A-Za-z0-9_])[A-Z]:[\\/][A-Za-z0-9_.~$]")
SEVERITIES = ("critical", "high", "medium", "low")
SEVERITY_LABELS = {"critical": "nghiêm trọng", "high": "cao", "medium": "trung bình", "low": "thấp"}
RULE_LABELS = {
    "python-parse-error": "lỗi cú pháp Python",
    "bare-except": "khối except không chỉ định loại lỗi",
    "large-module": "module có kích thước lớn",
    "hardcoded-windows-path": "đường dẫn Windows được ghi trực tiếp",
}
SUMMARY_LABELS = {
    "python_files": "Số tệp Python",
    "python_lines": "Số dòng Python",
    "test_count": "Số kiểm thử thu thập được",
    "test_collection_error": "Lỗi thu thập kiểm thử",
    "findings_by_severity": "Phát hiện theo mức độ",
}


def python_files() -> list[Path]:
    files: list[Path] = []
    for name in SCAN_ROOTS:
        base = ROOT / name
        if base.exists():
            files.extend(path for path in base.rglob("*.py") if "__pycache__" not in path.parts)
    return sorted(files)


def module_kind(path: str) -> str:
    mappings = (("tests/", "test"), ("src/parsers/", "parser"),
                ("src/engine/", "business_engine"), ("src/services/", "service"),
                ("src/db/", "database"), ("src/audit/", "audit"),
                ("scripts/", "developer_tool"), ("packaging/", "packaging"))
    return next((kind for prefix, kind in mappings if path.startswith(prefix)), "application")


def collect_test_count() -> tuple[int | None, str | None]:
    try:
        result = subprocess.run(
            ["py", "-m", "pytest", "--collect-only", "-q"], cwd=ROOT,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=180, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, "Không thể thu thập danh sách kiểm thử trong thời gian cho phép."
    output = "\n".join((result.stdout, result.stderr))
    match = re.search(r"(\d+) tests? collected", output)
    return (int(match.group(1)), None) if result.returncode in {0, 5} and match else (None, "Không thể xác định số lượng kiểm thử đã thu thập.")


def scan(*, collect_tests: bool = True) -> dict:
    modules, findings = [], []
    total_lines = 0
    for file_path in python_files():
        relative = file_path.relative_to(ROOT).as_posix()
        lines = file_path.read_text(encoding="utf-8-sig").splitlines()
        total_lines += len(lines)
        functions = classes = 0
        imports: set[str] = set()
        try:
            tree = ast.parse("\n".join(lines), filename=relative)
        except SyntaxError as exc:
            findings.append({"severity": "high", "rule": "python-parse-error", "path": relative,
                             "line": exc.lineno or 1, "message": "Không thể phân tích cú pháp Python; cần kiểm tra dòng được chỉ ra."})
            tree = None
        if tree is not None:
            functions = sum(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) for node in ast.walk(tree))
            classes = sum(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module)
                elif isinstance(node, ast.ExceptHandler) and node.type is None:
                    findings.append({"severity": "medium", "rule": "bare-except", "path": relative,
                                     "line": node.lineno, "message": "Khối except trống có thể che giấu lỗi không mong đợi."})
        if len(lines) >= 1500:
            findings.append({"severity": "medium", "rule": "large-module", "path": relative, "line": 1,
                             "message": f"Có {len(lines)} dòng; cần kiểm thử bảo vệ trước khi tách module theo từng giai đoạn."})
        if not relative.startswith("tests/"):
            for number, line in enumerate(lines, 1):
                if ABSOLUTE_WINDOWS_PATH.search(line):
                    findings.append({"severity": "high", "rule": "hardcoded-windows-path", "path": relative,
                                     "line": number, "message": "Có thể tồn tại đường dẫn Windows tuyệt đối trong mã chạy thực tế."})
        modules.append({"path": relative, "kind": module_kind(relative), "lines": len(lines),
                        "functions": functions, "classes": classes,
                        "internal_imports": sorted(name for name in imports if name.startswith(("src.", "scripts.")))})
    order = {name: index for index, name in enumerate(SEVERITIES)}
    findings.sort(key=lambda item: (order[item["severity"]], item["path"], item["line"]))
    test_count, test_error = collect_test_count() if collect_tests else (None, None)
    counts = Counter(item["severity"] for item in findings)
    return {"schema_version": 1,
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "scope": {"roots": list(SCAN_ROOTS), "private_runtime_data_scanned": False,
                      "business_pipeline_executed": False},
            "summary": {"python_files": len(modules), "python_lines": total_lines,
                        "test_count": test_count, "test_collection_error": test_error,
                        "findings_by_severity": {name: counts.get(name, 0) for name in SEVERITIES}},
            "modules": modules, "findings": findings}


def markdown(report: dict) -> str:
    summary, findings = report["summary"], report["findings"]
    blockers = [item for item in findings if item["severity"] in {"critical", "high"}]
    lines = ["# Kiểm toán kỹ thuật hiện tại của MP2027", "", f"Thời điểm tạo: `{report['generated_at']}`", "",
             "> Đây chỉ là đường cơ sở tĩnh nhanh: không mở tệp Excel riêng tư, cơ sở dữ liệu runtime hoặc pipeline nghiệp vụ.", "",
             "## Tóm tắt", "", f"- Số tệp Python: **{summary['python_files']}**",
             f"- Số dòng Python: **{summary['python_lines']}**",
             f"- Số kiểm thử thu thập được: **{summary['test_count'] if summary['test_count'] is not None else 'không xác định'}**",
             "- Phát hiện: " + ", ".join(f"{SEVERITY_LABELS.get(key, key)}={value}" for key, value in summary["findings_by_severity"].items()),
             "", "## Quyết định đóng gói", "",
             (f"> **CHƯA SẴN SÀNG:** cần phân loại {len(blockers)} phát hiện mức nghiêm trọng/cao trước khi đóng gói phát hành."
              if blockers else "> **ĐÃ ĐẠT CỔNG KIỂM TRA TĨNH:** vẫn phải kiểm tra vận hành và nghiệm thu nghiệp vụ."),
             "", "## Các phát hiện", ""]
    if findings:
        lines += ["| Mức độ | Quy tắc | Vị trí | Thông báo |", "|---|---|---|---|"]
        lines += [f"| {SEVERITY_LABELS.get(item['severity'], item['severity'])} | {RULE_LABELS.get(item['rule'], item['rule'])} | `{item['path']}:{item['line']}` | {item['message'].replace('|', '/')} |" for item in findings]
    else:
        lines.append("Không có phát hiện tĩnh trong phạm vi đã cấu hình.")
    lines += ["", "## Tạo lại báo cáo", "", "```powershell", "py scripts/generate_quality_baseline.py", "```", "",
              "Kết quả dành cho máy đọc: `reports/quality_baseline.json`.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = VietnameseArgumentParser(description="Tạo đường cơ sở chất lượng kỹ thuật MP2027 nhanh và có thể tái lập.")
    parser.add_argument("--json", type=Path, default=ROOT / "reports" / "quality_baseline.json", help="Đường dẫn JSON kết quả")
    parser.add_argument("--markdown", type=Path, default=ROOT / "docs" / "audits" / "current_technical_audit.md", help="Đường dẫn báo cáo Markdown")
    parser.add_argument("--skip-test-collection", action="store_true", help="Không thu thập danh sách kiểm thử")
    parser.add_argument("--fail-on-high", action="store_true", help="Trả mã lỗi nếu có phát hiện mức critical hoặc high")
    args = parser.parse_args(argv)
    report = scan(collect_tests=not args.skip_test_collection)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(report), encoding="utf-8")
    display_summary = {
        SUMMARY_LABELS.get(key, key): (
            {SEVERITY_LABELS.get(name, name): count for name, count in value.items()}
            if key == "findings_by_severity" else value
        )
        for key, value in report["summary"].items()
    }
    print(json.dumps(display_summary, ensure_ascii=False, indent=2))
    return 2 if args.fail_on_high and any(item["severity"] in {"critical", "high"} for item in report["findings"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
