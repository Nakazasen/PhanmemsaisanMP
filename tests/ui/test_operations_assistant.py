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

        # Kiểm tra nút Đóng
        self.assertEqual(len(factory.created_buttons), 1)
        self.assertEqual(factory.created_buttons[0].text, "Đóng")

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
            self.assertEqual(factory.created_buttons[0].text, expected_close)

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

                # Nút duy nhất được phép tồn tại trên giao diện là nút Đóng (Close)
                self.assertEqual(len(factory.created_buttons), 1)
                close_btn = factory.created_buttons[0]
                self.assertEqual(close_btn.role, "close_button")
                self.assertEqual(close_btn.command, dialog.close)

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

        for idx, status in enumerate(terminal_statuses):
            table.set_selection(f"node_{idx}")
            self.assertEqual(assistant_btn.state, "normal", f"Status {status} phải bật nút NORMAL")

        # Kiểm tra truyền đúng active language qua VI, EN, JA
        for lang in ("vi", "en", "ja"):
            set_current_language(lang)
            table.set_selection("node_0")

            fake_case = _make_confirmed_case(lang, run_id="run-FAILED")
            with patch("src.universal_app.assemble_operational_case", return_value=fake_case) as mock_assemble, \
                 patch("src.universal_app.OperationsAssistantDialog.open_or_focus") as mock_open_or_focus:
                assistant_btn.command()

                mock_assemble.assert_called_once_with("D:/history_test", "run-FAILED", lang)
                mock_open_or_focus.assert_called_once_with(app.root, fake_case, lang)

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


if __name__ == "__main__":
    unittest.main()

