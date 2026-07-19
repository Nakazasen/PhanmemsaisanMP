import json
import importlib
import importlib.util
import sys
import types
from pathlib import Path

from scripts import package_app, update_launcher
from src.services.app_updates import resolve_current_entrypoint


def test_run_e2e_exposes_callable_main():
    module = importlib.import_module("scripts.run_e2e")

    assert callable(module.main)


def test_packaging_entrypoint_file_import_has_callable_main():
    entrypoint = Path("packaging/mp2027_portable_entry.py")
    spec = importlib.util.spec_from_file_location("mp2027_portable_entry_smoke", entrypoint)
    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    assert callable(module.main)


def test_packaging_health_dispatch_does_not_import_gui(tmp_path, monkeypatch):
    entrypoint = Path("packaging/mp2027_portable_entry.py")
    spec = importlib.util.spec_from_file_location("mp2027_portable_entry_health", entrypoint)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    health = types.ModuleType("src.services.runtime_health")
    health.ensure_external_runtime_data = lambda *_args, **_kwargs: str(tmp_path)
    health.print_health_report = lambda runtime_root: 0 if runtime_root == str(tmp_path) else 2
    monkeypatch.setitem(sys.modules, "src.services.runtime_health", health)
    monkeypatch.setitem(sys.modules, "src.universal_app", None)
    monkeypatch.setattr(sys, "argv", ["MP2027_Portable.exe", "--health-check"])

    assert module.main() == 0


def test_run_e2e_tolerates_windowed_packaged_streams(monkeypatch):
    module = importlib.import_module("scripts.run_e2e")

    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    module._ensure_text_streams()
    module._safe_console_print("headless packaged log")

    assert sys.stdout is not None
    assert sys.stderr is not None


def test_frozen_launcher_defaults_to_executable_directory(tmp_path, monkeypatch):
    executable = tmp_path / "MP2027_Launcher.exe"
    monkeypatch.setattr(update_launcher.sys, "frozen", True, raising=False)
    monkeypatch.setattr(update_launcher.sys, "executable", str(executable))

    assert update_launcher.default_app_root() == tmp_path


def test_launcher_import_does_not_load_signed_update_service(monkeypatch):
    launcher_path = Path("scripts/update_launcher.py")
    spec = importlib.util.spec_from_file_location("mp2027_lightweight_launcher", launcher_path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "src.services.app_updates", None)

    spec.loader.exec_module(module)

    assert callable(module.resolve_current_entrypoint)
    assert callable(module.main)


def test_launcher_health_check_waits_for_active_app_and_returns_its_status(tmp_path, monkeypatch):
    executable = tmp_path / "apps" / "0.1.0" / "MP2027_Portable.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"app")
    calls = []

    monkeypatch.setattr(update_launcher, "resolve_current_entrypoint", lambda _root: executable)
    monkeypatch.setattr(
        update_launcher.subprocess,
        "run",
        lambda *args, **kwargs: calls.append((args, kwargs)) or update_launcher.subprocess.CompletedProcess(args[0], 7),
    )

    result = update_launcher.main(["--app-root", str(tmp_path), "--health-check"])

    assert result == 7
    assert calls[0][0][0] == [str(executable), "--health-check"]
    assert calls[0][1]["cwd"] == str(executable.parent)
    assert calls[0][1]["timeout"] == 180


