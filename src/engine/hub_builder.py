"""
MP2027 Manager - Hub Builder.

Aggregates final results and writes them back to the FORM hub sheet.
"""
import os
import shutil
import sqlite3
from typing import Optional

import openpyxl
import pandas as pd

from src.utils.excel_helpers import find_hub_sheet_name, get_fy_month_labels, get_fy_months

TOTAL_LABEL = "合計"


class HubBuilder:
    def __init__(self, conn: sqlite3.Connection, fiscal_year: int = 2027):
        self.conn = conn
        self.fiscal_year = fiscal_year
        self.fy_months = get_fy_months(fiscal_year)

    def get_structured_data(self, cc_code: Optional[int] = None) -> pd.DataFrame:
        """Query DB, join with dimensions, and pivot to 12 months structure."""
        where_clause = "WHERE f.account_code > 0"
        params = []
        if cc_code:
            where_clause += " AND f.cc_code = ?"
            params.append(cc_code)

        query = f"""
            SELECT
                f.cc_code,
                dc.name_jp AS cc_name,
                f.account_code,
                da.name_jp AS account_name,
                f.description,
                f.period,
                SUM(f.amount_vnd) AS amount
            FROM fact_input_data f
            JOIN dim_cost_centers dc ON f.cc_code = dc.code
            JOIN dim_accounts da ON f.account_code = da.code
            {where_clause}
            GROUP BY f.cc_code, dc.name_jp, f.account_code, da.name_jp, f.description, f.period
        """
        raw_df = pd.read_sql(query, self.conn, params=params)
        if raw_df.empty:
            return pd.DataFrame()

        pivot_df = (
            raw_df.pivot_table(
                index=["cc_code", "cc_name", "account_code", "account_name", "description"],
                columns="period",
                values="amount",
                aggfunc="sum",
            )
            .fillna(0)
            .reset_index()
        )

        for month in self.fy_months:
            if month not in pivot_df.columns:
                pivot_df[month] = 0.0

        pivot_df["Total"] = pivot_df[self.fy_months].sum(axis=1)
        for column in self.fy_months + ["Total"]:
            pivot_df[column] = pivot_df[column].round(0).astype(int)

        final_cols = ["cc_code", "cc_name", "account_code", "account_name", "description"] + self.fy_months + ["Total"]
        return pivot_df[final_cols]

    def export_to_template(
        self,
        template_path: str,
        output_path: str,
        cc_code: Optional[int] = None,
        sheet_name: Optional[str] = None,
        start_row: int = 29,
    ) -> bool:
        """Copy the template and write data for one CC or all CCs."""
        df = self.get_structured_data(cc_code=cc_code)
        if df.empty:
            return False

        if os.path.exists(output_path):
            os.remove(output_path)
        shutil.copy2(template_path, output_path)

        workbook = openpyxl.load_workbook(output_path)
        try:
            hub_sheet_name = sheet_name if sheet_name and sheet_name in workbook.sheetnames else find_hub_sheet_name(workbook)
            worksheet_hub = workbook[hub_sheet_name]

            month_labels = get_fy_month_labels(self.fiscal_year)
            for index, label in enumerate(month_labels):
                worksheet_hub.cell(row=4, column=6 + index, value=label)
            worksheet_hub.cell(row=4, column=18, value=TOTAL_LABEL)

            working_day_sheet = next((name for name in workbook.sheetnames if "稼働" in name), None)
            if working_day_sheet:
                worksheet_working_days = workbook[working_day_sheet]
                for index, label in enumerate(month_labels):
                    worksheet_working_days.cell(row=3 + index, column=1, value=label)

            if worksheet_hub.max_row >= start_row:
                worksheet_hub.delete_rows(start_row, worksheet_hub.max_row - start_row + 1)

            current_row = start_row
            for _, row in df.iterrows():
                for column_index, value in enumerate(row, start=1):
                    worksheet_hub.cell(row=current_row, column=column_index, value=value)
                current_row += 1

            workbook.save(output_path)
            return True
        finally:
            workbook.close()
