# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


REQUIRED_RAW_CSVS = (
    'headcount_manual.csv',
    'bus_headcount_manual.csv',
)


def data_tree_without_excel_locks(source, target):
    rows = []
    source_path = Path(source)
    for path in source_path.rglob("*"):
        if not path.is_file():
            continue
        if path.name.startswith("~$"):
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
    ('docs\\MP2027', 'docs\\MP2027'),
    *required_raw_csvs(),
    *data_tree_without_excel_locks('raw', 'raw'),
]


a = Analysis(
    ['src\\universal_app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'cv2',
        'llvmlite',
        'numba',
        'onnxruntime',
        'pyarrow',
        'scipy',
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
    upx=True,
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
    upx=True,
    upx_exclude=[],
    name='MP2027_Portable',
)
