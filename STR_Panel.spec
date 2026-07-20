# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build for the standalone STR Control Panel executable.

Why a second executable rather than a flag on the first: the panel answers "why
isn't this working?", and the app's own login-screen button cannot help when the
app is what won't start. That is not hypothetical -- a packaged client died
before reaching the login screen on the first real rollout.

Same pathex reasoning as STR.spec: flet_app is a package, so its children only
resolve as bare names with flet_app on the path.

Data files: the panel reads config.json and the shared folder, and does not open
the database schema, but the assets are bundled so it shows the same logo.

Build with:  pyinstaller STR_Panel.spec      (build.bat builds both)
"""

a = Analysis(
    ['panel/panel_main.py'],
    pathex=['.', 'flet_app'],
    binaries=[],
    datas=[
        ('flet_app/assets', 'assets'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'unittest', 'tkinter'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FIU_Control_Panel',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='flet_app/assets/logo.ico',
)
