"""
MP2027 Manager - Excel Helper Utilities (Refactored V4.5.0)
Universal helper functions for reading financial workbooks.
"""
import pandas as pd
import openpyxl
import math
from src.utils.fiscal_periods import fiscal_month_order, fiscal_periods
from datetime import datetime
from typing import Optional, Any
from pathlib import Path

# Constants for Hub Sheet Identification
HUB_SHEET_CANDIDATES = ('内訳ﾘｽﾄ(4～3月)', '内訳リスト(4～3月)')

def get_month_mapping(fiscal_year: int = 2027) -> dict:
    """Returns a mapping of month Index (0-11) to Period String (YYYYMM)."""
    return {index: period for index, period in enumerate(fiscal_periods(fiscal_year))}

def get_fy_months(fiscal_year: int = 2027) -> list:
    """Returns a list of 12 YYYYMM strings for the given fiscal year."""
    return fiscal_periods(fiscal_year)

def get_fy_month_labels(fiscal_year: int = 2027) -> list:
    """Returns a list of 12 numeric month labels (4, 5, ..., 12, 1, 2, 3)."""
    return fiscal_month_order()

def normalize_period(value: Any) -> Optional[str]:
    """Universal period normalizer to YYYYMM format."""
    if pd.isna(value) or value in ('', None): return None
    if isinstance(value, datetime): return value.strftime('%Y%m')
    if hasattr(value, 'year') and hasattr(value, 'month'):
        return f"{int(value.year)}{int(value.month):02d}"
    s = str(value).strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y/%m/%d', '%m/%Y', '%m-%Y', '%Y%m'):
        try: return datetime.strptime(s, fmt).strftime('%Y%m')
        except ValueError: continue
    return None

def find_hub_sheet_name(workbook: openpyxl.Workbook) -> str:
    """Find the hub sheet name in FORM.xlsx dynamically."""
    for candidate in HUB_SHEET_CANDIDATES:
        if candidate in workbook.sheetnames: return candidate
    for sheet_name in workbook.sheetnames:
        if '内訳' in sheet_name and '4' in sheet_name and '3' in sheet_name: return sheet_name
    raise ValueError('Hub sheet 内訳ﾘｽﾄ(4～3月) not found in FORM.xlsx')

def validate_exchange_rate(value: Any) -> float:
    """Return a safe USD/VND rate or raise instead of silently substituting one."""
    if isinstance(value, str):
        value = value.strip().replace(",", "")
    try:
        rate = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Tỷ giá USD/VND phải là một số hợp lệ.") from exc
    if not math.isfinite(rate) or rate <= 0 or rate > 1_000_000:
        raise ValueError("Tỷ giá USD/VND phải lớn hơn 0 và không vượt quá 1,000,000.")
    return rate


def read_exchange_rate_from_form(form_path: str) -> float:
    """Read the USD/VND rate from the selected FORM hub-sheet B2 cell."""
    path = Path(form_path)
    if not path.exists(): raise FileNotFoundError(f'FORM.xlsx not found at {path}')
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        sheet_name = find_hub_sheet_name(wb)
        return validate_exchange_rate(wb[sheet_name]['B2'].value)
    finally: wb.close()


def write_exchange_rate_to_form(form_path: str, exchange_rate: Any) -> float:
    """Set the effective rate in a copied output FORM without mutating its template."""
    rate = validate_exchange_rate(exchange_rate)
    path = Path(form_path)
    if not path.exists():
        raise FileNotFoundError(f'FORM.xlsx not found at {path}')
    wb = openpyxl.load_workbook(path)
    try:
        sheet_name = find_hub_sheet_name(wb)
        wb[sheet_name]['B2'].value = rate
        wb.save(path)
    finally:
        wb.close()
    return rate

import re

CC_CODE_PATTERNS = (
    r"\b\d{4}[A-Za-z]\d{5,}\b",
    r"\b\d{4,10}\b",
)


def normalize_cc_code(val: Any) -> Optional[str]:
    """Normalize cost center code from raw Excel/csv values."""
    if pd.isna(val) or val is None:
        return None

    if isinstance(val, (int, float)):
        try:
            number = int(float(val))
            if number >= 1000:
                return str(number)
        except Exception:
            pass

    s = str(val).strip()
    if not s:
        return None

    compact = s.replace(" ", "")
    for pattern in CC_CODE_PATTERNS:
        direct_match = re.fullmatch(pattern, compact)
        if direct_match:
            return direct_match.group(0).upper()

    for pattern in CC_CODE_PATTERNS:
        match = re.search(pattern, s)
        if match:
            return match.group(0).upper()
    return None


def extract_cc_code(val: Any) -> Optional[str]:
    """Backward-compatible alias for normalized cost center extraction."""
    return normalize_cc_code(val)

def safe_float(val: Any) -> float:
    """Convert a value to float, returning 0.0 for invalid values."""
    if pd.isna(val) or val is None: return 0.0
    try: return float(val)
    except (ValueError, TypeError): return 0.0

def normalize_text(value: str) -> str:
    """Normalize text for consistent mapping."""
    text = str(value or '').replace('\n', ' ').replace('\u3000', ' ')
    return ' '.join(text.split()).strip().lower()

def item_key(value: str) -> str:
    """Generate a lookup key from item description."""
    return normalize_text(str(value or '').split('\n')[0].strip())
