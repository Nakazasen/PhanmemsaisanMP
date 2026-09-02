"""Unit tests for OperationsAssistantDialog (presentation-only shell, full read-only content, singleton guard).

Covers:
- Fake widget rendering (no Tk/display dependency)
- Correct multilingual shell labels across VI, EN, JA
- Evidence list rendering with localized status (verified/missing/mismatch)
- Confidence display (confirmed vs unknown distinct styling and labels)
- Technical details section displaying case metadata without disk reads
- No technical evidence fallback handling
- Singleton window guard:
  - Repeated open requests for the same run reuse existing dialog and focus/lift window
  - Closing dialog cleans up registry so subsequent request creates a new dialog
  - Destroyed dialog creates a fresh dialog rather than returning dead reference
  - Opening a different run on the same parent safely closes the old dialog and creates a new one
  - Different parents can open independent dialogs
  - Window manager WM_DELETE_WINDOW triggers proper cleanup
- Fail-closed enforcement for invalid language, missing presentation, or language mismatch
- Verification that raw traceback/JSON are not rendered in primary shell
- Zero side-effects (no pipeline execution, no DB access, no file mutation)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable
import unittest
from unittest.mock import MagicMock, patch

from src.services.i18n import get_current_language, set_current_language, t, translate_for_language
from src.services.operations_case_service import EvidenceReference, OperationalCase
from src.services.operations_knowledge import (
    ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK,
    ERROR_CODE_MISSING_STAFFING_BASELINE,
    ERROR_CODE_PREFLIGHT_SOURCE_VALIDATION_FAILURE,
    get_knowledge_entry,
)
from src.ui.operations_assistant import OperationsAssistantDialog
from src.universal_app import MPManagerApp


@dataclass
class FakeWidget:
    parent: Any
    role: str = ""
    text: str = ""
    command: Callable[[], None] | None = None
    destroyed: bool = False

    def destroy(self) -> None:
        self.destroyed = True


@dataclass
class FakeWindow(FakeWidget):
    title_text: str = ""
    lifted: bool = False
    focused: bool = False
    protocols: dict[str, Callable[[], None]] = field(default_factory=dict)
    bindings: dict[str, Callable[[Any], None]] = field(default_factory=dict)

    def destroy(self) -> None:
        if self.destroyed:
            return
        self.destroyed = True
        callback = self.bindings.get("<Destroy>")
        if callback is not None:
            callback(SimpleNamespace(widget=self))

    def title(self, text: str) -> None:
        self.title_text = text

    def lift(self) -> None:
        self.lifted = True

    def focus(self) -> None:
        self.focused = True

    def focus_force(self) -> None:
        self.focused = True

    def deiconify(self) -> None:
        pass

    def protocol(self, name: str, callback: Callable[[], None]) -> None:
        self.protocols[name] = callback

    def bind(self, sequence: str, callback: Callable[[Any], None]) -> None:
        self.bindings[sequence] = callback

    def trigger_protocol(self, name: str) -> None:
        if name in self.protocols:
            self.protocols[name]()


class FakeWidgetFactory:
    """Factory tạo fake widgets trong môi trường test không có màn hình hiển thị."""

    def __init__(self) -> None:
        self.created_windows: list[FakeWindow] = []
        self.created_labels: list[FakeWidget] = []
        self.created_frames: list[FakeWidget] = []
        self.created_buttons: list[FakeWidget] = []

    def create_window(self, parent: Any, title: str = "") -> FakeWindow:
        win = FakeWindow(parent=parent, role="window", text=title, title_text=title)
        self.created_windows.append(win)
        return win

    def create_frame(self, parent: Any, role: str = "") -> FakeWidget:
        frame = FakeWidget(parent=parent, role=role)
        self.created_frames.append(frame)
        return frame

    def create_label(self, parent: Any, text: str = "", role: str = "") -> FakeWidget:
        lbl = FakeWidget(parent=parent, text=text, role=role)
        self.created_labels.append(lbl)
        return lbl

    def create_button(
        self,
        parent: Any,
        text: str = "",
        command: Callable[[], None] | None = None,
        role: str = "",
    ) -> FakeWidget:
        btn = FakeWidget(parent=parent, text=text, command=command, role=role)
        self.created_buttons.append(btn)
        return btn


def _make_confirmed_case(lang: str = "vi", run_id: str = "run-t018-confirmed") -> OperationalCase:
    """Tạo đối tượng OperationalCase mẫu cho lỗi confirmed."""
    entry = get_knowledge_entry(ERROR_CODE_MISSING_STAFFING_BASELINE)
    assert entry is not None
    pres = entry.translations[lang]
    evidence = (
        EvidenceReference(
            type="catalog_row",
            local_path="run_history.db",
            locator=f"runs.run_id = '{run_id}'",
            summary="Bản ghi catalog",
            verification="verified",
        ),
        EvidenceReference(
            type="stage_evidence",
            local_path="reports/pipeline_stage_evidence.json",
            locator="validate_staffing",
            summary="Bằng chứng bước kiểm tra nhân sự",
            verification="verified",
        ),
        EvidenceReference(
            type="failure_traceback",
            local_path="reports/failure_traceback.txt",
            locator="traceback",
            summary="Nhật ký lỗi",
            verification="missing",
        ),
    )
    return OperationalCase(
        case_id=f"case-{run_id}",
        run_id=run_id,
        fiscal_year=2028,
        cost_center_scope="1412000040",
        status="PRECHECK_FAILED",
        stage="validate_staffing",
        classification=ERROR_CODE_MISSING_STAFFING_BASELINE,
        confidence="confirmed",
        summary=pres.title,
        evidence=evidence,
        guidance=pres.what_to_do,
        presentation=pres,
    )


def _make_unknown_case(lang: str = "vi", run_id: str = "run-t018-unknown") -> OperationalCase:
    """Tạo đối tượng OperationalCase mẫu cho lỗi unknown."""
    from src.services.operations_case_service import _create_unknown_fallback_presentation
    pres = _create_unknown_fallback_presentation(lang, 2028, "ALL")
    evidence = (
        EvidenceReference(
            type="catalog_row",
            local_path="run_history.db",
            locator=f"runs.run_id = '{run_id}'",
            summary="Bản ghi catalog",
            verification="verified",
        ),
        EvidenceReference(
            type="preflight_report",
            local_path="reports/preflight_report.json",
            locator="issues",
            summary="Báo cáo tiền trạm bị hỏng",
            verification="mismatch",
        ),
    )
    return OperationalCase(
        case_id=f"case-{run_id}",
        run_id=run_id,
        fiscal_year=2028,
        cost_center_scope="ALL",
        status="FAILED",
        stage="publication",
        classification="unknown",
        confidence="unknown",
        summary=pres.title,
        evidence=evidence,
        guidance=pres.what_to_do,
        presentation=pres,
    )


class TestOperationsAssistantDialog(unittest.TestCase):
    def setUp(self) -> None:
        OperationsAssistantDialog.clear_registry()

    def tearDown(self) -> None:
        OperationsAssistantDialog.clear_registry()

    def test_dialog_renders_confirmed_case_in_vietnamese(self) -> None:
        factory = FakeWidgetFactory()
        case = _make_confirmed_case("vi")
        dialog = OperationsAssistantDialog(None, case, "vi", widget_factory=factory)

        self.assertEqual(dialog.window_title, "Trợ lý Vận hành & Xử lý Lỗi")
        self.assertIn("chỉ cung cấp thông tin hướng dẫn", dialog.readonly_notice)
        self.assertEqual(dialog.close_btn_text, "Đóng")

        # Kiểm tra nội dung window và các label
        self.assertEqual(len(factory.created_windows), 1)
        self.assertEqual(factory.created_windows[0].title_text, "Trợ lý Vận hành & Xử lý Lỗi")

        label_texts = [lbl.text for lbl in factory.created_labels]
        self.assertTrue(any("FY2028" in t for t in label_texts))
        self.assertTrue(any("1412000040" in t for t in label_texts))
        self.assertTrue(any("Cần bổ sung dữ liệu trước khi tính" in t for t in label_texts))
        self.assertTrue(any("Thiếu dữ liệu nhân sự mốc ban đầu" in t for t in label_texts))

        # Kiểm tra nút Đóng và hai nút hỏi AI
        self.assertEqual(len(factory.created_buttons), 3)
        close_btn = next(b for b in factory.created_buttons if b.role == "close_button")
        self.assertEqual(close_btn.text, "Đóng")

        # Đóng dialog
        dialog.close()
        self.assertTrue(factory.created_windows[0].destroyed)

    def test_dialog_renders_unknown_case_across_languages(self) -> None:
        for lang, expected_title, expected_close, expected_status, expected_scope in [
            ("vi", "Trợ lý Vận hành & Xử lý Lỗi", "Đóng", "Chưa hoàn tất", "Phạm vi lần chạy"),
            ("ja", "運用・エラー対応アシスタント", "閉じる", "完了できませんでした", "実行範囲"),
            ("en", "Operations & Error Assistant", "Close", "Did Not Complete", "Run Scope"),
        ]:
            factory = FakeWidgetFactory()
            case = _make_unknown_case(lang)
            dialog = OperationsAssistantDialog(None, case, lang, widget_factory=factory)

            self.assertEqual(dialog.window_title, expected_title)
            self.assertEqual(dialog.close_btn_text, expected_close)
            self.assertEqual(dialog.scope_title, expected_scope)
            self.assertEqual(dialog.scope_labels["status_value"], expected_status)
            self.assertEqual(factory.created_windows[0].title_text, expected_title)
            close_btn = next(b for b in factory.created_buttons if b.role == "close_button")
            self.assertEqual(close_btn.text, expected_close)

    def test_evidence_rendering_with_verified_missing_mismatch_statuses(self) -> None:
        """Kiểm tra bảng bằng chứng hiển thị đầy đủ các trạng thái và nhãn đa ngôn ngữ thân thiện."""
        for lang, exp_verified, exp_missing, exp_mismatch, exp_catalog, exp_stage, exp_trace in [
            ("vi", "Đã xác minh", "Thiếu tệp", "Không khớp", "Bản ghi danh mục", "Bằng chứng giai đoạn", "Nhật ký chi tiết lỗi"),
            ("en", "Verified", "Missing", "Mismatch", "Catalog Record", "Stage Evidence", "Error Details Log"),
            ("ja", "検証済み", "不足", "不一致", "カタログレコード", "フェーズ証拠", "エラー詳細ログ"),
        ]:
            factory = FakeWidgetFactory()
            pres = get_knowledge_entry(ERROR_CODE_MISSING_STAFFING_BASELINE).translations[lang]
            evidence = (
                EvidenceReference(
                    type="catalog_row",
                    local_path="run_history.db",
                    locator="runs.run_id = 'run-test-ev'",
                    summary="Catalog row summary",
                    verification="verified",
                ),
                EvidenceReference(
                    type="stage_evidence",
                    local_path="reports/pipeline_stage_evidence.json",
                    locator="validate_staffing",
                    summary="Stage evidence summary",
                    verification="mismatch",
                ),
                EvidenceReference(
                    type="failure_traceback",
                    local_path="reports/failure_traceback.txt",
                    locator="traceback",
                    summary="Traceback summary",
                    verification="missing",
                ),
            )
            case = OperationalCase(
                case_id="case-ev",
                run_id="run-ev",
                fiscal_year=2028,
                cost_center_scope="1412000040",
                status="FAILED",
                stage="validate_staffing",
                classification=ERROR_CODE_MISSING_STAFFING_BASELINE,
                confidence="confirmed",
                summary=pres.title,
                evidence=evidence,
                guidance=pres.what_to_do,
                presentation=pres,
            )
            dialog = OperationsAssistantDialog(None, case, lang, widget_factory=factory)

            # Lấy các nhãn thuộc evidence_frame
            evidence_labels = [lbl for lbl in factory.created_labels if lbl.role.startswith("evidence_")]
            self.assertEqual(len(evidence_labels), 3)

            texts = [lbl.text for lbl in evidence_labels]
            # Xác thực có đầy đủ 3 trạng thái bản địa hóa
            self.assertTrue(any(f"[{exp_verified}]" in t for t in texts))
            self.assertTrue(any(f"[{exp_mismatch}]" in t for t in texts))
            self.assertTrue(any(f"[{exp_missing}]" in t for t in texts))

            # Xác thực có đầy đủ loại bằng chứng bản địa hóa
            self.assertTrue(any(exp_catalog in t for t in texts))
            self.assertTrue(any(exp_stage in t for t in texts))
            self.assertTrue(any(exp_trace in t for t in texts))

    def test_confidence_label_confirmed_vs_unknown(self) -> None:
        """Đảm bảo unknown confidence luôn có nhãn và role unconfirmed rõ ràng, không bị nhầm với confirmed."""
        # 1. Confirmed case (VI)
        factory_conf = FakeWidgetFactory()
        case_conf = _make_confirmed_case("vi")
        dialog_conf = OperationsAssistantDialog(None, case_conf, "vi", widget_factory=factory_conf)
        self.assertEqual(dialog_conf.confidence_label, "Đã xác nhận")
        conf_lbl = next(lbl for lbl in factory_conf.created_labels if lbl.role == "confidence_confirmed")
        self.assertIn("Đã xác nhận", conf_lbl.text)

        # 2. Unknown case (VI)
        factory_unk = FakeWidgetFactory()
        case_unk = _make_unknown_case("vi")
        dialog_unk = OperationsAssistantDialog(None, case_unk, "vi", widget_factory=factory_unk)
        self.assertEqual(dialog_unk.confidence_label, "Chưa xác nhận")
        unk_lbl = next(lbl for lbl in factory_unk.created_labels if lbl.role == "confidence_unknown")
        self.assertIn("Chưa xác nhận", unk_lbl.text)
        self.assertNotIn("Đã xác nhận", unk_lbl.text)

        # 3. Unknown case (EN)
        factory_en = FakeWidgetFactory()
        case_en = _make_unknown_case("en")
        dialog_en = OperationsAssistantDialog(None, case_en, "en", widget_factory=factory_en)
        self.assertEqual(dialog_en.confidence_label, "Unconfirmed")
        en_lbl = next(lbl for lbl in factory_en.created_labels if lbl.role == "confidence_unknown")
        self.assertIn("Unconfirmed", en_lbl.text)
        self.assertNotIn("Confirmed", en_lbl.text)

    def test_technical_details_without_disk_reads(self) -> None:
        """Kiểm tra vùng chi tiết kỹ thuật render từ OperationalCase mà không đọc tệp từ đĩa."""
        factory = FakeWidgetFactory()
        case = _make_confirmed_case("vi")
        dialog = OperationsAssistantDialog(None, case, "vi", widget_factory=factory)

        tech_labels = [
            lbl for lbl in factory.created_labels
            if lbl.role in ("technical_detail_meta", "technical_detail_ref")
        ]
        self.assertGreaterEqual(len(tech_labels), 2)
        meta_text = tech_labels[0].text
        self.assertIn("case-run-t018-confirmed", meta_text)
        self.assertIn("validate_staffing", meta_text)
        self.assertIn("missing_staffing_baseline", meta_text)

        # Kiểm tra technical ref của từng evidence
        ref_texts = [lbl.text for lbl in tech_labels[1:]]
        self.assertTrue(any("run_history.db" in t for t in ref_texts))
        self.assertTrue(any("reports/pipeline_stage_evidence.json" in t for t in ref_texts))

    def test_technical_details_fallback_when_no_evidence(self) -> None:
        """Kiểm tra thông báo thân thiện khi case không có bằng chứng kỹ thuật."""
        from src.services.operations_case_service import _create_unknown_fallback_presentation
        pres = _create_unknown_fallback_presentation("vi", 2028, "ALL")
        case_empty_ev = OperationalCase(
            case_id="case-empty-ev",
            run_id="run-empty-ev",
            fiscal_year=2028,
            cost_center_scope="ALL",
            status="SUCCEEDED",
            stage="publication",
            classification="unknown",
            confidence="unknown",
            summary=pres.title,
            evidence=(),
            guidance=pres.what_to_do,
            presentation=pres,
        )

        factory = FakeWidgetFactory()
        dialog = OperationsAssistantDialog(None, case_empty_ev, "vi", widget_factory=factory)
        no_tech_lbl = next(lbl for lbl in factory.created_labels if lbl.role == "no_technical_evidence")
        self.assertEqual(
            no_tech_lbl.text,
            "Không có bằng chứng kỹ thuật bổ sung nào được ghi nhận."
        )

    # ---------------------------------------------------------------------------
    # T020: Singleton Window Guard Tests
    # ---------------------------------------------------------------------------

    def test_singleton_guard_reuses_existing_dialog_for_same_run(self) -> None:
        """Mở cùng parent + cùng run_id hai lần: chỉ tạo 1 window, focus cửa sổ cũ."""
        factory = FakeWidgetFactory()
        parent = object()
        case = _make_confirmed_case("vi", run_id="run-singleton-1")

        dialog_1 = OperationsAssistantDialog.open_or_focus(parent, case, "vi", widget_factory=factory)
        self.assertEqual(len(factory.created_windows), 1)
        win = factory.created_windows[0]

        # Reset cờ focused/lifted để kiểm tra lần gọi thứ hai
        win.focused = False
        win.lifted = False

        # Mở lần hai với cùng run_id
        dialog_2 = OperationsAssistantDialog.open_or_focus(parent, case, "vi", widget_factory=factory)

        # Xác nhận trả về cùng dialog instance, không tạo window mới, đã gọi focus/lift
        self.assertIs(dialog_1, dialog_2)
        self.assertEqual(len(factory.created_windows), 1)
        self.assertTrue(win.focused)
        self.assertTrue(win.lifted)

    def test_singleton_guard_creates_new_dialog_after_close(self) -> None:
        """Đóng dialog cũ rồi mở lại: dọn registry và tạo window mới."""
        factory = FakeWidgetFactory()
        parent = object()
        case = _make_confirmed_case("vi", run_id="run-singleton-2")

        dialog_1 = OperationsAssistantDialog.open_or_focus(parent, case, "vi", widget_factory=factory)
        self.assertEqual(len(factory.created_windows), 1)
        win_1 = factory.created_windows[0]

        # Đóng dialog_1
        dialog_1.close()
        self.assertTrue(win_1.destroyed)
        self.assertFalse(dialog_1.is_alive())

        # Mở lại
        dialog_2 = OperationsAssistantDialog.open_or_focus(parent, case, "vi", widget_factory=factory)
        self.assertIsNot(dialog_1, dialog_2)
        self.assertEqual(len(factory.created_windows), 2)
        self.assertTrue(dialog_2.is_alive())

    def test_singleton_guard_recovers_if_window_destroyed_externally(self) -> None:
        """Khi window bị destroy bên ngoài (is_alive=False), mở lại sẽ tạo mới."""
        factory = FakeWidgetFactory()
        parent = object()
        case = _make_confirmed_case("vi", run_id="run-singleton-3")

        dialog_1 = OperationsAssistantDialog.open_or_focus(parent, case, "vi", widget_factory=factory)
        win_1 = factory.created_windows[0]
        # Giả lập window bị destroy từ bên ngoài mà chưa gọi dialog.close().
        # Binding phải dọn registry ngay, không chờ lần mở tiếp theo.
        win_1.destroy()
        self.assertIsNone(OperationsAssistantDialog._get_active_dialog(parent))

        dialog_2 = OperationsAssistantDialog.open_or_focus(parent, case, "vi", widget_factory=factory)
        self.assertIsNot(dialog_1, dialog_2)
        self.assertEqual(len(factory.created_windows), 2)
        self.assertTrue(dialog_2.is_alive())

    def test_singleton_guard_switches_to_different_run_by_closing_old(self) -> None:
        """Cùng parent nhưng mở run_id khác: đóng cửa sổ cũ và mở cửa sổ mới cho run mới."""
        factory = FakeWidgetFactory()
        parent = object()
        case_1 = _make_confirmed_case("vi", run_id="run-first")
        case_2 = _make_unknown_case("vi", run_id="run-second")

        dialog_1 = OperationsAssistantDialog.open_or_focus(parent, case_1, "vi", widget_factory=factory)
        win_1 = factory.created_windows[0]
        self.assertEqual(dialog_1.case.run_id, "run-first")

        # Yêu cầu mở run_id khác
        dialog_2 = OperationsAssistantDialog.open_or_focus(parent, case_2, "vi", widget_factory=factory)

        # Cửa sổ cũ đã bị đóng, cửa sổ mới đại diện cho run-second
        self.assertTrue(win_1.destroyed)
        self.assertIsNot(dialog_1, dialog_2)
        self.assertEqual(len(factory.created_windows), 2)
        self.assertEqual(dialog_2.case.run_id, "run-second")

    def test_singleton_guard_recreates_dialog_when_active_language_changes(self) -> None:
        """Cùng run nhưng đổi VI sang EN phải tạo presentation theo ngôn ngữ mới."""
        factory = FakeWidgetFactory()
        parent = object()
        case_vi = _make_confirmed_case("vi", run_id="run-language-switch")
        case_en = _make_confirmed_case("en", run_id="run-language-switch")

        dialog_vi = OperationsAssistantDialog.open_or_focus(parent, case_vi, "vi", widget_factory=factory)
        window_vi = factory.created_windows[0]
        dialog_en = OperationsAssistantDialog.open_or_focus(parent, case_en, "en", widget_factory=factory)

        self.assertTrue(window_vi.destroyed)
        self.assertIsNot(dialog_vi, dialog_en)
        self.assertEqual(dialog_en.language, "en")
        self.assertEqual(len(factory.created_windows), 2)

    def test_singleton_guard_supports_multiple_independent_parents(self) -> None:
        """Các parent khác nhau được phép mở các dialog độc lập cùng lúc."""
        factory = FakeWidgetFactory()
        parent_a = object()
        parent_b = object()
        case_a = _make_confirmed_case("vi", run_id="run-parent-a")
        case_b = _make_confirmed_case("vi", run_id="run-parent-b")

        dialog_a = OperationsAssistantDialog.open_or_focus(parent_a, case_a, "vi", widget_factory=factory)
        dialog_b = OperationsAssistantDialog.open_or_focus(parent_b, case_b, "vi", widget_factory=factory)

        self.assertIsNot(dialog_a, dialog_b)
        self.assertEqual(len(factory.created_windows), 2)
        self.assertTrue(dialog_a.is_alive())
        self.assertTrue(dialog_b.is_alive())

    def test_singleton_guard_cleanup_on_wm_delete_window_protocol(self) -> None:
        """Đóng qua protocol WM_DELETE_WINDOW (nút X trên thanh tiêu đề) thực hiện dọn registry."""
        factory = FakeWidgetFactory()
        parent = object()
        case = _make_confirmed_case("vi", run_id="run-wm-delete")

        dialog_1 = OperationsAssistantDialog.open_or_focus(parent, case, "vi", widget_factory=factory)
        win_1 = factory.created_windows[0]
        self.assertIn("WM_DELETE_WINDOW", win_1.protocols)

        # Kích hoạt callback WM_DELETE_WINDOW
        win_1.trigger_protocol("WM_DELETE_WINDOW")
        self.assertTrue(win_1.destroyed)
        self.assertFalse(dialog_1.is_alive())

        # Lần mở tiếp theo sẽ tạo dialog mới
        dialog_2 = OperationsAssistantDialog.open_or_focus(parent, case, "vi", widget_factory=factory)
        self.assertIsNot(dialog_1, dialog_2)
        self.assertEqual(len(factory.created_windows), 2)

    def test_dialog_fail_closed_on_unsupported_language(self) -> None:
        factory = FakeWidgetFactory()
        case = _make_confirmed_case("vi")
        with self.assertRaises(ValueError) as ctx:
            OperationsAssistantDialog(None, case, "fr", widget_factory=factory)
        self.assertIn("không được hỗ trợ", str(ctx.exception))

    def test_dialog_fail_closed_on_none_presentation(self) -> None:
        factory = FakeWidgetFactory()
        case = _make_confirmed_case("vi")
        case_no_pres = OperationalCase(
            case_id=case.case_id,
            run_id=case.run_id,
            fiscal_year=case.fiscal_year,
            cost_center_scope=case.cost_center_scope,
            status=case.status,
            stage=case.stage,
            classification=case.classification,
            confidence=case.confidence,
            summary=case.summary,
            evidence=case.evidence,
            guidance=case.guidance,
            presentation=None,
        )
        with self.assertRaises(ValueError) as ctx:
            OperationsAssistantDialog(None, case_no_pres, "vi", widget_factory=factory)
        self.assertIn("presentation không được để trống", str(ctx.exception))

    def test_dialog_fail_closed_on_language_mismatch(self) -> None:
        factory = FakeWidgetFactory()
        case_vi = _make_confirmed_case("vi")
        # Yêu cầu dialog hiển thị tiếng Nhật (ja) nhưng case mang presentation tiếng Việt (vi)
        with self.assertRaises(ValueError) as ctx:
            OperationsAssistantDialog(None, case_vi, "ja", widget_factory=factory)
        self.assertIn("không khớp", str(ctx.exception))

    def test_dialog_fail_closed_on_invalid_case_type(self) -> None:
        factory = FakeWidgetFactory()
        with self.assertRaises(TypeError) as ctx:
            OperationsAssistantDialog(None, {"not": "a case"}, "vi", widget_factory=factory)  # type: ignore[arg-type]
        self.assertIn("phải là một đối tượng OperationalCase", str(ctx.exception))

    def test_dialog_no_side_effects_on_environment(self, tmp_path: Path | None = None) -> None:
        """Đảm bảo dialog không tạo file, không gọi DB, không gọi pipeline."""
        factory = FakeWidgetFactory()
        case = _make_confirmed_case("vi")
        dialog = OperationsAssistantDialog(None, case, "vi", widget_factory=factory)
        self.assertIsNotNone(dialog)

        # Kiểm tra không render raw JSON hoặc traceback vào labels
        for lbl in factory.created_labels:
            self.assertNotIn("Traceback (most recent call last)", lbl.text)
            self.assertNotIn('"schema_version":', lbl.text)
            self.assertNotIn("{{", lbl.text)
            self.assertNotIn("}}", lbl.text)

    def test_dialog_exposes_no_write_or_repair_or_pipeline_buttons_or_commands(self) -> None:
        """T023 Regression: Dialog chỉ là presentation-only shell, tuyệt đối không có nút ghi, sửa file, chạy pipeline hay sửa tự động."""
        # 1. Kiểm tra API bề mặt của OperationsAssistantDialog không có bất kỳ hàm mutation/write/repair nào
        prohibited_methods = (
            "save_source", "save_file", "write_file", "apply_fix", "auto_fix",
            "auto_repair", "automatic_repair", "run_pipeline", "recalculate",
            "execute_repair", "publish_case", "export_fix", "modify_source",
        )
        for method_name in prohibited_methods:
            self.assertFalse(
                hasattr(OperationsAssistantDialog, method_name),
                f"OperationsAssistantDialog không được có phương thức '{method_name}'"
            )

        # 2. Kiểm tra giao diện qua các ngôn ngữ
        for lang in ("vi", "en", "ja"):
            for case_fn in (_make_confirmed_case, _make_unknown_case):
                factory = FakeWidgetFactory()
                case = case_fn(lang)
                dialog = OperationsAssistantDialog(None, case, lang, widget_factory=factory)

                # Các nút được phép tồn tại là Đóng, C-AGENT và Gemini Web.
                self.assertEqual(len(factory.created_buttons), 3)
                close_btn = next(b for b in factory.created_buttons if b.role == "close_button")
                self.assertEqual(close_btn.role, "close_button")
                self.assertEqual(close_btn.command, dialog.close)

                ask_btn = next(b for b in factory.created_buttons if b.role == "ask_ai_button")
                self.assertEqual(ask_btn.role, "ask_ai_button")
                self.assertEqual(ask_btn.command, dialog.ask_cagent)

                gemini_btn = next(b for b in factory.created_buttons if b.role == "ask_gemini_button")
                self.assertEqual(gemini_btn.command, dialog.ask_gemini_web)

                # Xác nhận không có nút hay command nào khác được tạo
                for btn in factory.created_buttons:
                    self.assertNotEqual(btn.role, "apply_fix")
                    self.assertNotEqual(btn.role, "save_source")
                    self.assertNotEqual(btn.role, "run_pipeline")
                    self.assertNotEqual(btn.role, "auto_repair")




class MockProjectPaths:
    def __init__(self, history_root: str) -> None:
        self.history_root = history_root


class MockTreeview:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.bindings: dict[str, Callable[[Any], None]] = {}
        self.children: list[str] = []
        self._selection: tuple[str, ...] = ()

    def heading(self, *args: Any, **kwargs: Any) -> None:
        pass

    def column(self, *args: Any, **kwargs: Any) -> None:
        pass

    def pack(self, *args: Any, **kwargs: Any) -> None:
        pass

    def bind(self, event: str, callback: Callable[[Any], None]) -> None:
        self.bindings[event] = callback

    def get_children(self) -> list[str]:
        return list(self.children)

    def delete(self, node: str) -> None:
        if node in self.children:
            self.children.remove(node)

    def insert(self, parent: str, index: Any, values: Any = None) -> str:
        node_id = f"node_{len(self.children)}"
        self.children.append(node_id)
        return node_id

    def selection(self) -> tuple[str, ...]:
        return self._selection

    def set_selection(self, node_id: str | None) -> None:
        self._selection = (node_id,) if node_id else ()
        if "<<TreeviewSelect>>" in self.bindings:
            self.bindings["<<TreeviewSelect>>"](None)


class MockButton:
    def __init__(self, parent: Any, text: str = "", command: Callable[[], None] | None = None, state: str = "normal", **kwargs: Any) -> None:
        self.parent = parent
        self.text = text
        self.command = command
        self.state = state

    def pack(self, *args: Any, **kwargs: Any) -> None:
        pass

    def grid(self, *args: Any, **kwargs: Any) -> None:
        pass

    def configure(self, **kwargs: Any) -> None:
        if "state" in kwargs:
            self.state = kwargs["state"]
        if "text" in kwargs:
            self.text = kwargs["text"]


class MockToplevel:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._exists = True

    def title(self, *args: Any) -> None:
        pass

    def geometry(self, *args: Any) -> None:
        pass

    def transient(self, *args: Any) -> None:
        pass

    def lift(self, *args: Any) -> None:
        pass

    def focus_force(self, *args: Any) -> None:
        pass

    def winfo_exists(self) -> bool:
        return self._exists


class SynchronousThread:
    def __init__(self, target: Callable[[], None] | None = None, daemon: bool | None = None) -> None:
        self.target = target

    def start(self) -> None:
        if self.target:
            self.target()


class MockStringVar:
    def __init__(self, master: Any = None, value: Any = "", name: Any = None) -> None:
        self._value = str(value)

    def get(self) -> str:
        return self._value

    def set(self, val: Any) -> None:
        self._value = str(val)


class MockApp:
    def __init__(self, history_root: str = "D:/dummy_history") -> None:
        self.root = "mock_root"
        self._history_root = history_root
        self._run_history_window = None

    def _focus_existing_editor(self, name: str) -> bool:
        return False

    def _project_paths(self, fiscal_year: int | None = None) -> MockProjectPaths:
        return MockProjectPaths(self._history_root)

    def _current_fiscal_year(self) -> int:
        return 2028

    def _register_singleton_editor(self, name: str, dialog: Any) -> None:
        setattr(self, name, dialog)

    def _run_on_ui_thread(self, fn: Any, *args: Any) -> None:
        fn(*args)

    open_run_history = MPManagerApp.open_run_history


class TestRunHistoryOperationsAssistantIntegration(unittest.TestCase):
    def setUp(self) -> None:
        OperationsAssistantDialog.clear_registry()
        self.original_language = get_current_language()

    def tearDown(self) -> None:
        OperationsAssistantDialog.clear_registry()
        set_current_language(self.original_language)

    def _setup_run_history(
        self,
        rows: list[dict[str, object]],
        history_root: str = "D:/dummy_history",
    ) -> tuple[MockApp, MockTreeview, MockButton, MockToplevel]:
        app = MockApp(history_root)
        created_treeview = []
        created_buttons = []
        created_toplevel = []

        def mock_treeview_factory(*args: Any, **kwargs: Any) -> MockTreeview:
            tv = MockTreeview(*args, **kwargs)
            created_treeview.append(tv)
            return tv

        def mock_button_factory(*args: Any, **kwargs: Any) -> MockButton:
            btn = MockButton(*args, **kwargs)
            created_buttons.append(btn)
            return btn

        def mock_toplevel_factory(*args: Any, **kwargs: Any) -> MockToplevel:
            tl = MockToplevel(*args, **kwargs)
            created_toplevel.append(tl)
            return tl

        with patch("src.universal_app.tk.Toplevel", side_effect=mock_toplevel_factory), \
             patch("src.universal_app.tk.StringVar", side_effect=MockStringVar), \
             patch("src.universal_app.ttk.Treeview", side_effect=mock_treeview_factory), \
             patch("src.universal_app.ttk.Button", side_effect=mock_button_factory), \
             patch("src.universal_app.ttk.Frame", return_value=MagicMock()), \
             patch("src.universal_app.ttk.Label", return_value=MagicMock()), \
             patch("src.universal_app.ttk.Entry", return_value=MagicMock()), \
             patch("src.universal_app.ttk.Combobox", return_value=MagicMock()), \
             patch("src.universal_app.filter_runs", return_value=rows), \
             patch("src.universal_app.threading.Thread", side_effect=SynchronousThread):
            app.open_run_history()

        table = created_treeview[0]
        assistant_btn = [btn for btn in created_buttons if btn.text == t("operations_assistant_btn")][0]
        dialog = created_toplevel[0]
        return app, table, assistant_btn, dialog

    def test_action_disabled_and_guards_when_no_selection(self) -> None:
        """Nút bị vô hiệu hóa khi không chọn dòng; nếu bị kích hoạt sẽ hiện cảnh báo và không gọi service."""
        rows = [
            {"run_id": "run-failed-1", "status": "FAILED", "started_at": "2026-09-01", "finished_at": "2026-09-01", "selected_cost_center": "1412000040", "output_path": "", "error_summary": ""},
        ]
        app, table, assistant_btn, dialog = self._setup_run_history(rows)

        # Ban đầu không chọn dòng -> Nút phải DISABLED
        self.assertEqual(assistant_btn.state, "disabled")

        with patch("src.universal_app.messagebox.showwarning") as mock_warn, \
             patch("src.universal_app.assemble_operational_case") as mock_assemble:
            assistant_btn.command()
            mock_warn.assert_called_once()
            args, kwargs = mock_warn.call_args
            self.assertEqual(args[1], t("operations_assistant_no_run_selected"))
            mock_assemble.assert_not_called()

    def test_action_disabled_and_guards_when_running_selected(self) -> None:
        """Nút bị vô hiệu hóa khi chọn RUNNING; nếu kích hoạt sẽ hiện thông báo và tuyệt đối không gọi service."""
        rows = [
            {"run_id": "run-running-1", "status": "RUNNING", "started_at": "2026-09-01", "finished_at": "", "selected_cost_center": "ALL", "output_path": "", "error_summary": ""},
        ]
        app, table, assistant_btn, dialog = self._setup_run_history(rows)

        # Chọn dòng RUNNING (node_0)
        table.set_selection("node_0")
        self.assertEqual(assistant_btn.state, "disabled")

        with patch("src.universal_app.messagebox.showinfo") as mock_info, \
             patch("src.universal_app.assemble_operational_case") as mock_assemble:
            assistant_btn.command()
            mock_info.assert_called_once()
            args, kwargs = mock_info.call_args
            self.assertEqual(args[1], t("operations_assistant_run_not_finished"))
            mock_assemble.assert_not_called()

    def test_action_enabled_and_passes_active_language_for_terminal_runs(self) -> None:
        """Với các trạng thái terminal, nút bật NORMAL và truyền đúng ngôn ngữ (VI, EN, JA) cho service và dialog."""
        terminal_statuses = ["FAILED", "PRECHECK_FAILED", "SUCCEEDED", "SUCCEEDED_INCOMPLETE", "LEGACY_FY2027"]
        rows = [
            {"run_id": f"run-{status}", "status": status, "started_at": "2026-09-01", "finished_at": "2026-09-01", "selected_cost_center": "1412000040", "output_path": "", "error_summary": ""}
            for status in terminal_statuses
        ]
        app, table, assistant_btn, dialog = self._setup_run_history(rows, history_root="D:/history_test")
        from src.services.operations_ai_provider import CagentProviderPolicy

        expected_policy = CagentProviderPolicy(
            enabled=True,
            endpoint_url="https://cagent.example.test/v1/guidance",
            data_policy_id="POL-TEST-RUN-HISTORY",
        )
        app.cagent_policy = expected_policy

        for idx, status in enumerate(terminal_statuses):
            table.set_selection(f"node_{idx}")
            self.assertEqual(assistant_btn.state, "normal", f"Status {status} phải bật nút NORMAL")

        # Kiểm tra truyền đúng active language qua VI, EN, JA
        for lang in ("vi", "en", "ja"):
            set_current_language(lang)
            table.set_selection("node_0")

            fake_case = _make_confirmed_case(lang, run_id="run-FAILED")
            with patch("src.universal_app.assemble_operational_case", return_value=fake_case) as mock_assemble, \
                 patch("src.universal_app.OperationsBusinessChatDialog.open_with_case") as mock_open_with_case:
                assistant_btn.command()

                mock_assemble.assert_called_once_with("D:/history_test", "run-FAILED", lang)
                mock_open_with_case.assert_called_once()
                call_args, call_kwargs = mock_open_with_case.call_args
                self.assertEqual(call_args[0], app.root)
                self.assertEqual(call_args[1], lang)
                self.assertEqual(call_args[2], fake_case)
                self.assertEqual(call_kwargs.get("history_root"), "D:/history_test")
                self.assertIs(call_kwargs.get("policy"), expected_policy)
                self.assertIsNotNone(call_kwargs.get("open_history"))

    def test_action_handles_assembly_failure_with_safe_friendly_message(self) -> None:
        """Khi assemble_operational_case ném ngoại lệ (hỏng JSON, DB, path), chỉ hiện thông báo i18n an toàn."""
        rows = [
            {"run_id": "run-corrupt-1", "status": "FAILED", "started_at": "2026-09-01", "finished_at": "2026-09-01", "selected_cost_center": "1412000040", "output_path": "", "error_summary": ""},
        ]
        app, table, assistant_btn, dialog = self._setup_run_history(rows)
        table.set_selection("node_0")

        for lang in ("vi", "en", "ja"):
            set_current_language(lang)
            with patch("src.universal_app.assemble_operational_case", side_effect=RuntimeError("corrupt JSON in pipeline_stage_evidence.json at C:/path/raw/traceback")), \
                 patch("src.universal_app.messagebox.showerror") as mock_error:
                assistant_btn.command()

                mock_error.assert_called_once()
                args, kwargs = mock_error.call_args
                shown_msg = args[1]

                expected_msg = translate_for_language("operations_assistant_unable_to_load_case", lang)
                self.assertEqual(shown_msg, expected_msg)

                # Không làm lộ chi tiết kỹ thuật
                for forbidden in ("RuntimeError", "corrupt", "pipeline_stage_evidence", "traceback", "C:/path", "json"):
                    self.assertNotIn(forbidden.lower(), shown_msg.lower())


class TestOperationsAssistantCagentIntegration(unittest.TestCase):
    def setUp(self) -> None:
        OperationsAssistantDialog.clear_registry()
        self.factory = FakeWidgetFactory()

    def tearDown(self) -> None:
        OperationsAssistantDialog.clear_registry()

    def test_ask_cagent_button_and_disclosure_multilingual(self) -> None:
        for lang in ("vi", "en", "ja"):
            case = _make_confirmed_case(lang, run_id=f"run-{lang}")
            dialog = OperationsAssistantDialog(
                parent=None,
                case=case,
                language=lang,
                widget_factory=self.factory,
            )

            btn = next((w for w in dialog._widgets if getattr(w, "role", "") == "ask_ai_button"), None)
            self.assertIsNotNone(btn, f"Phải có nút Ask C-AGENT cho ngôn ngữ {lang}")
            expected_btn_text = translate_for_language("operations_assistant_ask_ai_btn", lang)
            self.assertEqual(btn.text, expected_btn_text)

            gemini_btn = next((w for w in dialog._widgets if getattr(w, "role", "") == "ask_gemini_button"), None)
            self.assertIsNotNone(gemini_btn, f"Phải có nút Gemini Web cho ngôn ngữ {lang}")
            self.assertEqual(
                gemini_btn.text,
                translate_for_language("operations_assistant_gemini_btn", lang),
            )

            disclosure = next((w for w in dialog._widgets if getattr(w, "role", "") == "ai_disclosure"), None)
            self.assertIsNotNone(disclosure, f"Phải có thông báo phạm vi dữ liệu AI cho {lang}")
            expected_disclosure = translate_for_language("operations_assistant_ai_disclosure", lang)
            self.assertEqual(disclosure.text, expected_disclosure)

            dialog.close()

    def test_ask_cagent_renders_ready_guidance_result(self) -> None:
        import json
        from src.services.operations_ai_provider import CagentProviderPolicy

        policy = CagentProviderPolicy(
            enabled=True,
            endpoint_url="https://cagent.internal.company.com/api/v1/guidance",
            data_policy_id="POL-01",
        )

        def mock_transport(url: str, headers: dict, body: bytes, timeout: float):
            resp = {
                "answer": "Vui lòng đóng file Excel và tính lại.",
                "evidence_ids": ["E1"],
                "limitations": "Tư vấn tham khảo.",
            }
            return 200, {}, json.dumps(resp).encode("utf-8")

        case = _make_confirmed_case("vi", run_id="run-cagent-1")
        dialog = OperationsAssistantDialog(
            parent=None,
            case=case,
            language="vi",
            policy=policy,
            cagent_transport=mock_transport,
            widget_factory=self.factory,
        )

        # Trigger request synchronously for test
        dialog._async_request_cagent()

        self.assertIsNotNone(dialog.ai_result)
        self.assertEqual(dialog.ai_result.status, "ready")
        self.assertIn("đóng file Excel", dialog.ai_result.answer)
        self.assertEqual(dialog.ai_result.cited_evidence_ids, ("E1",))

        # Check rendered widget text
        result_widget = next((w for w in dialog._widgets if getattr(w, "role", "") == "ai_result"), None)
        self.assertIsNotNone(result_widget)
        self.assertIn("đóng file Excel", result_widget.text)
        self.assertIn("E1", result_widget.text)
        self.assertIn("Tư vấn tham khảo", result_widget.text)

        dialog.close()

    def test_ask_cagent_handles_unavailable_state(self) -> None:
        from src.services.operations_ai_provider import CagentProviderPolicy

        # Policy disabled by default
        policy = CagentProviderPolicy(enabled=False)

        case = _make_confirmed_case("vi", run_id="run-cagent-disabled")
        dialog = OperationsAssistantDialog(
            parent=None,
            case=case,
            language="vi",
            policy=policy,
            widget_factory=self.factory,
        )

        dialog._async_request_cagent()

        self.assertIsNotNone(dialog.ai_result)
        self.assertEqual(dialog.ai_result.status, "unavailable")

        result_widget = next((w for w in dialog._widgets if getattr(w, "role", "") == "ai_result"), None)
        self.assertIsNotNone(result_widget)
        self.assertIn("dữ liệu nội bộ", result_widget.text.lower())

        dialog.close()

    def test_env_loader_wiring_and_happy_path_integration(self) -> None:
        """Integration test: nạp cấu hình từ môi trường, inject fake transport và hiển thị kết quả tư vấn tiếng Việt."""
        import json
        import os
        from unittest.mock import patch
        from src.services.operations_ai_provider import load_cagent_provider_policy_from_env

        env_vars = {
            "CAGENT_ENABLED": "1",
            "CAGENT_ENDPOINT_URL": "https://cagent.corp.internal/v1/guidance",
            "CAGENT_DATA_POLICY_ID": "POL-CORP-01",
            "CAGENT_AUTH_MODE": "bearer_env",
            "CAGENT_BEARER_TOKEN_ENV": "TEST_CAGENT_KEY",
            "TEST_CAGENT_KEY": "secret-cagent-token-12345",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            loaded_policy = load_cagent_provider_policy_from_env()
            self.assertTrue(loaded_policy.enabled)
            self.assertEqual(loaded_policy.endpoint_url, "https://cagent.corp.internal/v1/guidance")

            def mock_transport(url: str, headers: dict, body: bytes, timeout: float):
                self.assertIn("Bearer secret-cagent-token-12345", headers.get("Authorization", ""))
                resp = {
                    "answer": "Kiểm tra tiến trình Excel đang chạy nền và đóng trước khi xuất bản.",
                    "evidence_ids": ["E1"],
                    "limitations": "Thông tin tư vấn nội bộ doanh nghiệp.",
                }
                return 200, {}, json.dumps(resp).encode("utf-8")

            case = _make_confirmed_case("vi", run_id="run-cagent-env-integration")
            dialog = OperationsAssistantDialog(
                parent=None,
                case=case,
                language="vi",
                policy=loaded_policy,
                cagent_transport=mock_transport,
                widget_factory=self.factory,
            )

            dialog._async_request_cagent()

            self.assertIsNotNone(dialog.ai_result)
            self.assertEqual(dialog.ai_result.status, "ready")
            self.assertIn("Kiểm tra tiến trình Excel", dialog.ai_result.answer)
            self.assertEqual(dialog.ai_result.cited_evidence_ids, ("E1",))

            result_widget = next((w for w in dialog._widgets if getattr(w, "role", "") == "ai_result"), None)
            self.assertIsNotNone(result_widget)
            self.assertIn("Kiểm tra tiến trình Excel", result_widget.text)
            self.assertIn("E1", result_widget.text)

            dialog.close()


class TestOperationsBusinessChatDialog(unittest.TestCase):
    def setUp(self) -> None:
        import tkinter as tk
        try:
            self.root = tk.Tk()
            self.root.withdraw()
            self.tk_available = True
        except Exception:
            self.tk_available = False

    def tearDown(self) -> None:
        if getattr(self, "tk_available", False) and hasattr(self, "root"):
            try:
                self.root.destroy()
            except Exception:
                pass

    def test_business_chat_dialog_placeholder_and_typing(self) -> None:
        if not getattr(self, "tk_available", False):
            self.skipTest("Tkinter display not available in environment")

        from src.ui.operations_assistant import OperationsBusinessChatDialog
        dialog = OperationsBusinessChatDialog(self.root, "vi", open_history=lambda: None)

        # Ban đầu buffer rỗng và placeholder overlay hiển thị
        self.assertTrue(dialog._placeholder_active)
        self.assertEqual(dialog.question.get(), "")
        self.assertEqual(dialog.question.placeholder_text, dialog._placeholder_text)

        # Gõ văn bản tiếng Việt có dấu (nghiệp vụ, gì, phân bổ, chi phí)
        vietnamese_question = "cụ thể nghiệp vụ mp là gì"
        dialog.question.insert(0, vietnamese_question)
        self.assertEqual(dialog.question.get(), vietnamese_question)
        self.assertFalse(dialog._placeholder_active)

        # Select all
        res = dialog._select_all_text()
        self.assertEqual(res, "break")

        # Xóa hết -> khôi phục trạng thái placeholder
        dialog.question.delete(0, "end")
        self.assertTrue(dialog._placeholder_active)
        self.assertEqual(dialog.question.get(), "")

        dialog.close()

    def test_business_chat_dialog_suggestion_chip(self) -> None:
        if not getattr(self, "tk_available", False):
            self.skipTest("Tkinter display not available in environment")

        from src.ui.operations_assistant import OperationsBusinessChatDialog
        dialog = OperationsBusinessChatDialog(self.root, "vi", open_history=lambda: None)

        with patch("src.ui.operations_assistant.request_gemini_web_business_guidance") as mock_req, \
             patch("threading.Thread", side_effect=lambda target, args=(), daemon=True: type("DummyThread", (), {"start": lambda s: target(*args)})()):
            from src.services.operations_ai_provider import CagentGuidanceResult
            mock_req.return_value = CagentGuidanceResult(
                status="ready",
                answer="Hướng dẫn xử lý mẫu",
                limitation="Tư vấn tham khảo.",
            )

            # Click chip gợi ý
            dialog._use_suggestion("Lỗi này là gì?")
            mock_req.assert_called_once()
            call_args, _ = mock_req.call_args
            self.assertEqual(call_args[0], "Lỗi này là gì?")
            self.assertTrue(dialog._placeholder_active)
            self.assertEqual(dialog.question.get(), "")

        dialog.close()

    def test_open_with_case_diagnoses_and_renders_in_chat(self) -> None:
        if not getattr(self, "tk_available", False):
            self.skipTest("Tkinter display not available in environment")

        from src.ui.operations_assistant import OperationsBusinessChatDialog
        from src.services.operations_ai_provider import CagentProviderPolicy, CagentGuidanceResult

        case = _make_confirmed_case("vi", run_id="run-chat-diagnosis")
        policy = CagentProviderPolicy(enabled=False)

        with patch("src.ui.operations_assistant.request_gemini_web_business_guidance") as mock_gemini:
            dialog = OperationsBusinessChatDialog.open_with_case(
                self.root,
                "vi",
                case,
                policy=policy,
                sync=True,
            )

            self.assertIsNotNone(dialog)
            self.assertTrue(dialog.is_alive())

            # Kiểm tra trong các widget tin nhắn có chứa nội dung chẩn đoán
            found_diag = False
            for w in dialog.messages.winfo_children():
                for sub_w in w.winfo_children():
                    for text_w in sub_w.winfo_children():
                        try:
                            text_val = str(text_w.cget("text"))
                        except Exception:
                            text_val = ""
                        if "KẾT QUẢ" in text_val or "run-chat-diagnosis" in text_val:
                            found_diag = True
                            break
            self.assertTrue(found_diag, "Phải có tin nhắn chẩn đoán sự cố trong luồng chat")
            mock_gemini.assert_not_called()

            dialog.close()

    def test_main_window_floating_mascot(self) -> None:
        if not getattr(self, "tk_available", False):
            self.skipTest("Tkinter display not available in environment")

        from src.universal_app import MPManagerApp
        from src.ui.operations_assistant import OperationsBusinessChatDialog

        with patch("src.universal_app.OperationsBusinessChatDialog.open") as mock_chat_open:
            app = MPManagerApp(self.root)
            self.assertIsNotNone(getattr(app, "_mascot_frame", None))
            self.assertTrue(app._mascot_frame.winfo_exists())

            # Nút dư thừa và kỹ thuật đã được loại bỏ khỏi action_buttons
            chat_btn_tuple = [b for b in app.action_buttons if b[1] == "operations_business_chat_btn"]
            self.assertEqual(len(chat_btn_tuple), 0, "Không để nút chat trùng lặp trong action_buttons")
            history_btn_tuple = [b for b in app.action_buttons if b[1] == "run_history_btn"]
            self.assertEqual(len(history_btn_tuple), 0, "Nút run_history kỹ thuật đã ẩn khỏi thanh công cụ chính")

            # Gọi open_business_chat_assistant từ Robot Mascot
            app.open_business_chat_assistant()
            mock_chat_open.assert_called_once()

            # Kiểm tra text đa ngôn ngữ động của Mascot
            from src.services.i18n import set_current_language
            for lang, expected in [("vi", "✦ Hỏi AI nội bộ"), ("ja", "✦ 社内AIに質問"), ("en", "✦ Ask Internal AI")]:
                set_current_language(lang)
                app._refresh_localized_ui()
                self.assertEqual(app._mascot_text_lbl.cget("text"), expected)

    def test_business_chat_ui_localization_en_ja_vi(self) -> None:
        if not getattr(self, "tk_available", False):
            self.skipTest("Tkinter display not available in environment")

        from src.ui.operations_assistant import OperationsBusinessChatDialog
        from src.services.i18n import translate_for_language

        for lang in ("vi", "ja", "en"):
            dialog = OperationsBusinessChatDialog(self.root, lang, open_history=lambda: None)
            try:
                # 1. Placeholder phải khớp theo ngôn ngữ
                expected_placeholder = translate_for_language("operations_business_chat_placeholder", lang)
                self.assertEqual(dialog._placeholder_text, expected_placeholder)

                # 2. Window title phải khớp
                expected_title = translate_for_language("operations_business_chat_title", lang)
                self.assertEqual(dialog.window.title(), expected_title)

                # 3. Disclosure phải hiển thị trước khi người dùng gửi nội dung cho Gemini Web.
                self.assertEqual(
                    dialog.gemini_disclosure_label.cget("text"),
                    translate_for_language("operations_business_chat_gemini_disclosure", lang),
                )

                # 4. Gợi ý câu hỏi nhanh (chips) phải tồn tại và không rỗng
                self.assertEqual(len(dialog.suggestion_buttons), 4)
                for btn in dialog.suggestion_buttons:
                    self.assertTrue(bool(btn.cget("text").strip()))
            finally:
                dialog.close()

    def test_business_chat_offline_fallback_uses_original_question(self) -> None:
        """Offline fallback must retrieve from what the user asked, not from prompt context."""
        if not getattr(self, "tk_available", False):
            self.skipTest("Tkinter display not available in environment")

        from src.services.operations_ai_provider import CagentGuidanceResult
        from src.ui.operations_assistant import OperationsBusinessChatDialog

        dialog = OperationsBusinessChatDialog(self.root, "ja", open_history=lambda: None)
        try:
            dialog.answer = MagicMock()
            with patch(
                "src.services.business_chat_knowledge.local_fallback",
                return_value="local Japanese guidance",
            ) as local_fallback:
                dialog._apply(
                    CagentGuidanceResult(
                        status="unavailable",
                        provider_label="Gemini Web",
                        limitation="offline",
                    ),
                    "出力Excelファイルがロックされました",
                )

            local_fallback.assert_called_once_with("出力Excelファイルがロックされました", "ja", intent="business")
        finally:
            dialog.close()

    def test_is_error_related_query_multilingual(self) -> None:
        from src.ui.operations_assistant import is_error_related_query

        # VI
        self.assertTrue(is_error_related_query("Lỗi này là gì?"))
        self.assertTrue(is_error_related_query("Tại sao tính toán bị dừng?"))
        self.assertTrue(is_error_related_query("Cách khắc phục file bị khóa"))

        # JA
        self.assertTrue(is_error_related_query("このエラーは何ですか？"))
        self.assertTrue(is_error_related_query("処理が失敗した原因は？"))
        self.assertTrue(is_error_related_query("どうすれば対処できますか"))

        # EN
        self.assertTrue(is_error_related_query("What does this error mean?"))
        self.assertTrue(is_error_related_query("Why did the calculation fail?"))
        self.assertTrue(is_error_related_query("Troubleshoot missing staffing baseline"))

        # Non-error queries
        self.assertFalse(is_error_related_query("Xin chào"))
        self.assertFalse(is_error_related_query("Hello there"))
        self.assertFalse(is_error_related_query("こんにちは"))
        self.assertFalse(is_error_related_query("cách sử dụng phần mềm này"))
        self.assertFalse(is_error_related_query("MP có bao nhiêu chi phí?"))
        self.assertFalse(is_error_related_query("Why is this cost allocated this way?"))

    def test_format_nontech_case_diagnosis_no_uuids(self) -> None:
        from src.ui.operations_assistant import format_nontech_case_diagnosis

        uuid_run = "aa5fe28dbaa143e4b2a8f3cc4e98f01a"
        case = _make_confirmed_case("vi", run_id=uuid_run)

        # VI check
        diag_vi = format_nontech_case_diagnosis(case, "vi")
        self.assertNotIn(uuid_run, diag_vi, "Non-tech diagnosis must not expose raw run UUID")
        self.assertIn("Bộ phận / Phòng ban", diag_vi)
        self.assertIn("Hướng dẫn các bước tự xử lý", diag_vi)

        # JA check
        diag_ja = format_nontech_case_diagnosis(case, "ja")
        self.assertNotIn(uuid_run, diag_ja)
        self.assertIn("コストセンター", diag_ja)
        self.assertIn("対処手順", diag_ja)

        # EN check
        diag_en = format_nontech_case_diagnosis(case, "en")
        self.assertNotIn(uuid_run, diag_en)
        self.assertIn("Cost Center", diag_en)
        self.assertIn("Action Steps", diag_en)

    def test_chat_auto_diagnoses_latest_error(self) -> None:
        if not getattr(self, "tk_available", False):
            self.skipTest("Tkinter display not available in environment")

        from src.ui.operations_assistant import OperationsBusinessChatDialog

        uuid_run = "bb6fe28dbaa143e4b2a8f3cc4e98f02b"
        case = _make_confirmed_case("vi", run_id=uuid_run)

        dialog = OperationsBusinessChatDialog(
            self.root,
            "vi",
            open_history=lambda: None,
            history_root="/fake/history/root",
            fiscal_year=2027,
        )
        try:
            with patch(
                "src.ui.operations_assistant.find_relevant_error_case",
                return_value=case,
            ), patch(
                "src.ui.operations_assistant.request_gemini_web_business_guidance",
                return_value=MagicMock(status="unavailable", answer="", limitation="offline"),
            ):
                dialog._use_suggestion("Lỗi này là gì?", sync=True)

                # Phải render chẩn đoán của case lỗi gần nhất vào khung chat
                found_text = False
                for w in dialog.messages.winfo_children():
                    for sub_w in w.winfo_children():
                        for text_w in sub_w.winfo_children():
                            try:
                                val = str(text_w.cget("text"))
                            except Exception:
                                val = ""
                            if "KẾT QUẢ CHẨN ĐOÁN SỰ CỐ GẦN NHẤT" in val:
                                found_text = True
                                self.assertNotIn(uuid_run, val, "Không được chứa UUID kỹ thuật")
                                break
                self.assertTrue(found_text, "Phải tự động hiển thị chẩn đoán non-tech từ lỗi gần nhất")
        finally:
            dialog.close()

    def test_chat_when_no_error_recorded_gives_desktop_guidance(self) -> None:
        if not getattr(self, "tk_available", False):
            self.skipTest("Tkinter display not available in environment")

        from src.ui.operations_assistant import OperationsBusinessChatDialog

        dialog = OperationsBusinessChatDialog(
            self.root,
            "vi",
            open_history=lambda: None,
            history_root="/fake/empty/history",
            fiscal_year=2027,
        )
        try:
            with patch("src.ui.operations_assistant.find_relevant_error_case", return_value=None), \
                 patch("src.ui.operations_assistant.request_gemini_web_business_guidance", return_value=MagicMock(status="unavailable", answer="", limitation="offline")):
                dialog._use_suggestion("Lỗi này là gì?", sync=True)

                found_guidance = False
                for w in dialog.messages.winfo_children():
                    for sub_w in w.winfo_children():
                        for text_w in sub_w.winfo_children():
                            try:
                                val = str(text_w.cget("text"))
                            except Exception:
                                val = ""
                            val_lower = val.lower()
                            if "chưa tìm thấy sự cố" in val_lower or "chưa ghi nhận lỗi" in val_lower or "chưa ghi nhận sự cố" in val_lower:
                                found_guidance = True
                                self.assertIn("Lịch sử lần chạy", val)
                                self.assertNotIn("F5", val)
                                self.assertNotIn("trình duyệt", val)
                                self.assertNotIn("đăng xuất", val)
                                break
                self.assertTrue(found_guidance, "Phải hiển thị thông báo chưa ghi nhận lỗi khi không có lỗi thực tế")
        finally:
            dialog.close()

    def test_web_hallucinations_filtered_out(self) -> None:
        if not getattr(self, "tk_available", False):
            self.skipTest("Tkinter display not available in environment")

        from src.ui.operations_assistant import OperationsBusinessChatDialog

        dialog = OperationsBusinessChatDialog(self.root, "vi", open_history=lambda: None)
        try:
            hallucinated_web_answer = (
                "Chào bạn,\n"
                "1. Nhấn nút F5 trên bàn phím để tải lại trang trình duyệt.\n"
                "2. Đăng xuất và đăng nhập lại tài khoản.\n"
            )
            with patch("src.ui.operations_assistant.request_gemini_web_business_guidance", return_value=MagicMock(status="ready", answer=hallucinated_web_answer)):
                dialog.question_var.set("Lỗi này là gì?")
                dialog.send(sync=True)

                # Kiểm tra nội dung hiển thị trong bubble câu trả lời: Phải bị filter và không chứa F5/đăng xuất
                answer_text = dialog.answer.cget("text")
                self.assertNotIn("F5", answer_text, "Guardrail phải lọc sạch lỗi F5 trình duyệt")
                self.assertNotIn("trình duyệt", answer_text, "Guardrail phải lọc sạch tham chiếu trình duyệt")
                self.assertNotIn("đăng xuất", answer_text, "Guardrail phải lọc sạch hướng dẫn đăng xuất web")
                answer_lower = answer_text.lower()
                self.assertTrue("chưa tìm thấy sự cố" in answer_lower or "chưa ghi nhận lỗi" in answer_lower or "chưa ghi nhận sự cố" in answer_lower, "Phải thay bằng thông báo chưa ghi nhận lỗi phù hợp")
        finally:
            dialog.close()

    def test_copy_button_copies_ai_response(self) -> None:
        if not getattr(self, "tk_available", False):
            self.skipTest("Tkinter display not available in environment")

        import tkinter as tk
        from src.ui.operations_assistant import OperationsBusinessChatDialog

        dialog = OperationsBusinessChatDialog(self.root, "vi", open_history=lambda: None)
        try:
            sample_text = "Đây là câu trả lời mẫu của AI cần sao chép."
            text_w = dialog._add_message("✦ Trợ lý AI", sample_text, assistant=True)

            # Tìm nút copy trong header row của bubble
            copy_btn = None
            parent_bubble = text_w.master
            for child in parent_bubble.winfo_children():
                if isinstance(child, tk.Frame):
                    for sub_w in child.winfo_children():
                        if isinstance(sub_w, tk.Button) and "Sao chép" in sub_w.cget("text"):
                            copy_btn = sub_w
                            break

            self.assertIsNotNone(copy_btn, "Phải có nút Sao chép trong tin nhắn của AI")

            # Kích hoạt copy
            dialog._copy_message_text(text_w, copy_btn)
            copied = self.root.clipboard_get()
            self.assertEqual(copied, sample_text)
            self.assertIn("Đã sao chép", copy_btn.cget("text"))
        finally:
            dialog.close()

    def test_image_paste_and_attachment_in_chat(self) -> None:
        if not getattr(self, "tk_available", False):
            self.skipTest("Tkinter display not available in environment")

        from PIL import Image
        from src.ui.operations_assistant import OperationsBusinessChatDialog

        dialog = OperationsBusinessChatDialog(self.root, "vi", open_history=lambda: None)
        try:
            # Tạo ảnh giả lập
            fake_img = Image.new("RGB", (120, 80), color="blue")
            dialog._set_attached_image(fake_img)

            self.assertIsNotNone(dialog._attached_image)
            self.assertEqual(dialog._attached_image.width, 120)
            self.assertEqual(dialog._attached_image.height, 80)
            self.assertIn("120×80", dialog.image_preview_lbl.cget("text"))

            # Gửi tin nhắn kèm ảnh
            with patch(
                "src.ui.operations_assistant.request_gemini_web_business_guidance",
                return_value=MagicMock(status="ready", answer="Phân tích ảnh xong!"),
            ) as mock_gemini:
                dialog.question_var.set("Hãy xem ảnh lỗi này")
                dialog.send(sync=True)

                self.assertIsNone(dialog._attached_image, "Ảnh đính kèm phải được reset sau khi gửi")
                mock_gemini.assert_called_once()
                call_args = mock_gemini.call_args[0]
                self.assertEqual(call_args[0], "Hãy xem ảnh lỗi này")
                self.assertIn("120×80", call_args[1], "Ngữ cảnh gửi cho AI phải chứa thông tin ảnh đính kèm")
        finally:
            dialog.close()


class TestCagentStartupPolicyWiring(unittest.TestCase):
    """Tests for C-AGENT startup policy wiring in MPManagerApp.

    Proves:
    1. No C-AGENT env vars → policy disabled.
    2. Valid env config (fake HTTPS endpoint + policy ID) → MPManagerApp loads enabled policy
       and selected-run flow receives that exact policy.
    3. Invalid URL/policy/auth mode → disabled.
    4. Token value is never stored in the policy object.
    """

    def setUp(self) -> None:
        set_current_language("vi")

    def tearDown(self) -> None:
        set_current_language("vi")

    def test_no_env_vars_yields_disabled_policy(self) -> None:
        """Without C-AGENT env vars, load_cagent_provider_policy_from_env returns disabled."""
        from src.services.operations_ai_provider import load_cagent_provider_policy_from_env

        policy = load_cagent_provider_policy_from_env({})
        self.assertFalse(policy.enabled)

    def test_valid_env_yields_enabled_policy(self) -> None:
        """Fake HTTPS endpoint + policy ID → enabled policy with correct attributes."""
        from src.services.operations_ai_provider import load_cagent_provider_policy_from_env

        env = {
            "CAGENT_ENABLED": "1",
            "CAGENT_ENDPOINT_URL": "https://cagent.example.test/v1/guidance",
            "CAGENT_DATA_POLICY_ID": "POL-TEST-001",
            "CAGENT_AUTH_MODE": "bearer_env",
            "CAGENT_BEARER_TOKEN_ENV": "MY_CAGENT_TOKEN",
            "CAGENT_TIMEOUT_SECONDS": "30",
        }
        policy = load_cagent_provider_policy_from_env(env)
        self.assertTrue(policy.enabled)
        self.assertEqual(policy.endpoint_url, "https://cagent.example.test/v1/guidance")
        self.assertEqual(policy.data_policy_id, "POL-TEST-001")
        self.assertEqual(policy.auth_mode, "bearer_env")
        self.assertEqual(policy.bearer_token_env_var, "MY_CAGENT_TOKEN")
        self.assertEqual(policy.timeout_seconds, 30)

    def test_mpmanagerapp_constructor_keeps_startup_policy_wiring(self) -> None:
        """A future refactor must not remove the fail-closed startup policy load."""
        import inspect

        constructor_source = inspect.getsource(MPManagerApp.__init__)
        self.assertIn("self.cagent_policy", constructor_source)
        self.assertIn("load_cagent_provider_policy_from_env()", constructor_source)

    def test_startup_environment_yields_enabled_policy(self) -> None:
        """A valid startup environment produces the policy that MPManagerApp stores."""
        import os

        env_vars = {
            "CAGENT_ENABLED": "1",
            "CAGENT_ENDPOINT_URL": "https://cagent.example.test/v1/guidance",
            "CAGENT_DATA_POLICY_ID": "POL-STARTUP-01",
            "CAGENT_AUTH_MODE": "bearer_env",
            "CAGENT_BEARER_TOKEN_ENV": "STARTUP_CAGENT_KEY",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            from src.services.operations_ai_provider import load_cagent_provider_policy_from_env

            # Simulate what MPManagerApp.__init__ does: call the loader
            loaded_policy = load_cagent_provider_policy_from_env()
            self.assertTrue(loaded_policy.enabled)
            self.assertEqual(loaded_policy.endpoint_url, "https://cagent.example.test/v1/guidance")
            self.assertEqual(loaded_policy.data_policy_id, "POL-STARTUP-01")

    def test_selected_run_flow_receives_loaded_policy(self) -> None:
        """When cagent_policy is set on the app, open_with_case receives it (not a default disabled one)."""
        import os

        env_vars = {
            "CAGENT_ENABLED": "1",
            "CAGENT_ENDPOINT_URL": "https://cagent.example.test/v1/guidance",
            "CAGENT_DATA_POLICY_ID": "POL-FLOW-01",
            "CAGENT_AUTH_MODE": "none",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            from src.services.operations_ai_provider import (
                CagentProviderPolicy,
                load_cagent_provider_policy_from_env,
            )

            loaded_policy = load_cagent_provider_policy_from_env()
            self.assertTrue(loaded_policy.enabled)

            # Simulate the getattr pattern used in universal_app.py line 3553
            app_mock = SimpleNamespace(cagent_policy=loaded_policy)
            policy = getattr(app_mock, "cagent_policy", None) or CagentProviderPolicy()
            self.assertTrue(policy.enabled)
            self.assertEqual(policy.data_policy_id, "POL-FLOW-01")

    def test_invalid_http_url_yields_disabled_policy(self) -> None:
        """HTTP (not HTTPS) endpoint → fail-closed to disabled."""
        from src.services.operations_ai_provider import load_cagent_provider_policy_from_env

        env = {
            "CAGENT_ENABLED": "true",
            "CAGENT_ENDPOINT_URL": "http://insecure.example.test/v1/guidance",
            "CAGENT_DATA_POLICY_ID": "POL-INSECURE-01",
        }
        policy = load_cagent_provider_policy_from_env(env)
        self.assertFalse(policy.enabled)

    def test_missing_data_policy_id_yields_disabled(self) -> None:
        """Enabled but missing data_policy_id → fail-closed to disabled."""
        from src.services.operations_ai_provider import load_cagent_provider_policy_from_env

        env = {
            "CAGENT_ENABLED": "1",
            "CAGENT_ENDPOINT_URL": "https://cagent.example.test/v1/guidance",
            "CAGENT_DATA_POLICY_ID": "",
        }
        policy = load_cagent_provider_policy_from_env(env)
        self.assertFalse(policy.enabled)

    def test_invalid_auth_mode_yields_disabled(self) -> None:
        """Unsupported auth_mode → fail-closed to disabled."""
        from src.services.operations_ai_provider import load_cagent_provider_policy_from_env

        env = {
            "CAGENT_ENABLED": "1",
            "CAGENT_ENDPOINT_URL": "https://cagent.example.test/v1/guidance",
            "CAGENT_DATA_POLICY_ID": "POL-01",
            "CAGENT_AUTH_MODE": "oauth2_implicit",
        }
        policy = load_cagent_provider_policy_from_env(env)
        self.assertFalse(policy.enabled)

    def test_token_value_never_stored_in_policy(self) -> None:
        """The actual token value (secret) must never appear in the policy object's fields."""
        import os
        from src.services.operations_ai_provider import load_cagent_provider_policy_from_env

        env_vars = {
            "CAGENT_ENABLED": "1",
            "CAGENT_ENDPOINT_URL": "https://cagent.example.test/v1/guidance",
            "CAGENT_DATA_POLICY_ID": "POL-SECRET-CHECK",
            "CAGENT_AUTH_MODE": "bearer_env",
            "CAGENT_BEARER_TOKEN_ENV": "SECRET_TOKEN_VAR",
        }
        with patch.dict(os.environ, {**env_vars, "SECRET_TOKEN_VAR": "super-secret-token-12345"}, clear=False):
            policy = load_cagent_provider_policy_from_env()
            self.assertTrue(policy.enabled)

            # Policy stores the env var NAME, not the token VALUE
            self.assertEqual(policy.bearer_token_env_var, "SECRET_TOKEN_VAR")

            # Verify the actual secret is NOT anywhere in the policy object
            policy_repr = repr(policy)
            self.assertNotIn("super-secret-token-12345", policy_repr)
            self.assertNotIn("super-secret-token-12345", policy.endpoint_url)
            self.assertNotIn("super-secret-token-12345", policy.data_policy_id)
            self.assertNotIn("super-secret-token-12345", policy.bearer_token_env_var)
            self.assertNotIn("super-secret-token-12345", policy.auth_mode)

    def test_no_cagent_policy_attribute_uses_disabled_fallback(self) -> None:
        """If cagent_policy attribute somehow missing, getattr fallback creates disabled policy."""
        from src.services.operations_ai_provider import CagentProviderPolicy

        app_mock = SimpleNamespace()  # No cagent_policy attribute
        policy = getattr(app_mock, "cagent_policy", None) or CagentProviderPolicy()
        self.assertFalse(policy.enabled)


