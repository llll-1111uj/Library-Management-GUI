# -*- mode: python ; coding: utf-8 -*-
"""Windows GUI bundle. Build: pyinstaller --noconfirm library.spec"""
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None
root = os.path.abspath(SPECPATH)

datas = [("GUI", "GUI")]
for name in ("logo64.png", "logo.ico"):
    path = os.path.join(root, name)
    if os.path.isfile(path):
        datas.append((path, "."))

binaries = []
hiddenimports = collect_submodules("passlib") + [
    "bcrypt",
    "cffi",
    "fpdf",
    "PyQt5",
    "PyQt5.sip",
    "PyQt5.QtCore",
    "PyQt5.QtGui",
    "PyQt5.QtWidgets",
    "GUIManager",
    "Officer",
    "Person",
    "Book",
    "Costumer",
    "Tools",
    "Password",
    "Lending",
    "Receipt_Bill",
    "GUI.officer_gui",
    "GUI.costumer_gui",
    "GUI.Signin_gui",
    "GUI.Signup_gui",
    "domain",
    "repository",
    "service",
]
tmp_ret = collect_all("PyQt5")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

a = Analysis(
    ["main.py"],
    pathex=[root, os.path.join(root, "Code")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LibraryManagement",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=os.path.join(root, "logo.ico") if os.path.isfile(os.path.join(root, "logo.ico")) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="LibraryManagement",
)
