"""Các tiện ích kỳ năm tài chính cho MP2027.

Năm tài chính của công ty bắt đầu từ tháng 4 của năm dương lịch trước và kết
thúc vào tháng 3 của năm tài chính. Đây là nguồn quy tắc duy nhất cho nhãn nhân
sự trên giao diện, kiểm tra CSV/cơ sở dữ liệu và danh sách kỳ.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable


def _validate_fiscal_year(fiscal_year: int) -> int:
    try:
        year = int(fiscal_year)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Năm tài chính phải là số nguyên. "
            "Nguyên nhân: Giá trị năm tài chính nhập vào không thể chuyển đổi thành số nguyên. "
            "Cách xử lý: Nhập năm tài chính gồm 4 chữ số (ví dụ: 2027)."
        ) from exc
    if year < 1900:
        raise ValueError(
            "Năm tài chính phải lớn hơn hoặc bằng 1900. "
            "Nguyên nhân: Năm tài chính nhỏ hơn 1900 không hợp lệ trong hệ thống. "
            "Cách xử lý: Nhập năm tài chính từ 1900 trở lên."
        )
    return year


FISCAL_START_MONTH = 4


def fiscal_period_for_month(fiscal_year: int, month: int) -> str:
    """Return YYYYMM period for a month in MP2027 fiscal year.

    MP2027 company fiscal year is April through March.
    """
    year = _validate_fiscal_year(fiscal_year)
    start = FISCAL_START_MONTH
    try:
        calendar_month = int(month)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Tháng phải là số nguyên. "
            "Nguyên nhân: Giá trị tháng cung cấp không phải là số nguyên. "
            "Cách xử lý: Nhập tháng từ 1 đến 12."
        ) from exc
    if calendar_month < 1 or calendar_month > 12:
        raise ValueError(
            "Tháng phải nằm trong khoảng từ 1 đến 12. "
            "Nguyên nhân: Giá trị tháng vượt ngoài khoảng 1 đến 12. "
            "Cách xử lý: Nhập tháng hợp lệ trong khoảng 1-12."
        )
    calendar_year = year - 1 if calendar_month >= start else year
    return f"{calendar_year}{calendar_month:02d}"


def fiscal_month_order() -> list[int]:
    """Return MP2027 company fiscal month order: April through March."""
    start = FISCAL_START_MONTH
    return list(range(start, 13)) + list(range(1, start))


def fiscal_periods(fiscal_year: int) -> list[str]:
    """Return the 12 MP2027 fiscal periods in April-through-March order."""
    return [fiscal_period_for_month(fiscal_year, month) for month in fiscal_month_order()]


def fiscal_baseline_period(fiscal_year: int) -> str:
    """Return previous March baseline period for MP2027 fiscal year."""
    year = _validate_fiscal_year(fiscal_year)
    baseline_month = FISCAL_START_MONTH - 1
    baseline_year = year - 1
    return f"{baseline_year}{baseline_month:02d}"


def fiscal_month_labels(fiscal_year: int) -> list[tuple[int, str, str]]:
    """Return tuples of (month, period, canonical Vietnamese GUI label)."""
    labels = []
    for month in fiscal_month_order():
        period = fiscal_period_for_month(fiscal_year, month)
        labels.append((month, period, f"Tháng {month}"))
    return labels


_SYSTEM_PERIOD_PATTERN = re.compile(r"(?<!\d)(20\d{2})(0[1-9]|1[0-2])(?!\d)")
_SYSTEM_MONTH_YEAR_PATTERN = re.compile(
    r"(?i)(?<![A-Za-z])"
    r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"[.\s_-]*(20\d{2})\b"
)
_SYSTEM_MONTH_NAMES = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12,
}


@dataclass(frozen=True)
class SystemSourcePeriodAssignment:
    """One System Cost source and the exact FY periods supplied by it."""

    path: str
    periods: tuple[str, ...]


class SystemSourcePeriodError(ValueError):
    """Structured fail-closed error for invalid System Cost period coverage."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        paths: Iterable[str | Path] = (),
        periods: Iterable[str] = (),
    ) -> None:
        super().__init__(message)
        self.code = code
        self.paths = tuple(str(path) for path in paths)
        self.periods = tuple(str(period) for period in periods)


def _system_period_key(period: str) -> tuple[int, int]:
    return int(period[:4]), int(period[4:])


def _expand_system_period_range(start: str, end: str, *, path: str) -> tuple[str, ...]:
    if _system_period_key(start) > _system_period_key(end):
        raise SystemSourcePeriodError(
            "SYSTEM_PERIOD_REVERSED",
            f"Khoảng kỳ trong tên file bị đảo ngược: {Path(path).name} ({start} -> {end}). "
            f"Nguyên nhân: Mốc kỳ bắt đầu ({start}) lớn hơn mốc kỳ kết thúc ({end}). "
            "Cách xử lý: Đổi tên file sao cho kỳ bắt đầu đứng trước kỳ kết thúc (ví dụ: 202604 ~ 202609).",
            paths=(path,),
            periods=(start, end),
        )
    periods: list[str] = []
    year, month = _system_period_key(start)
    end_key = _system_period_key(end)
    while (year, month) <= end_key:
        periods.append(f"{year}{month:02d}")
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return tuple(periods)