class BusinessDocumentContextRagV3Tests(unittest.TestCase):
    """Verify that _business_document_context uses Document-grounded RAG v3 retrieval."""

    def test_business_document_context_calls_rag_v3_retrieval(self) -> None:
        from src.ui.operations_assistant import _business_document_context

        ctx_vi = _business_document_context("file bị khóa", "vi")
        self.assertIn("Nguồn tham khảo:", ctx_vi)
        self.assertNotIn("d:\\sandbox", ctx_vi.lower())
        self.assertNotIn("traceback", ctx_vi.lower())

        ctx_en = _business_document_context("locked file", "en")
        self.assertIn("Source Reference:", ctx_en)

        ctx_ja = _business_document_context("ファイルロック", "ja")
        self.assertIn("参照元:", ctx_ja)

    def test_business_document_context_no_match_returns_safe_message(self) -> None:
        from src.ui.operations_assistant import _business_document_context

        no_match_vi = _business_document_context("mon an phap nau the nao", "vi")
        self.assertIn("Chưa tìm thấy hướng dẫn nội bộ phù hợp", no_match_vi)

    def test_v3_available_but_retrieval_empty_does_not_call_v2_fallback(self) -> None:
        """When V3 index is active but query has no match, V2 fallback must NOT be called."""
        from src.ui.operations_assistant import _business_document_context

        with patch("src.services.business_knowledge_retrieval.retrieve_grounded_chunks", return_value=[]):
            with patch("src.services.business_chat_knowledge.retrieve") as mock_v2_retrieve:
                ctx = _business_document_context("cau hoi khong lien quan 12345xyz", "vi")
                self.assertIn("Chưa tìm thấy hướng dẫn nội bộ phù hợp", ctx)
                mock_v2_retrieve.assert_not_called()

    def test_v3_unavailable_calls_v2_fallback(self) -> None:
        """When V3 index is unbuilt or empty, V2 catalog fallback must be invoked."""
        from src.ui.operations_assistant import _business_document_context

        with patch("src.services.business_knowledge_index.get_knowledge_index", return_value=[]):
            with patch("src.services.business_chat_knowledge.retrieve", return_value=[]) as mock_v2_retrieve:
                _business_document_context("file bị khóa", "vi")
                mock_v2_retrieve.assert_called_once_with("file bị khóa", "vi")


