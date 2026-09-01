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
