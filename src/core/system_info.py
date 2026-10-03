"""
جمع معلومات الجهاز — CPU وRAM والقرص ونظام التشغيل والحماية والشبكة.
نستخدم psutil و WMI (ويندوز فقط).
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

import os
import platform
import socket

import psutil

from src.utils.logger import setup_logger

log = setup_logger(__name__)


def _wmi_client():
    """يرجع WMI client، أو None لو WMI مو متاح."""
    try:
        import wmi

        return wmi.WMI()
    except Exception as exc:
        log.warning(f"WMI unavailable: {exc}")
        return None


# ── هوية الجهاز ───────────────────────────────────────────────────────────


def get_device_name() -> str:
    try:
        return socket.gethostname()
    except Exception:
        return "Unknown"


def get_username() -> str:
    try:
        return os.getlogin()
    except Exception:
        return os.environ.get("USERNAME", "Unknown")


# ── نظام التشغيل ──────────────────────────────────────────────────────────


def get_os_info() -> dict:
    try:
        return {
            "name": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "full": f"{platform.system()} {platform.release()}",
            "architecture": platform.architecture()[0],
        }
    except Exception as exc:
        log.error(f"OS info error: {exc}")
        return {
            "name": "Unknown",
            "release": "Unknown",
            "version": "Unknown",
            "full": "Unknown",
            "architecture": "Unknown",
        }


# ── المعالج CPU ───────────────────────────────────────────────────────────


def get_cpu_info() -> dict:
    result = {
        "name": "Unknown",
        "physical_cores": psutil.cpu_count(logical=False) or 0,
        "logical_cores": psutil.cpu_count(logical=True) or 0,
        "usage_pct": 0.0,
        "query_ok": False,
        "frequency_mhz": 0,
    }
    try:
        result["usage_pct"] = psutil.cpu_percent(interval=1)
        result["query_ok"] = True
        freq = psutil.cpu_freq()
        if freq:
            result["frequency_mhz"] = int(freq.current)

        wmi = _wmi_client()
        if wmi:
            for cpu in wmi.Win32_Processor():
                result["name"] = cpu.Name.strip()
                if not result["frequency_mhz"] and cpu.MaxClockSpeed:
                    result["frequency_mhz"] = int(cpu.MaxClockSpeed)
                break
    except Exception as exc:
        log.error(f"CPU info error: {exc}")
    return result


# ── الذاكرة RAM ───────────────────────────────────────────────────────────


def get_ram_info() -> dict:
    try:
        mem = psutil.virtual_memory()
        return {
            "query_ok": True,
            "total": mem.total,
            "used": mem.used,
            "available": mem.available,
            "usage_pct": mem.percent,
            "total_gb": round(mem.total / (1024**3), 1),
        }
    except Exception as exc:
        log.error(f"RAM info error: {exc}")
        return {
            "query_ok": False,
            "total": 0,
            "used": 0,
            "available": 0,
            "usage_pct": 0.0,
            "total_gb": 0,
        }


# ── الأقراص ───────────────────────────────────────────────────────────────


def get_disk_info() -> list[dict]:
    disks = []
    try:
        for part in psutil.disk_partitions(all=False):
            if not part.mountpoint:
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks.append(
                    {
                        "device": part.device,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "usage_pct": usage.percent,
                        "disk_type": _guess_disk_type(part.device),
                    }
                )
            except (PermissionError, OSError):
                continue
    except Exception as exc:
        log.error(f"Disk info error: {exc}")
    return disks


def _guess_disk_type(device: str) -> str:
    """يحاول يعرف هل القرص SSD أو HDD عن طريق WMI."""
    try:
        import wmi

        c = wmi.WMI()
        for disk in c.Win32_DiskDrive():
            caption = (disk.Caption or "").upper()
            media = (disk.MediaType or "").upper()
            if "SSD" in caption or "SOLID" in caption or "NVME" in caption:
                return "SSD"
            if "FIXED" in media or "HDD" in caption:
                return "HDD"
        return "Unknown"
    except Exception:
        return "Unknown"


# ── برنامج الحماية (Antivirus) ────────────────────────────────────────────


def get_antivirus_status() -> dict:
    """
    يسأل SecurityCenter2 عن برامج مكافحة الفيروسات.
    يرجع بيانات افتراضية لو WMI مو متاح.
    """
    try:
        import wmi

        sc = wmi.WMI(namespace=r"root\SecurityCenter2")
        products = sc.AntiVirusProduct()
        if products:
            av = products[0]
            # productState: البتات 12-15 تحدد هل الحماية الفورية شغّالة
            state = getattr(av, "productState", 0) or 0
            enabled = ((int(state) >> 12) & 0xF) == 1
            return {
                "name": av.displayName,
                "enabled": enabled,
                "status": "Enabled" if enabled else "Disabled",
            }
    except Exception as exc:
        log.warning(f"Antivirus check failed: {exc}")
    return {"name": "Unknown", "enabled": None, "status": "Unknown"}


# ── Windows Defender ──────────────────────────────────────────────────────


def get_defender_status() -> dict:
    """يسأل PowerShell عن حالة الحماية الفورية لـ Defender."""
    result = {"enabled": False, "status": "Unknown", "last_update": "Unknown"}
    try:
        from src.utils.command_runner import run_command

        ok, out, _ = run_command(
            "powershell -NoProfile -Command "
            '"Get-MpComputerStatus | Select-Object -Property '
            'RealTimeProtectionEnabled,AntivirusSignatureLastUpdated | ConvertTo-Csv -NoTypeInformation"',
            timeout=15,
        )
        if ok and out:
            lines = [line.strip().strip('"') for line in out.strip().splitlines()]
            if len(lines) >= 2:
                headers = [h.strip().strip('"') for h in lines[0].split(",")]
                values = [v.strip().strip('"') for v in lines[1].split(",")]
                data = dict(zip(headers, values))
                enabled = data.get("RealTimeProtectionEnabled", "False").lower() == "true"
                result["enabled"] = enabled
                result["status"] = "Enabled" if enabled else "Disabled"
                result["last_update"] = data.get("AntivirusSignatureLastUpdated", "Unknown")
    except Exception as exc:
        log.warning(f"Defender status error: {exc}")
    return result


# ── الاتصال بالإنترنت ─────────────────────────────────────────────────────


def get_network_status() -> dict:
    """يتحقق من الاتصال عن طريق الاتصال بـ DNS الخاص بـ Google."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect(("8.8.8.8", 53))
        sock.close()
        return {"connected": True, "status": "Connected"}
    except Exception:
        return {"connected": False, "status": "Disconnected"}


