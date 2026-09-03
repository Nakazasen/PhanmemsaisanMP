"""Cửa sổ hiển thị chỉ đọc (presentation-only) cho Trợ lý Vận hành & Xử lý Lỗi (F-020).

Cung cấp OperationsAssistantDialog:
- Nhận trực tiếp đối tượng OperationalCase đã được lắp ráp và ngôn ngữ đang hoạt động.
- Cung cấp hành động "Hỏi AI nội bộ (C-AGENT)" (T035) gọi dịch vụ tư vấn nội bộ không khóa giao diện.
- Hiển thị bản dịch, phạm vi, giải thích nguyên nhân, danh sách bằng chứng và tư vấn AI.
- Tuyệt đối chỉ đọc: không sửa đổi tệp, không ghi DB/Excel, không chạy pipeline hay tự ý repair.
"""

from __future__ import annotations

from pathlib import Path
import re
import threading
import tkinter as tk
from tkinter import ttk
import unicodedata
import uuid
from typing import Any

from src.services.i18n import SUPPORTED_LANGUAGES, translate_for_language
from src.services.operations_ai_provider import (
    CagentGuidanceResult,
    CagentProviderPolicy,
)
from src.services.operations_cagent_client import request_cagent_chat_guidance, request_cagent_guidance
from src.services.operations_gemini_web import request_gemini_web_business_guidance, request_gemini_web_guidance
from src.services.operations_case_service import EvidenceReference, OperationalCase
from src.services.project_config import read_ai_provider, remember_ai_provider
from src.ui.fiscal_year_update_dialog import FiscalYearKnowledgeUpdateDialog


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

_ACTIVE_DIALOGS: dict[Any, OperationsAssistantDialog] = {}
_NONE_PARENT_DIALOG: OperationsAssistantDialog | None = None
_BUSINESS_CHAT_DIALOGS: dict[Any, OperationsBusinessChatDialog] = {}


def apply_modern_window_style(window: Any) -> None:
    """Áp dụng theme sáng Windows 11 với titlebar thanh lịch và mica/acrylic an toàn."""
    try:
        import pywinstyles
        pywinstyles.apply_style(window, "mica")
        pywinstyles.change_header_color(window, color="#F1F5F9")
        pywinstyles.change_title_color(window, color="#1E293B")
    except Exception:
        pass


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


def _business_document_context(question: str, language: str = "vi") -> str:
    """Return document-grounded, plain-text context from MP2027's RAG v3 knowledge index.

    Retrieves grounded chunks from pre-computed document index.
    Falls back to v2 catalog ONLY if v3 index is unbuilt, missing, or invalid.
    """
    from src.services.business_knowledge_index import get_knowledge_index
    from src.services.business_knowledge_retrieval import (
        format_grounded_context,
        retrieve_grounded_chunks,
    )

    index_chunks = get_knowledge_index()
    if index_chunks:
        # V3 is active and available
        chunks = retrieve_grounded_chunks(question, language)
        if chunks:
            return format_grounded_context(chunks, language, question=question)
        # V3 index is active but query found no match: do NOT fall back to V2 catalog
        no_match = {
            "vi": "Chưa tìm thấy hướng dẫn nội bộ phù hợp.",
            "en": "No matching internal MP2027 business guidance was found.",
            "ja": "該当する社内ガイダンスが見つかりません。",
        }
        lang = str(language).strip().lower() if language else "vi"
        return no_match.get(lang, no_match["vi"])

    # Fallback to curated catalog v2 ONLY when v3 index is completely unbuilt / unavailable
    from src.services.business_chat_knowledge import format_curated_context, retrieve

    results = retrieve(question, language)
    if not results:
        no_match = {
            "vi": "Chưa tìm thấy hướng dẫn nội bộ phù hợp.",
            "en": "No matching internal MP2027 business guidance was found.",
            "ja": "該当する社内ガイダンスが見つかりません。",
        }
        lang = str(language).strip().lower() if language else "vi"
        return no_match.get(lang, no_match["vi"])
    return format_curated_context(results, language)




def is_error_related_query(query: str) -> bool:
    """Kiểm tra xem câu hỏi của người dùng có đang hỏi về lỗi/sự cố/cách xử lý hay không."""
    from src.services.business_knowledge_retrieval import classify_question_intent

    return classify_question_intent(query) == "incident"


def format_nontech_case_diagnosis(case: OperationalCase, language: str = "vi") -> str:
    """Định dạng kết quả chẩn đoán sự cố hoàn toàn bằng ngôn ngữ nghiệp vụ non-tech, không hiển thị UUID hay thuật ngữ kỹ thuật phức tạp."""
    lang = str(language or "vi").strip().lower()
    fy_text = f"FY{case.fiscal_year}" if case.fiscal_year else "2027"
    cc_text = case.cost_center_scope or "tất cả"

    friendly_classifications = {
        "vi": {
            "blocked_output_file_lock": "Tệp Excel kết quả đang bị mở hoặc khóa bởi ứng dụng khác",
            "missing_staffing_baseline": "Chưa có số liệu nhân sự cơ sở (mốc tháng 3) để tính phân bổ",
            "preflight_source_validation_failure": "Tệp dữ liệu đầu vào chưa đúng mẫu hoặc thiếu trang tính",
            "unknown": "Phát sinh cảnh báo trong quá trình đọc và xử lý dữ liệu",
        },
        "en": {
            "blocked_output_file_lock": "Output Excel workbook is currently open or locked by another program",
            "missing_staffing_baseline": "Missing baseline staffing headcount (March) required for monthly allocation",
            "preflight_source_validation_failure": "Input data workbook has formatting discrepancies or missing sheets",
            "unknown": "Warning or discrepancy detected during data processing",
        },
        "ja": {
            "blocked_output_file_lock": "出力先Excelファイルが別のアプリで開かれています",
            "missing_staffing_baseline": "配賦計算に必要な期首基準月（3月）の人員データが登録されていません",
            "preflight_source_validation_failure": "入力データファイルの形式不備またはシート不足が検出されました",
            "unknown": "データ処理中に警告または不整合が検出されました",
        },
    }
    lang_dict = friendly_classifications.get(lang, friendly_classifications["vi"])
    classification_title = lang_dict.get(
        str(case.classification or "").strip(),
        str(case.classification or "Chưa phân loại"),
    )

    sections: list[str] = []

    if lang == "ja":
        sections.append(
            f"📊 【直近の実行エラー診断】\n"
            f"• 対象部門 / コストセンター: {cc_text} ({fy_text}年度)\n"
            f"• 検出された事象: {classification_title}"
        )
        if case.presentation is not None:
            if case.presentation.what_happened:
                sections.append(f"🔍 状況:\n{case.presentation.what_happened}")
            if case.presentation.why_it_happened:
                sections.append(f"💡 発生原因:\n{case.presentation.why_it_happened}")
            if case.presentation.what_to_do:
                if isinstance(case.presentation.what_to_do, (list, tuple)):
                    steps_text = "\n".join(f"  {idx+1}. {step}" for idx, step in enumerate(case.presentation.what_to_do))
                else:
                    steps_text = str(case.presentation.what_to_do)
                sections.append(f"🛠️ おすすめの対処手順:\n{steps_text}")
        elif case.summary:
            sections.append(f"🔍 概要:\n{case.summary}")

        verified_evidence = [ev for ev in case.evidence if str(ev.verification).strip().lower() == "verified"]
        if verified_evidence:
            ev_names = []
            for ev in verified_evidence[:4]:
                loc = ev.local_path or ev.summary
                name = Path(loc).name if "/" in loc or "\\" in loc else loc
                ev_names.append(f"  • {name}")
            sections.append("📁 関連ファイル:\n" + "\n".join(ev_names))

    elif lang == "en":
        sections.append(
            f"📊 【Latest Run Issue Diagnosis】\n"
            f"• Department / Cost Center: {cc_text} ({fy_text})\n"
            f"• Issue Identified: {classification_title}"
        )
        if case.presentation is not None:
            if case.presentation.what_happened:
                sections.append(f"🔍 What Happened:\n{case.presentation.what_happened}")
            if case.presentation.why_it_happened:
                sections.append(f"💡 Why It Happened:\n{case.presentation.why_it_happened}")
            if case.presentation.what_to_do:
                if isinstance(case.presentation.what_to_do, (list, tuple)):
                    steps_text = "\n".join(f"  {idx+1}. {step}" for idx, step in enumerate(case.presentation.what_to_do))
                else:
                    steps_text = str(case.presentation.what_to_do)
                sections.append(f"🛠️ Recommended Action Steps:\n{steps_text}")
        elif case.summary:
            sections.append(f"🔍 Summary:\n{case.summary}")

        verified_evidence = [ev for ev in case.evidence if str(ev.verification).strip().lower() == "verified"]
        if verified_evidence:
            ev_names = []
            for ev in verified_evidence[:4]:
                loc = ev.local_path or ev.summary
                name = Path(loc).name if "/" in loc or "\\" in loc else loc
                ev_names.append(f"  • {name}")
            sections.append("📁 Related Files:\n" + "\n".join(ev_names))

    else:
        sections.append(
            f"📊 【KẾT QUẢ CHẨN ĐOÁN SỰ CỐ GẦN NHẤT】\n"
            f"• Bộ phận / Phòng ban: {cc_text} (Năm tài chính {fy_text})\n"
            f"• Vấn đề ghi nhận: {classification_title}"
        )
        if case.presentation is not None:
            if case.presentation.what_happened:
                sections.append(f"🔍 Tình trạng thực tế:\n{case.presentation.what_happened}")
            if case.presentation.why_it_happened:
                sections.append(f"💡 Nguyên nhân nghiệp vụ:\n{case.presentation.why_it_happened}")
            if case.presentation.what_to_do:
                if isinstance(case.presentation.what_to_do, (list, tuple)):
                    steps_text = "\n".join(f"  {idx+1}. {step}" for idx, step in enumerate(case.presentation.what_to_do))
                else:
                    steps_text = str(case.presentation.what_to_do)
                sections.append(f"🛠️ Hướng dẫn các bước tự xử lý:\n{steps_text}")
        elif case.summary:
            sections.append(f"🔍 Tóm tắt:\n{case.summary}")

        verified_evidence = [ev for ev in case.evidence if str(ev.verification).strip().lower() == "verified"]
        if verified_evidence:
            ev_lines = []
            for ev in verified_evidence[:4]:
                loc = ev.local_path or ev.summary
                name = Path(loc).name if "/" in loc or "\\" in loc else loc
                ev_lines.append(f"  • {name}")
            sections.append("📁 Tệp liên quan:\n" + "\n".join(ev_lines))

    return "\n\n".join(sections)


