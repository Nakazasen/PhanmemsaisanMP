from pathlib import Path

import openpyxl

from src.universal_app import (
    MPManagerApp,
    _friendly_error_message,
    _validate_selected_template,
)


ROOT = Path(__file__).resolve().parents[1]


def test_form_without_system_cost_account_is_valid():
    path = ROOT / "docs" / "MP2027" / "FORM.xlsx"
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=False)
    try:
        worksheet = workbook["内訳ﾘｽﾄ(4～3月)"]
        assert worksheet["B75"].value is None
    finally:
        workbook.close()

    assert _validate_selected_template(str(path)) is None


def test_form_validation_does_not_require_system_cost_text_or_account(tmp_path):
    source = ROOT / "docs" / "MP2027" / "FORM.xlsx"
    path = tmp_path / "FORM_neutral.xlsx"
    workbook = openpyxl.load_workbook(source)
    worksheet = workbook["内訳ﾘｽﾄ(4～3月)"]
    for row in worksheet.iter_rows(min_col=2, max_col=20):
        for cell in row:
            text = str(cell.value or "").lower()
            if "system cost" in text or "kdc" in text or "システム" in text:
                cell.value = None
    workbook.save(path)
    workbook.close()

    assert _validate_selected_template(str(path)) is None


def test_invalid_template_b2_clears_old_ui_rate():
    path = ROOT / "docs" / "MP2027" / "FORM 1.xlsx"

    class Variable:
        def __init__(self, value):
            self.value = value

        def get(self):
            return self.value

        def set(self, value):
            self.value = value

    app = object.__new__(MPManagerApp)
    app.template_path = Variable(str(path))
    app.exchange_rate = Variable("26273")
    messages = []
    app.log = messages.append

    assert app._reload_exchange_rate_from_template() is False
    assert app.exchange_rate.get() == ""
    assert "B2" in messages[-1]


def test_missing_march_headcount_has_actionable_user_message():
    raw_error = (
        "Kiểm tra nguồn nhân sự & thời gian FY2027 không đạt.\n"
        "Chương trình dừng trước khi xuất FORM để tránh kết quả sai.\n"
        "- Phòng 1412000004 – 機器製造1課: chưa có Tổng số người tháng 03/2026. "
        "Dữ liệu này cần để tính chi phí tháng 04/2026. "
        "Hãy chọn “Nhập nhân sự thủ công”, nhập dữ liệu tháng này và lưu lại"
    )

    message = _friendly_error_message(ValueError(raw_error))

    assert message.startswith("Thiếu dữ liệu nhân sự để xuất báo cáo.")
    assert "Phòng 1412000004 – 機器製造1課" in message
    assert "Tổng số người tháng 03/2026" in message
    assert "tính chi phí tháng 04/2026" in message
    assert "Nhập nhân sự thủ công" in message
    assert "CHẠY TÍNH TOÁN" in message
    assert "kiểm tra lại Tệp mẫu FORM" not in message


def test_refresh_cost_centers_seeds_empty_database_from_selected_form(tmp_path, monkeypatch):
    from src import universal_app
    from src.db.schema import get_connection

    class Variable:
        def get(self):
            return str(ROOT / "docs" / "MP2027" / "FORM.xlsx")

    class Widget:
        def __init__(self):
            self.values = []
            self.states = []

        def __setitem__(self, key, value):
            assert key == "values"
            self.values = list(value)

        def configure(self, **kwargs):
            if "state" in kwargs:
                self.states.append(kwargs["state"])

    monkeypatch.setattr(universal_app, "BASE_DIR", str(tmp_path))
    notices = []
    monkeypatch.setattr(
        universal_app.messagebox,
        "showinfo",
        lambda title, message: notices.append((title, message)),
    )
    monkeypatch.setattr(
        universal_app.messagebox,
        "showerror",
        lambda title, message: notices.append((title, message)),
    )
    app = object.__new__(MPManagerApp)
    app.template_path = Variable()
    app.cc_combo = Widget()
    app.refresh_btn = Widget()
    app.messages = []
    app.log = app.messages.append

    app.refresh_cost_centers_from_form()

    conn = get_connection(str(tmp_path / "mp2027.db"))
    try:
        assert conn.execute("SELECT COUNT(*) FROM dim_cost_centers").fetchone()[0] == 65
        assert conn.execute(
            "SELECT name_jp FROM dim_cost_centers WHERE code='1412000004'"
        ).fetchone()[0] == "機器製造1課"
    finally:
        conn.close()
    assert len(app.cc_combo.values) == 65
    assert app.refresh_btn.states == [universal_app.tk.DISABLED, universal_app.tk.NORMAL]
    assert notices and notices[0][0] == "Nạp Trung tâm chi phí thành công"
    assert any("Đã nạp 65" in message for message in app.messages)


def test_refresh_cost_centers_uses_existing_database_without_reloading_form(tmp_path, monkeypatch):
    import sqlite3

    from src import universal_app
    from src.db.schema import create_schema

    class Variable:
        def get(self):
            return str(ROOT / "docs" / "MP2027" / "FORM.xlsx")

    class Widget:
        def __init__(self):
            self.values = []
            self.states = []

        def __setitem__(self, key, value):
            assert key == "values"
            self.values = list(value)

        def configure(self, **kwargs):
            if "state" in kwargs:
                self.states.append(kwargs["state"])

    monkeypatch.setattr(universal_app, "BASE_DIR", str(tmp_path))
    conn = sqlite3.connect(tmp_path / "mp2027.db")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    with conn:
        conn.execute(
            "INSERT INTO dim_cost_centers(code,name_jp,saisan_type,cost_type) VALUES(?,?,?,?)",
            ("1412000004", "機器製造1課", "製造", "製造"),
        )
    conn.close()

    def fail_if_reloaded(*_args, **_kwargs):
        raise AssertionError("Existing master must not reload FORM")

    monkeypatch.setattr(universal_app, "load_cost_centers", fail_if_reloaded)
    monkeypatch.setattr(universal_app.messagebox, "showinfo", fail_if_reloaded)
    app = object.__new__(MPManagerApp)
    app.template_path = Variable()
    app.cc_combo = Widget()
    app.refresh_btn = Widget()
    app.messages = []
    app.log = app.messages.append

    app.refresh_cost_centers_from_form()

    assert app.cc_combo.values == ["1412000004 - 機器製造1課"]
    assert app.refresh_btn.states == [universal_app.tk.DISABLED, universal_app.tk.NORMAL]
    assert any("Đã làm mới danh sách 1" in message for message in app.messages)
