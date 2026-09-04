import os
from pathlib import Path
import pytest

from src.services.project_config import ProjectConfig
from src.services.fiscal_run import resolve_uniform_policy_path
from tests.test_fiscal_run_context import _write_minimal_uniform_policy
from scripts.package_app import _validate_dist


def test_resolve_path_strips_quotes(tmp_path):
    project = ProjectConfig.create_legacy_compatible(str(tmp_path), 2027)
    
    target_path = str(tmp_path / 'raw' / 'test.xlsx')
    quoted_abs = f'"{target_path}"'
    resolved = project.resolve_path(quoted_abs)
    assert resolved == str((tmp_path / 'raw' / 'test.xlsx').resolve())
    assert '"' not in resolved

    single_quoted = f"'{target_path}'"
    resolved_single = project.resolve_path(single_quoted)
    assert resolved_single == str((tmp_path / 'raw' / 'test.xlsx').resolve())
    assert "'" not in resolved_single


def test_ensure_fiscal_year_defaults_uniform_policy_when_raw_file_exists(tmp_path):
    raw_dir = tmp_path / 'raw'
    raw_dir.mkdir(parents=True, exist_ok=True)
    policy_file = raw_dir / 'Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx'
    _write_minimal_uniform_policy(policy_file)

    project = ProjectConfig.create_legacy_compatible(str(tmp_path), 2027)
    assert project.data['fiscal_years']['2027']['uniform_policy'] == (
        'raw/Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx'
    )
    paths = project.fiscal_paths(2027)
    assert paths.uniform_policy_path == str(policy_file.resolve())


def test_fiscal_paths_self_heals_dead_absolute_path(tmp_path):
    raw_dir = tmp_path / 'raw'
    raw_dir.mkdir(parents=True, exist_ok=True)
    local_policy = raw_dir / 'Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx'
    _write_minimal_uniform_policy(local_policy)

    project = ProjectConfig.create_legacy_compatible(str(tmp_path), 2027)
    project.data['fiscal_years']['2027']['uniform_policy'] = (
        r'X:\NonExistentDrive\Sandbox\MP2027\raw\Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx'
    )

    paths = project.fiscal_paths(2027)
    assert paths.uniform_policy_path == str(local_policy.resolve())
    assert project.data['fiscal_years']['2027']['uniform_policy'] == (
        'raw/Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx'
    )


def test_resolve_uniform_policy_path_falls_back_when_explicit_path_missing(tmp_path):
    raw_dir = tmp_path / 'raw'
    raw_dir.mkdir(parents=True, exist_ok=True)
    local_policy = raw_dir / 'Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx'
    _write_minimal_uniform_policy(local_policy)

    dead_explicit = r'Z:\DeadPath\raw\Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx'
    resolved = resolve_uniform_policy_path(2027, dead_explicit, base_dir=tmp_path)
    assert resolved == str(local_policy.resolve())


def test_validate_dist_requires_uniform_policy_file(tmp_path):
    dist_root = tmp_path / 'dist'
    internal = dist_root / '_internal'
    internal.mkdir(parents=True, exist_ok=True)
    
    (dist_root / 'MP2027_Portable.exe').touch()
    (internal / 'assets').mkdir()
    (internal / 'assets' / 'app_icon.ico').touch()
    (internal / 'docs' / 'MP2027').mkdir(parents=True)
    (internal / 'docs' / 'MP2027' / 'FORM.xlsx').touch()
    (internal / 'release.json').touch()
    (internal / 'update_sources.default.json').touch()

    with pytest.raises(RuntimeError, match='Cải tiến'):
        _validate_dist(dist_root)

    (internal / 'raw').mkdir()
    (internal / 'raw' / 'Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx').touch()
    _validate_dist(dist_root)
