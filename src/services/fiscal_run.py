"""Fiscal-year source resolution and fail-closed preflight validation.

This module is intentionally independent from the calculation engine.  It
answers one question before a run is allowed to mutate any calculation data:
"are these the approved sources for the fiscal year that was selected?"
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from hashlib import sha256
from pathlib import Path
from functools import lru_cache
import os
import re
import subprocess
import uuid
from typing import Iterable

import openpyxl

from src.engine.uniform_cup_rules import UNIFORM_ITEM_SPECS, normalize_uniform_text
from src.utils.fiscal_periods import fiscal_baseline_period, fiscal_periods
from src.utils.source_manifest import read_source_manifest, resolve_manifest_files


REQUIRED_SOURCE_CATEGORIES = (
    "facility",
    "fixed_assets",
    "it_simulation",
    "ga",
    "birthday",
    "allocation_rules",
    "nnn_paperwork",
    "uniform_policy",
)
REFERENCE_POLICY_DISABLED = "DISABLED"
REFERENCE_POLICY_EXPLICIT_SAME_FY = "EXPLICIT_SAME_FY"
REFERENCE_POLICY_LEGACY_FY2027_MAP = "LEGACY_FY2027_MAP"

_FY_PATTERN = re.compile(r"(?<!\d)FY\s*(20\d{2})(?!\d)", re.IGNORECASE)
_MPFY_PATTERN = re.compile(r"MPFY\s*(20\d{2})(?!\d)", re.IGNORECASE)
_PERIOD_PATTERN = re.compile(r"(?<!\d)(20\d{2})(0[1-9]|1[0-2])(?!\d)")
_MONTH_YEAR_PATTERN = re.compile(
    r"(?i)(?<![A-Za-z])(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"[.\s_-]*(20\d{2})\b"
)
_MONTH_NAMES = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12,
}


@dataclass(frozen=True)
class FiscalYearEvidence:
    """All FY markers found in one source, without choosing one arbitrarily."""

    path: str
    filename_years: tuple[int, ...] = ()
    directory_years: tuple[int, ...] = ()
    sheet_years: tuple[int, ...] = ()
    content_years: tuple[int, ...] = ()
    inspection_error: str | None = None

    @property
    def years(self) -> tuple[int, ...]:
        return tuple(sorted(set((*self.filename_years, *self.directory_years, *self.sheet_years, *self.content_years))))

    @property
    def anchor_years(self) -> tuple[int, ...]:
        """FY markers that identify the selected annual source, not old values."""
        return tuple(sorted(set((*self.filename_years, *self.directory_years, *self.sheet_years))))

    @property
    def resolved_fiscal_year(self) -> int | None:
        if len(self.anchor_years) == 1:
            return self.anchor_years[0]
        return self.content_years[0] if not self.anchor_years and len(self.content_years) == 1 else None

    @property
    def conflict(self) -> bool:
        # A historic price/snapshot year in a cell must not override a clear
        # FY label in the filename, folder or sheet.  Only conflicting annual
        # anchors are a cross-year safety failure.
        return len(self.anchor_years) > 1 or (not self.anchor_years and len(self.content_years) > 1)

    def as_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "filename_years": list(self.filename_years),
            "directory_years": list(self.directory_years),
            "sheet_years": list(self.sheet_years),
            "content_years": list(self.content_years),
            "all_years": list(self.years),
            "inspection_error": self.inspection_error,
        }


@dataclass(frozen=True)
class SourceIssue:
    category: str
    path: str
    detected_fiscal_year: int | None
    reason: str
    action: str
    status: str = "FAILED"
    sheet: str | None = None
    period_coverage: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        candidate = Path(self.path) if self.path else None
        return {
            "category": self.category,
            "selected_path": self.path,
            "detected_fiscal_year": self.detected_fiscal_year,
            "expected_fiscal_year": None,
            "status": self.status,
            "checksum": sha256_file(candidate) if candidate and candidate.is_file() else None,
            "sheet": self.sheet,
            "period_coverage": list(self.period_coverage),
            "reason": self.reason,
            "required_action": self.action,
        }

    def as_text(self) -> str:
        detected = f"FY{self.detected_fiscal_year}" if self.detected_fiscal_year else "không xác định"
        return (
            f"[{self.category}] file={self.path or '(không có)'}; "
            f"năm phát hiện={detected}; lý do={self.reason}; cần làm={self.action}"
        )


@dataclass(frozen=True)
class SourceCheck:
    """One auditable preflight decision, including successful sources."""

    category: str
    selected_path: str
    detected_fiscal_year: int | None
    expected_fiscal_year: int
    status: str
    checksum: str | None
    sheet: str | None = None
    period_coverage: tuple[str, ...] = ()
    reason: str = ""
    required_action: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "category": self.category,
            "selected_path": self.selected_path,
            "detected_fiscal_year": self.detected_fiscal_year,
            "expected_fiscal_year": self.expected_fiscal_year,
            "status": self.status,
            "checksum": self.checksum,
            "sheet": self.sheet,
            "period_coverage": list(self.period_coverage),
            "reason": self.reason,
            "required_action": self.required_action,
        }


@dataclass(frozen=True)
class RunPreflightReport:
    fiscal_year: int
    issues: tuple[SourceIssue, ...] = ()
    resolved_sources: dict[str, tuple[str, ...]] = field(default_factory=dict)
    checks: tuple[SourceCheck, ...] = ()

    def as_dict(self) -> dict[str, object]:
        issues = []
        for issue in self.issues:
            row = issue.as_dict()
            row["expected_fiscal_year"] = self.fiscal_year
            issues.append(row)
        return {
            "fiscal_year": self.fiscal_year,
            "ok": self.ok,
            "issues": issues,
            "checks": [check.as_dict() for check in self.checks],
            "resolved_sources": {key: list(value) for key, value in self.resolved_sources.items()},
        }

    def as_markdown(self) -> str:
        """Human-readable companion to the JSON provenance report."""
        lines = [
            f"# Kiểm tra nguồn trước khi chạy FY{self.fiscal_year}",
            "",
            "| Nhóm nguồn | Trạng thái | File đã chọn | Năm phát hiện | Trang | Kỳ đọc được | Lý do / việc cần làm |",
            "|---|---|---|---|---|---|---|",
        ]
        for check in self.checks:
            year = f"FY{check.detected_fiscal_year}" if check.detected_fiscal_year else "Không xác định"
            detail = check.reason or check.required_action or "Đạt"
            path = check.selected_path or "(chưa có)"
            lines.append(
                "| {category} | {status} | {path} | {year} | {sheet} | {periods} | {detail} |".format(
                    category=check.category,
                    status=check.status,
                    path=path.replace("|", "\\|"),
                    year=year,
                    sheet=check.sheet or "",
                    periods=", ".join(check.period_coverage),
                    detail=detail.replace("|", "\\|"),
                )
            )
        return "\n".join(lines) + "\n"

    @property
    def ok(self) -> bool:
        return not self.issues

    def raise_if_invalid(self) -> None:
        if self.ok:
            return
        detail = "\n".join(f"- {issue.as_text()}" for issue in self.issues)
        raise ValueError(
            f"Kiểm tra nguồn FY{self.fiscal_year} không đạt. Chương trình chưa tạo dữ liệu tính toán.\n{detail}"
        )


@dataclass(frozen=True)
class FiscalRunContext:
    run_id: str
    fiscal_year: int
    fiscal_periods: tuple[str, ...]
    baseline_period: str
    template_path: str
    source_dir: str
    headcount_source_dir: str
    uniform_policy_path: str | None
    output_dir: str
    exchange_rate: float
    exchange_rate_source: str = "not declared"
    resolved_sources: dict[str, tuple[str, ...]] = field(default_factory=dict)
    history_root: str | None = None
    workspace_dir: str | None = None
    database_path: str | None = None
    manual_input_store: str | None = None
    ordered_sources: tuple[dict[str, object], ...] = ()
    reference_policy: str = REFERENCE_POLICY_DISABLED
    application_version: str = "unknown"

    def with_resolution(self, sources: dict[str, tuple[str, ...]]) -> "FiscalRunContext":
        return replace(self, resolved_sources=sources, ordered_sources=resolve_ordered_sources(self))


def _base_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def annual_default_paths(fiscal_year: int, base_dir: str | os.PathLike[str] | None = None) -> dict[str, str]:
    root = Path(base_dir) if base_dir else _base_dir()
    return {
        "template_path": str(root / "docs" / f"MP{fiscal_year}" / "FORM.xlsx"),
        "source_dir": str(root / "docs" / f"MP{fiscal_year}"),
        "headcount_source_dir": str(root / "raw" / f"FY{fiscal_year}"),
        "output_dir": str(root / f"OUTPUT_FY{fiscal_year}"),
        "history_root": str(root / "RUN_HISTORY"),
        "manual_input_store": str(root / "raw" / f"FY{fiscal_year}" / "manual_inputs.db"),
    }


def _has_headcount_workbook(directory: Path) -> bool:
    return directory.is_dir() and any(path.suffix.lower() in {".xls", ".xlsx", ".xlsm"} for path in directory.iterdir())


def _legacy_uniform_policy_path(root: Path) -> Path | None:
    for path in sorted((root / "raw").glob("*.xlsx")):
        try:
            if _is_uniform_policy(path):
                return path
        except Exception:
            continue
    return None


def _file_cache_key(path: str | os.PathLike[str]) -> tuple[str, int, int]:
    """Cache key that changes whenever the source file changes."""
    candidate = Path(path).resolve()
    stat = candidate.stat()
    return str(candidate), int(stat.st_mtime_ns), int(stat.st_size)


@lru_cache(maxsize=128)
def _is_uniform_policy_cached(path: str, _mtime_ns: int, _size: int) -> bool:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        if "原価センタ" not in workbook.sheetnames:
            return False
        sheet = workbook["原価センタ"]
        headers = {
            normalize_uniform_text(sheet.cell(1, column).value)
            for column in range(1, sheet.max_column + 1)
        }
        return all(normalize_uniform_text(spec.header) in headers for spec in UNIFORM_ITEM_SPECS)
    finally:
        workbook.close()


def _is_uniform_policy(path: Path) -> bool:
    try:
        return _is_uniform_policy_cached(*_file_cache_key(path))
    except OSError:
        return False


def resolve_uniform_policy_path(
    fiscal_year: int,
    explicit_path: str | None = None,
    *,
    base_dir: str | os.PathLike[str] | None = None,
) -> str | None:
    if explicit_path:
        return str(Path(explicit_path).resolve())

    root = Path(base_dir) if base_dir else _base_dir()
    annual_dir = root / "raw" / f"FY{fiscal_year}"
    candidates = []
    if annual_dir.is_dir():
        candidates = [path for path in annual_dir.glob("*.xlsx") if _is_uniform_policy(path)]
    if len(candidates) == 1:
        return str(candidates[0].resolve())
    if len(candidates) > 1:
        raise ValueError(
            f"FY{fiscal_year} có nhiều file bảng dấu chọn đồng phục/cốc xếp: "
            + "; ".join(str(path) for path in candidates)
        )
    if fiscal_year == 2027:
        legacy = _legacy_uniform_policy_path(root)
        return str(legacy.resolve()) if legacy else None
    return None


def create_fiscal_run_context(
    fiscal_year: int,
    *,
    template_path: str | None = None,
    source_dir: str | None = None,
    headcount_source_dir: str | None = None,
    uniform_policy_path: str | None = None,
    output_dir: str | None = None,
    exchange_rate: float = 25450.0,
    exchange_rate_source: str = "explicit pipeline input",
    history_root: str | None = None,
    manual_input_store: str | None = None,
    reference_policy: str | None = None,
    base_dir: str | os.PathLike[str] | None = None,
    run_id: str | None = None,
) -> FiscalRunContext:
    year = int(fiscal_year)
    defaults = annual_default_paths(year, base_dir)
    root = Path(base_dir) if base_dir else _base_dir()
    resolved_headcount_dir = headcount_source_dir or defaults["headcount_source_dir"]
    # The FY2027 delivered data predates the annual raw/FY folder convention.
    # Preserve that compatibility only when its annual folder has no workbooks.
    if year == 2027 and not headcount_source_dir and not _has_headcount_workbook(Path(resolved_headcount_dir)):
        resolved_headcount_dir = str(root / "raw")
    resolved_uniform = resolve_uniform_policy_path(year, uniform_policy_path, base_dir=root)
    try:
        git_revision = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        git_revision = "unknown"
    release_version = os.environ.get("MP_MANAGER_VERSION", "unversioned")
    application_version = f"release={release_version};git={git_revision}"
    resolved_reference_policy = reference_policy or (
        REFERENCE_POLICY_LEGACY_FY2027_MAP
        if year == 2027 else REFERENCE_POLICY_DISABLED
    )
    if resolved_reference_policy not in {
        REFERENCE_POLICY_DISABLED,
        REFERENCE_POLICY_EXPLICIT_SAME_FY,
        REFERENCE_POLICY_LEGACY_FY2027_MAP,
    }:
        raise ValueError(f"Chính sách file tham khảo không hợp lệ: {resolved_reference_policy}")
    if year != 2027 and resolved_reference_policy == REFERENCE_POLICY_LEGACY_FY2027_MAP:
        raise ValueError("Chỉ FY2027 mới được dùng bảng tham khảo tương thích cũ.")
    return FiscalRunContext(
        run_id=run_id or uuid.uuid4().hex,
        fiscal_year=year,
        fiscal_periods=tuple(fiscal_periods(year)),
        baseline_period=fiscal_baseline_period(year),
        template_path=str(Path(template_path or defaults["template_path"]).resolve()),
        source_dir=str(Path(source_dir or defaults["source_dir"]).resolve()),
        headcount_source_dir=str(Path(resolved_headcount_dir).resolve()),
        uniform_policy_path=resolved_uniform,
        output_dir=str(Path(output_dir or defaults["output_dir"]).resolve()),
        exchange_rate=float(exchange_rate),
        exchange_rate_source=str(exchange_rate_source or "").strip(),
        history_root=str(Path(history_root or defaults["history_root"]).resolve()),
        manual_input_store=str(Path(manual_input_store or defaults["manual_input_store"]).resolve()),
        reference_policy=resolved_reference_policy,
        application_version=application_version,
    )


def _years_in_text(value: object, *, allow_periods: bool = True) -> set[int]:
    text = str(value or "")
    years = {
        int(match.group(1))
        for pattern in (_FY_PATTERN, _MPFY_PATTERN)
        for match in pattern.finditer(text)
    }
    if allow_periods:
        for match in _PERIOD_PATTERN.finditer(text):
            calendar_year, month = int(match.group(1)), int(match.group(2))
            years.add(calendar_year + 1 if month >= 4 else calendar_year)
    return years


def inspect_fiscal_year_evidence(path: str | os.PathLike[str]) -> FiscalYearEvidence:
    """Inspect filename, sheet names and visible workbook text for FY markers.

    A source is intentionally *not* accepted based on the first marker found.
    This prevents a FY2028 filename from masking a FY2027 business sheet.
    """
    candidate = Path(path).resolve()
    try:
        stat = candidate.stat()
    except OSError:
        stat = None
    return _inspect_fiscal_year_evidence_cached(
        str(candidate),
        int(stat.st_mtime_ns) if stat else -1,
        int(stat.st_size) if stat else -1,
    )


@lru_cache(maxsize=256)
def _inspect_fiscal_year_evidence_cached(
    resolved_path: str,
    _mtime_ns: int,
    _size: int,
) -> FiscalYearEvidence:
    candidate = Path(resolved_path)
    filename_years = _years_in_text(candidate.name)
    directory_years = _years_in_text(candidate.parent.name, allow_periods=False)
    sheet_years: set[int] = set()
    content_years: set[int] = set()
    suffix = candidate.suffix.lower()
    if suffix not in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        return FiscalYearEvidence(
            str(candidate), tuple(sorted(filename_years)), tuple(sorted(directory_years))
        )
    try:
        workbook = openpyxl.load_workbook(candidate, read_only=True, data_only=True)
    except Exception as exc:
        return FiscalYearEvidence(
            str(candidate), tuple(sorted(filename_years)), tuple(sorted(directory_years)), inspection_error=str(exc)
        )
    try:
        for name in workbook.sheetnames:
            sheet_years.update(_years_in_text(name))
            # A bounded scan is deliberate: business FY headings are normally
            # in the title area and scanning entire large workbooks is unsafe.
            sheet = workbook[name]
            for row in sheet.iter_rows(min_row=1, max_row=min(sheet.max_row, 20), values_only=True):
                for value in row[: min(sheet.max_column, 20)]:
                    content_years.update(_years_in_text(value, allow_periods=False))
    finally:
        workbook.close()
    return FiscalYearEvidence(
        str(candidate),
        tuple(sorted(filename_years)),
        tuple(sorted(directory_years)),
        tuple(sorted(sheet_years)),
        tuple(sorted(content_years)),
    )


def validate_fiscal_year_evidence(
    evidence: FiscalYearEvidence,
    expected_fiscal_year: int,
    *,
    required: bool = True,
) -> str | None:
    """Return a deterministic rejection reason, or ``None`` when valid."""
    expected = int(expected_fiscal_year)
    if evidence.conflict:
        if not required and not evidence.anchor_years:
            # Fixed-asset snapshots often contain comparative FY headers.  A
            # separate parser audit validates their month range; do not reject
            # the source merely for historical labels in its cells.
            return None
        found = ", ".join(f"FY{year}" for year in (evidence.anchor_years or evidence.content_years))
        return f"Nguồn chứa dấu hiệu nhiều năm tài chính khác nhau: {found}."
    if evidence.resolved_fiscal_year is None:
        if required:
            return "Không xác định được năm tài chính trong tên file, trang hoặc phần tiêu đề nguồn."
        return None
    if evidence.resolved_fiscal_year != expected:
        return f"Nguồn thuộc FY{evidence.resolved_fiscal_year}, không phải FY{expected}."
    return None


def detect_fiscal_year(path: str | os.PathLike[str]) -> int | None:
    """Compatibility helper that returns a year only when all evidence agrees."""
    return inspect_fiscal_year_evidence(path).resolved_fiscal_year


def _manifest_sources(source_dir: str, category: str) -> tuple[str, ...]:
    return tuple(str(Path(path).resolve()) for path in resolve_manifest_files(source_dir, category))


def resolve_annual_sources(context: FiscalRunContext) -> dict[str, tuple[str, ...]]:
    """Resolve every business source inside the selected annual source folder only."""
    sources: dict[str, tuple[str, ...]] = {}
    for category in REQUIRED_SOURCE_CATEGORIES:
        if category == "uniform_policy":
            sources[category] = (context.uniform_policy_path,) if context.uniform_policy_path else ()
        else:
            sources[category] = _manifest_sources(context.source_dir, category)
    return sources


def resolve_ordered_sources(context: FiscalRunContext) -> tuple[dict[str, object], ...]:
    """Return the ordered annual manifest as immutable run provenance."""
    entries = read_source_manifest(context.source_dir, include_missing=True)
    result: list[dict[str, object]] = []
    for entry in entries:
        path = str(entry.get("_path", ""))
        result.append({
            "category": str(entry.get("category", "")),
            "order": int(str(entry.get("order", "9999")) or 9999),
            "path": path,
            "filename": str(entry.get("filename", "")),
            "fiscal_year": detect_fiscal_year(path) if path else None,
            "checksum": sha256_file(path) if path and Path(path).is_file() else None,
            "invalid_path": bool(entry.get("_invalid_path")),
        })
    return tuple(sorted(result, key=lambda row: (int(row["order"]), str(row["filename"]).lower())))


@lru_cache(maxsize=128)
def _workbook_sheet_names_cached(path: str, _mtime_ns: int, _size: int) -> tuple[str, ...]:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        return tuple(str(name) for name in workbook.sheetnames)
    finally:
        workbook.close()


def _workbook_sheet_names(path: str) -> tuple[str, ...]:
    return _workbook_sheet_names_cached(*_file_cache_key(path))


def _allocation_has_exact_sheet(path: str, fiscal_year: int) -> bool:
    try:
        names = _workbook_sheet_names(path)
    except Exception:
        return False
    return any(f"FY{fiscal_year}" in name.upper() for name in names)


def _workbook_has_fiscal_sheet(path: str, fiscal_year: int) -> bool:
    """Require an explicit FY marker in a workbook that is yearly by design."""
    try:
        names = _workbook_sheet_names(path)
    except Exception:
        return False
    expected = f"FY{int(fiscal_year)}"
    return any(expected in name.upper().replace(" ", "") for name in names)


def _matching_fiscal_sheet(path: str, fiscal_year: int) -> str | None:
    """Return the FY-labelled sheet used as evidence, without guessing."""
    try:
        names = _workbook_sheet_names(path)
    except Exception:
        return None
    expected = f"FY{int(fiscal_year)}"
    for name in names:
        if expected in name.upper().replace(" ", ""):
            return name
    return None


def _workbook_period_coverage(path: str, fiscal_year: int) -> tuple[str, ...]:
    """Read explicit YYYYMM headings from a bounded workbook area for audit."""
    candidate = Path(path)
    if candidate.suffix.lower() not in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        return ()
    values: set[str] = set()
    expected = set(fiscal_periods(fiscal_year))
    try:
        workbook = openpyxl.load_workbook(candidate, read_only=True, data_only=True)
    except Exception:
        return ()
    try:
        for sheet in workbook.worksheets:
            for row in sheet.iter_rows(min_row=1, max_row=min(sheet.max_row, 30), max_col=min(sheet.max_column, 80), values_only=True):
                for value in row:
                    for match in _PERIOD_PATTERN.finditer(str(value or "")):
                        period = f"{match.group(1)}{match.group(2)}"
                        if period in expected:
                            values.add(period)
    finally:
        workbook.close()
    return tuple(period for period in fiscal_periods(fiscal_year) if period in values)


def _filename_period_coverage(path: str, fiscal_year: int) -> tuple[str, ...]:
    """Read a system-source month range from its filename without hardcoding FY."""
    text = Path(path).name
    periods = {f"{match.group(1)}{match.group(2)}" for match in _PERIOD_PATTERN.finditer(text)}
    calendar_months = [
        (int(match.group(2)), _MONTH_NAMES[match.group(1).lower()])
        for match in _MONTH_YEAR_PATTERN.finditer(text)
    ]
    if len(calendar_months) >= 2:
        start_year, start_month = calendar_months[0]
        end_year, end_month = calendar_months[-1]
        cursor_year, cursor_month = start_year, start_month
        while (cursor_year, cursor_month) <= (end_year, end_month):
            periods.add(f"{cursor_year}{cursor_month:02d}")
            cursor_year, cursor_month = (
                (cursor_year + 1, 1) if cursor_month == 12 else (cursor_year, cursor_month + 1)
            )
    expected = set(fiscal_periods(fiscal_year))
    return tuple(period for period in fiscal_periods(fiscal_year) if period in periods and period in expected)


def _preflight_headcount_coverage(context: FiscalRunContext) -> tuple[tuple[str, ...], str | None]:
    """Validate the selected FY's staffing files without writing a run DB."""
    try:
        from src.services.headcount_source_importer import scan_headcount_time_sources
        results = scan_headcount_time_sources(context.headcount_source_dir, context.fiscal_year)
    except Exception as exc:
        return (), f"Không đọc được nguồn nhân sự/thời gian: {exc}"
    valid = [result for result in results if getattr(result, "status", "") == "valid"]
    if not valid:
        return (), "Không có file nhân sự/thời gian đúng cấu trúc và đúng FY trong thư mục đã chọn."
    expected = tuple(fiscal_periods(context.fiscal_year))
    missing_files = []
    for result in valid:
        covered = {str(row.get("period", "")) for row in getattr(result, "rows", ())}
        if not set(expected).issubset(covered):
            missing_files.append(Path(str(getattr(result, "path", ""))).name)
    if missing_files:
        return expected, "Nguồn nhân sự thiếu một hoặc nhiều tháng FY: " + ", ".join(missing_files[:8])
    return expected, None


