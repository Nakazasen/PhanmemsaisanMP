# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


REQUIRED_RAW_CSVS = (
    'headcount_manual.csv',
    'bus_headcount_manual.csv',
)
EXCLUDED_DIRECTORY_NAMES = {
    '__pycache__',
    '.pytest_cache',
    'RUN_HISTORY',
}
EXCLUDED_SUFFIXES = {
    '.db',
    '.sqlite',
    '.sqlite3',
    '.db-shm',
    '.db-wal',
    '.log',
    '.tmp',
    '.bak',
}


def _is_seed_data(path, source_path):
    relative = path.relative_to(source_path)
    if any(part in EXCLUDED_DIRECTORY_NAMES or part.startswith('OUTPUT_FY') for part in relative.parts):
        return False
    if path.name.startswith('~$') or path.suffix.casefold() in EXCLUDED_SUFFIXES:
        return False
    return True


def data_tree_without_runtime_state(source, target):
    rows = []
    source_path = Path(source)
    for path in source_path.rglob("*"):
        if not path.is_file() or not _is_seed_data(path, source_path):
            continue
        if source_path.name == 'raw' and path.name in REQUIRED_RAW_CSVS:
            continue
        relative_parent = path.parent.relative_to(source_path)
        rows.append((str(path), str(Path(target) / relative_parent)))
    return rows


def required_raw_csvs():
    rows = []
    for filename in REQUIRED_RAW_CSVS:
        path = Path('raw') / filename
        if path.exists():
            rows.append((str(path), 'raw'))
    return rows


datas = [
    ('assets', 'assets'),
    ('release.json', '.'),
    ('update_sources.default.json', '.'),
    *data_tree_without_runtime_state('docs\\MP2027', 'docs\\MP2027'),
    *required_raw_csvs(),
    *data_tree_without_runtime_state('raw', 'raw'),
]


a = Analysis(
    ['packaging\\mp2027_portable_entry.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'aiohttp',
        'boto3',
        'botocore',
        'cv2',
        'llvmlite',
        'matplotlib',
        'numba',
        'onnxruntime',
        'pyarrow',
        'scipy',
        'shiboken2',
        'shiboken6',
        'sqlalchemy',
        'tokenizers',
        'torch',
        'torchvision',
        'transformers',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MP2027_Portable',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\app_icon.ico'],
    hide_console='minimize-late',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='MP2027_Portable',
)
