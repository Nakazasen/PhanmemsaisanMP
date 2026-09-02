"""Hộp thoại Cập nhật kiến thức AI theo năm tài chính (Fiscal Year RAG Knowledge Update Dialog).

Cho phép người vận hành nhập thông tin quy tắc nghiệp vụ mới, thay đổi biểu mẫu,
hoặc lỗi vận hành cho năm tài chính mới (FY2028, FY2029...) mà không sửa đổi/ghi đè tài liệu cũ.
Cung cấp xem trước trực tiếp (Live Preview) câu trả lời và trích dẫn của Chatbot,
hỗ trợ đọc cấu trúc tệp Excel tham khảo (không tự suy diễn quy tắc), và xuất bản an toàn (Fail-Closed Atomic Publish).
"""

from __future__ import annotations

from pathlib import Path
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Dict, List, Optional

from src.services.fiscal_year_knowledge_update import (
    FiscalYearUpdateItem,
    generate_update_preview,
    inspect_excel_reference_metadata,
    publish_update,
    save_draft,
    validate_update_item,
)
from src.services.i18n import SUPPORTED_LANGUAGES, translate_for_language


_ACTIVE_UPDATE_DIALOGS: Dict[Any, FiscalYearKnowledgeUpdateDialog] = {}


def apply_modern_dialog_style(window: Any) -> None:
    """Áp dụng theme sáng Windows 11 với titlebar thanh lịch và mica/acrylic an toàn."""
    try:
        import pywinstyles
        pywinstyles.apply_style(window, "mica")
        pywinstyles.change_header_color(window, color="#F1F5F9")
        pywinstyles.change_title_color(window, color="#1E293B")
    except Exception:
        pass


