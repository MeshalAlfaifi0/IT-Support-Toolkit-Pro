"""واجهة إعدادات الشبكة؛ إدخال القيم والتحقق والتأكيد يسبق أي تغيير فعلي.
المؤلف: Meshal Alfaifi."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QRadioButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.database.init_db import log_action, log_network_change
from src.utils.admin_check import confirm_action, is_admin
from src.utils.logger import setup_logger
from src.utils.ui_text import (
    QComboBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
)
from src.utils.workers import ManagedThread as QThread

log = setup_logger(__name__)
_NA = "غير متاح"


# ── Workers ───────────────────────────────────────────────────────────────


class AdapterLoadWorker(QThread):
    """يجمع بيانات المحولات في خلفية التطبيق."""

    finished = Signal(list, list)  # (adapters_list, adapter_names_list)

    def run(self):
        try:
            from src.core.network_info import get_adapter_names, get_all_adapters

            adapters = get_all_adapters()
            names = get_adapter_names()
            self.finished.emit(adapters, names)
        except Exception as exc:
            log.error(f"AdapterLoadWorker: {exc}")
            self.finished.emit([], [])


class IPChangeWorker(QThread):
    """ينفذ تغيير IP في خلفية التطبيق."""

    finished = Signal(bool, str)

    def __init__(self, fn, *args):
        super().__init__()
        self._fn = fn
        self._args = args

    def run(self):
        try:
            ok, msg = self._fn(*self._args)
            self.finished.emit(ok, msg)
        except Exception as exc:
            self.finished.emit(False, str(exc))


# ── Network Page ──────────────────────────────────────────────────────────


class NetworkPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._adapters: list[dict] = []
        self._netsh_names: list[str] = []
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # ── رأس الصفحة ───────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("الشبكة وإدارة IP")
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
        self._refresh_btn.clicked.connect(self._load_adapters)
        header.addWidget(self._refresh_btn)
        root.addLayout(header)

        subtitle = QLabel(
            "عرض معلومات الشبكة وتغيير إعدادات IP. تغيير IP يتطلب تشغيل البرنامج كمسؤول 🔑"
        )
        subtitle.setStyleSheet("color: #5c6370; font-size: 12px;")
        root.addWidget(subtitle)

        # ── منقسم: جدول المحولات + لوح التحكم ───────────────────
        splitter = QSplitter(Qt.Orientation.Vertical)
        root.addWidget(splitter, stretch=1)

        # ── الجزء العلوي: جدول المحولات ─────────────────────────
        top = QWidget()
        top_lay = QVBoxLayout(top)
        top_lay.setContentsMargins(0, 0, 0, 0)
        top_lay.setSpacing(6)

        adapters_lbl = QLabel("محولات الشبكة المتاحة")
        adapters_lbl.setStyleSheet("color: #61afef; font-weight: bold; font-size: 13px;")
        top_lay.addWidget(adapters_lbl)

        self._table = QTableWidget(0, 8)
        self._table.setHorizontalHeaderLabels(
            [
                "المحول",
                "عنوان IP",
                "قناع الشبكة",
                "البوابة",
                "DNS",
                "MAC",
                "DHCP",
                "نوع الاتصال",
            ]
        )
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 8):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setMaximumHeight(200)
        self._table.currentCellChanged.connect(
            lambda row, col, pr, pc: self._on_adapter_selected(row)
        )
        top_lay.addWidget(self._table)
        splitter.addWidget(top)

        # ── الجزء السفلي: لوح تغيير IP ───────────────────────────
        bottom = QWidget()
        bot_lay = QHBoxLayout(bottom)
        bot_lay.setContentsMargins(0, 8, 0, 0)
        bot_lay.setSpacing(14)

        # ── يسار: نموذج الإعداد ───────────────────────────────────
        form_grp = QGroupBox("🔧  إعداد عنوان IP")
        form_grp.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        form_lay = QVBoxLayout(form_grp)
        form_lay.setSpacing(8)

        # اختيار المحول
        adapter_row = QHBoxLayout()
        adapter_row.addWidget(QLabel("المحول:"))
        self._adapter_combo = QComboBox()
        self._adapter_combo.setMinimumWidth(220)
        adapter_row.addWidget(self._adapter_combo, stretch=1)
        form_lay.addLayout(adapter_row)

        # خيار DHCP / Static
        mode_row = QHBoxLayout()
        self._radio_dhcp = QRadioButton("تلقائي (DHCP)")
        self._radio_static = QRadioButton("ثابت (Static)")
        self._radio_dhcp.setChecked(True)
        self._radio_group = QButtonGroup(self)
        self._radio_group.addButton(self._radio_dhcp)
        self._radio_group.addButton(self._radio_static)
        self._radio_dhcp.toggled.connect(self._toggle_static_fields)
        mode_row.addWidget(self._radio_dhcp)
        mode_row.addWidget(self._radio_static)
        mode_row.addStretch()
        form_lay.addLayout(mode_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #3d4451;")
        sep.setFixedHeight(1)
        form_lay.addWidget(sep)

        # حقول IP الثابت
        self._static_widget = QWidget()
        static_lay = QVBoxLayout(self._static_widget)
        static_lay.setContentsMargins(0, 0, 0, 0)
        static_lay.setSpacing(6)

        fields = [
            ("عنوان IP *:", "_f_ip"),
            ("قناع الشبكة *:", "_f_mask"),
            ("البوابة الافتراضية *:", "_f_gw"),
            ("DNS الأساسي:", "_f_dns1"),
            ("DNS الاحتياطي:", "_f_dns2"),
        ]
        for lbl_text, attr in fields:
            row = QHBoxLayout()
            lbl = QLabel(lbl_text)
            lbl.setFixedWidth(160)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            field = QLineEdit()
            field.setPlaceholderText("مثال: 192.168.1.x")
            field.setStyleSheet(
                "QLineEdit { background-color: #21262d; color: #dcdfe4; "
                "border: 1px solid #3d4451; border-radius: 4px; padding: 4px 8px; }"
                "QLineEdit:focus { border-color: #61afef; }"
            )
            row.addWidget(lbl)
            row.addWidget(field, stretch=1)
            setattr(self, attr, field)
            static_lay.addLayout(row)

        form_lay.addWidget(self._static_widget)

        # زر التطبيق
        self._apply_btn = QPushButton("🔑  تطبيق الإعدادات")
        self._apply_btn.setMinimumHeight(40)
        self._apply_btn.setStyleSheet(
            "QPushButton { background-color: #3fb950; color: #1e2128; "
            "border: none; border-radius: 8px; font-size: 14px; font-weight: bold; }"
            "QPushButton:hover { background-color: #58d068; }"
            "QPushButton:disabled { background-color: #3d4451; color: #5c6370; }"
        )
        self._apply_btn.clicked.connect(self._apply_settings)
        form_lay.addWidget(self._apply_btn)
        form_lay.addStretch()
        bot_lay.addWidget(form_grp, stretch=1)

        # ── يمين: منطقة الإخراج ──────────────────────────────────
        out_grp = QGroupBox("📋  النتائج والسجل")
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
        bot_lay.addWidget(out_grp, stretch=1)

        splitter.addWidget(bottom)
        splitter.setSizes([200, 400])

        # تعطيل حقول Static في البداية
        self._toggle_static_fields(True)

    # ── Toggle static fields ──────────────────────────────────────────────

    def _toggle_static_fields(self, dhcp_checked: bool):
        enabled = not dhcp_checked  # static fields active when DHCP NOT chosen
        self._static_widget.setEnabled(enabled)
        for attr in ("_f_ip", "_f_mask", "_f_gw", "_f_dns1", "_f_dns2"):
            getattr(self, attr).setEnabled(enabled)

    # ── Load adapters ─────────────────────────────────────────────────────

    def _load_adapters(self):
        self._refresh_btn.setEnabled(False)
        self._table.setRowCount(0)
        self._output.append("جارٍ تحميل معلومات المحولات…")

        worker = AdapterLoadWorker(self)
        worker.finished.connect(self._on_adapters_loaded)
        worker.start()
        self._worker = worker

    def _on_adapters_loaded(self, adapters: list, netsh_names: list):
        self._refresh_btn.setEnabled(True)
        self._adapters = adapters
        self._netsh_names = netsh_names

        self._table.setRowCount(0)
        self._adapter_combo.clear()

        if not adapters:
            self._output.append("⚠ لم يتم العثور على محولات شبكة نشطة.")
            return

        for a in adapters:
            row = self._table.rowCount()
            self._table.insertRow(row)

            dns_str = ", ".join(a.get("dns", [])) or _NA
            dhcp_str = "تلقائي" if a.get("dhcp_enabled") else "ثابت"
            dhcp_color = "#3fb950" if a.get("dhcp_enabled") else "#e5c07b"

            cols = [
                a.get("name", _NA),
                a.get("ip", _NA),
                a.get("mask", _NA),
                a.get("gateway", _NA),
                dns_str,
                a.get("mac", _NA),
                dhcp_str,
                a.get("connection_type", _NA),
            ]
            for c, val in enumerate(cols):
                item = QTableWidgetItem(str(val))
                if c == 6:
                    item.setForeground(QColor(dhcp_color))
                self._table.setItem(row, c, item)

        # ملء القائمة المنسدلة بأسماء netsh
        for name in netsh_names if netsh_names else [a.get("name", "") for a in adapters]:
            self._adapter_combo.addItem(name)

        self._output.append(f"✓ تم تحميل {len(adapters)} محول شبكة.")

    def _on_adapter_selected(self, row: int):
        if 0 <= row < len(self._adapters):
            a = self._adapters[row]
            # أعبئ الحقول بقيم المحول المختار تسهيلاً على المستخدم
            if not a.get("dhcp_enabled"):
                self._radio_static.setChecked(True)
                self._f_ip.setText(a.get("ip", ""))
                self._f_mask.setText(a.get("mask", ""))
                self._f_gw.setText(a.get("gateway", ""))
                dns = a.get("dns", [])
                self._f_dns1.setText(dns[0] if len(dns) > 0 else "")
                self._f_dns2.setText(dns[1] if len(dns) > 1 else "")
            else:
                self._radio_dhcp.setChecked(True)

            # حدد المحول في القائمة المنسدلة
            name = a.get("name", "")
            idx = self._adapter_combo.findText(name)
            if idx == -1 and self._netsh_names:
                idx = 0
            if idx >= 0:
                self._adapter_combo.setCurrentIndex(idx)

    # ── Apply settings ────────────────────────────────────────────────────

    def _apply_settings(self):
        adapter = self._adapter_combo.currentText().strip()
        if not adapter:
            self._output.append("⚠ يرجى اختيار محول الشبكة أولاً.")
            return

        if not is_admin():
            self._output.append("⚠ هذه العملية تتطلب تشغيل البرنامج كمسؤول (Administrator).")
            return

        if self._radio_dhcp.isChecked():
            self._apply_dhcp(adapter)
        else:
            self._apply_static(adapter)

    def _apply_dhcp(self, adapter: str):
        confirmed = confirm_action(
            f"هل تريد تعيين عنوان IP تلقائي (DHCP) للمحول:\n'{adapter}'؟\n\n"
            "سيتم فقدان أي إعدادات IP ثابتة حالية.",
        )
        if not confirmed:
            return

        self._output.append(f"\n► تعيين DHCP للمحول: {adapter}…")
        self._apply_btn.setEnabled(False)

        from src.core.ip_manager import set_dhcp

        worker = IPChangeWorker(set_dhcp, adapter)
        worker.finished.connect(lambda ok, msg: self._on_change_done(ok, msg, adapter, "dhcp"))
        worker.start()
        self._worker = worker

    def _apply_static(self, adapter: str):
        ip = self._f_ip.text().strip()
        mask = self._f_mask.text().strip()
        gw = self._f_gw.text().strip()
        dns1 = self._f_dns1.text().strip()
        dns2 = self._f_dns2.text().strip()

        from src.core.ip_manager import validate_static_params

        valid, err = validate_static_params(ip, mask, gw, dns1, dns2)
        if not valid:
            self._output.append(f"⚠ خطأ في المدخلات: {err}")
            return

        confirmed = confirm_action(
            f"هل تريد تعيين IP الثابت التالي للمحول '{adapter}'؟\n\n"
            f"  عنوان IP  : {ip}\n"
            f"  قناع الشبكة: {mask}\n"
            f"  البوابة    : {gw}\n"
            f"  DNS الأساسي: {dns1 or '—'}\n"
            f"  DNS الاحتياطي: {dns2 or '—'}\n\n"
            "⚠ قد ينقطع الاتصال مؤقتاً أثناء التطبيق.",
        )
        if not confirmed:
            return

        self._output.append(f"\n► تعيين IP الثابت للمحول: {adapter}…")
        self._apply_btn.setEnabled(False)

        from src.core.ip_manager import set_static_ip

        worker = IPChangeWorker(set_static_ip, adapter, ip, mask, gw, dns1, dns2)
        worker.finished.connect(
            lambda ok, msg: self._on_change_done(
                ok, msg, adapter, "static", ip=ip, mask=mask, gw=gw, dns1=dns1, dns2=dns2
            )
        )
        worker.start()
        self._worker = worker

    def _on_change_done(self, ok: bool, msg: str, adapter: str, change_type: str, **kwargs):
        self._apply_btn.setEnabled(True)
        self._output.append(msg)
        self._output.append(f"\n[{'نجح' if ok else 'فشل'}] {change_type.upper()} — {adapter}")

        status = "Success" if ok else "Failed"
        log_action(f"تغيير IP ({change_type})", status, msg)
        log_network_change(
            adapter_name=adapter,
            change_type=change_type,
            status=status,
            message=msg[:500],
            ip_address=kwargs.get("ip", ""),
            subnet_mask=kwargs.get("mask", ""),
            gateway=kwargs.get("gw", ""),
            dns_primary=kwargs.get("dns1", ""),
            dns_secondary=kwargs.get("dns2", ""),
        )

        if ok:
            self._load_adapters()

    def on_show(self):
        self._load_adapters()
