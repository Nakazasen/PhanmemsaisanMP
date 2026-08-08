from pathlib import Path
import shutil

import openpyxl

from src.services.project_config import ProjectConfig
from src.services.template_confirmation import confirmation_status, inspect_form
from src.universal_app import MPManagerApp


ROOT = Path(__file__).resolve().parents[1]
FORM = ROOT / "docs" / "MP2027" / "FORM.xlsx"


def test_new_valid_form_requires_confirmation_and_then_is_known(tmp_path):
    form = tmp_path / "FORM.xlsx"
    shutil.copy2(FORM, form)

    inspection = inspect_form(form)

    assert inspection.is_valid
    assert confirmation_status({}, inspection) == "new"
    assert confirmation_status({inspection.checksum: inspection.as_confirmation()}, inspection) == "known"


def test_changed_form_at_same_path_requires_confirmation_again(tmp_path):
    form = tmp_path / "FORM.xlsx"
    shutil.copy2(FORM, form)
    first = inspect_form(form)
    workbook = openpyxl.load_workbook(form)
    workbook["内訳ﾘｽﾄ(4～3月)"]["B2"] = 26274
    workbook.save(form)
    workbook.close()
    changed = inspect_form(form)

    assert changed.is_valid
    assert changed.checksum != first.checksum
    assert confirmation_status({first.checksum: first.as_confirmation()}, changed) == "changed"


def test_form_with_department_payload_cannot_be_confirmed(tmp_path):
    form = tmp_path / "FORM.xlsx"
    shutil.copy2(FORM, form)
    workbook = openpyxl.load_workbook(form)
    workbook["内訳ﾘｽﾄ(4～3月)"]["B5"] = 1412000004
    workbook.save(form)
    workbook.close()

    inspection = inspect_form(form)

    assert not inspection.is_valid
    assert inspection.issue_cells == ("B5",)
    assert confirmation_status({}, inspection) == "invalid"


def test_project_persists_form_confirmation(tmp_path):
    project = ProjectConfig.create_legacy_compatible(str(tmp_path))
    record = {"checksum": "a" * 64, "path": str(tmp_path / "FORM.xlsx")}

    project.confirm_form(2027, record)
    project.save()
    restored = ProjectConfig.load(project.config_path)

    assert restored.form_confirmations(2027)[record["checksum"]] == record


def test_ui_confirms_new_form_once_then_recognizes_it(monkeypatch, tmp_path):
    form = tmp_path / "FORM.xlsx"
    shutil.copy2(FORM, form)
    project = ProjectConfig.create_legacy_compatible(str(tmp_path))
    app = object.__new__(MPManagerApp)
    app.project = project
    messages = []
    app.log = messages.append
    prompts = []
    monkeypatch.setattr(
        "src.universal_app.messagebox.askyesno",
        lambda title, message: prompts.append((title, message)) or True,
    )

    assert app._confirm_selected_form(str(form), 2027)
    assert prompts == [
        ("Xác nhận FORM", "FORM này chưa được dùng trước đây.\nVui lòng kiểm tra lại biểu mẫu trước khi chạy.")
    ]
    assert messages == ["Đã xác nhận FORM cho lần chạy này."]

    monkeypatch.setattr(
        "src.universal_app.messagebox.askyesno",
        lambda *_args: (_ for _ in ()).throw(AssertionError("FORM unchanged must not prompt")),
    )
    assert app._confirm_selected_form(str(form), 2027)
