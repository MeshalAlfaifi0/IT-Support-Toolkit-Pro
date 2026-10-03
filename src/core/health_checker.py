"""
فاحص صحة الجهاز الكامل.
يشغّل كل الفحوصات ويرجع scan_data موحّداً يُحفظ في قاعدة البيانات
ويُستخدَم في حساب الدرجة وتوليد التوصيات.
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

import datetime
import json

from src.core import system_info
from src.core.health_score import calculate_health_score
from src.core.recommendations import generate_recommendations
from src.database.connection import execute_query
from src.utils.logger import setup_logger

log = setup_logger(__name__)


def run_full_scan(progress_callback=None) -> dict:
    """
    ينفّذ كل فحوصات الجهاز ويرجع scan_data شاملاً.

    progress_callback: دالة اختيارية (نسبة%, رسالة) لتحديث شريط التقدم.
    """

    def _prog(pct: int, msg: str):
        from PySide6.QtCore import QThread

        if QThread.currentThread().isInterruptionRequested():
            raise RuntimeError("Scan cancelled during shutdown")
        if progress_callback:
            try:
                progress_callback(pct, msg)
            except Exception:
                pass

    scan_data = {}

    _prog(5, "جمع معلومات نظام التشغيل…")
    scan_data["device_name"] = system_info.get_device_name()
    scan_data["username"] = system_info.get_username()
    scan_data["os"] = system_info.get_os_info()
    scan_data["scan_timestamp"] = datetime.datetime.now().isoformat()

    _prog(15, "فحص المعالج CPU…")
    scan_data["cpu"] = system_info.get_cpu_info()

    _prog(25, "فحص الذاكرة RAM…")
    scan_data["ram"] = system_info.get_ram_info()

    _prog(35, "فحص الأقراص…")
    scan_data["disks"] = system_info.get_disk_info()

    _prog(45, "فحص برنامج الحماية…")
    scan_data["antivirus"] = system_info.get_antivirus_status()
    scan_data["defender"] = system_info.get_defender_status()

    _prog(50, "جمع أكثر البرامج استهلاكاً للـ CPU…")
    scan_data["cpu_top_processes"] = system_info.get_top_cpu_processes(limit=5)

    _prog(53, "جمع أكثر البرامج استهلاكاً للـ RAM…")
    scan_data["ram_top_processes"] = system_info.get_top_ram_processes(limit=5)

    _prog(55, "فحص خدمة Windows Update…")
    scan_data["windows_update"] = system_info.get_windows_update_status()

    _prog(62, "فحص الاتصال بالشبكة…")
    scan_data["network"] = system_info.get_network_status()

    _prog(68, "فحص التعريفات…")
    scan_data["drivers"] = system_info.get_driver_info()

    _prog(75, "فحص تطبيقات بدء التشغيل…")
    scan_data["startup_apps"] = system_info.get_startup_apps()

    _prog(82, "قراءة سجل الأحداث (آخر 7 أيام)…")
    try:
        from src.core.event_viewer import read_event_logs

        scan_data["event_viewer"] = read_event_logs(days=7, max_events=300)
    except Exception as exc:
        log.warning(f"Event Viewer skipped: {exc}")
        scan_data["event_viewer"] = {
            "error_message": str(exc),
            "total": 0,
            "errors": 0,
            "warnings": 0,
        }

    _prog(90, "حساب درجة الصحة…")
    cpu_pct = scan_data["cpu"].get("usage_pct", 0)
    ram_pct = scan_data["ram"].get("usage_pct", 0)
    ram_total_gb = scan_data["ram"].get("total_gb", 0)
    av_enabled = scan_data["antivirus"].get("enabled", False)
    av_name = scan_data["antivirus"].get("name", "Unknown")
    wu_running = scan_data["windows_update"].get("service_status") == "Running"
    net_ok = scan_data["network"].get("connected", False)

    # نسبة المساحة الحرة في C:
    c_free_pct = 0.0
    disk_known = False
    for disk in scan_data["disks"]:
        if disk.get("mountpoint", "").upper().startswith("C"):
            disk_known = True
            c_free_pct = 100.0 - disk.get("usage_pct", 0)
            break

    # هل في أخطاء تعريفات في سجل الأحداث؟
    driver_errors = scan_data["event_viewer"].get("driver", 0) > 0

    unavailable = set()
    if not scan_data["cpu"].get("query_ok"):
        unavailable.add("cpu")
    if not scan_data["ram"].get("query_ok"):
        unavailable.add("ram")
    if not disk_known:
        unavailable.add("disk")
    if scan_data["antivirus"].get("status") == "Unknown":
        unavailable.add("antivirus")
    if scan_data["windows_update"].get("service_status") == "Unknown":
        unavailable.add("windows_update")
    if scan_data["event_viewer"].get("error_message"):
        unavailable.add("drivers")
    scan_data["unavailable_checks"] = sorted(unavailable)
    health = calculate_health_score(
        cpu_pct,
        ram_pct,
        ram_total_gb,
        c_free_pct,
        av_enabled,
        av_name,
        wu_running,
        driver_errors,
        net_ok,
        unavailable=unavailable,
    )
    scan_data["health_score"] = health

    _prog(95, "توليد التوصيات…")
    scan_data["recommendations"] = generate_recommendations(scan_data)

    _prog(98, "حفظ النتائج في قاعدة البيانات…")
    _save_scan(scan_data)

    _prog(100, "اكتمل الفحص.")
    log.info(f"Full scan complete. Score={health['score']}/100")
    return scan_data


def _save_scan(scan_data: dict) -> int:
    """Commit device, scan and recommendations together; roll back any failure."""
    from src.database.connection import get_connection

    conn = get_connection()
    try:
        with conn:
            device_name = scan_data.get("device_name", "Unknown")
            row = conn.execute(
                "SELECT id FROM devices WHERE device_name = ? ORDER BY created_at DESC LIMIT 1",
                (device_name,),
            ).fetchone()
            if row:
                device_id = row["id"]
            else:
                device_id = conn.execute(
                    "INSERT INTO devices (device_name, username, os_version, cpu_name, ram_total) VALUES (?, ?, ?, ?, ?)",
                    (
                        device_name,
                        scan_data.get("username", "Unknown"),
                        scan_data.get("os", {}).get("full", "Unknown"),
                        scan_data.get("cpu", {}).get("name", "Unknown"),
                        scan_data.get("ram", {}).get("total", 0),
                    ),
                ).lastrowid
            disks = scan_data.get("disks", [])
            hc_id = conn.execute(
                "INSERT INTO health_checks (device_id, cpu_usage, ram_usage, disk_usage, antivirus_status, "
                "windows_update_status, network_status, health_score, scan_data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    device_id,
                    scan_data.get("cpu", {}).get("usage_pct", 0),
                    scan_data.get("ram", {}).get("usage_pct", 0),
                    disks[0].get("usage_pct", 0) if disks else 0,
                    scan_data.get("antivirus", {}).get("status", "Unknown"),
                    scan_data.get("windows_update", {}).get("service_status", "Unknown"),
                    scan_data.get("network", {}).get("status", "Unknown"),
                    scan_data.get("health_score", {}).get("score", 0),
                    json.dumps(scan_data, default=str),
                ),
            ).lastrowid
            conn.executemany(
                "INSERT INTO recommendations (health_check_id, category, recommendation, priority) VALUES (?, ?, ?, ?)",
                [
                    (hc_id, rec["category"], rec["recommendation"], rec["priority"])
                    for rec in scan_data.get("recommendations", [])
                ],
            )
        return hc_id
    finally:
        conn.close()


def get_latest_scan() -> dict | None:
    """يجيب آخر نتيجة فحص محفوظة في قاعدة البيانات."""
    rows = execute_query("SELECT scan_data FROM health_checks ORDER BY created_at DESC LIMIT 1")
    if not rows:
        return None
    try:
        return json.loads(rows[0]["scan_data"])
    except Exception:
        return None
