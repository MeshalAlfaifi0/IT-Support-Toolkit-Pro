"""عرض مواصفات الجهاز ونظام التشغيل والاستخدام الحالي للموارد.
المؤلف: Meshal Alfaifi."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from src.utils.formatters import fmt_bytes, fmt_pct
from src.utils.logger import setup_logger
from src.utils.ui_text import QGroupBox, QLabel, QPushButton
from src.utils.workers import ManagedThread as QThread

log = setup_logger(__name__)

_NA = "غير متاح"


# ── Background worker ─────────────────────────────────────────────────────


class DeviceInfoWorker(QThread):
    data_ready = Signal(dict)

    def run(self):
        try:
            from src.core import system_info
            from src.core.domain_info import get_domain_info
            from src.core.network_info import get_primary_adapter

            data = {
                "cpu": system_info.get_cpu_info(),
                "ram": system_info.get_ram_info(),
                "disks": system_info.get_disk_info(),
                "os": system_info.get_os_info(),
                "av": system_info.get_antivirus_status(),
                "network": get_primary_adapter(),
                "domain": get_domain_info(),
            }
            self.data_ready.emit(data)
        except Exception as exc:
            log.error(f"DeviceInfoWorker error: {exc}")
            self.data_ready.emit({})


# ── Info row widget ───────────────────────────────────────────────────────


class InfoRow(QWidget):
    """صف معلومة بتنسيق: [تسمية] [قيمة]"""

    def __init__(self, label: str, value: str = _NA, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        lbl = QLabel(label)
        lbl.setFixedWidth(170)
        lbl.setStyleSheet("color: #5c6370; font-size: 12px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(lbl)

        self._val = QLabel(value)
        self._val.setStyleSheet("color: #dcdfe4; font-size: 12px; font-weight: bold;")
        self._val.setWordWrap(True)
        layout.addWidget(self._val, stretch=1)

    def set_value(self, value: str, color: str = "#dcdfe4"):
        self._val.setText(value)
        self._val.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")


# ── Device Info Page ──────────────────────────────────────────────────────


class DeviceInfoPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: DeviceInfoWorker | None = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # ── رأس الصفحة ───────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("معلومات الجهاز")
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
        self._refresh_btn.clicked.connect(self._load_data)
        header.addWidget(self._refresh_btn)
        root.addLayout(header)

        self._status_lbl = QLabel("جارٍ تحميل معلومات الجهاز…")
        self._status_lbl.setStyleSheet("color: #5c6370; font-size: 12px;")
        root.addWidget(self._status_lbl)

        # ── منطقة القراءة القابلة للتمرير ───────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

        grid = QGridLayout(content)
        grid.setSpacing(14)
        grid.setContentsMargins(0, 0, 12, 0)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── مجموعة: هوية الجهاز ──────────────────────────────────
        identity_grp = self._make_group("🖥  هوية الجهاز")
        ig_lay = QVBoxLayout(identity_grp)

        self._r_computer = InfoRow("اسم الكمبيوتر:")
        self._r_user = InfoRow("المستخدم الحالي:")
        self._r_os = InfoRow("نظام التشغيل:")
        self._r_manufacturer = InfoRow("الشركة المصنّعة:")
        self._r_model = InfoRow("الموديل:")
        self._r_bios = InfoRow("الرقم التسلسلي (BIOS):")
        self._r_domain_stat = InfoRow("حالة المجال:")

        for row in (
            self._r_computer,
            self._r_user,
            self._r_os,
            self._r_manufacturer,
            self._r_model,
            self._r_bios,
            self._r_domain_stat,
        ):
            ig_lay.addWidget(row)

        grid.addWidget(identity_grp, 0, 0)

        # ── مجموعة: المعالج ───────────────────────────────────────
        cpu_grp = self._make_group("⚡  المعالج (CPU)")
        cpu_lay = QVBoxLayout(cpu_grp)

        self._r_cpu_name = InfoRow("اسم المعالج:")
        self._r_cpu_cores = InfoRow("الأنوية:")
        self._r_cpu_freq = InfoRow("التردد:")
        self._r_cpu_usage = InfoRow("الاستخدام الحالي:")

        for row in (self._r_cpu_name, self._r_cpu_cores, self._r_cpu_freq, self._r_cpu_usage):
            cpu_lay.addWidget(row)

        grid.addWidget(cpu_grp, 0, 1)

        # ── مجموعة: الذاكرة RAM ───────────────────────────────────
        ram_grp = self._make_group("💾  الذاكرة العشوائية (RAM)")
        ram_lay = QVBoxLayout(ram_grp)

        self._r_ram_total = InfoRow("الإجمالي:")
        self._r_ram_used = InfoRow("المستخدم:")
        self._r_ram_free = InfoRow("المتاح:")
        self._r_ram_pct = InfoRow("نسبة الاستخدام:")

        for row in (self._r_ram_total, self._r_ram_used, self._r_ram_free, self._r_ram_pct):
            ram_lay.addWidget(row)

        grid.addWidget(ram_grp, 1, 0)

        # ── مجموعة: القرص الصلب ──────────────────────────────────
        disk_grp = self._make_group("💿  القرص الصلب (C:)")
        disk_lay = QVBoxLayout(disk_grp)

        self._r_disk_total = InfoRow("الحجم الكلي:")
        self._r_disk_used = InfoRow("المستخدم:")
        self._r_disk_free = InfoRow("المساحة المتبقية:")
        self._r_disk_pct = InfoRow("نسبة الاستخدام:")

        for row in (self._r_disk_total, self._r_disk_used, self._r_disk_free, self._r_disk_pct):
            disk_lay.addWidget(row)

        grid.addWidget(disk_grp, 1, 1)

        # ── مجموعة: الشبكة ───────────────────────────────────────
        net_grp = self._make_group("🌐  الشبكة")
        net_lay = QVBoxLayout(net_grp)

        self._r_net_adapter = InfoRow("محول الشبكة:")
        self._r_net_ip = InfoRow("عنوان IP:")
        self._r_net_mask = InfoRow("قناع الشبكة:")
        self._r_net_gw = InfoRow("البوابة الافتراضية:")
        self._r_net_dns = InfoRow("خوادم DNS:")
        self._r_net_mac = InfoRow("عنوان MAC:")
        self._r_net_dhcp = InfoRow("نوع IP:")
        self._r_net_type = InfoRow("نوع الاتصال:")

        for row in (
            self._r_net_adapter,
            self._r_net_ip,
            self._r_net_mask,
            self._r_net_gw,
            self._r_net_dns,
            self._r_net_mac,
            self._r_net_dhcp,
            self._r_net_type,
        ):
            net_lay.addWidget(row)

        grid.addWidget(net_grp, 2, 0)

        # ── مجموعة: الحماية والتحديثات ───────────────────────────
        sec_grp = self._make_group("🛡  الحماية والتحديثات")
        sec_lay = QVBoxLayout(sec_grp)

        self._r_av_name = InfoRow("برنامج الحماية:")
        self._r_av_status = InfoRow("حالة الحماية:")

        for row in (self._r_av_name, self._r_av_status):
            sec_lay.addWidget(row)

        grid.addWidget(sec_grp, 2, 1)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

    # ── Group box factory ─────────────────────────────────────────────────

    def _make_group(self, title: str) -> QGroupBox:
        grp = QGroupBox(title)
        grp.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        return grp

    # ── Data loading ──────────────────────────────────────────────────────

    def _load_data(self):
        if self._worker and self._worker.isRunning():
            return
        self._status_lbl.setText("جارٍ تحديث المعلومات…")
        self._refresh_btn.setEnabled(False)
        self._worker = DeviceInfoWorker()
        self._worker.data_ready.connect(self._on_data_ready)
        self._worker.start()

    def _on_data_ready(self, data: dict):
        self._refresh_btn.setEnabled(True)
        if not data:
            self._status_lbl.setText("⚠ تعذّر تحميل معلومات الجهاز.")
            return

        from datetime import datetime

        self._status_lbl.setText(f"آخر تحديث: {datetime.now().strftime('%H:%M:%S')}")

        dom = data.get("domain", {})
        cpu = data.get("cpu", {})
        ram = data.get("ram", {})
        net = data.get("network", {})
        av = data.get("av", {})
        os_d = data.get("os", {})
        disks = data.get("disks", [])

        # ── هوية الجهاز ──────────────────────────────────────────
        self._r_computer.set_value(dom.get("computer_name", _NA))
        self._r_user.set_value(dom.get("username", _NA))
        self._r_os.set_value(dom.get("os_caption") or os_d.get("full", _NA))
        self._r_manufacturer.set_value(dom.get("manufacturer", _NA))
        self._r_model.set_value(dom.get("model", _NA))
        self._r_bios.set_value(dom.get("bios_serial", _NA))

        if dom.get("is_domain_joined"):
            self._r_domain_stat.set_value(f"منضم إلى المجال: {dom.get('domain', _NA)}", "#3fb950")
        else:
            self._r_domain_stat.set_value(f"مجموعة عمل: {dom.get('workgroup', _NA)}", "#e5c07b")

        # ── المعالج ───────────────────────────────────────────────
        self._r_cpu_name.set_value(cpu.get("name", _NA))
        self._r_cpu_cores.set_value(
            f"{cpu.get('physical_cores', '?')} فيزيائية / {cpu.get('logical_cores', '?')} منطقية"
        )
        freq = cpu.get("frequency_mhz", 0)
        self._r_cpu_freq.set_value(f"{freq} MHz" if freq else _NA)
        cpu_pct = cpu.get("usage_pct", 0)
        cpu_color = "#3fb950" if cpu_pct < 60 else ("#e5c07b" if cpu_pct < 85 else "#e06c75")
        self._r_cpu_usage.set_value(fmt_pct(cpu_pct), cpu_color)

        # ── الذاكرة ───────────────────────────────────────────────
        self._r_ram_total.set_value(fmt_bytes(ram.get("total", 0)))
        self._r_ram_used.set_value(fmt_bytes(ram.get("used", 0)))
        self._r_ram_free.set_value(fmt_bytes(ram.get("available", 0)))
        ram_pct = ram.get("usage_pct", 0)
        ram_color = "#3fb950" if ram_pct < 70 else ("#e5c07b" if ram_pct < 85 else "#e06c75")
        self._r_ram_pct.set_value(fmt_pct(ram_pct), ram_color)

        # ── القرص C ──────────────────────────────────────────────
        c_disk = next((d for d in disks if d.get("mountpoint", "").upper().startswith("C")), {})
        if c_disk:
            disk_pct = c_disk.get("usage_pct", 0)
            disk_color = "#3fb950" if disk_pct < 80 else ("#e5c07b" if disk_pct < 90 else "#e06c75")
            self._r_disk_total.set_value(fmt_bytes(c_disk.get("total", 0)))
            self._r_disk_used.set_value(fmt_bytes(c_disk.get("used", 0)))
            self._r_disk_free.set_value(fmt_bytes(c_disk.get("free", 0)))
            self._r_disk_pct.set_value(fmt_pct(disk_pct), disk_color)
        else:
            for r in (self._r_disk_total, self._r_disk_used, self._r_disk_free, self._r_disk_pct):
                r.set_value(_NA)

        # ── الشبكة ────────────────────────────────────────────────
        self._r_net_adapter.set_value(net.get("name", _NA))
        self._r_net_ip.set_value(net.get("ip", _NA), "#61afef")
        self._r_net_mask.set_value(net.get("mask", _NA))
        self._r_net_gw.set_value(net.get("gateway", _NA))
        dns_list = net.get("dns", [])
        self._r_net_dns.set_value(", ".join(dns_list) if dns_list else _NA)
        self._r_net_mac.set_value(net.get("mac", _NA))
        self._r_net_dhcp.set_value(
            "تلقائي (DHCP)" if net.get("dhcp_enabled") else "ثابت (Static)",
            "#3fb950" if net.get("dhcp_enabled") else "#e5c07b",
        )
        self._r_net_type.set_value(net.get("connection_type", _NA))

        # ── الحماية ───────────────────────────────────────────────
        self._r_av_name.set_value(av.get("name", _NA))
        av_enabled = av.get("enabled", False)
        self._r_av_status.set_value(
            "مفعّل ✓" if av_enabled else "غير مفعّل ✗", "#3fb950" if av_enabled else "#e06c75"
        )

    def on_show(self):
        self._load_data()
