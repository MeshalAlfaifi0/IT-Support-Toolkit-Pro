# -*- mode: python ; coding: utf-8 -*-
"""
مواصفات تجميع IT Operations Console إلى ملف EXE واحد.

Build command:
    pyinstaller IT-Support-Toolkit-Pro.spec

Or use:
    scripts\build_exe.bat
"""

import sys
import os
from pathlib import Path

# SPECPATH يشير إلى مجلد packaging عند البناء من الملف الجديد.
ROOT = Path(SPECPATH)
if ROOT.name == "packaging":
    ROOT = ROOT.parent

# نعزل مسار DLL عن الأدوات الخارجية لتستخدم Qt وPillow مكتباتهما ونظام Windows.
import importlib.util

system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
package_dirs = [
    Path(importlib.util.find_spec(name).origin).parent for name in ("PySide6", "shiboken6")
]
os.environ["PATH"] = os.pathsep.join(
    str(path)
    for path in [
        Path(sys.executable).parent,
        Path(sys.base_prefix),
        Path(sys.base_prefix) / "DLLs",
        *package_dirs,
        system_root / "System32",
        system_root,
    ]
)


# استيرادات Windows المخفية التي قد لا يكتشفها تحليل PyInstaller تلقائيًا.
HIDDEN_IMPORTS = [
    # pywin32
    "win32api",
    "win32con",
    "win32security",
    "win32net",
    "win32netcon",
    "win32print",
    "win32service",
    "win32serviceutil",
    "pywintypes",
    "winerror",
    # wmi
    "wmi",
    # PySide6 plugins sometimes missed
    "PySide6.QtXml",
    "PySide6.QtPrintSupport",
    # reportlab
    "reportlab.graphics.barcode",
    "reportlab.graphics.barcode.code128",
    "reportlab.platypus",
    "reportlab.lib.styles",
    "reportlab.lib.pagesizes",
    "reportlab.lib.colors",
    # openpyxl
    "openpyxl.styles.builtins",
    # standard library modules sometimes missed
    "socket",
    "ipaddress",
    "tempfile",
    "shutil",
    "subprocess",
    "sqlite3",
    "csv",
    "json",
    "datetime",
    "pathlib",
    "ctypes",
    "ctypes.wintypes",
    # src packages (explicit safety net)
    "src",
    "src.core",
    "src.database",
    "src.ui",
    "src.utils",
    "src.reports",
]

# ملفات الموارد؛ كل زوج يحدد الملف الأصلي ومجلده داخل الحزمة.
DATAS = [
    # كتالوجات الترجمة مطلوبة لعناصر الواجهة المترجمة.
    (str(ROOT / "src" / "utils" / "ui_translations.json"), "src/utils"),
    (str(ROOT / "src" / "utils" / "ui_translations_ar.json"), "src/utils"),
]

a = Analysis(
    [str(ROOT / "app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=DATAS,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # استثناء مكتبات لا يستخدمها التطبيق لتقليل حجم البناء
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "tkinter",
        "wx",
        "gtk",
        "pytest",
        "unittest",
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=os.environ.get("IT_TOOLKIT_BUILD_NAME", "IT-Operations-Console"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # compress with UPX if available
    upx_exclude=[
        "vcruntime140.dll",
        "python3*.dll",
        "Qt6Core.dll",
        "Qt6Gui.dll",
        "Qt6Widgets.dll",
    ],
    runtime_tmpdir=None,
    console=False,  # no black console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=False,  # privileged actions require running as administrator
    icon=None,  # replace with path to .ico file if available
    version=None,
    onefile=True,  # single .exe output
)