class FiscalYearKnowledgeUpdateDialog:
    """Hộp thoại cập nhật kiến thức AI theo năm tài chính dành cho người vận hành."""

    CHANGE_TYPES = (
        ("changed_rule", "fy_knowledge_update_type_changed_rule"),
        ("new_rule", "fy_knowledge_update_type_new_rule"),
        ("known_error", "fy_knowledge_update_type_known_error"),
        ("changed_excel_layout", "fy_knowledge_update_type_changed_excel_layout"),
        ("operational_guidance", "fy_knowledge_update_type_operational_guidance"),
    )

    def __init__(
        self,
        parent: Any,
        language: str,
        *,
        fiscal_year: str = "FY2028",
        on_published: Optional[Callable[[], None]] = None,
    ) -> None:
        self.parent = parent
        self.language = language if language in SUPPORTED_LANGUAGES else "vi"
        self.fiscal_year = fiscal_year or "FY2028"
        self.on_published = on_published
        self.excel_reference_path: Optional[Path] = None

        self._build_ui()

    @classmethod
    def open(
        cls,
        parent: Any,
        language: str,
        *,
        fiscal_year: str = "FY2028",
        on_published: Optional[Callable[[], None]] = None,
    ) -> FiscalYearKnowledgeUpdateDialog:
        active = _ACTIVE_UPDATE_DIALOGS.get(parent)
        if active is not None and active.is_alive():
            active.focus()
            return active
        dialog = cls(parent, language, fiscal_year=fiscal_year, on_published=on_published)
        _ACTIVE_UPDATE_DIALOGS[parent] = dialog
        return dialog

    def is_alive(self) -> bool:
        return hasattr(self, "window") and self.window.winfo_exists()

    def focus(self) -> None:
        if self.is_alive():
            self.window.lift()
            self.window.focus_force()

    def close(self) -> None:
        _ACTIVE_UPDATE_DIALOGS.pop(self.parent, None)
        if self.is_alive():
            self.window.destroy()

    def _t(self, key: str, **params: Any) -> str:
        return translate_for_language(key, self.language, **params)

    def _build_ui(self) -> None:
        if self.parent is not None:
            self.window = tk.Toplevel(self.parent)
        else:
            self.window = tk.Tk()

        self.window.title(self._t("fy_knowledge_update_dialog_title"))
        self.window.geometry("780x820")
        self.window.minsize(680, 640)
        self.window.configure(bg="#f8fafc")
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.bind("<Destroy>", lambda event: event.widget is self.window and _ACTIVE_UPDATE_DIALOGS.pop(self.parent, None), add="+")

        apply_modern_dialog_style(self.window)

        # 1. Header Frame
        header = tk.Frame(self.window, bg="#ffffff", height=74)
        header.pack(fill="x")
        header.pack_propagate(False)

        badge_frame = tk.Frame(header, bg="#e0f2fe", padx=8, pady=4)
        badge_frame.pack(side="left", padx=(18, 12), pady=14)
        tk.Label(badge_frame, text="✦", bg="#e0f2fe", fg="#0284c7", font=("Segoe UI", 16, "bold")).pack()

        title_block = tk.Frame(header, bg="#ffffff")
        title_block.pack(side="left", pady=12)
        tk.Label(
            title_block,
            text=self._t("fy_knowledge_update_dialog_title"),
            bg="#ffffff", fg="#0f172a", font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")
        sub_text = {
            "vi": "Bổ sung quy tắc nghiệp vụ cho năm tài chính mới mà không sửa đổi tài liệu cũ.",
            "en": "Add business rules for new fiscal years without modifying legacy records.",
            "ja": "過去の記録を変更することなく、新年度の業務ルールを登録します。",
        }.get(self.language, "Bổ sung quy tắc nghiệp vụ cho năm tài chính mới.")
        tk.Label(
            title_block,
            text=sub_text,
            bg="#ffffff", fg="#64748b", font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(2, 0))

        tk.Frame(self.window, bg="#e2e8f0", height=1).pack(fill="x")

        # 2. Scrollable Body
        body_canvas = tk.Canvas(self.window, bg="#f8fafc", highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(self.window, orient="vertical", command=body_canvas.yview)
        self.form_container = tk.Frame(body_canvas, bg="#f8fafc", padx=20, pady=14)

        canvas_window = body_canvas.create_window((0, 0), window=self.form_container, anchor="nw")
        self.form_container.bind("<Configure>", lambda e: body_canvas.configure(scrollregion=body_canvas.bbox("all")))
        body_canvas.bind("<Configure>", lambda e: body_canvas.itemconfigure(canvas_window, width=e.width))
        body_canvas.configure(yscrollcommand=scrollbar.set)

        body_canvas.pack(side="top", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Top Row: Fiscal Year & Change Type
        row_top = tk.Frame(self.form_container, bg="#f8fafc")
        row_top.pack(fill="x", pady=(0, 10))

        # FY
        col_fy = tk.Frame(row_top, bg="#f8fafc")
        col_fy.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Label(col_fy, text=self._t("fy_knowledge_update_fy_label"), bg="#f8fafc", fg="#334155", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.fy_var = tk.StringVar(value=self.fiscal_year)
        self.fy_entry = ttk.Entry(col_fy, textvariable=self.fy_var, font=("Segoe UI", 9))
        self.fy_entry.pack(fill="x", pady=(4, 0))
        self.fy_var.trace_add("write", lambda *_: self._update_preview())

        # Change Type
        col_type = tk.Frame(row_top, bg="#f8fafc")
        col_type.pack(side="left", fill="x", expand=True, padx=(8, 0))
        tk.Label(col_type, text=self._t("fy_knowledge_update_type_label"), bg="#f8fafc", fg="#334155", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.type_labels = [self._t(k) for _, k in self.CHANGE_TYPES]
        self.type_map = {self._t(k): code for code, k in self.CHANGE_TYPES}
        self.type_combobox = ttk.Combobox(col_type, values=self.type_labels, state="readonly", font=("Segoe UI", 9))
        self.type_combobox.current(0)
        self.type_combobox.pack(fill="x", pady=(4, 0))
        self.type_combobox.bind("<<ComboboxSelected>>", lambda *_: self._update_preview())

        # Multilingual Input Notebook
        self.title_vars: Dict[str, tk.StringVar] = {}
        self.title_entries: Dict[str, ttk.Entry] = {}
        self.what_changed_texts: Dict[str, tk.Text] = {}
        self.user_action_texts: Dict[str, tk.Text] = {}
        self.applies_to_vars: Dict[str, tk.StringVar] = {}
        self.applies_to_entries: Dict[str, ttk.Entry] = {}
        self.source_note_vars: Dict[str, tk.StringVar] = {}
        self.source_note_entries: Dict[str, ttk.Entry] = {}

        tab_config = (
            ("vi", "Tiếng Việt (VI)", "vi"),
            ("en", "English (EN)", "en"),
            ("ja", "日本語 (JA)", "ja"),
        )

        self.notebook = ttk.Notebook(self.form_container)
        self.notebook.pack(fill="x", pady=(4, 10))

        for lang_code, tab_label, locale_code in tab_config:
            tab_frame = tk.Frame(self.notebook, bg="#f8fafc", padx=12, pady=10)
            self.notebook.add(tab_frame, text=tab_label)

            # Title
            title_lbl = translate_for_language("fy_knowledge_update_title_label", locale_code)
            tk.Label(tab_frame, text=title_lbl, bg="#f8fafc", fg="#334155", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(2, 0))
            t_var = tk.StringVar()
            t_entry = ttk.Entry(tab_frame, textvariable=t_var, font=("Segoe UI", 9))
            t_entry.pack(fill="x", pady=(4, 6))
            t_var.trace_add("write", lambda *_: self._update_preview())
            self.title_vars[lang_code] = t_var
            self.title_entries[lang_code] = t_entry

            # What Changed
            wc_lbl = translate_for_language("fy_knowledge_update_what_changed_label", locale_code)
            tk.Label(tab_frame, text=wc_lbl, bg="#f8fafc", fg="#334155", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(2, 0))
            wc_text = tk.Text(tab_frame, height=3, font=("Segoe UI", 9), relief="solid", bd=1)
            wc_text.pack(fill="x", pady=(4, 6))
            wc_text.bind("<KeyRelease>", lambda *_: self._update_preview())
            self.what_changed_texts[lang_code] = wc_text

            # User Action
            ua_lbl = translate_for_language("fy_knowledge_update_user_action_label", locale_code)
            tk.Label(tab_frame, text=ua_lbl, bg="#f8fafc", fg="#334155", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(2, 0))
            ua_text = tk.Text(tab_frame, height=2, font=("Segoe UI", 9), relief="solid", bd=1)
            ua_text.pack(fill="x", pady=(4, 6))
            ua_text.bind("<KeyRelease>", lambda *_: self._update_preview())
            self.user_action_texts[lang_code] = ua_text

            # Applies To & Source Note Row
            row_tab_mid = tk.Frame(tab_frame, bg="#f8fafc")
            row_tab_mid.pack(fill="x", pady=(2, 4))

            col_tab_app = tk.Frame(row_tab_mid, bg="#f8fafc")
            col_tab_app.pack(side="left", fill="x", expand=True, padx=(0, 6))
            app_lbl = translate_for_language("fy_knowledge_update_applies_to_label", locale_code)
            tk.Label(col_tab_app, text=app_lbl, bg="#f8fafc", fg="#334155", font=("Segoe UI", 9)).pack(anchor="w")
            app_var = tk.StringVar()
            app_entry = ttk.Entry(col_tab_app, textvariable=app_var, font=("Segoe UI", 9))
            app_entry.pack(fill="x", pady=(4, 0))
            app_var.trace_add("write", lambda *_: self._update_preview())
            self.applies_to_vars[lang_code] = app_var
            self.applies_to_entries[lang_code] = app_entry

            col_tab_src = tk.Frame(row_tab_mid, bg="#f8fafc")
            col_tab_src.pack(side="left", fill="x", expand=True, padx=(6, 0))
            src_lbl = translate_for_language("fy_knowledge_update_source_note_label", locale_code)
            tk.Label(col_tab_src, text=src_lbl, bg="#f8fafc", fg="#334155", font=("Segoe UI", 9)).pack(anchor="w")
            src_var = tk.StringVar()
            src_entry = ttk.Entry(col_tab_src, textvariable=src_var, font=("Segoe UI", 9))
            src_entry.pack(fill="x", pady=(4, 0))
            src_var.trace_add("write", lambda *_: self._update_preview())
            self.source_note_vars[lang_code] = src_var
            self.source_note_entries[lang_code] = src_entry

        # Select tab matching current UI language
        lang_order = [cfg[0] for cfg in tab_config]
        initial_idx = lang_order.index(self.language) if self.language in lang_order else 0
        self.notebook.select(initial_idx)

        # Excel reference & Confidence Row
        row_excel_conf = tk.Frame(self.form_container, bg="#f8fafc")
        row_excel_conf.pack(fill="x", pady=(4, 8))

        # Confidence Level
        col_conf = tk.Frame(row_excel_conf, bg="#f8fafc")
        col_conf.pack(side="left", fill="x", expand=True)
        tk.Label(col_conf, text=self._t("fy_knowledge_update_confidence_label"), bg="#f8fafc", fg="#334155", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
        self.confidence_var = tk.StringVar(value="confirmed")
        rb1 = ttk.Radiobutton(col_conf, text=self._t("fy_knowledge_update_conf_confirmed"), value="confirmed", variable=self.confidence_var, command=self._update_preview)
        rb1.pack(anchor="w")
        rb2 = ttk.Radiobutton(col_conf, text=self._t("fy_knowledge_update_conf_caveat"), value="reference_with_caveat", variable=self.confidence_var, command=self._update_preview)
        rb2.pack(anchor="w", pady=(2, 0))

        # Excel Inspection
        col_excel = tk.Frame(row_excel_conf, bg="#f8fafc")
        col_excel.pack(side="right", padx=(12, 0))
        self.btn_inspect_excel = ttk.Button(col_excel, text="📊 " + self._t("fy_knowledge_update_excel_inspect_btn"), command=self._inspect_excel_file)
        self.btn_inspect_excel.pack(pady=(12, 0))

        # Superseded rule
        tk.Label(self.form_container, text=self._t("fy_knowledge_update_supersedes_label"), bg="#f8fafc", fg="#334155", font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 0))
        self.supersedes_var = tk.StringVar()
        self.supersedes_entry = ttk.Entry(self.form_container, textvariable=self.supersedes_var, font=("Segoe UI", 9))
        self.supersedes_entry.pack(fill="x", pady=(4, 10))

        # Live Preview Box
        preview_frame = tk.LabelFrame(self.form_container, text=self._t("fy_knowledge_update_preview_title"), bg="#ffffff", font=("Segoe UI", 9, "bold"), padx=10, pady=8)
        preview_frame.pack(fill="both", expand=True, pady=(6, 10))

        self.preview_text = tk.Text(preview_frame, height=5, font=("Segoe UI", 9), bg="#f8fafc", relief="flat", wrap="word", state="disabled")
        self.preview_text.pack(fill="both", expand=True)

        # 3. Bottom Action Bar
        tk.Frame(self.window, bg="#e2e8f0", height=1).pack(fill="x")
        bottom_bar = tk.Frame(self.window, bg="#ffffff", height=54, padx=20)
        bottom_bar.pack(fill="x")
        bottom_bar.pack_propagate(False)

        self.btn_close = ttk.Button(bottom_bar, text=self._t("fy_knowledge_update_cancel_btn"), command=self.close)
        self.btn_close.pack(side="right", pady=12, padx=(8, 0))

        self.btn_publish = tk.Button(
            bottom_bar,
            text="✦ " + self._t("fy_knowledge_update_publish_btn"),
            bg="#0284c7", fg="#ffffff", activebackground="#0369a1", activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4, cursor="hand2",
            command=self._handle_publish,
        )
        self.btn_publish.pack(side="right", pady=10, padx=(8, 0))

        self.btn_draft = ttk.Button(bottom_bar, text=self._t("fy_knowledge_update_save_draft_btn"), command=self._handle_save_draft)
        self.btn_draft.pack(side="right", pady=12)

        self._update_preview()

    @property
    def title_var(self) -> tk.StringVar:
        return self.title_vars.get(self.language, self.title_vars.get("vi", next(iter(self.title_vars.values()))))

    @property
    def title_entry(self) -> ttk.Entry:
        return self.title_entries.get(self.language, self.title_entries.get("vi", next(iter(self.title_entries.values()))))

    @property
    def what_changed_text(self) -> tk.Text:
        return self.what_changed_texts.get(self.language, self.what_changed_texts.get("vi", next(iter(self.what_changed_texts.values()))))

    @property
    def user_action_text(self) -> tk.Text:
        return self.user_action_texts.get(self.language, self.user_action_texts.get("vi", next(iter(self.user_action_texts.values()))))

    @property
    def applies_to_var(self) -> tk.StringVar:
        return self.applies_to_vars.get(self.language, self.applies_to_vars.get("vi", next(iter(self.applies_to_vars.values()))))

    @property
    def source_note_var(self) -> tk.StringVar:
        return self.source_note_vars.get(self.language, self.source_note_vars.get("vi", next(iter(self.source_note_vars.values()))))

    def _get_item_data(self) -> FiscalYearUpdateItem:
        selected_type_label = self.type_combobox.get()
        change_type = self.type_map.get(selected_type_label, "changed_rule")

        status_val = self.confidence_var.get()
        fy_val = self.fy_var.get().strip().upper() or "FY2028"

        supersedes_raw = self.supersedes_var.get().strip()
        supersedes_list = [s.strip() for s in re.split(r"[,;]+", supersedes_raw) if s.strip()]

        title_dict = {
            lang: self.title_vars[lang].get().strip()
            for lang in SUPPORTED_LANGUAGES
            if lang in self.title_vars
        }
        what_changed_dict = {
            lang: self.what_changed_texts[lang].get("1.0", "end").strip()
            for lang in SUPPORTED_LANGUAGES
            if lang in self.what_changed_texts
        }
        user_action_dict = {
            lang: self.user_action_texts[lang].get("1.0", "end").strip()
            for lang in SUPPORTED_LANGUAGES
            if lang in self.user_action_texts
        }
        applies_to_dict = {
            lang: self.applies_to_vars[lang].get().strip()
            for lang in SUPPORTED_LANGUAGES
            if lang in self.applies_to_vars
        }
        source_note_dict = {
            lang: self.source_note_vars[lang].get().strip()
            for lang in SUPPORTED_LANGUAGES
            if lang in self.source_note_vars
        }

        # Generate anchor: prioritize VI -> EN -> JA from what_changed, then title
        anchor = ""
        for lang_cand in SUPPORTED_LANGUAGES:
            txt = what_changed_dict.get(lang_cand, "").strip()
            if len(txt) >= 15:
                anchor = txt[:50]
                break
        if not anchor:
            for lang_cand in SUPPORTED_LANGUAGES:
                t_txt = title_dict.get(lang_cand, "").strip()
                if len(t_txt) >= 15:
                    anchor = t_txt[:50]
                    break

        slug_src = title_dict.get("vi") or title_dict.get("en") or title_dict.get("ja") or "item"
        slug = re.sub(r"[^a-zA-Z0-9_]+", "_", slug_src).strip("_").lower()
        update_id = f"upd_{fy_val.lower()}_{slug or 'item'}"

        return FiscalYearUpdateItem(
            fiscal_year=fy_val,
            update_id=update_id,
            status=status_val,
            change_type=change_type,
            business_area="cost_allocation",
            title=title_dict,
            what_changed=what_changed_dict,
            user_action=user_action_dict,
            applies_to=applies_to_dict,
            source_note=source_note_dict,
            evidence_anchor=anchor,
            replaces_or_supersedes=supersedes_list,
            is_active=True,
        )

    def _update_preview(self) -> None:
        if not hasattr(self, "preview_text"):
            return

        item = self._get_item_data()
        preview = generate_update_preview(item, self.language)

        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("end", preview["answer"])
        self.preview_text.configure(state="disabled")

    def _inspect_excel_file(self) -> None:
        file_path = filedialog.askopenfilename(
            parent=self.window,
            title="Chọn file Excel tham khảo",
            filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")],
        )
        if not file_path:
            return

        meta = inspect_excel_reference_metadata(Path(file_path))
        if "error" in meta:
            messagebox.showerror("Lỗi", meta["error"], parent=self.window)
            return

        # Show non-technical sheet summary
        lines = [f"Tệp: {meta['filename']} (Số trang tính: {meta['sheets_count']})\n"]
        for s in meta.get("sheets", []):
            headers = ", ".join(s["sample_headers"][:6]) if s["sample_headers"] else "(Trống)"
            lines.append(f"• Trang tính [{s['sheet_name']}]: Các cột chính: {headers}")

        lines.append("\n💡 Lưu ý: Hệ thống chỉ đọc tiêu đề cột để hỗ trợ ghi chú; người vận hành cần tự mô tả thay đổi nghiệp vụ bằng lời.")

        messagebox.showinfo("Cấu trúc tệp Excel", "\n".join(lines), parent=self.window)

    def _handle_save_draft(self) -> None:
        item = self._get_item_data()
        try:
            draft_file = save_draft(item)
            msg = self._t("fy_knowledge_update_draft_saved_msg", update_id=draft_file.stem)
            messagebox.showinfo(self._t("variance_compare_done_title"), msg, parent=self.window)
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không thể lưu bản nháp: {exc}", parent=self.window)

    def _handle_publish(self) -> None:
        item = self._get_item_data()
        is_valid, errors = validate_update_item(item)
        if not is_valid:
            messagebox.showwarning(
                self._t("fy_knowledge_update_validation_error_title"),
                "\n".join(f"• {e}" for e in errors),
                parent=self.window,
            )
            return

        success, message = publish_update(item)
        if success:
            msg = self._t("fy_knowledge_update_publish_success_msg", fiscal_year=item.fiscal_year)
            messagebox.showinfo(self._t("fy_knowledge_update_publish_success_title"), msg, parent=self.window)
            if self.on_published:
                try:
                    self.on_published()
                except Exception:
                    pass
            self.close()
        else:
            messagebox.showerror("Lỗi xuất bản kiến thức AI", message, parent=self.window)
