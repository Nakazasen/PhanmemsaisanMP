import pytest
from pathlib import Path

from src.services.i18n import set_current_language, t, DEFAULT_LANGUAGE
from src.universal_app import _friendly_error_message, MPManagerApp


def test_dynamic_error_formatting_in_all_languages():
    # 1. Vietnamese (Default)
    set_current_language("vi")
    msg_vi = _friendly_error_message("Hãy chọn ít nhất một Trung tâm chi phí.")
    assert "Hãy chọn ít nhất một Trung tâm chi phí." in msg_vi
    assert "Cách xử lý:" in msg_vi
    assert "Kiểm tra lại dữ liệu nguồn" in msg_vi

    title_vi = MPManagerApp._window_title("2027", "0.1.6")
    assert "Quản lý Ngân sách" in title_vi
    assert "Phòng Phát triển hệ thống Chế tạo" in title_vi

    assert t("pipeline_start_heading") == "--- BẮT ĐẦU TÍNH TOÁN ---"

    # 2. Japanese
    set_current_language("ja")
    msg_ja = _friendly_error_message(t("err_select_at_least_one_cc"))
    assert "少なくとも1つのコストセンターを選択してください。" in msg_ja
    assert "対処方法:" in msg_ja
    assert "上記のエラーメッセージに関連するソースデータおよび設定を確認してください。" in msg_ja

    title_ja = MPManagerApp._window_title("2027", "0.1.6")
    assert "予算管理" in title_ja
    assert "製造システム開発室" in title_ja

    assert t("pipeline_start_heading") == "--- 計算処理開始 ---"

    # 3. English
    set_current_language("en")
    msg_en = _friendly_error_message(t("err_select_at_least_one_cc"))
    assert "Please select at least one Cost Center." in msg_en
    assert "Action:" in msg_en
    assert "Check source data and settings related to the error above." in msg_en

    title_en = MPManagerApp._window_title("2027", "0.1.6")
    assert "Budget Management" in title_en
    assert "Manufacturing System Development Dept" in title_en

    assert t("pipeline_start_heading") == "--- STARTING CALCULATION ---"


def test_missing_headcount_error_localized():
    raw_error = "Thiếu dữ liệu nhân sự để xuất báo cáo.\n- chưa có tổng số người tháng 202604"

    set_current_language("vi")
    err_vi = _friendly_error_message(raw_error)
    assert "Cách xử lý:" in err_vi
    assert "Nhập nhân sự thủ công" in err_vi

    set_current_language("ja")
    err_ja = _friendly_error_message(raw_error)
    assert "対処方法:" in err_ja
    assert "人員手入力" in err_ja

    set_current_language("en")
    err_en = _friendly_error_message(raw_error)
    assert "Action:" in err_en
    assert "Manual Staffing Input" in err_en


class MockWidget:
    def __init__(self, text=""):
        self._text = text
        self.config = {}

    def configure(self, **kwargs):
        if "text" in kwargs:
            self._text = kwargs["text"]
        self.config.update(kwargs)

    def cget(self, key):
        if key == "text":
            return self._text
        return self.config.get(key)


class MockVar:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, val):
        self.value = val


class MockRoot:
    def __init__(self):
        self._title = ""

    def title(self, text=None):
        if text is not None:
            self._title = text
        return self._title


def test_main_screen_hides_requested_actions_and_keeps_source_order_visible():
    source = Path("src/universal_app.py").read_text(encoding="utf-8")
    actions_start = source.index("        actions = ttk.Frame(container)")
    actions_end = source.index("        log_frame = ttk.Frame(shell)", actions_start)
    main_screen_actions = source[actions_start:actions_end]

    assert '"install_rules_btn", self.install_content_package' not in main_screen_actions
    assert '"user_guide_btn", self.open_user_guide' not in main_screen_actions
    assert "self.quick_check_btn = ttk.Button" not in main_screen_actions
    assert "self.open_source_order_editor" in main_screen_actions


