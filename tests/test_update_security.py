import zipfile

import pytest

from src.services.update_security import (
    ArtifactVerificationError,
    canonical_json_bytes,
    safe_extract_zip,
    sha256_bytes,
    validate_manifest,
    verify_manifest_files,
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


def test_manifest_file_hash_and_size_are_verified(tmp_path):
    manifest = _manifest(tmp_path)
    validate_manifest(manifest, artifact_kind="content")
    verify_manifest_files(manifest, tmp_path)
    (tmp_path / "rules.json").write_bytes(b"tampered")
    with pytest.raises(ArtifactVerificationError, match="không khớp"):
        verify_manifest_files(manifest, tmp_path)


def test_manifest_is_canonical_and_rejects_unsafe_content_paths(tmp_path):
    manifest = _manifest(tmp_path)
    assert canonical_json_bytes(manifest).endswith(b"\n")
    manifest["files"][0]["path"] = "../rules.json"
    with pytest.raises(ArtifactVerificationError, match="không an toàn"):
        validate_manifest(manifest, artifact_kind="content")
    manifest["files"][0]["path"] = "rules.py"
    with pytest.raises(ArtifactVerificationError, match="tệp thực thi"):
        validate_manifest(manifest, artifact_kind="content")


def test_zip_extraction_rejects_traversal(tmp_path):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("../escape.txt", "no")
    with pytest.raises(ArtifactVerificationError, match="không an toàn"):
        safe_extract_zip(archive, tmp_path / "out")