def find_latest_error_case(
    history_root: Path | str | None,
    fiscal_year: int | None = None,
    language: str = "vi",
) -> OperationalCase | None:
    """Tự động tìm kiếm lần chạy bị lỗi hoặc cảnh báo gần nhất từ SQLite database và lắp ráp thành OperationalCase."""
    if not history_root:
        return None
    try:
        from src.services.run_history import list_runs
        from src.services.operations_case_service import assemble_operational_case

        runs = list_runs(str(history_root), fiscal_year)
        if not runs:
            return None

        error_run = next(
            (
                r for r in runs
                if str(r.get("status") or "").strip().upper() in ("FAILED", "PRECHECK_FAILED", "SUCCEEDED_INCOMPLETE")
                or bool(str(r.get("error_summary") or "").strip())
            ),
            None,
        )
        if not error_run:
            return None

        run_id = str(error_run.get("run_id") or "").strip()
        if not run_id:
            return None

        return assemble_operational_case(history_root, run_id, language)
    except Exception:
        return None


def find_relevant_error_case(
    history_root: Path | str | None,
    fiscal_year: int | None = None,
    language: str = "vi",
    question: str = "",
) -> OperationalCase | None:
    """Tìm kiếm trường hợp vận hành bị lỗi phù hợp nhất với câu hỏi trong năm tài chính được chọn."""
    from src.services.operations_case_service import find_relevant_error_case as _find_relevant_error_case

    return _find_relevant_error_case(history_root, fiscal_year, language, question)


def format_no_error_guidance(language: str = "vi") -> str:
    """Trả về thông báo xác nhận chưa tìm thấy sự cố phù hợp với câu hỏi."""
    lang = str(language or "").strip().lower()
    if lang == "ja":
        return (
            "この内容と一致する障害情報が記録に見つかりませんでした。\n"
            "画面上に表示された具体的なエラー内容をお知らせいただくか、「実行履歴」で対象の実行ログをご確認ください。"
        )
    if lang == "en":
        return (
            "No matching incident was found for this description in recent records.\n"
            "Please provide the specific on-screen error message or check the Run History to select the relevant run."
        )
    return (
        "Chưa tìm thấy sự cố hoặc lỗi phù hợp với mô tả này trong các lần chạy gần đây.\n"
        "Vui lòng cung cấp thông báo lỗi cụ thể trên màn hình hoặc kiểm tra trong mục \"Lịch sử lần chạy\" để chọn đúng lần chạy bị lỗi."
    )


def _contains_web_hallucination(text: str) -> bool:
    """Kiểm tra xem câu trả lời có chứa các hướng dẫn web sai lệch (F5, trình duyệt, đăng xuất/đăng nhập) hay không."""
    low = str(text or "").lower()
    hallucination_indicators = (
        "f5",
        "trình duyệt",
        "tải lại trang",
        "đăng xuất",
        "đăng nhập lại",
        "browser",
        "refresh the page",
        "reload the page",
        "log out",
        "login again",
        "ブラウザ",
        "ページを再読み込み",
        "ログアウト",
    )
    return any(ind in low for ind in hallucination_indicators)


