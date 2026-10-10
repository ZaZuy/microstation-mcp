# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('d:/3. Task/microstation-mcp/src', 'src')]
binaries = []
hiddenimports = [
    'fastmcp', 'mcp', 'anyio', 'win32com.client', 'win32gui', 'win32ui',
    'win32api', 'pythoncom', 'pywintypes', 'winreg', 'PIL', 'PIL.Image',
    'shapely', 'shapely.ops', 'shapely.geometry', 'pyclipper'
]

for pkg in ['fastmcp', 'mcp', 'anyio', 'pydantic', 'shapely', 'pyclipper', 'PIL']:
    try:
        tmp_ret = collect_all(pkg)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception:
        pass

a = Analysis(
    ['d:/3. Task/microstation-mcp/src/main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'tensorflow', 'scipy', 'matplotlib'],
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
    name='Vigela_MCP_Server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['d:/3. Task/microstation-mcp/assets/vigela_icon.ico'],
)