# ── أكثر البرامج استهلاكاً للـ CPU ──────────────────────────────────────────


def get_top_cpu_processes(limit: int = 5) -> list[dict]:
    items = []
    try:
        for proc in psutil.process_iter(["pid", "name", "cpu_percent"]):
            try:
                items.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        items.sort(key=lambda x: x.get("cpu_percent") or 0, reverse=True)
        return items[:limit]
    except Exception as exc:
        log.error(f"Top CPU processes error: {exc}")
    return items


# ── أكثر البرامج استهلاكاً للـ RAM ──────────────────────────────────────────


def get_top_ram_processes(limit: int = 5) -> list[dict]:
    items = []
    try:
        for proc in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                info = proc.info
                mem = info.get("memory_info")
                info["ram_mb"] = round(mem.rss / (1024**2), 1) if mem else 0
                items.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        items.sort(key=lambda x: x.get("ram_mb") or 0, reverse=True)
        return items[:limit]
    except Exception as exc:
        log.error(f"Top RAM processes error: {exc}")
    return items


# ── حالة خدمة Windows Update ─────────────────────────────────────────────


def get_windows_update_status() -> dict:
    result = {
        "service_status": "Unknown",
        "pending_updates": "Unknown",
        "note": "Service status only; pending updates and patch recency were not checked.",
    }
    try:
        import win32serviceutil

        svc_status = win32serviceutil.QueryServiceStatus("wuauserv")[1]
        # 4 = الخدمة شغّالة
        result["service_status"] = "Running" if svc_status == 4 else "Stopped"
    except Exception as exc:
        log.warning(f"Windows Update service check: {exc}")
    return result


# ── معلومات التعريفات ─────────────────────────────────────────────────────


def get_driver_info() -> list[dict]:
    """يرجع قائمة التعريفات الموقّعة ويشير لأي تعريف فيه مشكلة."""
    drivers = []
    try:
        import wmi

        c = wmi.WMI()
        for drv in c.Win32_PnPSignedDriver():
            if not drv.DeviceName:
                continue
            drivers.append(
                {
                    "name": drv.DeviceName or "Unknown",
                    "manufacturer": drv.Manufacturer or "Unknown",
                    "driver_version": drv.DriverVersion or "Unknown",
                    "status": "OK" if drv.IsSigned else "Unsigned",
                }
            )
        # نحدّد بـ 50 عشان ما تثقل الواجهة
        return drivers[:50]
    except Exception as exc:
        log.error(f"Driver info error: {exc}")
    return drivers


# ── تطبيقات بدء التشغيل ──────────────────────────────────────────────────


def get_startup_apps() -> list[dict]:
    """يقرأ التطبيقات اللي تشتغل مع الويندوز من HKLM و HKCU."""
    apps = []
    try:
        import winreg

        locations = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
        ]
        for hive, path in locations:
            try:
                key = winreg.OpenKey(hive, path)
                idx = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, idx)
                        apps.append({"name": name, "command": value})
                        idx += 1
                    except OSError:
                        break
                winreg.CloseKey(key)
            except Exception:
                continue
    except Exception as exc:
        log.error(f"Startup apps error: {exc}")
    return apps
