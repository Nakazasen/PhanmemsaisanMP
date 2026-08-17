# -*- coding: utf-8 -*-
import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from typing import List
from src.engine.variance_analyzer import VarianceReport

def export_variance_report(report: VarianceReport, output_path: str) -> None:
    """
    Export VarianceReport to an Excel file.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "So Sánh Biến Động MP"

    # Headers
    headers = ["Mã Tài Khoản", "Tên Khoản Mục", "Năm Trước", "Năm Nay", "Chênh Lệch", "% Biến Động", "Trạng Thái", "Ghi Chú (User)"]
    ws.append(headers)

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Data rows
    red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    yellow_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")

    for row_idx, line in enumerate(report.lines, start=2):
        ws.cell(row=row_idx, column=1, value=line.account_code)
        ws.cell(row=row_idx, column=2, value=line.item_name)

        c3 = ws.cell(row=row_idx, column=3, value=line.base_value)
        c3.number_format = '#,##0'

        c4 = ws.cell(row=row_idx, column=4, value=line.current_value)
        c4.number_format = '#,##0'

        c5 = ws.cell(row=row_idx, column=5, value=line.variance_absolute)
        c5.number_format = '#,##0'

        c6 = ws.cell(row=row_idx, column=6, value=(line.variance_percent / 100.0) if line.variance_percent is not None else "")
        c6.number_format = '0.00%'

        ws.cell(row=row_idx, column=7, value=line.status.value)
        ws.cell(row=row_idx, column=8, value="") # Placeholder for user notes

        if line.is_alert:
            fill = red_fill if line.variance_absolute > 0 else yellow_fill
            for col_num in range(1, len(headers) + 1):
                ws.cell(row=row_idx, column=col_num).fill = fill

    # Auto-fit columns
    for col_num in range(1, len(headers) + 1):
        col_letter = get_column_letter(col_num)
        ws.column_dimensions[col_letter].width = 18
    ws.column_dimensions['B'].width = 40
    ws.column_dimensions['H'].width = 30

    wb.save(output_path)

def batch_export_variance_reports(reports: List[VarianceReport], output_path: str) -> None:
    """
    Export multiple VarianceReports to a single Excel file (one sheet per CC).
    """
    wb = openpyxl.Workbook()
    wb.remove(wb.active) # Remove default sheet

    headers = ["Mã Tài Khoản", "Tên Khoản Mục", "Năm Trước", "Năm Nay", "Chênh Lệch", "% Biến Động", "Trạng Thái", "Ghi Chú (User)"]
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    yellow_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")

    for report in reports:
        # Sheet name max 31 chars
        title = str(report.context.cost_center_code)[:31]
        if title in wb.sheetnames:
            title = title[:28] + "_dup"
        ws = wb.create_sheet(title=title)

        ws.append(headers)
        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for row_idx, line in enumerate(report.lines, start=2):
            ws.cell(row=row_idx, column=1, value=line.account_code)
            ws.cell(row=row_idx, column=2, value=line.item_name)

            c3 = ws.cell(row=row_idx, column=3, value=line.base_value)
            c3.number_format = '#,##0'

            c4 = ws.cell(row=row_idx, column=4, value=line.current_value)
            c4.number_format = '#,##0'

            c5 = ws.cell(row=row_idx, column=5, value=line.variance_absolute)
            c5.number_format = '#,##0'

            c6 = ws.cell(row=row_idx, column=6, value=(line.variance_percent / 100.0) if line.variance_percent is not None else "")
            c6.number_format = '0.00%'

            ws.cell(row=row_idx, column=7, value=line.status.value)
            ws.cell(row=row_idx, column=8, value="")

            if line.is_alert:
                fill = red_fill if line.variance_absolute > 0 else yellow_fill
                for col_num in range(1, len(headers) + 1):
                    ws.cell(row=row_idx, column=col_num).fill = fill

        for col_num in range(1, len(headers) + 1):
            col_letter = get_column_letter(col_num)
            ws.column_dimensions[col_letter].width = 18
        ws.column_dimensions['B'].width = 40
        ws.column_dimensions['H'].width = 30

    wb.save(output_path)
