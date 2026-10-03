"""
قارئ سجل أحداث ويندوز (Event Viewer).
يقرأ الأخطاء والتحذيرات من آخر N يوم عن طريق pywin32.
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

import datetime

import win32evtlog
import win32evtlogutil

from src.utils.logger import setup_logger

log = setup_logger(__name__)

# تعيين أنواع الأحداث لتسميات مقروءة
_TYPE_MAP = {
    win32evtlog.EVENTLOG_ERROR_TYPE: "Error",
    win32evtlog.EVENTLOG_WARNING_TYPE: "Warning",
    win32evtlog.EVENTLOG_INFORMATION_TYPE: "Information",
    win32evtlog.EVENTLOG_AUDIT_SUCCESS: "Audit Success",
    win32evtlog.EVENTLOG_AUDIT_FAILURE: "Audit Failure",
}

# السجلات اللي نقرأها (System و Application الأهم لدعم IT)
QUERY_LOGS = ["System", "Application"]

# كلمات نستخدمها لتصنيف الأحداث
_KEYWORDS = {
    "disk": ["disk", "filesystem", "ntfs", "volume", "chkdsk", "storage"],
    "driver": ["driver", "device", "irq", "bsod", "bugcheck"],
    "app_crash": ["faulting", "application error", "crash", "stopped working"],
    "print": ["spooler", "print", "printer"],
    "network": ["network", "dns", "dhcp", "tcp", "connection"],
}


def read_event_logs(days: int = 7, max_events: int = 500) -> dict:
    """
    يقرأ سجلات أحداث ويندوز الأخيرة.

    days: عدد الأيام الماضية.
    max_events: الحد الأقصى للأحداث عشان ما تثقل الواجهة.

    يرجع dict فيه إحصائيات وقائمة الأحداث.
    """
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    summary = {
        "total": 0,
        "errors": 0,
        "warnings": 0,
        "disk": 0,
        "driver": 0,
        "app_crash": 0,
        "print": 0,
        "network": 0,
        "events": [],
        "error_message": None,
    }

    try:
        for log_name in QUERY_LOGS:
            _read_log(log_name, cutoff, max_events, summary)
    except Exception as exc:
        log.error(f"Event Viewer read failed: {exc}")
        summary["error_message"] = (
            f"Could not access Event Viewer: {exc}\n"
            "Run the application as Administrator for full Event Viewer access."
        )

    return summary


def _read_log(log_name: str, cutoff: datetime.datetime, max_events: int, summary: dict):
    """يضيف أحداث سجل واحد لـ summary."""
    try:
        handle = win32evtlog.OpenEventLog(None, log_name)
    except Exception as exc:
        log.warning(f"Cannot open '{log_name}' log: {exc}")
        summary["error_message"] = f"Could not read {log_name} event log"
        return

    # نقرأ من الأحدث للأقدم
    flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

    try:
        while len(summary["events"]) < max_events:
            events = win32evtlog.ReadEventLog(handle, flags, 0)
            if not events:
                break

            for evt in events:
                if len(summary["events"]) >= max_events:
                    break

                # TimeGenerated من نوع pywintypes.datetime، نحوّله لـ stdlib
                try:
                    evt_time = datetime.datetime(
                        evt.TimeGenerated.year,
                        evt.TimeGenerated.month,
                        evt.TimeGenerated.day,
                        evt.TimeGenerated.hour,
                        evt.TimeGenerated.minute,
                        evt.TimeGenerated.second,
                    )
                except Exception:
                    continue

                if evt_time < cutoff:
                    # الأحداث من الأحدث للأقدم — لو تجاوزنا التاريخ نوقف
                    return

                evt_type = _TYPE_MAP.get(evt.EventType, "Unknown")
                if evt_type not in ("Error", "Warning"):
                    continue

                # نجيب الرسالة بشكل مقروء
                try:
                    message = win32evtlogutil.SafeFormatMessage(evt, log_name)
                    message = (message or "").strip().replace("\r\n", " ").replace("\n", " ")[:300]
                except Exception:
                    message = f"EventID {evt.EventID & 0xFFFF}"

                entry = {
                    "time": evt_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "log": log_name,
                    "type": evt_type,
                    "source": evt.SourceName or "Unknown",
                    "message": message,
                }
                summary["events"].append(entry)
                summary["total"] += 1
                if evt_type == "Error":
                    summary["errors"] += 1
                elif evt_type == "Warning":
                    summary["warnings"] += 1

                # نصنّف الحدث حسب الكلمات المفتاحية
                msg_lower = message.lower()
                for category, keywords in _KEYWORDS.items():
                    if any(kw in msg_lower for kw in keywords):
                        summary[category] += 1
                        break  # فئة وحدة لكل حدث

    finally:
        win32evtlog.CloseEventLog(handle)
