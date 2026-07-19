import ast
import json
import sqlite3
import zipfile
from pathlib import Path
from types import SimpleNamespace

import openpyxl
import pytest

import src.universal_app as universal_app
import scripts.run_e2e as run_e2e

from src.db.loader import load_allocation_rules
from src.db.schema import create_schema
from src.services.fiscal_run import (
    ISSUE_SOURCE_SKIPPED,
    RunPreflightReport,
    create_fiscal_run_context,
    preflight_fiscal_run,
)
from src.services.content_packs import (
    ContentPackError,
    activate_content_pack,
    inspect_content_pack,
    install_content_pack,
    install_runtime_content_pack,
    load_active_content_rules,
    load_runtime_content_rules,
    validate_rules,
)
from src.services.update_security import (
    canonical_json_bytes,
    generate_signing_keypair,
    sha256_bytes,
    sign_payload,
)


def _rules():
    return {
        "schema": 1,
        "rules": [{
            "source_dept": "GA",
            "item_name": "Chi phí riêng phòng ban",
            "account_name": "福利厚生費",
            "ga_account": 551100,
            "posting_month": "12",
            "unit_price": 125000.0,
            "unit": "VND/person",
            "driver_type": "headcount_all",
            "driver_raw": "Số người",
        }],
    }


def _build_pack(path, private_key, *, min_app="0.1.0", rules=None, extras=None):
    rules_bytes = canonical_json_bytes(rules or _rules())
    manifest = {
        "schema": 1,
        "kind": "content",
        "id": "dept-ga",
        "version": "1.2.0",
        "min_app_version": min_app,
        "key_id": "pilot-2027-01",
        "content_schema": 1,
        "fiscal_year": 2027,
        "files": [{"path": "rules.json", "sha256": sha256_bytes(rules_bytes), "size": len(rules_bytes)}],
    }
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("manifest.json", canonical_json_bytes(manifest))
        archive.writestr("manifest.sig", sign_payload(manifest, private_key))
        archive.writestr("rules.json", rules_bytes)
        for name, value in (extras or {}).items():
            archive.writestr(name, value)
    return manifest


def _connection():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_schema(connection)
    return connection


def _write_allocation_workbook(path, *, source_dept="GA", item_name="Workbook rule"):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "FY2027配賦額一覧"
    sheet.append([
        "dept", "item", "account", "mfg", "ga", "sales",
        "posting", "unit_price", "unit", "driver",
    ])
    sheet.append([
        source_dept, item_name, "福利厚生費", None, 551100, None,
        "12月", 100000, "VND/person", "Số người",
    ])
    workbook.save(path)
    workbook.close()


def test_signed_content_pack_installs_and_activates_atomically(tmp_path):
    private, public = generate_signing_keypair()
    pack = tmp_path / "dept-ga.mpcontent"
    _build_pack(pack, private)

    destination = install_content_pack(
        pack,
        tmp_path / "content-packs",
        public_key_b64=public,
        current_app_version="0.1.0",
        activate=True,
    )

    assert destination.name == "1.2.0"
    assert (destination / "rules.json").is_file()
    active = json.loads((tmp_path / "content-packs" / "active.json").read_text(encoding="utf-8"))
    assert active["id"] == "dept-ga"
    assert active["version"] == "1.2.0"
    assert not (tmp_path / "content-packs" / "active.json.tmp").exists()


def test_content_pack_rejects_wrong_key_tamper_and_unexpected_code(tmp_path):
    private, _public = generate_signing_keypair()
    _other_private, other_public = generate_signing_keypair()
    pack = tmp_path / "pack.mpcontent"
    _build_pack(pack, private)
    with pytest.raises(ContentPackError, match="chữ ký"):
        inspect_content_pack(pack, public_key_b64=other_public, current_app_version="0.1.0")

    code_pack = tmp_path / "code.mpcontent"
    _build_pack(code_pack, private, extras={"plugin.py": "raise SystemExit"})
    with pytest.raises(ContentPackError, match="không có trong kê khai"):
        inspect_content_pack(code_pack, public_key_b64=_public, current_app_version="0.1.0")


