"""Canonical field-level source policy for monthly headcount."""
from __future__ import annotations

from dataclasses import dataclass
import sqlite3

from src.utils.fiscal_periods import fiscal_baseline_period, fiscal_periods


class HeadcountSourceError(ValueError):
    """Raised when canonical staffing data is missing or internally invalid."""


@dataclass(frozen=True)
class CanonicalHeadcount:
    period: str
    cc_code: str
    headcount_expat: float
    headcount_staff: float | None
    headcount_worker: float | None
    headcount_all: float
    staffing_source: str
    split_status: str = "READY"
    headcount_male: float = 0.0
    headcount_female: float = 0.0
    gender_source: str = ""


def _number(row: sqlite3.Row, key: str) -> float:
    return float(row[key] or 0.0)


def load_canonical_headcount(conn: sqlite3.Connection, fiscal_year: int) -> dict[tuple[str, str], CanonicalHeadcount]:
    """Resolve FY staffing from department plans and baseline staffing from manual input."""
    rows = conn.execute(
        """SELECT cc_code,period,headcount_all,headcount_expat,headcount_staff,
                   headcount_worker,headcount_male,headcount_female,source,
                   split_status,headcount_local_total
            FROM fact_monthly_headcount ORDER BY cc_code,period,source"""
    ).fetchall()
    grouped: dict[tuple[str, str], dict[str, sqlite3.Row]] = {}
    for row in rows:
        key = (str(row["cc_code"]).strip(), str(row["period"]).strip())
        grouped.setdefault(key, {})[str(row["source"] or "").strip()] = row

    baseline = fiscal_baseline_period(fiscal_year)
    fy_period_set = set(fiscal_periods(fiscal_year))
    result: dict[tuple[str, str], CanonicalHeadcount] = {}
    for (cc_code, period), by_source in grouped.items():
        if period in fy_period_set:
            staffing = by_source.get("department_plan")
        elif period == baseline:
            staffing = by_source.get("manual")
        else:
            continue
        if staffing is None:
            continue
        expat = _number(staffing, "headcount_expat")
        split_status = str(staffing["split_status"] or "READY")
        split_ready = split_status == "READY"
        staff = _number(staffing, "headcount_staff") if split_ready else None
        worker = _number(staffing, "headcount_worker") if split_ready else None
        if expat < 0 or (split_ready and min(float(staff), float(worker)) < 0):
            raise HeadcountSourceError(f"CC {cc_code}, kỳ {period}: số người không được là số âm.")
        recorded_local = staffing["headcount_local_total"]
        local_total = (
            _number(staffing, "headcount_local_total")
            if recorded_local is not None
            else float(staff or 0.0) + float(worker or 0.0)
        )
        if split_ready:
            derived_local = float(staff) + float(worker)
            if abs(local_total - derived_local) > 0.01:
                raise HeadcountSourceError(
                    f"CC {cc_code}, kỳ {period}: tổng local {local_total:g} không khớp "
                    f"Nhân viên + Công nhân ({float(staff):g} + {float(worker):g} = {derived_local:g})."
                )
        derived_total = expat + local_total
        recorded_total = _number(staffing, "headcount_all")
        if abs(recorded_total - derived_total) > 0.01:
            raise HeadcountSourceError(
                f"CC {cc_code}, kỳ {period}: Tổng người {recorded_total:g} không khớp "
                f"JP + tổng local ({expat:g} + {local_total:g} = {derived_total:g})."
            )
        supplement = by_source.get("manual")
        result[(cc_code, period)] = CanonicalHeadcount(
            period=period, cc_code=cc_code, headcount_expat=expat,
            headcount_staff=staff, headcount_worker=worker, headcount_all=derived_total,
            staffing_source=str(staffing["source"] or ""), split_status=split_status,
            headcount_male=_number(supplement or staffing, "headcount_male"),
            headcount_female=_number(supplement or staffing, "headcount_female"),
            gender_source="manual" if supplement else str(staffing["source"] or ""),
        )
    return result


def require_headcount(cache: dict[tuple[str, str], CanonicalHeadcount], cc_code: object, period: str) -> CanonicalHeadcount:
    key = (str(cc_code).strip(), str(period).strip())
    if key not in cache:
        raise HeadcountSourceError(f"CC {key[0]} thiếu Tổng người kỳ {key[1]} theo đúng nguồn quy định.")
    return cache[key]
