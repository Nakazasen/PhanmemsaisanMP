"""
MP2027 Manager - Excel Helper Utilities
Common functions for reading Excel files with merged cells, date parsing, etc.
"""
import pandas as pd
from datetime import datetime
from typing import Optional



def get_month_mapping(fiscal_year: int = 2027) -> dict:
    """
    Returns a mapping of month Index (0-11) to Period String (YYYYMM).
    FY starts in April of (fiscal_year - 1) and ends in March of fiscal_year.
    Example for FY2027: Index 0 (Apr) -> '202604', ..., Index 11 (Mar) -> '202703'
    """
    start_year = fiscal_year - 1
    mapping = {}
    
    # Apr (0) to Dec (8)
    for i in range(4, 13):
        month_idx = i - 4
        mapping[month_idx] = f"{start_year}{i:02d}"
        
    # Jan (9) to Mar (11)
    for i in range(1, 4):
        month_idx = i + 8
        mapping[month_idx] = f"{fiscal_year}{i:02d}"
        
    return mapping


def get_fy_months(fiscal_year: int = 2027) -> list:
    """Returns a list of 12 YYYYMM strings for the given fiscal year."""
    mapping = get_month_mapping(fiscal_year)
    return [mapping[i] for i in range(12)]


def get_fy_month_labels(fiscal_year: int = 2027) -> list:
    """Returns a list of 12 numeric month labels (4, 5, ..., 12, 1, 2, 3)."""
    # Fiscal year start month is usually April (4)
    months = []
    for i in range(4, 13):
        months.append(i)
    for i in range(1, 4):
        months.append(i)
    return months


def date_col_to_period(val) -> Optional[str]:
    """Convert a column header date value to YYYYMM period string."""
    if pd.isna(val) or val == '':
        return None
    if isinstance(val, datetime):
        return val.strftime('%Y%m')
    s = str(val).strip()
    # Try to parse "2026-04-01 00:00:00" format
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y/%m/%d'):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime('%Y%m')
        except ValueError:
            continue
    return None


def find_data_start_row(df: pd.DataFrame, cc_col: int = 0) -> int:
    """Find the first data row by looking for a cost center code (numeric)."""
    for i in range(len(df)):
        val = df.iloc[i, cc_col]
        if pd.isna(val):
            continue
        try:
            code = int(float(val))
            if code > 1000000:  # CC codes are 10-digit numbers
                return i
        except (ValueError, TypeError):
            continue
    return 0


def extract_cc_code(val) -> Optional[int]:
    """Extract cost center code from a cell value."""
    if pd.isna(val):
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def safe_float(val) -> float:
    """Convert a value to float, returning 0.0 for invalid values."""
    if pd.isna(val):
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0
