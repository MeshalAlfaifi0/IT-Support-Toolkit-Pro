"""معلومات الدومين وطلب الانضمام؛ لا يُحفظ حقل كلمة المرور في السجلات.
المؤلف: Meshal Alfaifi."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget

from src.database.init_db import log_action, log_domain_action
from src.utils.admin_check import confirm_action, is_admin
from src.utils.logger import setup_logger
from src.utils.ui_text import QGroupBox, QLabel, QLineEdit, QMessageBox, QPushButton, QTextEdit
from src.utils.workers import ManagedThread as QThread

log = setup_logger(__name__)
_NA = "غير متاح"


# ── Workers ───────────────────────────────────────────────────────────────


class DomainInfoWorker(QThread):
    finished = Signal(dict)

    def run(self):
        try:
            from src.core.domain_info import get_domain_info

            self.finished.emit(get_domain_info())
        except Exception as exc:
            log.error(f"DomainInfoWorker: {exc}")
            self.finished.emit({})


class DomainJoinWorker(QThread):
    finished = Signal(bool, str)

    def __init__(self, domain: str, username: str, password: str, ou: str):
        super().__init__()
        self._domain = domain
        self._username = username
        self._password = password
        self._ou = ou

    def run(self):
        try:
            from src.core.domain_info import join_domain

            ok, msg = join_domain(self._domain, self._username, self._password, self._ou)
            self.finished.emit(ok, msg)
        except Exception:
            self.finished.emit(False, "Domain join failed; credential details suppressed.")
        finally:
            # مسح كلمة المرور من الذاكرة فور الانتهاء
            self._password = ""


# ── Info row widget ───────────────────────────────────────────────────────


class InfoRow(QHBoxLayout):
    def __init__(self, label: str, value: str = _NA):
        super().__init__()
        self.setSpacing(8)

        lbl = QLabel(label)
        lbl.setFixedWidth(180)
        lbl.setStyleSheet("color: #5c6370; font-size: 12px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.addWidget(lbl)

        self._val = QLabel(value)
        self._val.setStyleSheet("color: #dcdfe4; font-size: 12px; font-weight: bold;")
        self._val.setWordWrap(True)
        self.addWidget(self._val, stretch=1)

    def set_value(self, value: str, color: str = "#dcdfe4"):
        self._val.setText(value)
        self._val.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")


# ── Domain Page ───────────────────────────────────────────────────────────


class DomainPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._info_worker: DomainInfoWorker | None = None
        self._join_worker: DomainJoinWorker | None = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # ── رأس الصفحة ───────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("المجال والدومين")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #dcdfe4;")
        header.addWidget(title)
        header.addStretch()

        self._refresh_btn = QPushButton("↻  تحديث")
        self._refresh_btn.setFixedSize(110, 36)
        self._refresh_btn.setStyleSheet(
            "QPushButton { background-color: #282c34; color: #61afef; "
            "border: 1px solid #61afef; border-radius: 6px; font-size: 13px; }"
            "QPushButton:hover { background-color: #61afef; color: #1e2128; }"
        )
        self._refresh_btn.clicked.connect(self._load_info)
        header.addWidget(self._refresh_btn)
        root.addLayout(header)

        # ── مجموعة: معلومات المجال الحالية ───────────────────────
        info_grp = QGroupBox("ℹ  معلومات المجال الحالية")
        info_grp.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        info_lay = QVBoxLayout(info_grp)
        info_lay.setSpacing(6)

        self._r_computer = InfoRow("اسم الكمبيوتر:")
        self._r_user = InfoRow("اسم المستخدم الحالي:")
        self._r_status = InfoRow("حالة الانضمام:")
        self._r_domain = InfoRow("المجال الحالي:")
        self._r_workgroup = InfoRow("مجموعة العمل:")
        self._r_logon = InfoRow("خادم تسجيل الدخول:")
        self._r_userdomain = InfoRow("مجال المستخدم:")

        for row in (
            self._r_computer,
            self._r_user,
            self._r_status,
            self._r_domain,
            self._r_workgroup,
            self._r_logon,
            self._r_userdomain,
        ):
            info_lay.addLayout(row)

        self._info_status_lbl = QLabel("جارٍ التحميل…")
        self._info_status_lbl.setStyleSheet("color: #5c6370; font-size: 11px;")
        info_lay.addWidget(self._info_status_lbl)
        root.addWidget(info_grp)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #3d4451;")
        sep.setFixedHeight(1)
        root.addWidget(sep)

        # ── الجزء السفلي: نموذج الانضمام + إخراج ────────────────
        bottom_row = QHBoxLayout()
        root.addLayout(bottom_row, stretch=1)

        # ── يسار: نموذج الانضمام ─────────────────────────────────
        join_grp = QGroupBox("🔑  الانضمام إلى مجال (Domain Join)")
        join_grp.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        join_lay = QVBoxLayout(join_grp)
        join_lay.setSpacing(8)

        # تحذير الأمان
        warn_lbl = QLabel("⚠ هذه العملية تتطلب صلاحيات مسؤول وقد تتطلب إعادة تشغيل الجهاز.")
        warn_lbl.setStyleSheet(
            "color: #e5c07b; font-size: 12px; "
            "background-color: #2d2a1e; border: 1px solid #e5c07b; "
            "border-radius: 4px; padding: 6px;"
        )
        warn_lbl.setWordWrap(True)
        join_lay.addWidget(warn_lbl)

        # حقول الإدخال
        fields_data = [
            ("اسم المجال *:", "_j_domain", "مثال: company.local", False),
            ("اسم المستخدم *:", "_j_username", "مثال: admin أو domain\\admin", False),
            ("كلمة المرور *:", "_j_password", "كلمة مرور المسؤول", True),
            ("مسار OU (اختياري):", "_j_ou", "مثال: OU=PCs,DC=company,DC=local", False),
        ]
        for label_text, attr, placeholder, is_password in fields_data:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFixedWidth(165)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl.setStyleSheet("color: #abb2bf;")

            field = QLineEdit()
            field.setPlaceholderText(placeholder)
            if is_password:
                field.setEchoMode(QLineEdit.EchoMode.Password)
            field.setStyleSheet(
                "QLineEdit { background-color: #21262d; color: #dcdfe4; "
                "border: 1px solid #3d4451; border-radius: 4px; padding: 4px 8px; }"
                "QLineEdit:focus { border-color: #61afef; }"
            )
            setattr(self, attr, field)
            row.addWidget(lbl)
            row.addWidget(field, stretch=1)
            join_lay.addLayout(row)

        # زر الانضمام
        self._join_btn = QPushButton("🔑  إدخال الجهاز في المجال")
        self._join_btn.setMinimumHeight(42)
        self._join_btn.setStyleSheet(
            "QPushButton { background-color: #e06c75; color: #1e2128; "
            "border: none; border-radius: 8px; font-size: 14px; font-weight: bold; }"
            "QPushButton:hover { background-color: #ef8a90; }"
            "QPushButton:disabled { background-color: #3d4451; color: #5c6370; }"
        )
        self._join_btn.clicked.connect(self._start_join)
        join_lay.addWidget(self._join_btn)

        sec_note = QLabel("🔒 ملاحظة أمان: كلمة المرور لا تُخزَّن في أي سجل أو قاعدة بيانات.")
        sec_note.setStyleSheet("color: #5c6370; font-size: 11px;")
        sec_note.setWordWrap(True)
        join_lay.addWidget(sec_note)
        join_lay.addStretch()

        bottom_row.addWidget(join_grp, stretch=1)

        # ── يمين: منطقة الإخراج ──────────────────────────────────
        out_grp = QGroupBox("📋  النتائج")
        out_grp.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        out_lay = QVBoxLayout(out_grp)

        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setPlaceholderText("نتائج العمليات ستظهر هنا…")
        out_lay.addWidget(self._output)

        clear_btn = QPushButton("مسح")
        clear_btn.setFixedWidth(80)
        clear_btn.clicked.connect(self._output.clear)
        out_lay.addWidget(clear_btn, alignment=Qt.AlignmentFlag.AlignRight)

        bottom_row.addWidget(out_grp, stretch=1)

    # ── Load domain info ──────────────────────────────────────────────────

    def _load_info(self):
        self._refresh_btn.setEnabled(False)
        self._info_status_lbl.setText("جارٍ تحميل معلومات المجال…")

        self._info_worker = DomainInfoWorker(self)
        self._info_worker.finished.connect(self._on_info_ready)
        self._info_worker.start()

    def _on_info_ready(self, info: dict):
        self._refresh_btn.setEnabled(True)

        if not info:
            self._info_status_lbl.setText("⚠ تعذّر تحميل معلومات المجال.")
            return

        self._r_computer.set_value(info.get("computer_name", _NA))
        self._r_user.set_value(info.get("username", _NA))
        self._r_logon.set_value(info.get("logon_server", _NA))
        self._r_userdomain.set_value(info.get("user_domain", _NA))

        if info.get("is_domain_joined"):
            self._r_status.set_value("✓ منضم إلى مجال", "#3fb950")
            self._r_domain.set_value(info.get("domain", _NA), "#3fb950")
            self._r_workgroup.set_value("—")
        else:
            self._r_status.set_value("✗ غير منضم (مجموعة عمل)", "#e5c07b")
            self._r_domain.set_value("—")
            self._r_workgroup.set_value(info.get("workgroup", _NA), "#e5c07b")

        from datetime import datetime

        self._info_status_lbl.setText(f"آخر تحديث: {datetime.now().strftime('%H:%M:%S')}")

    # ── Domain join ───────────────────────────────────────────────────────

    def _start_join(self):
        if self._join_worker and self._join_worker.isRunning():
            return

        domain = self._j_domain.text().strip()
        username = self._j_username.text().strip()
        password = self._j_password.text()
        ou = self._j_ou.text().strip()

        # التحقق من المدخلات
        if not domain:
            self._output.append("⚠ يرجى إدخال اسم المجال.")
            return
        if not username:
            self._output.append("⚠ يرجى إدخال اسم المستخدم.")
            return
        if not password:
            self._output.append("⚠ يرجى إدخال كلمة المرور.")
            return

        if not is_admin():
            self._output.append(
                "⚠ هذه العملية تتطلب تشغيل البرنامج كمسؤول (Administrator).\n"
                "أغلق البرنامج وافتحه بـ 'تشغيل كمسؤول'."
            )
            return

        # تأكيد المستخدم
        confirmed = confirm_action(
            f"هل تريد إدخال هذا الجهاز في المجال:\n\n"
            f"  المجال   : {domain}\n"
            f"  المستخدم : {username}\n"
            f"  مسار OU  : {ou or '(افتراضي)'}\n\n"
            "⚠ هذه العملية تتطلب صلاحيات مسؤول وقد تتطلب إعادة تشغيل الجهاز.\n"
            "هل تريد المتابعة؟"
        )
        if not confirmed:
            self._output.append("تم إلغاء العملية.")
            return

        self._output.append(
            f"\n► جارٍ الانضمام إلى المجال '{domain}'…\n(قد تستغرق هذه العملية دقيقة أو أكثر)"
        )
        self._join_btn.setEnabled(False)

        self._join_worker = DomainJoinWorker(domain, username, password, ou)
        self._join_worker.finished.connect(
            lambda ok, msg: self._on_join_done(ok, msg, domain, username)
        )
        self._join_worker.start()

        # مسح كلمة المرور من حقل الإدخال فور الإرسال
        self._j_password.clear()

    def _on_join_done(self, ok: bool, msg: str, domain: str, username: str):
        self._join_btn.setEnabled(True)
        self._output.append(msg)

        status = "Success" if ok else "Failed"

        # تسجيل العملية بدون كلمة المرور
        log_action(f"انضمام إلى مجال: {domain}", status, msg[:500])
        log_domain_action(
            action_type="join_attempt",
            domain_name=domain,
            username="[redacted]",
            status=status,
            message=msg[:500],
        )

        if ok and not getattr(self.window(), "_closing", False):
            # اسأل عن إعادة التشغيل
            reply = QMessageBox.question(
                self,
                "نجاح — إعادة التشغيل",
                "تم الانضمام إلى المجال بنجاح.\n\n"
                "يُوصى بإعادة تشغيل الجهاز الآن لتطبيق التغييرات.\n\n"
                "هل تريد إعادة التشغيل الآن؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                import subprocess

                subprocess.Popen(
                    ["shutdown", "/r", "/t", "30", "/c", "إعادة تشغيل بعد الانضمام للمجال"]
                )
                self._output.append(
                    "\nتم جدولة إعادة التشغيل خلال 30 ثانية.\nلإلغاء: افتح CMD واكتب: shutdown /a"
                )
            else:
                self._output.append("\n⚠ تذكر إعادة تشغيل الجهاز لاحقاً لتطبيق الإعدادات.")
            # تحديث معلومات المجال
            self._load_info()

    def on_show(self):
        self._load_info()
