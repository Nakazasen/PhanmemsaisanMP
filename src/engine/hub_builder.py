"""
MP2027 Manager - Hub Builder.

Writes shared-cost data back into the MP detail sheet while preserving the
original FORM layout and formulas.
"""

from __future__ import annotations

from collections import defaultdict
from copy import copy
import os
import shutil
import sqlite3
from typing import Optional
import unicodedata

import openpyxl
from openpyxl.utils import get_column_letter

from src.engine.output_mode import OutputGroupSpec, get_default_output_group_specs
from src.utils import excel_helpers as helpers


VISIBLE_MONTH_START_COL = 6   # F
TOTAL_COL = 18                # R
ACCOUNT_COL = 2               # B
DESCRIPTION_COL = 19          # S
WBS_COL = 20                  # T
LOOKUP_NAME_COL = 3           # C
LOOKUP_GROUP_COL = 4          # D
APPEND_TEMPLATE_ROW = 29
MIN_APPEND_START_ROW = 168
APPEND_START_ROW = MIN_APPEND_START_ROW
MIN_APPEND_LAST_ROW = 1000
TEMPLATE_ACCOUNT_CLEAR_START_ROW = 30
APPEND_LEFT_FILL = "CCFFFF"
APPEND_MONTH_FILL = "CCFFFF"
APPEND_NOTE_FILL = "CCFFFF"
IT_COMPONENT_ORDER = ("vpn", "mail", "r3", "mes", "plm", "qlik_sense", "vps", "ams")
IT_SYSTEM_ACCOUNT_CODES = {5005246282, 6005146628, 6005146542}
IT_SYSTEM_ACCOUNT_BY_COST_TYPE = {
    "製造": 5005246282,
    "一般": 6005146628,
    "販売": 6005146542,
}
IT_SYSTEM_ROW_TEXT_TOKENS = ("system cost", "kdc", "ｋｄｃ", "システム", "社内システム")
MONTHLY_HEADCOUNT_FIXED_ROWS = (46, 48, 49, 51)
FIXED_ALLOCATION_ROW_MATCHERS = {
    57: {
        "tokens": ("kham suc khoe (cho cnv nam)", "kham suc khoe (cho cnv nu)", "health check"),
        "exclude_tokens": ("tuyen dung", "gpld"),
    },
    58: {
        "tokens": ("kham suc khoe khi tuyen dung", "tuyen dung"),
        "exclude_tokens": (),
    },
    59: {
        "tokens": ("sinh nhat", "birthday"),
        "exclude_tokens": (),
    },
    97: {
        "tokens": ("ノート", "note", "notebook"),
        "exclude_tokens": ("g7", "worker", "cong nhan"),
    },
    98: {
        "tokens": ("ノート", "note", "notebook"),
        "exclude_tokens": ("staff", "nhan vien"),
    },
    54: {
        "tokens": ("決起コンパ", "tiệc khuấy động năm tài chính", "phương châm bộ phận", "phuong cham bo phan"),
        "exclude_tokens": (),
    },
    63: {
        "tokens": ("お年玉", "tiền lì xì"),
        "exclude_tokens": (),
    },
    66: {
        "tokens": ("社員旅行 du lịch công ty", "社員旅行", "京セラフェスティバル", "lễ hội kyocera"),
        "exclude_tokens": ("不参加", "gift", "quà tặng", "qua tang"),
    },
    67: {
        "tokens": ("運動会", "đại hội thể thao"),
        "exclude_tokens": (),
    },
    70: {
        "tokens": ("忘年会補助金", "hỗ trợ tiệc tất niên"),
        "exclude_tokens": (),
    },
    71: {
        "tokens": ("月餅", "bánh trung thu"),
        "exclude_tokens": (),
    },
    64: {
        "tokens": ("10年勤続記念コンパ", "tiệc kỷ niệm 10 năm", "tiec ky niem 10 nam"),
        "exclude_tokens": (),
    },
    65: {
        "tokens": ("10年勤続記念品", "quà kỷ niệm", "qua ky niem"),
        "exclude_tokens": (),
    },
    68: {
        "tokens": ("会社設立記念", "sự kiện tri ân", "su kien tri an"),
        "exclude_tokens": (),
    },
    79: {
        "tokens": ("社員証（新入社員用・再発行時、写真含む）", "thẻ từ chấm công + ảnh"),
        "exclude_tokens": (),
    },
    80: {
        "tokens": ("社員証用写真のみ", "ảnh của thẻ từ chấm công"),
        "exclude_tokens": (),
    },
    81: {
        "tokens": ("フィロソフィ手帳1", "フィロソフィ手帳2", "philosophy quyển 1", "philosophy quyển 2"),
        "exclude_tokens": (),
    },
    82: {
        "tokens": ("ポケットカレンダー", "pocket calendar", "lịch bỏ túi"),
        "exclude_tokens": (),
    },
    88: {
        "tokens": ("社員証用ケース", "vỏ thẻ + móc thẻ"),
        "exclude_tokens": (),
    },
    89: {
        "tokens": ("alloc: ペン", "ペン bút"),
        "exclude_tokens": (),
    },
    90: {
        "tokens": ("alloc: ノート", "ノート sổ"),
        "exclude_tokens": (),
    },
}
MANAGED_FIXED_ROWS = tuple(
    sorted(
        set(range(38, 91))
        | set(range(93, 110))
        | set(range(111, 153))
    )
)