def test_content_pack_enforces_version_and_restricted_rules(tmp_path):
    private, public = generate_signing_keypair()
    pack = tmp_path / "future.mpcontent"
    _build_pack(pack, private, min_app="9.0.0")
    with pytest.raises(ContentPackError, match="mới hơn"):
        inspect_content_pack(pack, public_key_b64=public, current_app_version="0.1.0")

    invalid = _rules()
    invalid["rules"][0]["driver_type"] = "execute_python"
    with pytest.raises(ContentPackError, match="cách tính không được hỗ trợ"):
        validate_rules(invalid)


def test_activation_requires_an_installed_version(tmp_path):
    with pytest.raises(ContentPackError, match="Không tìm thấy"):
        activate_content_pack(tmp_path, "missing", "1.0.0")


def test_active_content_rules_are_fully_revalidated_for_each_fiscal_run(tmp_path):
    private, public = generate_signing_keypair()
    pack = tmp_path / "dept-ga.mpcontent"
    _build_pack(pack, private)
    root = tmp_path / "content-packs"
    destination = install_content_pack(
        pack,
        root,
        public_key_b64=public,
        current_app_version="0.1.0",
        activate=True,
    )

    rules = load_active_content_rules(
        root,
        public_key_b64=public,
        current_app_version="0.1.0",
        fiscal_year=2027,
    )
    assert rules == _rules()["rules"]

    with pytest.raises(ContentPackError, match="FY2027, không phải FY2028"):
        load_active_content_rules(
            root,
            public_key_b64=public,
            current_app_version="0.1.0",
            fiscal_year=2028,
        )

    (destination / "unexpected.txt").write_text("not signed", encoding="utf-8")
    with pytest.raises(ContentPackError, match="không có trong kê khai"):
        load_active_content_rules(
            root,
            public_key_b64=public,
            current_app_version="0.1.0",
            fiscal_year=2027,
        )


def test_active_content_state_hash_tamper_is_rejected(tmp_path):
    private, public = generate_signing_keypair()
    pack = tmp_path / "dept-ga.mpcontent"
    _build_pack(pack, private)
    root = tmp_path / "content-packs"
    install_content_pack(
        pack,
        root,
        public_key_b64=public,
        current_app_version="0.1.0",
        activate=True,
    )
    state_path = root / "active.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["manifest_sha256"] = "0" * 64
    state_path.write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(ContentPackError, match="Tệp kê khai.*bị thiếu hoặc đã thay đổi"):
        load_active_content_rules(
            root,
            public_key_b64=public,
            current_app_version="0.1.0",
            fiscal_year=2027,
        )


def test_verified_content_rules_map_to_database_columns(tmp_path):
    connection = _connection()
    try:
        loaded = load_allocation_rules(
            connection,
            alloc_path=str(tmp_path / "missing.xlsx"),
            search_dir=str(tmp_path),
            fiscal_year=2027,
            content_rules=_rules()["rules"],
        )
        assert loaded == 1
        row = connection.execute("SELECT * FROM map_allocation_rules").fetchone()
        assert row["source_dept"] == "GA"
        assert row["item_name"] == "Chi phí riêng phòng ban"
        assert row["ga_account"] == 551100
        assert row["posting_month"] == "12"
        assert row["unit_price"] == 125000.0
        assert row["driver_type"] == "headcount_all"
    finally:
        connection.close()


def test_content_workbook_conflict_rolls_back_previous_rules(tmp_path):
    connection = _connection()
    try:
        connection.execute(
            """
            INSERT INTO map_allocation_rules
            (source_dept, item_name, unit_price, driver_type)
            VALUES ('OLD', 'Previous committed rule', 1, 'headcount_all')
            """
        )
        connection.commit()
        workbook_path = tmp_path / "rules.xlsx"
        _write_allocation_workbook(
            workbook_path,
            source_dept="GA",
            item_name="Chi phí riêng phòng ban",
        )

        with pytest.raises(ValueError, match="trùng với workbook"):
            load_allocation_rules(
                connection,
                alloc_path=str(workbook_path),
                search_dir=str(tmp_path),
                fiscal_year=2027,
                content_rules=_rules()["rules"],
            )

        remaining = connection.execute(
            "SELECT source_dept, item_name FROM map_allocation_rules"
        ).fetchall()
        assert [(row["source_dept"], row["item_name"]) for row in remaining] == [
            ("OLD", "Previous committed rule")
        ]
    finally:
        connection.close()


