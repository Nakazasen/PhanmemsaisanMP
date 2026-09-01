"""Cửa sổ hiển thị chỉ đọc (presentation-only) cho Trợ lý Vận hành & Xử lý Lỗi.

Mô-đun này cung cấp OperationsAssistantDialog, nhận trực tiếp một đối tượng
OperationalCase đã được lắp ráp và ngôn ngữ đang hoạt động. Tuyệt đối không thực hiện
truy vấn CSDL, không đọc tệp từ đĩa, không can thiệp pipeline, không chạy lại tính toán.
"""

from __future__ import annotations

from typing import Any

from src.services.i18n import SUPPORTED_LANGUAGES, translate_for_language
from src.services.operations_case_service import EvidenceReference, OperationalCase


_STATUS_TRANSLATION_KEYS = {
    "SUCCEEDED": "operations_assistant_status_succeeded",
    "FAILED": "operations_assistant_status_failed",
    "PRECHECK_FAILED": "operations_assistant_status_precheck_failed",
    "SUCCEEDED_INCOMPLETE": "operations_assistant_status_succeeded_incomplete",
    "LEGACY_FY2027": "operations_assistant_status_legacy",
}

_EVIDENCE_TYPE_TRANSLATION_KEYS = {
    "catalog_row": "operations_assistant_evidence_type_catalog_row",
    "run_manifest": "operations_assistant_evidence_type_run_manifest",
    "preflight_report": "operations_assistant_evidence_type_preflight_report",
    "stage_evidence": "operations_assistant_evidence_type_stage_evidence",
    "failure_traceback": "operations_assistant_evidence_type_failure_traceback",
}

_VERIFICATION_TRANSLATION_KEYS = {
    "verified": "operations_assistant_verification_verified",
    "missing": "operations_assistant_verification_missing",
    "mismatch": "operations_assistant_verification_mismatch",
}

_CONFIDENCE_TRANSLATION_KEYS = {
    "confirmed": "operations_assistant_confidence_confirmed",
    "possible": "operations_assistant_confidence_possible",
    "unknown": "operations_assistant_confidence_unknown",
}

# Key by the parent object itself, never ``id(parent)``.  The dialog already owns
# its parent while it is alive; close and <Destroy> remove this entry promptly, so
# this registry cannot map a recycled Python id to the wrong parent.
_ACTIVE_DIALOGS: dict[Any, OperationsAssistantDialog] = {}
_NONE_PARENT_DIALOG: OperationsAssistantDialog | None = None


def _localized_run_status(status: str, language: str) -> str:
    """Chuyển đổi trạng thái lần chạy sang chuỗi bản địa hóa thân thiện."""
    key = _STATUS_TRANSLATION_KEYS.get(str(status).strip().upper(), "operations_assistant_status_unavailable")
    return translate_for_language(key, language)


def _localized_evidence_type(evidence_type: str, language: str) -> str:
    """Chuyển đổi loại bằng chứng sang chuỗi bản địa hóa."""
    key = _EVIDENCE_TYPE_TRANSLATION_KEYS.get(
        str(evidence_type).strip().lower(), "operations_assistant_evidence_type_other"
    )
    return translate_for_language(key, language)


def _localized_verification_status(verification: str, language: str) -> str:
    """Chuyển đổi trạng thái xác minh bằng chứng (verified/missing/mismatch) sang nhãn i18n."""
    key = _VERIFICATION_TRANSLATION_KEYS.get(
        str(verification).strip().lower(), "operations_assistant_verification_missing"
    )
    return translate_for_language(key, language)


def _localized_confidence(confidence: str, language: str) -> str:
    """Chuyển đổi mức độ tin cậy sang nhãn bản địa hóa."""
    key = _CONFIDENCE_TRANSLATION_KEYS.get(
        str(confidence).strip().lower(), "operations_assistant_confidence_unknown"
    )
    return translate_for_language(key, language)


def _safe_evidence_summary(summary: str, language: str) -> str:
    """Giữ chẩn đoán thô ngoài danh sách bằng chứng người dùng đọc."""
    value = str(summary or "").strip()
    raw_markers = (
        "traceback", "exception", "error:", "failed", "precheck_failed",
        "pipeline_stage_evidence", "preflight_report", "run_manifest",
        "failure_traceback", "{", "}",
    )
    if any(marker in value.lower() for marker in raw_markers):
        return translate_for_language("operations_assistant_evidence_summary_protected", language)
    return value


