"""
اكتشاف الأجهزة المتصلة — طابعات وUSB وتخزين ومنافذ شبكة وشاشات وغيرها.
نستخدم WMI ونرجع قائمة فارغة لو ما في صلاحيات.
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

from src.utils.logger import setup_logger

log = setup_logger(__name__)

_NA = "غير متاح"

# ترجمة كودات حالة أجهزة WMI للعربية
_STATUS_MAP = {
    "OK": "يعمل",
    "Error": "خطأ",
    "Unknown": "غير معروف",
    "Degraded": "متدهور",
    "Starting": "يبدأ",
    "Stopping": "يتوقف",
    "Service": "في الصيانة",
}


def _wmi():
    try:
        import wmi

        return wmi.WMI()
    except Exception as exc:
        log.warning(f"WMI unavailable: {exc}")
        return None


def _arabic_status(raw: str) -> str:
    return _STATUS_MAP.get(raw or "", raw or _NA)


# ── استعلامات كل فئة من الأجهزة ─────────────────────────────────────────


def _get_printers(c) -> list[dict]:
    devices = []
    try:
        for p in c.Win32_Printer():
            status_raw = "OK" if getattr(p, "WorkOffline", True) is False else "Unknown"
            devices.append(
                {
                    "name": p.Name or _NA,
                    "type": "طابعة",
                    "manufacturer": p.DriverName or _NA,
                    "status": _arabic_status(status_raw),
                    "device_id": p.DeviceID or _NA,
                    "connection": "شبكي" if (p.PortName or "").startswith("IP_") else "محلي",
                }
            )
    except Exception as exc:
        log.warning(f"Printer query error: {exc}")
    return devices


def _get_disk_drives(c) -> list[dict]:
    devices = []
    try:
        for d in c.Win32_DiskDrive():
            conn = "USB" if "usb" in (d.InterfaceType or "").lower() else (d.InterfaceType or _NA)
            devices.append(
                {
                    "name": d.Model or d.Caption or _NA,
                    "type": "وحدة تخزين",
                    "manufacturer": d.Manufacturer or _NA,
                    "status": _arabic_status(d.Status),
                    "device_id": d.DeviceID or _NA,
                    "connection": conn,
                }
            )
    except Exception as exc:
        log.warning(f"Disk query error: {exc}")
    return devices


def _get_network_adapters(c) -> list[dict]:
    devices = []
    try:
        for nic in c.Win32_NetworkAdapter():
            if not nic.Name:
                continue
            if "loopback" in (nic.Name or "").lower():
                continue
            conn = (
                "Wi-Fi"
                if any(k in (nic.Name or "").lower() for k in ("wireless", "wi-fi", "wlan"))
                else "شبكة"
            )
            devices.append(
                {
                    "name": nic.Name or _NA,
                    "type": "محول شبكة",
                    "manufacturer": nic.Manufacturer or _NA,
                    "status": "متصل" if nic.NetEnabled else "غير متصل",
                    "device_id": nic.DeviceID or _NA,
                    "connection": conn,
                }
            )
    except Exception as exc:
        log.warning(f"NIC query error: {exc}")
    return devices


def _get_monitors(c) -> list[dict]:
    devices = []
    try:
        for m in c.Win32_DesktopMonitor():
            if not m.Name:
                continue
            devices.append(
                {
                    "name": m.Name or _NA,
                    "type": "شاشة",
                    "manufacturer": m.MonitorManufacturer or _NA,
                    "status": _arabic_status(m.Status),
                    "device_id": m.DeviceID or _NA,
                    "connection": "محلي",
                }
            )
    except Exception as exc:
        log.warning(f"Monitor query error: {exc}")
    return devices


def _get_pnp_devices(c) -> list[dict]:
    """
    يجيب الأجهزة من Win32_PnPEntity — لوحة مفاتيح وفأرة وUSB وماسح ضوئي وغيرها.
    """
    devices = []
    # الفئات اللي نهتم فيها
    wanted_classes = {
        "Keyboard": "لوحة مفاتيح",
        "Mouse": "فأرة",
        "HIDClass": "جهاز HID",
        "Image": "ماسح ضوئي / كاميرا",
        "USB": "USB",
        "USBDevice": "جهاز USB",
        "USBHUB": "موزع USB",
        "Printer": "طابعة",
        "Scanner": "ماسح ضوئي",
        "Bluetooth": "بلوتوث",
        "Camera": "كاميرا",
        "AudioEndpoint": "صوت",
        "Media": "وسائط",
        "Net": "شبكة",
    }

    try:
        for dev in c.Win32_PnPEntity():
            pnp_class = getattr(dev, "PNPClass", "") or ""
            if pnp_class not in wanted_classes:
                continue
            if not dev.Name:
                continue
            # نتجاهل الفئات اللي أخذناها بالاستعلامات المخصصة
            if pnp_class in ("Printer", "Net"):
                continue

            devices.append(
                {
                    "name": dev.Name or _NA,
                    "type": wanted_classes.get(pnp_class, pnp_class),
                    "manufacturer": dev.Manufacturer or _NA,
                    "status": _arabic_status(dev.Status),
                    "device_id": dev.DeviceID or _NA,
                    "connection": _guess_pnp_connection(dev.DeviceID or ""),
                }
            )
    except Exception as exc:
        log.warning(f"PnP query error: {exc}")

    return devices


def _guess_pnp_connection(device_id: str) -> str:
    did = device_id.upper()
    if did.startswith("USB\\"):
        return "USB"
    if did.startswith("BTHENUM\\") or did.startswith("BTH\\"):
        return "بلوتوث"
    if did.startswith("HID\\"):
        return "HID"
    if did.startswith("PCI\\"):
        return "PCI"
    return "محلي"


# ── الدالة الرئيسية ───────────────────────────────────────────────────────


def get_connected_devices() -> list[dict]:
    """
    يرجع قائمة موحّدة لكل الأجهزة المتصلة.
    كل dict فيه: name, type, manufacturer, status, device_id, connection.
    ما يرمي exception أبداً — يرجع قائمة فارغة لو صار خطأ.
    """
    c = _wmi()
    if not c:
        return [
            {
                "name": "WMI غير متاح — تعذّر جلب قائمة الأجهزة",
                "type": _NA,
                "manufacturer": _NA,
                "status": _NA,
                "device_id": _NA,
                "connection": _NA,
            }
        ]

    all_devices: list[dict] = []

    all_devices.extend(_get_printers(c))
    all_devices.extend(_get_disk_drives(c))
    all_devices.extend(_get_network_adapters(c))
    all_devices.extend(_get_monitors(c))
    all_devices.extend(_get_pnp_devices(c))

    # نحذف المكررات حسب device_id
    seen: set[str] = set()
    unique: list[dict] = []
    for d in all_devices:
        key = d.get("device_id", d.get("name", ""))
        if key and key not in seen:
            seen.add(key)
            unique.append(d)

    log.info(f"Connected devices scan: {len(unique)} devices found")
    return unique