def system_source_periods_for_file(path: str | Path, fiscal_year: int) -> tuple[str, ...]:
    """Parse one filename into one month or an inclusive month range within FY."""
    path_text = str(path)
    filename = Path(path_text).name
    explicit = [
        f"{match.group(1)}{match.group(2)}"
        for match in _SYSTEM_PERIOD_PATTERN.finditer(filename)
    ]
    named = [
        f"{int(match.group(2))}{_SYSTEM_MONTH_NAMES[match.group(1).lower()]:02d}"
        for match in _SYSTEM_MONTH_YEAR_PATTERN.finditer(filename)
    ]
    markers: list[str] = []
    for period in (*explicit, *named):
        if period not in markers:
            markers.append(period)
    if not markers:
        raise SystemSourcePeriodError(
            "SYSTEM_PERIOD_UNRECOGNIZED",
            f"Không xác định được kỳ từ tên file System Cost: {filename}. "
            "Nguyên nhân: Tên file không chứa định dạng kỳ YYYYMM (ví dụ 202604) hoặc tên tháng tiếng Anh kèm năm. "
            f"Cách xử lý: Đổi tên file System Cost có chứa mốc kỳ hợp lệ trong năm tài chính FY{fiscal_year}.",
            paths=(path_text,),
        )
    if len(markers) > 2:
        raise SystemSourcePeriodError(
            "SYSTEM_PERIOD_AMBIGUOUS",
            f"Tên file System Cost chứa nhiều hơn hai mốc kỳ: {filename} ({', '.join(markers)}). "
            "Nguyên nhân: Tên file chứa quá nhiều mốc thời gian gây nhầm lẫn. "
            "Cách xử lý: Đổi tên file chỉ chứa 1 mốc kỳ đơn hoặc 2 mốc kỳ giới hạn khoảng thời gian.",
            paths=(path_text,),
            periods=markers,
        )

    covered = (
        (markers[0],)
        if len(markers) == 1
        else _expand_system_period_range(markers[0], markers[1], path=path_text)
    )
    expected = tuple(fiscal_periods(fiscal_year))
    outside = tuple(period for period in covered if period not in expected)
    if outside:
        raise SystemSourcePeriodError(
            "SYSTEM_PERIOD_OUTSIDE_FY",
            f"Tên file {filename} chứa kỳ ngoài FY{int(fiscal_year)}: {', '.join(outside)}. "
            f"Nguyên nhân: Mốc kỳ trong tên file không thuộc 12 kỳ của năm tài chính FY{int(fiscal_year)}. "
            f"Cách xử lý: Kiểm tra lại tệp System Cost đúng cho năm tài chính FY{int(fiscal_year)}.",
            paths=(path_text,),
            periods=outside,
        )
    return tuple(period for period in expected if period in covered)


def map_system_source_periods(
    paths: Iterable[str | Path],
    fiscal_year: int,
    *,
    require_complete: bool = True,
) -> tuple[SystemSourcePeriodAssignment, ...]:
    """Return deterministic file-to-period assignments and reject overlap/gaps."""
    expected = tuple(fiscal_periods(fiscal_year))
    order = {period: index for index, period in enumerate(expected)}
    assignments: list[SystemSourcePeriodAssignment] = []
    owners: dict[str, str] = {}

    for raw_path in paths:
        path = str(raw_path)
        covered = system_source_periods_for_file(path, fiscal_year)
        duplicates = tuple(period for period in covered if period in owners)
        if duplicates:
            conflicting = tuple(dict.fromkeys((*(owners[period] for period in duplicates), path)))
            raise SystemSourcePeriodError(
                "SYSTEM_PERIOD_OVERLAP",
                f"Các file System Cost bị trùng kỳ: {', '.join(duplicates)}. "
                "Nguyên nhân: Có nhiều hơn một tệp nguồn System Cost cùng chứa dữ liệu của một kỳ tài chính. "
                "Cách xử lý: Kiểm tra và loại bỏ các tệp System Cost trùng lặp.",
                paths=conflicting,
                periods=duplicates,
            )
        for period in covered:
            owners[period] = path
        assignments.append(SystemSourcePeriodAssignment(path, covered))

    if require_complete:
        missing = tuple(period for period in expected if period not in owners)
        if missing:
            raise SystemSourcePeriodError(
                "SYSTEM_PERIOD_MISSING",
                f"Nguồn System Cost chưa bao phủ đủ 12 kỳ; còn thiếu: {', '.join(missing)}. "
                "Nguyên nhân: Danh sách các tệp System Cost không đủ 12 tháng từ tháng 4 đến tháng 3. "
                f"Cách xử lý: Bổ sung các tệp System Cost cho các kỳ còn thiếu: {', '.join(missing)}.",
                paths=(assignment.path for assignment in assignments),
                periods=missing,
            )

    return tuple(
        sorted(assignments, key=lambda assignment: order[assignment.periods[0]])
    )