class HubBuilder:
    def __init__(self, conn: sqlite3.Connection, fiscal_year: int = 2027):
        self.conn = conn
        self.fiscal_year = fiscal_year
        self.fy_months = helpers.get_fy_months(fiscal_year)
        self.rule_unit_price_by_source = self._load_rule_unit_price_by_source()

    def _output_group_specs(self) -> tuple[OutputGroupSpec, ...]:
        """Return canonical output group specs for future row-placement planning."""
        return get_default_output_group_specs()

    def _normalize_text(self, value: object) -> str:
        text = unicodedata.normalize("NFKD", str(value or ""))
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = text.replace("\n", " ").replace("\u3000", " ").strip().lower()
        return " ".join(text.split())

    def _format_number(self, value: float) -> str:
        number = float(value or 0.0)
        if abs(number - round(number)) < 1e-9:
            return str(int(round(number)))
        return f"{number:.6f}".rstrip("0").rstrip(".")

    def _as_int(self, value: object) -> int | None:
        try:
            if value is None or str(value).strip() == "":
                return None
            return int(float(str(value).strip()))
        except (TypeError, ValueError):
            return None

    def _series_has_output(self, values: dict[str, float]) -> bool:
        return any(abs(float(amount or 0.0)) > 1e-9 for amount in values.values())

    def _formula_series_has_output(
        self,
        terms_by_period: dict[str, list[str]],
        numeric_values: dict[str, float] | None = None,
    ) -> bool:
        if any(terms for terms in terms_by_period.values()):
            return True
        return self._series_has_output(numeric_values or {})

    def _find_it_system_total_row(self, worksheet) -> int:
        candidates: list[tuple[int, int]] = []
        for row_index in range(1, worksheet.max_row + 1):
            account_code = self._as_int(worksheet.cell(row=row_index, column=ACCOUNT_COL).value)
            has_kdc_account = account_code in IT_SYSTEM_ACCOUNT_CODES
            row_text = " ".join(
                self._normalize_text(worksheet.cell(row=row_index, column=column_index).value)
                for column_index in range(1, WBS_COL + 1)
                if worksheet.cell(row=row_index, column=column_index).value is not None
            )
            has_system_text = any(token in row_text for token in IT_SYSTEM_ROW_TEXT_TOKENS)
            if has_kdc_account or has_system_text:
                score = (2 if has_kdc_account else 0) + (3 if has_system_text else 0)
                candidates.append((score, row_index))

        if not candidates:
            raise RuntimeError("Unable to locate System Cost row in FORM template")
        candidates.sort(key=lambda item: (-item[0], item[1]))
        return candidates[0][1]

    def _resolve_it_system_account_code(self, cc_code: int, fact_account_codes: set[int]) -> int | None:
        valid_fact_accounts = fact_account_codes & IT_SYSTEM_ACCOUNT_CODES
        if len(valid_fact_accounts) == 1:
            return next(iter(valid_fact_accounts))

        row = self.conn.execute(
            "SELECT cost_type FROM dim_cost_centers WHERE code = ? LIMIT 1",
            (str(cc_code),),
        ).fetchone()
        if row:
            cost_type = str(row["cost_type"] or "").strip()
            if cost_type in IT_SYSTEM_ACCOUNT_BY_COST_TYPE:
                return IT_SYSTEM_ACCOUNT_BY_COST_TYPE[cost_type]
        return None

    def _load_rule_unit_price_by_source(self) -> dict[str, float]:
        rows = self.conn.execute("SELECT id, unit_price FROM map_allocation_rules").fetchall()
        return {f"alloc_{int(row['id'])}": float(row["unit_price"] or 0.0) for row in rows}

    def _copy_row_style(self, worksheet, source_row: int, target_row: int) -> None:
        worksheet.row_dimensions[target_row].height = worksheet.row_dimensions[source_row].height
        for column_index in range(1, WBS_COL + 1):
            source_cell = worksheet.cell(row=source_row, column=column_index)
            target_cell = worksheet.cell(row=target_row, column=column_index)
            if source_cell.has_style:
                target_cell.font = copy(source_cell.font)
                target_cell.fill = copy(source_cell.fill)
                target_cell.border = copy(source_cell.border)
                target_cell.alignment = copy(source_cell.alignment)
                target_cell.number_format = source_cell.number_format
                target_cell.protection = copy(source_cell.protection)

    def _write_lookup_formulas(self, worksheet, row_index: int) -> None:
        worksheet.cell(
            row=row_index,
            column=LOOKUP_NAME_COL,
            value=(
                f'=IFERROR(IF(VLOOKUP($B{row_index},勘定科目!$A:$H,'
                f'HLOOKUP($E$5,勘定科目!$F$1:$H$2,2,0),0)="","",'
                f'VLOOKUP($B{row_index},勘定科目!$A:$E,2,0)),"")'
            ),
        )
        worksheet.cell(
            row=row_index,
            column=LOOKUP_GROUP_COL,
            value=f'=IF(C{row_index}="","",VLOOKUP($B{row_index},勘定科目!$A:$E,4,0))',
        )
        worksheet.cell(
            row=row_index,
            column=TOTAL_COL,
            value=f"=SUM(F{row_index}:Q{row_index})",
        )

    def _clear_visible_months(self, worksheet, row_index: int) -> None:
        for offset in range(len(self.fy_months)):
            worksheet.cell(row=row_index, column=VISIBLE_MONTH_START_COL + offset).value = None
        worksheet.cell(row=row_index, column=TOTAL_COL, value=f"=SUM(F{row_index}:Q{row_index})")

    def _prepare_append_row(self, worksheet, row_index: int) -> None:
        self._copy_row_style(worksheet, APPEND_TEMPLATE_ROW, row_index)
        self._write_lookup_formulas(worksheet, row_index)
        for column_index in range(1, WBS_COL + 1):
            cell = worksheet.cell(row=row_index, column=column_index)
            if VISIBLE_MONTH_START_COL <= column_index <= TOTAL_COL:
                cell.fill = openpyxl.styles.PatternFill("solid", fgColor=APPEND_MONTH_FILL)
            elif column_index in (DESCRIPTION_COL, WBS_COL):
                cell.fill = openpyxl.styles.PatternFill("solid", fgColor=APPEND_NOTE_FILL)
            else:
                cell.fill = openpyxl.styles.PatternFill("solid", fgColor=APPEND_LEFT_FILL)
        worksheet.cell(row=row_index, column=5).value = None
        worksheet.cell(row=row_index, column=ACCOUNT_COL).value = None
        worksheet.cell(row=row_index, column=DESCRIPTION_COL).value = None
        worksheet.cell(row=row_index, column=WBS_COL).value = None
        self._clear_visible_months(worksheet, row_index)

    def _clear_append_area(self, worksheet, start_row: int) -> None:
        for row_index in range(start_row, self._append_last_row(worksheet) + 1):
            self._prepare_append_row(worksheet, row_index)

    def _append_last_row(self, worksheet) -> int:
        return max(int(worksheet.max_row or 0), MIN_APPEND_LAST_ROW)

    def _clear_template_account_column(
        self,
        worksheet,
        start_row: int = TEMPLATE_ACCOUNT_CLEAR_START_ROW,
    ) -> None:
        for row_index in range(max(int(start_row or 1), 1), self._append_last_row(worksheet) + 1):
            worksheet.cell(row=row_index, column=ACCOUNT_COL).value = None

    def _cell_has_user_visible_value(self, worksheet, row_index: int, column_index: int) -> bool:
        value = worksheet.cell(row=row_index, column=column_index).value
        if value is None:
            return False
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return False
            # Template lookup/total formulas are pre-filled in many blank rows.
            # They should not make a row count as occupied.
            if text.startswith("="):
                return False
            return True
        if isinstance(value, (int, float)):
            return abs(float(value)) > 1e-9
        return True

    def _resolve_append_start_row(self, worksheet, requested_start_row: int) -> int:
        """Find the first safe append row for this CC's generated workbook.

        ``requested_start_row`` is a minimum, not a hard-coded destination.
        Different CCs can have different final occupied rows, so append output
        starts after the last row that contains visible business data.
        """
        minimum_start = max(int(requested_start_row or MIN_APPEND_START_ROW), MIN_APPEND_START_ROW)
        meaningful_columns = (
            ACCOUNT_COL,
            5,
            *range(VISIBLE_MONTH_START_COL, TOTAL_COL + 1),
            DESCRIPTION_COL,
            WBS_COL,
        )
        last_occupied = minimum_start - 1
        for row_index in range(1, self._append_last_row(worksheet) + 1):
            if any(
                self._cell_has_user_visible_value(worksheet, row_index, column_index)
                for column_index in meaningful_columns
            ):
                last_occupied = max(last_occupied, row_index)
        return max(minimum_start, last_occupied + 1)

    def _input_rows_for_cc(self, cc_code: object, source: str | None = None) -> list[sqlite3.Row]:
        cc_key = str(cc_code)
        if source is None:
            query = """
                SELECT source, period, description, account_code, amount_vnd, amount_usd
                FROM fact_input_data
                WHERE cc_code = ?
            """
            params = (cc_key,)
        else:
            query = """
                SELECT source, period, description, account_code, amount_vnd, amount_usd
                FROM fact_input_data
                WHERE cc_code = ? AND source = ?
            """
            params = (cc_key, source)
        return self.conn.execute(query, params).fetchall()

    def _month_series(
        self,
        cc_code: int,
        *,
        source: str | None = None,
        description: str | None = None,
        description_like: str | None = None,
        account_code: int | None = None,
        value_column: str = "amount_vnd",
    ) -> dict[str, float]:
        conditions = ["cc_code = ?"]
        params: list[object] = [str(cc_code)]
        if source is not None:
            conditions.append("source = ?")
            params.append(source)
        if description is not None:
            conditions.append("description = ?")
            params.append(description)
        if description_like is not None:
            conditions.append("description LIKE ?")
            params.append(description_like)
        if account_code is not None:
            conditions.append("account_code = ?")
            params.append(int(account_code))

        query = f"""
            SELECT period, SUM(COALESCE({value_column}, 0)) AS amount
            FROM fact_input_data
            WHERE {' AND '.join(conditions)}
            GROUP BY period
        """
        rows = self.conn.execute(query, params).fetchall()
        return {str(row["period"]): float(row["amount"] or 0.0) for row in rows}

    def _ga_unit_price_series(self, match_tokens: tuple[str, ...]) -> dict[str, float]:
        rows = self.conn.execute(
            """
            SELECT period, description, amount_vnd
            FROM fact_input_data
            WHERE source = 'ga_unit_price'
            """
        ).fetchall()
        result: dict[str, float] = {}
        normalized_tokens = tuple(self._normalize_text(token) for token in match_tokens)
        for row in rows:
            description = self._normalize_text(row["description"])
            if not any(token in description for token in normalized_tokens):
                continue
            result[str(row["period"])] = float(row["amount_vnd"] or 0.0)
        return result

    def _write_numeric_series(self, worksheet, row_index: int, values: dict[str, float]) -> None:
        self._clear_visible_months(worksheet, row_index)
        for offset, period in enumerate(self.fy_months):
            amount = float(values.get(period, 0.0))
            formula_value = f"={self._format_number(amount)}" if amount else None
            worksheet.cell(
                row=row_index,
                column=VISIBLE_MONTH_START_COL + offset,
                value=formula_value,
            )
        worksheet.cell(row=row_index, column=TOTAL_COL, value=f"=SUM(F{row_index}:Q{row_index})")

    def _write_formula_series(
        self,
        worksheet,
        row_index: int,
        terms_by_period: dict[str, list[str]],
        numeric_values: dict[str, float] | None = None,
    ) -> None:
        self._clear_visible_months(worksheet, row_index)
        numeric_values = numeric_values or {}
        for offset, period in enumerate(self.fy_months):
            terms = list(terms_by_period.get(period, []))
            numeric_amount = float(numeric_values.get(period, 0.0))
            if numeric_amount:
                terms.append(self._format_number(numeric_amount))
            if not terms:
                continue
            worksheet.cell(
                row=row_index,
                column=VISIBLE_MONTH_START_COL + offset,
                value=f"={' + '.join(terms)}".replace(" + ", "+"),
            )
        worksheet.cell(row=row_index, column=TOTAL_COL, value=f"=SUM(F{row_index}:Q{row_index})")

    def _write_fx_formula_series(self, worksheet, row_index: int, values_usd: dict[str, float]) -> None:
        self._clear_visible_months(worksheet, row_index)
        for offset, period in enumerate(self.fy_months):
            amount_usd = float(values_usd.get(period, 0.0))
            if amount_usd <= 0:
                continue
            worksheet.cell(
                row=row_index,
                column=VISIBLE_MONTH_START_COL + offset,
                value=f"=ROUND({self._format_number(amount_usd)}*$B$2,0)",
            )
        worksheet.cell(row=row_index, column=TOTAL_COL, value=f"=SUM(F{row_index}:Q{row_index})")

    def _write_headcount_formula_series(
        self,
        worksheet,
        row_index: int,
        unit_prices: dict[str, float],
        start_headcount_row: int = 24,
        end_headcount_row: int = 25,
    ) -> None:
        self._clear_visible_months(worksheet, row_index)
        for offset, period in enumerate(self.fy_months):
            unit_price = float(unit_prices.get(period, 0.0))
            if unit_price <= 0:
                continue
            column_letter = get_column_letter(VISIBLE_MONTH_START_COL + offset)
            worksheet.cell(
                row=row_index,
                column=VISIBLE_MONTH_START_COL + offset,
                value=(
                    f"=SUM({column_letter}${start_headcount_row}:{column_letter}${end_headcount_row})"
                    f"*{self._format_number(unit_price)}"
                ),
            )
        worksheet.cell(row=row_index, column=TOTAL_COL, value=f"=SUM(F{row_index}:Q{row_index})")

    def _write_prev_month_headcount_formula_series(
        self,
        worksheet,
        row_index: int,
        unit_prices: dict[str, float],
        start_headcount_row: int = 24,
        end_headcount_row: int = 25,
    ) -> None:
        # Business sheet requires recurring admin costs to use previous-month headcount.
        # April falls back to April because prior-March data is not available in the FY file.
        self._clear_visible_months(worksheet, row_index)
        for offset, period in enumerate(self.fy_months):
            unit_price = float(unit_prices.get(period, 0.0))
            if unit_price <= 0:
                continue
            source_offset = offset if offset == 0 else offset - 1
            source_column_letter = get_column_letter(VISIBLE_MONTH_START_COL + source_offset)
            worksheet.cell(
                row=row_index,
                column=VISIBLE_MONTH_START_COL + offset,
                value=(
                    f"=SUM({source_column_letter}${start_headcount_row}:{source_column_letter}${end_headcount_row})"
                    f"*{self._format_number(unit_price)}"
                ),
            )
        worksheet.cell(row=row_index, column=TOTAL_COL, value=f"=SUM(F{row_index}:Q{row_index})")

    def _match_description(self, description: str, tokens: tuple[str, ...], exclude_tokens: tuple[str, ...]) -> bool:
        normalized_description = self._normalize_text(description)
        normalized_tokens = tuple(self._normalize_text(token) for token in tokens)
        normalized_excludes = tuple(self._normalize_text(token) for token in exclude_tokens)
        return any(token in normalized_description for token in normalized_tokens) and not any(
            token in normalized_description for token in normalized_excludes
        )

    def _series_from_tokens(
        self,
        cc_code: int,
        *,
        tokens: tuple[str, ...],
        exclude_tokens: tuple[str, ...] = (),
        source_prefix: str = "alloc_",
        value_column: str = "amount_vnd",
    ) -> dict[str, float]:
        result: dict[str, float] = defaultdict(float)
        for row in self._input_rows_for_cc(cc_code):
            source = str(row["source"] or "")
            if source_prefix and not source.startswith(source_prefix):
                continue
            if not self._match_description(str(row["description"] or ""), tokens, exclude_tokens):
                continue
            result[str(row["period"])] += float(row[value_column] or 0.0)
        return dict(result)

    def _alloc_formula_term_from_row(self, row: sqlite3.Row) -> str | None:
        source = str(row["source"] or "")
        if not source.startswith("alloc_"):
            return None
        unit_price = float(self.rule_unit_price_by_source.get(source, 0.0) or 0.0)
        keys = row.keys()
        raw_amount = row["amount_vnd"] if "amount_vnd" in keys else row["amount"]
        amount_vnd = float(raw_amount or 0.0)
        if unit_price <= 0 or amount_vnd <= 0:
            return None
        driver_value = amount_vnd / unit_price
        if abs(driver_value - round(driver_value)) < 1e-9:
            driver_value = round(driver_value)
        return f"{self._format_number(driver_value)}*{self._format_number(unit_price)}"

    def _alloc_formula_series_from_tokens(
        self,
        cc_code: object,
        *,
        tokens: tuple[str, ...],
        exclude_tokens: tuple[str, ...] = (),
        source_prefix: str = "alloc_",
    ) -> tuple[dict[str, list[str]], dict[str, float]]:
        terms_by_period: dict[str, list[str]] = defaultdict(list)
        numeric_values: dict[str, float] = defaultdict(float)
        for row in self._input_rows_for_cc(cc_code):
            source = str(row["source"] or "")
            if source_prefix and not source.startswith(source_prefix):
                continue
            if not self._match_description(str(row["description"] or ""), tokens, exclude_tokens):
                continue
            term = self._alloc_formula_term_from_row(row)
            if term:
                terms_by_period[str(row["period"])].append(term)
            else:
                numeric_values[str(row["period"])] += float(row["amount_vnd"] or 0.0)
        return dict(terms_by_period), dict(numeric_values)

    def _account_code_from_tokens(
        self,
        cc_code: int,
        *,
        tokens: tuple[str, ...],
        exclude_tokens: tuple[str, ...] = (),
        source_prefix: str = "alloc_",
    ) -> int | None:
        account_codes: set[int] = set()
        for row in self._input_rows_for_cc(cc_code):
            source = str(row["source"] or "")
            if source_prefix and not source.startswith(source_prefix):
                continue
            if not self._match_description(str(row["description"] or ""), tokens, exclude_tokens):
                continue
            code = int(row["account_code"] or 0)
            if code > 0:
                account_codes.add(code)
        if len(account_codes) == 1:
            return next(iter(account_codes))
        return None

    def _fixed_row_for_description(self, description: str) -> int | None:
        for row_index, matcher in FIXED_ALLOCATION_ROW_MATCHERS.items():
            if self._match_description(description, matcher["tokens"], matcher["exclude_tokens"]):
                return row_index
        return None

    def _load_explicit_form_rows(self, cc_code: int) -> list[dict[str, object]]:
        rows = self.conn.execute(
            """
            SELECT form_row, account_code, description, period, SUM(amount_vnd) AS amount
            FROM fact_input_data
            WHERE cc_code = ?
              AND account_code > 0
              AND form_row IS NOT NULL
            GROUP BY form_row, account_code, description, period
            ORDER BY form_row, account_code, description, period
            """,
            (str(cc_code),),
        ).fetchall()

        grouped: dict[int, dict[str, object]] = {}
        for row in rows:
            row_index = int(row["form_row"] or 0)
            if row_index <= 0:
                continue
            bucket = grouped.setdefault(
                row_index,
                {
                    "form_row": row_index,
                    "account_codes": set(),
                    "descriptions": set(),
                    "months": defaultdict(float),
                    "terms": defaultdict(list),
                    "numeric_values": defaultdict(float),
                },
            )
            account_code = int(row["account_code"] or 0)
            if account_code > 0:
                bucket["account_codes"].add(account_code)
            description = str(row["description"] or "").strip()
            if description:
                clean_description = self._strip_explicit_formula_metadata(description)
                if clean_description:
                    bucket["descriptions"].add(clean_description)
            period = str(row["period"])
            amount = float(row["amount"] or 0.0)
            term = self._explicit_formula_term_from_description(description)
            if term:
                bucket["terms"][period].append(term)
            else:
                bucket["numeric_values"][period] += amount
                bucket["months"][period] += amount

        result: list[dict[str, object]] = []
        for row_index in sorted(grouped):
            bucket = grouped[row_index]
            account_codes = bucket.pop("account_codes")
            descriptions = bucket.pop("descriptions")
            bucket["account_code"] = next(iter(account_codes)) if len(account_codes) == 1 else None
            bucket["description"] = next(iter(descriptions)) if len(descriptions) == 1 else None
            bucket["months"] = dict(bucket["months"])
            bucket["terms"] = dict(bucket["terms"])
            bucket["numeric_values"] = dict(bucket["numeric_values"])
            result.append(bucket)
        return result

    def _explicit_formula_term_from_description(self, description: str) -> str | None:
        marker = "formula_expr="
        for part in str(description or "").split("|"):
            if part.startswith(marker):
                formula = part[len(marker):].strip()
                return formula[1:] if formula.startswith("=") else formula
        return None

    def _strip_explicit_formula_metadata(self, description: str) -> str:
        return "|".join(
            part
            for part in str(description or "").split("|")
            if not part.startswith("formula_expr=")
        ).strip()

    def _parse_it_component_term(self, description: str) -> tuple[str, float, float] | None:
        parts = description.split("|")
        if len(parts) < 5 or parts[0:2] != ["it_sim", "component_term"]:
            return None

        component_key = parts[2]
        quantity = 0.0
        unit_price_usd = 0.0
        for part in parts[3:]:
            if part.startswith("qty="):
                quantity = float(part.split("=", 1)[1] or 0.0)
            elif part.startswith("unit_usd="):
                unit_price_usd = float(part.split("=", 1)[1] or 0.0)
        if quantity <= 0 or unit_price_usd <= 0:
            return None
        return component_key, quantity, unit_price_usd

    def _write_explicit_form_rows(self, worksheet, cc_code: int) -> None:
        for row in self._load_explicit_form_rows(cc_code):
            row_index = int(row["form_row"])
            self._clear_visible_months(worksheet, row_index)
            account_code = row.get("account_code")
            if account_code:
                worksheet.cell(row=row_index, column=ACCOUNT_COL, value=int(account_code))
            existing_description = worksheet.cell(row=row_index, column=DESCRIPTION_COL).value
            if not existing_description and row.get("description"):
                worksheet.cell(row=row_index, column=DESCRIPTION_COL, value=row["description"])
            if row.get("terms"):
                self._write_formula_series(worksheet, row_index, row["terms"], row["numeric_values"])
            else:
                self._write_numeric_series(worksheet, row_index, row["months"])

    def _write_it_system_total_row(self, worksheet, cc_code: int) -> None:
        rows = self._input_rows_for_cc(cc_code, source="it_sim")
        total_vnd_by_period: dict[str, float] = {}
        component_usd_by_period: dict[str, dict[str, float]] = defaultdict(dict)
        component_terms_by_period: dict[str, dict[str, list[tuple[float, float]]]] = defaultdict(lambda: defaultdict(list))
        account_codes: set[int] = set()

        for row in rows:
            description = str(row["description"] or "")
            period = str(row["period"])
            account_code = int(row["account_code"] or 0)
            if account_code > 0:
                account_codes.add(account_code)

            if description.startswith("it_sim|system_usage_total"):
                total_vnd_by_period[period] = float(row["amount_vnd"] or 0.0)
                continue

            parsed_term = self._parse_it_component_term(description)
            if parsed_term is not None:
                component_key, quantity, unit_price_usd = parsed_term
                component_terms_by_period[period][component_key].append((quantity, unit_price_usd))
                continue

            if description.startswith("it_sim|component|"):
                parts = description.split("|")
                if len(parts) >= 3:
                    component_key = parts[2]
                    component_usd_by_period[period][component_key] = float(row["amount_usd"] or 0.0)

        row_index = self._find_it_system_total_row(worksheet)
        account_code = self._resolve_it_system_account_code(cc_code, account_codes)
        if account_code is None:
            raise RuntimeError(f"Unable to resolve KDC System Cost account for cost center {cc_code}")
        worksheet.cell(row=row_index, column=ACCOUNT_COL, value=account_code)

        self._clear_visible_months(worksheet, row_index)
        for offset, period in enumerate(self.fy_months):
            component_terms = component_terms_by_period.get(period, {})
            ordered_terms = []
            for key in IT_COMPONENT_ORDER:
                for quantity, unit_price_usd in component_terms.get(key, []):
                    ordered_terms.append(f"{self._format_number(quantity)}*{self._format_number(unit_price_usd)}")

            component_values = component_usd_by_period.get(period, {})
            ordered_values = [
                float(component_values[key])
                for key in IT_COMPONENT_ORDER
                if float(component_values.get(key, 0.0)) > 0
            ]
            cell = worksheet.cell(row=row_index, column=VISIBLE_MONTH_START_COL + offset)
            if ordered_terms:
                cell.value = f"=ROUND(({'+'.join(ordered_terms)})*$B$2,0)"
                continue
            if ordered_values:
                formula = "+".join(self._format_number(value) for value in ordered_values)
                cell.value = f"=ROUND(({formula})*$B$2,0)"
                continue

            total_amount = float(total_vnd_by_period.get(period, 0.0))
            cell.value = int(round(total_amount)) if total_amount else None
        worksheet.cell(row=row_index, column=TOTAL_COL, value=f"=SUM(F{row_index}:Q{row_index})")

    def _write_fixed_rows_legacy(self, worksheet, cc_code: int) -> None:
        fixed_account_codes = {
            36: 5006016260,
            37: 5006016261,
            38: 5006016244,
            40: 9114120007,
            41: 9114120007,
            42: 9114120007,
            44: 5005066281,
            45: 5005066282,
            46: 5005056281,
            48: 5005016372,
            49: 5005016372,
            51: 5005246286,
            57: 5004086291,
            58: 5004086291,
            59: 5004086291,
            97: 5005246288,
            98: 5005246288,
            137: 5005246286,
        }
        for row_index in MANAGED_FIXED_ROWS:
            self._clear_visible_months(worksheet, row_index)
        for row_index, account_code in fixed_account_codes.items():
            worksheet.cell(row=row_index, column=ACCOUNT_COL, value=account_code)

        self._write_numeric_series(
            worksheet,
            44,
            self._month_series(cc_code, source="facility", description="electric"),
        )
        self._write_numeric_series(
            worksheet,
            45,
            self._month_series(cc_code, source="facility", description="water"),
        )
        self._write_prev_month_headcount_formula_series(
            worksheet,
            46,
            self._ga_unit_price_series(("gas|headcount_per_person", "食堂燃料費")),
        )
        self._write_prev_month_headcount_formula_series(
            worksheet,
            51,
            self._ga_unit_price_series(("清掃費", "chi phí làm sạch|headcount_per_person")),
        )
        cleaning_series = self._ga_unit_price_series(("cleaning|headcount_per_person",))
        if cleaning_series:
            self._write_prev_month_headcount_formula_series(worksheet, 51, cleaning_series)
        self._write_prev_month_headcount_formula_series(
            worksheet,
            48,
            self._ga_unit_price_series(("手洗い洗剤", "nuoc rua tay|headcount_per_person", "nước rửa tay|headcount_per_person")),
        )
        self._write_prev_month_headcount_formula_series(
            worksheet,
            49,
            self._ga_unit_price_series(("トイレットペーパー", "giay ve sinh|headcount_per_person", "giấy vệ sinh|headcount_per_person")),
        )
        self._write_fx_formula_series(
            worksheet,
            36,
            self._month_series(cc_code, source="facility", description="depreciation_building", value_column="amount_usd"),
        )
        self._write_fx_formula_series(
            worksheet,
            37,
            self._month_series(cc_code, source="facility", description="depreciation_land", value_column="amount_usd"),
        )
        self._write_fx_formula_series(
            worksheet,
            38,
            self._month_series(cc_code, source="fixed_assets", description_like="fixed_assets_depr|%", value_column="amount_usd"),
        )
        self._write_fx_formula_series(
            worksheet,
            40,
            self._month_series(cc_code, source="facility", description="interest_building", value_column="amount_usd"),
        )
        self._write_fx_formula_series(
            worksheet,
            41,
            self._month_series(cc_code, source="facility", description="interest_land", value_column="amount_usd"),
        )
        self._write_fx_formula_series(
            worksheet,
            42,
            self._month_series(cc_code, source="fixed_assets", description_like="fixed_assets_interest|%", value_column="amount_usd"),
        )
        self._write_it_system_total_row(worksheet, cc_code)

        for row_index, matcher in FIXED_ALLOCATION_ROW_MATCHERS.items():
            series = self._series_from_tokens(
                cc_code,
                tokens=matcher["tokens"],
                exclude_tokens=matcher["exclude_tokens"],
            )
            if not series:
                continue
            account_code = self._account_code_from_tokens(
                cc_code,
                tokens=matcher["tokens"],
                exclude_tokens=matcher["exclude_tokens"],
            )
            if account_code:
                worksheet.cell(row=row_index, column=ACCOUNT_COL, value=account_code)
            terms_by_period, numeric_values = self._alloc_formula_series_from_tokens(
                cc_code,
                tokens=matcher["tokens"],
                exclude_tokens=matcher["exclude_tokens"],
            )
            if terms_by_period:
                self._write_formula_series(worksheet, row_index, terms_by_period, numeric_values)
            else:
                self._write_numeric_series(worksheet, row_index, series)

        self._write_explicit_form_rows(worksheet, cc_code)

    def _write_fixed_rows(self, worksheet, cc_code: int) -> None:
        fixed_account_codes = {
            36: 5006016260,
            37: 5006016261,
            38: 5006016244,
            40: 9114120007,
            41: 9114120007,
            42: 9114120007,
            44: 5005066281,
            45: 5005066282,
            46: 5005056281,
            48: 5005016372,
            49: 5005016372,
            51: 5005246286,
            57: 5004086291,
            58: 5004086291,
            59: 5004086291,
            97: 5005246288,
            98: 5005246288,
            137: 5005246286,
        }
        for row_index in MANAGED_FIXED_ROWS:
            self._clear_visible_months(worksheet, row_index)

        def _set_fixed_account(row_index: int) -> None:
            account_code = fixed_account_codes.get(row_index)
            if account_code:
                worksheet.cell(row=row_index, column=ACCOUNT_COL, value=account_code)

        electric_series = self._month_series(cc_code, source="facility", description="electric")
        if self._series_has_output(electric_series):
            _set_fixed_account(44)
            self._write_numeric_series(worksheet, 44, electric_series)

        water_series = self._month_series(cc_code, source="facility", description="water")
        if self._series_has_output(water_series):
            _set_fixed_account(45)
            self._write_numeric_series(worksheet, 45, water_series)

        gas_series = self._ga_unit_price_series(("gas|headcount_per_person", "食堂燃料費"))
        if self._series_has_output(gas_series):
            _set_fixed_account(46)
            self._write_prev_month_headcount_formula_series(worksheet, 46, gas_series)

        legacy_cleaning_series = self._ga_unit_price_series(("清掃費", "chi ph\u00ed l\u00e0m s\u1ea1ch|headcount_per_person"))
        if self._series_has_output(legacy_cleaning_series):
            _set_fixed_account(51)
            self._write_prev_month_headcount_formula_series(worksheet, 51, legacy_cleaning_series)

        cleaning_series = self._ga_unit_price_series(("cleaning|headcount_per_person",))
        if self._series_has_output(cleaning_series):
            _set_fixed_account(51)
            self._write_prev_month_headcount_formula_series(worksheet, 51, cleaning_series)

        handwash_series = self._ga_unit_price_series(
            ("手洗い洗剤", "nuoc rua tay|headcount_per_person", "nước rửa tay|headcount_per_person")
        )
        if self._series_has_output(handwash_series):
            _set_fixed_account(48)
            self._write_prev_month_headcount_formula_series(worksheet, 48, handwash_series)

        toilet_paper_series = self._ga_unit_price_series(
            ("トイレットペーパー", "giay ve sinh|headcount_per_person", "giấy vệ sinh|headcount_per_person")
        )
        if self._series_has_output(toilet_paper_series):
            _set_fixed_account(49)
            self._write_prev_month_headcount_formula_series(worksheet, 49, toilet_paper_series)

        building_depr_series = self._month_series(
            cc_code,
            source="facility",
            description="depreciation_building",
            value_column="amount_usd",
        )
        if self._series_has_output(building_depr_series):
            _set_fixed_account(36)
            self._write_fx_formula_series(worksheet, 36, building_depr_series)

        land_depr_series = self._month_series(
            cc_code,
            source="facility",
            description="depreciation_land",
            value_column="amount_usd",
        )
        if self._series_has_output(land_depr_series):
            _set_fixed_account(37)
            self._write_fx_formula_series(worksheet, 37, land_depr_series)

        equipment_depr_series = self._month_series(
            cc_code,
            source="fixed_assets",
            description_like="fixed_assets_depr|%",
            value_column="amount_usd",
        )
        if self._series_has_output(equipment_depr_series):
            _set_fixed_account(38)
            self._write_fx_formula_series(worksheet, 38, equipment_depr_series)

        building_interest_series = self._month_series(
            cc_code,
            source="facility",
            description="interest_building",
            value_column="amount_usd",
        )
        if self._series_has_output(building_interest_series):
            _set_fixed_account(40)
            self._write_fx_formula_series(worksheet, 40, building_interest_series)

        land_interest_series = self._month_series(
            cc_code,
            source="facility",
            description="interest_land",
            value_column="amount_usd",
        )
        if self._series_has_output(land_interest_series):
            _set_fixed_account(41)
            self._write_fx_formula_series(worksheet, 41, land_interest_series)

        equipment_interest_series = self._month_series(
            cc_code,
            source="fixed_assets",
            description_like="fixed_assets_interest|%",
            value_column="amount_usd",
        )
        if self._series_has_output(equipment_interest_series):
            _set_fixed_account(42)
            self._write_fx_formula_series(worksheet, 42, equipment_interest_series)

        self._write_it_system_total_row(worksheet, cc_code)

        for row_index, matcher in FIXED_ALLOCATION_ROW_MATCHERS.items():
            series = self._series_from_tokens(
                cc_code,
                tokens=matcher["tokens"],
                exclude_tokens=matcher["exclude_tokens"],
            )
            if not series:
                continue
            account_code = self._account_code_from_tokens(
                cc_code,
                tokens=matcher["tokens"],
                exclude_tokens=matcher["exclude_tokens"],
            )
            if account_code:
                worksheet.cell(row=row_index, column=ACCOUNT_COL, value=account_code)
            terms_by_period, numeric_values = self._alloc_formula_series_from_tokens(
                cc_code,
                tokens=matcher["tokens"],
                exclude_tokens=matcher["exclude_tokens"],
            )
            if self._formula_series_has_output(terms_by_period, numeric_values):
                self._write_formula_series(worksheet, row_index, terms_by_period, numeric_values)
            else:
                self._write_numeric_series(worksheet, row_index, series)

        self._write_explicit_form_rows(worksheet, cc_code)

    def _load_append_rows(self, cc_code: int) -> list[dict[str, object]]:
        rows = self.conn.execute(
            """
            SELECT source, account_code, description, period, SUM(amount_vnd) AS amount
            FROM fact_input_data
            WHERE cc_code = ?
              AND account_code > 0
              AND form_row IS NULL
              AND source NOT IN ('facility', 'fixed_assets', 'it_sim', 'ga_unit_price')
            GROUP BY source, account_code, description, period
            ORDER BY account_code, description, source, period
            """,
            (str(cc_code),),
        ).fetchall()

        grouped: dict[tuple[int, str], dict[str, object]] = {}
        for row in rows:
            description = str(row["description"] or "")
            if self._fixed_row_for_description(description) is not None:
                continue

            clean_description = self._strip_explicit_formula_metadata(description)
            key = (int(row["account_code"]), clean_description)
            bucket = grouped.setdefault(
                key,
                {
                    "account_code": int(row["account_code"]),
                    "description": clean_description,
                    "months": {},
                    "terms": defaultdict(list),
                    "numeric_months": defaultdict(float),
                },
            )
            period = str(row["period"])
            term = self._explicit_formula_term_from_description(description) or self._alloc_formula_term_from_row(row)
            if term:
                bucket["terms"][period].append(term)
            else:
                amount = float(row["amount"] or 0.0)
                bucket["numeric_months"][period] += amount
                bucket["months"][period] = bucket["numeric_months"][period]
        return list(grouped.values())

    def export_to_template(
        self,
        template_path: str,
        output_path: str,
        cc_code: Optional[object] = None,
        sheet_name: Optional[str] = None,
        start_row: int = APPEND_START_ROW,
    ) -> bool:
        target_cc = str(cc_code).strip() if cc_code else None
        if target_cc is None:
            return False

        fact_exists = self.conn.execute(
            "SELECT 1 FROM fact_input_data WHERE cc_code = ? LIMIT 1",
            (target_cc,),
        ).fetchone()
        if not fact_exists:
            return False

        if os.path.exists(output_path):
            os.remove(output_path)
        shutil.copy2(template_path, output_path)

        workbook = openpyxl.load_workbook(output_path)
        try:
            hub_sheet_name = sheet_name if sheet_name and sheet_name in workbook.sheetnames else helpers.find_hub_sheet_name(workbook)
            worksheet = workbook[hub_sheet_name]

            worksheet.cell(
                row=5,
                column=ACCOUNT_COL,
                value=int(target_cc) if target_cc.isdigit() else target_cc,
            )
            self._clear_template_account_column(worksheet)
            self._write_fixed_rows(worksheet, target_cc)

            append_start_row = self._resolve_append_start_row(worksheet, start_row)
            self._clear_append_area(worksheet, append_start_row)
            max_data_row = self._append_last_row(worksheet)
            current_row = append_start_row
            for row in self._load_append_rows(target_cc):
                if current_row > max_data_row:
                    raise ValueError("FORM detail sheet does not have enough append rows prepared.")
                self._prepare_append_row(worksheet, current_row)
                worksheet.cell(row=current_row, column=ACCOUNT_COL, value=int(row["account_code"]))
                worksheet.cell(row=current_row, column=DESCRIPTION_COL, value=row["description"])
                if row["terms"]:
                    self._write_formula_series(
                        worksheet,
                        current_row,
                        dict(row["terms"]),
                        dict(row["numeric_months"]),
                    )
                else:
                    self._write_numeric_series(worksheet, current_row, row["months"])
                current_row += 1

            workbook.save(output_path)
            return True
        finally:
            workbook.close()
