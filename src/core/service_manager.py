"""
إدارة خدمات ويندوز — فحص الحالة وتشغيل وإيقاف وإعادة تشغيل.
عمليات الإيقاف والتشغيل تحتاج صلاحيات مسؤول.
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

import win32serviceutil

from src.utils.logger import setup_logger

log = setup_logger(__name__)

# الخدمات المتاحة في الواجهة لفريق دعم IT
MANAGED_SERVICES = {
    "Print Spooler": "Spooler",
    "Windows Update": "wuauserv",
    "DNS Client": "Dnscache",
    "DHCP Client": "Dhcp",
    "Windows Defender": "WinDefend",
    "Remote Desktop Services": "TermService",
}

# تعيين أكواد حالة الخدمة لنصوص مقروءة
_STATE_MAP = {
    1: "Stopped",
    2: "Starting",
    3: "Stopping",
    4: "Running",
    5: "Continue Pending",
    6: "Pause Pending",
    7: "Paused",
}


def get_service_status(service_name: str) -> str:
    """
    يرجع حالة خدمة ويندوز كنص مقروء.
    service_name: الاسم القصير مثل "Spooler".
    """
    try:
        status = win32serviceutil.QueryServiceStatus(service_name)
        return _STATE_MAP.get(status[1], "Unknown")
    except Exception as exc:
        log.warning(f"Could not query service '{service_name}': {exc}")
        return "Unknown"


def restart_service(service_name: str) -> tuple[bool, str]:
    """
    يوقف ثم يشغّل خدمة.
    يحتاج صلاحيات Administrator.
    يرجع (نجح؟, رسالة).
    """
    try:
        log.info(f"Restarting service: {service_name}")
        win32serviceutil.RestartService(service_name, waitSeconds=10)
        status = get_service_status(service_name)
        msg = f"Service '{service_name}' restarted successfully. Status: {status}"
        log.info(msg)
        return True, msg
    except Exception as exc:
        msg = f"Failed to restart '{service_name}': {exc}"
        log.error(msg)
        return False, msg


def start_service(service_name: str) -> tuple[bool, str]:
    """يشغّل خدمة متوقفة."""
    try:
        win32serviceutil.StartService(service_name)
        msg = f"Service '{service_name}' started."
        log.info(msg)
        return True, msg
    except Exception as exc:
        msg = f"Failed to start '{service_name}': {exc}"
        log.error(msg)
        return False, msg


def stop_service(service_name: str) -> tuple[bool, str]:
    """يوقف خدمة شغّالة."""
    try:
        win32serviceutil.StopService(service_name)
        msg = f"Service '{service_name}' stopped."
        log.info(msg)
        return True, msg
    except Exception as exc:
        msg = f"Failed to stop '{service_name}': {exc}"
        log.error(msg)
        return False, msg


def get_all_managed_statuses() -> dict:
    """يرجع حالة كل الخدمات في MANAGED_SERVICES."""
    return {display: get_service_status(short) for display, short in MANAGED_SERVICES.items()}
