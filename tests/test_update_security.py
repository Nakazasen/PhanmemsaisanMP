import base64
import zipfile

import pytest

from src.services.update_security import (
    ArtifactVerificationError,
    canonical_json_bytes,
    generate_signing_keypair,
    resolve_trusted_signing_key,
    safe_extract_zip,
    sha256_bytes,
    sign_payload,
    validate_manifest,
    verify_manifest_files,
    verify_payload,
)


def _manifest(root, payload=b"rule"):
    path = root / "rules.json"
    path.write_bytes(payload)
    return {
        "schema": 1,
        "kind": "content",
        "id": "dept-ga",
        "version": "1.0.0",
        "min_app_version": "0.1.0",
        "files": [{"path": "rules.json", "sha256": sha256_bytes(payload), "size": len(payload)}],
    }


def test_ed25519_signature_is_canonical_and_tamper_evident():
    private, public = generate_signing_keypair()
    payload = {"z": 1, "a": "quy tắc"}
    signature = sign_payload(payload, private)
    verify_payload({"a": "quy tắc", "z": 1}, signature, public)
    with pytest.raises(ArtifactVerificationError):
        verify_payload({"a": "changed", "z": 1}, signature, public)
    assert canonical_json_bytes(payload).endswith(b"\n")


def test_manifest_file_hash_and_size_are_verified(tmp_path):
    manifest = _manifest(tmp_path)
    validate_manifest(manifest, artifact_kind="content")
    verify_manifest_files(manifest, tmp_path)
    (tmp_path / "rules.json").write_bytes(b"tampered")
    with pytest.raises(ArtifactVerificationError, match="không khớp"):
        verify_manifest_files(manifest, tmp_path)


def test_unsafe_paths_and_executable_files_are_rejected_for_content_only(tmp_path):
    manifest = _manifest(tmp_path)
    manifest["files"][0]["path"] = "../rules.json"
    with pytest.raises(ArtifactVerificationError, match="không an toàn"):
        validate_manifest(manifest, artifact_kind="content")
    manifest["files"][0]["path"] = "rules.py"
    with pytest.raises(ArtifactVerificationError, match="tệp thực thi"):
        validate_manifest(manifest, artifact_kind="content")

    application_manifest = {
        **manifest,
        "kind": "application",
        "id": "MP2027_Manager",
        "files": [{"path": "MP2027_Portable.exe", "sha256": "0" * 64, "size": 1}],
    }
    validate_manifest(application_manifest, artifact_kind="application")


def test_zip_extraction_rejects_traversal(tmp_path):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("../escape.txt", "no")
    with pytest.raises(ArtifactVerificationError, match="không an toàn"):
        safe_extract_zip(archive, tmp_path / "out")


def _release_metadata(public_key, *, purposes=None):
    return {
        "version": "0.1.0",
        "trusted_signing_keys": [{
            "id": "pilot-2027-01",
            "public_key": public_key,
            "purposes": purposes or ["application"],
        }],
    }


def test_trusted_key_resolver_rejects_unknown_id_and_wrong_purpose():
    _private, public = generate_signing_keypair()
    metadata = _release_metadata(public)
    with pytest.raises(ArtifactVerificationError, match="không nằm trong danh sách tin cậy"):
        resolve_trusted_signing_key(metadata, "unknown-key", purpose="application")
    with pytest.raises(ArtifactVerificationError, match="không nằm trong danh sách tin cậy"):
        resolve_trusted_signing_key(metadata, "pilot-2027-01", purpose="content")


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        ({"id": "pilot-2027-01", "public_key": "unused", "purposes": ["application"], "extra": True}, "các trường không hợp lệ"),
        ({"id": "pilot-2027-01", "public_key": "***", "purposes": ["application"]}, "định dạng Base64"),
        ({
            "id": "pilot-2027-01",
            "public_key": base64.b64encode(b"short").decode("ascii"),
            "purposes": ["application"],
        }, "Ed25519"),
    ],
)
def test_trusted_key_resolver_rejects_malformed_entries(entry, message):
    metadata = {"version": "0.1.0", "trusted_signing_keys": [entry]}
    with pytest.raises(ArtifactVerificationError, match=message):
        resolve_trusted_signing_key(metadata, "pilot-2027-01", purpose="application")


def test_trusted_key_resolver_rejects_duplicate_ids():
    _private, public = generate_signing_keypair()
    entry = _release_metadata(public)["trusted_signing_keys"][0]
    metadata = {"version": "0.1.0", "trusted_signing_keys": [entry, dict(entry)]}
    with pytest.raises(ArtifactVerificationError, match="bị trùng"):
        resolve_trusted_signing_key(metadata, "pilot-2027-01", purpose="application")
