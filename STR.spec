# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build definition for the STR client/host executable.

Why this file exists instead of a one-line pyinstaller command:

1. pathex MUST include flet_app. flet_app is a package (it has __init__.py),
   so PyInstaller resolves its children as `flet_app.components`. But
   flet_app/main.py imports them bare -- `from components.overlay import ...`
   -- which works from source only because Python puts the script's own
   directory on sys.path. Without flet_app on pathex, seven packages
   (components, views, theme, router, dialogs, i18n, app_state) are silently
   left out of the bundle and the .exe dies on a fresh PC with
   "No module named components".

2. datas must carry the read-only files the app opens at runtime. These are
   found through __file__, which correctly points inside the unpacked bundle,
   so the target folders below have to mirror the source layout:
     database/schema.sql        -> database/   (init_db, migrations)
     database/second_reasons.json -> database/ (migrations)
     flet_app/assets/           -> assets/     (main.py, components/branding.py)

Writable data (config.json, the database, backups) is NOT bundled: it lives
beside the .exe via config.app_base_dir(). See that function for why.

Build with:  pyinstaller STR.spec      (or run build.bat)
"""

a = Analysis(
    ['flet_app/main.py'],
    pathex=['.', 'flet_app'],
    binaries=[],
    datas=[
        ('database/schema.sql', 'database'),
        ('database/second_reasons.json', 'database'),
        ('flet_app/assets', 'assets'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # test suites and their fixtures have no business in a bank's client
        # binary -- they only inflate it and ship scratch code to workstations
        'pytest', 'unittest', 'tkinter',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FIU_System',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    # windowed: no console window behind the app on a user's workstation
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='flet_app/assets/logo.ico',
)
