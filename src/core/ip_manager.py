"""
إدارة إعدادات IP عن طريق netsh.
كل العمليات تحتاج صلاحيات Administrator وتتحقق من الإدخال أولاً.
كلمات المرور ما تُمرَّر هنا أبداً.
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

import ipaddress

from src.utils.admin_check import is_admin
from src.utils.command_runner import run_command
from src.utils.lang import text as tx
from src.utils.logger import setup_logger

log = setup_logger(__name__)

# رسائل الخطأ والنجاح بالعربية
_ERR_NOT_ADMIN = "هذه العملية تتطلب تشغيل البرنامج كمسؤول (Administrator)."
_ERR_INVALID_IP = "عنوان IP غير صحيح: {}"
_ERR_NO_ADAPTER = "لم يتم تحديد محول الشبكة."
_OK_DHCP = "تم تعيين الإعدادات التلقائية (DHCP) بنجاح للمحول: {}"
_OK_STATIC = "تم تعيين IP الثابت بنجاح للمحول: {}"


# ── التحقق من عنوان IP ────────────────────────────────────────────────────


def is_valid_ip(ip: str) -> bool:
    try:
        ipaddress.IPv4Address(ip)
        return True
    except (ValueError, TypeError):
        return False


def validate_static_params(ip, mask, gateway, dns1="", dns2=""):
    if not ip or not mask:
        return False, tx(
            "عنوان IPv4 وقناع الشبكة مطلوبان.", "IPv4 address and subnet mask are required."
        )
    for label, value in (
        ("IPv4", ip),
        ("Mask", mask),
        ("Gateway", gateway),
        ("DNS 1", dns1),
        ("DNS 2", dns2),
    ):
        if value and not is_valid_ip(value):
            return False, tx(
                "عنوان IPv4 غير صالح: ", "Invalid IPv4 address: "
            ) + label + " " + value
    try:
        if not mask.startswith(
            ("0.", "128.", "192.", "224.", "240.", "248.", "252.", "254.", "255.")
        ):
            raise ValueError()
        # Hostmask syntax is accepted by ipaddress, but the form expects a netmask.
        bits = int(ipaddress.IPv4Address(mask))
        inverse = (~bits) & 0xFFFFFFFF
        if inverse & (inverse + 1):
            raise ValueError()
        network = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
        if network.prefixlen == 0:
            raise ValueError()
    except ValueError:
        return False, tx(
            "قناع الشبكة يجب أن يحتوي بتات متجاورة؛ مثال: 255.255.255.0.",
            "Subnet mask must be contiguous; for example 255.255.255.0.",
        )

    def usable(value):
        addr = ipaddress.IPv4Address(value)
        return not (
            addr.is_unspecified or addr.is_multicast or addr.is_loopback or int(addr) == 0xFFFFFFFF
        )

    if not usable(ip) or (
        network.prefixlen < 31
        and ipaddress.IPv4Address(ip) in (network.network_address, network.broadcast_address)
    ):
        return False, tx(
            "اختر عنوان جهاز صالحًا، وليس عنوان الشبكة أو البث.",
            "Use a valid host address, not the network or broadcast address.",
        )
    if gateway:
        gw = ipaddress.IPv4Address(gateway)
        if (
            not usable(gateway)
            or gw not in network
            or gateway == ip
            or (
                network.prefixlen < 31
                and gw in (network.network_address, network.broadcast_address)
            )
        ):
            return False, tx(
                "البوابة يجب أن تكون جهازًا آخر ضمن الشبكة نفسها.",
                "Gateway must be a different host in the same subnet.",
            )
    if dns2 and not dns1:
        return False, tx(
            "أدخل DNS الأساسي قبل الاحتياطي.", "Enter primary DNS before secondary DNS."
        )
    if any(value and not usable(value) for value in (dns1, dns2)):
        return False, tx(
            "خادم DNS يجب أن يكون عنوان IPv4 لجهاز صالح.", "DNS must be a valid IPv4 host address."
        )
    if dns1 and dns1 == dns2:
        return False, tx(
            "خادما DNS الأساسي والاحتياطي متطابقان.", "Primary and secondary DNS are identical."
        )
    return True, ""


# ── تفعيل DHCP ───────────────────────────────────────────────────────────


def set_dhcp(adapter_name: str) -> tuple[bool, str]:
    """
    يضبط المحوّل على DHCP (تلقائي).

    adapter_name: اسم NetConnectionID مثل "Ethernet".
    يرجع: (نجح؟, رسالة بالعربية)
    """
    if not is_admin():
        return False, _ERR_NOT_ADMIN

    if not adapter_name or not adapter_name.strip():
        return False, _ERR_NO_ADAPTER

    name = adapter_name.strip()
    log.info(f"Setting DHCP on adapter: {name}")

    results = []
    overall_ok = True

    # نحرّر العنوان ثم نضبط DHCP
    cmds = [
        (
            ["netsh", "interface", "ipv4", "set", "address", f"name={name}", "source=dhcp"],
            "ضبط عنوان IP تلقائي",
        ),
        (
            ["netsh", "interface", "ipv4", "set", "dnsservers", f"name={name}", "source=dhcp"],
            "ضبط DNS تلقائي",
        ),
    ]

    for cmd, label in cmds:
        ok, stdout, stderr = run_command(cmd, timeout=30, shell=False)
        out = (stdout or stderr or "").strip()
        status = "تم" if ok else "فشل"
        results.append(f"[{status}] {label}: {out}" if out else f"[{status}] {label}")
        if not ok:
            overall_ok = False
        log.info(f"DHCP step '{label}': {status} — {out}")

    summary = "\n".join(results)
    if overall_ok:
        msg = _OK_DHCP.format(name) + "\n\n" + summary
    else:
        msg = f"حدث خطأ أثناء ضبط DHCP للمحول: {name}\n\n" + summary

    return overall_ok, msg


# ── ضبط IP ثابت ──────────────────────────────────────────────────────────


def set_static_ip(
    adapter_name: str,
    ip: str,
    mask: str,
    gateway: str,
    dns1: str = "",
    dns2: str = "",
) -> tuple[bool, str]:
    """
    يضبط المحوّل على IP ثابت.

    adapter_name: اسم NetConnectionID مثل "Ethernet".
    يرجع: (نجح؟, رسالة بالعربية)
    """
    if not is_admin():
        return False, _ERR_NOT_ADMIN

    if not adapter_name or not adapter_name.strip():
        return False, _ERR_NO_ADAPTER

    valid, err_msg = validate_static_params(ip, mask, gateway, dns1, dns2)
    if not valid:
        return False, err_msg

    name = adapter_name.strip()
    log.info(f"Setting static IP on adapter: {name} — {ip}/{mask} gw={gateway}")

    results = []
    overall_ok = True

    # نضبط IP والقناع والبوابة
    cmd_ip = [
        "netsh",
        "interface",
        "ipv4",
        "set",
        "address",
        f"name={name}",
        "source=static",
        f"address={ip}",
        f"mask={mask}",
        f"gateway={gateway or 'none'}",
    ]
    ok, stdout, stderr = run_command(cmd_ip, timeout=30, shell=False)
    out = (stdout or stderr or "").strip()
    status = "تم" if ok else "فشل"
    results.append(f"[{status}] ضبط IP: {out}" if out else f"[{status}] ضبط IP")
    if not ok:
        return False, tx(
            "فشل ضبط IP؛ لم يُغيّر DNS.\n", "IP configuration failed; DNS was not changed.\n"
        ) + out

    # DNS الأساسي
    if dns1 and is_valid_ip(dns1):
        cmd_dns1 = [
            "netsh",
            "interface",
            "ipv4",
            "set",
            "dnsservers",
            f"name={name}",
            "source=static",
            f"address={dns1}",
            "validate=no",
        ]
        ok, stdout, stderr = run_command(cmd_dns1, timeout=30, shell=False)
        out = (stdout or stderr or "").strip()
        status = "تم" if ok else "فشل"
        results.append(f"[{status}] DNS الأساسي: {out}" if out else f"[{status}] DNS الأساسي")
        if not ok:
            return False, tx(
                "تم ضبط IP، لكن فشل DNS الأساسي؛ لم يُعدّل DNS الاحتياطي.\n",
                "IP was applied, but primary DNS failed; secondary DNS was not changed.\n",
            ) + "\n".join(results)

    else:
        ok, stdout, stderr = run_command(
            ["netsh", "interface", "ipv4", "set", "dnsservers", f"name={name}", "source=dhcp"],
            timeout=30,
            shell=False,
        )
        results.append("DNS: DHCP" if ok else (stderr or stdout or "DNS DHCP failed"))
        overall_ok = overall_ok and ok

    # DNS الاحتياطي
    if dns2 and is_valid_ip(dns2):
        cmd_dns2 = [
            "netsh",
            "interface",
            "ipv4",
            "add",
            "dnsservers",
            f"name={name}",
            f"address={dns2}",
            "index=2",
            "validate=no",
        ]
        ok, stdout, stderr = run_command(cmd_dns2, timeout=30, shell=False)
        out = (stdout or stderr or "").strip()
        status = "تم" if ok else "فشل"
        results.append(f"[{status}] DNS الاحتياطي: {out}" if out else f"[{status}] DNS الاحتياطي")

        if not ok:
            overall_ok = False

    summary = "\n".join(results)
    if overall_ok:
        msg = (
            _OK_STATIC.format(name)
            + f"\n  IP: {ip}\n  القناع: {mask}\n  البوابة: {gateway}\n\n"
            + summary
        )
    else:
        msg = f"حدث خطأ أثناء ضبط IP الثابت للمحول: {name}\n\n" + summary

    return overall_ok, msg
