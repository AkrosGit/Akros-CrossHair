from pathlib import Path


project_root = Path(SPECPATH).parent
logo_png = project_root / 'assets' / 'akros_crosshair.png'
logo_ico = project_root / 'assets' / 'akros_crosshair.ico'
datas = [
    (str(project_root / 'crosshairs'), 'crosshairs'),
    (str(logo_png), 'assets'),
]

qt_translations = (
    Path(__import__('PyQt5').__file__).parent
    / 'Qt5'
    / 'translations'
    / 'qtbase_es.qm'
)
if qt_translations.is_file():
    datas.append((str(qt_translations), 'PyQt5/Qt5/translations'))

a = Analysis(
    [str(project_root / 'main.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='AkrosCrossHair',
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
    icon=str(logo_ico),
)