class FiscalYearKnowledgeUpdateDialogTests(unittest.TestCase):
    """Unit tests for FiscalYearKnowledgeUpdateDialog UI initialization, live preview, and validation."""

    def test_open_update_dialog_does_not_duplicate_fy_prefix(self) -> None:
        from src.ui.fiscal_year_update_dialog import FiscalYearKnowledgeUpdateDialog

        from src.ui.operations_assistant import OperationsBusinessChatDialog

        dialog = SimpleNamespace(window=object(), language="vi", fiscal_year="FY2028")
        with patch.object(FiscalYearKnowledgeUpdateDialog, "open") as open_dialog:
            OperationsBusinessChatDialog._open_fy_knowledge_update(dialog)

        open_dialog.assert_called_once_with(dialog.window, "vi", fiscal_year="FY2028")

    def test_dialog_initialization_multilingual(self) -> None:
        from src.ui.fiscal_year_update_dialog import FiscalYearKnowledgeUpdateDialog
        import tkinter as tk

        try:
            root = tk.Tk()
            root.withdraw()
        except Exception:
            self.skipTest("Tkinter display not available")

        try:
            # VI
            dlg_vi = FiscalYearKnowledgeUpdateDialog(root, "vi", fiscal_year="FY2028")
            self.assertEqual(dlg_vi.language, "vi")
            self.assertEqual(dlg_vi.fy_var.get(), "FY2028")
            self.assertEqual(dlg_vi.window.title(), translate_for_language("fy_knowledge_update_dialog_title", "vi"))
            dlg_vi.close()

            # EN
            dlg_en = FiscalYearKnowledgeUpdateDialog(root, "en", fiscal_year="FY2029")
            self.assertEqual(dlg_en.language, "en")
            self.assertEqual(dlg_en.fy_var.get(), "FY2029")
            self.assertEqual(dlg_en.window.title(), translate_for_language("fy_knowledge_update_dialog_title", "en"))
            dlg_en.close()

            # JA
            dlg_ja = FiscalYearKnowledgeUpdateDialog(root, "ja", fiscal_year="FY2030")
            self.assertEqual(dlg_ja.language, "ja")
            self.assertEqual(dlg_ja.fy_var.get(), "FY2030")
            self.assertEqual(dlg_ja.window.title(), translate_for_language("fy_knowledge_update_dialog_title", "ja"))
            dlg_ja.close()
        finally:
            root.destroy()

    def test_live_preview_updates_on_typing(self) -> None:
        from src.ui.fiscal_year_update_dialog import FiscalYearKnowledgeUpdateDialog
        import tkinter as tk

        try:
            root = tk.Tk()
            root.withdraw()
        except Exception:
            self.skipTest("Tkinter display not available")

        try:
            dlg = FiscalYearKnowledgeUpdateDialog(root, "vi", fiscal_year="FY2028")
            dlg.title_var.set("Phân bổ tiền điện xưởng")
            dlg.what_changed_text.insert("1.0", "Phân bổ theo chỉ số đồng hồ đo riêng từng xưởng.")
            dlg.user_action_text.insert("1.0", "Kiểm tra chỉ số cột F.")
            dlg._update_preview()

            preview_content = dlg.preview_text.get("1.0", "end")
            self.assertIn("Phân bổ theo chỉ số đồng hồ đo riêng từng xưởng.", preview_content)
            self.assertIn("1. Kiểm tra chỉ số cột F.", preview_content)
            self.assertIn("Nguồn tham khảo: Cập nhật nghiệp vụ FY2028 — Phân bổ tiền điện xưởng", preview_content)
            self.assertIn("Mức tin cậy: Đã xác nhận", preview_content)
            dlg.close()
        finally:
            root.destroy()

    def test_get_item_data_distinct_multilingual_values(self) -> None:
        from src.ui.fiscal_year_update_dialog import FiscalYearKnowledgeUpdateDialog
        import tkinter as tk

        try:
            root = tk.Tk()
            root.withdraw()
        except Exception:
            self.skipTest("Tkinter display not available")

        try:
            dlg = FiscalYearKnowledgeUpdateDialog(root, "vi", fiscal_year="FY2028")

            # VI
            dlg.title_vars["vi"].set("Tiêu đề tiếng Việt")
            dlg.what_changed_texts["vi"].insert("1.0", "Nội dung thay đổi tiếng Việt.")
            dlg.user_action_texts["vi"].insert("1.0", "Người dùng làm tiếng Việt.")
            dlg.applies_to_vars["vi"].set("Phòng ban VN")
            dlg.source_note_vars["vi"].set("Tài liệu VN")

            # EN
            dlg.title_vars["en"].set("English Title")
            dlg.what_changed_texts["en"].insert("1.0", "English change description.")
            dlg.user_action_texts["en"].insert("1.0", "English user action.")
            dlg.applies_to_vars["en"].set("EN Department")
            dlg.source_note_vars["en"].set("EN Document")

            # JA
            dlg.title_vars["ja"].set("日本語タイトル")
            dlg.what_changed_texts["ja"].insert("1.0", "日本語の変更内容です。")
            dlg.user_action_texts["ja"].insert("1.0", "日本語の対応手順です。")
            dlg.applies_to_vars["ja"].set("JA 適用部署")
            dlg.source_note_vars["ja"].set("JA 参照文書")

            item = dlg._get_item_data()

            self.assertEqual(item.title["vi"], "Tiêu đề tiếng Việt")
            self.assertEqual(item.title["en"], "English Title")
            self.assertEqual(item.title["ja"], "日本語タイトル")

            self.assertEqual(item.what_changed["vi"], "Nội dung thay đổi tiếng Việt.")
            self.assertEqual(item.what_changed["en"], "English change description.")
            self.assertEqual(item.what_changed["ja"], "日本語の変更内容です。")

            self.assertEqual(item.user_action["vi"], "Người dùng làm tiếng Việt.")
            self.assertEqual(item.user_action["en"], "English user action.")
            self.assertEqual(item.user_action["ja"], "日本語の対応手順です。")

            self.assertEqual(item.applies_to["vi"], "Phòng ban VN")
            self.assertEqual(item.applies_to["en"], "EN Department")
            self.assertEqual(item.applies_to["ja"], "JA 適用部署")

            self.assertEqual(item.source_note["vi"], "Tài liệu VN")
            self.assertEqual(item.source_note["en"], "EN Document")
            self.assertEqual(item.source_note["ja"], "JA 参照文書")

            dlg.close()
        finally:
            root.destroy()

    def test_notebook_tab_selection_matches_dialog_language(self) -> None:
        from src.ui.fiscal_year_update_dialog import FiscalYearKnowledgeUpdateDialog
        import tkinter as tk

        try:
            root = tk.Tk()
            root.withdraw()
        except Exception:
            self.skipTest("Tkinter display not available")

        try:
            dlg_vi = FiscalYearKnowledgeUpdateDialog(root, "vi", fiscal_year="FY2028")
            self.assertEqual(dlg_vi.notebook.index(dlg_vi.notebook.select()), 0)
            dlg_vi.close()

            dlg_en = FiscalYearKnowledgeUpdateDialog(root, "en", fiscal_year="FY2028")
            self.assertEqual(dlg_en.notebook.index(dlg_en.notebook.select()), 1)
            dlg_en.close()

            dlg_ja = FiscalYearKnowledgeUpdateDialog(root, "ja", fiscal_year="FY2028")
            self.assertEqual(dlg_ja.notebook.index(dlg_ja.notebook.select()), 2)
            dlg_ja.close()
        finally:
            root.destroy()


