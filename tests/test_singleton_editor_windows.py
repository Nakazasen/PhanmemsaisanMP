from src.universal_app import MPManagerApp


class _FakeWindow:
    def __init__(self, exists=True):
        self.exists = exists
        self.deiconified = False
        self.transient_parent = None
        self.lifted = False
        self.focused = False

    def winfo_exists(self):
        return self.exists

    def deiconify(self):
        self.deiconified = True

    def transient(self, parent):
        self.transient_parent = parent

    def lift(self):
        self.lifted = True

    def focus_force(self):
        self.focused = True


def test_existing_headcount_editor_is_reused_and_brought_to_front():
    app = MPManagerApp.__new__(MPManagerApp)
    app.root = object()
    window = _FakeWindow()
    app._headcount_editor_v2 = window

    assert app._focus_existing_editor("_headcount_editor_v2") is True
    assert window.deiconified is True
    assert window.transient_parent is app.root
    assert window.lifted is True
    assert window.focused is True


def test_closed_headcount_editor_reference_is_discarded():
    app = MPManagerApp.__new__(MPManagerApp)
    app.root = object()
    app._headcount_editor_v2 = _FakeWindow(exists=False)

    assert app._focus_existing_editor("_headcount_editor_v2") is False
    assert app._headcount_editor_v2 is None


def test_singleton_registration_releases_slot_when_editor_is_destroyed():
    class Window(_FakeWindow):
        def __init__(self):
            super().__init__()
            self.protocol_callback = None
            self.destroyed = False

        def protocol(self, _name, callback):
            self.protocol_callback = callback

        def bind(self, _event, _callback, add=None):
            pass

        def destroy(self):
            self.destroyed = True
            self.exists = False

    app = MPManagerApp.__new__(MPManagerApp)
    window = Window()

    close_editor = app._register_singleton_editor("_event_driver_editor", window)
    close_editor()

    assert window.destroyed is True
    assert app._event_driver_editor is None


def test_pipeline_busy_locks_every_action_that_can_change_sources_or_project():
    class Button:
        def __init__(self):
            self.state = None

        def configure(self, **kwargs):
            self.state = kwargs.get("state", self.state)

    app = MPManagerApp.__new__(MPManagerApp)
    app.start_btn = Button()
    app.cc_select_btn = Button()
    app.refresh_btn = Button()
    app.update_db_btn = Button()
    app.deep_scan_btn = Button()
    app.open_proj_btn = Button()
    app.create_proj_btn = Button()
    app.config_proj_btn = Button()
    app.fiscal_year_entry = Button()
    app.exchange_rate_entry = Button()
    app.template_path_entry = Button()
    app.source_dir_entry = Button()
    app.headcount_source_dir_entry = Button()
    action_one = Button()
    action_two = Button()
    app.action_buttons = [(action_one, "manual_headcount_btn"), (action_two, "event_driver_btn")]

    app._set_pipeline_ui_busy(True)

    assert app._pipeline_busy is True
    assert all(button.state == "disabled" for button in (
        app.start_btn, app.cc_select_btn, app.refresh_btn, app.update_db_btn,
        app.deep_scan_btn, app.open_proj_btn, app.create_proj_btn, app.config_proj_btn,
        app.fiscal_year_entry, app.exchange_rate_entry, app.template_path_entry,
        app.source_dir_entry, app.headcount_source_dir_entry,
        action_one, action_two,
    ))

    app._set_pipeline_ui_busy(False)

    assert app._pipeline_busy is False
    assert app.start_btn.state == "normal"
    assert action_one.state == "normal"