def test_gui_widget_dynamic_language_switching_on_live_app(monkeypatch, tmp_path):
    saved_languages = []
    monkeypatch.setattr(
        "src.universal_app.remember_ui_language",
        lambda code: saved_languages.append(code),
    )

    app = object.__new__(MPManagerApp)
    app.root = MockRoot()
    app.application_version = "0.1.6"
    app.fiscal_year = MockVar("2027")
    app.language_var = MockVar("Tiếng Việt")
    app.template_path = MockVar("FORM.xlsx")
    app.source_dir = MockVar("costs")
    app.headcount_source_dir = MockVar("headcount")
    app._approved_preflight_report = None
    app.preflight_status = MockVar("")
    app.headcount_source_status = MockVar("")
    app.cc_code_filter = MockVar("")
    app._available_cc_choices = []
    app._selected_cc_values = []
    app.messages = []
    app.log = app.messages.append

    # Setup mock UI widgets
    app.version_lbl = MockWidget()
    app.lang_lbl = MockWidget()
    app.main_heading = MockWidget()
    app.open_proj_btn = MockWidget()
    app.create_proj_btn = MockWidget()
    app.config_proj_btn = MockWidget()
    app.fiscal_year_lbl = MockWidget()
    app.exchange_rate_lbl = MockWidget()
    app.exchange_rate_hint_lbl = MockWidget()
    app.template_lbl = MockWidget()
    app.cost_source_lbl = MockWidget()
    app.headcount_source_lbl = MockWidget()
    app.update_db_btn = MockWidget()
    app.cc_lbl = MockWidget()
    app.cc_select_btn = MockWidget()
    app.refresh_btn = MockWidget()
    app.cc_hint_lbl = MockWidget()
    app.workflow_guide_lbl = MockWidget()
    app.workflow_next_action = MockWidget()
    app.workflow_cards = [
        (MockWidget(), MockWidget(), MockWidget(), MockWidget()) for _ in range(5)
    ]
    app.action_buttons = [
        (MockWidget(), "manual_headcount_btn"),
        (MockWidget(), "event_driver_btn"),
        (MockWidget(), "source_order_btn"),
        (MockWidget(), "install_update_btn"),
        (MockWidget(), "run_history_btn"),
        (MockWidget(), "variance_analysis_btn"),
    ]
    app.deep_scan_btn = MockWidget()
    app.start_btn = MockWidget()
    app.log_title_lbl = MockWidget()

    # Dynamic statuses must be re-rendered from semantic keys after a language switch.
    app._set_preflight_error_status(t("err_select_at_least_one_cc"))
    app._set_headcount_source_status("hc_source_needs_sync")

    # 1. Switch to Japanese
    app.language_var.set("日本語")
    app._on_language_selected()

    assert "言語:" in app.lang_lbl.cget("text")
    assert "年度" in app.fiscal_year_lbl.cget("text")
    assert "為替レート" in app.exchange_rate_lbl.cget("text")
    assert "FORMテンプレート" in app.template_lbl.cget("text")
    assert "費用ソースフォルダ" in app.cost_source_lbl.cget("text")
    assert "人員・勤務時間ソース" in app.headcount_source_lbl.cget("text")
    assert "コストセンター" in app.cc_lbl.cget("text")
    assert "計算実行" in app.start_btn.cget("text")
    assert "ソース詳細再検証" in app.deep_scan_btn.cget("text")
    assert "製造システム開発室" in app.root.title()

    assert app.preflight_status.get() == t("preflight_cannot_check", error=t("err_select_at_least_one_cc"))
    assert app.headcount_source_status.get() == t("hc_source_needs_sync")

    action_texts_ja = [btn.cget("text") for btn, _ in app.action_buttons]
    assert "人員手入力" in action_texts_ja
    assert "イベントデータ手入力" in action_texts_ja
    assert "ソースファイル順序" in action_texts_ja
    assert "実行履歴" in action_texts_ja
    assert "MP年度差異分析 (YoY)" in action_texts_ja

    # 2. Switch to English
    app.language_var.set("English")
    app._on_language_selected()

    assert "Language:" in app.lang_lbl.cget("text")
    assert "Fiscal Year" in app.fiscal_year_lbl.cget("text")
    assert "Exchange Rate" in app.exchange_rate_lbl.cget("text")
    assert "FORM Template" in app.template_lbl.cget("text")
    assert "Cost Source Folder" in app.cost_source_lbl.cget("text")
    assert "Staffing & Hours Source" in app.headcount_source_lbl.cget("text")
    assert "Cost Center" in app.cc_lbl.cget("text")
    assert "RUN CALCULATION" in app.start_btn.cget("text")
    assert "Deep Source Scan" in app.deep_scan_btn.cget("text")
    assert "Manufacturing System Development Dept" in app.root.title()

    assert app.preflight_status.get() == t("preflight_cannot_check", error=t("err_select_at_least_one_cc"))
    assert app.headcount_source_status.get() == t("hc_source_needs_sync")

    action_texts_en = [btn.cget("text") for btn, _ in app.action_buttons]
    assert "Manual Staffing Input" in action_texts_en
    assert "Manual Event Input" in action_texts_en
    assert "Source File Order" in action_texts_en
    assert "Run History" in action_texts_en
    assert "MP Variance Analysis (YoY)" in action_texts_en

    # 3. Switch back to Vietnamese
    app.language_var.set("Tiếng Việt")
    app._on_language_selected()

    assert "Ngôn ngữ:" in app.lang_lbl.cget("text")
    assert "Năm tài chính" in app.fiscal_year_lbl.cget("text")
    assert "Tỷ giá" in app.exchange_rate_lbl.cget("text")
    assert "Tệp mẫu FORM" in app.template_lbl.cget("text")
    assert "Thư mục nguồn chi phí" in app.cost_source_lbl.cget("text")
    assert "Nguồn nhân sự & thời gian" in app.headcount_source_lbl.cget("text")
    assert "Trung tâm chi phí" in app.cc_lbl.cget("text")
    assert "CHẠY TÍNH TOÁN" in app.start_btn.cget("text")
    assert "Quét kỹ lại nội dung" in app.deep_scan_btn.cget("text")
    assert "Phòng Phát triển hệ thống Chế tạo" in app.root.title()

    assert app.preflight_status.get() == t("preflight_cannot_check", error=t("err_select_at_least_one_cc"))
    assert app.headcount_source_status.get() == t("hc_source_needs_sync")

    action_texts_vi = [btn.cget("text") for btn, _ in app.action_buttons]
    assert "Nhập nhân sự thủ công" in action_texts_vi
    assert "Nhập sự kiện thiếu dữ liệu" in action_texts_vi
    assert "Thứ tự tệp nguồn" in action_texts_vi
    assert "Lịch sử lần chạy" in action_texts_vi
    assert "So sánh biến động MP (YoY)" in action_texts_vi

    assert saved_languages == ["ja", "en", "vi"]
