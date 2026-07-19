"""Provision an MP2027 update signing key without storing its private half in Git."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.update_security import generate_signing_keypair, resolve_trusted_signing_key

_KEY_ID = re.compile(r"^[A-Za-z0-9._-]+$")


def provision_update_key(
    private_key_output: str | os.PathLike[str],
    *,
    key_id: str,
    release_path: str | os.PathLike[str] = PROJECT_ROOT / "release.json",
) -> tuple[Path, str]:
    """Create a private key outside the repo and add only its public key to release metadata."""
    if not _KEY_ID.fullmatch(str(key_id)):
        raise ValueError("key_id chỉ được chứa chữ, số, dấu chấm, gạch dưới hoặc gạch ngang.")
    output = Path(private_key_output).expanduser().resolve()
    project = PROJECT_ROOT.resolve()
    if output == project or project in output.parents:
        raise ValueError("Khóa ký riêng phải nằm ngoài thư mục dự án/Git.")
    if output.exists():
        raise FileExistsError(f"Không ghi đè khóa ký riêng đã tồn tại: {output}")
    release_file = Path(release_path).resolve()
    metadata = json.loads(release_file.read_text(encoding="utf-8-sig"))
    entries = metadata.get("trusted_signing_keys")
    if not isinstance(entries, list):
        raise ValueError("release.json không có danh sách trusted_signing_keys hợp lệ.")
    if any(isinstance(item, dict) and item.get("id") == key_id for item in entries):
        raise ValueError(f"release.json đã có key_id: {key_id}")
    private_key, public_key = generate_signing_keypair()
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("x", encoding="ascii") as handle:
            handle.write(private_key + "\n")
        try:
            os.chmod(output, 0o600)
        except OSError:
            pass
        updated = dict(metadata)
        updated["trusted_signing_keys"] = [
            *entries,
            {"id": key_id, "public_key": public_key, "purposes": ["application"]},
        ]
        temporary = release_file.with_suffix(release_file.suffix + ".tmp")
        temporary.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, release_file)
        resolve_trusted_signing_key(updated, key_id, purpose="application")
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return output, public_key


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Tạo khóa ký update MP2027 và ghi public key vào release.json.")
    parser.add_argument("--private-key-output", required=True, help="Tệp private key nằm ngoài repo.")
    parser.add_argument("--key-id", required=True, help="Mã khóa production, ví dụ mp2027-prod-2026.")
    parser.add_argument("--release-json", default=str(PROJECT_ROOT / "release.json"))
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    output, public_key = provision_update_key(
        args.private_key_output,
        key_id=args.key_id,
        release_path=args.release_json,
    )
    print(f"Đã lưu PRIVATE key ngoài repo: {output}")
    print("Không gửi, không commit và phải sao lưu tệp private key này.")
    print(f"Public key đã nhúng vào release.json: {public_key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
