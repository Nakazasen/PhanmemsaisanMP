import json
import sqlite3
import subprocess
import zipfile
from types import SimpleNamespace

import pytest

import src.universal_app as universal_app

from src.services.app_updates import (
    ApplicationUpdateError,
    activate_staged_update,
    application_install_root,
    backup_runtime_databases,
    inspect_update_package,
    install_runtime_application_update,
    resolve_current_entrypoint,
    rollback_activation,
    stage_application_update,
)
from src.services.update_security import canonical_json_bytes, generate_signing_keypair, sha256_bytes, sign_payload


def test_gui_application_version_uses_release_metadata(monkeypatch):
    monkeypatch.setattr(universal_app, "current_release_version", lambda: "0.9.1")

    assert universal_app.MPManagerApp._application_version() == "0.9.1"


def test_gui_window_title_identifies_owner_and_department():
    title = universal_app.MPManagerApp._window_title("2027", "0.9.1")

    assert title == "MP2027 Manager v0.9.1 - Quản lý Ngân sách | Bùi Đức Vinh - Phòng Phát triển hệ thống Chế tạo"


def test_gui_initial_window_size_fits_lower_resolution_screens():
    assert universal_app.MPManagerApp._initial_window_size(1920, 1080) == (1180, 800)
    assert universal_app.MPManagerApp._initial_window_size(1024, 768) == (976, 672)
    assert universal_app.MPManagerApp._initial_window_size(800, 600) == (752, 504)


def test_gui_discovered_update_shows_release_notes(monkeypatch):
    calls = {}
    logs = []
    candidate = SimpleNamespace(version="0.2.0", notes="• Sửa lỗi\n• Thêm hướng dẫn")
    monkeypatch.setattr(
        universal_app.messagebox,
        "askyesno",
        lambda title, message: calls.setdefault("prompt", (title, message)) and False,
    )

    app = SimpleNamespace(
        _startup_update_prompted=False,
        _application_update_running=False,
        log=logs.append,
    )

    universal_app.MPManagerApp._offer_discovered_update(app, candidate, "unused", "0.1.0")

    assert calls["prompt"][0] == "Có bản cập nhật MP2027"
    assert "Nội dung cập nhật:" in calls["prompt"][1]
    assert candidate.notes in calls["prompt"][1]
    assert any("hoãn" in message.lower() for message in logs)


def _build_update(path, private_key, *, version="0.2.0", payload=b"fake-exe", extras=None):
    entrypoint = "MP2027_Portable.exe"
    manifest = {
        "schema": 1,
        "kind": "application",
        "id": "MP2027_Manager",
        "version": version,
        "min_app_version": "0.1.0",
        "key_id": "pilot-2027-01",
        "database_schema": 1,
        "health_check": "--health-check",
        "entrypoint": entrypoint,
        "files": [{"path": entrypoint, "sha256": sha256_bytes(payload), "size": len(payload)}],
    }
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("manifest.json", canonical_json_bytes(manifest))
        archive.writestr("manifest.sig", sign_payload(manifest, private_key))
        archive.writestr(entrypoint, payload)
        for name, value in (extras or {}).items():
            archive.writestr(name, value)
    return manifest


def test_signed_update_stages_health_checks_activates_and_rolls_back(tmp_path):
    private, public = generate_signing_keypair()
    root = tmp_path / "install"
    old = root / "apps" / "0.1.0"
    old.mkdir(parents=True)
    (old / "MP2027_Portable.exe").write_bytes(b"old")
    old_manifest = old / "manifest.json"
    old_manifest.write_text("{}", encoding="utf-8")
    (root / "current.json").write_bytes(canonical_json_bytes({
        "schema": 1,
        "version": "0.1.0",
        "entrypoint": "MP2027_Portable.exe",
        "manifest_sha256": __import__("hashlib").sha256(b"{}").hexdigest(),
    }))
    update = tmp_path / "release.mpupdate"
    _build_update(update, private)

    staged = stage_application_update(
        update, root, public_key_b64=public, current_app_version="0.1.0", current_database_schema=1
    )
    calls = []

    def healthy(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0)

    state = activate_staged_update(
        root, "0.2.0", public_key_b64=public,
        health_data_root=tmp_path / "health", health_runner=healthy,
    )

    assert staged == root / "apps" / "0.2.0"
    assert state["version"] == "0.2.0"
    assert calls[0][0][-1] == "--health-check"
    assert resolve_current_entrypoint(root) == staged / "MP2027_Portable.exe"
    assert rollback_activation(root)["version"] == "0.1.0"
    assert resolve_current_entrypoint(root) == old / "MP2027_Portable.exe"


