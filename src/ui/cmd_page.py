"""أوامر الدعم المقيدة؛ تنفيذ طويل في الخلفية مع إظهار النتيجة دون تجميد الواجهة.
المؤلف: Meshal Alfaifi."""

import subprocess

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.utils.logger import setup_logger
from src.utils.ui_text import QLabel, QPushButton, QTabWidget, QTextEdit
from src.utils.workers import ManagedThread as QThread

log = setup_logger(__name__)


# ── قاعدة الأوامر ──────────────────────────────────────────────────────────

CMD_CATEGORIES = {
    "🌐 الشبكة": [
        ("ipconfig /all", "عرض كامل تكوين الشبكة (IP / MAC / DNS / Gateway)"),
        ("ipconfig /release", "تحرير عنوان IP الحالي المخصص من DHCP"),
        ("ipconfig /renew", "طلب عنوان IP جديد من DHCP"),
        ("ipconfig /flushdns", "مسح ذاكرة التخزين المؤقت لـ DNS"),
        ("ping 8.8.8.8 -t", "اختبار الاتصال بـ Google DNS بشكل مستمر"),
        ("ping -n 4 google.com", "اختبار تحليل الأسماء والاتصال بالإنترنت"),
        ("tracert google.com", "تتبع مسار الحزم حتى الوجهة (Traceroute)"),
        ("nslookup google.com", "استعلام DNS عن اسم نطاق أو عنوان IP"),
        ("netstat -an", "عرض جميع الاتصالات النشطة والمنافذ المفتوحة"),
        ("netstat -b", "عرض البرامج المرتبطة بكل اتصال (يتطلب مسؤول)"),
        ("arp -a", "عرض جدول ARP (ربط IP بـ MAC)"),
        ("route print", "عرض جدول التوجيه الكامل"),
        ("netsh wlan show profiles", "عرض جميع شبكات Wi-Fi المحفوظة"),
        ("netsh wlan show interfaces", "حالة وإحصائيات محوّل Wi-Fi"),
        ("net view", "عرض الأجهزة المشاركة في الشبكة المحلية"),
        ("nbtstat -n", "عرض أسماء NetBIOS المسجّلة محلياً"),
        ("pathping 8.8.8.8", "تحليل تفصيلي لمسار الحزم ونسبة الفقدان"),
    ],
    "🖥 النظام": [
        ("systeminfo", "معلومات تفصيلية عن الجهاز ونظام التشغيل"),
        ("winver", "إصدار ويندوز (نافذة رسومية)"),
        ("msinfo32", "معلومات النظام الكاملة (نافذة رسومية)"),
        ("hostname", "اسم الجهاز الحالي"),
        ("whoami", "اسم المستخدم الحالي والنطاق"),
        ("whoami /groups", "مجموعات المستخدم وصلاحياته"),
        ("set", "عرض جميع متغيرات البيئة"),
        ("tasklist", "قائمة العمليات الجارية"),
        ("tasklist /svc", "العمليات مع الخدمات المرتبطة بها"),
        ("taskkill /IM notepad.exe /F", "إنهاء عملية بالاسم قسراً"),
        ("ver", "إصدار نظام التشغيل (سطر الأوامر)"),
        ("echo %computername%", "اسم الجهاز من متغير البيئة"),
        ("echo %username%", "اسم المستخدم الحالي"),
        ("echo %logonserver%", "اسم Domain Controller المستخدم للدخول"),
        ("wmic csproduct get name", "اسم موديل الجهاز من BIOS/UEFI"),
        ("wmic bios get serialnumber", "الرقم التسلسلي للجهاز من BIOS"),
        ("dxdiag", "أداة تشخيص DirectX (معلومات شاملة)"),
    ],
    "⚙ الخدمات": [
        ("net start", "قائمة الخدمات الشغّالة حالياً"),
        ("sc query", "حالة جميع الخدمات"),
        ("sc query Spooler", "حالة خدمة الطباعة (Print Spooler)"),
        ("net start Spooler", "تشغيل خدمة الطباعة"),
        ("net stop Spooler", "إيقاف خدمة الطباعة"),
        ("sc start wuauserv", "تشغيل خدمة Windows Update"),
        ("sc stop wuauserv", "إيقاف خدمة Windows Update"),
        ('net start "Remote Registry"', "تشغيل خدمة السجل البعيد"),
        ("services.msc", "فتح مدير الخدمات (نافذة رسومية)"),
        ("sc config Spooler start=auto", "ضبط خدمة تلقائية عند بدء التشغيل"),
        ("sc failure Spooler reset=60 actions=restart/60000", "إعادة تشغيل خدمة عند فشلها تلقائياً"),
    ],
    "💾 الأقراص والملفات": [
        ("chkdsk C: /f /r", "فحص وإصلاح أخطاء قرص C (يتطلب إعادة تشغيل)"),
        ("sfc /scannow", "فحص ملفات النظام وإصلاحها (يتطلب مسؤول)"),
        ("DISM /Online /Cleanup-Image /RestoreHealth", "إصلاح صورة ويندوز عبر Windows Update"),
        ("diskpart", "أداة إدارة الأقراص والأقسام (تفاعلي)"),
        ("diskmgmt.msc", "إدارة الأقراص (نافذة رسومية)"),
        ("dir C:\\", "قائمة محتويات جذر قرص C"),
        ("tree C:\\ /f", "شجرة المجلدات والملفات في C"),
        ('del /f /q "C:\\Temp\\*.*"', "حذف كل ملفات مجلد Temp قسراً"),
        ("robocopy C:\\src D:\\dst /MIR", "نسخ احتياطي كامل مع المزامنة"),
        ("wmic logicaldisk get name,size,freespace", "مساحة جميع الأقراص (فارغ ومستخدَم)"),
        ("fsutil volume diskfree C:", "مساحة قرص C المتاحة"),
        ("cleanmgr", "أداة تنظيف القرص (نافذة رسومية)"),
    ],
    "🔒 الأمان والمستخدمون": [
        ("net user", "قائمة جميع حسابات المستخدمين"),
        ("net user /domain", "قائمة حسابات النطاق"),
        ("net user ahmed /domain", "تفاصيل حساب مستخدم في النطاق"),
        ("net localgroup administrators", "أعضاء مجموعة المسؤولين المحليين"),
        ("net accounts", "سياسات كلمة المرور وإقفال الحساب"),
        ("gpupdate /force", "تطبيق Group Policy فوراً (يتطلب مسؤول)"),
        ("gpresult /r", "ملخص سياسات Group Policy المطبّقة"),
        ("gpresult /h gp_report.html", "تقرير HTML كامل لسياسات Group Policy"),
        ("auditpol /get /category:*", "عرض سياسات تدقيق الأحداث الأمنية"),
        ("secedit /analyze /db temp.sdb", "تحليل إعدادات الأمان مقارنة بالنموذج"),
        ("netsh advfirewall show allprofiles", "حالة جدار الحماية لجميع الـ profiles"),
        ("netsh advfirewall firewall show rule name=all", "قواعد جدار الحماية الكاملة"),
        ("cipher /u /n", "عرض الملفات المشفّرة بـ EFS"),
        ("manage-bde -status", "حالة BitLocker على جميع الأقراص"),
    ],
    "🖨 الطباعة": [
        ("net start Spooler", "تشغيل خدمة الطباعة"),
        ("net stop Spooler", "إيقاف خدمة الطباعة"),
        ("printmanagement.msc", "إدارة الطابعات (نافذة رسومية)"),
        ("wmic printer get name,status", "قائمة الطابعات وحالتها"),
        ("wmic printer where name='HP' call PrintTestPage", "طباعة صفحة اختبار لطابعة محددة"),
        (
            'del /Q /F /S "%systemroot%\\System32\\spool\\PRINTERS\\*"',
            "مسح طابور الطباعة يدوياً (الخدمة يجب أن تكون متوقفة)",
        ),
    ],
    "🔧 تشخيص متقدم": [
        ("msconfig", "إعداد بدء تشغيل ويندوز (نافذة رسومية)"),
        ("eventvwr", "عارض أحداث ويندوز (نافذة رسومية)"),
        ("perfmon", "مراقب الأداء (نافذة رسومية)"),
        ("resmon", "مراقب الموارد (CPU/RAM/Disk/Net)"),
        ("mdsched", "فحص ذاكرة RAM (يشتغل عند إعادة التشغيل)"),
        ("powercfg /batteryreport", "تقرير حالة البطارية (HTML)"),
        ("powercfg /energy", "تقرير استهلاك الطاقة"),
        ("netsh int tcp show global", "إعدادات TCP العامة للنظام"),
        ("wevtutil cl System", "مسح سجل النظام (يتطلب مسؤول)"),
        ("wevtutil cl Application", "مسح سجل التطبيقات"),
        ("logman query", "عرض جلسات تتبع الأداء النشطة"),
        ("wmic process list brief", "قائمة مختصرة لجميع العمليات الجارية"),
        ("driverquery", "قائمة برامج التشغيل المثبّتة"),
        ("driverquery /v /fo csv", "تقرير مفصّل بصيغة CSV لبرامج التشغيل"),
    ],
}


