from pathlib import Path

import pytest

from src.services.run_history import OutputPublicationLockedError
from src.universal_app import (
    MPManagerApp,
    _friendly_error_message,
    _headcount_coverage_error_message,
)


class Variable:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class Root:
    def after(self, _delay, _callback):
        return None


def test_output_lock_error_keeps_actionable_vietnamese_guidance():
    error = OutputPublicationLockedError(
        Path("C:/runtime/OUTPUT_FY2027"),
        Path("C:/runtime/.OUTPUT_FY2027.run.backup"),
    )

    message = _friendly_error_message(error)

    assert "Windows đang khóa" in message
    assert "Excel" in message
    assert "File Explorer" in message


def _app_with_choices(*selected):
    app = object.__new__(MPManagerApp)
    app.cc_code_filter = Variable()
    app._available_cc_choices = [
        "1412000004 - 機器製造1課",
        "1412000006 - 生産管理課",
        "1412000036 - 総務課",
    ]
    app._selected_cc_values = list(selected)
    app._update_cc_selection_summary()
    return app


def test_parse_selected_cost_centers_requires_at_least_one_choice():
    app = _app_with_choices()

    with pytest.raises(ValueError, match="ít nhất một Trung tâm chi phí"):
        app._parse_selected_cc_codes()


def test_parse_selected_cost_centers_supports_multiple_rooms():
    app = _app_with_choices(
        "1412000004 - 機器製造1課",
        "1412000036 - 総務課",
    )

    assert app._parse_selected_cc_codes() == ("1412000004", "1412000036")
    assert app.cc_code_filter.get() == "Đã chọn 2 Trung tâm chi phí"
    assert not app._all_cost_centers_selected()


def test_missing_selected_staffing_source_message_names_the_missing_cost_center():
    message = _headcount_coverage_error_message(
        2027,
        {
            "missing_cc_codes": ("1412000036",),
            "available_cc_codes": ("1412000004",),
        },
    )

    assert "1412000036" in message
    assert "1412000004" in message
    assert "không chạy" in message


def test_selecting_every_cost_center_sets_all_summary():
    app = _app_with_choices(
        "1412000004 - 機器製造1課",
        "1412000006 - 生産管理課",
        "1412000036 - 総務課",
    )

    assert app._all_cost_centers_selected()
    assert app.cc_code_filter.get() == "Tất cả Trung tâm chi phí (3)"


def test_refresh_choices_keeps_valid_selections_and_removes_stale_values():
    app = _app_with_choices(
        "1412000004 - 機器製造1課",
        "1412000036 - 総務課",
    )

    app._set_cc_choices(
        [
            "1412000004 - 機器製造1課",
            "1412000006 - 生産管理課",
        ]
    )

    assert app._available_cc_choices == [
        "1412000004 - 機器製造1課",
        "1412000006 - 生産管理課",
    ]
    assert app._selected_cc_values == ["1412000004 - 機器製造1課"]
    assert app.cc_code_filter.get() == "1412000004 - 機器製造1課"


def test_all_cost_centers_command_omits_target_cc(tmp_path):
    app = object.__new__(MPManagerApp)
    app._approved_uniform_policy_path = None
    app.project = type("Project", (), {"config_path": str(tmp_path / "project.json")})()
    app._operational_database = lambda: str(tmp_path / "operational.db")
    paths = type(
        "Paths",
        (),
        {
            "manual_input_store": str(tmp_path / "manual.db"),
            "output_dir": str(tmp_path / "OUTPUT_FY2027"),
            "history_root": str(tmp_path / "RUN_HISTORY"),
        },
    )()
    app._project_paths = lambda _fy: paths

    command = app._pipeline_subprocess_command(
        2027, "FORM.xlsx", "raw", "headcount", 25450, None
    )

    assert "--target-cc" not in command


def test_batch_pipeline_runs_selected_cost_centers_in_order(tmp_path):
    app = object.__new__(MPManagerApp)
    output_dir = tmp_path / "OUTPUT_FY2027"
    app._project_paths = lambda _fy: type("Paths", (), {"output_dir": str(output_dir)})()
    calls = []
    messages = []
    finished = []
    app.log = messages.append
    app._run_on_ui_thread = lambda callback, *args: callback(*args)
    app._finish_pipeline = lambda success, result: finished.append((success, result))

    def run_one(*args):
        calls.append(args[-1])
        return True, str(output_dir), None

    app._run_pipeline_process = run_one

    app.run_process(
        2027,
        "FORM.xlsx",
        "raw",
        "headcount",
        25450,
        ("1412000004", "1412000036"),
    )

    assert calls == ["1412000004", "1412000036"]
    assert finished == [(True, str(output_dir))]
    assert any("1/2" in message for message in messages)
    assert any("2/2" in message for message in messages)


def test_batch_pipeline_stops_at_first_failed_cost_center(tmp_path):
    app = object.__new__(MPManagerApp)
    output_dir = tmp_path / "OUTPUT_FY2027"
    app._project_paths = lambda _fy: type("Paths", (), {"output_dir": str(output_dir)})()
    calls = []
    finished = []
    app.log = lambda _message: None
    app._run_on_ui_thread = lambda callback, *args: callback(*args)
    app._finish_pipeline = lambda success, result: finished.append((success, result))

    def run_one(*args):
        target_cc = args[-1]
        calls.append(target_cc)
        if target_cc == "1412000036":
            return False, RuntimeError("source invalid"), None
        return True, str(output_dir), None

    app._run_pipeline_process = run_one

    app.run_process(
        2027,
        "FORM.xlsx",
        "raw",
        "headcount",
        25450,
        ("1412000004", "1412000036", "1412000099"),
    )

    assert calls == ["1412000004", "1412000036"]
    assert finished[0][0] is False
    assert "1412000036" in str(finished[0][1])


def test_successful_pipeline_can_open_output(monkeypatch, tmp_path):
    output_dir = tmp_path / "OUTPUT_FY2027"
    output_dir.mkdir()
    result_file = output_dir / "MP2027.xlsx"
    result_file.touch()
    opened = []
    messages = []
    app = object.__new__(MPManagerApp)
    app.root = Root()
    app.log = messages.append
    app.load_cc_list = lambda: None
    app._mark_preflight_stale = lambda: None
    app._open_path = opened.append
    monkeypatch.setattr(
        "src.universal_app.messagebox.askyesno", lambda *_args, **_kwargs: True
    )

    app._finish_pipeline(True, str(result_file))

    assert opened == [str(output_dir)]
    assert any("THÀNH CÔNG" in message for message in messages)


def test_open_path_warns_when_output_does_not_exist(monkeypatch, tmp_path):
    warnings = []
    monkeypatch.setattr(
        "src.universal_app.messagebox.showwarning",
        lambda title, message: warnings.append((title, message)),
    )
    app = object.__new__(MPManagerApp)

    app._open_path(str(tmp_path / "missing"))

    assert warnings and warnings[0][0] == "Chưa có tệp"
