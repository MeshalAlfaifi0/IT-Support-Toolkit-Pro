"""
نظام الترجمة — عربي وإنجليزي.
استدعي set_lang() مرة وحدة عند بداية البرنامج، وبعدين استخدم tr() في كل مكان.
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

from __future__ import annotations

# اللغة الحالية — تتغير عن طريق set_lang()
_current: str = "ar"

# ── جدول الترجمات ────────────────────────────────────────────────────────────
_T: dict[str, dict[str, str]] = {
    # ── أزرار الشريط الجانبي ───────────────────────────────────────────────
    "nav_dashboard": {"ar": "لوحة التحكم", "en": "Dashboard"},
    "nav_device_info": {"ar": "معلومات الجهاز", "en": "Device Info"},
    "nav_drivers": {"ar": "تشخيص التعريفات", "en": "Driver Diagnostics"},
    "nav_health": {"ar": "فحص صحة الجهاز", "en": "Health Check"},
    "nav_network": {"ar": "الشبكة و IP", "en": "Network & IP"},
    "nav_devices": {"ar": "الأجهزة المتصلة", "en": "Connected Devices"},
    "nav_printers": {"ar": "الطابعات والماسحات", "en": "Printers & Scanners"},
    "nav_maintenance": {"ar": "مركز الصيانة", "en": "Maintenance Center"},
    "nav_domain": {"ar": "المجال والدومين", "en": "Domain & Workgroup"},
    "nav_cybersecurity": {"ar": "الأمن السيبراني", "en": "Cybersecurity"},
    "nav_cmd": {"ar": "أوامر CMD", "en": "CMD Commands"},
    "nav_history": {"ar": "السجل", "en": "History"},
    "nav_settings": {"ar": "الإعدادات", "en": "Settings"},
    # ── رأس البرنامج ───────────────────────────────────────────────────────
    "app_subtitle": {"ar": "أدوات دعم IT", "en": "IT Support Tools"},
    # ── شريط الحالة في الأسفل ──────────────────────────────────────────────
    "status_admin": {"ar": "🔑 يعمل كمسؤول", "en": "🔑 Running as Admin"},
    "status_no_admin": {"ar": "⚠ لا يعمل كمسؤول", "en": "⚠ Not Admin"},
    "status_ready_admin": {
        "ar": "جاهز  |  وضع المسؤول مفعّل",
        "en": "Ready  |  Administrator mode active",
    },
    "status_ready_no_admin": {
        "ar": "جاهز  |  بعض الميزات تتطلب صلاحيات مسؤول",
        "en": "Ready  |  Some features require Administrator",
    },
    # ── لوحة التحكم ────────────────────────────────────────────────────────
    "dashboard_title": {"ar": "لوحة التحكم", "en": "Dashboard"},
    "refresh": {"ar": "↻  تحديث", "en": "↻  Refresh"},
    "loading": {"ar": "جارٍ تحميل معلومات الجهاز…", "en": "Loading device info…"},
    "last_update": {"ar": "آخر تحديث:", "en": "Last update:"},
    "load_failed": {"ar": "⚠ تعذّر تحميل معلومات الجهاز.", "en": "⚠ Failed to load device info."},
    # عناوين بطاقات لوحة التحكم
    "card_device_name": {"ar": "اسم الجهاز", "en": "Device Name"},
    "card_user": {"ar": "المستخدم الحالي", "en": "Current User"},
    "card_os": {"ar": "نظام التشغيل", "en": "Operating System"},
    "card_manufacturer": {"ar": "الشركة المصنّعة / الموديل", "en": "Manufacturer / Model"},
    "card_cpu_name": {"ar": "المعالج (CPU)", "en": "Processor (CPU)"},
    "card_cpu_use": {"ar": "استخدام المعالج", "en": "CPU Usage"},
    "card_ram_total": {"ar": "إجمالي الذاكرة RAM", "en": "Total RAM"},
    "card_ram_use": {"ar": "استخدام الذاكرة", "en": "RAM Usage"},
    "card_disk": {"ar": "مساحة C المتبقية", "en": "C: Free Space"},
    "card_network": {"ar": "حالة الشبكة", "en": "Network Status"},
    "card_ip": {"ar": "عنوان IP", "en": "IP Address"},
    "card_domain": {"ar": "المجال / مجموعة العمل", "en": "Domain / Workgroup"},
    "card_av": {"ar": "برنامج الحماية", "en": "Antivirus"},
    "card_wu": {"ar": "Windows Update", "en": "Windows Update"},
    "card_ip_type": {"ar": "نوع IP", "en": "IP Type"},
    "card_health": {"ar": "درجة صحة الجهاز", "en": "Device Health Score"},
    # قيم حالة الشبكة
    "connected": {"ar": "متصل ✓", "en": "Connected ✓"},
    "disconnected": {"ar": "غير متصل ✗", "en": "Disconnected ✗"},
    "dhcp": {"ar": "تلقائي (DHCP)", "en": "Automatic (DHCP)"},
    "static": {"ar": "ثابت (Static)", "en": "Static"},
    "domain_joined": {"ar": "منضم للمجال", "en": "Domain Joined"},
    "workgroup": {"ar": "مجموعة عمل", "en": "Workgroup"},
    "available": {"ar": "المتاح:", "en": "Available:"},
    "av_enabled": {"ar": "مفعّل ✓", "en": "Enabled ✓"},
    "av_disabled": {"ar": "معطّل ✗", "en": "Disabled ✗"},
    "av_unknown": {"ar": "غير معروف", "en": "Unknown"},
    "wu_running": {"ar": "يعمل ✓", "en": "Running ✓"},
    "wu_stopped": {"ar": "متوقف ✗", "en": "Stopped ✗"},
    # ── الإعدادات ──────────────────────────────────────────────────────────
    "settings_title": {"ar": "الإعدادات", "en": "Settings"},
    "settings_appearance": {"ar": "المظهر", "en": "Appearance"},
    "settings_theme": {"ar": "السمة:", "en": "Theme:"},
    "settings_apply_theme": {"ar": "تطبيق السمة", "en": "Apply Theme"},
    "settings_language": {"ar": "اللغة:", "en": "Language:"},
    "settings_apply_lang": {"ar": "تطبيق اللغة", "en": "Apply Language"},
    "settings_lang_restart": {
        "ar": "سيتم إعادة تشغيل التطبيق لتطبيق اللغة الجديدة.\nهل تريد المتابعة؟",
        "en": "The application will restart to apply the new language.\nContinue?",
    },
    "settings_db": {"ar": "قاعدة البيانات", "en": "Database"},
    "settings_db_path": {"ar": "مسار قاعدة البيانات:", "en": "Database Path:"},
    "settings_open_folder": {"ar": "فتح المجلد", "en": "Open Folder"},
    "settings_backup": {"ar": "نسخ احتياطي…", "en": "Backup…"},
    "settings_exports": {"ar": "مجلد التصدير", "en": "Export Folder"},
    "settings_export_path": {"ar": "مسار التصدير:", "en": "Export Path:"},
    "settings_about_title": {
        "ar": "حول IT Operations Console",
        "en": "About IT Operations Console",
    },
    # ── عام ────────────────────────────────────────────────────────────────
    "yes_continue": {"ar": "نعم، متابعة", "en": "Yes, Continue"},
    "cancel": {"ar": "إلغاء", "en": "Cancel"},
    "na": {"ar": "غير متاح", "en": "N/A"},
    "success": {"ar": "نجح", "en": "Success"},
    "failed": {"ar": "فشل", "en": "Failed"},
    "status": {"ar": "الحالة:", "en": "Status:"},
    "clear": {"ar": "مسح", "en": "Clear"},
    "results": {"ar": "النتائج", "en": "Results"},
    # ── صفحة الأمن السيبراني ──────────────────────────────────────────────
    "cyber_title": {"ar": "الأمن السيبراني", "en": "Cybersecurity"},
    "cyber_subtitle": {
        "ar": "فحص وضع الحماية على هذا الجهاز وفق معايير أمن المعلومات",
        "en": "Assess the security posture of this device",
    },
    "cyber_scan": {"ar": "↻  فحص الآن", "en": "↻  Scan Now"},
    "cyber_score": {"ar": "درجة الأمان", "en": "Security Score"},
    "cyber_antivirus": {"ar": "مكافح الفيروسات", "en": "Antivirus"},
    "cyber_firewall": {"ar": "جدار الحماية", "en": "Firewall"},
    "cyber_defender": {"ar": "Windows Defender", "en": "Windows Defender"},
    "cyber_bitlocker": {"ar": "تشفير BitLocker", "en": "BitLocker Encryption"},
    "cyber_uac": {"ar": "التحكم بحسابات المستخدمين (UAC)", "en": "User Account Control (UAC)"},
    "cyber_smartscreen": {"ar": "Windows SmartScreen", "en": "Windows SmartScreen"},
    "cyber_wu": {"ar": "Windows Update", "en": "Windows Update"},
    "cyber_installed": {"ar": "برامج الأمن المثبَّتة", "en": "Installed Security Software"},
    "cyber_nca": {"ar": "معايير هيئة الأمن السيبراني (NCA)", "en": "NCA Compliance"},
    "cyber_enabled": {"ar": "مفعّل", "en": "Enabled"},
    "cyber_disabled": {"ar": "معطّل", "en": "Disabled"},
    "cyber_protected": {"ar": "محمي", "en": "Protected"},
    "cyber_not_protected": {"ar": "غير محمي", "en": "Not Protected"},
    "cyber_name_col": {"ar": "البرنامج", "en": "Software"},
    "cyber_type_col": {"ar": "النوع", "en": "Type"},
    "cyber_status_col": {"ar": "الحالة", "en": "Status"},
    "cyber_version_col": {"ar": "الإصدار", "en": "Version"},
    "cyber_publisher_col": {"ar": "الناشر", "en": "Publisher"},
}


def set_lang(code: str) -> None:
    """حدّد اللغة — استدعيها مرة وحدة عند بداية البرنامج."""
    global _current
    if code in ("ar", "en"):
        _current = code


def get_lang() -> str:
    """ارجع اللغة الحالية."""
    return _current


def text(ar: str, en: str) -> str:
    return ar if _current == "ar" else en


def tr(key: str) -> str:
    """
    ارجع النص المترجم للمفتاح المطلوب حسب اللغة الحالية.
    لو المفتاح مو موجود يرجع المفتاح نفسه.
    """
    entry = _T.get(key)
    if entry is None:
        return key
    return entry.get(_current, entry.get("ar", key))
