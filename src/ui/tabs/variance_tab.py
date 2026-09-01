# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import re
from src.engine.variance_analyzer import ComparisonContext, map_and_analyze_variances, safe_load_mp_form
from src.services.i18n import (
    t,
    get_current_language,
    register_language_listener,
    unregister_language_listener,
)

class VarianceTab(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.pack(fill="both", expand=True)
        self.base_file = tk.StringVar()
        self.curr_file = tk.StringVar()
        self.threshold_pct = tk.DoubleVar(value=10.0)
        self.threshold_abs = tk.DoubleVar(value=50000000.0)
        self._build_ui()
        self._current_report = None
        register_language_listener(self._on_language_changed)
        self.bind("<Destroy>", self._on_destroy)

    def _on_destroy(self, event):
        if event.widget == self:
            unregister_language_listener(self._on_language_changed)

    def _on_language_changed(self, _lang: str):
        self.refresh_language()

    def _build_ui(self):
        self.title_lbl = ttk.Label(self, text=t("variance_tab_title"), font=("Segoe UI", 12, "bold"))
        self.title_lbl.pack(anchor="w", pady=10, padx=10)

        # Setup control frame
        self.control_frame = ttk.LabelFrame(self, text=t("variance_settings_frame"))
        self.control_frame.pack(fill="x", padx=10, pady=5)

        # File selectors
        self.lbl_base_file = ttk.Label(self.control_frame, text=t("prev_year_file_label"))
        self.lbl_base_file.grid(row=0, column=0, sticky="e", padx=5, pady=5)
        ttk.Entry(self.control_frame, textvariable=self.base_file, width=60).grid(row=0, column=1, padx=5, pady=5)
        self.btn_base_file = ttk.Button(self.control_frame, text=t("choose_file_btn"), command=lambda: self._select_file(self.base_file))
        self.btn_base_file.grid(row=0, column=2, padx=5, pady=5)

        self.lbl_curr_file = ttk.Label(self.control_frame, text=t("curr_year_file_label"))
        self.lbl_curr_file.grid(row=1, column=0, sticky="e", padx=5, pady=5)
        ttk.Entry(self.control_frame, textvariable=self.curr_file, width=60).grid(row=1, column=1, padx=5, pady=5)
        self.btn_curr_file = ttk.Button(self.control_frame, text=t("choose_file_btn"), command=lambda: self._select_file(self.curr_file))
        self.btn_curr_file.grid(row=1, column=2, padx=5, pady=5)

        # Thresholds
        thresh_frame = ttk.Frame(self.control_frame)
        thresh_frame.grid(row=2, column=0, columnspan=3, sticky="w", padx=5, pady=5)
        self.lbl_thresh = ttk.Label(thresh_frame, text=t("alert_threshold_label"))
        self.lbl_thresh.pack(side="left")
        ttk.Entry(thresh_frame, textvariable=self.threshold_pct, width=6).pack(side="left", padx=5)
        self.lbl_or = ttk.Label(thresh_frame, text=t("or_label"))
        self.lbl_or.pack(side="left")
        ttk.Entry(thresh_frame, textvariable=self.threshold_abs, width=15).pack(side="left", padx=5)
        self.lbl_vnd = ttk.Label(thresh_frame, text=t("vnd_unit"))
        self.lbl_vnd.pack(side="left")
        self.btn_compare = ttk.Button(thresh_frame, text=t("run_compare_btn"), command=self._run_comparison, style="Accent.TButton")
        self.btn_compare.pack(side="left", padx=20)
        self.btn_export = ttk.Button(thresh_frame, text=t("export_excel_btn"), command=self._export_excel)
        self.btn_export.pack(side="left", padx=5)
        self.btn_chart = ttk.Button(thresh_frame, text=t("variance_chart_btn"), command=self._show_variance_chart)
        self.btn_chart.pack(side="left", padx=5)
        self.btn_batch = ttk.Button(thresh_frame, text=t("batch_compare_btn"), command=self._run_batch_comparison)
        self.btn_batch.pack(side="left", padx=5)

        # Data Grid
        self.data_frame = ttk.Frame(self)
        self.data_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("Account", "Name", "Base", "Current", "Diff", "Pct", "Status")
        self.tree = ttk.Treeview(self.data_frame, columns=columns, show="headings")
        self.tree.heading("Account", text=t("col_account_code"))
        self.tree.heading("Name", text=t("col_item_name"))
        self.tree.heading("Base", text=t("col_prev_year"))
        self.tree.heading("Current", text=t("col_curr_year"))
        self.tree.heading("Diff", text=t("col_curr_year_diff"))
        self.tree.heading("Pct", text=t("col_pct_diff"))
        self.tree.heading("Status", text=t("col_status"))

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

    def refresh_language(self):
        try:
            top = self.winfo_toplevel()
            if isinstance(top, tk.Toplevel):
                top.title(t("variance_analysis_btn"))
        except Exception:
            pass

        if hasattr(self, "title_lbl"):
            self.title_lbl.configure(text=t("variance_tab_title"))
        if hasattr(self, "control_frame"):
            self.control_frame.configure(text=t("variance_settings_frame"))
        if hasattr(self, "lbl_base_file"):
            self.lbl_base_file.configure(text=t("prev_year_file_label"))
        if hasattr(self, "lbl_curr_file"):
            self.lbl_curr_file.configure(text=t("curr_year_file_label"))
        if hasattr(self, "btn_base_file"):
            self.btn_base_file.configure(text=t("choose_file_btn"))
        if hasattr(self, "btn_curr_file"):
            self.btn_curr_file.configure(text=t("choose_file_btn"))
        if hasattr(self, "lbl_thresh"):
            self.lbl_thresh.configure(text=t("alert_threshold_label"))
        if hasattr(self, "lbl_or"):
            self.lbl_or.configure(text=t("or_label"))
        if hasattr(self, "lbl_vnd"):
            self.lbl_vnd.configure(text=t("vnd_unit"))
        if hasattr(self, "btn_compare"):
            self.btn_compare.configure(text=t("run_compare_btn"))
        if hasattr(self, "btn_export"):
            self.btn_export.configure(text=t("export_excel_btn"))
        if hasattr(self, "btn_chart"):
            self.btn_chart.configure(text=t("variance_chart_btn"))
        if hasattr(self, "btn_batch"):
            self.btn_batch.configure(text=t("batch_compare_btn"))
        if hasattr(self, "tree"):
            self.tree.heading("Account", text=t("col_account_code"))
            self.tree.heading("Name", text=t("col_item_name"))
            self.tree.heading("Base", text=t("col_prev_year"))
            self.tree.heading("Current", text=t("col_curr_year"))
            self.tree.heading("Diff", text=t("col_curr_year_diff"))
            self.tree.heading("Pct", text=t("col_pct_diff"))
            self.tree.heading("Status", text=t("col_status"))

    def _dialog_parent(self):
        return self.winfo_toplevel()

    def _select_file(self, var):
        path = filedialog.askopenfilename(
            parent=self._dialog_parent(),
            filetypes=[(t("excel_file_type"), "*.xlsx")],
        )
        if path:
            var.set(path)

    def _run_comparison(self):
        bf = self.base_file.get().strip()
        cf = self.curr_file.get().strip()
        if not bf or not cf:
            messagebox.showwarning(
                t("variance_missing_files_title"),
                t("variance_missing_files_msg"),
                parent=self._dialog_parent(),
            )
            return

        try:
            thresh_pct = self.threshold_pct.get()
            thresh_abs = self.threshold_abs.get()
            if thresh_pct < 0 or thresh_abs < 0:
                raise ValueError(t("variance_threshold_negative_error"))
        except (tk.TclError, ValueError):
            messagebox.showwarning(
                t("variance_threshold_invalid_title"),
                t("variance_threshold_invalid_msg"),
                parent=self._dialog_parent(),
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

                status_text = t(f"variance_status_{line.status.name.lower()}")
                self.tree.insert("", "end", values=(line.account_code, line.item_name, b_str, c_str, d_str, p_str, status_text), tags=tags)

            self._current_report = report
            messagebox.showinfo(
                t("variance_compare_done_title"),
                t("variance_compare_done_msg"),
                parent=self._dialog_parent(),
            )

        except Exception as e:
            messagebox.showerror(t("variance_compare_err_title"), f"{str(e)}", parent=self._dialog_parent())

    def _export_excel(self):
        if not hasattr(self, "_current_report") or not self._current_report:
            messagebox.showwarning(
                t("variance_no_data_title"),
                t("variance_no_data_msg"),
                parent=self._dialog_parent(),
            )
            return

        path = filedialog.asksaveasfilename(
            parent=self._dialog_parent(),
            defaultextension=".xlsx",
            filetypes=[(t("excel_file_type"), "*.xlsx")],
            initialfile="Bao_cao_bien_dong_MP.xlsx"
        )
        if path:
            try:
                from src.utils.excel_variance_writer import export_variance_report
                export_variance_report(self._current_report, path)
                messagebox.showinfo(
                    t("variance_export_success_title"),
                    t("variance_export_success_msg", path=path),
                    parent=self._dialog_parent(),
                )
            except Exception as e:
                messagebox.showerror(
                    t("variance_export_err_title"),
                    t("variance_export_err_msg", error=str(e)),
                    parent=self._dialog_parent(),
                )

    def _show_variance_chart(self):
        if not self._current_report:
            messagebox.showwarning(
                t("variance_no_data_title"),
                t("variance_no_data_msg"),
                parent=self._dialog_parent(),
            )
            return

        from src.ui.variance_chart import build_variance_chart_rows, resolve_multilingual_font_path

        rows = build_variance_chart_rows(
            self._current_report.lines,
            language=get_current_language(),
        )
        if not rows:
            messagebox.showinfo(
                t("variance_chart_title"),
                t("variance_chart_no_data"),
                parent=self._dialog_parent(),
            )
            return

        try:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure
            from matplotlib.font_manager import FontProperties
            from matplotlib.ticker import FuncFormatter
        except ImportError as exc:
            messagebox.showerror(t("variance_compare_err_title"), str(exc), parent=self._dialog_parent())
            return

        chart_window = tk.Toplevel(self._dialog_parent())
        chart_window.title(t("variance_chart_title"))
        chart_window.geometry("1060x620")
        chart_window.transient(self._dialog_parent())
        chart_window.lift()
        chart_window.focus_force()

        figure = Figure(figsize=(10.5, 5.8), dpi=100)
        axes = figure.add_subplot(111)
        display_rows = list(reversed(rows))
        font_path = resolve_multilingual_font_path(language=get_current_language())
        chart_font = FontProperties(fname=str(font_path)) if font_path else FontProperties()
        positions = list(range(len(display_rows)))
        bars = axes.barh(
            positions,
            [row.amount for row in display_rows],
            color=[row.color for row in display_rows],
        )
        axes.axvline(0, color="#555555", linewidth=0.8)
        axes.set_yticks(positions, [row.label for row in display_rows], fontproperties=chart_font)
        axes.set_title(t("variance_chart_title"), fontproperties=chart_font)
        axes.set_xlabel(
            f"{t('variance_chart_axis_label')} — {t('variance_chart_legend')}",
            fontproperties=chart_font,
        )
        axes.xaxis.set_major_formatter(FuncFormatter(lambda value, _position: f"{value / 1_000_000:,.1f}M"))
        axes.grid(axis="x", linestyle="--", alpha=0.35)
        axes.set_axisbelow(True)
        for bar, row in zip(bars, display_rows):
            axes.text(
                row.amount / 2,
                bar.get_y() + bar.get_height() / 2,
                f"{row.amount / 1_000_000:+,.2f}M",
                ha="center",
                va="center",
                color="white",
                fontweight="bold",
                fontsize=9,
            )
        figure.subplots_adjust(left=0.36, right=0.96, top=0.90, bottom=0.17)

        canvas = FigureCanvasTkAgg(figure, master=chart_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)
        ttk.Label(chart_window, text=t("variance_chart_source_note")).pack(anchor="w", padx=10, pady=(0, 8))

    def _run_batch_comparison(self):
        try:
            thresh_pct = self.threshold_pct.get()
            thresh_abs = self.threshold_abs.get()
            if thresh_pct < 0 or thresh_abs < 0:
                raise ValueError(t("variance_threshold_negative_error"))
        except (tk.TclError, ValueError):
            messagebox.showwarning(
                t("variance_threshold_invalid_title"),
                t("variance_threshold_invalid_msg"),
                parent=self._dialog_parent(),
            )
            return

        base_dir = filedialog.askdirectory(
            parent=self._dialog_parent(),
            title=t("variance_batch_select_base_title"),
        )
        if not base_dir:
            return
        curr_dir = filedialog.askdirectory(
            parent=self._dialog_parent(),
            title=t("variance_batch_select_curr_title"),
        )
        if not curr_dir:
            return

        from src.engine.variance_analyzer import scan_directories_and_pair_files, batch_analyze_variances
        pairs, unmatched = scan_directories_and_pair_files(base_dir, curr_dir)
        if not pairs:
            msg = t("variance_batch_no_pairs_msg")
            messagebox.showwarning(t("variance_batch_no_pairs_title"), msg, parent=self._dialog_parent())
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
                    t("variance_batch_parse_err_title"),
                    t("variance_batch_parse_err_msg", error=err_msg),
                    parent=self._dialog_parent(),
                )
                return

            path = filedialog.asksaveasfilename(
                parent=self._dialog_parent(),
                defaultextension=".xlsx",
                filetypes=[(t("excel_file_type"), "*.xlsx")],
                initialfile="Tong_hop_bien_dong_MP.xlsx",
                title=t("variance_batch_save_title")
            )
            if path:
                from src.utils.excel_variance_writer import batch_export_variance_reports

                # Sanitize sheet names: remove invalid Excel characters like \ / * ? : [ ]
                def sanitize_sheet_name(name):
                    return re.sub(r'[\\/*?:\[\]]', '_', name)

                for r in reports:
                    r.context.cost_center_code = sanitize_sheet_name(r.context.cost_center_code)

                batch_export_variance_reports(reports, path)

                msg = t("variance_batch_success_msg", count=len(reports), path=path)
                if errors:
                    msg += f"\n\n(Errors: {len(errors)})\n" + "\n".join(errors[:3])
                if unmatched:
                    msg += f"\n\n(Unmatched: {len(unmatched)})\n" + "\n".join(unmatched[:5])

                messagebox.showinfo(t("variance_export_success_title"), msg, parent=self._dialog_parent())
        except Exception as e:
            messagebox.showerror(t("variance_batch_err_title"), f"{str(e)}", parent=self._dialog_parent())
