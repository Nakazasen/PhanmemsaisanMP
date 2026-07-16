"""Explicit FY2027-only compatibility metadata.

New fiscal-year runs receive their source order from ``FiscalRunContext`` and
must never import this module.  The names remain solely so historical FY2027
workbooks and focused writer tests can be opened without changing the accepted
FY2027 layout.
"""

FY2027_COMPAT_SOURCE_FILE_ORDER = (
    "施設課　MPFY2027.xlsx",
    "固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx",
    "システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls",
    "総務課 FY2027 MP 振替予定.xlsx",
    "Sinh nhật MP FY2027.xlsx",
    "FY2027配賦額一覧 (2025.12.29).xlsx",
    "Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx",
)
