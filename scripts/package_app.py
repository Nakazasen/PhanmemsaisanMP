"""Đóng gói, kiểm tra nhanh và công bố các tệp MP2027 Manager cho Windows.

Luồng thường dựng ứng dụng onedir và trình khởi chạy, ghép bộ cài theo phiên
bản rồi kiểm tra sức khỏe. Tùy chọn ``--build-update`` tạo gói ``.mpupdate``
được kiểm tra mã băm và công bố danh mục nguyên tử vào thư mục mạng đã cấu
hình; không yêu cầu thông tin xác thực ký.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from hashlib import sha256
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.cli import VietnameseArgumentParser

APP_SPEC_PATH = PROJECT_ROOT / "MP2027_Portable.spec"
LAUNCHER_SPEC_PATH = PROJECT_ROOT / "MP2027_Manager.spec"
DIST_ROOT = PROJECT_ROOT / "dist" / "MP2027_Portable"
LAUNCHER_DIST_ROOT = PROJECT_ROOT / "dist" / "MP2027_Launcher"
INSTALL_BUNDLE_ROOT = PROJECT_ROOT / "release_artifacts" / "install_bundle"


def _validate_dist(dist_root: str | os.PathLike[str]) -> None:
    root = Path(dist_root)
    required = [
        root / "MP2027_Portable.exe",
        root / "_internal" / "assets" / "app_icon.ico",
        root / "_internal" / "docs" / "MP2027" / "FORM.xlsx",
        root / "_internal" / "raw" / "Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx",
        root / "_internal" / "release.json",
        root / "_internal" / "update_sources.default.json",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        formatted = "\n  - ".join(missing)
        raise RuntimeError(f"Bản đóng gói thiếu tài nguyên bắt buộc:\n  - {formatted}")


def smoke_packaged_health(dist_root: str | os.PathLike[str] = DIST_ROOT) -> None:
    """Run a non-destructive executable check in isolated per-user data."""
    root = Path(dist_root)
    executable = root / "MP2027_Portable.exe"
    if not executable.is_file():
        raise FileNotFoundError(f"Không tìm thấy tệp chạy để kiểm tra: {executable}")
    smoke_root = PROJECT_ROOT / "build" / "packaged-health-smoke"
    env = os.environ.copy()
    env["LOCALAPPDATA"] = str(smoke_root)
    env.pop("MP_MANAGER_PORTABLE_MODE", None)
    subprocess.run(
        [str(executable), "--health-check"],
        check=True,
        cwd=str(root),
        env=env,
        timeout=180,
    )


def smoke_launcher_health(bundle_root: str | os.PathLike[str] = INSTALL_BUNDLE_ROOT) -> None:
    """Verify the stable launcher resolves and health-checks the active version."""
    root = Path(bundle_root)
    executable = root / "MP2027_Launcher.exe"
    if not executable.is_file():
        raise FileNotFoundError(f"Không tìm thấy launcher để kiểm tra: {executable}")
    smoke_root = PROJECT_ROOT / "build" / "launcher-health-smoke"
    env = os.environ.copy()
    env["LOCALAPPDATA"] = str(smoke_root)
    env.pop("MP_MANAGER_PORTABLE_MODE", None)
    subprocess.run(
        [str(executable), "--health-check"],
        check=True,
        cwd=str(root),
        env=env,
        timeout=180,
    )


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


_UPDATE_RESERVED_NAMES = {"manifest.json"}
_UPDATE_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def _update_zip_info(relative_path: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(relative_path, date_time=_UPDATE_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def _read_external_private_key(private_key_path: str | os.PathLike[str]) -> str:
    path = Path(private_key_path).expanduser().resolve()
    project = PROJECT_ROOT.resolve()
    if path == project or project in path.parents:
        raise ValueError("Khóa ký riêng phải nằm ngoài thư mục dự án/Git.")
    try:
        value = path.read_text(encoding="ascii").strip()
    except OSError as exc:
        raise ValueError(f"Không đọc được tệp khóa ký riêng: {path}") from exc
    if not value:
        raise ValueError("Tệp khóa ký riêng đang trống.")
    return value


def _application_inventory(app_dist: str | os.PathLike[str]) -> list[dict[str, object]]:
    root = Path(app_dist).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Không tìm thấy thư mục ứng dụng đã đóng gói: {root}")
    files = sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    if not files:
        raise ValueError(f"Thư mục ứng dụng đóng gói đang trống: {root}")
    inventory: list[dict[str, object]] = []
    total_size = 0
    for path in files:
        if path.is_symlink():
            raise ValueError(f"Không cho phép symbolic link trong bản cập nhật: {path}")
        resolved = path.resolve()
        if root not in resolved.parents:
            raise ValueError(f"Tệp cập nhật thoát khỏi thư mục ứng dụng: {path}")
        relative = path.relative_to(root).as_posix()
        if relative in _UPDATE_RESERVED_NAMES:
            raise ValueError(f"Tên tệp dành riêng không được có trong app dist: {relative}")
        size = path.stat().st_size
        total_size += size
        inventory.append({"path": relative, "sha256": _sha256(path), "size": size})
    # Keep the extracted package within the verifier's global artifact budget.
    from src.services.update_security import MAX_ARTIFACT_BYTES

    if total_size > MAX_ARTIFACT_BYTES:
        raise ValueError(
            f"Bản cập nhật có tổng kích thước {total_size:,} byte, vượt giới hạn "
            f"{MAX_ARTIFACT_BYTES:,} byte."
        )
    return inventory


def build_hash_checked_update(
    app_dist: str | os.PathLike[str],
    output_path: str | os.PathLike[str],
    *,
    min_app_version: str,
    release_path: str | os.PathLike[str] = PROJECT_ROOT / "release.json",
    database_schema: int | None = None,
) -> Path:
    """Build a reproducible hash-checked update from an already validated onedir app.

    Application packages are intentionally unsigned. The controlled company
    update folder is the trust boundary; catalog and manifest SHA-256 values
    detect incomplete or corrupted files before activation.
    """
    from src.db.migrations import CURRENT_SCHEMA_VERSION
    from src.services.update_security import (
        MAX_ARTIFACT_BYTES,
        MAX_MANIFEST_BYTES,
        canonical_json_bytes,
    )

    release = json.loads(Path(release_path).read_text(encoding="utf-8-sig"))
    version = str(release.get("version", ""))
    if not _SEMVER.fullmatch(version) or not _SEMVER.fullmatch(str(min_app_version)):
        raise ValueError("Phiên bản release và min_app_version phải có dạng x.y.z.")
    schema = CURRENT_SCHEMA_VERSION if database_schema is None else database_schema
    if not isinstance(schema, int) or isinstance(schema, bool) or schema < 1:
        raise ValueError("database_schema phải là số nguyên dương.")

    root = Path(app_dist).resolve()
    output = Path(output_path).resolve()
    if output.suffix.casefold() != ".mpupdate":
        raise ValueError("Tệp đầu ra cập nhật phải có đuôi .mpupdate.")
    if output == root or root in output.parents:
        raise ValueError("Tệp .mpupdate phải nằm ngoài thư mục app dist.")
    inventory = _application_inventory(root)
    entrypoint = "MP2027_Portable.exe"
    if entrypoint not in {str(item["path"]) for item in inventory}:
        raise FileNotFoundError(f"App dist thiếu entrypoint bắt buộc: {entrypoint}")
    manifest = {
        "schema": 1,
        "kind": "application",
        "id": "MP2027_Manager",
        "version": version,
        "min_app_version": str(min_app_version),
        "database_schema": schema,
        "health_check": "--health-check",
        "entrypoint": entrypoint,
        "files": inventory,
    }
    manifest_bytes = canonical_json_bytes(manifest)
    if len(manifest_bytes) > MAX_MANIFEST_BYTES:
        raise ValueError(
            f"Tệp kê khai cập nhật có kích thước {len(manifest_bytes):,} byte, vượt giới hạn "
            f"{MAX_MANIFEST_BYTES:,} byte. Hãy giảm số lượng tệp hoặc tăng giới hạn dùng chung trước khi phát hành."
        )
    extracted_size = sum(int(entry["size"]) for entry in inventory) + len(manifest_bytes)
    if extracted_size > MAX_ARTIFACT_BYTES:
        raise ValueError(
            f"Bản cập nhật có tổng kích thước giải nén {extracted_size:,} byte, vượt giới hạn "
            f"{MAX_ARTIFACT_BYTES:,} byte."
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        with zipfile.ZipFile(temporary, "w", allowZip64=True) as archive:
            archive.writestr(_update_zip_info("manifest.json"), manifest_bytes)
            for entry in inventory:
                relative = str(entry["path"])
                source = root / Path(relative)
                with source.open("rb") as input_file, archive.open(
                    _update_zip_info(relative), "w", force_zip64=True
                ) as output_file:
                    shutil.copyfileobj(input_file, output_file, length=1024 * 1024)
        os.replace(temporary, output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return output


def publish_update(
    package_path: str | os.PathLike[str],
    publish_dir: str | os.PathLike[str],
    *,
    channel: str,
    version: str,
    notes: str = "",
) -> tuple[Path, Path]:
    """Publish package first and latest.json last so clients never see a partial release."""
    package = Path(package_path).resolve()
    target_dir = Path(publish_dir).expanduser().resolve()
    if not package.is_file() or package.suffix.casefold() != ".mpupdate":
        raise ValueError("Không tìm thấy gói .mpupdate hợp lệ để phát hành.")
    if not _SEMVER.fullmatch(str(version)):
        raise ValueError("Phiên bản phát hành phải có dạng x.y.z.")
    if not isinstance(channel, str) or not channel.strip() or len(channel) > 64:
        raise ValueError("Kênh phát hành không hợp lệ.")
    if not isinstance(notes, str) or len(notes) > 2000:
        raise ValueError("Ghi chú phát hành không hợp lệ hoặc quá dài.")
    target_dir.mkdir(parents=True, exist_ok=True)
    published_package = target_dir / package.name
    package_part = target_dir / f"{package.name}.part"
    catalog = target_dir / "latest.json"
    catalog_part = target_dir / "latest.json.part"
    package_part.unlink(missing_ok=True)
    catalog_part.unlink(missing_ok=True)
    try:
        shutil.copyfile(package, package_part)
        if _sha256(package_part) != _sha256(package):
            raise RuntimeError("SHA-256 của gói sau khi copy không khớp.")
        os.replace(package_part, published_package)
        payload = {
            "schema": 1,
            "channel": channel.strip(),
            "version": str(version),
            "package": published_package.name,
            "sha256": _sha256(published_package),
            "size": published_package.stat().st_size,
            "notes": notes,
        }
        catalog_part.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(catalog_part, catalog)
    except Exception:
        package_part.unlink(missing_ok=True)
        catalog_part.unlink(missing_ok=True)
        raise
    return published_package, catalog


def assemble_install_bundle(
    app_dist: Path = DIST_ROOT,
    launcher_dist: Path = LAUNCHER_DIST_ROOT,
    bundle_root: Path = INSTALL_BUNDLE_ROOT,
) -> Path:
    release = json.loads((PROJECT_ROOT / "release.json").read_text(encoding="utf-8-sig"))
    version = str(release["version"])
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    version_dir = bundle_root / "apps" / version
    shutil.copytree(app_dist, version_dir)
    for item in launcher_dist.iterdir():
        destination = bundle_root / item.name
        if item.is_dir():
            shutil.copytree(item, destination)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, destination)
    manifest = {
        "schema": 1,
        "kind": "initial-install",
        "version": version,
        "entrypoint": "MP2027_Portable.exe",
        "release_channel": release["channel"],
    }
    manifest_path = version_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    current = {
        "schema": 1,
        "version": version,
        "entrypoint": manifest["entrypoint"],
        "manifest_sha256": _sha256(manifest_path),
    }
    (bundle_root / "current.json").write_text(
        json.dumps(current, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    return bundle_root


def _build(spec_path: Path) -> None:
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", str(spec_path)],
        check=True,
        cwd=str(PROJECT_ROOT),
    )


def package() -> None:
    print("Bắt đầu đóng gói MP2027 Manager dạng thư mục...")
    for spec_path in (APP_SPEC_PATH, LAUNCHER_SPEC_PATH):
        if not spec_path.is_file():
            raise FileNotFoundError(f"Không tìm thấy spec chuẩn: {spec_path}")
    try:
        _build(APP_SPEC_PATH)
        _validate_dist(DIST_ROOT)
        smoke_packaged_health(DIST_ROOT)
        _build(LAUNCHER_SPEC_PATH)
        bundle = assemble_install_bundle()
        smoke_launcher_health(bundle)
        print("\nTHÀNH CÔNG! Đã đóng gói app, launcher và kiểm tra sức khỏe xuyên suốt.")
        print(f"Bộ cài nguồn nằm tại: {bundle}")
        print("Dữ liệu người dùng sẽ được giữ ngoài Program Files trong LocalAppData.")
    except subprocess.CalledProcessError as exc:
        print(f"\nLỗi khi đóng gói: {exc}")
        raise SystemExit(1) from exc


def _parse_args(argv=None):
    parser = VietnameseArgumentParser(description="Đóng gói MP2027 Manager hoặc tạo bản cập nhật kiểm tra hash.")
    parser.add_argument("--build-update", action="store_true", help="Tạo .mpupdate từ dist onedir hiện có.")
    parser.add_argument("--min-app-version", help="Phiên bản cũ nhất được phép cập nhật.")
    parser.add_argument("--update-output", help="Đường dẫn .mpupdate đầu ra.")
    parser.add_argument("--publish-dir", help="Thư mục LAN/web-root nhận package và latest.json.")
    parser.add_argument("--release-notes", default="", help="Ghi chú ngắn đưa vào latest.json.")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    if not args.build_update:
        package()
        return 0
    if not args.min_app_version:
        raise SystemExit("Thiếu tham số tạo update: --min-app-version")
    release = json.loads((PROJECT_ROOT / "release.json").read_text(encoding="utf-8-sig"))
    output = Path(args.update_output) if args.update_output else (
        PROJECT_ROOT / "release_artifacts" / f"MP2027_Manager-{release['version']}.mpupdate"
    )
    artifact = build_hash_checked_update(
        DIST_ROOT,
        output,
        min_app_version=args.min_app_version,
    )
    print(f"Đã tạo bản cập nhật kiểm tra hash: {artifact}")
    if args.publish_dir:
        published, catalog = publish_update(
            artifact,
            args.publish_dir,
            channel=str(release["channel"]),
            version=str(release["version"]),
            notes=args.release_notes,
        )
        print(f"Đã phát hành gói nguyên tử: {published}")
        print(f"Đã cập nhật catalog sau cùng: {catalog}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