def test_packaging_health_smokes_allow_cold_start_on_slow_machines(tmp_path, monkeypatch):
    app_dist = tmp_path / "app"
    bundle = tmp_path / "bundle"
    app_dist.mkdir()
    bundle.mkdir()
    (app_dist / "MP2027_Portable.exe").write_bytes(b"app")
    (bundle / "MP2027_Launcher.exe").write_bytes(b"launcher")
    calls = []

    monkeypatch.setattr(package_app, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        package_app.subprocess,
        "run",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    package_app.smoke_packaged_health(app_dist)
    package_app.smoke_launcher_health(bundle)

    assert [call[1]["timeout"] for call in calls] == [180, 180]


def test_package_builds_app_and_launcher_then_assembles_bundle(monkeypatch):
    events = []

    monkeypatch.setattr(Path, "is_file", lambda _path: True)
    monkeypatch.setattr(package_app, "_build", lambda path: events.append(("build", path)))
    monkeypatch.setattr(package_app, "_validate_dist", lambda path: events.append(("validate", path)))
    monkeypatch.setattr(package_app, "smoke_packaged_health", lambda path: events.append(("health", path)))
    monkeypatch.setattr(
        package_app,
        "assemble_install_bundle",
        lambda: events.append(("bundle", package_app.INSTALL_BUNDLE_ROOT)) or package_app.INSTALL_BUNDLE_ROOT,
    )
    monkeypatch.setattr(package_app, "smoke_launcher_health", lambda path: events.append(("launcher_health", path)))

    package_app.package()

    assert [event[0] for event in events] == [
        "build",
        "validate",
        "health",
        "build",
        "bundle",
        "launcher_health",
    ]


def test_assemble_install_bundle_writes_versioned_current_pointer(tmp_path, monkeypatch):
    app_dist = tmp_path / "app"
    launcher_dist = tmp_path / "launcher"
    bundle = tmp_path / "bundle"
    app_dist.mkdir()
    launcher_dist.mkdir()
    (app_dist / "MP2027_Portable.exe").write_bytes(b"app")
    (launcher_dist / "MP2027_Launcher.exe").write_bytes(b"launcher")
    monkeypatch.setattr(package_app, "PROJECT_ROOT", Path.cwd())

    result = package_app.assemble_install_bundle(app_dist, launcher_dist, bundle)

    assert result == bundle
    assert (bundle / "apps" / "0.1.0" / "MP2027_Portable.exe").is_file()
    assert (bundle / "MP2027_Launcher.exe").is_file()
    assert (bundle / "current.json").read_text(encoding="utf-8").startswith('{"entrypoint":"MP2027_Portable.exe"')


def test_assembled_initial_bundle_resolves_through_launcher_contract(tmp_path, monkeypatch):
    app_dist = tmp_path / "app"
    launcher_dist = tmp_path / "launcher"
    bundle = tmp_path / "bundle"
    app_dist.mkdir()
    launcher_dist.mkdir()
    (app_dist / "MP2027_Portable.exe").write_bytes(b"app")
    (launcher_dist / "MP2027_Launcher.exe").write_bytes(b"launcher")
    monkeypatch.setattr(package_app, "PROJECT_ROOT", Path.cwd())

    package_app.assemble_install_bundle(app_dist, launcher_dist, bundle)

    assert resolve_current_entrypoint(bundle) == bundle / "apps" / "0.1.0" / "MP2027_Portable.exe"


def test_inno_installer_uses_complete_vietnamese_messages():
    script = Path("installer/MP2027_Manager.iss").read_text(encoding="utf-8")
    messages = Path("installer/languages/Vietnamese.isl").read_text(encoding="utf-8")
    assignments = {
        line.partition("=")[0]
        for line in messages.splitlines()
        if line and line[0].isalpha() and "=" in line
    }

    assert '[Languages]' in script
    assert 'Name: "vietnamese"; MessagesFile: "languages\\Vietnamese.isl"' in script
    assert "LanguageName=Tiếng Việt" in messages
    assert "Inno Setup version 6.5.0+ Vietnamese messages" in messages
    assert len(assignments) == 296
    assert {
        "DownloadingLabel2",
        "ExtractingLabel",
        "VerificationSignatureInvalid",
        "ConfirmUninstall",
        "UninstalledAll",
    } <= assignments


def test_publish_update_writes_package_then_catalog(tmp_path):
    package = tmp_path / "MP2027_Manager-0.2.0.mpupdate"
    package.write_bytes(b"signed-update")
    target = tmp_path / "published"

    published, catalog = package_app.publish_update(
        package,
        target,
        channel="pilot",
        version="0.2.0",
        notes="Sửa lỗi cập nhật.",
    )

    payload = json.loads(catalog.read_text(encoding="utf-8"))
    assert published.read_bytes() == package.read_bytes()
    assert payload["package"] == package.name
    assert payload["version"] == "0.2.0"
    assert payload["size"] == len(b"signed-update")
    assert payload["sha256"] == package_app._sha256(published)
    assert not list(target.glob("*.part"))
