from unittest.mock import patch

from src.universal_app import MPManagerApp


class _FakeRoot:
    def winfo_screenwidth(self):
        return 1280

    def winfo_screenheight(self):
        return 900


class _FakeWindow:
    def __init__(self, parent):
        self.parent = parent
        self.transient_parent = None
        self.was_lifted = False
        self.focused = False

    def title(self, _text):
        pass

    def geometry(self, _value):
        pass

    def minsize(self, _width, _height):
        pass

    def transient(self, parent):
        self.transient_parent = parent

    def lift(self):
        self.was_lifted = True

    def focus_force(self):
        self.focused = True

    def deiconify(self):
        self.was_lifted = True

    def winfo_exists(self):
        return True

    def destroy(self):
        pass

    def protocol(self, _name, _callback):
        pass

    def bind(self, _event, _callback, add=None):
        pass


def test_yoy_window_is_kept_above_the_main_application(monkeypatch):
    app = MPManagerApp.__new__(MPManagerApp)
    app.root = _FakeRoot()
    created = []

    def create_window(parent):
        window = _FakeWindow(parent)
        created.append(window)
        return window

    with patch("src.universal_app.tk.Toplevel", side_effect=create_window), patch(
        "src.ui.tabs.variance_tab.VarianceTab", return_value=None
    ):
        app.open_variance_tab()

    window = created[0]
    assert window.parent is app.root
    assert window.transient_parent is app.root
    assert window.was_lifted is True
    assert window.focused is True


def test_yoy_button_reuses_its_existing_window(monkeypatch):
    app = MPManagerApp.__new__(MPManagerApp)
    app.root = _FakeRoot()
    created = []

    def create_window(parent):
        window = _FakeWindow(parent)
        created.append(window)
        return window

    with patch("src.universal_app.tk.Toplevel", side_effect=create_window), patch(
        "src.ui.tabs.variance_tab.VarianceTab", return_value=None
    ):
        app.open_variance_tab()
        app.open_variance_tab()

    assert len(created) == 1
    assert created[0].was_lifted is True