# ── Worker للتشغيل في الخلفية ─────────────────────────────────────────────


class CmdRunWorker(QThread):
    """يشغّل أمر CMD في thread منفصل."""

    done = Signal(str, str)  # (stdout, stderr)

    def __init__(self, command: str, parent=None):
        super().__init__(parent)
        self._command = command

    def run(self):
        from src.utils.command_runner import run_command_streaming

        lines = []
        if self._command.lower().startswith("del "):
            from src.core.windows_repair import clear_temp_files

            if "spool" in self._command.lower():
                self.done.emit("", "Use the printer page to clear jobs safely.")
            else:
                ok, output = clear_temp_files()
                self.done.emit(output if ok else "", "" if ok else output)
            return
        ok = run_command_streaming(self._command, lines.append, timeout=30)
        output = "\n".join(lines)
        self.done.emit(output if ok else "", "" if ok else output)


# ── بطاقة الأمر ──────────────────────────────────────────────────────────


class CmdCard(QFrame):
    """بطاقة تعرض أمراً واحداً مع زر نسخ وزر تشغيل."""

    def __init__(self, command: str, description: str, output_area: QTextEdit, parent=None):
        super().__init__(parent)
        self._command = command
        self._output_area = output_area
        self._worker: CmdRunWorker | None = None

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "CmdCard { background:#161b22; border:1px solid #21262d; border-radius:8px; }"
            "CmdCard:hover { border-color:#30363d; }"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(6)

        # ── وصف الأمر ────────────────────────────────────────────────
        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet("color:#8b949e; font-size:11px;")
        desc_lbl.setWordWrap(True)
        lay.addWidget(desc_lbl)

        # ── الأمر + الأزرار ───────────────────────────────────────────
        row = QHBoxLayout()
        cmd_lbl = QLabel(command)
        cmd_lbl.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        cmd_lbl.setStyleSheet("color:#79c0ff;")
        cmd_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        row.addWidget(cmd_lbl, stretch=1)

        copy_btn = QPushButton("📋")
        copy_btn.setFixedSize(32, 28)
        copy_btn.setToolTip("نسخ الأمر")
        copy_btn.setStyleSheet(
            "QPushButton{background:#21262d;border:1px solid #30363d;"
            "border-radius:6px;font-size:13px;}"
            "QPushButton:hover{background:#30363d;}"
        )
        copy_btn.clicked.connect(self._copy)
        row.addWidget(copy_btn)

        self._run_btn = QPushButton("▶ تشغيل")
        self._run_btn.setFixedSize(80, 28)
        self._run_btn.setStyleSheet(
            "QPushButton{background:#238636;color:#f0f6fc;"
            "border:none;border-radius:6px;font-size:11px;font-weight:bold;}"
            "QPushButton:hover{background:#2ea043;}"
            "QPushButton:disabled{background:#21262d;color:#484f58;}"
        )
        self._run_btn.clicked.connect(self._run)
        row.addWidget(self._run_btn)

        lay.addLayout(row)

    def _copy(self):
        QApplication.clipboard().setText(self._command)

    def _run(self):
        from src.utils.admin_check import confirm_action, is_admin, show_admin_warning

        lower = self._command.lower()
        mutating = (
            lower.startswith(
                (
                    "del ",
                    "net start ",
                    "net stop ",
                    "sc start ",
                    "sc stop ",
                    "sc config ",
                    "sc failure ",
                    "taskkill ",
                    "chkdsk ",
                    "sfc ",
                    "dism ",
                    "robocopy ",
                    "wevtutil cl ",
                    "gpupdate ",
                    "ipconfig /release",
                    "ipconfig /renew",
                    "ipconfig /flushdns",
                )
            )
            or "printtestpage" in lower
        )
        if mutating:
            if not lower.startswith(("del ", "ipconfig /flushdns")) and not is_admin():
                show_admin_warning(self)
                return
            from src.utils.lang import text as tx

            if not confirm_action(
                tx("سيُنفّذ إجراء يغيّر حالة الجهاز:\n", "This action changes device state:\n")
                + self._command,
                self,
            ):
                return
        # نتجنب تشغيل أوامر تفاعلية تفتح نوافذ أو تنتظر إدخال
        interactive = [
            "diskpart",
            "msconfig",
            "eventvwr",
            "perfmon",
            "resmon",
            "mdsched",
            "services.msc",
            "diskmgmt.msc",
            "printmanagement.msc",
            "msinfo32",
            "dxdiag",
            "gpresult /h",
            "winver",
            "cleanmgr",
        ]
        cmd_lower = self._command.lower()
        if any(k in cmd_lower for k in interactive):
            try:
                subprocess.Popen(self._command, shell=True)
            except Exception as exc:
                self._output_area.setPlainText(f"فشل التشغيل: {exc}")
            return

        if self._worker and self._worker.isRunning():
            return
        self._run_btn.setEnabled(False)
        self._run_btn.setText("⏳")
        self._output_area.setPlainText(f"⏳ جارٍ تنفيذ: {self._command}\n")

        self._worker = CmdRunWorker(self._command)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, stdout: str, stderr: str):
        self._run_btn.setEnabled(True)
        self._run_btn.setText("▶ تشغيل")
        output = stdout or stderr or "(لا يوجد إخراج)"
        self._output_area.setPlainText(f"$ {self._command}\n\n{output}")