class OperationsBusinessChatDialog:
    """Hộp thoại trò chuyện hỏi đáp thông minh và tư vấn nghiệp vụ MP2027."""

    def __init__(
        self,
        parent: Any,
        language: str,
        *,
        open_history: Any = None,
        history_root: Path | str | None = None,
        fiscal_year: int | None = None,
        cagent_transport: Any = None,
    ) -> None:
        self.parent = parent
        self.language = language
        self.open_history = open_history
        self.history_root = history_root
        self.fiscal_year = fiscal_year
        self.cagent_transport = cagent_transport
        self._in_progress = False
        self._attached_image = None
        self._attached_photo_image = None
        self._placeholder_text = translate_for_language("operations_business_chat_placeholder", self.language)
        self.ai_provider = read_ai_provider()
        self._provider_cagent_label = translate_for_language("operations_business_chat_provider_cagent", self.language)
        self._provider_gemini_label = translate_for_language("operations_business_chat_provider_gemini", self.language)
        self.provider_combo = None
        self.session_id = f"chat-{uuid.uuid4().hex[:12]}"
        self.conversation_history: list[dict[str, str]] = []
        self.scroll_bottom_btn = None
        self._build()

    @property
    def _placeholder_active(self) -> bool:
        if hasattr(self, "question_var"):
            return not bool(self.question_var.get().strip())
        return not bool(getattr(self, "question", None) and self.question.get().strip())

    @_placeholder_active.setter
    def _placeholder_active(self, _val: bool) -> None:
        pass

    @classmethod
    def open(
        cls,
        parent: Any,
        language: str,
        *,
        open_history: Any = None,
        history_root: Path | str | None = None,
        fiscal_year: int | None = None,
        cagent_transport: Any = None,
    ) -> OperationsBusinessChatDialog:
        active = _BUSINESS_CHAT_DIALOGS.get(parent)
        if active is not None and active.is_alive():
            if open_history is not None:
                active.open_history = open_history
            if history_root is not None:
                active.history_root = history_root
            if fiscal_year is not None:
                active.fiscal_year = fiscal_year
            if cagent_transport is not None:
                active.cagent_transport = cagent_transport
            active.focus()
            active.scroll_to_bottom()
            return active
        dialog = cls(
            parent,
            language,
            open_history=open_history,
            history_root=history_root,
            fiscal_year=fiscal_year,
            cagent_transport=cagent_transport,
        )
        _BUSINESS_CHAT_DIALOGS[parent] = dialog
        dialog.scroll_to_bottom()
        return dialog

    @classmethod
    def open_with_case(
        cls,
        parent: Any,
        language: str,
        case: OperationalCase,
        *,
        policy: CagentProviderPolicy | None = None,
        history_root: Path | str | None = None,
        open_history: Any = None,
        sync: bool = False,
    ) -> OperationsBusinessChatDialog:
        """Mở giao diện chat và tự động xử lý ngầm việc chẩn đoán sự cố lần chạy, gửi vào luồng chat."""
        dialog = cls.open(
            parent,
            language,
            open_history=open_history,
            history_root=history_root,
            fiscal_year=getattr(case, "fiscal_year", None),
        )
        dialog.diagnose_case(case, policy=policy, history_root=history_root, sync=sync)
        return dialog

    def diagnose_case(
        self,
        case: OperationalCase,
        *,
        policy: CagentProviderPolicy | None = None,
        history_root: Path | str | None = None,
        sync: bool = False,
    ) -> None:
        """Chạy ngầm quy trình chẩn đoán sự cố cho case đã chọn và đưa kết quả vào luồng chat."""
        if not isinstance(case, OperationalCase):
            return

        user_name = translate_for_language("operations_business_chat_user_name", self.language)
        ai_name = translate_for_language("operations_assistant_ai_name", self.language)

        fy_text = f"FY{case.fiscal_year}" if case.fiscal_year else "FY2027"
        cc_text = case.cost_center_scope or "ALL"
        if self.language == "ja":
            user_prompt = f"エラーの対処手順を案内してください (コストセンター: {cc_text} • {fy_text})"
            thinking_msg = f"⏳ コストセンター {cc_text} のデータを分析中..."
        elif self.language == "en":
            user_prompt = f"Request troubleshooting guidance for Cost Center: {cc_text} ({fy_text})"
            thinking_msg = f"⏳ Analyzing issue and preparing guidance for Cost Center {cc_text}..."
        else:
            user_prompt = f"Yêu cầu hướng dẫn xử lý sự cố cho Phòng ban: {cc_text} ({fy_text})"
            thinking_msg = f"⏳ Đang kiểm tra dữ liệu và phân tích sự cố cho Phòng {cc_text}..."

        self._add_message(user_name, user_prompt, assistant=False)

        self.status.configure(text="⏳ " + translate_for_language("operations_assistant_ai_in_progress", self.language))
        self._in_progress = True
        self.send_button.configure(state="disabled")
        for button in self.suggestion_buttons:
            button.configure(state="disabled")

        answer_widget = self._add_message(ai_name, thinking_msg, assistant=True)

        def worker() -> None:
          try:
            full_response = format_nontech_case_diagnosis(case, self.language)

            pol = policy if policy is not None else CagentProviderPolicy()
            if pol.enabled:
                cagent_res = request_cagent_guidance(
                    case, pol, self.language, history_root=history_root
                )
                if cagent_res.status == "ready":
                    ai_header = "✦ Tư vấn thêm từ AI nội bộ:" if self.language == "vi" else ("✦ 社内AIからのアドバイス:" if self.language == "ja" else "✦ Guidance from Internal AI:")
                    full_response += f"\n\n{ai_header}\n{cagent_res.answer}"
          except Exception:
            full_response = (
                f"⚠️ {translate_for_language('operations_assistant_unable_to_load_case', self.language)}"
            )
            status_str = _localized_run_status(case.status, self.language)

            friendly_classifications = {
                "vi": {
                    "blocked_output_file_lock": "Tệp Excel kết quả đang bị mở hoặc khóa bởi ứng dụng khác",
                    "missing_staffing_baseline": "Thiếu số liệu nhân sự cơ sở (mốc tháng 3) để tính phân bổ",
                    "preflight_source_validation_failure": "Tệp dữ liệu đầu vào chưa đúng mẫu hoặc thiếu trang tính",
                    "unknown": "Sự cố cần kiểm tra thêm dữ liệu đầu vào hoặc báo cáo xử lý",
                },
                "en": {
                    "blocked_output_file_lock": "Output Excel workbook is currently open or locked by another app",
                    "missing_staffing_baseline": "Missing baseline headcount data (March) for monthly cost allocation",
                    "preflight_source_validation_failure": "Input data workbook has formatting errors or missing sheets",
                    "unknown": "Unclassified issue (check input files or processing reports)",
                },
                "ja": {
                    "blocked_output_file_lock": "出力先Excelファイルが別のアプリで開かれています",
                    "missing_staffing_baseline": "配賦計算に必要な期首基準月（3月）の人員データが不足しています",
                    "preflight_source_validation_failure": "入力データファイルの形式不備またはシート不足が検出されました",
                    "unknown": "未特定の事象（入力ファイルまたは処理レポートをご確認ください）",
                },
            }
            lang_dict = friendly_classifications.get(self.language, friendly_classifications["vi"])
            classification_title = lang_dict.get(
                str(case.classification or "").strip(),
                str(case.classification or "Chưa phân loại"),
            )

            sections: list[str] = []
            if self.language == "vi":
              sections.append(
                  f"📊 KẾT QUẢ PHÂN TÍCH LẦN CHẠY [{case.run_id}]\n"
                  f"• Kỳ tài chính: {fy_text} | Bộ phận / Phòng ban: {cc_text}\n"
                  f"• Trạng thái xử lý: {status_str}\n"
                  f"• Vấn đề ghi nhận: {classification_title}"
              )

              if case.presentation is not None:
                if case.presentation.what_happened:
                  sections.append(
                      f"🔍 Tình trạng thực tế:\n{case.presentation.what_happened}"
                  )
                if case.presentation.why_it_happened:
                  sections.append(
                      f"💡 Lý do phát sinh:\n{case.presentation.why_it_happened}"
                  )
                if case.presentation.what_to_do:
                  if isinstance(case.presentation.what_to_do, (list, tuple)):
                    steps_text = "\n".join(
                        f"  {idx+1}. {step}"
                        for idx, step in enumerate(case.presentation.what_to_do)
                    )
                  else:
                    steps_text = str(case.presentation.what_to_do)
                  sections.append(
                      f"🛠️ Hướng dẫn các bước tự xử lý:\n{steps_text}"
                  )
              elif case.summary:
                sections.append(f"🔍 Tóm tắt:\n{case.summary}")

              # Báo cáo & tệp liên quan
              verified_evidence = [
                  ev
                  for ev in case.evidence
                  if str(ev.verification).strip().lower() == "verified"
              ]
              if verified_evidence:
                ev_lines = []
                for ev in verified_evidence[:5]:
                  ev_loc = ev.local_path or ev.summary
                  ev_name = (
                      Path(ev_loc).name
                      if "/" in ev_loc or "\\" in ev_loc
                      else ev_loc
                  )
                  ev_lines.append(f"  • {ev_name}")
                sections.append(
                    "📁 Báo cáo & tệp liên quan:\n" + "\n".join(ev_lines)
                )

              # AI Provider Guidance
              ai_text = ""
              pol = policy if policy is not None else CagentProviderPolicy()
              if pol.enabled:
                cagent_res = request_cagent_guidance(
                    case, pol, self.language, history_root=history_root
                )
                if cagent_res.status == "ready":
                  ai_text = (
                      f"✦ Tư vấn từ AI nội bộ (C-AGENT):\n{cagent_res.answer}"
                  )
                  if cagent_res.limitation:
                    ai_text += f"\n[{cagent_res.limitation}]"
                elif cagent_res.limitation:
                  ai_text = f"✦ Lưu ý từ AI: {cagent_res.limitation}"

              if ai_text:
                sections.append(ai_text)

            elif self.language == "ja":
              sections.append(
                  f"📊 実行分析結果 [{case.run_id}]\n"
                  f"• 会計年度: {fy_text} | コストセンター: {cc_text}\n"
                  f"• 処理状態: {status_str}\n"
                  f"• 検出事象: {classification_title}"
              )
              if case.presentation is not None:
                if case.presentation.what_happened:
                  sections.append(
                      f"🔍 実際の状況:\n{case.presentation.what_happened}"
                  )
                if case.presentation.why_it_happened:
                  sections.append(
                      f"💡 発生原因:\n{case.presentation.why_it_happened}"
                  )
                if case.presentation.what_to_do:
                  if isinstance(case.presentation.what_to_do, (list, tuple)):
                    steps_text = "\n".join(
                        f"  {idx+1}. {step}"
                        for idx, step in enumerate(case.presentation.what_to_do)
                    )
                  else:
                    steps_text = str(case.presentation.what_to_do)
                  sections.append(f"🛠️ 対処手順:\n{steps_text}")
              elif case.summary:
                sections.append(f"🔍 概要:\n{case.summary}")

              # 関連レポート＆ファイル
              verified_evidence = [
                  ev
                  for ev in case.evidence
                  if str(ev.verification).strip().lower() == "verified"
              ]
              if verified_evidence:
                ev_lines = []
                for ev in verified_evidence[:5]:
                  ev_loc = ev.local_path or ev.summary
                  ev_name = Path(ev_loc).name if "/" in ev_loc or "\\" in ev_loc else ev_loc
                  ev_lines.append(f"  • {ev_name}")
                sections.append("📁 関連ファイル＆レポート:\n" + "\n".join(ev_lines))

              pol = policy if policy is not None else CagentProviderPolicy()
              if pol.enabled:
                cagent_res = request_cagent_guidance(
                    case, pol, self.language, history_root=history_root
                )
                if cagent_res.status == "ready":
                  sections.append(f"✦ 社内AIからのアドバイス:\n{cagent_res.answer}")

            else:
              sections.append(
                  f"📊 RUN ANALYSIS RESULTS [{case.run_id}]\n"
                  f"• Scope: {fy_text} | Department / CC: {cc_text}\n"
                  f"• Status: {status_str}\n"
                  f"• Issue: {classification_title}"
              )
              if case.presentation is not None:
                if case.presentation.what_happened:
                  sections.append(
                      f"🔍 What happened:\n{case.presentation.what_happened}"
                  )
                if case.presentation.why_it_happened:
                  sections.append(
                      f"💡 Why it happened:\n{case.presentation.why_it_happened}"
                  )
                if case.presentation.what_to_do:
                  if isinstance(case.presentation.what_to_do, (list, tuple)):
                    steps_text = "\n".join(
                        f"  {idx+1}. {step}"
                        for idx, step in enumerate(case.presentation.what_to_do)
                    )
                  else:
                    steps_text = str(case.presentation.what_to_do)
                  sections.append(f"🛠️ Suggested Next Steps:\n{steps_text}")
              elif case.summary:
                sections.append(f"🔍 Summary:\n{case.summary}")

              # Related Reports & Files
              verified_evidence = [
                  ev
                  for ev in case.evidence
                  if str(ev.verification).strip().lower() == "verified"
              ]
              if verified_evidence:
                ev_lines = []
                for ev in verified_evidence[:5]:
                  ev_loc = ev.local_path or ev.summary
                  ev_name = Path(ev_loc).name if "/" in ev_loc or "\\" in ev_loc else ev_loc
                  ev_lines.append(f"  • {ev_name}")
                sections.append("📁 Related Reports & Files:\n" + "\n".join(ev_lines))

              pol = policy if policy is not None else CagentProviderPolicy()
              if pol.enabled:
                cagent_res = request_cagent_guidance(
                    case, pol, self.language, history_root=history_root
                )
                if cagent_res.status == "ready":
                  sections.append(
                      f"✦ Advisory from Internal AI:\n{cagent_res.answer}"
                  )

            full_response = "\n\n".join(sections)
          except Exception:
            full_response = (
                f"⚠️ {translate_for_language('operations_assistant_unable_to_load_case', self.language)}"
            )

          def apply_diagnosis() -> None:
            if not self.is_alive():
              return
            self._in_progress = False
            self.send_button.configure(state="normal")
            for button in self.suggestion_buttons:
              button.configure(state="normal")
            self.status.configure(text="")
            answer_widget.configure(text=full_response)
            try:
              self.window.update_idletasks()
              self.message_canvas.yview_moveto(1.0)
            except Exception:
              pass

          if sync:
            apply_diagnosis()
          else:
            try:
              if self.is_alive():
                self.window.after(0, apply_diagnosis)
            except Exception:
              pass

        if sync:
          worker()
        else:
          t = threading.Thread(target=worker, daemon=True)
          self._current_thread = t
          t.start()

    def is_alive(self) -> bool:
        try:
            return bool(self.window.winfo_exists())
        except Exception:
            return False

    def focus(self) -> None:
        if not self.is_alive():
            return
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()

    def close(self) -> None:
        if _BUSINESS_CHAT_DIALOGS.get(self.parent) is self:
            _BUSINESS_CHAT_DIALOGS.pop(self.parent, None)
        if self.is_alive():
            self.window.destroy()

    def scroll_to_bottom(self) -> None:
        """Cuộn nhanh xuống tin nhắn mới nhất ở đáy khung chat."""
        if not self.is_alive():
            return
        try:
            self.window.update_idletasks()
            self.message_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _build(self) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.window = tk.Toplevel(self.parent)
        self.window.title(translate_for_language("operations_business_chat_title", self.language))
        self.window.geometry("780x620")
        self.window.minsize(640, 500)
        self.window.configure(bg="#f8fafc")
        # Không dùng transient() hay grab_set() vì chúng can thiệp vào
        # cách Windows chuyển tiếp WM_CHAR/WM_IME_CHAR của Unikey/EVKey,
        # gây lỗi nuốt dấu tiếng Việt trên cửa sổ Toplevel.
        self.window.lift()
        self.window.focus_force()
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.bind("<Destroy>", lambda event: event.widget is self.window and _BUSINESS_CHAT_DIALOGS.pop(self.parent, None), add="+")

        apply_modern_window_style(self.window)

        # 1. Header cao cấp Light Fluent
        header = tk.Frame(self.window, bg="#ffffff", height=78)
        header.pack(fill="x")
        header.pack_propagate(False)

        badge_frame = tk.Frame(header, bg="#e0f2fe", padx=8, pady=4)
        badge_frame.pack(side="left", padx=(20, 14), pady=16)
        tk.Label(badge_frame, text="✦", bg="#e0f2fe", fg="#0284c7", font=("Segoe UI", 18, "bold")).pack()

        title_block = tk.Frame(header, bg="#ffffff")
        title_block.pack(side="left", pady=14)
        tk.Label(
            title_block,
            text=translate_for_language("operations_business_chat_title", self.language),
            bg="#ffffff", fg="#0f172a", font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title_block,
            text=translate_for_language("operations_business_chat_subtitle", self.language),
            bg="#ffffff", fg="#64748b", font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(2, 0))

        # Nút Cập nhật kiến thức AI theo năm tài chính
        btn_fy_update = ttk.Button(
            header,
            text="✨ " + translate_for_language("fy_knowledge_update_btn", self.language),
            command=self._open_fy_knowledge_update,
        )
        btn_fy_update.pack(side="right", padx=(8, 20), pady=20)

        # Bộ chọn nguồn AI chuyển đổi song song (C-Agent / Gemini Web)
        provider_frame = tk.Frame(header, bg="#ffffff")
        provider_frame.pack(side="right", padx=(0, 10), pady=20)

        tk.Label(
            provider_frame,
            text=translate_for_language("operations_business_chat_provider_label", self.language),
            bg="#ffffff",
            fg="#475569",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(0, 6))

        init_val = self._provider_cagent_label if self.ai_provider == "cagent" else self._provider_gemini_label
        self.provider_var = tk.StringVar(value=init_val)
        self.provider_combo = ttk.Combobox(
            provider_frame,
            textvariable=self.provider_var,
            values=[self._provider_cagent_label, self._provider_gemini_label],
            state="readonly",
            width=18,
            font=("Segoe UI", 9),
        )
        self.provider_combo.pack(side="left")
        self.provider_combo.bind("<<ComboboxSelected>>", self._on_provider_selected)

        # Đường viền phân cách dưới header
        border_line = tk.Frame(self.window, bg="#e2e8f0", height=1)
        border_line.pack(fill="x")

        # 2. Vùng thân hộp thoại (Chat Thread Stream)
        body = tk.Frame(self.window, bg="#f8fafc")
        body.pack(fill="both", expand=True, padx=20, pady=(16, 16))

        thread_shell = tk.Frame(body, bg="#f8fafc")
        thread_shell.pack(fill="both", expand=True)

        self.message_canvas = tk.Canvas(
            thread_shell, bg="#f8fafc", highlightthickness=0, bd=0,
        )
        thread_scroll = ttk.Scrollbar(
            thread_shell, orient="vertical", command=self.message_canvas.yview,
        )
        self.messages = tk.Frame(self.message_canvas, bg="#f8fafc")
        self._message_canvas_window = self.message_canvas.create_window((0, 0), window=self.messages, anchor="nw")

        self.messages.bind(
            "<Configure>",
            lambda _event: self.message_canvas.configure(scrollregion=self.message_canvas.bbox("all")),
        )
        self.message_canvas.bind(
            "<Configure>",
            lambda event: self.message_canvas.itemconfigure(self._message_canvas_window, width=event.width),
        )
        self.message_canvas.configure(yscrollcommand=thread_scroll.set)
        self.message_canvas.pack(side="left", fill="both", expand=True)
        thread_scroll.pack(side="right", fill="y")

        def _on_mousewheel(event: Any) -> None:
            try:
                self.message_canvas.yview_scroll(-int(event.delta / 120), "units")
            except Exception:
                pass

        self.message_canvas.bind("<MouseWheel>", _on_mousewheel, add="+")
        self.messages.bind("<MouseWheel>", _on_mousewheel, add="+")

        # Tin nhắn chào mừng ban đầu
        self._add_message(
            translate_for_language("operations_assistant_ai_name", self.language),
            translate_for_language("operations_business_chat_welcome_msg", self.language),
            assistant=True,
        )

        # 3. Gợi ý câu hỏi nhanh (Pill Chips)
        starter_frame = tk.Frame(self.messages, bg="#f8fafc")
        starter_frame.pack(fill="x", pady=(12, 10), anchor="w")

        tk.Label(
            starter_frame,
            text=translate_for_language("operations_business_chat_suggestions_header", self.language),
            bg="#f8fafc", fg="#64748b", font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        starter_row = tk.Frame(starter_frame, bg="#f8fafc")
        starter_row.pack(anchor="w")

        if self.language == "ja":
            prompts = (
                ("🔍 このエラーは何ですか？", "このエラーの原因と対処法は何ですか？"),
                ("🛠️ ファイルロックの解除方法は？", "出力先Excelファイルがロックされた場合の対処方法は？"),
                ("📊 期首人員データ不足の対処は？", "期首基準月（3月）の人員データ不足はどう登録しますか？"),
                ("📋 事前検証の手順は？", "入力データソースの事前検証手順を教えてください。"),
            )
        elif self.language == "en":
            prompts = (
                ("🔍 What is this error?", "What does this error mean?"),
                ("🛠️ How to fix locked file?", "How to resolve locked output Excel file issue?"),
                ("📊 Missing baseline staffing?", "How to fix missing March baseline headcount?"),
                ("📋 Source preflight process?", "What is the preflight source data verification process?"),
            )
        else:
            prompts = (
                ("🔍 Lỗi này là gì?", "Lỗi này là gì?"),
                ("🛠️ Xử lý file bị khóa thế nào?", "Lỗi file kết quả bị khóa xử lý thế nào?"),
                ("📊 Chưa có số nhân sự tháng 3?", "Chưa có số nhân sự tháng 3 thì cần làm gì?"),
                ("📋 Quy trình kiểm tra nguồn?", "Quy trình kiểm tra tính hợp lệ của dữ liệu nguồn đầu vào?"),
            )

        self.suggestion_buttons: list[Any] = []
        for label_text, prompt_val in prompts:
            chip_btn = tk.Button(
                starter_row,
                text=label_text,
                command=lambda value=prompt_val: self._use_suggestion(value),
                bg="#ffffff", fg="#0369a1", activebackground="#f0f9ff",
                activeforeground="#0284c7", bd=1, relief="solid",
                highlightthickness=0, padx=12, pady=5,
                font=("Segoe UI", 9), cursor="hand2",
            )
            chip_btn.configure(highlightbackground="#cbd5e1")
            chip_btn.pack(side="left", padx=(0, 8), pady=2)
            self.suggestion_buttons.append(chip_btn)

        # 4. Trạng thái phản hồi & Nhãn gợi ý nhập liệu
        status_row = tk.Frame(body, bg="#f8fafc")
        status_row.pack(fill="x", pady=(2, 4))
        self.status = tk.Label(status_row, text="", bg="#f8fafc", fg="#2563eb", font=("Segoe UI", 9, "italic"))
        self.status.pack(side="left")

        # Nút bấm cuộn nhanh xuống tin nhắn mới nhất
        scroll_btn_text = f"⬇ {translate_for_language('operations_business_chat_scroll_bottom', self.language)}"
        self.scroll_bottom_btn = tk.Button(
            status_row,
            text=scroll_btn_text,
            command=self.scroll_to_bottom,
            bg="#f1f5f9",
            fg="#1e293b",
            activebackground="#e2e8f0",
            activeforeground="#0f172a",
            bd=1,
            relief="solid",
            highlightthickness=0,
            padx=8,
            pady=1,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
        )
        self.scroll_bottom_btn.configure(highlightbackground="#cbd5e1")
        self.scroll_bottom_btn.pack(side="right", padx=(8, 0))

        self.prompt_label = tk.Label(
            status_row,
            text="💬 " + self._placeholder_text,
            bg="#f8fafc",
            fg="#64748b",
            font=("Segoe UI", 9),
        )
        self.prompt_label.pack(side="right")

        # 5. Thanh xem trước ảnh đính kèm (Clipboard Image Preview Bar)
        self.image_preview_bar = tk.Frame(
            body, bg="#e0f2fe", padx=10, pady=6, highlightbackground="#bae6fd", highlightthickness=1
        )
        self.image_thumbnail_lbl = tk.Label(self.image_preview_bar, bg="#e0f2fe")
        self.image_thumbnail_lbl.pack(side="left", padx=(0, 8))
        self.image_preview_lbl = tk.Label(
            self.image_preview_bar,
            text="",
            bg="#e0f2fe",
            fg="#0369a1",
            font=("Segoe UI", 9, "bold"),
        )
        self.image_preview_lbl.pack(side="left", fill="x", expand=True)
        tk.Button(
            self.image_preview_bar,
            text="✕",
            command=self._remove_attached_image,
            bg="#e0f2fe",
            fg="#dc2626",
            activebackground="#e0f2fe",
            activeforeground="#b91c1c",
            bd=0,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
        ).pack(side="right", padx=(4, 0))

        # 6. Khung soạn thảo nổi bật (Floating Composer Card)
        self.composer = ttk.Frame(body)
        self.composer.pack(fill="x")

        # Ô nhập liệu trực tiếp - Sử dụng ttk.Entry chuẩn Windows với StringVar
        self.question_var = tk.StringVar()
        self.question = ttk.Entry(
            self.composer,
            textvariable=self.question_var,
            font=("Segoe UI", 11),
        )
        self.question.placeholder_text = self._placeholder_text
        self.question.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=6)

        self.question.bind("<Return>", lambda _e: self.send())
        self.question.bind("<Control-a>", self._select_all_text)
        self.question.bind("<Control-A>", self._select_all_text)
        self.question.bind("<Control-v>", self._handle_paste)
        self.question.bind("<Control-V>", self._handle_paste)
        self.window.bind("<Control-v>", self._handle_paste, add="+")
        self.window.bind("<Control-V>", self._handle_paste, add="+")

        # Nút gửi câu hỏi
        send_btn_text = f"➤  {translate_for_language('operations_business_chat_send', self.language)}"
        self.send_button = ttk.Button(
            self.composer,
            text=send_btn_text,
            command=self.send,
            style="Primary.TButton",
        )
        self.send_button.pack(side="right", fill="y", pady=6)

        hints_row = tk.Frame(body, bg="#f8fafc")
        hints_row.pack(fill="x", pady=(2, 0))

        self.gemini_disclosure_label = tk.Label(
            hints_row,
            text=translate_for_language("operations_business_chat_gemini_disclosure", self.language),
            bg="#f8fafc",
            fg="#64748b",
            font=("Segoe UI", 8),
            wraplength=420,
            justify="left",
        )
        self.gemini_disclosure_label.pack(side="left")

        self.paste_hint_label = tk.Label(
            hints_row,
            text=translate_for_language("operations_business_chat_paste_image_hint", self.language),
            bg="#f8fafc",
            fg="#0284c7",
            font=("Segoe UI", 8),
            justify="right",
        )
        self.paste_hint_label.pack(side="right")

        # 7. Nút chuyển nhanh sang Lịch sử lần chạy
        footer_row = tk.Frame(body, bg="#f8fafc")
        footer_row.pack(fill="x", pady=(8, 0))

        tk.Button(
            footer_row,
            text=f"⏱  {translate_for_language('operations_business_chat_open_history', self.language)}",
            command=self._open_history,
            bg="#f8fafc",
            fg="#0284c7",
            activebackground="#f8fafc",
            activeforeground="#0369a1",
            bd=0,
            font=("Segoe UI", 9, "underline"),
            cursor="hand2",
        ).pack(side="left")

        self.question.focus_set()
        self.window.after(100, self.scroll_to_bottom)

    def _handle_paste(self, _event: Any = None) -> str | None:
        try:
            from PIL import ImageGrab, Image
            data = ImageGrab.grabclipboard()
            img = None
            if isinstance(data, Image.Image):
                img = data
            elif isinstance(data, list) and data:
                path_str = str(data[0])
                if any(path_str.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif")):
                    img = Image.open(path_str)

            if img is not None:
                self._set_attached_image(img)
                return "break"
        except Exception:
            pass
        return None

    def _set_attached_image(self, img: Any) -> None:
        try:
            from PIL import ImageTk
            self._attached_image = img
            thumb = img.copy()
            thumb.thumbnail((64, 40))
            self._attached_photo_image = ImageTk.PhotoImage(thumb)
            self.image_thumbnail_lbl.configure(image=self._attached_photo_image)
            dim_text = f"{img.width}×{img.height}"
            self.image_preview_lbl.configure(
                text=f"{translate_for_language('operations_business_chat_image_attached', self.language)} ({dim_text})"
            )
            self.image_preview_bar.pack(fill="x", pady=(0, 6), before=self.composer)
        except Exception:
            self._remove_attached_image()

    def _remove_attached_image(self) -> None:
        self._attached_image = None
        self._attached_photo_image = None
        try:
            self.image_preview_bar.pack_forget()
        except Exception:
            pass

    def _copy_message_text(self, text_widget: Any, button: Any) -> None:
        try:
            text_content = text_widget.cget("text")
            self.window.clipboard_clear()
            self.window.clipboard_append(text_content)
            copied_text = f"✓ {translate_for_language('operations_business_chat_copied', self.language)}"
            orig_text = f"📋 {translate_for_language('operations_business_chat_copy', self.language)}"
            button.configure(text=copied_text, fg="#16a34a")
            self.window.after(1800, lambda: button.winfo_exists() and button.configure(text=orig_text, fg="#64748b"))
        except Exception:
            pass

    def _on_input_focus_in(self, _event: Any = None) -> None:
        pass

    def _on_input_focus_out(self, _event: Any = None) -> None:
        pass

    def _select_all_text(self, _event: Any = None) -> str:
        try:
            self.question.select_range(0, tk.END)
            self.question.icursor(tk.END)
        except Exception:
            pass
        return "break"

    def _add_message(self, sender: str, message: str, *, assistant: bool, attached_image: Any = None) -> Any:
        import tkinter as tk

        row = tk.Frame(self.messages, bg="#f8fafc")
        row.pack(fill="x", pady=6, anchor="w")

        if assistant:
            bubble_bg, name_fg, side = "#ffffff", "#2563eb", "left"
            border_color = "#e2e8f0"
            text_fg = "#1e293b"
            pad_tuple = (0, 80)
        else:
            bubble_bg, name_fg, side = "#e0f2fe", "#0369a1", "right"
            border_color = "#bae6fd"
            text_fg = "#0c4a6e"
            pad_tuple = (80, 0)

        bubble = tk.Frame(row, bg=bubble_bg, highlightbackground=border_color, highlightthickness=1)
        bubble.pack(side=side, padx=pad_tuple)

        header_row = tk.Frame(bubble, bg=bubble_bg)
        header_row.pack(fill="x", padx=14, pady=(10, 3))

        tk.Label(
            header_row, text=sender, bg=bubble_bg, fg=name_fg, font=("Segoe UI", 9, "bold"),
        ).pack(side="left")

        # Nút sao chép câu trả lời cho phản hồi của AI Assistant
        copy_btn = None
        if assistant:
            copy_btn = tk.Button(
                header_row,
                text=f"📋 {translate_for_language('operations_business_chat_copy', self.language)}",
                bg=bubble_bg,
                fg="#64748b",
                activebackground=bubble_bg,
                activeforeground="#0284c7",
                bd=0,
                font=("Segoe UI", 8),
                cursor="hand2",
            )
            copy_btn.pack(side="right")

        # Nếu có ảnh đính kèm từ người dùng, hiển thị thumbnail trong bubble
        if attached_image is not None:
            try:
                from PIL import ImageTk
                user_thumb = attached_image.copy()
                user_thumb.thumbnail((160, 100))
                user_photo = ImageTk.PhotoImage(user_thumb)
                img_lbl = tk.Label(bubble, image=user_photo, bg=bubble_bg)
                img_lbl.image = user_photo
                img_lbl.pack(anchor="w", padx=14, pady=(2, 4))
            except Exception:
                pass

        text_widget = tk.Label(
            bubble,
            text=message,
            bg=bubble_bg,
            fg=text_fg,
            justify="left",
            wraplength=580,
            font=("Segoe UI", 10),
        )
        text_widget.pack(anchor="w", padx=14, pady=(0, 11))

        if copy_btn is not None:
            copy_btn.configure(
                command=lambda b=copy_btn, tw=text_widget: self._copy_message_text(tw, b)
            )

        try:
            self.window.update_idletasks()
            self.message_canvas.yview_moveto(1.0)
        except Exception:
            pass
        return text_widget

    def _on_provider_selected(self, event: Any = None) -> None:
        val = self.provider_var.get() if hasattr(self, "provider_var") else ""
        if val == self._provider_gemini_label:
            self.ai_provider = "gemini_web"
        else:
            self.ai_provider = "cagent"
        remember_ai_provider(self.ai_provider)

    def _use_suggestion(self, prompt: str, *, sync: bool = False) -> None:
        self.question_var.set(prompt)
        self.send(sync=sync)

    def _open_history(self) -> None:
        self.close()
        self.open_history()

    def send(self, *, sync: bool = False) -> None:
        raw_text = self.question_var.get() if hasattr(self, "question_var") else self.question.get()
        question = unicodedata.normalize("NFC", raw_text).strip()
        attached_img = getattr(self, "_attached_image", None)

        if not question and attached_img is not None:
            question = translate_for_language("operations_business_chat_image_attached", self.language)

        if not question or self._in_progress:
            return

        self._remove_attached_image()
        self._in_progress = True
        self.send_button.configure(state="disabled")
        for button in self.suggestion_buttons:
            button.configure(state="disabled")

        self.status.configure(text="⏳ " + translate_for_language("operations_assistant_ai_in_progress", self.language))
        user_name = translate_for_language("operations_business_chat_user_name", self.language)
        active_provider = getattr(self, "ai_provider", "cagent")
        provider_name = self._provider_cagent_label if active_provider == "cagent" else self._provider_gemini_label
        ai_name = f"✦ {provider_name}"
        analyzing_msg = translate_for_language("operations_business_chat_analyzing", self.language)
        self._add_message(user_name, question, assistant=False, attached_image=attached_img)
        self.answer = self._add_message(ai_name, analyzing_msg, assistant=True)

        if hasattr(self, "question_var"):
            self.question_var.set("")
        else:
            self.question.delete(0, "end")

        # Ghi nhận lượt câu hỏi vào lịch sử đối thoại
        self.conversation_history.append({"role": "user", "content": question})
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

        history_snapshot = [dict(t) for t in self.conversation_history[:-1]]

        if sync:
            self._request(question, None, attached_img, history=history_snapshot, sync=True)
        else:
            t = threading.Thread(
                target=self._request,
                args=(question, None, attached_img),
                kwargs={"history": history_snapshot},
                daemon=True,
            )
            self._current_thread = t
            t.start()

    def _request(
        self,
        question: str,
        context: str | None = None,
        attached_image: Any = None,
        *,
        history: list[dict[str, str]] | None = None,
        sync: bool = False,
    ) -> None:
        if context is None:
            retrieval_query = question
            if history:
                prev_user_queries = [t["content"] for t in history if t.get("role") == "user"]
                if prev_user_queries and len(question.strip().split()) <= 6:
                    retrieval_query = f"{prev_user_queries[-1]} {question}"
            context = _business_document_context(retrieval_query, self.language)

        from src.services.business_knowledge_retrieval import classify_question_intent

        intent = classify_question_intent(question, self.language)
        case_diagnosis = ""

        if intent == "incident":
            relevant_case = None
            if getattr(self, "history_root", None):
                try:
                    relevant_case = find_relevant_error_case(
                        self.history_root,
                        getattr(self, "fiscal_year", None),
                        self.language,
                        question=question,
                    )
                except Exception:
                    relevant_case = None
            if relevant_case is not None:
                case_diagnosis = format_nontech_case_diagnosis(relevant_case, self.language)
            else:
                case_diagnosis = format_no_error_guidance(self.language)

        full_context = f"{case_diagnosis}\n\n{context}" if case_diagnosis else context
        if attached_image is not None:
            img_notice = f"[{translate_for_language('operations_business_chat_image_attached', self.language)}: {getattr(attached_image, 'width', 0)}×{getattr(attached_image, 'height', 0)}]"
            full_context = f"{img_notice}\n{full_context}"

        if getattr(self, "ai_provider", "cagent") == "cagent":
            result = request_cagent_chat_guidance(
                question,
                full_context,
                self.language,
                chat_id=getattr(self, "session_id", None),
                history=history,
                transport=getattr(self, "cagent_transport", None),
            )
        else:
            result = request_gemini_web_business_guidance(
                question,
                full_context,
                self.language,
                intent=intent,
                history=history,
            )

        if sync:
            self._apply(result, question, case_diagnosis=case_diagnosis, intent=intent)
        else:
            try:
                if self.is_alive():
                    self.window.after(0, lambda: self._apply(result, question, case_diagnosis=case_diagnosis, intent=intent))
            except Exception:
                pass

    def _apply(
        self,
        result: CagentGuidanceResult,
        question: str,
        case_diagnosis: str = "",
        intent: str = "business",
    ) -> None:
        if not self.is_alive():
            return
        self._in_progress = False
        self.send_button.configure(state="normal")
        for button in self.suggestion_buttons:
            button.configure(state="normal")
        self.status.configure(text="")

        if result.status == "ready" and result.answer:
            if getattr(self, "ai_provider", "cagent") == "gemini_web":
                if not _contains_web_hallucination(result.answer):
                    self.answer.configure(text=result.answer)
                    self.conversation_history.append({"role": "assistant", "content": result.answer})
                    self.scroll_to_bottom()
                    return
            else:
                self.answer.configure(text=result.answer)
                self.conversation_history.append({"role": "assistant", "content": result.answer})
                self.scroll_to_bottom()
                return

        if case_diagnosis:
            self.answer.configure(text=case_diagnosis)
            self.conversation_history.append({"role": "assistant", "content": case_diagnosis})
            self.scroll_to_bottom()
            return

        from src.services.business_chat_knowledge import local_fallback as _local_fallback

        fallback_answer = _local_fallback(question, self.language, intent=intent)
        fallback = (
            f"{translate_for_language('operations_assistant_fallback_header', self.language)}\n"
            f"{translate_for_language('operations_assistant_fallback_notice', self.language)}\n\n"
            f"{fallback_answer}"
        )
        self.answer.configure(text=fallback)
        self.conversation_history.append({"role": "assistant", "content": fallback})
        self.scroll_to_bottom()

    def _open_fy_knowledge_update(self) -> None:
        """Mở hộp thoại cập nhật kiến thức AI theo năm tài chính."""
        current_fy = str(self.fiscal_year or "").strip().upper()
        fy_text = current_fy if current_fy.startswith("FY") else (f"FY{current_fy}" if current_fy else "FY2028")
        FiscalYearKnowledgeUpdateDialog.open(self.window, self.language, fiscal_year=fy_text)


class OperationsAssistantDialog:
    """Hộp thoại chỉ-hiển-thị cho trường hợp vận hành (OperationalCase)."""

    def __init__(
        self,
        parent: Any,
        case: OperationalCase,
        language: str,
        *,
        policy: CagentProviderPolicy | None = None,
        history_root: Path | str | None = None,
        cagent_transport: Any = None,
        widget_factory: Any = None,
        auto_request: bool = False,
    ) -> None:
        if not isinstance(language, str) or language.strip().lower() not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Ngôn ngữ '{language}' không được hỗ trợ. Phải là một trong các ngôn ngữ: "
                f"{sorted(SUPPORTED_LANGUAGES)}"
            )
        self.language = language.strip().lower()

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
        self.policy = policy if policy is not None else CagentProviderPolicy()
        self.history_root = history_root
        self.cagent_transport = cagent_transport
        self.widget_factory = widget_factory
        self.auto_request = bool(auto_request)

        self.ai_result: CagentGuidanceResult | None = None
        self._ai_in_progress: bool = False

        # Chuẩn bị dữ liệu hiển thị bản địa hóa
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
            "ai_advisory": translate_for_language("operations_assistant_ai_result_header", self.language),
        }

        self.confidence_label = _localized_confidence(case.confidence, self.language)
        self.no_technical_evidence_text = translate_for_language(
            "operations_assistant_no_technical_evidence", self.language
        )
        self.ask_ai_btn_text = translate_for_language("operations_assistant_ask_ai_btn", self.language)
        self.ask_gemini_btn_text = translate_for_language("operations_assistant_gemini_btn", self.language)
        self.ai_disclosure_text = translate_for_language("operations_assistant_ai_disclosure", self.language)
        self.fallback_header_text = translate_for_language("operations_assistant_fallback_header", self.language)
        self.fallback_notice_text = translate_for_language("operations_assistant_fallback_notice", self.language)
        self.retry_ai_btn_text = translate_for_language("operations_assistant_retry_ai_btn", self.language)
        self.show_technical_details_text = translate_for_language(
            "operations_assistant_show_technical_details", self.language
        )
        self.hide_technical_details_text = translate_for_language(
            "operations_assistant_hide_technical_details", self.language
        )

        # UI references
        self.window = None
        self._widgets: list[Any] = []
        self._ai_status_widget: Any = None
        self._ai_result_widget: Any = None
        self._ask_ai_btn_widget: Any = None
        self._ask_gemini_btn_widget: Any = None
        self._technical_details_widget: Any = None
        self._technical_details_toggle: Any = None

        self._build_ui()
        OperationsAssistantDialog._register_dialog(self.parent, self)
        if self.auto_request:
            self._start_initial_ai_request()

    @classmethod
    def open_or_focus(
        cls,
        parent: Any,
        case: OperationalCase,
        language: str,
        *,
        policy: CagentProviderPolicy | None = None,
        history_root: Path | str | None = None,
        cagent_transport: Any = None,
        widget_factory: Any = None,
        auto_request: bool = False,
    ) -> OperationsAssistantDialog:
        """Mở mới hoặc chuyển tiêu điểm tới cửa sổ trợ lý của parent."""
        active = cls._get_active_dialog(parent)
        if active is not None and active.is_alive():
            if active.case.run_id == case.run_id and active.language == language.strip().lower():
                active.focus()
                return active
            active.close()

        dialog = cls(
            parent,
            case,
            language,
            policy=policy,
            history_root=history_root,
            cagent_transport=cagent_transport,
            widget_factory=widget_factory,
            auto_request=auto_request,
        )
        return dialog

    def _start_initial_ai_request(self) -> None:
        """Start the primary Gemini Web request after the chat window is visible."""
        if self.window is not None and hasattr(self.window, "after"):
            try:
                self.window.after(80, self.ask_gemini_web)
                return
            except Exception:
                pass
        self.ask_gemini_web()

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

    def ask_cagent(self) -> None:
        """Kích hoạt yêu cầu tư vấn AI nội bộ C-AGENT một cách bất đồng bộ."""
        if self._ai_in_progress:
            return
        self._ai_in_progress = True
        in_progress_msg = translate_for_language("operations_assistant_ai_in_progress", self.language)
        self._update_ai_status(in_progress_msg)

        # Chạy trong luồng phụ để không chặn Tkinter event loop
        thread = threading.Thread(target=self._async_request_cagent, daemon=True)
        thread.start()

    def _async_request_cagent(self) -> None:
        """Thực thi request C-AGENT trong worker thread."""
        result = request_cagent_guidance(
            case=self.case,
            policy=self.policy,
            language=self.language,
            history_root=self.history_root,
            transport=self.cagent_transport,
        )
        self._dispatch_ui_update(result)

    def ask_gemini_web(self) -> None:
        """Keep selected-run evidence on-device; Gemini Web is generic-chat only."""
        if self._ai_in_progress:
            return
        self._update_ai_result(
            translate_for_language("operations_assistant_gemini_case_disabled", self.language),
            status="unavailable",
        )

    def _dispatch_ui_update(self, result: CagentGuidanceResult) -> None:
        """Đưa kết quả cập nhật về luồng UI."""
        if self.window is not None and hasattr(self.window, "after"):
            try:
                self.window.after(0, lambda: self._apply_cagent_result(result))
                return
            except Exception:
                pass
        self._apply_cagent_result(result)

    def _apply_cagent_result(self, result: CagentGuidanceResult) -> None:
        """Cập nhật kết quả phản hồi từ C-AGENT lên giao diện."""
        self._ai_in_progress = False
        self.ai_result = result

        if result.status == "ready":
            cited_text = ""
            if result.cited_evidence_ids:
                cited_label = translate_for_language("operations_assistant_ai_cited_evidence", self.language)
                cited_text = f"\n\n{cited_label} {', '.join(result.cited_evidence_ids)}"

            display_text = f"{result.answer}{cited_text}\n\n[{result.limitation}]"
            if self._ask_ai_btn_widget is not None and hasattr(self._ask_ai_btn_widget, "pack_forget"):
                self._ask_ai_btn_widget.pack_forget()
            self._update_ai_result(display_text, status="ready")
        else:
            steps = "\n".join(f"{index}. {step}" for index, step in enumerate(self.presentation.what_to_do, start=1))
            fallback_text = (
                f"{self.fallback_header_text}\n"
                f"{self.fallback_notice_text}\n\n"
                f"{self.presentation.what_happened}\n\n"
                f"{steps}"
            )
            self._update_ai_result(fallback_text, status=result.status)
            if self._ask_ai_btn_widget is not None and hasattr(self._ask_ai_btn_widget, "pack"):
                try:
                    self._ask_ai_btn_widget.configure(text=self.ask_gemini_btn_text)
                except Exception:
                    pass
                self._ask_ai_btn_widget.pack(anchor="w", pady=(8, 0))

    def _update_ai_status(self, message: str) -> None:
        """Cập nhật trạng thái yêu cầu AI."""
        if self._ai_status_widget is not None:
            if hasattr(self._ai_status_widget, "config"):
                try:
                    self._ai_status_widget.config(text=message)
                except Exception:
                    pass
            elif hasattr(self._ai_status_widget, "text"):
                self._ai_status_widget.text = message

    def _update_ai_result(self, message: str, status: str = "ready") -> None:
        """Cập nhật nội dung kết quả tư vấn AI."""
        if self._ai_result_widget is not None:
            if hasattr(self._ai_result_widget, "config"):
                try:
                    self._ai_result_widget.config(text=message)
                except Exception:
                    pass
            elif hasattr(self._ai_result_widget, "text"):
                self._ai_result_widget.text = message
        self._update_ai_status("")

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

        notice_widget = factory.create_label(
            self.window,
            text=self.readonly_notice,
            role="notice",
        )
        self._widgets.append(notice_widget)

        scope_frame = factory.create_frame(self.window, role="scope_frame")
        for key, val in self.scope_labels.items():
            lbl = factory.create_label(scope_frame, text=val, role=key)
            self._widgets.append(lbl)
        self._widgets.append(scope_frame)

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

        steps_frame = factory.create_frame(self.window, role="steps_frame")
        for step in self.presentation.what_to_do:
            step_lbl = factory.create_label(steps_frame, text=step, role="guidance_step")
            self._widgets.append(step_lbl)
        self._widgets.append(steps_frame)

        conf_lbl = factory.create_label(
            self.window,
            text=f"{self.section_headers['confidence']}: {self.confidence_label}",
            role=f"confidence_{self.case.confidence}",
        )
        self._widgets.append(conf_lbl)

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

        # AI Advisory Section (T035)
        ai_frame = factory.create_frame(self.window, role="ai_advisory_frame")
        ai_disclosure_lbl = factory.create_label(
            ai_frame,
            text=self.ai_disclosure_text,
            role="ai_disclosure",
        )
        self._widgets.append(ai_disclosure_lbl)

        self._ask_ai_btn_widget = factory.create_button(
            ai_frame,
            text=self.ask_ai_btn_text,
            command=self.ask_cagent,
            role="ask_ai_button",
        )
        self._widgets.append(self._ask_ai_btn_widget)

        self._ask_gemini_btn_widget = factory.create_button(
            ai_frame,
            text=self.ask_gemini_btn_text,
            command=self.ask_gemini_web,
            role="ask_gemini_button",
        )
        self._widgets.append(self._ask_gemini_btn_widget)

        self._ai_status_widget = factory.create_label(
            ai_frame,
            text="",
            role="ai_status",
        )
        self._widgets.append(self._ai_status_widget)

        self._ai_result_widget = factory.create_label(
            ai_frame,
            text="",
            role="ai_result",
        )
        self._widgets.append(self._ai_result_widget)
        self._widgets.append(ai_frame)

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
        self.window.geometry("820x720")
        self.window.minsize(680, 560)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.bind("<Destroy>", self._on_window_destroyed)

        apply_modern_window_style(self.window)

        # Create Canvas with Scrollbar for scrollable content
        canvas = tk.Canvas(self.window, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, padding=16)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        main_frame = scrollable_frame

        # Banner cảnh báo chỉ đọc
        notice_lbl = ttk.Label(
            main_frame,
            text=self.readonly_notice,
            wraplength=760,
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
            wraplength=760,
        )
        case_title.pack(anchor="w", pady=(5, 10))
        self._build_chat_panel(main_frame, ttk)
        return

        # The AI action is the primary reason many users open this dialog, so
        # it belongs above the long incident and technical-detail sections.
        ai_frame = ttk.LabelFrame(
            main_frame,
            text=f"✨ {self.section_headers['ai_advisory']}",
            padding=10,
        )
        ai_frame.pack(fill="x", pady=(0, 12))
        ttk.Label(
            ai_frame,
            text=self.ai_disclosure_text,
            wraplength=740,
            font=("Segoe UI", 8, "italic"),
            foreground="#4d5a66",
        ).pack(anchor="w", pady=(0, 8))
        btn_row = ttk.Frame(ai_frame)
        btn_row.pack(fill="x")
        try:
            ttk.Style().configure(
                "OperationsAssistantAI.TButton",
                font=("Segoe UI", 11, "bold"),
                padding=(16, 9),
            )
        except Exception:
            pass
        self._ask_ai_btn_widget = ttk.Button(
            btn_row,
            text=f"✨  {self.ask_ai_btn_text}",
            command=self.ask_cagent,
            style="OperationsAssistantAI.TButton",
        )
        self._ask_ai_btn_widget.pack(side="left")
        self._ask_gemini_btn_widget = ttk.Button(
            btn_row,
            text=self.ask_gemini_btn_text,
            command=self.ask_gemini_web,
        )
        self._ask_gemini_btn_widget.pack(side="left", padx=(8, 0))
        self._ai_status_widget = ttk.Label(
            btn_row,
            text="",
            font=("Segoe UI", 9, "italic"),
            foreground="#1976d2",
        )
        self._ai_status_widget.pack(side="left", padx=(10, 0))
        self._ai_result_widget = ttk.Label(
            ai_frame,
            text="",
            wraplength=740,
            font=("Segoe UI", 9),
        )
        self._ai_result_widget.pack(anchor="w", pady=(8, 0))

        # Nội dung chính
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True)

        ttk.Label(content_frame, text=self.section_headers["what_happened"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(content_frame, text=self.presentation.what_happened, wraplength=750).pack(anchor="w", padx=(10, 0), pady=(2, 6))

        ttk.Label(content_frame, text=self.section_headers["why_it_happened"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(content_frame, text=self.presentation.why_it_happened, wraplength=750).pack(anchor="w", padx=(10, 0), pady=(2, 6))

        ttk.Label(content_frame, text=self.section_headers["what_to_do"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        for step in self.presentation.what_to_do:
            ttk.Label(content_frame, text=step, wraplength=740).pack(anchor="w", padx=(15, 0), pady=(1, 1))

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
            ttk.Label(row_f, text=f"{ev_type_label}: {ev_summary} ({ev_loc})", wraplength=640).pack(side="left")

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
                wraplength=750,
            ).pack(anchor="w", pady=(0, 4))
            for item in self.case.evidence:
                ttk.Label(
                    tech_frame,
                    text=(
                        f"{item.type}: {_evidence_location(item)} -> {item.verification}\n"
                        f"{item.summary}"
                    ),
                    wraplength=750,
                ).pack(anchor="w", pady=(2, 2))
        else:
            ttk.Label(tech_frame, text=self.no_technical_evidence_text, wraplength=750).pack(anchor="w")

        # Footer với nút Đóng
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(fill="x", pady=(10, 0))

        close_btn = ttk.Button(footer_frame, text=self.close_btn_text, command=self.close)
        close_btn.pack(side="right")

    def _build_chat_panel(self, main_frame: Any, ttk: Any) -> None:
        """Build the operator-first view: answer first, local evidence on demand."""
        chat_frame = ttk.LabelFrame(
            main_frame,
            text=self.section_headers["ai_advisory"],
            padding=12,
        )
        chat_frame.pack(fill="both", expand=True)
        self._ai_status_widget = ttk.Label(
            chat_frame,
            text=translate_for_language("operations_assistant_ai_in_progress", self.language),
            font=("Segoe UI", 9, "italic"),
            foreground="#1976d2",
        )
        self._ai_status_widget.pack(anchor="w", pady=(0, 8))
        self._ai_result_widget = ttk.Label(
            chat_frame,
            text="",
            wraplength=740,
            justify="left",
            font=("Segoe UI", 10),
        )
        self._ai_result_widget.pack(anchor="w", fill="x")

        # No initial Gemini button: the selected run was already sent as the
        # dialog opened.  This retry appears only after a failed request.
        self._ask_ai_btn_widget = ttk.Button(
            chat_frame,
            text=self.ask_gemini_btn_text,
            command=self.ask_gemini_web,
        )
        self._ask_gemini_btn_widget = ttk.Button(
            chat_frame,
            text=self.ask_gemini_btn_text,
            command=self.ask_gemini_web,
        )
        self._ask_gemini_btn_widget.pack(anchor="w", pady=(10, 0))

        details_frame = ttk.LabelFrame(
            main_frame,
            text=self.section_headers["technical_details"],
            padding=10,
        )
        ttk.Label(
            details_frame,
            text=f"{self.section_headers['what_happened']}: {self.presentation.what_happened}",
            wraplength=740,
            justify="left",
        ).pack(anchor="w", pady=(0, 7))
        ttk.Label(
            details_frame,
            text=f"{self.section_headers['why_it_happened']}: {self.presentation.why_it_happened}",
            wraplength=740,
            justify="left",
        ).pack(anchor="w", pady=(0, 7))
        for item in self.case.evidence:
            ttk.Label(
                details_frame,
                text=f"{item.type}: {_safe_evidence_summary(item.summary, self.language)}",
                wraplength=740,
                justify="left",
            ).pack(anchor="w", pady=1)

        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(fill="x", pady=(10, 0))
        details_visible = {"value": False}

        def toggle_technical_details() -> None:
            details_visible["value"] = not details_visible["value"]
            if details_visible["value"]:
                details_frame.pack(fill="x", pady=(10, 0), before=footer_frame)
                details_button.configure(text=self.hide_technical_details_text)
            else:
                details_frame.pack_forget()
                details_button.configure(text=self.show_technical_details_text)

        details_button = ttk.Button(
            footer_frame,
            text=self.show_technical_details_text,
            command=toggle_technical_details,
        )
        details_button.pack(side="left")
        self._technical_details_widget = details_frame
        self._technical_details_toggle = details_button
        ttk.Button(footer_frame, text=self.close_btn_text, command=self.close).pack(side="right")

    def close(self) -> None:
        """Đóng cửa sổ hộp thoại an toàn và dọn registry singleton."""
        OperationsAssistantDialog._unregister_dialog(self.parent, self)
        window = self.window
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