def _validate_manual_input_store(context: FiscalRunContext) -> str | None:
    """Reject a future-FY manual store that is unscoped or contains another FY."""
    if context.fiscal_year == 2027:
        return None  # handled by the explicit one-time FY2027 migration
    store = Path(context.manual_input_store or "")
    if not store:
        return "Chưa xác định được kho dữ liệu nhập tay theo năm."
    try:
        store.resolve().relative_to(Path(context.headcount_source_dir).resolve())
    except ValueError:
        return "Kho dữ liệu nhập tay phải nằm trong raw/FY của năm đang chạy."
    if not store.exists():
        return None
    import sqlite3
    try:
        conn = sqlite3.connect(store)
        try:
            for table in (
                "fact_manual_headcount_time_override",
                "fact_manual_headcount_baseline_override",
                "fact_bus_headcount_drivers",
            ):
                exists = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
                ).fetchone()
                if not exists:
                    continue
                columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
                if "fiscal_year" not in columns:
                    return f"Kho nhập tay thiếu trường fiscal_year ở bảng {table}."
                foreign = conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE fiscal_year<>?", (context.fiscal_year,)
                ).fetchone()[0]
                if foreign:
                    return f"Kho nhập tay có {foreign} dòng {table} không thuộc FY{context.fiscal_year}."
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return f"Không đọc được kho dữ liệu nhập tay: {exc}"
    return None