def test_update_rejects_wrong_key_downgrade_and_unexpected_files(tmp_path):
    private, public = generate_signing_keypair()
    _other_private, other_public = generate_signing_keypair()
    update = tmp_path / "release.mpupdate"
    _build_update(update, private)
    with pytest.raises(ApplicationUpdateError, match="chữ ký"):
        inspect_update_package(
            update, public_key_b64=other_public, current_app_version="0.1.0", current_database_schema=1
        )

    downgrade = tmp_path / "downgrade.mpupdate"
    _build_update(downgrade, private, version="0.1.0")
    with pytest.raises(ApplicationUpdateError, match="mới hơn"):
        inspect_update_package(
            downgrade, public_key_b64=public, current_app_version="0.1.0", current_database_schema=1
        )

    extra = tmp_path / "extra.mpupdate"
    _build_update(extra, private, extras={"surprise.txt": "no"})
    with pytest.raises(ApplicationUpdateError, match="không có trong kê khai"):
        inspect_update_package(
            extra, public_key_b64=public, current_app_version="0.1.0", current_database_schema=1
        )


def test_health_failure_does_not_change_current_pointer(tmp_path):
    private, public = generate_signing_keypair()
    root = tmp_path / "install"
    update = tmp_path / "release.mpupdate"
    _build_update(update, private)
    stage_application_update(
        update, root, public_key_b64=public, current_app_version="0.1.0", current_database_schema=1
    )

    def unhealthy(*_args, **_kwargs):
        raise subprocess.CalledProcessError(2, "health")

    with pytest.raises(ApplicationUpdateError, match="kiểm tra tình trạng"):
        activate_staged_update(
            root, "0.2.0", public_key_b64=public,
            health_data_root=tmp_path / "health", health_runner=unhealthy,
        )
    assert not (root / "current.json").exists()


def test_database_backup_has_inventory_and_preserves_source(tmp_path):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    database = runtime / "data.db"
    conn = sqlite3.connect(database)
    conn.execute("CREATE TABLE sample(value TEXT)")
    conn.execute("INSERT INTO sample VALUES ('kept')")
    conn.commit()
    conn.close()

    backup = backup_runtime_databases(runtime, tmp_path / "backups", target_version="0.2.0")

    inventory = json.loads((backup / "backup.json").read_text(encoding="utf-8"))
    assert inventory["files"][0]["path"] == "data.db"
    copied = sqlite3.connect(backup / "data.db")
    assert copied.execute("SELECT value FROM sample").fetchone()[0] == "kept"
    copied.close()
    assert database.is_file()


def test_release_builder_is_deterministic_and_verifiable(tmp_path):
    from scripts import package_app

    private, public = generate_signing_keypair()
    app_dist = tmp_path / "app-dist"
    (app_dist / "_internal").mkdir(parents=True)
    (app_dist / "MP2027_Portable.exe").write_bytes(b"portable-app")
    (app_dist / "_internal" / "runtime.dll").write_bytes(b"runtime")
    key_path = tmp_path / "release.key"
    key_path.write_text(private, encoding="ascii")
    release_path = tmp_path / "release.json"
    release_path.write_text(json.dumps({"version": "0.2.0"}), encoding="utf-8")
    first = tmp_path / "first.mpupdate"
    second = tmp_path / "second.mpupdate"

    for output in (first, second):
        package_app.build_signed_update(
            app_dist,
            output,
            private_key_path=key_path,
            key_id="pilot-2027-01",
            min_app_version="0.1.0",
            release_path=release_path,
        )

    assert first.read_bytes() == second.read_bytes()
    manifest = inspect_update_package(
        first,
        public_key_b64=public,
        current_app_version="0.1.0",
        current_database_schema=1,
    )
    assert manifest["version"] == "0.2.0"
    assert [item["path"] for item in manifest["files"]] == [
        "MP2027_Portable.exe",
        "_internal/runtime.dll",
    ]


def test_release_builder_rejects_manifest_larger_than_shared_limit(tmp_path, monkeypatch):
    from scripts import package_app
    from src.services import update_security

    private, _public = generate_signing_keypair()
    app_dist = tmp_path / "app-dist"
    app_dist.mkdir()
    (app_dist / "MP2027_Portable.exe").write_bytes(b"portable-app")
    key_path = tmp_path / "release.key"
    key_path.write_text(private, encoding="ascii")
    release_path = tmp_path / "release.json"
    release_path.write_text(json.dumps({"version": "0.2.0"}), encoding="utf-8")
    monkeypatch.setattr(update_security, "MAX_MANIFEST_BYTES", 1)

    with pytest.raises(ValueError, match="Tệp kê khai cập nhật"):
        package_app.build_signed_update(
            app_dist,
            tmp_path / "release.mpupdate",
            private_key_path=key_path,
            key_id="pilot-2027-01",
            min_app_version="0.1.0",
            release_path=release_path,
        )


