"""
MP2027 Manager - Hub Builder
Aggregates and formats the final allocation results to write back to the Hub (内訳ﾘｽﾄ).
"""
import sqlite3
import pandas as pd
import openpyxl
import os
import shutil
from typing import Optional

from src.db.schema import get_connection
from src.utils.excel_helpers import get_fy_months, get_fy_month_labels

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
                dc.name_jp as cc_name,
                f.account_code,
                da.name_jp as account_name,
                f.description,
                f.period,
                SUM(f.amount_vnd) as amount
            FROM fact_input_data f
            JOIN dim_cost_centers dc ON f.cc_code = dc.code
            JOIN dim_accounts da ON f.account_code = da.code
            {where_clause}
            GROUP BY f.cc_code, dc.name_jp, f.account_code, da.name_jp, f.description, f.period
        """
        raw_df = pd.read_sql(query, self.conn, params=params)
        
        if raw_df.empty:
            return pd.DataFrame()
            
        pivot_df = raw_df.pivot_table(
            index=['cc_code', 'cc_name', 'account_code', 'account_name', 'description'],
            columns='period',
            values='amount',
            aggfunc='sum'
        ).fillna(0).reset_index()
        
        # Ensure all fy_months exist as columns
        for m in self.fy_months:
            if m not in pivot_df.columns:
                pivot_df[m] = 0.0
                
        # Calculate Total Column
        pivot_df['Total'] = pivot_df[self.fy_months].sum(axis=1)
        
        # FIX: Round everything to integers to satisfy Excel Row 3 CHECK
        cols_to_round = self.fy_months + ['Total']
        for col in cols_to_round:
            pivot_df[col] = pivot_df[col].round(0).astype(int)

        # Reorder columns: CC Info (A-E), Months Apr-Mar (F-Q), Total (R)
        final_cols = ['cc_code', 'cc_name', 'account_code', 'account_name', 'description'] + self.fy_months + ['Total']
        return pivot_df[final_cols]
        

    def export_to_template(self, template_path: str, output_path: str, cc_code: Optional[int] = None, 
                           sheet_name: str = '内訳ﾘｽﾄ(4～3月)', start_row: int = 29):
        """Copies template and writes data for a specific CC (or all) to the target sheet."""
        df = self.get_structured_data(cc_code=cc_code)
        if df.empty:
            print(f"⚠️ No data for CC {cc_code if cc_code else 'All'}, skipping export.")
            return False
            
        # Always overwrite output with a fresh copy of the template
        if os.path.exists(output_path):
            os.remove(output_path)
        shutil.copy2(template_path, output_path)
            
        wb = openpyxl.load_workbook(output_path)
        ws_hub = wb[sheet_name] if sheet_name in wb.sheetnames else wb.worksheets[0]
        
        # 1. Update Labels Row 4 (Month labels F-Q, Total R)
        month_labels = get_fy_month_labels(self.fiscal_year)
        for i, label in enumerate(month_labels):
            ws_hub.cell(row=4, column=6 + i, value=label) # Col F is 6
        ws_hub.cell(row=4, column=18, value="合計") # Col R is 18

        # 2. Update Working Days (稼働日) sheet
        if '稼働日' in wb.sheetnames:
            ws_k = wb['稼働日']
            labels = get_fy_month_labels(self.fiscal_year)
            for i, label in enumerate(labels):
                ws_k.cell(row=3 + i, column=1, value=label) 

        # 3. Write Data Records
        # Clear existing data manually via delete_rows or just overwrite
        if ws_hub.max_row >= start_row:
             # Targeted clear to preserve formatting if possible, but delete_rows is safer for formula integrity
             ws_hub.delete_rows(start_row, ws_hub.max_row - start_row + 1)

        current_row = start_row
        for _, row in df.iterrows():
            col_idx = 1
            for col_val in row:
                ws_hub.cell(row=current_row, column=col_idx, value=col_val)
                col_idx += 1
            current_row += 1
            
        wb.save(output_path)
        # print(f"✅ Exported {len(df)} rows to {output_path}")
        return True