def _preflight_checks(
    context: FiscalRunContext,
    sources: dict[str, tuple[str, ...]],
    issues: list[SourceIssue],
) -> tuple[SourceCheck, ...]:
    """Build a complete source table; failures are never hidden by JSON only."""
    candidates: list[tuple[str, str]] = [
        ("template", context.template_path),
        ("headcount", context.headcount_source_dir),
        ("manual_inputs", str(context.manual_input_store or "")),
        ("exchange_rate", context.exchange_rate_source),
    ]
    for category in REQUIRED_SOURCE_CATEGORIES:
        paths = sources.get(category, ())
        if paths:
            candidates.extend((category, str(path)) for path in paths)
        else:
            candidates.append((category, ""))
    if any(issue.category == "form_uniform_master" for issue in issues):
        candidates.append(("form_uniform_master", context.uniform_policy_path or context.template_path))
    checks: list[SourceCheck] = []
    for category, path in candidates:
        is_file = bool(path) and Path(path).is_file()
        evidence = inspect_fiscal_year_evidence(path) if is_file else FiscalYearEvidence(path)
        related = [
            issue for issue in issues
            if issue.category == category and (not issue.path or issue.path == path or path in issue.path)
        ]
        issue = related[0] if related else None
        checks.append(SourceCheck(
            category=category,
            selected_path=path,
            detected_fiscal_year=evidence.resolved_fiscal_year,
            expected_fiscal_year=context.fiscal_year,
            status="FAILED" if issue else "OK",
            checksum=sha256_file(path) if is_file else None,
            sheet=(
                "原価センタ" if category == "uniform_policy" and is_file else
                _matching_fiscal_sheet(path, context.fiscal_year) if is_file else None
            ),
            period_coverage=(
                issue.period_coverage if issue and issue.period_coverage else
                _filename_period_coverage(path, context.fiscal_year) if category == "it_simulation" and is_file else
                _workbook_period_coverage(path, context.fiscal_year) if is_file else ()
            ),
            reason=(
                issue.reason if issue else
                f"Tỷ giá {context.exchange_rate:,.6g} từ {context.exchange_rate_source}."
                if category == "exchange_rate" else
                "Đã xác nhận nguồn phù hợp với lần chạy."
            ),
            required_action=issue.action if issue else "",
        ))
    return tuple(checks)


