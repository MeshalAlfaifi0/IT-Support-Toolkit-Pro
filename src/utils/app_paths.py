"""تحديد مسارات البيانات الدائمة وترحيل البيانات القديمة دون استبدال بيانات المستخدم."""

import os
import re
import shutil
import sqlite3
import sys
import tempfile
import threading
from contextlib import closing
from pathlib import Path

# اسم مجلد التخزين ثابت حتى يبقى الوصول إلى البيانات بعد تغيير اسم التطبيق.
STORAGE_DIR_NAME = "IT Support Toolkit Pro"
DATA_DIR = Path(
    os.environ.get("IT_TOOLKIT_DATA_DIR")
    or (
        Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / STORAGE_DIR_NAME
    )
)
DATABASE_DIR = DATA_DIR / "database"
LOG_DIR = DATA_DIR / "logs"
EXPORTS_DIR = DATA_DIR / "exports"
DB_FILE = DATABASE_DIR / "app.db"
_lock = threading.Lock()
_prepared = False


def legacy_roots():
    roots = [Path(__file__).resolve().parents[2]]
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        roots = [exe_dir, exe_dir.parent] + roots
    return list(dict.fromkeys(roots))


def prepare_data():
    """Copy legacy data without replacing user data. SQLite backup includes WAL.
    Originals remain untouched; migration errors must not silently lose data.
    """
    global _prepared
    with _lock:
        if _prepared:
            return
        for directory in (DATABASE_DIR, LOG_DIR, EXPORTS_DIR):
            directory.mkdir(parents=True, exist_ok=True)
        roots = legacy_roots()
        if not DB_FILE.exists():
            for root in roots:
                old = root / "database" / "app.db"
                if old.resolve() == DB_FILE.resolve() or not old.is_file():
                    continue
                handle, temporary_name = tempfile.mkstemp(
                    prefix="migration-", suffix=".db", dir=DATABASE_DIR
                )
                os.close(handle)
                temporary = Path(temporary_name)
                try:
                    with closing(sqlite3.connect(old.as_uri() + "?mode=ro", uri=True)) as source:
                        if source.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                            raise sqlite3.DatabaseError("Legacy database failed integrity check")
                        with closing(sqlite3.connect(temporary)) as destination:
                            source.backup(destination)
                    if not DB_FILE.exists():
                        try:
                            temporary.rename(DB_FILE)
                        except FileExistsError:
                            pass  # Another Windows instance completed migration first.
                finally:
                    temporary.unlink(missing_ok=True)
                break
        for root in roots:
            for name, destination in (("exports", EXPORTS_DIR), ("logs", DATA_DIR / "legacy_logs")):
                old = root / name
                if not old.is_dir() or old.resolve() == destination.resolve():
                    continue
                for item in old.rglob("*"):
                    if item.is_file() and not item.is_symlink():
                        target = destination / item.relative_to(old)
                        if not target.exists():
                            target.parent.mkdir(parents=True, exist_ok=True)
                            if name == "logs":
                                content = item.read_text(encoding="utf-8", errors="replace")
                                # Older command logs may contain the full credential script.
                                content = "\n".join(
                                    "[legacy credential command redacted]"
                                    if re.search(r"ConvertTo-SecureString|PSCredential", line, re.I)
                                    else line
                                    for line in content.splitlines()
                                )
                                target.write_text(content, encoding="utf-8")
                            else:
                                shutil.copy2(item, target)
        _prepared = True
