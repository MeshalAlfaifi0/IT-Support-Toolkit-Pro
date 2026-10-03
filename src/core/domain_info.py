"""
معلومات المجال ومجموعة العمل + الانضمام للمجال.
نستخدم WMI ومتغيرات البيئة و PowerShell.
كلمات المرور ما تُخزَّن أبداً ولا تُكتب في أي سجل.
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

import os
import socket

from src.utils.admin_check import is_admin
from src.utils.command_runner import run_command
from src.utils.logger import setup_logger

log = setup_logger(__name__)

_NA = "غير متاح"


# ── WMI helper ────────────────────────────────────────────────────────────


def _wmi():
    try:
        import wmi

        return wmi.WMI()
    except Exception as exc:
        log.warning(f"WMI unavailable: {exc}")
        return None


# ── معلومات المجال ────────────────────────────────────────────────────────


def get_domain_info() -> dict:
    """
    يرجع dict يحتوي:
        computer_name, username, domain, workgroup,
        is_domain_joined (bool), logon_server, user_domain,
        manufacturer, model, bios_serial, os_caption.
    يرجع لمتغيرات البيئة لو WMI ما اشتغل.
    """
    result = {
        "computer_name": socket.gethostname(),
        "username": os.environ.get("USERNAME", _NA),
        "domain": _NA,
        "workgroup": _NA,
        "is_domain_joined": False,
        "logon_server": os.environ.get("LOGONSERVER", _NA).lstrip("\\\\"),
        "user_domain": os.environ.get("USERDOMAIN", _NA),
        "manufacturer": _NA,
        "model": _NA,
        "bios_serial": _NA,
        "os_caption": _NA,
    }

    c = _wmi()
    if not c:
        # نستخدم متغيرات البيئة كبديل
        logon_srv = result["logon_server"]
        comp_name = result["computer_name"]
        if logon_srv and logon_srv.upper() != comp_name.upper():
            result["is_domain_joined"] = True
            result["domain"] = result["user_domain"]
        else:
            result["workgroup"] = result["user_domain"]
        return result

    # Win32_ComputerSystem — معلومات الجهاز والمجال
    try:
        for cs in c.Win32_ComputerSystem():
            result["computer_name"] = cs.Name or result["computer_name"]
            result["manufacturer"] = cs.Manufacturer or _NA
            result["model"] = cs.Model or _NA
            result["username"] = (cs.UserName or "").split("\\")[-1] or result["username"]

            domain_role = cs.DomainRole or 0
            # DomainRole: 0=ورك ستيشن مستقل، 1=عضو ورك ستيشن،
            #             2=سيرفر مستقل، 3=عضو سيرفر، 4/5=دومين كونترولر
            if domain_role in (1, 3, 4, 5):
                result["is_domain_joined"] = True
                result["domain"] = cs.Domain or _NA
                result["workgroup"] = _NA
            else:
                result["is_domain_joined"] = False
                result["workgroup"] = cs.Workgroup or cs.Domain or _NA
                result["domain"] = _NA
            break
    except Exception as exc:
        log.warning(f"Win32_ComputerSystem query error: {exc}")

    # Win32_BIOS — الرقم التسلسلي
    try:
        for bios in c.Win32_BIOS():
            result["bios_serial"] = bios.SerialNumber or _NA
            break
    except Exception as exc:
        log.warning(f"BIOS query error: {exc}")

    # Win32_OperatingSystem — اسم نظام التشغيل الكامل
    try:
        for os_obj in c.Win32_OperatingSystem():
            result["os_caption"] = os_obj.Caption or _NA
            break
    except Exception as exc:
        log.warning(f"OS query error: {exc}")

    return result


# ── الانضمام للمجال ───────────────────────────────────────────────────────


def join_domain(
    domain_name: str,
    username: str,
    password: str,
    ou_path: str = "",
) -> tuple[bool, str]:
    """
    يحاول ينضم الجهاز لمجال domain_name.

    الأمان:
      - كلمة المرور تُمرَّر كـ SecureString في PowerShell
        وما تُكتب في أي سجل أو قاعدة بيانات أبداً.
      - اللي يُحفظ فقط: اسم المجال، اسم المستخدم، الحالة، الرسالة المنقّحة.

    يرجع: (نجح؟, رسالة بالعربية)
    """
    if not is_admin():
        return False, "هذه العملية تتطلب تشغيل البرنامج كمسؤول (Administrator)."

    if not domain_name.strip():
        return False, "يرجى إدخال اسم المجال."
    if not username.strip():
        return False, "يرجى إدخال اسم المستخدم."
    if not password:
        return False, "يرجى إدخال كلمة المرور."

    import json

    from src.utils.lang import text as tx

    log.info("Domain join attempt")
    ps_script = """
    $ErrorActionPreference = 'Stop'
    $data = [Console]::In.ReadToEnd() | ConvertFrom-Json
    $pw = ConvertTo-SecureString $data.password -AsPlainText -Force
    $cred = [System.Management.Automation.PSCredential]::new($data.username, $pw)
    $params = @{DomainName=$data.domain; Credential=$cred; Force=$true; ErrorAction='Stop'}
    if ($data.ou) { $params.OUPath = $data.ou }
    try { Add-Computer @params | Out-Null; exit 0 }
    catch { exit 1 }
    finally { $data = $null; $cred = $null; if ($pw) { $pw.Dispose() } }
    """
    cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_script]
    payload = json.dumps(
        dict(
            domain=domain_name.strip(),
            username=username.strip(),
            password=password,
            ou=ou_path.strip(),
        ),
        ensure_ascii=True,
    )
    try:
        ok, _, error = run_command(
            cmd, timeout=120, shell=False, input_text=payload, sensitive=True
        )
        if ok:
            log.info("Domain join succeeded")
            return True, tx(
                "تم الانضمام إلى المجال بنجاح. يُوصى بإعادة تشغيل الجهاز.",
                "Domain joined successfully. Restart the computer to apply changes.",
            )
        log.warning("Domain join failed")
        if "timed out" in error:
            return False, tx(
                "انتهت مهلة الانضمام؛ تحقق من حالة المجال قبل المحاولة مجددًا.",
                "Domain join timed out; verify domain membership before retrying.",
            )
        return False, tx(
            "فشل الانضمام. تحقق من اسم المجال والصلاحيات والاتصال. أُخفيت تفاصيل الأمر لحماية بيانات الاعتماد.",
            "Domain join failed. Check the domain, permissions and connection. Command details are hidden to protect credentials.",
        )
    except Exception:
        log.error("Domain join exception (details suppressed)")
        return False, tx("تعذّر تنفيذ عملية الانضمام إلى المجال.", "Could not execute domain join.")
    finally:
        payload = ""
        password = ""  # Drop references; Python immutable strings cannot guarantee zeroisation.


def _escape_ps(value: str) -> str:
    return value.replace("'", "''")


def _sanitise_output(output: str, password: str) -> str:
    return output.replace(password, "***") if password else output
