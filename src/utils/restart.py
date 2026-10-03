"""إعادة تشغيل التطبيق من المصدر أو من EXE مع فصل مجلد استخراج PyInstaller."""

import os
import subprocess
import sys
from pathlib import Path


def restart_request():
    frozen = getattr(sys, "frozen", False)
    command = [sys.executable] + (
        sys.argv[1:] if frozen else [str(Path(__file__).resolve().parents[2] / "app.py")]
    )
    environment = os.environ.copy()
    if frozen:
        # نطلب استخراجًا مستقلاً؛ مجلد _MEIPASS القديم قد يُحذف عند خروج العملية السابقة.
        environment["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return command, environment


def restart_application():
    command, environment = restart_request()
    return subprocess.Popen(
        command, env=environment, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )
