"""
محرّك التوصيات.
يحلّل نتائج الفحص ويولّد قائمة توصيات مرتّبة حسب الأولوية.
التوصيات تُحفظ في SQLite.
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

from src.database.connection import execute_write
from src.utils.logger import setup_logger

log = setup_logger(__name__)

# مستويات الأولوية
HIGH = "High"
MEDIUM = "Medium"
LOW = "Low"


def generate_recommendations(scan_data: dict) -> list[dict]:
    """
    يحلّل scan_data ويرجع قائمة توصيات، كل عنصر فيه:
        category, recommendation, priority
    مرتّبة من الأعلى أولوية للأدنى.
    """
    recs = []

    cpu = scan_data.get("cpu", {})
    ram = scan_data.get("ram", {})
    disks = scan_data.get("disks", [])
    av = scan_data.get("antivirus", {})
    wu = scan_data.get("windows_update", {})
    net = scan_data.get("network", {})
    ev = scan_data.get("event_viewer", {})
    start = scan_data.get("startup_apps", [])

    # ── المعالج ──────────────────────────────────────────────────────────────
    cpu_pct = cpu.get("usage_pct", 0)
    if cpu_pct > 85:
        recs.append(
            {
                "category": "CPU",
                "recommendation": f"CPU usage is critically high ({cpu_pct:.0f}%). "
                "Identify and close resource-heavy processes.",
                "priority": HIGH,
            }
        )
    elif cpu_pct > 60:
        recs.append(
            {
                "category": "CPU",
                "recommendation": f"CPU usage is elevated ({cpu_pct:.0f}%). "
                "Consider closing unnecessary background applications.",
                "priority": MEDIUM,
            }
        )

    # ── الذاكرة ──────────────────────────────────────────────────────────────
    ram_pct = ram.get("usage_pct", 0)
    ram_gb = ram.get("total_gb", 0)
    if 0 < ram_gb <= 4:
        recs.append(
            {
                "category": "RAM",
                "recommendation": f"Only {ram_gb:.0f} GB of RAM installed. "
                "Upgrading to 8 GB or 16 GB is strongly recommended for better performance.",
                "priority": HIGH,
            }
        )
    if ram_pct > 85:
        recs.append(
            {
                "category": "RAM",
                "recommendation": f"RAM usage is very high ({ram_pct:.0f}%). "
                "Close unused applications or consider adding more RAM.",
                "priority": HIGH,
            }
        )
    elif ram_pct > 70:
        recs.append(
            {
                "category": "RAM",
                "recommendation": f"RAM usage is elevated ({ram_pct:.0f}%). "
                "Monitor for memory leaks or plan a RAM upgrade.",
                "priority": MEDIUM,
            }
        )

    # ── الأقراص ──────────────────────────────────────────────────────────────
    for disk in disks:
        mountpoint = disk.get("mountpoint", "")
        free_pct = 100 - disk.get("usage_pct", 0)
        if mountpoint.upper().startswith("C"):
            if free_pct < 10:
                recs.append(
                    {
                        "category": "Disk",
                        "recommendation": f"C: drive is critically low on space "
                        f"({free_pct:.0f}% free). "
                        "Run Temp Cleanup, uninstall unused programs, "
                        "or expand the drive.",
                        "priority": HIGH,
                    }
                )
            elif free_pct < 20:
                recs.append(
                    {
                        "category": "Disk",
                        "recommendation": f"C: drive is running low ({free_pct:.0f}% free). "
                        "Consider clearing temporary files.",
                        "priority": MEDIUM,
                    }
                )
        disk_type = disk.get("disk_type", "Unknown")
        if disk_type == "HDD" and mountpoint.upper().startswith("C"):
            recs.append(
                {
                    "category": "Disk",
                    "recommendation": "The OS drive appears to be a traditional HDD. "
                    "Upgrading to an SSD would significantly improve "
                    "Windows boot times and application responsiveness.",
                    "priority": LOW,
                }
            )

    # ── برنامج الحماية ────────────────────────────────────────────────────────
    av_enabled = av.get("enabled", False)
    av_name = av.get("name", "Unknown")
    if av_name == "Unknown":
        recs.append(
            dict(
                category="Antivirus",
                recommendation="Antivirus status could not be verified. This does not prove protection is disabled.",
                priority=MEDIUM,
            )
        )
    elif av_enabled is False:
        recs.append(
            {
                "category": "Antivirus",
                "recommendation": "Antivirus protection is disabled or could not be detected. "
                "Ensure Windows Defender or a third-party AV is active.",
                "priority": HIGH,
            }
        )

    # ── Windows Update ────────────────────────────────────────────────────────
    wu_status = wu.get("service_status", "Unknown")
    if wu_status == "Unknown":
        recs.append(
            dict(
                category="Windows Update",
                recommendation="Windows Update service status could not be read. Check it manually; patch currency was not evaluated.",
                priority=MEDIUM,
            )
        )
    elif wu_status != "Running":
        recs.append(
            {
                "category": "Windows Update",
                "recommendation": "The Windows Update service is not running. "
                "This can be normal for a trigger-start service. Check update history and pending updates manually.",
                "priority": HIGH,
            }
        )

    # ── الشبكة ────────────────────────────────────────────────────────────────
    if not net.get("connected", True):
        recs.append(
            {
                "category": "Network",
                "recommendation": "The test endpoint 8.8.8.8:53 could not be reached. "
                "This alone does not prove the device is offline. Check local connectivity and policy.",
                "priority": HIGH,
            }
        )

    # ── تطبيقات بدء التشغيل ──────────────────────────────────────────────────
    if len(start) > 8:
        recs.append(
            {
                "category": "Startup",
                "recommendation": f"{len(start)} startup applications found. "
                "Disable unnecessary startup items via Task Manager → "
                "Startup tab to improve boot time.",
                "priority": MEDIUM,
            }
        )

    # ── سجل الأحداث ──────────────────────────────────────────────────────────
    if ev.get("disk", 0) > 5:
        recs.append(
            {
                "category": "Disk Health",
                "recommendation": f"{ev['disk']} disk-related errors found in Event Viewer. "
                "Run chkdsk and back up data immediately.",
                "priority": HIGH,
            }
        )
    if ev.get("driver", 0) > 3:
        recs.append(
            {
                "category": "Drivers",
                "recommendation": f"{ev['driver']} driver errors found in Event Viewer. "
                "Update or reinstall affected drivers.",
                "priority": MEDIUM,
            }
        )
    if ev.get("print", 0) > 2:
        recs.append(
            {
                "category": "Printing",
                "recommendation": f"{ev['print']} print-related errors found. "
                "Restart the Print Spooler service from the Automation Center.",
                "priority": MEDIUM,
            }
        )

    # ترتيب: عالية أولاً ثم متوسطة ثم منخفضة
    order = {HIGH: 0, MEDIUM: 1, LOW: 2}
    recs.sort(key=lambda r: order.get(r["priority"], 3))

    log.info(f"Generated {len(recs)} recommendations.")
    return recs


def save_recommendations(health_check_id: int, recs: list[dict]) -> None:
    """يحفظ التوصيات في قاعدة البيانات مرتبطةً بفحص معين."""
    for rec in recs:
        execute_write(
            "INSERT INTO recommendations (health_check_id, category, recommendation, priority) "
            "VALUES (?, ?, ?, ?)",
            (health_check_id, rec["category"], rec["recommendation"], rec["priority"]),
        )
