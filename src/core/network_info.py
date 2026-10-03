"""
جمع معلومات الشبكة — IP والقناع والبوابة والـ DNS والـ MAC وحالة DHCP.
نستخدم psutil و WMI وإخراج ipconfig كبديل.
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

import re

from src.utils.command_runner import run_command
from src.utils.logger import setup_logger

log = setup_logger(__name__)

_NA = "غير متاح"  # يطلع لما البيانات مو متاحة


# ── WMI helper ────────────────────────────────────────────────────────────


def _wmi():
    try:
        import wmi

        return wmi.WMI()
    except Exception as exc:
        log.warning(f"WMI غير متاح: {exc}")
        return None


# ── قائمة محولات الشبكة ───────────────────────────────────────────────────


def get_all_adapters() -> list[dict]:
    """
    يرجع قائمة محولات الشبكة مع كل تفاصيلها.
    كل dict فيه: name, ip, mask, gateway, dns, mac,
    dhcp_enabled, status, connection_type, description.
    """
    adapters = []

    # المصدر الأساسي: WMI Win32_NetworkAdapterConfiguration
    c = _wmi()
    if c:
        try:
            for cfg in c.Win32_NetworkAdapterConfiguration(IPEnabled=True):
                adapter = _build_adapter_from_wmi(cfg)
                if adapter:
                    adapters.append(adapter)
        except Exception as exc:
            log.error(f"WMI adapter query error: {exc}")

    # بديل: نحلّل إخراج ipconfig /all لو WMI فشل
    if not adapters:
        adapters = _parse_ipconfig_all()

    return adapters


def _build_adapter_from_wmi(cfg) -> dict | None:
    """يبني dict معلومات المحوّل من كائن WMI NetworkAdapterConfiguration."""
    try:
        ip_list = list(cfg.IPAddress or [])
        mask_list = list(cfg.IPSubnet or [])
        gw_list = list(cfg.DefaultIPGateway or [])
        dns_list = list(cfg.DNSServerSearchOrder or [])

        # نحتاج IPv4 فقط
        ipv4 = [ip for ip in ip_list if _is_ipv4(ip)]
        masks = [m for m in mask_list if _is_ipv4(m)]

        if not ipv4:
            return None

        ip = ipv4[0]
        mask = masks[0] if masks else _NA
        gw = next((g for g in gw_list if _is_ipv4(g)), _NA)
        dns = [d for d in dns_list if _is_ipv4(d)]

        conn_type = _guess_connection_type(cfg.Description or "")

        return {
            "name": cfg.Description or _NA,
            "adapter_index": cfg.Index,
            "ip": ip,
            "mask": mask,
            "gateway": gw,
            "dns": dns,
            "mac": _fmt_mac(cfg.MACAddress or ""),
            "dhcp_enabled": bool(cfg.DHCPEnabled),
            "dhcp_server": cfg.DHCPServer or _NA,
            "status": "متصل",
            "connection_type": conn_type,
            "description": cfg.Description or _NA,
        }
    except Exception as exc:
        log.error(f"WMI adapter build error: {exc}")
        return None


def _parse_ipconfig_all() -> list[dict]:
    """بديل: يحلّل إخراج ipconfig /all ويبني قائمة المحولات."""
    adapters = []
    try:
        _, out, _ = run_command("ipconfig /all", timeout=15)
        if not out:
            return adapters

        current: dict | None = None
        collecting_dns = False

        for line in out.splitlines():
            # قسم محوّل جديد
            if re.search(r"adapter\s+", line, re.I) and not line.startswith(" "):
                if current and current.get("ip") and current["ip"] != _NA:
                    adapters.append(current)
                name = re.sub(r".*adapter\s+", "", line, flags=re.I).rstrip(":").strip()
                current = _empty_adapter(name)
                collecting_dns = False
                continue

            if current is None:
                continue

            stripped = line.strip()

            if "Media disconnected" in stripped:
                current = None
                continue

            if re.search(r"IPv4 Address", stripped, re.I):
                m = re.search(r"(\d+\.\d+\.\d+\.\d+)", stripped)
                if m:
                    current["ip"] = m.group(1)
                collecting_dns = False

            elif re.search(r"Subnet Mask", stripped, re.I):
                m = re.search(r"(\d+\.\d+\.\d+\.\d+)", stripped)
                if m:
                    current["mask"] = m.group(1)

            elif re.search(r"Default Gateway", stripped, re.I):
                m = re.search(r"(\d+\.\d+\.\d+\.\d+)", stripped)
                if m:
                    current["gateway"] = m.group(1)
                collecting_dns = False

            elif re.search(r"DNS Servers", stripped, re.I):
                m = re.search(r"(\d+\.\d+\.\d+\.\d+)", stripped)
                if m:
                    current["dns"].append(m.group(1))
                collecting_dns = True

            elif collecting_dns and re.match(r"^\d+\.\d+\.\d+\.\d+", stripped):
                current["dns"].append(stripped.split()[0])

            elif re.search(r"Physical Address", stripped, re.I):
                m = re.search(r"([0-9A-F]{2}-){5}[0-9A-F]{2}", stripped, re.I)
                if m:
                    current["mac"] = m.group(0)
                collecting_dns = False

            elif re.search(r"DHCP Enabled", stripped, re.I):
                current["dhcp_enabled"] = "yes" in stripped.lower()
                collecting_dns = False

        if current and current.get("ip") and current["ip"] != _NA:
            adapters.append(current)

    except Exception as exc:
        log.error(f"ipconfig parse error: {exc}")

    return adapters


def _empty_adapter(name: str) -> dict:
    return {
        "name": name,
        "adapter_index": -1,
        "ip": _NA,
        "mask": _NA,
        "gateway": _NA,
        "dns": [],
        "mac": _NA,
        "dhcp_enabled": False,
        "dhcp_server": _NA,
        "status": "متصل",
        "connection_type": _NA,
        "description": name,
    }


# ── أسماء المحولات لأوامر netsh ──────────────────────────────────────────


def get_adapter_names() -> list[str]:
    """يرجع أسماء المحولات الشغّالة المناسبة لأوامر netsh."""
    names = []
    c = _wmi()
    if c:
        try:
            for nic in c.Win32_NetworkAdapter(NetEnabled=True):
                if nic.NetConnectionID:
                    names.append(nic.NetConnectionID)
            return names
        except Exception:
            pass

    # بديل عن طريق netsh
    try:
        _, out, _ = run_command("netsh interface show interface", timeout=10)
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 4 and "connected" in parts[1].lower():
                names.append(" ".join(parts[3:]))
    except Exception as exc:
        log.warning(f"netsh adapter names: {exc}")

    return names


def get_adapter_netsh_name(wmi_description: str) -> str:
    """
    يحوّل اسم WMI إلى NetConnectionID اللي يستخدمه netsh.
    يرجع الاسم كما هو لو فشل التحويل.
    """
    c = _wmi()
    if c:
        try:
            for nic in c.Win32_NetworkAdapter(NetEnabled=True):
                if (nic.Name or "").lower() == wmi_description.lower():
                    return nic.NetConnectionID or wmi_description
        except Exception:
            pass
    return wmi_description


# ── دوال مساعدة ──────────────────────────────────────────────────────────


def _is_ipv4(addr: str) -> bool:
    return bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}$", addr or ""))


def _fmt_mac(mac: str) -> str:
    if not mac:
        return _NA
    return mac.replace(":", "-").upper()


def _guess_connection_type(description: str) -> str:
    desc = description.lower()
    if any(k in desc for k in ("wi-fi", "wireless", "wlan", "802.11")):
        return "Wi-Fi"
    if any(k in desc for k in ("ethernet", "gigabit", "realtek", "intel", "broadcom")):
        return "Ethernet"
    if "loopback" in desc or "virtual" in desc:
        return "Virtual"
    return _NA


# ── ملخص المحوّل الأساسي ─────────────────────────────────────────────────


def get_primary_adapter() -> dict:
    """يرجع أول محوّل شغّال مو loopback، أو dict فارغ لو ما في."""
    adapters = get_all_adapters()
    for a in adapters:
        if a["ip"] not in (_NA, "127.0.0.1", ""):
            return a
    return _empty_adapter(_NA)