def test_runtime_content_rules_are_noop_without_active_pack(tmp_path):
    missing_release_metadata = tmp_path / "missing-release.json"
    assert load_runtime_content_rules(
        tmp_path,
        fiscal_year=2027,
        release_metadata_path=missing_release_metadata,
    ) == []


def test_runtime_content_rules_select_trusted_key_by_id_and_purpose(tmp_path):
    private, public = generate_signing_keypair()
    pack = tmp_path / "dept-ga.mpcontent"
    _build_pack(pack, private)
    content_root = tmp_path / "content-packs"
    install_content_pack(
        pack,
        content_root,
        public_key_b64=public,
        current_app_version="0.1.0",
        activate=True,
    )
    release_metadata = tmp_path / "release.json"
    release_metadata.write_text(json.dumps({
        "version": "0.1.0",
        "trusted_signing_keys": [{
            "id": "pilot-2027-01",
            "public_key": public,
            "purposes": ["content"],
        }],
    }), encoding="utf-8")

    assert load_runtime_content_rules(
        tmp_path,
        fiscal_year=2027,
        release_metadata_path=release_metadata,
    ) == _rules()["rules"]

    payload = json.loads(release_metadata.read_text(encoding="utf-8"))
    payload["trusted_signing_keys"][0]["purposes"] = ["application"]
    release_metadata.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ContentPackError, match="không nằm trong danh sách tin cậy"):
        load_runtime_content_rules(
            tmp_path,
            fiscal_year=2027,
            release_metadata_path=release_metadata,
        )


def test_content_collision_preserves_unrelated_pending_transaction(tmp_path):
    connection = _connection()
    try:
        connection.execute("CREATE TABLE caller_pending (value TEXT NOT NULL)")
        connection.commit()
        connection.execute("INSERT INTO caller_pending (value) VALUES ('keep me')")
        workbook_path = tmp_path / "rules.xlsx"
        _write_allocation_workbook(
            workbook_path,
            source_dept="GA",
            item_name="Chi phí riêng phòng ban",
        )

        with pytest.raises(ValueError, match="trùng với workbook"):
            load_allocation_rules(
                connection,
                alloc_path=str(workbook_path),
                search_dir=str(tmp_path),
                fiscal_year=2027,
                content_rules=_rules()["rules"],
            )

        assert connection.execute("SELECT value FROM caller_pending").fetchone()[0] == "keep me"
        assert connection.in_transaction
    finally:
        connection.rollback()
        connection.close()


def test_release_savepoint_failure_preserves_original_error_and_caller_transaction(tmp_path):
    connection = _connection()
    connection.execute("CREATE TABLE caller_pending (value TEXT NOT NULL)")
    connection.commit()
    connection.execute("INSERT INTO caller_pending (value) VALUES ('keep me')")

    class ReleaseOnceCursor:
        def __init__(self, cursor):
            self._cursor = cursor
            self._failed_release = False

        def execute(self, sql, *args):
            if sql.startswith("RELEASE SAVEPOINT") and not self._failed_release:
                self._failed_release = True
                raise RuntimeError("original release failure")
            return self._cursor.execute(sql, *args)

        def executemany(self, sql, parameters):
            return self._cursor.executemany(sql, parameters)

    class ConnectionProxy:
        def cursor(self):
            return ReleaseOnceCursor(connection.cursor())

        def execute(self, *args, **kwargs):
            return connection.execute(*args, **kwargs)

        def executemany(self, *args, **kwargs):
            return connection.executemany(*args, **kwargs)

        def commit(self):
            return connection.commit()

        def rollback(self):
            raise AssertionError("caller transaction must not be rolled back")

    try:
        with pytest.raises(RuntimeError, match="original release failure"):
            load_allocation_rules(
                ConnectionProxy(),
                alloc_path=str(tmp_path / "missing.xlsx"),
                search_dir=str(tmp_path),
                fiscal_year=2027,
                content_rules=_rules()["rules"],
            )

        assert connection.execute("SELECT value FROM caller_pending").fetchone()[0] == "keep me"
        assert connection.execute("SELECT COUNT(*) FROM map_allocation_rules").fetchone()[0] == 0
        assert connection.in_transaction
    finally:
        connection.rollback()
        connection.close()


