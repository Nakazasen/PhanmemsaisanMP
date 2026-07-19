import json

import pytest

from scripts import provision_update_key
from src.services.update_security import resolve_trusted_signing_key


def _release(path):
    path.write_text(
        json.dumps({"version": "0.1.0", "trusted_signing_keys": []}),
        encoding="utf-8",
    )


def test_provision_update_key_writes_private_outside_repo_and_public_to_release(tmp_path):
    release = tmp_path / "release.json"
    private_key_path = tmp_path / "safe" / "mp2027-prod.key"
    _release(release)

    output, public_key = provision_update_key.provision_update_key(
        private_key_path,
        key_id="mp2027-prod-2026",
        release_path=release,
    )

    metadata = json.loads(release.read_text(encoding="utf-8"))
    assert output == private_key_path
    assert output.read_text(encoding="ascii").strip()
    assert public_key not in output.read_text(encoding="ascii")
    assert resolve_trusted_signing_key(
        metadata, "mp2027-prod-2026", purpose="application"
    )[1] == public_key


def test_provision_update_key_rejects_private_key_inside_repository(tmp_path, monkeypatch):
    release = tmp_path / "release.json"
    _release(release)
    monkeypatch.setattr(provision_update_key, "PROJECT_ROOT", tmp_path)

    with pytest.raises(ValueError, match="ngoài thư mục dự án"):
        provision_update_key.provision_update_key(
            tmp_path / "secret.key",
            key_id="mp2027-prod-2026",
            release_path=release,
        )
