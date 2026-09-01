"""Unit tests for the MP2027 i18n localization system.

Covers:
- Default language behavior (Vietnamese: vi)
- Language switching (vi -> ja -> en)
- Missing key fallback to Vietnamese
- Parameter interpolation in localized strings
- Preference persistence to launcher.json and error recovery
- Listener registration and notifications
- UTF-8 Unicode integrity for Vietnamese and Japanese text
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from src.services.i18n import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    get_current_language,
    get_language_code,
    get_language_name,
    get_supported_languages,
    register_language_listener,
    set_current_language,
    t,
    unregister_language_listener,
)
from src.services.project_config import (
    read_ui_language,
    remember_ui_language,
)


class TestI18nLocalization(unittest.TestCase):
    def setUp(self):
        # Always reset to default language before each test
        set_current_language(DEFAULT_LANGUAGE)

    def tearDown(self):
        # Reset to default language after each test
        set_current_language(DEFAULT_LANGUAGE)

    def test_default_language_is_vietnamese(self):
        self.assertEqual(DEFAULT_LANGUAGE, "vi")
        self.assertEqual(get_current_language(), "vi")
        self.assertEqual(t("app_title"), "Quản lý Ngân sách")
        self.assertEqual(t("language_label"), "Ngôn ngữ:")

    def test_language_switch_to_japanese_and_english(self):
        set_current_language("ja")
        self.assertEqual(get_current_language(), "ja")
        self.assertEqual(t("app_title"), "予算管理")
        self.assertEqual(t("language_label"), "言語:")
        self.assertEqual(t("fiscal_year_label"), "会計年度")
        self.assertEqual(t("start_pipeline_btn"), "計算実行")

        set_current_language("en")
        self.assertEqual(get_current_language(), "en")
        self.assertEqual(t("app_title"), "Budget Management")
        self.assertEqual(t("language_label"), "Language:")
        self.assertEqual(t("fiscal_year_label"), "Fiscal Year")
        self.assertEqual(t("start_pipeline_btn"), "RUN CALCULATION")

        set_current_language("vi")
        self.assertEqual(get_current_language(), "vi")
        self.assertEqual(t("app_title"), "Quản lý Ngân sách")

    def test_fallback_to_vietnamese_on_missing_key(self):
        # Temporarily test with a simulated key present only in vi
        from src.services.i18n import TRANSLATIONS

        TRANSLATIONS["vi"]["_test_only_key"] = "Chỉ có tiếng Việt"
        try:
            set_current_language("ja")
            self.assertEqual(t("_test_only_key"), "Chỉ có tiếng Việt")

            set_current_language("en")
            self.assertEqual(t("_test_only_key"), "Chỉ có tiếng Việt")
        finally:
            TRANSLATIONS["vi"].pop("_test_only_key", None)

    def test_completely_unknown_key_returns_key(self):
        self.assertEqual(t("non_existent_random_key_12345"), "non_existent_random_key_12345")

    def test_dynamic_parameter_formatting(self):
        set_current_language("vi")
        self.assertIn("MP2027", t("main_heading", fiscal_year=2027))
        self.assertIn("v1.5.0", t("app_version", version="1.5.0"))
        self.assertIn("10 Trung tâm chi phí", t("selected_cc_count", count=10))

        set_current_language("ja")
        self.assertIn("MP2027", t("main_heading", fiscal_year=2027))
        self.assertIn("10 コストセンター選択済", t("selected_cc_count", count=10))

        set_current_language("en")
        self.assertIn("MP2027", t("main_heading", fiscal_year=2027))
        self.assertIn("10 Cost Centers selected", t("selected_cc_count", count=10))

    def test_invalid_language_code_falls_back_to_default(self):
        set_current_language("invalid_code_xyz")
        self.assertEqual(get_current_language(), "vi")

    def test_supported_languages_list_and_helpers(self):
        langs = get_supported_languages()
        codes = [code for code, _ in langs]
        self.assertIn("vi", codes)
        self.assertIn("ja", codes)
        self.assertIn("en", codes)

        self.assertEqual(get_language_name("vi"), "Tiếng Việt")
        self.assertEqual(get_language_name("ja"), "日本語")
        self.assertEqual(get_language_name("en"), "English")

        self.assertEqual(get_language_code("Tiếng Việt"), "vi")
        self.assertEqual(get_language_code("日本語"), "ja")
        self.assertEqual(get_language_code("English"), "en")
        self.assertEqual(get_language_code("Unknown"), "vi")

    def test_language_listeners_notification(self):
        events = []

        def on_lang_changed(lang: str):
            events.append(lang)

        register_language_listener(on_lang_changed)
        try:
            set_current_language("ja")
            self.assertEqual(events, ["ja"])

            set_current_language("en")
            self.assertEqual(events, ["ja", "en"])
        finally:
            unregister_language_listener(on_lang_changed)

        # After unregistering, no more notifications
        set_current_language("vi")
        self.assertEqual(events, ["ja", "en"])

    def test_preference_persistence_in_launcher_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initially no preference -> fallback to vi
            self.assertEqual(read_ui_language(local_app_data=tmpdir), "vi")

            # Save ja
            remember_ui_language("ja", local_app_data=tmpdir)
            self.assertEqual(read_ui_language(local_app_data=tmpdir), "ja")

            # Save en
            remember_ui_language("en", local_app_data=tmpdir)
            self.assertEqual(read_ui_language(local_app_data=tmpdir), "en")

            # Corrupted JSON -> fallback to vi
            cfg_file = os.path.join(tmpdir, "MPManager", "launcher.json")
            with open(cfg_file, "w", encoding="utf-8") as f:
                f.write("{corrupted json...")
            self.assertEqual(read_ui_language(local_app_data=tmpdir), "vi")

            # Invalid language in json -> fallback to vi
            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump({"ui_language": "invalid_lang"}, f)
            self.assertEqual(read_ui_language(local_app_data=tmpdir), "vi")

    def test_unicode_utf8_encoding_integrity(self):
        # Verify Japanese and Vietnamese characters are not mojibake
        vi_sample = t("workflow_guide_title")
        self.assertEqual(vi_sample, "Làm theo 5 bước")

        set_current_language("ja")
        ja_sample = t("workflow_guide_title")
        self.assertEqual(ja_sample, "5ステップガイド")

        ja_action = t("start_pipeline_btn")
        self.assertEqual(ja_action, "計算実行")

    def test_variance_tab_dialog_translations_exist(self):
        for lang in ("vi", "ja", "en"):
            set_current_language(lang)
            self.assertTrue(bool(t("variance_tab_title")))
            self.assertTrue(bool(t("variance_missing_files_title")))
            self.assertTrue(bool(t("variance_missing_files_msg")))
            self.assertTrue(bool(t("variance_export_success_title")))
            self.assertTrue(bool(t("variance_batch_select_base_title")))
            self.assertTrue(bool(t("variance_batch_no_pairs_title")))
            self.assertTrue(bool(t("variance_chart_btn")))
            self.assertTrue(bool(t("variance_chart_title")))
            self.assertTrue(bool(t("variance_chart_no_data")))
            self.assertTrue(bool(t("variance_chart_axis_label")))
            self.assertTrue(bool(t("variance_chart_legend")))
            self.assertTrue(bool(t("variance_chart_source_note")))

    def test_universal_app_dialog_translations_exist(self):
        dialog_keys = [
            "open_project_dialog_title",
            "cannot_open_project_title",
            "choose_project_dir_title",
            "cannot_create_project_title",
            "config_project_storage_title",
            "choose_rule_pack_title",
            "invalid_rule_pack_title",
            "cannot_install_rule_pack_title",
            "installed_rule_pack_title",
            "source_not_verified_title",
            "source_not_verified_msg",
            "export_all_cc_title",
            "pipeline_complete_title",
            "pipeline_failed_title",
            "no_update_source_title",
            "cannot_auto_update_title",
            "update_found_title",
            "update_ready_title",
            "cc_dialog_title",
            "no_cc_warning_title",
            "cleanup_confirm_title",
            "cleanup_success_title",
            "output_cost_row_order_btn",
            "output_cost_row_order_title",
            "output_cost_row_order_choose",
            "output_cost_row_order_hint",
            "output_cost_row_order_saved",
            "output_cost_row_order_error",
            "manual_special_restore_log",
            "cc_search_label",
            "cc_search_hint",
            "cc_search_clear",
            "cc_search_matches",
        ]
        for lang in ("vi", "ja", "en"):
            set_current_language(lang)
            for key in dialog_keys:
                translated = t(key, fiscal_year=2027, count=5, version="1.0.0", current_version="0.9.0", result="output")
                self.assertTrue(bool(translated), f"Key '{key}' is missing in language '{lang}'")
                self.assertNotEqual(translated, key, f"Key '{key}' was not translated in '{lang}'")

    def test_variance_tab_listener_and_dynamic_refresh(self):
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
        except Exception:
            # Headless environment without display
            return

        try:
            from src.ui.tabs.variance_tab import VarianceTab
            set_current_language("vi")
            tab = VarianceTab(root)
            self.assertEqual(tab.title_lbl.cget("text"), "So sánh biến động chi phí MP giữa hai năm tài chính")
            self.assertEqual(tab.tree.heading("Account")["text"], "Mã Tài Khoản")

            # Switch language to Japanese -> VarianceTab should automatically update via listener
            set_current_language("ja")
            self.assertEqual(tab.title_lbl.cget("text"), "2会計年度間のMP費用差異比較")
            self.assertEqual(tab.tree.heading("Account")["text"], "勘定科目コード")

            # Switch language to English -> VarianceTab should automatically update via listener
            set_current_language("en")
            self.assertEqual(tab.title_lbl.cget("text"), "Compare MP Cost Variance Between Two Fiscal Years")
            self.assertEqual(tab.tree.heading("Account")["text"], "Account Code")

            # Destroy tab -> listener is unregistered
            tab.destroy()
        finally:
            try:
                root.destroy()
            except Exception:
                pass

    def test_operations_assistant_i18n_keys_completeness_and_quality(self):
        """Xác thực toàn bộ 24 nhãn i18n của trợ lý vận hành có đủ trên cả 3 ngôn ngữ và không chứa từ cấm."""
        from src.services.i18n import OPERATIONS_ASSISTANT_I18N_KEYS, TRANSLATIONS

        self.assertGreaterEqual(len(OPERATIONS_ASSISTANT_I18N_KEYS), 20)

        for lang in ("vi", "ja", "en"):
            set_current_language(lang)
            for key in OPERATIONS_ASSISTANT_I18N_KEYS:
                # Do not let t(...) hide a missing Japanese/English entry by
                # falling back to Vietnamese.  Every active language must own
                # every assistant label before the UI is allowed to use it.
                self.assertIn(key, TRANSLATIONS[lang], f"Key '{key}' thiếu trực tiếp trong '{lang}'")
                direct_translation = TRANSLATIONS[lang][key]
                self.assertTrue(
                    isinstance(direct_translation, str) and bool(direct_translation.strip()),
                    f"Key '{key}' bị rỗng trực tiếp trong ngôn ngữ '{lang}'",
                )
                translated = t(key)
                self.assertEqual(
                    translated,
                    direct_translation,
                    f"Key '{key}' ({lang}) đã rơi sang fallback thay vì dùng bản dịch hiện hành",
                )
                self.assertTrue(bool(translated), f"Key '{key}' bị rỗng trong ngôn ngữ '{lang}'")
                self.assertNotEqual(translated, key, f"Key '{key}' chưa được dịch trong '{lang}'")

                # Không chứa placeholder chưa xử lý hoặc từ khóa kỹ thuật thô
                for forbidden in (
                    "{{", "}}", "i18n.", "translation_key", "TODO", "TBD",
                    "Traceback", "FAILED", "PRECHECK_FAILED",
                ):
                    self.assertNotIn(
                        forbidden,
                        translated,
                        f"Key '{key}' ({lang}) chứa chuỗi cấm '{forbidden}': '{translated}'"
                    )

    def test_operations_assistant_language_switching(self):
        """Xác thực chuyển đổi ngôn ngữ cho nút bấm và tiêu đề cửa sổ của trợ lý."""
        # 1. Tiếng Việt
        set_current_language("vi")
        self.assertEqual(t("operations_assistant_btn"), "Trợ lý xử lý lỗi")
        self.assertEqual(t("operations_assistant_window_title"), "Trợ lý Vận hành & Xử lý Lỗi")
        self.assertEqual(t("operations_assistant_close_btn"), "Đóng")

        # 2. Tiếng Nhật
        set_current_language("ja")
        self.assertEqual(t("operations_assistant_btn"), "エラー対応アシスタント")
        self.assertEqual(t("operations_assistant_window_title"), "運用・エラー対応アシスタント")
        self.assertEqual(t("operations_assistant_close_btn"), "閉じる")

        # 3. Tiếng Anh
        set_current_language("en")
        self.assertEqual(t("operations_assistant_btn"), "Operations Assistant")
        self.assertEqual(t("operations_assistant_window_title"), "Operations & Error Assistant")
        self.assertEqual(t("operations_assistant_close_btn"), "Close")

    def test_translate_for_language_explicit_lookup(self):
        """Xác thực translate_for_language tra cứu đúng theo ngôn ngữ yêu cầu mà không đổi global language."""
        from src.services.i18n import translate_for_language

        set_current_language("vi")

        # Tra cứu tiếng Nhật nhưng global vẫn là tiếng Việt
        ja_btn = translate_for_language("operations_assistant_btn", "ja")
        self.assertEqual(ja_btn, "エラー対応アシスタント")
        self.assertEqual(get_current_language(), "vi")
        self.assertEqual(t("operations_assistant_btn"), "Trợ lý xử lý lỗi")

        # Tra cứu tiếng Anh
        en_btn = translate_for_language("operations_assistant_btn", "en")
        self.assertEqual(en_btn, "Operations Assistant")

        # Từ chối ngôn ngữ không hỗ trợ
        with self.assertRaises(ValueError):
            translate_for_language("operations_assistant_btn", "fr")

        # Từ chối key không tồn tại (không fallback im lặng)
        with self.assertRaises(KeyError):
            translate_for_language("non_existent_key_9999", "vi")


if __name__ == "__main__":
    unittest.main()