def _template_looks_valid(path: str) -> bool:
    candidate = Path(path)
    if candidate.name.lower() == "form_old.xlsx" or not candidate.is_file():
        return False
    try:
        workbook = openpyxl.load_workbook(candidate, read_only=True, data_only=True)
    except Exception:
        return False
    try:
        return any("内訳" in name or "採算" in name for name in workbook.sheetnames)
    finally:
        workbook.close()


def _validate_form_master_and_uniform(context: FiscalRunContext) -> str | None:
    """Use production readers against an in-memory DB before calculation starts."""
    if not Path(context.template_path).is_file() or not context.uniform_policy_path:
        return None
    import sqlite3
    from src.db.loader import load_accounts, load_cost_centers, load_uniform_entitlements
    from src.db.schema import create_schema

    conn = sqlite3.connect(":memory:")
    try:
        create_schema(conn)
        cc_count = load_cost_centers(conn, context.template_path)
        account_count = load_accounts(conn, context.template_path)
        if cc_count <= 0 or account_count <= 0:
            return "FORM không đọc được danh mục phòng ban hoặc tài khoản."
        load_uniform_entitlements(
            conn,
            context.uniform_policy_path,
            fiscal_year=context.fiscal_year,
        )
    except Exception as exc:
        return str(exc)
    finally:
        conn.close()
    return None


