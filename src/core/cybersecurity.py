"""
تقييم وضع الأمن السيبراني.
يجمع معلومات عن برامج الحماية المثبّتة ومزايا أمان ويندوز
ومعايير هيئة الأمن السيبراني السعودية (NCA ECC-1:2018).
كل العمليات قراءة فقط — ما نغيّر في النظام.
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

import winreg
from datetime import date

from src.utils.command_runner import run_powershell_json
from src.utils.lang import text as tx
from src.utils.logger import setup_logger

log = setup_logger(__name__)

# ── تصنيف برامج الأمن ────────────────────────────────────────────────────────
# كل مجموعة تحتوي كلمات مفتاحية للتعرف على نوع البرنامج
_CATEGORY_MAP = {
    "مكافح فيروسات": [
        "kaspersky",
        "norton",
        "mcafee",
        "bitdefender",
        "avast",
        "avg",
        "eset",
        "sophos",
        "trend micro",
        "malwarebytes",
        "webroot",
        "f-secure",
        "g data",
        "panda",
        "vipre",
        "comodo",
        "cylance",
        "crowdstrike falcon",
        "carbon black",
        "cybereason",
        "sentinel one",
        "sentinelone",
        "defender antivirus",
        "windows defender",
        "spybot",
        "adaware",
        "hitmanpro",
    ],
    "جدار حماية": [
        "zonealarm",
        "comodo firewall",
        "glasswire",
        "little snitch",
        "windows firewall",
        "checkpoint firewall",
        "cisco asa",
        "fortinet fortigate",
        "paloalto",
        "watchguard",
    ],
    "EDR / الكشف والاستجابة": [
        "crowdstrike",
        "falcon sensor",
        "sentinelone",
        "carbon black",
        "cybereason",
        "cylance",
        "darktrace",
        "vectra",
        "cortex xdr",
        "microsoft defender for endpoint",
        "microsoft 365 defender",
        "trend micro apex",
        "elastic security",
        "secureworks",
        "sophos intercept",
        "symantec edr",
    ],
    "DLP / منع تسرب البيانات": [
        "dlp",
        "data loss prevention",
        "data leak prevention",
        "symantec dlp",
        "forcepoint dlp",
        "digital guardian",
        "safetica",
        "teramind",
        "spirion",
        "nightfall",
        "microsoft purview",
        "microsoft information protection",
        "endpoint protector",
        "drivelock",
    ],
    "MDM / إدارة الأجهزة": [
        "intune",
        "microsoft intune",
        "jamf",
        "mobile device management",
        "mdm",
        "workspace one",
        "airwatch",
        "citrix endpoint",
        "ivanti",
        "baramundi",
        "matrix42",
        "soti mobicontrol",
        "vmware mdm",
        "cisco meraki mdm",
    ],
    "SIEM / مراقبة الأحداث": [
        "splunk",
        "qradar",
        "siem",
        "arcsight",
        "logrhythm",
        "microsoft sentinel",
        "elastic siem",
        "exabeam",
        "securonix",
        "sumologic",
        "graylog",
    ],
    "VPN / الشبكة الخاصة": [
        "vpn",
        "cisco anyconnect",
        "globalprotect",
        "pulse secure",
        "openvpn",
        "nordvpn",
        "expressvpn",
        "fortivpn",
        "checkpoint vpn",
        "sonicwall",
        "f5 vpn",
    ],
    "إدارة الهوية والوصول": [
        "cyberark",
        "beyondtrust",
        "thycotic",
        "privileged access",
        "duo security",
        "okta",
        "ping identity",
        "sailpoint",
        "saviynt",
        "centrify",
        "delinea",
    ],
    "أمن عام": [
        "antivirus",
        "anti-virus",
        "security",
        "protect",
        "malware",
        "endpoint",
        "firewall",
        "ransomware",
        "encrypt",
        "crypto",
        "certificate",
        "pki",
        "iam",
        "sso",
        "mfa",
        "2fa",
    ],
}

# قائمة موحّدة لمطابقة سريعة (اسم البرنامج → فئته)
_ALL_KEYWORDS: list[tuple[str, str]] = []
for _cat, _words in _CATEGORY_MAP.items():
    for _word in _words:
        _ALL_KEYWORDS.append((_word, _cat))


def _detect_category(name: str) -> str:
    """يحدد فئة البرنامج بناءً على اسمه."""
    lower = name.lower()
    # نبدأ من الفئات الأكثر تخصصاً أولاً
    priority = [
        "EDR / الكشف والاستجابة",
        "DLP / منع تسرب البيانات",
        "MDM / إدارة الأجهزة",
        "SIEM / مراقبة الأحداث",
        "VPN / الشبكة الخاصة",
        "إدارة الهوية والوصول",
        "جدار حماية",
        "مكافح فيروسات",
        "أمن عام",
    ]
    for cat in priority:
        for word in _CATEGORY_MAP[cat]:
            if word in lower:
                return cat
    return "أمن عام"


# ── مكافح فيروسات وجدار حماية (عن طريق WMI SecurityCenter2) ─────────────


def get_security_center_products() -> dict:
    """
    يسأل WMI SecurityCenter2 عن برامج الحماية المسجّلة.
    يرجع dict فيه ثلاث قوائم: antivirus, firewall, antispyware.
    """
    result = {"antivirus": [], "firewall": [], "antispyware": [], "query_ok": False}
    try:
        import wmi

        sc = wmi.WMI(namespace=r"root\SecurityCenter2")

        for av in sc.AntiVirusProduct():
            state = int(getattr(av, "productState", 0) or 0)
            enabled = ((state >> 12) & 0xF) == 1
            result["antivirus"].append(
                {
                    "name": av.displayName,
                    "enabled": enabled,
                    "status": "مفعّل" if enabled else "معطّل",
                }
            )

        result["query_ok"] = True
        for fw in sc.FirewallProduct():
            state = int(getattr(fw, "productState", 0) or 0)
            enabled = ((state >> 12) & 0xF) == 1
            result["firewall"].append(
                {
                    "name": fw.displayName,
                    "enabled": enabled,
                    "status": "مفعّل" if enabled else "معطّل",
                }
            )

        for asp in sc.AntiSpywareProduct():
            state = int(getattr(asp, "productState", 0) or 0)
            enabled = ((state >> 12) & 0xF) == 1
            result["antispyware"].append(
                {
                    "name": asp.displayName,
                    "enabled": enabled,
                    "status": "مفعّل" if enabled else "معطّل",
                }
            )
    except Exception as exc:
        log.warning(f"SecurityCenter2 query failed: {exc}")
    return result


# ── Windows Defender ──────────────────────────────────────────────────────


def get_defender_detail():
    result = dict(
        realtime=None, definitions="Unknown", last_scan="Unknown", enabled=None, query_ok=False
    )
    try:
        data = run_powershell_json(
            "Get-MpComputerStatus | Select-Object RealTimeProtectionEnabled,AntivirusSignatureLastUpdated,QuickScanEndTime | ConvertTo-Json -Compress"
        )
        if not isinstance(data, dict) or not isinstance(
            data.get("RealTimeProtectionEnabled"), bool
        ):
            raise ValueError("Invalid Defender status")
        result.update(
            realtime=data["RealTimeProtectionEnabled"],
            enabled=data["RealTimeProtectionEnabled"],
            definitions=str(data.get("AntivirusSignatureLastUpdated", "Unknown")),
            last_scan=str(data.get("QuickScanEndTime", "Unknown")),
            query_ok=True,
        )
    except Exception as exc:
        log.warning("Defender query failed: %s", exc)
    return result


def get_windows_firewall_status():
    profiles = {"domain": None, "private": None, "public": None}
    try:
        data = run_powershell_json(
            "Get-NetFirewallProfile -PolicyStore ActiveStore | Select-Object Name,@{Name='Enabled';Expression={[int]$_.Enabled}} | ConvertTo-Json -Compress",
            timeout=15,
        )
        rows = [data] if isinstance(data, dict) else data
        if not isinstance(rows, list):
            raise ValueError("Invalid firewall data")
        for row in rows:
            name = str(row.get("Name", "")).lower()
            value = row.get("Enabled")
            if name in profiles:
                # GpoBoolean: False=0, True=1, NotConfigured=2.
                profiles[name] = (
                    {0: False, 1: True}.get(value)
                    if type(value) is int
                    else (value if type(value) is bool else None)
                )
    except Exception as exc:
        log.warning("Firewall query failed: %s", exc)
    return profiles


def firewall_assessment(profiles):
    values = [profiles.get(name) for name in ("domain", "private", "public")]
    if any(value is False for value in values):
        return False
    if any(value is None for value in values):
        return None
    return True


def get_bitlocker_status():
    result = dict(
        enabled=None,
        status="Unknown",
        protection="Unknown",
        protection_enabled=None,
        encrypted=None,
        encryption_percentage=None,
        query_ok=False,
    )
    try:
        data = run_powershell_json(
            "Get-BitLockerVolume -MountPoint $env:SystemDrive | Select-Object @{Name='VolumeStatus';Expression={[int]$_.VolumeStatus}},@{Name='ProtectionStatus';Expression={[int]$_.ProtectionStatus}},EncryptionPercentage | ConvertTo-Json -Compress",
            timeout=15,
        )
        if not isinstance(data, dict):
            raise ValueError("Invalid BitLocker data")
        protection = data.get("ProtectionStatus")
        volume = data.get("VolumeStatus")
        percentage = data.get("EncryptionPercentage")
        if type(protection) is not int or type(volume) is not int:
            raise ValueError("Invalid BitLocker status types")
        result["protection_enabled"] = {0: False, 1: True}.get(protection)
        result["encrypted"] = {0: False, 1: True}.get(volume)
        result["status"] = {
            0: "FullyDecrypted",
            1: "FullyEncrypted",
            2: "EncryptionInProgress",
            3: "DecryptionInProgress",
            4: "EncryptionPaused",
            5: "DecryptionPaused",
        }.get(volume, "Unknown")
        result["encryption_percentage"] = (
            percentage if isinstance(percentage, (int, float)) and 0 <= percentage <= 100 else None
        )
        result["protection"] = {0: "Off", 1: "On"}.get(protection, "Unknown")
        if result["protection_enabled"] is False or volume in (0, 2, 3, 4, 5):
            result["enabled"] = False
        elif result["protection_enabled"] is True and volume == 1 and percentage == 100:
            result["enabled"] = True
        result["query_ok"] = True
    except Exception as exc:
        log.warning("BitLocker query failed: %s", exc)
    return result


def get_uac_status() -> dict:
    """يقرأ حالة UAC من السجل (Registry)."""
    result = {"enabled": None, "level": "Unknown"}
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
        )
        val, _ = winreg.QueryValueEx(key, "EnableLUA")
        winreg.CloseKey(key)
        result["enabled"] = bool(val)
        result["level"] = "مفعّل" if val else "معطّل"
    except Exception as exc:
        log.warning(f"UAC registry read error: {exc}")
    return result


# ── SmartScreen ───────────────────────────────────────────────────────────


def get_smartscreen_status() -> dict:
    """يقرأ حالة SmartScreen من السجل."""
    result = {"enabled": None, "level": "Unknown"}
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer",
        )
        val, _ = winreg.QueryValueEx(key, "SmartScreenEnabled")
        winreg.CloseKey(key)
        enabled = str(val).lower() not in ("off", "0", "")
        result["enabled"] = enabled
        result["level"] = str(val)
    except Exception as exc:
        log.warning(f"SmartScreen registry read error: {exc}")
    return result


# ── فحص سياسات كلمة المرور ───────────────────────────────────────────────


def get_password_policy():
    result = dict(min_length=None, max_age=None, complexity=None, ok=None)
    try:
        import win32net

        policy = win32net.NetUserModalsGet(None, 0)
        result.update(
            min_length=policy["min_passwd_len"],
            max_age=policy["max_passwd_age"],
            ok=policy["min_passwd_len"] >= 8,
        )
    except Exception as exc:
        log.warning("Local password policy query failed: %s", exc)
    return result


def get_windows_update_status(today=None, recent_days=35):
    """HotFix history heuristic; cannot prove no outstanding Windows updates."""
    result = dict(
        last_update="Unknown", has_updates=None, recent=None, age_days=None, ok=None, query_ok=False
    )
    try:
        data = run_powershell_json(
            "$items = @(Get-HotFix); $dated = @($items | Where-Object {$_.InstalledOn} | Sort-Object InstalledOn -Descending); [pscustomobject]@{Count=$items.Count; Date=if($dated.Count){$dated[0].InstalledOn.ToString('yyyy-MM-dd',[Globalization.CultureInfo]::InvariantCulture)}else{$null}} | ConvertTo-Json -Compress"
        )
        if not isinstance(data, dict) or type(data.get("Count")) is not int:
            raise ValueError("Invalid update history")
        result.update(query_ok=True, has_updates=data["Count"] > 0)
        if data.get("Date"):
            installed = date.fromisoformat(data["Date"])
            age = ((today or date.today()) - installed).days
            if age >= 0:
                result.update(
                    last_update=installed.isoformat(),
                    age_days=age,
                    recent=age <= recent_days,
                    ok=age <= recent_days,
                )
        elif data["Count"] == 0:
            result.update(recent=False, ok=False)
    except Exception as exc:
        log.warning("Update history query failed: %s", exc)
    return result


def get_audit_policy():
    result = dict(logon_audit=None, ok=None)
    try:
        import ctypes
        from ctypes import wintypes

        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        class AUDIT_POLICY_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("AuditSubCategoryGuid", GUID),
                ("AuditingInformation", wintypes.ULONG),
                ("AuditCategoryGuid", GUID),
            ]

        import uuid

        subcategory = GUID.from_buffer_copy(
            uuid.UUID("0cce9215-69ae-11d9-bed3-505054503030").bytes_le
        )
        ptr = ctypes.POINTER(AUDIT_POLICY_INFORMATION)()
        api = ctypes.WinDLL("advapi32", use_last_error=True)
        api.AuditQuerySystemPolicy.argtypes = [
            ctypes.POINTER(GUID),
            wintypes.ULONG,
            ctypes.POINTER(ctypes.POINTER(AUDIT_POLICY_INFORMATION)),
        ]
        api.AuditQuerySystemPolicy.restype = wintypes.BOOL
        api.AuditFree.argtypes = [ctypes.c_void_p]
        if not api.AuditQuerySystemPolicy(ctypes.byref(subcategory), 1, ctypes.byref(ptr)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            enabled = bool(ptr.contents.AuditingInformation & 3)
            result.update(logon_audit=enabled, ok=enabled)
        finally:
            api.AuditFree(ptr)
    except Exception as exc:
        log.warning("Logon audit query failed: %s", exc)
    return result


def get_rdp_status() -> dict:
    """يتحقق من حالة Remote Desktop."""
    result = {"enabled": None}
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Terminal Server",
        )
        val, _ = winreg.QueryValueEx(key, "fDenyTSConnections")
        winreg.CloseKey(key)
        # 0 = RDP مفعّل، 1 = RDP معطّل
        result["enabled"] = val == 0
    except Exception as exc:
        log.warning(f"RDP status error: {exc}")
    return result


# ── فحص تشفير الاتصالات (TLS) ────────────────────────────────────────────


def get_tls_status():
    result = dict(tls10_disabled=None, ssl3_disabled=None, ok=None)
    states = []
    for protocol, key in (("TLS 1.0", "tls10_disabled"), ("SSL 3.0", "ssl3_disabled")):
        role_states = []
        for role in ("Client", "Server"):
            try:
                path = (
                    "SYSTEM\\CurrentControlSet\\Control\\SecurityProviders\\SCHANNEL\\Protocols\\"
                    + protocol
                    + "\\"
                    + role
                )
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as k:
                    value, _ = winreg.QueryValueEx(k, "Enabled")
                role_states.append(value == 0)
            except OSError:
                role_states.append(None)  # Missing keys use OS defaults; no conclusion.
        state = False if False in role_states else (None if None in role_states else True)
        result[key] = state
        states.append(state)
    result["ok"] = False if False in states else (None if None in states else True)
    return result


def get_installed_security_software() -> list[dict]:
    """
    يبحث في مفاتيح Uninstall بالسجل عن أي برنامج أمني.
    يرجع قائمة dicts فيها: name, publisher, version, install_date, category.
    """
    found: list[dict] = []
    seen: set[str] = set()

    # كلمات المطابقة الموحّدة من كل الفئات
    all_words = [word for words in _CATEGORY_MAP.values() for word in words]

    reg_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    for hive, path in reg_paths:
        try:
            key = winreg.OpenKey(hive, path)
            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    sub_name = winreg.EnumKey(key, i)
                    sub_key = winreg.OpenKey(key, sub_name)

                    def _get(name: str, default: str = "") -> str:
                        try:
                            return winreg.QueryValueEx(sub_key, name)[0] or default
                        except Exception:
                            return default

                    display_name = _get("DisplayName")
                    if not display_name:
                        winreg.CloseKey(sub_key)
                        continue

                    name_lower = display_name.lower()
                    if any(w in name_lower for w in all_words):
                        uid = display_name.strip().lower()
                        if uid not in seen:
                            seen.add(uid)
                            found.append(
                                {
                                    "name": display_name,
                                    "publisher": _get("Publisher"),
                                    "version": _get("DisplayVersion"),
                                    "install_date": _get("InstallDate"),
                                    "category": _detect_category(display_name),
                                }
                            )
                    winreg.CloseKey(sub_key)
                except Exception:
                    continue
            winreg.CloseKey(key)
        except Exception:
            continue

    return sorted(found, key=lambda x: (x["category"], x["name"].lower()))


# ── قائمة التحقق من معايير NCA ECC-1:2018 ────────────────────────────────


def get_nca_compliance(snapshot=None):
    """Local indicators only; no certification or validation of ECC control IDs."""
    data = snapshot or {}

    def get(key, fn):
        return data[key] if key in data else fn()

    sc = get("security_center", get_security_center_products)
    fw = get("firewall", get_windows_firewall_status)
    bl = get("bitlocker", get_bitlocker_status)
    wd = get("defender", get_defender_detail)
    uac = get("uac", get_uac_status)
    ss = get("smartscreen", get_smartscreen_status)
    wu = get("updates", get_windows_update_status)
    pw = get_password_policy()
    audit = get_audit_policy()
    rdp = get_rdp_status()
    tls = get_tls_status()
    from src.utils.admin_check import is_admin

    av = any(p["enabled"] for p in sc["antivirus"]) if sc.get("query_ok") else None
    items = [
        (
            tx("مكافح فيروسات فعّال", "Active antivirus"),
            av,
            tx(
                "حالة مسجّلة؛ لا يثبت حداثة التعريفات.",
                "Registered status; does not prove current definitions.",
            ),
        ),
        (
            tx("جدار الحماية لجميع ملفات الشبكة", "Firewall on all network profiles"),
            firewall_assessment(fw),
            tx("يشمل Domain وPrivate وPublic.", "Includes Domain, Private and Public."),
        ),
        (tx("التحكم بحسابات المستخدمين (UAC)", "User Account Control (UAC)"), uac["enabled"], ""),
        (
            tx("تشفير وحماية قرص النظام", "System drive encryption and protection"),
            bl["enabled"],
            tx(
                "يتطلب تشفيرًا كاملًا وحماية مفعّلة.",
                "Requires full encryption and active protection.",
            ),
        ),
        (
            tx("حماية Defender الفورية", "Defender real-time protection"),
            wd["realtime"],
            tx(
                "قد تستخدم المؤسسة برنامج حماية آخر.",
                "An organisation may use another antivirus product.",
            ),
        ),
        ("Windows SmartScreen", ss["enabled"], ""),
        (
            tx("صلاحيات العملية الحالية", "Current process privilege"),
            not is_admin(),
            tx(
                "لا يقيّم صلاحيات الحساب أو جلساته الأخرى.",
                "Does not assess account permissions or other sessions.",
            ),
        ),
        (
            tx("الحد الأدنى لطول كلمة المرور المحلية", "Local minimum password length"),
            pw["ok"],
            tx(
                "لا يتحقق من التعقيد أو سياسة الدومين.",
                "Does not verify complexity or domain policy.",
            ),
        ),
        (
            tx("حداثة سجل تحديثات ويندوز", "Recency of Windows update history"),
            wu["ok"],
            tx(
                "عتبة إرشادية 35 يومًا؛ لا يثبت خلو الجهاز من تحديثات معلقة. ",
                "35-day heuristic; does not prove there are no pending updates. ",
            )
            + str(wu["last_update"]),
        ),
        (tx("تدقيق تسجيل الدخول", "Logon auditing"), audit["ok"], ""),
        (
            tx("RDP معطّل", "RDP disabled"),
            None if rdp["enabled"] is None else not rdp["enabled"],
            tx(
                "تفعيل RDP لا يثبت أنه غير محمي؛ لا يُفحص VPN أو NLA.",
                "Enabled RDP does not prove insecurity; VPN and NLA are not assessed.",
            ),
        ),
        (
            tx("تعطيل TLS 1.0 وSSL 3.0 صراحة", "Explicit TLS 1.0 and SSL 3.0 disablement"),
            tls["ok"],
            tx(
                "قيم السجل فقط؛ القيم الغائبة تعتمد على افتراضات إصدار ويندوز.",
                "Registry only; absent values depend on Windows version defaults.",
            ),
        ),
    ]
    return [
        dict(title=title, standard="Local indicator", passed=passed, note=note)
        for title, passed, note in items
    ]


def get_full_security_status():
    result = dict(
        security_center=get_security_center_products(),
        defender=get_defender_detail(),
        firewall=get_windows_firewall_status(),
        bitlocker=get_bitlocker_status(),
        uac=get_uac_status(),
        smartscreen=get_smartscreen_status(),
        installed=get_installed_security_software(),
        updates=get_windows_update_status(),
    )
    result["nca"] = get_nca_compliance(result)
    return result
