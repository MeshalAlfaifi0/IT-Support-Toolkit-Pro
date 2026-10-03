"""
تهيئة قاعدة البيانات — تستدعيها مرة وحدة عند بداية البرنامج.
تنشئ كل الجداول وتحط الإعدادات الافتراضية لو ما موجودة.
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

from src.database.connection import get_connection
from src.database.models import ALL_TABLES, DEFAULT_SETTINGS
from src.utils.logger import setup_logger

log = setup_logger(__name__)


def initialize_database() -> None:
    """
    ينشئ الجداول ويحط الإعدادات الافتراضية.
    آمن تستدعيه أكثر من مرة (IF NOT EXISTS / INSERT OR IGNORE).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # نبني كل الجداول
        for ddl in ALL_TABLES:
            cursor.execute(ddl)

        # نحط الإعدادات الافتراضية — INSERT OR IGNORE عشان ما نكتب فوق إعدادات المستخدم
        for key, value in DEFAULT_SETTINGS:
            cursor.execute(
                "INSERT OR IGNORE INTO settings (setting_key, setting_value) VALUES (?, ?)",
                (key, value),
            )

        conn.commit()
        log.info("Database initialised successfully.")
    except Exception as exc:
        log.error(f"Database initialisation failed: {exc}")
        conn.rollback()
        raise
    finally:
        conn.close()


def get_setting(key: str, default: str = "") -> str:
    """يجيب قيمة إعداد معين من قاعدة البيانات."""
    from src.database.connection import execute_query

    rows = execute_query("SELECT setting_value FROM settings WHERE setting_key = ?", (key,))
    return rows[0]["setting_value"] if rows else default


def save_setting(key: str, value: str) -> None:
    """يحفظ إعداد (يدرج أو يحدّث لو موجود)."""
    from src.database.connection import execute_write

    result = execute_write(
        "INSERT INTO settings (setting_key, setting_value) VALUES (?, ?) "
        "ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value",
        (key, value),
    )
    if result < 0:
        raise RuntimeError("Could not save the application setting")


def log_action(action_name: str, status: str, output: str) -> int:
    """يسجّل عملية في جدول السجلات ويرجع id السجل."""
    from src.database.connection import execute_write

    return execute_write(
        "INSERT INTO actions_log (action_name, status, output) VALUES (?, ?, ?)",
        (action_name, status, output),
    )


def get_action_logs(limit: int = 100) -> list:
    """يجيب آخر سجلات العمليات."""
    from src.database.connection import execute_query

    return execute_query("SELECT * FROM actions_log ORDER BY executed_at DESC LIMIT ?", (limit,))


def get_health_history(limit: int = 50) -> list:
    """يجيب آخر نتائج فحوصات الصحة."""
    from src.database.connection import execute_query

    return execute_query("SELECT * FROM health_checks ORDER BY created_at DESC LIMIT ?", (limit,))


def log_network_change(
    adapter_name: str,
    change_type: str,
    status: str,
    message: str,
    ip_address: str = "",
    subnet_mask: str = "",
    gateway: str = "",
    dns_primary: str = "",
    dns_secondary: str = "",
) -> int:
    """يسجّل تغيير في إعدادات الشبكة."""
    from src.database.connection import execute_write

    return execute_write(
        """INSERT INTO network_settings_logs
           (adapter_name, change_type, ip_address, subnet_mask, gateway,
            dns_primary, dns_secondary, status, message)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            adapter_name,
            change_type,
            ip_address,
            subnet_mask,
            gateway,
            dns_primary,
            dns_secondary,
            status,
            message,
        ),
    )


def log_domain_action(
    action_type: str,
    domain_name: str,
    username: str,
    status: str,
    message: str,
) -> int:
    """يسجّل عملية مجال — كلمة المرور ما تُمرَّر هنا أبداً."""
    from src.database.connection import execute_write

    return execute_write(
        """INSERT INTO domain_actions
           (action_type, domain_name, username, status, message)
           VALUES (?, ?, ?, ?, ?)""",
        (action_type, domain_name, username, status, message),
    )


def log_temp_cleanup(
    deleted_count: int,
    skipped_count: int,
    recovered_bytes: int,
    status: str,
) -> int:
    """يسجّل نتيجة تنظيف الملفات المؤقتة."""
    from src.database.connection import execute_write

    return execute_write(
        """INSERT INTO temp_cleanup_logs
           (deleted_count, skipped_count, recovered_bytes, status)
           VALUES (?, ?, ?, ?)""",
        (deleted_count, skipped_count, recovered_bytes, status),
    )


def get_network_logs(limit: int = 50) -> list:
    """يجيب آخر سجلات تغييرات الشبكة."""
    from src.database.connection import execute_query

    return execute_query(
        "SELECT * FROM network_settings_logs ORDER BY executed_at DESC LIMIT ?",
        (limit,),
    )


def get_domain_logs(limit: int = 50) -> list:
    """يجيب آخر سجلات عمليات المجال."""
    from src.database.connection import execute_query

    return execute_query(
        "SELECT * FROM domain_actions ORDER BY executed_at DESC LIMIT ?",
        (limit,),
    )