def preflight_fiscal_run(context: FiscalRunContext) -> RunPreflightReport:
    """Validate annual isolation without writing to calculation or output storage."""
    issues: list[SourceIssue] = []
    sources = resolve_annual_sources(context)
    ordered = resolve_ordered_sources(context)
    for entry in ordered:
        if entry["invalid_path"]:
            issues.append(SourceIssue(
                str(entry["category"]), str(entry["filename"]), None,
                "Đường dẫn manifest đi ra ngoài thư mục nguồn của năm", "Sửa filename trong manifest; không dùng ../ hoặc đường dẫn tuyệt đối."
            ))

    if not _template_looks_valid(context.template_path):
        issues.append(SourceIssue("template", context.template_path, detect_fiscal_year(context.template_path), "FORM không tồn tại hoặc không đúng cấu trúc", "Chọn FORM mới nhất của FY đã chọn."))
    if not Path(context.source_dir).is_dir():
        issues.append(SourceIssue("source_dir", context.source_dir, None, "Thư mục nguồn chi phí không tồn tại", f"Tạo hoặc chọn docs/MP{context.fiscal_year}."))
    if not Path(context.headcount_source_dir).is_dir():
        issues.append(SourceIssue("headcount", context.headcount_source_dir, None, "Thư mục nguồn nhân sự không tồn tại", f"Tạo hoặc chọn raw/FY{context.fiscal_year}."))
    elif not _has_headcount_workbook(Path(context.headcount_source_dir)):
        issues.append(SourceIssue("headcount", context.headcount_source_dir, None, "Không có file nguồn nhân sự/thời gian", "Bổ sung đủ nguồn nhân sự có tháng 3 mốc và 12 tháng FY."))
    elif context.fiscal_year >= 2028:
        coverage, coverage_error = _preflight_headcount_coverage(context)
        if coverage_error:
            issues.append(SourceIssue(
                "headcount", context.headcount_source_dir, context.fiscal_year,
                coverage_error,
                "Bổ sung đủ 12 tháng nhân sự/thời gian theo đúng mẫu FY; tháng 3 mốc phải được nhập tay có truy vết nếu không có trong file.",
                period_coverage=coverage,
            ))
    if context.exchange_rate <= 0 or not context.exchange_rate_source:
        issues.append(SourceIssue(
            "exchange_rate", "", None,
            "Tỷ giá không hợp lệ hoặc chưa có nguồn truy vết.",
            "Nhập tỷ giá dương và nêu rõ nguồn đã được duyệt (ví dụ FORM!B2).",
        ))
    manual_store_error = _validate_manual_input_store(context)
    if manual_store_error:
        issues.append(SourceIssue(
            "manual_inputs", str(context.manual_input_store or ""), context.fiscal_year,
            manual_store_error,
            f"Dùng kho raw/FY{context.fiscal_year}/manual_inputs.db với từng dòng mang fiscal_year={context.fiscal_year}.",
        ))

    manifest_present = any(
        (Path(context.source_dir) / name).is_file()
        for name in ("source_file_order.csv", "source_file_order.xlsx")
    )
    strict_categories = context.fiscal_year != 2027 or manifest_present
    for category in REQUIRED_SOURCE_CATEGORIES:
        paths = sources.get(category, ())
        if not paths:
            if strict_categories:
                issues.append(SourceIssue(category, "", None, "Không tìm thấy nguồn bắt buộc", "Bổ sung đúng file năm đã chọn vào manifest hoặc thư mục nguồn."))
            continue
        if category != "it_simulation" and len(paths) != 1:
            issues.append(SourceIssue(category, "; ".join(paths), None, "Có nhiều nguồn cùng loại", "Chỉ giữ một nguồn hoặc chọn rõ trong manifest."))
        if category == "it_simulation" and len(paths) != 3:
            issues.append(SourceIssue(category, "; ".join(paths), None, "Phải có đúng ba file hệ thống", "Bổ sung đủ nhóm tháng 4–6, 7–12 và 1–3."))
        for path in paths:
            evidence = inspect_fiscal_year_evidence(path)
            # Fixed-asset snapshot workbooks can legitimately use a prior
            # calendar snapshot label instead of an annual FY marker.
            reason = validate_fiscal_year_evidence(
                evidence,
                context.fiscal_year,
                required=(
                    category != "fixed_assets"
                    and not (category == "uniform_policy" and context.fiscal_year == 2027)
                ),
            )
            if reason:
                issues.append(SourceIssue(
                    category,
                    path,
                    evidence.resolved_fiscal_year,
                    reason,
                    f"Thay bằng nguồn xác nhận đúng FY{context.fiscal_year}.",
                ))

    system_periods = {
        period
        for path in sources.get("it_simulation", ())
        for period in _filename_period_coverage(path, context.fiscal_year)
    }
    expected_system_periods = set(fiscal_periods(context.fiscal_year))
    if len(sources.get("it_simulation", ())) == 3 and system_periods != expected_system_periods:
        missing = ", ".join(period for period in fiscal_periods(context.fiscal_year) if period not in system_periods)
        issues.append(SourceIssue(
            "it_simulation", "; ".join(sources.get("it_simulation", ()),), context.fiscal_year,
            f"Ba file hệ thống không bao phủ đủ 12 kỳ của FY; còn thiếu: {missing or 'không xác định được kỳ từ tên file'}.",
            "Chọn đúng ba file hệ thống bao phủ lần lượt tháng 4–6, 7–12 và 1–3 của FY đang chạy.",
            period_coverage=tuple(period for period in fiscal_periods(context.fiscal_year) if period in system_periods),
        ))

    fixed_asset_paths = sources.get("fixed_assets", ())
    if len(fixed_asset_paths) == 1:
        evidence = inspect_fiscal_year_evidence(fixed_asset_paths[0])
        if evidence.inspection_error:
            issues.append(SourceIssue(
                "fixed_assets", fixed_asset_paths[0], evidence.resolved_fiscal_year,
                f"Không đọc được snapshot tài sản cố định: {evidence.inspection_error}",
                "Cung cấp file snapshot tài sản cố định mở được và chứa dữ liệu cần tính cho FY đang chạy.",
            ))

    allocation_paths = sources.get("allocation_rules", ())
    if len(allocation_paths) == 1 and not _allocation_has_exact_sheet(allocation_paths[0], context.fiscal_year):
        issues.append(SourceIssue("allocation_rules", allocation_paths[0], detect_fiscal_year(allocation_paths[0]), "Không có sheet quy tắc đúng FY", f"Bổ sung sheet FY{context.fiscal_year}."))

    for category in ("ga", "birthday", "nnn_paperwork"):
        paths = sources.get(category, ())
        if len(paths) == 1 and not _workbook_has_fiscal_sheet(paths[0], context.fiscal_year):
            issues.append(SourceIssue(
                category, paths[0], detect_fiscal_year(paths[0]),
                "Không có sheet xác nhận đúng năm tài chính", f"Bổ sung sheet FY{context.fiscal_year}; không dùng sheet của năm khác."
            ))

    uniform_paths = sources.get("uniform_policy", ())
    if len(uniform_paths) == 1:
        try:
            if not _is_uniform_policy(Path(uniform_paths[0])):
                raise ValueError("thiếu trang 原価センタ hoặc cột F:U")
        except Exception as exc:
            issues.append(SourceIssue("uniform_policy", uniform_paths[0], detect_fiscal_year(uniform_paths[0]), str(exc), "Dùng bảng dấu chọn đồng phục/cốc xếp hợp lệ."))

    master_uniform_error = _validate_form_master_and_uniform(context)
    if master_uniform_error:
        issues.append(SourceIssue(
            "form_uniform_master",
            context.uniform_policy_path or context.template_path,
            detect_fiscal_year(context.uniform_policy_path) if context.uniform_policy_path else None,
            master_uniform_error,
            "Sửa danh mục phòng/tài khoản trong FORM hoặc danh sách phòng của bảng đồng phục để hai nguồn khớp nhau.",
        ))

    return RunPreflightReport(
        context.fiscal_year,
        tuple(issues),
        sources,
        _preflight_checks(context, sources, issues),
    )


def sha256_file(path: str | os.PathLike[str]) -> str:
    digest = sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
