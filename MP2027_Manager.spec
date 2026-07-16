# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src\\universal_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('docs\\MP2027', 'docs\\MP2027'),
        ('raw\\Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx', 'raw'),
    ],
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
    a.binaries,
    a.datas,
    [],
    name='MP2027_Manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\app_icon.ico'],
    hide_console='minimize-late',
)
