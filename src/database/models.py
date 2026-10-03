"""
جداول قاعدة البيانات — كل التعديلات على الـ schema تجي هنا.
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

from src.utils.app_paths import EXPORTS_DIR

# ── معلومات الجهاز الأساسية ──────────────────────────────────────────────────
CREATE_DEVICES = """
CREATE TABLE IF NOT EXISTS devices (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    device_name TEXT    NOT NULL,
    username    TEXT,
    os_version  TEXT,
    cpu_name    TEXT,
    ram_total   INTEGER,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# ── نتيجة فحص صحة الجهاز الكامل ────────────────────────────────────────────
CREATE_HEALTH_CHECKS = """
CREATE TABLE IF NOT EXISTS health_checks (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id             INTEGER,
    cpu_usage             REAL,
    ram_usage             REAL,
    disk_usage            REAL,
    antivirus_status      TEXT,
    windows_update_status TEXT,
    network_status        TEXT,
    health_score          INTEGER,
    scan_data             TEXT,   -- بيانات الفحص الكاملة بصيغة JSON
    created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id)
);
"""

# ── سجل العمليات والأتمتة ───────────────────────────────────────────────────
CREATE_ACTIONS_LOG = """
CREATE TABLE IF NOT EXISTS actions_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    action_name TEXT    NOT NULL,
    status      TEXT,
    output      TEXT,
    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# ── التوصيات الناتجة عن كل فحص ─────────────────────────────────────────────
CREATE_RECOMMENDATIONS = """
CREATE TABLE IF NOT EXISTS recommendations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    health_check_id INTEGER,
    category        TEXT,
    recommendation  TEXT,
    priority        TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (health_check_id) REFERENCES health_checks(id)
);
"""

# ── إعدادات البرنامج (مفتاح وقيمة) ─────────────────────────────────────────
CREATE_SETTINGS = """
CREATE TABLE IF NOT EXISTS settings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key   TEXT UNIQUE NOT NULL,
    setting_value TEXT
);
"""

# ── سجل تغييرات إعدادات الشبكة ──────────────────────────────────────────────
CREATE_NETWORK_SETTINGS_LOGS = """
CREATE TABLE IF NOT EXISTS network_settings_logs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    adapter_name TEXT    NOT NULL,
    change_type  TEXT    NOT NULL,  -- 'dhcp' أو 'static'
    ip_address   TEXT,
    subnet_mask  TEXT,
    gateway      TEXT,
    dns_primary  TEXT,
    dns_secondary TEXT,
    status       TEXT,              -- 'Success' أو 'Failed'
    message      TEXT,
    executed_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# ── لقطة الأجهزة المتصلة ────────────────────────────────────────────────────
CREATE_CONNECTED_DEVICES = """
CREATE TABLE IF NOT EXISTS connected_devices (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    device_name   TEXT,
    device_type   TEXT,
    manufacturer  TEXT,
    status        TEXT,
    device_id     TEXT,
    connection    TEXT,
    scanned_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# ── سجل عمليات المجال (بدون كلمات مرور أبداً) ──────────────────────────────
CREATE_DOMAIN_ACTIONS = """
CREATE TABLE IF NOT EXISTS domain_actions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type  TEXT    NOT NULL,  -- 'join_attempt' أو 'info_query'
    domain_name  TEXT,
    username     TEXT,              -- domain\\user (كلمة المرور ما تُخزَّن أبداً)
    status       TEXT,              -- 'Success' أو 'Failed' أو 'Cancelled'
    message      TEXT,              -- مخرجات آمنة فقط
    executed_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# ── نتائج تنظيف الملفات المؤقتة ─────────────────────────────────────────────
CREATE_TEMP_CLEANUP_LOGS = """
CREATE TABLE IF NOT EXISTS temp_cleanup_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    deleted_count   INTEGER DEFAULT 0,
    skipped_count   INTEGER DEFAULT 0,
    recovered_bytes INTEGER DEFAULT 0,
    status          TEXT,
    executed_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# الترتيب مهم عشان الـ foreign keys تشتغل صح
ALL_TABLES = [
    CREATE_DEVICES,
    CREATE_HEALTH_CHECKS,
    CREATE_ACTIONS_LOG,
    CREATE_RECOMMENDATIONS,
    CREATE_SETTINGS,
    CREATE_NETWORK_SETTINGS_LOGS,
    CREATE_CONNECTED_DEVICES,
    CREATE_DOMAIN_ACTIONS,
    CREATE_TEMP_CLEANUP_LOGS,
]

# الإعدادات الافتراضية عند أول تشغيل
DEFAULT_SETTINGS = [
    ("theme", "dark"),
    ("app_version", "1.0.0"),
    ("auto_refresh_seconds", "30"),
    ("export_path", str(EXPORTS_DIR)),
]