def test_commit_failure_after_release_preserves_commit_error(tmp_path):
    connection = _connection()
    connection.execute("CREATE TABLE caller_pending (value TEXT NOT NULL)")
    connection.commit()
    connection.execute("INSERT INTO caller_pending (value) VALUES ('rollback me')")

    class CommitFailureProxy:
        rollback_calls = 0

        def cursor(self):
            return connection.cursor()

        def execute(self, *args, **kwargs):
            return connection.execute(*args, **kwargs)

        def executemany(self, *args, **kwargs):
            return connection.executemany(*args, **kwargs)

        def commit(self):
            raise RuntimeError("original commit failure")

        def rollback(self):
            self.rollback_calls += 1
            connection.rollback()
            raise RuntimeError("cleanup rollback failure")

    proxy = CommitFailureProxy()
    try:
        with pytest.raises(RuntimeError, match="original commit failure"):
            load_allocation_rules(
                proxy,
                alloc_path=str(tmp_path / "missing.xlsx"),
                search_dir=str(tmp_path),
                fiscal_year=2027,
                content_rules=_rules()["rules"],
            )

        assert proxy.rollback_calls == 1
        assert not connection.in_transaction
        assert connection.execute("SELECT COUNT(*) FROM caller_pending").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM map_allocation_rules").fetchone()[0] == 0
    finally:
        connection.close()


def test_runtime_installer_uses_trusted_key_and_activates(tmp_path):
    private, public = generate_signing_keypair()
    pack = tmp_path / "dept-ga.mpcontent"
    _build_pack(pack, private)
    release_metadata = tmp_path / "release.json"
    release_metadata.write_text(json.dumps({
        "version": "0.1.0",
        "trusted_signing_keys": [{
            "id": "pilot-2027-01",
            "public_key": public,
            "purposes": ["content"],
        }],
    }), encoding="utf-8")

    installed = install_runtime_content_pack(
        pack,
        tmp_path,
        fiscal_year=2027,
        release_metadata_path=release_metadata,
    )

    assert installed == tmp_path / "content-packs" / "installed" / "dept-ga" / "1.2.0"
    assert (tmp_path / "content-packs" / "active.json").is_file()
    assert load_runtime_content_rules(
        tmp_path,
        fiscal_year=2027,
        release_metadata_path=release_metadata,
    ) == _rules()["rules"]