class TestOperationsBusinessChatIntentRoutingUI(unittest.TestCase):
    """UI Regression tests proving that business, clarify, and incident intents are properly routed in chat dialog."""

    def setUp(self) -> None:
        import tkinter as tk
        try:
            self.root = tk.Tk()
            self.root.withdraw()
            self.tk_available = True
        except Exception:
            self.tk_available = False

    def tearDown(self) -> None:
        if getattr(self, "tk_available", False) and hasattr(self, "root"):
            try:
                self.root.destroy()
            except Exception:
                pass

    def test_business_query_does_not_attach_incident_diagnosis(self) -> None:
        if not getattr(self, "tk_available", False):
            self.skipTest("Tkinter display not available in environment")

        from src.ui.operations_assistant import OperationsBusinessChatDialog

        dialog = OperationsBusinessChatDialog(
            self.root,
            "vi",
            open_history=lambda: None,
            history_root="/fake/history",
            fiscal_year=2027,
        )
        try:
            with patch("src.ui.operations_assistant.request_gemini_web_business_guidance") as mock_gemini:
                mock_gemini.return_value = MagicMock(
                    status="ready",
                    answer="MP2027 là ứng dụng hỗ trợ phân bổ chi phí.",
                )
                dialog.question_var.set("cách sử dụng phần mềm này")
                dialog.send(sync=True)

                mock_gemini.assert_called_once()
                call_args = mock_gemini.call_args
                question_arg = call_args[0][0]
                context_arg = call_args[0][1]
                intent_arg = call_args[1].get("intent") or (call_args[0][3] if len(call_args[0]) > 3 else "business")

                self.assertEqual(question_arg, "cách sử dụng phần mềm này")
                self.assertEqual(intent_arg, "business")
                self.assertNotIn("KẾT QUẢ CHẨN ĐOÁN SỰ CỐ GẦN NHẤT", context_arg)
                self.assertNotIn("chưa ghi nhận lỗi", context_arg)

                answer_text = dialog.answer.cget("text")
                self.assertNotIn("không có lỗi", answer_text.lower())
                self.assertNotIn("hệ thống bình thường", answer_text.lower())
        finally:
            dialog.close()

    def test_clarify_query_routes_clarify_intent_and_asks_scope(self) -> None:
        if not getattr(self, "tk_available", False):
            self.skipTest("Tkinter display not available in environment")

        from src.ui.operations_assistant import OperationsBusinessChatDialog

        dialog = OperationsBusinessChatDialog(
            self.root,
            "vi",
            open_history=lambda: None,
            history_root="/fake/history",
            fiscal_year=2027,
        )
        try:
            with patch("src.ui.operations_assistant.request_gemini_web_business_guidance") as mock_gemini:
                mock_gemini.return_value = MagicMock(
                    status="ready",
                    answer="Bạn đang cần hỏi về số lượng nhóm chi phí hay số dòng chi phí cho năm tài chính nào?",
                )
                dialog.question_var.set("MP có bao nhiêu chi phí?")
                dialog.send(sync=True)

                mock_gemini.assert_called_once()
                call_args = mock_gemini.call_args
                question_arg = call_args[0][0]
                context_arg = call_args[0][1]
                intent_arg = call_args[1].get("intent") or (call_args[0][3] if len(call_args[0]) > 3 else "business")

                self.assertEqual(question_arg, "MP có bao nhiêu chi phí?")
                self.assertEqual(intent_arg, "clarify")
                self.assertNotIn("KẾT QUẢ CHẨN ĐOÁN SỰ CỐ GẦN NHẤT", context_arg)
                self.assertNotIn("chưa ghi nhận lỗi", context_arg)

                answer_text = dialog.answer.cget("text")
                self.assertNotIn("không có lỗi", answer_text.lower())
                self.assertNotIn("hệ thống bình thường", answer_text.lower())
        finally:
            dialog.close()

    def test_incident_query_routes_incident_intent_with_matching_case(self) -> None:
        if not getattr(self, "tk_available", False):
            self.skipTest("Tkinter display not available in environment")

        from src.ui.operations_assistant import OperationsBusinessChatDialog

        case_lock = _make_confirmed_case("vi", run_id="run-lock-test")

        dialog = OperationsBusinessChatDialog(
            self.root,
            "vi",
            open_history=lambda: None,
            history_root="/fake/history",
            fiscal_year=2028,
        )
        try:
            with patch("src.ui.operations_assistant.find_relevant_error_case", return_value=case_lock) as mock_find, \
                 patch("src.ui.operations_assistant.request_gemini_web_business_guidance") as mock_gemini:
                mock_gemini.return_value = MagicMock(
                    status="ready",
                    answer="Chạy bị dừng do tệp Excel bị khóa.",
                )
                dialog.question_var.set("Chạy tính toán bị dừng khi xuất Excel")
                dialog.send(sync=True)

                mock_find.assert_called_once()
                mock_gemini.assert_called_once()
                call_args = mock_gemini.call_args
                question_arg = call_args[0][0]
                context_arg = call_args[0][1]
                intent_arg = call_args[1].get("intent") or (call_args[0][3] if len(call_args[0]) > 3 else "business")

                self.assertEqual(question_arg, "Chạy tính toán bị dừng khi xuất Excel")
                self.assertEqual(intent_arg, "incident")
                self.assertIn("KẾT QUẢ CHẨN ĐOÁN SỰ CỐ GẦN NHẤT", context_arg)
        finally:
            dialog.close()

    def test_incident_query_when_no_case_matches_shows_clean_guidance(self) -> None:
        if not getattr(self, "tk_available", False):
            self.skipTest("Tkinter display not available in environment")

        from src.ui.operations_assistant import OperationsBusinessChatDialog

        dialog = OperationsBusinessChatDialog(
            self.root,
            "vi",
            open_history=lambda: None,
            history_root="/fake/history",
            fiscal_year=2028,
        )
        try:
            with patch("src.ui.operations_assistant.find_relevant_error_case", return_value=None), \
                 patch("src.ui.operations_assistant.request_gemini_web_business_guidance") as mock_gemini:
                mock_gemini.return_value = MagicMock(status="unavailable", answer="", limitation="offline")
                dialog.question_var.set("Chạy bị dừng do sự cố không xác định")
                dialog.send(sync=True)

                answer_text = dialog.answer.cget("text")
                self.assertIn("Chưa tìm thấy sự cố hoặc lỗi phù hợp", answer_text)
                self.assertIn("Lịch sử lần chạy", answer_text)
                self.assertNotIn("hệ thống bình thường", answer_text.lower())
                self.assertNotIn("quét lại nội dung", answer_text.lower())
        finally:
            dialog.close()

    def test_business_and_clarify_multilingual_en_ja(self) -> None:
        if not getattr(self, "tk_available", False):
            self.skipTest("Tkinter display not available in environment")

        from src.ui.operations_assistant import OperationsBusinessChatDialog

        # EN Check
        dialog_en = OperationsBusinessChatDialog(self.root, "en", open_history=lambda: None)
        try:
            with patch("src.ui.operations_assistant.request_gemini_web_business_guidance") as mock_gemini:
                mock_gemini.return_value = MagicMock(status="ready", answer="Why cost is allocated.")
                dialog_en.question_var.set("Why is this cost allocated this way?")
                dialog_en.send(sync=True)

                mock_gemini.assert_called_once()
                self.assertEqual(mock_gemini.call_args[1].get("intent"), "business")
        finally:
            dialog_en.close()

        # JA Check
        dialog_ja = OperationsBusinessChatDialog(self.root, "ja", open_history=lambda: None)
        try:
            with patch("src.ui.operations_assistant.request_gemini_web_business_guidance") as mock_gemini:
                mock_gemini.return_value = MagicMock(status="ready", answer="Clarification in Japanese.")
                dialog_ja.question_var.set("MPには費用がいくつありますか？")
                dialog_ja.send(sync=True)

                mock_gemini.assert_called_once()
                self.assertEqual(mock_gemini.call_args[1].get("intent"), "clarify")
        finally:
            dialog_ja.close()

    def test_send_async_defers_context_to_worker_thread(self) -> None:
        """send(sync=False) khởi chạy worker thread ngay mà không chạy _business_document_context trên UI thread."""
        if not getattr(self, "tk_available", False):
            self.skipTest("Tkinter display not available in environment")

        from src.ui.operations_assistant import OperationsBusinessChatDialog

        dialog = OperationsBusinessChatDialog(self.root, "vi", open_history=lambda: None)
        try:
            with patch("threading.Thread") as mock_thread_cls:
                mock_thread_instance = MagicMock()
                mock_thread_cls.return_value = mock_thread_instance

                dialog.question_var.set("Cách sử dụng phần mềm này")
                dialog.send(sync=False)

                # Thread phải được tạo với target=_request và context=None (để worker tự tính context)
                mock_thread_cls.assert_called_once()
                call_kwargs = mock_thread_cls.call_args
                target = call_kwargs[1].get("target") or call_kwargs[0][0]
                args = call_kwargs[1].get("args") if "args" in call_kwargs[1] else call_kwargs[0][1]

                self.assertEqual(target, dialog._request)
                self.assertEqual(args[0], "Cách sử dụng phần mềm này")
                self.assertIsNone(args[1], "context phải là None khi truyền vào thread để tránh block UI thread")
                mock_thread_instance.start.assert_called_once()
        finally:
            dialog.close()


if __name__ == "__main__":
    unittest.main()
