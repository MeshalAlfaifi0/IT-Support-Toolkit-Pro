"""
تشخيص الشبكة — IP والبوابة والـ DNS والـ ping وفحص الأسماء.
كل العمليات قراءة فقط وآمنة بدون صلاحيات مسؤول.
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

import re
import socket

from src.utils.command_runner import run_command
from src.utils.logger import setup_logger

log = setup_logger(__name__)


def get_ip_config() -> dict:
    """اختيار محول IPv4 ذي بوابة وقراءة DNS كاملًا من جامع الشبكة المشترك."""
    from src.core.network_info import get_all_adapters

    result = {
        "ip_address": "Unknown",
        "mac_address": "Unknown",
        "default_gateway": "Unknown",
        "dns_servers": [],
        "adapter_name": "Unknown",
    }
    adapters = get_all_adapters()
    if not adapters:
        return result
    adapter = next(
        (item for item in adapters if item.get("gateway") not in (None, "", "Unknown", "غير متاح")),
        adapters[0],
    )

    def known(value):
        return value if value not in (None, "", "غير متاح") else "Unknown"

    result.update(
        ip_address=known(adapter.get("ip")),
        mac_address=known(adapter.get("mac")),
        default_gateway=known(adapter.get("gateway")),
        dns_servers=list(adapter.get("dns") or []),
        adapter_name=known(adapter.get("name")),
    )
    return result


def ping_host(host: str, count: int = 4) -> dict:
    """
    يختبر الاتصال بجهاز ويرجع إحصائيات التأخير.

    يرجع dict فيه: reachable, min_ms, max_ms, avg_ms,
    packets_sent, packets_received, loss_pct, raw_output.
    """
    result = {
        "host": host,
        "reachable": False,
        "min_ms": None,
        "max_ms": None,
        "avg_ms": None,
        "packets_sent": count,
        "packets_received": 0,
        "loss_pct": 100,
        "raw_output": "",
    }
    try:
        # العنوان وسيط مستقل؛ لا يستطيع تشغيل أمر إضافي عبر & أو |.
        if (
            not isinstance(host, str)
            or not re.fullmatch(r"[A-Za-z0-9_.:%-]{1,253}", host)
            or host.startswith("-")
        ):
            raise ValueError("Invalid ping host")
        if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 10:
            raise ValueError("Ping count must be between 1 and 10")
        ok, out, err = run_command(
            ["ping", "-n", str(count), "-w", "2000", host], timeout=30, shell=False
        )
        raw = out or err
        result["raw_output"] = raw

        result["reachable"] = ok

        # نحلّل الحزم المرسلة والمستقبَلة
        m = re.search(
            r"Packets: Sent\s*=\s*(\d+).*?Received\s*=\s*(\d+).*?Lost\s*=\s*(\d+)", raw, re.I
        )
        if m:
            sent, recv, lost = int(m.group(1)), int(m.group(2)), int(m.group(3))
            result["packets_sent"] = sent
            result["packets_received"] = recv
            result["loss_pct"] = round((lost / sent) * 100) if sent else 100
            result["reachable"] = recv > 0

        # نحلّل أوقات التأخير
        m2 = re.search(
            r"Minimum\s*=\s*(\d+)ms.*?Maximum\s*=\s*(\d+)ms.*?Average\s*=\s*(\d+)ms", raw, re.I
        )
        if m2:
            result["min_ms"] = int(m2.group(1))
            result["max_ms"] = int(m2.group(2))
            result["avg_ms"] = int(m2.group(3))

    except Exception as exc:
        log.error(f"Ping error for {host}: {exc}")
        result["raw_output"] = str(exc)

    return result


def resolve_hostname(hostname: str) -> dict:
    """يحاول يحل اسم الجهاز لعنوان IP عن طريق DNS."""
    try:
        ip = socket.gethostbyname(hostname)
        return {"hostname": hostname, "resolved": True, "ip": ip}
    except socket.gaierror as exc:
        return {"hostname": hostname, "resolved": False, "ip": None, "error": str(exc)}


def run_full_network_diagnostics() -> dict:
    """
    يشغّل كل فحوصات الشبكة ويرجع تقريراً موحّداً.
    هذي هي الدالة اللي تستدعيها الواجهة في thread منفصل.
    """
    log.info("Starting full network diagnostics")
    report = {}

    report["ip_config"] = get_ip_config()
    gw = report["ip_config"].get("default_gateway", "")

    # نختبر البوابة الافتراضية
    if gw and gw != "Unknown":
        report["ping_gateway"] = ping_host(gw, count=4)
    else:
        report["ping_gateway"] = {
            "host": "N/A",
            "reachable": False,
            "raw_output": "No gateway found",
        }

    # نختبر DNS العامة
    report["ping_google_dns"] = ping_host("8.8.8.8")
    report["ping_cloudflare_dns"] = ping_host("1.1.1.1")

    # نختبر تحليل الأسماء
    report["resolve_google"] = resolve_hostname("google.com")
    report["resolve_microsoft"] = resolve_hostname("microsoft.com")

    log.info("Network diagnostics complete")
    return report