def _evidence_location(item: EvidenceReference) -> str:
    """Định dạng vị trí bằng chứng có sẵn trong case, không mở tệp."""
    path = str(item.local_path or "")
    locator = str(item.locator or "")
    if locator and locator != path:
        return f"{path} ({locator})"
    return path


class OperationsAssistantDialog:
    """Hộp thoại chỉ-hiển-thị cho trường hợp vận hành (OperationalCase)."""

    def __init__(
        self,
        parent: Any,
        case: OperationalCase,
        language: str,
        *,
        widget_factory: Any = None,
    ) -> None:
        # 1. Fail-closed: Kiểm tra tính hợp lệ của ngôn ngữ
        if not isinstance(language, str) or language.strip().lower() not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Ngôn ngữ '{language}' không được hỗ trợ. Phải là một trong các ngôn ngữ: "
                f"{sorted(SUPPORTED_LANGUAGES)}"
            )
        self.language = language.strip().lower()

        # 2. Fail-closed: Kiểm tra đối tượng OperationalCase
        if not isinstance(case, OperationalCase):
            raise TypeError("case phải là một đối tượng OperationalCase hợp lệ.")
        if case.presentation is None:
            raise ValueError("case.presentation không được để trống (None).")
        if case.presentation.language != self.language:
            raise ValueError(
                f"Ngôn ngữ của case.presentation ('{case.presentation.language}') "
                f"không khớp với ngôn ngữ được yêu cầu ('{self.language}')."
            )

        self.parent = parent
        self.case = case
        self.presentation = case.presentation
        self.widget_factory = widget_factory

        # 3. Chuẩn bị dữ liệu hiển thị bản địa hóa
        self.window_title = translate_for_language("operations_assistant_window_title", self.language)
        self.readonly_notice = translate_for_language("operations_assistant_readonly_notice", self.language)
        self.close_btn_text = translate_for_language("operations_assistant_close_btn", self.language)
        self.scope_title = translate_for_language("operations_assistant_section_scope", self.language)

        self.scope_labels = {
            "fiscal_year_label": translate_for_language("operations_assistant_fiscal_year_label", self.language),
            "fiscal_year_value": f"FY{case.fiscal_year}",
            "cost_center_label": translate_for_language("operations_assistant_cost_center_label", self.language),
            "cost_center_value": case.cost_center_scope,
            "status_label": translate_for_language("operations_assistant_status_label", self.language),
            "status_value": _localized_run_status(case.status, self.language),
        }

        self.section_headers = {
            "what_happened": translate_for_language("operations_assistant_section_what_happened", self.language),
            "why_it_happened": translate_for_language("operations_assistant_section_why_it_happened", self.language),
            "what_to_do": translate_for_language("operations_assistant_section_what_to_do", self.language),
            "confidence": translate_for_language("operations_assistant_section_confidence", self.language),
            "evidence": translate_for_language("operations_assistant_section_evidence", self.language),
            "technical_details": translate_for_language("operations_assistant_section_technical_details", self.language),
        }

        self.confidence_label = _localized_confidence(case.confidence, self.language)
        self.no_technical_evidence_text = translate_for_language(
            "operations_assistant_no_technical_evidence", self.language
        )

        # 4. Xây dựng giao diện (UI)
        self.window = None
        self._widgets: list[Any] = []
        self._build_ui()

        # 5. Đăng ký Singleton theo parent
        OperationsAssistantDialog._register_dialog(self.parent, self)

    @classmethod
    def open_or_focus(
        cls,
        parent: Any,
        case: OperationalCase,
        language: str,
        *,
        widget_factory: Any = None,
    ) -> OperationsAssistantDialog:
        """Mở mới hoặc chuyển tiêu điểm tới cửa sổ trợ lý của parent.

        - Chưa có cửa sổ: tạo mới.
        - Đã có cửa sổ cùng run_id và cùng ngôn ngữ: nâng lên trước và focus.
        - Đã có cửa sổ nhưng thuộc run_id khác: đóng an toàn cửa sổ cũ và mở cửa sổ mới.
        """
        active = cls._get_active_dialog(parent)
        if active is not None and active.is_alive():
            # A presentation is localized when the case is built.  Reusing it
            # after the application language changes would show a stale language.
            if active.case.run_id == case.run_id and active.language == language.strip().lower():
                active.focus()
                return active
            active.close()

        dialog = cls(parent, case, language, widget_factory=widget_factory)
        return dialog

    @classmethod
    def _get_active_dialog(cls, parent: Any) -> OperationsAssistantDialog | None:
        """Lấy dialog đang hoạt động của parent nếu còn sống."""
        global _NONE_PARENT_DIALOG
        if parent is None:
            dialog = _NONE_PARENT_DIALOG
            if dialog is not None and dialog.is_alive():
                return dialog
            _NONE_PARENT_DIALOG = None
            return None

        dialog = _ACTIVE_DIALOGS.get(parent)
        if dialog is not None and dialog.is_alive():
            return dialog
        if dialog is not None:
            _ACTIVE_DIALOGS.pop(parent, None)
        return None

    @classmethod
    def _register_dialog(cls, parent: Any, dialog: OperationsAssistantDialog) -> None:
        """Đăng ký dialog cho parent."""
        global _NONE_PARENT_DIALOG
        if parent is None:
            _NONE_PARENT_DIALOG = dialog
            return
        _ACTIVE_DIALOGS[parent] = dialog

    @classmethod
    def _unregister_dialog(cls, parent: Any, dialog: OperationsAssistantDialog) -> None:
        """Hủy đăng ký dialog khỏi parent."""
        global _NONE_PARENT_DIALOG
        if parent is None:
            if _NONE_PARENT_DIALOG is dialog:
                _NONE_PARENT_DIALOG = None
            return
        if _ACTIVE_DIALOGS.get(parent) is dialog:
            _ACTIVE_DIALOGS.pop(parent, None)

    @classmethod
    def clear_registry(cls) -> None:
        """Xóa toàn bộ registry phục vụ dọn dẹp giữa các bài test."""
        global _NONE_PARENT_DIALOG
        _ACTIVE_DIALOGS.clear()
        _NONE_PARENT_DIALOG = None

    def is_alive(self) -> bool:
        """Kiểm tra cửa sổ dialog còn tồn tại và đang hoạt động hay không."""
        if self.window is None:
            return False
        if getattr(self.window, "destroyed", False):
            return False
        if hasattr(self.window, "winfo_exists"):
            try:
                return bool(self.window.winfo_exists())
            except Exception:
                return False
        return True

    def focus(self) -> None:
        """Nâng cửa sổ lên trước và focus."""
        if not self.is_alive() or self.window is None:
            return
        if hasattr(self.window, "deiconify"):
            try:
                self.window.deiconify()
            except Exception:
                pass
        if hasattr(self.window, "lift"):
            try:
                self.window.lift()
            except Exception:
                pass
        if hasattr(self.window, "focus_force"):
            try:
                self.window.focus_force()
            except Exception:
                pass
        elif hasattr(self.window, "focus"):
            try:
                self.window.focus()
            except Exception:
                pass

    def _build_ui(self) -> None:
        """Khởi tạo các thành phần giao diện chỉ đọc."""
        if self.widget_factory is not None:
            self._build_with_custom_factory(self.widget_factory)
        else:
            self._build_with_tkinter()

    def _build_with_custom_factory(self, factory: Any) -> None:
        """Xây dựng giao diện qua fake factory phục vụ kiểm thử đơn vị độc lập."""
        self.window = factory.create_window(self.parent, title=self.window_title)
        if hasattr(self.window, "protocol"):
            try:
                self.window.protocol("WM_DELETE_WINDOW", self.close)
            except Exception:
                pass
        if hasattr(self.window, "bind"):
            try:
                self.window.bind("<Destroy>", self._on_window_destroyed)
            except Exception:
                pass
        
        # Banner cảnh báo chỉ đọc
        notice_widget = factory.create_label(
            self.window,
            text=self.readonly_notice,
            role="notice",
        )
        self._widgets.append(notice_widget)

        # Khung phạm vi hoạt động (Scope)
        scope_frame = factory.create_frame(self.window, role="scope_frame")
        for key, val in self.scope_labels.items():
            lbl = factory.create_label(scope_frame, text=val, role=key)
            self._widgets.append(lbl)
        self._widgets.append(scope_frame)

        # Tiêu đề trường hợp và các phần hướng dẫn chính
        case_title = factory.create_label(
            self.window,
            text=self.presentation.title,
            role="case_title",
        )
        self._widgets.append(case_title)

        what_happened_lbl = factory.create_label(
            self.window,
            text=f"{self.section_headers['what_happened']}: {self.presentation.what_happened}",
            role="what_happened",
        )
        self._widgets.append(what_happened_lbl)

        why_lbl = factory.create_label(
            self.window,
            text=f"{self.section_headers['why_it_happened']}: {self.presentation.why_it_happened}",
            role="why_it_happened",
        )
        self._widgets.append(why_lbl)

        # Danh sách các bước hướng dẫn
        steps_frame = factory.create_frame(self.window, role="steps_frame")
        for step in self.presentation.what_to_do:
            step_lbl = factory.create_label(steps_frame, text=step, role="guidance_step")
            self._widgets.append(step_lbl)
        self._widgets.append(steps_frame)

        # Nhãn độ tin cậy (Confidence)
        conf_lbl = factory.create_label(
            self.window,
            text=f"{self.section_headers['confidence']}: {self.confidence_label}",
            role=f"confidence_{self.case.confidence}",
        )
        self._widgets.append(conf_lbl)

        # Bảng/Danh sách bằng chứng (Evidence List)
        evidence_frame = factory.create_frame(self.window, role="evidence_frame")
        for item in self.case.evidence:
            ev_type_label = _localized_evidence_type(item.type, self.language)
            ev_status_label = _localized_verification_status(item.verification, self.language)
            ev_summary = _safe_evidence_summary(item.summary, self.language)
            ev_loc = _evidence_location(item)
            
            ev_lbl = factory.create_label(
                evidence_frame,
                text=f"[{ev_status_label}] {ev_type_label}: {ev_summary} ({ev_loc})",
                role=f"evidence_{item.type}",
            )
            self._widgets.append(ev_lbl)
        self._widgets.append(evidence_frame)

        # Vùng chi tiết kỹ thuật tách biệt (Technical Details)
        tech_frame = factory.create_frame(self.window, role="technical_details_frame")
        if self.case.evidence:
            tech_meta_lbl = factory.create_label(
                tech_frame,
                text=f"Case ID: {self.case.case_id} | Stage: {self.case.stage} | Classification: {self.case.classification}",
                role="technical_detail_meta",
            )
            self._widgets.append(tech_meta_lbl)
            for item in self.case.evidence:
                ref_lbl = factory.create_label(
                    tech_frame,
                    text=f"{item.type}: {_evidence_location(item)} -> {item.verification}",
                    role="technical_detail_ref",
                )
                self._widgets.append(ref_lbl)
        else:
            no_tech_lbl = factory.create_label(
                tech_frame,
                text=self.no_technical_evidence_text,
                role="no_technical_evidence",
            )
            self._widgets.append(no_tech_lbl)
        self._widgets.append(tech_frame)

        # Nút Đóng
        close_btn = factory.create_button(
            self.window,
            text=self.close_btn_text,
            command=self.close,
            role="close_button",
        )
        self._widgets.append(close_btn)

    def _build_with_tkinter(self) -> None:
        """Xây dựng giao diện qua Tkinter Toplevel tiêu chuẩn."""
        import tkinter as tk
        from tkinter import ttk

        self.window = tk.Toplevel(self.parent)
        self.window.title(self.window_title)
        self.window.geometry("780x640")
        self.window.minsize(640, 500)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.bind("<Destroy>", self._on_window_destroyed)

        main_frame = ttk.Frame(self.window, padding=16)
        main_frame.pack(fill="both", expand=True)

        # Banner cảnh báo chỉ đọc
        notice_lbl = ttk.Label(
            main_frame,
            text=self.readonly_notice,
            wraplength=740,
            font=("Segoe UI", 9, "italic"),
            foreground="#555555",
        )
        notice_lbl.pack(fill="x", pady=(0, 10))

        # Khung phạm vi (Scope)
        scope_frame = ttk.LabelFrame(
            main_frame,
            text=self.scope_title,
            padding=10,
        )
        scope_frame.pack(fill="x", pady=(0, 10))

        grid_frame = ttk.Frame(scope_frame)
        grid_frame.pack(fill="x")

        ttk.Label(grid_frame, text=self.scope_labels["fiscal_year_label"], font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 5))
        ttk.Label(grid_frame, text=self.scope_labels["fiscal_year_value"]).grid(row=0, column=1, sticky="w", padx=(0, 20))

        ttk.Label(grid_frame, text=self.scope_labels["cost_center_label"], font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w", padx=(0, 5))
        ttk.Label(grid_frame, text=self.scope_labels["cost_center_value"]).grid(row=0, column=3, sticky="w")

        ttk.Label(grid_frame, text=self.scope_labels["status_label"], font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", padx=(0, 5), pady=(4, 0))
        ttk.Label(grid_frame, text=self.scope_labels["status_value"]).grid(row=1, column=1, sticky="w", padx=(0, 20), pady=(4, 0))

        # Tiêu đề trường hợp
        case_title = ttk.Label(
            main_frame,
            text=self.presentation.title,
            font=("Segoe UI", 12, "bold"),
            wraplength=740,
        )
        case_title.pack(anchor="w", pady=(5, 10))

        # Nội dung chính
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True)

        ttk.Label(content_frame, text=self.section_headers["what_happened"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(content_frame, text=self.presentation.what_happened, wraplength=730).pack(anchor="w", padx=(10, 0), pady=(2, 6))

        ttk.Label(content_frame, text=self.section_headers["why_it_happened"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(content_frame, text=self.presentation.why_it_happened, wraplength=730).pack(anchor="w", padx=(10, 0), pady=(2, 6))

        ttk.Label(content_frame, text=self.section_headers["what_to_do"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        for step in self.presentation.what_to_do:
            ttk.Label(content_frame, text=step, wraplength=720).pack(anchor="w", padx=(15, 0), pady=(1, 1))

        # Độ tin cậy (Confidence)
        conf_frame = ttk.Frame(content_frame)
        conf_frame.pack(anchor="w", pady=(8, 10))
        ttk.Label(conf_frame, text=f"{self.section_headers['confidence']}: ", font=("Segoe UI", 9, "bold")).pack(side="left")
        confidence_color = {
            "confirmed": "#2e7d32",
            "possible": "#ed6c02",
            "unknown": "#d32f2f",
        }.get(self.case.confidence, "#d32f2f")
        ttk.Label(conf_frame, text=self.confidence_label, foreground=confidence_color).pack(side="left")

        # Bằng chứng (Evidence)
        ev_frame = ttk.LabelFrame(main_frame, text=self.section_headers["evidence"], padding=8)
        ev_frame.pack(fill="x", pady=(0, 10))
        for item in self.case.evidence:
            ev_type_label = _localized_evidence_type(item.type, self.language)
            ev_status_label = _localized_verification_status(item.verification, self.language)
            ev_summary = _safe_evidence_summary(item.summary, self.language)
            ev_loc = _evidence_location(item)
            status_color = "#2e7d32" if item.verification == "verified" else ("#d32f2f" if item.verification == "mismatch" else "#ed6c02")
            
            row_f = ttk.Frame(ev_frame)
            row_f.pack(fill="x", pady=1)
            ttk.Label(row_f, text=f"[{ev_status_label}]", foreground=status_color, font=("Segoe UI", 8, "bold")).pack(side="left", padx=(0, 5))
            ttk.Label(row_f, text=f"{ev_type_label}: {ev_summary} ({ev_loc})", wraplength=620).pack(side="left")

        # Vùng chi tiết kỹ thuật
        tech_frame = ttk.LabelFrame(
            main_frame,
            text=self.section_headers["technical_details"],
            padding=8,
        )
        tech_frame.pack(fill="x", pady=(0, 10))
        if self.case.evidence:
            ttk.Label(
                tech_frame,
                text=(
                    f"Case ID: {self.case.case_id} | Stage: {self.case.stage} | "
                    f"Classification: {self.case.classification}"
                ),
                wraplength=720,
            ).pack(anchor="w", pady=(0, 4))
            for item in self.case.evidence:
                ttk.Label(
                    tech_frame,
                    text=(
                        f"{item.type}: {_evidence_location(item)} -> {item.verification}\n"
                        f"{item.summary}"
                    ),
                    wraplength=720,
                ).pack(anchor="w", pady=(2, 2))
        else:
            ttk.Label(tech_frame, text=self.no_technical_evidence_text, wraplength=720).pack(anchor="w")

        # Footer với nút Đóng
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(fill="x", pady=(10, 0))

        close_btn = ttk.Button(footer_frame, text=self.close_btn_text, command=self.close)
        close_btn.pack(side="right")

    def close(self) -> None:
        """Đóng cửa sổ hộp thoại an toàn và dọn registry singleton."""
        OperationsAssistantDialog._unregister_dialog(self.parent, self)
        window = self.window
        # Clear our reference before destroying: Tk emits <Destroy> synchronously,
        # so the handler below remains idempotent instead of recursively destroying.
        self.window = None
        if window is not None:
            try:
                window.destroy()
            except Exception:
                pass

    def _on_window_destroyed(self, event: Any) -> None:
        """Drop the singleton registration when a window is destroyed externally."""
        if getattr(event, "widget", None) is not self.window:
            return
        self.window = None
        OperationsAssistantDialog._unregister_dialog(self.parent, self)
