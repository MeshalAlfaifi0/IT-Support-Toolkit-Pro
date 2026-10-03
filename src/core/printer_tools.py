"""
إدارة الطابعات — عرض القائمة وفحص الطوابير وإعادة تشغيل Spooler ومسح الطابور.
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

import re
from contextlib import contextmanager

import win32print

from src.core.network_tools import ping_host
from src.utils.logger import setup_logger

log = setup_logger(__name__)


def get_printers() -> list[dict]:
    """
    يرجع قائمة الطابعات المثبّتة مع الاسم والحالة والتعريف والمنفذ.
    """
    printers = []
    try:
        default_printer = win32print.GetDefaultPrinter()
    except Exception:
        default_printer = ""

    try:
        for flags in [win32print.PRINTER_ENUM_LOCAL, win32print.PRINTER_ENUM_CONNECTIONS]:
            try:
                for printer in win32print.EnumPrinters(flags, None, 2):
                    info = printer  # PRINTER_INFO_2
                    name = info.get("pPrinterName", "Unknown")
                    printers.append(
                        {
                            "name": name,
                            "driver": info.get("pDriverName", "Unknown"),
                            "port": info.get("pPortName", "Unknown"),
                            "status": _decode_printer_status(info.get("Status", 0)),
                            "is_default": (name == default_printer),
                            "jobs": _get_job_count(name),
                        }
                    )
            except Exception as exc:
                log.warning(f"EnumPrinters flags={flags} failed: {exc}")

    except Exception as exc:
        log.error(f"get_printers error: {exc}")

    # نحذف المكررات
    seen = set()
    unique = []
    for p in printers:
        if p["name"] not in seen:
            seen.add(p["name"])
            unique.append(p)
    return unique


def _decode_printer_status(status_code: int) -> str:
    """حالة الطابعة مجموعة أعلام بتّية، وليست أرقامًا متتابعة."""
    if status_code == 0:
        return "Ready"
    flags = {
        win32print.PRINTER_STATUS_PAUSED: "Paused",
        win32print.PRINTER_STATUS_ERROR: "Error",
        win32print.PRINTER_STATUS_PENDING_DELETION: "Pending Deletion",
        win32print.PRINTER_STATUS_PAPER_JAM: "Paper Jam",
        win32print.PRINTER_STATUS_PAPER_OUT: "Paper Out",
        win32print.PRINTER_STATUS_MANUAL_FEED: "Manual Feed",
        win32print.PRINTER_STATUS_PAPER_PROBLEM: "Paper Problem",
        win32print.PRINTER_STATUS_OFFLINE: "Offline",
        win32print.PRINTER_STATUS_IO_ACTIVE: "I/O Active",
        win32print.PRINTER_STATUS_BUSY: "Busy",
        win32print.PRINTER_STATUS_PRINTING: "Printing",
        win32print.PRINTER_STATUS_OUTPUT_BIN_FULL: "Output Bin Full",
        win32print.PRINTER_STATUS_NOT_AVAILABLE: "Not Available",
        win32print.PRINTER_STATUS_WAITING: "Waiting",
        win32print.PRINTER_STATUS_PROCESSING: "Processing",
        win32print.PRINTER_STATUS_INITIALIZING: "Initializing",
        win32print.PRINTER_STATUS_WARMING_UP: "Warming Up",
        win32print.PRINTER_STATUS_TONER_LOW: "Toner Low",
        win32print.PRINTER_STATUS_NO_TONER: "No Toner",
        win32print.PRINTER_STATUS_PAGE_PUNT: "Page Punt",
        win32print.PRINTER_STATUS_USER_INTERVENTION: "User Intervention",
        win32print.PRINTER_STATUS_OUT_OF_MEMORY: "Out of Memory",
        win32print.PRINTER_STATUS_DOOR_OPEN: "Door Open",
        win32print.PRINTER_STATUS_SERVER_UNKNOWN: "Server Unknown",
        win32print.PRINTER_STATUS_POWER_SAVE: "Power Save",
    }
    labels = [label for flag, label in flags.items() if status_code & flag]
    known_bits = 0
    for flag in flags:
        known_bits |= flag
    if status_code & ~known_bits:
        labels.append(f"Unknown flags 0x{status_code & ~known_bits:x}")
    return ", ".join(labels) if labels else f"Status {status_code}"


@contextmanager
def _printer_handle(printer_name):
    """إغلاق مقبض الطابعة مضمون حتى لو أخفق الاستعلام أو إلغاء مهمة."""
    handle = win32print.OpenPrinter(printer_name)
    try:
        yield handle
    finally:
        win32print.ClosePrinter(handle)


def _get_job_count(printer_name: str) -> int:
    """قراءة العدد الفعلي، بما يشمل الطوابير التي تتجاوز 100 مهمة."""
    try:
        with _printer_handle(printer_name) as handle:
            return int(win32print.GetPrinter(handle, 2).get("cJobs", 0))
    except Exception:
        return 0


def get_printer_jobs(printer_name: str) -> list[dict]:
    """إرجاع أول 100 مهمة للعرض، مع إغلاق المقبض عند الفشل."""
    jobs = []
    try:
        with _printer_handle(printer_name) as handle:
            for job in win32print.EnumJobs(handle, 0, 100, 1):
                jobs.append(
                    {
                        "job_id": job.get("JobId", "?"),
                        "document": job.get("pDocument", "Unknown"),
                        "user": job.get("pUserName", "Unknown"),
                        "status": job.get("Status", 0),
                        "pages": job.get("TotalPages", 0),
                    }
                )
    except Exception as exc:
        log.error(f"EnumJobs failed for '{printer_name}': {exc}")
    return jobs


def clear_print_queue(printer_name: str) -> tuple[bool, str]:
    """إلغاء الطابور المحدد؛ لا نعلن نجاحًا كاملًا إذا تعذّر إلغاء بعض المهام."""
    try:
        with _printer_handle(printer_name) as handle:
            count = int(win32print.GetPrinter(handle, 2).get("cJobs", 0))
            jobs = win32print.EnumJobs(handle, 0, max(count, 1), 1)
            cancelled = failed = 0
            for job in jobs:
                try:
                    win32print.SetJob(handle, job["JobId"], 0, None, win32print.JOB_CONTROL_DELETE)
                    cancelled += 1
                except Exception as exc:
                    failed += 1
                    log.warning(f"Cannot cancel job {job.get('JobId')}: {exc}")
        message = f"Cancelled {cancelled} job(s) on '{printer_name}'."
        if failed:
            message += f" Failed to cancel {failed} job(s)."
        return failed == 0, message
    except Exception as exc:
        message = f"Failed to clear queue for '{printer_name}': {exc}"
        log.error(message)
        return False, message


def ping_printer(port_name: str) -> dict:
    """
    لو الطابعة على شبكة (IP في اسم المنفذ)، يختبر الاتصال بها.
    يرجع نتيجة ping أو رسالة أن المنفذ مو شبكي.
    """
    # نستخرج IP من اسم المنفذ مثل "IP_192.168.1.100"
    ip_match = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", port_name)
    if ip_match:
        return ping_host(ip_match.group(1), count=4)
    return {
        "host": port_name,
        "reachable": None,
        "raw_output": "Not a network (IP) port – ping not applicable.",
    }


def restart_spooler() -> tuple[bool, str]:
    """يوقف ثم يشغّل خدمة Print Spooler (يحتاج مسؤول)."""
    from src.core.service_manager import restart_service

    return restart_service("Spooler")
