# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for CallGiant.

Build command:
    pyinstaller CallGiant.spec

Or use the simple one-liner:
    pyinstaller --onefile --noconsole --name CallGiant main.py
"""

import sys
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[("callgiant.ico", ".")],
    hiddenimports=[
        "twilio",
        "twilio.rest",
        "twilio.base",
        "twilio.base.exceptions",
        "pyttsx3",
        "pyttsx3.drivers",
        "pyttsx3.drivers.sapi5",     # Windows SAPI voice driver
        "openpyxl",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "flask",          # webhook.py runs separately on the server
        "gunicorn",
        "pytest",
        "unittest",
    ],
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="CallGiant",
    icon="callgiant.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                    # --noconsole: no terminal window
    disable_windowed_traceback=False, # keep tracebacks for error dialog
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