# ── صفحة أوامر CMD ────────────────────────────────────────────────────────


class CmdPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # ── رأس الصفحة ────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("💻  أوامر CMD")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        hdr.addWidget(title)
        hdr.addStretch()
        root.addLayout(hdr)

        sub = QLabel("اضغط ▶ لتشغيل الأمر مباشرة أو 📋 لنسخه إلى الحافظة")
        sub.setStyleSheet("color:#8b949e; font-size:12px;")
        root.addWidget(sub)

        # ── التبويبات ─────────────────────────────────────────────────
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        root.addWidget(tabs, stretch=1)

        # ── منطقة الإخراج (مشتركة) ────────────────────────────────────
        out_grp_widget = QWidget()
        out_lay = QVBoxLayout(out_grp_widget)
        out_lay.setContentsMargins(0, 0, 0, 0)
        out_lay.setSpacing(4)

        out_hdr = QHBoxLayout()
        out_lbl = QLabel("نتيجة الأمر:")
        out_lbl.setStyleSheet("color:#8b949e; font-size:12px; font-weight:bold;")
        out_hdr.addWidget(out_lbl)
        out_hdr.addStretch()
        clear_btn = QPushButton("🗑 مسح")
        clear_btn.setFixedSize(80, 26)
        clear_btn.setStyleSheet(
            "QPushButton{background:#21262d;color:#8b949e;"
            "border:1px solid #30363d;border-radius:6px;font-size:11px;}"
            "QPushButton:hover{background:#30363d;color:#c9d1d9;}"
        )
        out_hdr.addWidget(clear_btn)
        out_lay.addLayout(out_hdr)

        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setFont(QFont("Consolas", 11))
        self._output.setMinimumHeight(140)
        self._output.setMaximumHeight(200)
        self._output.setPlaceholderText("نتيجة الأمر المشغَّل ستظهر هنا…")
        out_lay.addWidget(self._output)
        clear_btn.clicked.connect(self._output.clear)
        root.addWidget(out_grp_widget)

        # ── نبني تبويب لكل فئة ────────────────────────────────────────
        for cat_name, commands in CMD_CATEGORIES.items():
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)

            container = QWidget()
            grid = QGridLayout(container)
            grid.setContentsMargins(8, 8, 8, 8)
            grid.setSpacing(8)

            for idx, (cmd, desc) in enumerate(commands):
                card = CmdCard(cmd, desc, self._output)
                grid.addWidget(card, idx // 2, idx % 2)

            # نملأ العمود الأيمن لو الأوامر فردية العدد
            for c in range(2):
                grid.setColumnStretch(c, 1)
            grid.setRowStretch(grid.rowCount(), 1)

            scroll.setWidget(container)
            tabs.addTab(scroll, cat_name)

    def on_show(self):
        pass
