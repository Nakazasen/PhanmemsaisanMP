"""Cấu hình đường dẫn cấp dự án, độc lập với thư mục cài ứng dụng."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_CONFIG_FILENAME = "project.json"
LAUNCHER_CONFIG_FILENAME = "launcher.json"
PROJECT_CONFIG_VERSION = 1


@dataclass(frozen=True)
class FiscalProjectPaths:
    """Resolved absolute paths used by one fiscal year."""

    fiscal_year: int
    template_path: str
    source_dir: str
    headcount_source_dir: str
    uniform_policy_path: str | None
    manual_input_store: str
    manual_special_inheritance_dir: str | None
    manual_special_legacy_starts: dict[str, int]
    output_dir: str
    history_root: str


class ProjectConfig:
    """Read, resolve and safely update one project.json file."""

    def __init__(self, config_path: str, data: dict[str, Any]):
        self.config_path = os.path.abspath(config_path)
        self.root_dir = os.path.dirname(self.config_path)
        self.data = data
        self.data.setdefault("config_version", PROJECT_CONFIG_VERSION)
        self.data.setdefault("project_name", Path(self.root_dir).name or "Master Plan")
        self.data.setdefault("operational_database", "mp2027.db")
        self.data.setdefault("fiscal_years", {})
        self.data.setdefault("form_confirmations", {})

    @classmethod
    def load(cls, config_path: str) -> "ProjectConfig":
        path = os.path.abspath(config_path)
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError(f"Cấu hình project phải là JSON object: {path}")
        if not isinstance(data.get("fiscal_years", {}), dict):
            raise ValueError("Trường fiscal_years trong project.json phải là object")
        project = cls(path, data)
        project.validate_storage_roles()
        return project

    @classmethod
    def create_legacy_compatible(
        cls, project_root: str, fiscal_year: int = 2027, *, config_path: str | None = None
    ) -> "ProjectConfig":
        """Describe the existing layout without moving or deleting data."""
        root = os.path.abspath(project_root)
        target = os.path.abspath(config_path or os.path.join(root, PROJECT_CONFIG_FILENAME))
        project = cls(target, {
            "config_version": PROJECT_CONFIG_VERSION,
            "project_name": Path(root).name or "Master Plan",
            "operational_database": "mp2027.db",
            "fiscal_years": {},
        })
        project.ensure_fiscal_year(fiscal_year, legacy_root=root)
        return project

    @property
    def operational_database(self) -> str:
        return self.resolve_path(self.data.get("operational_database", "mp2027.db"))

    @staticmethod
    def _same_path(left: str, right: str) -> bool:
        if not left or not right:
            return False
        return os.path.normcase(os.path.abspath(left)) == os.path.normcase(os.path.abspath(right))

    def _manual_store_owner(self, path: str, *, exclude_year: int | None = None) -> int | None:
        for raw_year, entry in self.data.get("fiscal_years", {}).items():
            try:
                year = int(raw_year)
            except (TypeError, ValueError):
                continue
            if exclude_year is not None and year == int(exclude_year):
                continue
            if not isinstance(entry, dict):
                continue
            configured = self.resolve_path(entry.get("manual_input_store"))
            if self._same_path(path, configured):
                return year
        return None

    def set_operational_database(self, path: str) -> None:
        self.update_storage_paths(None, operational_database=path)

    def update_storage_paths(
        self,
        fiscal_year: int | None,
        *,
        operational_database: str | None = None,
        **paths: Any,
    ) -> None:
        """Validate and atomically update shared and annual storage roles."""
        candidate_operational = (
            self.operational_database
            if operational_database is None
            else self.resolve_path(operational_database)
        )
        if not candidate_operational:
            raise ValueError("Đường dẫn CSDL vận hành không được để trống")

        candidate_entry = None
        year = None
        if fiscal_year is not None:
            year = int(fiscal_year)
            self.ensure_fiscal_year(year)
            current_entry = self.data["fiscal_years"][str(year)]
            candidate_entry = dict(current_entry)
            aliases = {
                "template_path": "template", "source_dir": "cost_source_dir",
                "headcount_source_dir": "headcount_source_dir", "uniform_policy_path": "uniform_policy",
                "manual_input_store": "manual_input_store",
                "manual_special_inheritance_dir": "manual_special_inheritance_dir",
                "output_dir": "output_dir", "history_root": "history_root",
            }
            for argument, key in aliases.items():
                if argument in paths:
                    value = paths[argument]
                    candidate_entry[key] = "" if not value else _portable_path(self.resolve_path(value), self.root_dir)
            if "manual_special_legacy_starts" in paths:
                raw_starts = paths["manual_special_legacy_starts"] or {}
                if not isinstance(raw_starts, dict):
                    raise ValueError("Mốc chi phí riêng cũ phải là danh sách theo Trung tâm chi phí")
                normalized_starts: dict[str, int] = {}
                for raw_cc, raw_row in raw_starts.items():
                    cc_code = str(raw_cc or "").strip()
                    try:
                        start_row = int(raw_row)
                    except (TypeError, ValueError) as exc:
                        raise ValueError(f"Dòng bắt đầu chi phí riêng không hợp lệ cho CC {cc_code}") from exc
                    if not cc_code or start_row < 1:
                        raise ValueError(f"Dòng bắt đầu chi phí riêng không hợp lệ cho CC {cc_code}")
                    normalized_starts[cc_code] = start_row
                candidate_entry["manual_special_legacy_starts"] = normalized_starts

            manual_store = self.resolve_path(candidate_entry.get("manual_input_store"))
            if not manual_store:
                raise ValueError(f"Kho nhập tay FY{year} không được để trống")
            owner = self._manual_store_owner(manual_store, exclude_year=year)
            if owner is not None:
                raise ValueError(f"FY{year} và FY{owner} không được dùng chung kho nhập tay: {manual_store}")
            if self._same_path(manual_store, candidate_operational):
                raise ValueError(f"Kho nhập tay FY{year} phải khác CSDL vận hành: {manual_store}")

        for raw_year, entry in self.data.get("fiscal_years", {}).items():
            if year is not None and int(raw_year) == year:
                entry = candidate_entry
            if not isinstance(entry, dict):
                continue
            configured = self.resolve_path(entry.get("manual_input_store"))
            if self._same_path(candidate_operational, configured):
                raise ValueError(
                    f"CSDL vận hành không được trùng kho nhập tay FY{raw_year}: {candidate_operational}"
                )

        self.data["operational_database"] = _portable_path(candidate_operational, self.root_dir)
        if candidate_entry is not None:
            self.data["fiscal_years"][str(year)] = candidate_entry

    def validate_storage_roles(self) -> None:
        """Reject cross-FY manual-store reuse and operational/manual collisions."""
        operational = self.operational_database
        seen: dict[str, int] = {}
        for raw_year, entry in self.data.get("fiscal_years", {}).items():
            try:
                year = int(raw_year)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"FY không hợp lệ trong project.json: {raw_year}") from exc
            if not isinstance(entry, dict):
                raise ValueError(f"Cấu hình FY{year} phải là JSON object")
            manual_store = self.resolve_path(entry.get("manual_input_store"))
            if not manual_store:
                raise ValueError(f"Kho nhập tay FY{year} không được để trống")
            normalized = os.path.normcase(os.path.abspath(manual_store))
            if normalized in seen:
                raise ValueError(f"FY{year} và FY{seen[normalized]} không được dùng chung kho nhập tay: {manual_store}")
            if self._same_path(operational, manual_store):
                raise ValueError(f"CSDL vận hành không được trùng kho nhập tay FY{year}: {manual_store}")
            seen[normalized] = year

    def resolve_path(self, value: object) -> str:
        text = os.path.expandvars(os.path.expanduser(str(value or "").strip()))
        if not text:
            return ""
        if os.path.isabs(text):
            return os.path.abspath(text)
        return os.path.abspath(os.path.join(self.root_dir, text))

    def ensure_fiscal_year(self, fiscal_year: int, *, legacy_root: str | None = None) -> bool:
        year = int(fiscal_year)
        key = str(year)
        fiscal_years = self.data.setdefault("fiscal_years", {})
        if key in fiscal_years:
            return False
        root = os.path.abspath(legacy_root or self.root_dir)
        docs_dir = os.path.join(root, "docs", f"MP{year}")
        raw_dir = os.path.join(root, "raw", f"FY{year}")
        fiscal_years[key] = {
            "template": _portable_path(os.path.join(docs_dir, "FORM.xlsx"), self.root_dir),
            "cost_source_dir": _portable_path(docs_dir, self.root_dir),
            "headcount_source_dir": _portable_path(raw_dir, self.root_dir),
            # An empty value means "auto-discover inside this fiscal project".
            # Do not persist a plausible-looking file that may not exist: any
            # non-empty value is an explicit, fail-closed user selection.
            "uniform_policy": "",
            "manual_input_store": _portable_path(os.path.join(raw_dir, "manual_inputs.db"), self.root_dir),
            "manual_special_inheritance_dir": "",
            "manual_special_legacy_starts": {},
            "output_dir": _portable_path(os.path.join(root, f"OUTPUT_FY{year}"), self.root_dir),
            "history_root": _portable_path(os.path.join(root, "RUN_HISTORY"), self.root_dir),
        }
        return True

    def fiscal_paths(self, fiscal_year: int) -> FiscalProjectPaths:
        year = int(fiscal_year)
        self.ensure_fiscal_year(year)
        entry = self.data["fiscal_years"][str(year)]
        if not isinstance(entry, dict):
            raise ValueError(f"Cấu hình FY{year} phải là JSON object")
        uniform = self.resolve_path(entry.get("uniform_policy"))
        generated_placeholder = os.path.join(
            self.root_dir, "docs", f"MP{year}", "uniform_eligibility.xlsx"
        )
        # Version 1 originally persisted this nonexistent placeholder. Treat
        # only that exact missing path as unset so legacy FY2027 discovery can
        # run; custom explicit paths remain fail-closed even when missing.
        if (
            uniform
            and self._same_path(uniform, generated_placeholder)
            and not os.path.isfile(uniform)
        ):
            uniform = ""
        raw_legacy_starts = entry.get("manual_special_legacy_starts", {})
        if not isinstance(raw_legacy_starts, dict):
            raise ValueError(f"Mốc chi phí riêng cũ FY{year} phải là object")
        legacy_starts: dict[str, int] = {}
        for raw_cc, raw_row in raw_legacy_starts.items():
            cc_code = str(raw_cc or "").strip()
            try:
                start_row = int(raw_row)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Dòng bắt đầu chi phí riêng không hợp lệ cho CC {cc_code}") from exc
            if not cc_code or start_row < 1:
                raise ValueError(f"Dòng bắt đầu chi phí riêng không hợp lệ cho CC {cc_code}")
            legacy_starts[cc_code] = start_row
        return FiscalProjectPaths(
            fiscal_year=year,
            template_path=self.resolve_path(entry.get("template")),
            source_dir=self.resolve_path(entry.get("cost_source_dir")),
            headcount_source_dir=self.resolve_path(entry.get("headcount_source_dir")),
            uniform_policy_path=uniform or None,
            manual_input_store=self.resolve_path(entry.get("manual_input_store")),
            manual_special_inheritance_dir=(
                self.resolve_path(entry.get("manual_special_inheritance_dir")) or None
            ),
            manual_special_legacy_starts=legacy_starts,
            output_dir=self.resolve_path(entry.get("output_dir")),
            history_root=self.resolve_path(entry.get("history_root")),
        )

    def form_confirmations(self, fiscal_year: int) -> dict[str, dict[str, Any]]:
        """Return confirmation records for one FY, keyed by FORM checksum."""
        records = self.data.setdefault("form_confirmations", {}).setdefault(str(int(fiscal_year)), {})
        return records if isinstance(records, dict) else {}

    def confirm_form(self, fiscal_year: int, record: dict[str, Any]) -> None:
        """Remember a user's confirmation for the exact inspected FORM file."""
        checksum = str(record.get("checksum", "")).strip()
        if not checksum:
            raise ValueError("Không thể lưu xác nhận FORM khi chưa có checksum")
        confirmations = self.form_confirmations(fiscal_year)
        confirmations[checksum] = dict(record)

    def update_fiscal_paths(self, fiscal_year: int, **paths: str | None) -> None:
        year = int(fiscal_year)
        self.update_storage_paths(year, **paths)

    def save(self) -> None:
        os.makedirs(self.root_dir, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".project.", suffix=".json.tmp", dir=self.root_dir, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(self.data, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.config_path)
        except Exception:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise


def _portable_path(path: str, project_root: str) -> str:
    absolute = os.path.abspath(path)
    root = os.path.abspath(project_root)
    try:
        relative = os.path.relpath(absolute, root)
    except ValueError:
        return absolute
    if relative == ".":
        return "."
    if relative == ".." or relative.startswith(".." + os.sep):
        return absolute
    return relative.replace(os.sep, "/")


def launcher_config_path(local_app_data: str | None = None) -> str:
    root = local_app_data or os.environ.get("LOCALAPPDATA") or os.path.join(Path.home(), ".mp_manager")
    return os.path.join(os.path.abspath(root), "MPManager", LAUNCHER_CONFIG_FILENAME)


def remember_last_project(config_path: str, *, local_app_data: str | None = None) -> str:
    target = launcher_config_path(local_app_data)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    existing: dict[str, Any] = {}
    try:
        if os.path.isfile(target):
            with open(target, "r", encoding="utf-8") as handle:
                existing = json.load(handle) or {}
    except Exception:
        existing = {}
    existing["last_project_file"] = os.path.abspath(config_path)
    fd, temporary = tempfile.mkstemp(prefix=".launcher.", suffix=".json.tmp", dir=os.path.dirname(target), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(existing, handle, indent=2)
            handle.write("\n")
        os.replace(temporary, target)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return target


def read_last_project(*, local_app_data: str | None = None) -> str | None:
    try:
        with open(launcher_config_path(local_app_data), "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError, TypeError):
        return None
    path = str(payload.get("last_project_file", "") or "").strip()
    return os.path.abspath(path) if path and os.path.isfile(path) else None


def remember_ui_language(language: str, *, local_app_data: str | None = None) -> str:
    target = launcher_config_path(local_app_data)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    existing: dict[str, Any] = {}
    try:
        if os.path.isfile(target):
            with open(target, "r", encoding="utf-8") as handle:
                existing = json.load(handle) or {}
    except Exception:
        existing = {}
    existing["ui_language"] = str(language or "").strip()
    fd, temporary = tempfile.mkstemp(prefix=".launcher.", suffix=".json.tmp", dir=os.path.dirname(target), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(existing, handle, indent=2)
            handle.write("\n")
        os.replace(temporary, target)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return target


def read_ui_language(*, local_app_data: str | None = None) -> str:
    try:
        with open(launcher_config_path(local_app_data), "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError, TypeError):
        return "vi"
    lang = str(payload.get("ui_language", "") or "").strip().lower()
    return lang if lang in ("vi", "ja", "en") else "vi"


def discover_or_create_project(
    app_dir: str, fiscal_year: int = 2027, *, explicit_path: str | None = None,
    local_app_data: str | None = None,
) -> tuple[ProjectConfig, bool]:
    """Load explicit/recent/local project, or save a legacy-compatible project."""
    candidate = explicit_path or os.environ.get("MP_MANAGER_PROJECT")
    if candidate:
        candidate = os.path.abspath(candidate)
        if os.path.isdir(candidate):
            candidate = os.path.join(candidate, PROJECT_CONFIG_FILENAME)
        if not os.path.isfile(candidate):
            raise FileNotFoundError(f"Không tìm thấy project.json: {candidate}")
        project = ProjectConfig.load(candidate)
        remember_last_project(project.config_path, local_app_data=local_app_data)
        return project, False
    recent = read_last_project(local_app_data=local_app_data)
    if recent:
        return ProjectConfig.load(recent), False
    local_config = os.path.join(os.path.abspath(app_dir), PROJECT_CONFIG_FILENAME)
    if os.path.isfile(local_config):
        project = ProjectConfig.load(local_config)
        remember_last_project(project.config_path, local_app_data=local_app_data)
        return project, False
    project = ProjectConfig.create_legacy_compatible(app_dir, fiscal_year, config_path=local_config)
    project.save()
    remember_last_project(project.config_path, local_app_data=local_app_data)
    return project, True
