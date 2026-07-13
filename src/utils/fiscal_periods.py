"""Fiscal-year period helpers for MP2027.

The company fiscal year starts in April of the prior calendar year and
ends in March of the fiscal year. These helpers are the single source of
truth for manual headcount GUI labels, CSV/DB validation, and period lists.
"""

from __future__ import annotations


def _validate_fiscal_year(fiscal_year: int) -> int:
    try:
        year = int(fiscal_year)
    except (TypeError, ValueError) as exc:
        raise ValueError("fiscal_year must be an integer") from exc
    if year < 1900:
        raise ValueError("fiscal_year must be >= 1900")
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
        raise ValueError("month must be an integer") from exc
    if calendar_month < 1 or calendar_month > 12:
        raise ValueError("month must be in 1..12")
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
