import json
import zipfile
from pathlib import Path

import pytest

from src.services import update_delivery
from src.services.update_security import (
    canonical_json_bytes,
    sha256_bytes,
)


def _config(*, sources, startup_check=True):
    return {"schema": 1, "startup_check": startup_check, "sources": sources}


def _write_config(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_release(path: Path, _unused_value: str = ""):
    path.write_text(
        json.dumps(
            {
                "version": "0.1.0",
            }
        ),
        encoding="utf-8",
    )


def _legacy_values() -> tuple[str, str]:
    return "unused", "unused"


def _build_update(path: Path, _unused_private_key: str, *, version: str):
    payload = f"portable-{version}".encode("ascii")
    manifest = {
        "schema": 1,
        "kind": "application",
        "id": "MP2027_Manager",
        "version": version,
        "min_app_version": "0.1.0",
        "database_schema": 1,
        "health_check": "--health-check",
        "entrypoint": "MP2027_Portable.exe",
        "files": [
            {
                "path": "MP2027_Portable.exe",
                "sha256": sha256_bytes(payload),
                "size": len(payload),
            }
        ],
    }
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("manifest.json", canonical_json_bytes(manifest))
        archive.writestr("MP2027_Portable.exe", payload)


def test_load_update_config_prefers_user_then_company_policy(tmp_path):
    default = tmp_path / "default.json"
    runtime = tmp_path / "runtime"
    program_data = tmp_path / "program-data"
    _write_config(default, _config(sources=[]))
    _write_config(
        runtime / "update_sources.json",
        _config(sources=[{"type": "folder", "location": r"\\user\updates", "enabled": True}]),
    )
    _write_config(
        program_data / "MPManager" / "update_sources.json",
        _config(
            startup_check=False,
            sources=[{"type": "https", "location": "https://updates.example.test/mp2027", "enabled": True}],
        ),
    )

    config = update_delivery.load_update_config(
        runtime,
        default_path=default,
        program_data=program_data,
    )

    assert config["startup_check"] is False
    assert config["sources"] == [
        {"type": "https", "location": "https://updates.example.test/mp2027", "enabled": True}
    ]


def test_folder_discovery_ignores_partial_invalid_and_selects_newest(tmp_path):
    private_key, public_key = _legacy_values()
    release = tmp_path / "release.json"
    updates = tmp_path / "updates"
    updates.mkdir()
    _write_release(release, public_key)
    _build_update(updates / "MP2027_Manager-0.2.0.mpupdate", private_key, version="0.2.0")
    newest = updates / "MP2027_Manager-0.3.0.mpupdate"
    _build_update(newest, private_key, version="0.3.0")
    (updates / "uploading.mpupdate.part").write_bytes(b"incomplete")
    (updates / "broken.mpupdate").write_bytes(b"not a zip")

    candidate = update_delivery.discover_available_update(
        [{"type": "folder", "location": str(updates), "enabled": True}],
        current_version="0.1.0",
        current_database_schema=1,
        release_metadata_path_override=release,
    )

    assert candidate is not None
    assert candidate.version == "0.3.0"
    assert candidate.location == str(newest)


def test_folder_catalog_supplies_release_notes_and_verifies_its_package(tmp_path):
    private_key, public_key = _legacy_values()
    release = tmp_path / "release.json"
    updates = tmp_path / "updates"
    updates.mkdir()
    _write_release(release, public_key)
    package = updates / "MP2027_Manager-0.3.0.mpupdate"
    _build_update(package, private_key, version="0.3.0")
    updates.joinpath("latest.json").write_text(json.dumps({
        "schema": 1,
        "channel": "pilot",
        "version": "0.3.0",
        "package": package.name,
        "sha256": sha256_bytes(package.read_bytes()),
        "size": package.stat().st_size,
        "notes": "• Sửa lỗi\n• Cải thiện trải nghiệm",
    }), encoding="utf-8")

    candidate = update_delivery.discover_available_update(
        [{"type": "folder", "location": str(updates), "enabled": True}],
        current_version="0.1.0",
        current_database_schema=1,
        release_metadata_path_override=release,
    )

    assert candidate is not None
    assert candidate.version == "0.3.0"
    assert candidate.notes == "• Sửa lỗi\n• Cải thiện trải nghiệm"
    assert candidate.sha256 == sha256_bytes(package.read_bytes())


def test_manifest_identity_allows_the_same_size_as_application_inspection(tmp_path):
    package = tmp_path / "large-manifest.mpupdate"
    manifest = {
        "version": "0.2.0",
        "padding": "x" * (update_delivery.MAX_CATALOG_BYTES + 1),
    }
    manifest_bytes = json.dumps(manifest).encode("utf-8")
    assert len(manifest_bytes) <= update_delivery.MAX_UPDATE_MANIFEST_BYTES

    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("manifest.json", manifest_bytes)

    assert update_delivery._manifest_identity(package) == "0.2.0"


def test_update_manifest_limit_is_shared_with_package_security():
    from src.services.update_security import MAX_MANIFEST_BYTES

    assert update_delivery.MAX_UPDATE_MANIFEST_BYTES == MAX_MANIFEST_BYTES == 1024 * 1024


def test_fetch_folder_candidate_uses_atomic_local_cache(tmp_path):
    source = tmp_path / "release.mpupdate"
    source.write_bytes(b"signed-package-placeholder")
    candidate = update_delivery.UpdateCandidate(
        version="0.2.0",
        source_type="folder",
        location=str(source),
        package_name=source.name,
        size=source.stat().st_size,
    )

    cached = update_delivery.fetch_update_candidate(candidate, tmp_path / "runtime")

    assert cached.read_bytes() == source.read_bytes()
    assert cached.parent.name == "downloads"
    assert not list(cached.parent.glob("*.tmp"))


def test_https_catalog_requires_valid_fields_and_newer_version(monkeypatch):
    catalog = {
        "schema": 1,
        "channel": "pilot",
        "version": "0.2.0",
        "package": "MP2027_Manager-0.2.0.mpupdate",
        "sha256": "a" * 64,
        "size": 42,
        "notes": "Sửa lỗi",
    }
    monkeypatch.setattr(update_delivery, "_read_https_json", lambda *_args, **_kwargs: catalog)

    candidate = update_delivery.discover_https_update(
        "https://updates.example.test/mp2027",
        current_version="0.1.0",
    )
    assert candidate is not None
    assert candidate.location.endswith("MP2027_Manager-0.2.0.mpupdate")
    assert update_delivery.discover_https_update(
        "https://updates.example.test/mp2027",
        current_version="0.2.0",
    ) is None

    catalog["package"] = "../unsafe.mpupdate"
    with pytest.raises(update_delivery.UpdateDeliveryError, match="không an toàn"):
        update_delivery.discover_https_update(
            "https://updates.example.test/mp2027",
            current_version="0.1.0",
        )


def test_unavailable_source_does_not_hide_valid_source(tmp_path):
    private_key, public_key = _legacy_values()
    release = tmp_path / "release.json"
    updates = tmp_path / "updates"
    updates.mkdir()
    _write_release(release, public_key)
    _build_update(updates / "release.mpupdate", private_key, version="0.2.0")

    candidate = update_delivery.discover_available_update(
        [
            {"type": "folder", "location": str(tmp_path / "missing"), "enabled": True},
            {"type": "folder", "location": str(updates), "enabled": True},
        ],
        current_version="0.1.0",
        current_database_schema=1,
        release_metadata_path_override=release,
    )

    assert candidate is not None
    assert candidate.version == "0.2.0"
