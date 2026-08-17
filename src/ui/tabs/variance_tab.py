# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from src.engine.variance_analyzer import ComparisonContext, map_and_analyze_variances, safe_load_mp_form

class VarianceTab(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.pack(fill="both", expand=True)
        self.base_file = tk.StringVar()
        self.curr_file = tk.StringVar()
        self.threshold_pct = tk.DoubleVar(value=10.0)
        self.threshold_abs = tk.DoubleVar(value=50000000.0)
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="So sánh biến động chi phí MP giữa hai năm tài chính", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=10, padx=10)

        # Setup control frame
        self.control_frame = ttk.LabelFrame(self, text="Cài đặt so sánh")
        self.control_frame.pack(fill="x", padx=10, pady=5)

        # File selectors
        ttk.Label(self.control_frame, text="File MP Năm Trước:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        ttk.Entry(self.control_frame, textvariable=self.base_file, width=60).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(self.control_frame, text="Chọn file...", command=lambda: self._select_file(self.base_file)).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(self.control_frame, text="File MP Năm Nay:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        ttk.Entry(self.control_frame, textvariable=self.curr_file, width=60).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(self.control_frame, text="Chọn file...", command=lambda: self._select_file(self.curr_file)).grid(row=1, column=2, padx=5, pady=5)

        # Thresholds
        thresh_frame = ttk.Frame(self.control_frame)
        thresh_frame.grid(row=2, column=0, columnspan=3, sticky="w", padx=5, pady=5)
        ttk.Label(thresh_frame, text="Ngưỡng cảnh báo:").pack(side="left")
        ttk.Entry(thresh_frame, textvariable=self.threshold_pct, width=6).pack(side="left", padx=5)
        ttk.Label(thresh_frame, text="% HOẶC").pack(side="left")
        ttk.Entry(thresh_frame, textvariable=self.threshold_abs, width=15).pack(side="left", padx=5)
        ttk.Label(thresh_frame, text="VNĐ").pack(side="left")
        ttk.Button(thresh_frame, text="Thực hiện So sánh", command=self._run_comparison, style="Accent.TButton").pack(side="left", padx=20)
        ttk.Button(thresh_frame, text="Xuất báo cáo Excel", command=self._export_excel).pack(side="left", padx=5)
        ttk.Button(thresh_frame, text="So sánh hàng loạt (Thư mục)", command=self._run_batch_comparison).pack(side="left", padx=5)

        # Data Grid
        self.data_frame = ttk.Frame(self)
        self.data_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("Account", "Name", "Base", "Current", "Diff", "Pct", "Status")
        self.tree = ttk.Treeview(self.data_frame, columns=columns, show="headings")
        self.tree.heading("Account", text="Mã Tài Khoản")
        self.tree.heading("Name", text="Tên Khoản Mục")
        self.tree.heading("Base", text="Năm Trước")
        self.tree.heading("Current", text="Năm Nay")
        self.tree.heading("Diff", text="Chênh Lệch")
        self.tree.heading("Pct", text="% Biến Động")
        self.tree.heading("Status", text="Trạng Thái")

        self.tree.column("Account", width=100)
        self.tree.column("Name", width=250)
        self.tree.column("Base", width=120, anchor="e")
        self.tree.column("Current", width=120, anchor="e")
        self.tree.column("Diff", width=120, anchor="e")
        self.tree.column("Pct", width=100, anchor="e")
        self.tree.column("Status", width=120)

        vsb = ttk.Scrollbar(self.data_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Tags for colors
        self.tree.tag_configure("alert_increase", background="#ffcccc") # Light red
        self.tree.tag_configure("alert_decrease", background="#fff0b3") # Light yellow

    def _select_file(self, var):
        path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx")])
        if path:
            var.set(path)

    def _run_comparison(self):
        bf = self.base_file.get().strip()
        cf = self.curr_file.get().strip()
        if not bf or not cf:
            messagebox.showwarning(
                "Chưa chọn tệp",
                "Vui lòng chọn đầy đủ cả Tệp Năm Trước và Tệp Năm Nay trước khi so sánh.\n\n"
                "Cách xử lý:\n"
                "1. Bấm nút 'Chọn...' tại mục Báo cáo MP Năm Trước để chọn tệp.\n"
                "2. Bấm nút 'Chọn...' tại mục Báo cáo MP Năm Nay để chọn tệp.\n"
                "3. Bấm nút 'So sánh (Năm nay vs Năm ngoái)'."
            )
            return

        try:
            thresh_pct = self.threshold_pct.get()
            thresh_abs = self.threshold_abs.get()
            if thresh_pct < 0 or thresh_abs < 0:
                raise ValueError("Ngưỡng cảnh báo không được là số âm.")
        except (tk.TclError, ValueError):
            messagebox.showwarning(
                "Lỗi nhập liệu ngưỡng",
                "Ngưỡng cảnh báo phải là giá trị số dương hợp lệ (ví dụ: Tỷ lệ %: 10, Số tiền: 50,000,000).\n\n"
                "Cách xử lý:\n"
                "1. Kiểm tra lại ô 'Tỷ lệ biến động (%)' và 'Số tiền biến động tuyệt đối'.\n"
                "2. Xóa các ký tự không phải số và nhập lại giá trị hợp lệ.\n"
                "3. Thực hiện so sánh lại."
            )
            return

        try:
            df_base = safe_load_mp_form(bf)
            df_curr = safe_load_mp_form(cf)

            ctx = ComparisonContext(
                fiscal_year_base=2026,
                fiscal_year_current=2027,
                cost_center_code="UNKNOWN",
                base_file_path=bf,
                current_file_path=cf,
                threshold_percent=thresh_pct,
                threshold_absolute=thresh_abs
            )
            report = map_and_analyze_variances(df_base, df_curr, ctx, acc_col=1, name_col=2, val_col=17)

            # Clear tree
            for item in self.tree.get_children():
                self.tree.delete(item)

            for line in report.lines:
                # Format numbers
                b_str = f"{line.base_value:,.0f}"
                c_str = f"{line.current_value:,.0f}"
                d_str = f"{line.variance_absolute:,.0f}"
                p_str = f"{line.variance_percent:.2f}%" if line.variance_percent is not None else "N/A"

                tags = ()
                if line.is_alert:
                    if line.variance_absolute > 0:
                        tags = ("alert_increase",)
                    else:
                        tags = ("alert_decrease",)

                self.tree.insert("", "end", values=(line.account_code, line.item_name, b_str, c_str, d_str, p_str, line.status.value), tags=tags)

            self._current_report = report
            messagebox.showinfo("Hoàn tất", "Đã so sánh xong dữ liệu hai năm.")

        except Exception as e:
            messagebox.showerror("Lỗi So Sánh", f"{str(e)}")

    def _export_excel(self):
        if not hasattr(self, "_current_report") or not self._current_report:
            messagebox.showwarning(
                "Chưa có dữ liệu",
                "Vui lòng thực hiện So sánh dữ liệu trước khi xuất báo cáo Excel.\n\n"
                "Cách xử lý:\n"
                "1. Chọn tệp Năm Trước và Năm Nay ở phía trên.\n"
                "2. Bấm 'So sánh (Năm nay vs Năm ngoái)'.\n"
                "3. Sau khi bảng kết quả hiện ra, bấm 'Xuất Excel'."
            )
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            initialfile="Bao_cao_bien_dong_MP.xlsx"
        )
        if path:
            try:
                from src.utils.excel_variance_writer import export_variance_report
                export_variance_report(self._current_report, path)
                messagebox.showinfo("Thành công", f"Đã xuất báo cáo thành công tới:\n{path}")
            except Exception as e:
                messagebox.showerror(
                    "Lỗi xuất Excel",
                    f"Đã xảy ra lỗi khi ghi tệp Excel:\n{str(e)}\n\n"
                    "Cách xử lý:\n"
                    "1. Kiểm tra xem tệp Excel có đang được mở bởi ứng dụng khác không (nếu có, hãy đóng tệp).\n"
                    "2. Kiểm tra quyền ghi tại thư mục đã chọn.\n"
                    "3. Thử lưu với tên tệp khác hoặc vị trí khác."
                )

    def _run_batch_comparison(self):
        try:
            thresh_pct = self.threshold_pct.get()
            thresh_abs = self.threshold_abs.get()
            if thresh_pct < 0 or thresh_abs < 0:
                raise ValueError("Ngưỡng cảnh báo không được là số âm.")
        except (tk.TclError, ValueError):
            messagebox.showwarning(
                "Lỗi nhập liệu ngưỡng",
                "Ngưỡng cảnh báo phải là giá trị số dương hợp lệ.\n\n"
                "Cách xử lý: Kiểm tra lại 2 ô nhập ngưỡng cảnh báo ở phía trên."
            )
            return

        base_dir = filedialog.askdirectory(title="Chọn thư mục chứa báo cáo MP Năm Trước")
        if not base_dir:
            return
        curr_dir = filedialog.askdirectory(title="Chọn thư mục chứa báo cáo MP Năm Nay")
        if not curr_dir:
            return

        from src.engine.variance_analyzer import scan_directories_and_pair_files, batch_analyze_variances
        pairs, unmatched = scan_directories_and_pair_files(base_dir, curr_dir)
        if not pairs:
            msg = (
                "Không tìm thấy cặp tệp MP nào khớp theo mã bộ phận giữa 2 thư mục.\n\n"
                "Nguyên nhân: Tên tệp không chứa mã bộ phận giống nhau (ví dụ: MP_1412000040_FY2026.xlsx và MP_1412000040_FY2027.xlsx).\n\n"
            )
            if unmatched:
                msg += f"Đã tìm thấy {len(unmatched)} tệp nhưng không thể ghép cặp:\n"
                msg += "• " + "\n• ".join(unmatched[:10])
                if len(unmatched) > 10:
                    msg += f"\n... (và {len(unmatched) - 10} tệp khác)\n"
                msg += "\n"
            msg += (
                "Cách xử lý:\n"
                "1. Đảm bảo cả 2 thư mục đều chứa các tệp MP tương ứng của cùng bộ phận.\n"
                "2. Kiểm tra quy tắc đặt tên tệp (chứa mã Cost Center 4 hoặc 10 chữ số).\n"
                "3. Bấm 'So sánh hàng loạt' lại."
            )
            messagebox.showwarning("Không tìm thấy dữ liệu ghép cặp", msg)
            return

        try:
            reports, errors = batch_analyze_variances(
                pairs,
                base_fy=2026,
                curr_fy=2027,
                thresh_pct=thresh_pct,
                thresh_abs=thresh_abs
            )
            if not reports:
                err_msg = "\n• ".join(errors[:5])
                messagebox.showwarning(
                    "Không thể phân tích dữ liệu",
                    f"Đã tìm thấy các tệp MP nhưng không thể phân tích nội dung.\n\n"
                    f"Chi tiết lỗi:\n• {err_msg}\n\n"
                    f"Cách xử lý:\n"
                    f"1. Kiểm tra các tệp bị báo lỗi theo hướng dẫn trong thông báo trên.\n"
                    f"2. Đảm bảo các tệp là báo cáo MP hợp lệ có chứa trang tính chi tiết '内訳ﾘｽﾄ(4～3月)'.\n"
                    f"3. Khắc phục lỗi trong các tệp và thực hiện lại."
                )
                return

            path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel Files", "*.xlsx")],
                initialfile="Tong_hop_bien_dong_MP.xlsx",
                title="Lưu báo cáo tổng hợp"
            )
            if path:
                from src.utils.excel_variance_writer import batch_export_variance_reports
                import re

                # Sanitize sheet names: remove invalid Excel characters like \ / * ? : [ ]
                def sanitize_sheet_name(name):
                    return re.sub(r'[\\/*?:\[\]]', '_', name)

                for r in reports:
                    r.context.cost_center_code = sanitize_sheet_name(r.context.cost_center_code)

                batch_export_variance_reports(reports, path)

                msg = f"Đã xử lý {len(reports)} phòng và lưu báo cáo tại:\n{path}"
                if errors:
                    msg += f"\n\nTuy nhiên có {len(errors)} file bị lỗi:\n" + "\n".join(errors[:3])
                    if len(errors) > 3:
                        msg += f"\n... (và {len(errors) - 3} lỗi khác)"
                if unmatched:
                    msg += f"\n\nĐã bỏ qua {len(unmatched)} file do không tìm thấy đối chiếu:\n"
                    msg += "- " + "\n- ".join(unmatched[:10])
                    if len(unmatched) > 10:
                        msg += f"\n... (và {len(unmatched) - 10} file khác)"

                messagebox.showinfo("Thành công", msg)
        except Exception as e:
            messagebox.showerror("Lỗi So Sánh Hàng Loạt", f"Đã xảy ra lỗi:\n{str(e)}")