def test_release_builder_rejects_private_key_inside_repository(tmp_path, monkeypatch):
    from scripts import package_app

    private, _public = generate_signing_keypair()
    monkeypatch.setattr(package_app, "PROJECT_ROOT", tmp_path)
    key_path = tmp_path / "secret" / "release.key"
    key_path.parent.mkdir()
    key_path.write_text(private, encoding="ascii")

    with pytest.raises(ValueError, match="ngoài thư mục dự án"):
        package_app._read_external_private_key(key_path)


def _write_release_keyring(path, public_key, *, purposes):
    path.write_text(json.dumps({
        "version": "0.1.0",
        "trusted_signing_keys": [{
            "id": "pilot-2027-01",
            "public_key": public_key,
            "purposes": purposes,
        }],
    }), encoding="utf-8")


def test_runtime_offline_update_uses_application_key_health_backup_and_activation(tmp_path):
    private, public = generate_signing_keypair()
    update = tmp_path / "release.mpupdate"
    _build_update(update, private)
    release_metadata = tmp_path / "release.json"
    _write_release_keyring(release_metadata, public, purposes=["application"])
    install_root = tmp_path / "MP2027 Manager"
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    (runtime_root / "manual_inputs.db").write_bytes(b"database-snapshot")
    calls = []

    def healthy(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0)

    state = install_runtime_application_update(
        update,
        install_root,
        runtime_root,
        current_database_schema=1,
        release_metadata_path_override=release_metadata,
        health_runner=healthy,
    )

    assert state["version"] == "0.2.0"
    assert json.loads((install_root / "current.json").read_text(encoding="utf-8"))["version"] == "0.2.0"
    assert (install_root / "backups" / "before-0.2.0" / "manual_inputs.db").read_bytes() == b"database-snapshot"
    assert calls[0][0][-1] == "--health-check"


def test_runtime_offline_update_rejects_content_only_key_before_staging(tmp_path):
    private, public = generate_signing_keypair()
    update = tmp_path / "release.mpupdate"
    _build_update(update, private)
    release_metadata = tmp_path / "release.json"
    _write_release_keyring(release_metadata, public, purposes=["content"])
    install_root = tmp_path / "MP2027 Manager"

    with pytest.raises(ApplicationUpdateError, match="không nằm trong danh sách tin cậy"):
        install_runtime_application_update(
            update,
            install_root,
            tmp_path / "runtime",
            current_database_schema=1,
            release_metadata_path_override=release_metadata,
        )

    assert not (install_root / "apps" / "0.2.0").exists()
    assert not (install_root / "current.json").exists()


def test_application_install_root_only_accepts_versioned_onedir_layout(tmp_path):
    version_dir = tmp_path / "MP2027 Manager" / "apps" / "0.1.0"
    assert application_install_root(version_dir) == tmp_path / "MP2027 Manager"
    with pytest.raises(ApplicationUpdateError, match="đã cài đặt"):
        application_install_root(tmp_path / "source-checkout")


def test_gui_offline_update_uses_runtime_trust_without_key_prompt(monkeypatch, tmp_path):
    version_dir = tmp_path / "MP2027 Manager" / "apps" / "0.1.0"
    package_path = tmp_path / "release.mpupdate"
    calls = {}
    logs = []

    class ImmediateThread:
        def __init__(self, *, target, daemon):
            calls["thread_daemon"] = daemon
            self.target = target

        def start(self):
            self.target()

    def fake_install(path, app_root, runtime_root, *, current_database_schema):
        calls["install"] = (path, app_root, runtime_root, current_database_schema)
        return {"version": "0.2.0"}

    monkeypatch.setattr(universal_app, "APP_DIR", str(version_dir))
    monkeypatch.setattr(
        universal_app.filedialog,
        "askopenfilename",
        lambda **kwargs: calls.setdefault("file_dialog", kwargs) and str(package_path),
    )
    monkeypatch.setattr(universal_app, "install_runtime_application_update", fake_install)
    monkeypatch.setattr(universal_app.threading, "Thread", ImmediateThread)
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
        _application_update_running=False,
        log=logs.append,
    )
    app._finish_application_update = lambda state, error: (
        universal_app.MPManagerApp._finish_application_update(app, state, error)
    )
    app._run_on_ui_thread = lambda callback, *args: callback(*args)

    universal_app.MPManagerApp.install_application_update(app)

    assert calls["install"] == (
        str(package_path),
        tmp_path / "MP2027 Manager",
        universal_app.BASE_DIR,
        universal_app.CURRENT_SCHEMA_VERSION,
    )
    assert calls["file_dialog"]["filetypes"] == [("Bản cập nhật MP2027", "*.mpupdate")]
    assert calls["thread_daemon"] is True
    assert "0.2.0" in calls["showinfo"][1]
    assert "showerror" not in calls
    assert app._application_update_running is False
    assert any("kích hoạt" in message.lower() for message in logs)
