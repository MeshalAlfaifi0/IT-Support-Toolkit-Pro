"""
إدارة الاتصال بقاعدة البيانات SQLite.
ملف واحد مشترك مع WAL mode عشان ما يصير تعارض في القراءة والكتابة.
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

import os
import sqlite3

from src.utils.app_paths import DB_FILE, prepare_data
from src.utils.logger import setup_logger

log = setup_logger(__name__)

# المسار الكامل لملف قاعدة البيانات

DB_PATH = str(DB_FILE)


def get_connection() -> sqlite3.Connection:
    """
    يفتح (أو ينشئ) قاعدة البيانات ويرجع اتصال.
    row_factory = sqlite3.Row عشان نوصل للأعمدة باسمها.
    """
    try:
        prepare_data()
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # WAL يخلي القراءة والكتابة تصير بنفس الوقت بدون تعارض
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn
    except sqlite3.Error as exc:
        log.error(f"Cannot open database at {DB_PATH}: {exc}")
        raise


def execute_query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    """
    ينفّذ استعلام SELECT ويرجع كل النتائج.
    يرجع قائمة فارغة لو صار خطأ.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()
    except sqlite3.Error as exc:
        log.error(f"Query failed: {exc}\nSQL: {sql}")
        return []
    finally:
        conn.close()


def execute_write(sql: str, params: tuple = ()) -> int:
    """
    ينفّذ INSERT أو UPDATE أو DELETE.
    يرجع lastrowid للإدراج، أو rowcount للتحديث والحذف.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid or cursor.rowcount
    except sqlite3.Error as exc:
        log.error(f"Write failed: {exc}\nSQL: {sql}")
        conn.rollback()
        return -1
    finally:
        conn.close()


def execute_many(sql: str, data: list[tuple]) -> bool:
    """
    يدرج عدة صفوف دفعة وحدة (bulk insert).
    يرجع True لو نجح.
    """
    if not data:
        return True
    conn = get_connection()
    try:
        conn.executemany(sql, data)
        conn.commit()
        return True
    except sqlite3.Error as exc:
        log.error(f"Bulk write failed: {exc}\nSQL: {sql}")
        conn.rollback()
        return False
    finally:
        conn.close()