def test_runtime_installer_rejects_wrong_fy_before_install(tmp_path):
    private, public = generate_signing_keypair()
    pack = tmp_path / "dept-ga.mpcontent"
    _build_pack(pack, private)
    release_metadata = tmp_path / "release.json"
    release_metadata.write_text(json.dumps({
        "version": "0.1.0",
        "trusted_signing_keys": [{
            "id": "pilot-2027-01",
            "public_key": public,
            "purposes": ["content"],
        }],
    }), encoding="utf-8")

    with pytest.raises(ContentPackError, match="FY2027, không phải FY2028"):
        install_runtime_content_pack(
            pack,
            tmp_path,
            fiscal_year=2028,
            release_metadata_path=release_metadata,
        )

    assert not (tmp_path / "content-packs" / "active.json").exists()
    assert not (tmp_path / "content-packs" / "installed").exists()


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def test_pipeline_verifies_runtime_content_before_database_access_and_passes_rules():
    project_root = Path(__file__).resolve().parents[1]
    tree = ast.parse((project_root / "scripts" / "run_e2e.py").read_text(encoding="utf-8-sig"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "run_universal_pipeline"
    )
    calls = [node for node in ast.walk(function) if isinstance(node, ast.Call)]
    verify_call = next(node for node in calls if _call_name(node) == "load_runtime_content_rules")
    connection_call = next(node for node in calls if _call_name(node) == "get_connection")
    load_call = next(node for node in calls if _call_name(node) == "load_all")

    assert verify_call.lineno < connection_call.lineno < load_call.lineno
    content_keyword = next(keyword for keyword in load_call.keywords if keyword.arg == "content_rules")
    assert isinstance(content_keyword.value, ast.Name)
    assert content_keyword.value.id == "content_rules"


def test_preflight_keeps_missing_allocation_workbook_non_blocking_for_content_only_run(tmp_path):
    source_dir = tmp_path / "docs" / "MP2028"
    headcount_dir = tmp_path / "raw" / "FY2028"
    source_dir.mkdir(parents=True)
    headcount_dir.mkdir(parents=True)
    context = create_fiscal_run_context(2028, base_dir=tmp_path)

    report = preflight_fiscal_run(context)

    allocation_issue = next(
        issue
        for issue in report.issues
        if issue.category == "allocation_rules" and issue.code == "MISSING_SOURCE"
    )
    assert allocation_issue.severity == ISSUE_SOURCE_SKIPPED
    assert allocation_issue not in report.blocking_issues


def test_runtime_pipeline_passes_verified_content_rules_to_loader(monkeypatch, tmp_path):
    verified_rules = _rules()["rules"]
    calls = {}

    monkeypatch.setattr(
        run_e2e,
        "preflight_fiscal_run",
        lambda context: RunPreflightReport(fiscal_year=2027, resolved_sources={}),
    )

    def verify_rules(runtime_root, *, fiscal_year):
        calls["verify"] = (runtime_root, fiscal_year)
        return verified_rules

    def capture_load(**kwargs):
        calls["load"] = kwargs
        raise RuntimeError("stop after verified content reaches loader")

    monkeypatch.setattr(run_e2e, "load_runtime_content_rules", verify_rules)
    monkeypatch.setattr(run_e2e, "load_all", capture_load)

    ok, message = run_e2e.run_universal_pipeline(
        2027,
        str(tmp_path / "FORM.xlsx"),
        str(tmp_path),
        headcount_source_dir=str(tmp_path / "headcount"),
        db_path=str(tmp_path / "isolated.db"),
        output_dir=str(tmp_path / "output"),
        preserve_run_history=False,
        mp_saisan_complete_v1=False,
        log_callback=lambda _message: None,
    )

    assert not ok
    assert "stop after verified content reaches loader" in message
    assert calls["verify"] == (run_e2e.BASE_DIR, 2027)
    assert calls["load"]["content_rules"] is verified_rules
    assert calls["load"]["include_allocation_rules"] is True
    assert calls["load"]["rules_path"] is None


def test_gui_content_install_uses_runtime_trust_without_key_prompt(monkeypatch, tmp_path):
    package_path = tmp_path / "department.mpcontent"
    installed_path = tmp_path / "content-packs" / "installed" / "dept-ga" / "1.2.0"
    calls = {}
    logs = []

    def choose_package(**kwargs):
        calls["file_dialog"] = kwargs
        return str(package_path)

    def fake_install(path, runtime_root, *, fiscal_year):
        calls["install"] = (path, runtime_root, fiscal_year)
        return installed_path

    monkeypatch.setattr(universal_app.filedialog, "askopenfilename", choose_package)
    monkeypatch.setattr(universal_app, "install_runtime_content_pack", fake_install)
    monkeypatch.setattr(
        universal_app.messagebox,
        "showinfo",
        lambda title, message: calls.setdefault("showinfo", (title, message)),
    )
    monkeypatch.setattr(
        universal_app.messagebox,
        "showerror",
        lambda *args, **kwargs: calls.setdefault("showerror", (args, kwargs)),
    )
    monkeypatch.setattr(
        universal_app.messagebox,
        "askyesno",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not prompt for key trust")),
    )

    app = SimpleNamespace(
        fiscal_year=SimpleNamespace(get=lambda: "2027"),
        log=logs.append,
        _mark_preflight_stale=lambda **kwargs: calls.setdefault("preflight", kwargs),
    )
    universal_app.MPManagerApp.install_content_package(app)

    assert calls["install"] == (str(package_path), universal_app.BASE_DIR, 2027)
    assert calls["preflight"] == {"force_refresh": True}
    assert calls["file_dialog"]["filetypes"] == [("Gói quy tắc MP2027", "*.mpcontent")]
    assert "FY2027" in calls["showinfo"][1]
    assert "showerror" not in calls
    assert any("đã xác minh" in message.lower() for message in logs)
