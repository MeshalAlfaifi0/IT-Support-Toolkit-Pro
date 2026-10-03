"""لوحة المعلومات المختصرة؛ تجمع النتائج في الخلفية وتحدّث البطاقات المرنة.
المؤلف: Meshal Alfaifi."""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from src.core import system_info
from src.utils.formatters import fmt_bytes, fmt_pct, health_score_color
from src.utils.logger import setup_logger
from src.utils.responsive_grid import ResponsiveGrid
from src.utils.ui_style import style_widget
from src.utils.ui_text import QLabel, QPushButton
from src.utils.workers import ManagedThread as QThread

log = setup_logger(__name__)

_NA = "غير متاح"


# ── Background worker ─────────────────────────────────────────────────────


class DashboardWorker(QThread):
    """يجمع بيانات النظام في خلفية التطبيق لتجنب تجميد الواجهة."""

    data_ready = Signal(dict)

    def run(self):
        try:
            from src.core.domain_info import get_domain_info
            from src.core.network_info import get_primary_adapter

            data = {
                "device_name": system_info.get_device_name(),
                "username": system_info.get_username(),
                "os": system_info.get_os_info(),
                "cpu": system_info.get_cpu_info(),
                "ram": system_info.get_ram_info(),
                "disks": system_info.get_disk_info(),
                "antivirus": system_info.get_antivirus_status(),
                "network_status": system_info.get_network_status(),
                "windows_update": system_info.get_windows_update_status(),
                "network_detail": get_primary_adapter(),
                "domain": get_domain_info(),
            }
            self.data_ready.emit(data)
        except Exception as exc:
            log.error(f"DashboardWorker error: {exc}")
            self.data_ready.emit({})


# ── Card widget ───────────────────────────────────────────────────────────


class InfoCard(QFrame):
    """بطاقة معلومة واحدة: عنوان + قيمة كبيرة + نص فرعي."""

    def __init__(self, title: str, small_value: bool = False, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(170, 110)
        style_widget(
            self,
            "InfoCard { background-color: #21262d; border: 1px solid #3d4451; "
            "border-radius: 10px; }",
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(3)

        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet(
            "color: #5c6370; font-size: 12px; font-weight: bold; background: transparent;"
        )
        self._title_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._title_lbl)

        font_size = 14 if small_value else 18
        self._value_lbl = QLabel("—")
        self._value_lbl.setFont(QFont("Segoe UI", font_size, QFont.Weight.Bold))
        self._value_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._value_lbl.setWordWrap(True)
        layout.addWidget(self._value_lbl)

        self._sub_lbl = QLabel("")
        self._sub_lbl.setStyleSheet("color: #5c6370; font-size: 12px; background: transparent;")
        self._sub_lbl.setWordWrap(True)
        layout.addWidget(self._sub_lbl)

        layout.addStretch()

    def set_value(self, value: str, color: str = "#abb2bf"):
        self._value_lbl.setText(value)
        font_size = self._value_lbl.font().pointSize()
        self._value_lbl.setStyleSheet(
            f"color: {color}; font-size: {font_size}px; font-weight: bold;"
        )

    def set_sub(self, text: str):
        self._sub_lbl.setText(text)

    def set_accent(self, color: str):
        """تغيير لون حدود البطاقة للتأكيد على حالتها."""
        style_widget(
            self,
            f"InfoCard {{ background-color: #21262d; border: 1px solid {color}; "
            "border-radius: 10px; }",
        )


# ── Dashboard page ────────────────────────────────────────────────────────


class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: DashboardWorker | None = None
        self._setup_ui()
        self._start_refresh()

    # ── UI layout ──────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # ── رأس الصفحة ───────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("لوحة التحكم")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #dcdfe4;")
        header.addWidget(title)
        header.addStretch()

        self._refresh_btn = QPushButton("↻  تحديث")
        self._refresh_btn.setFixedSize(120, 36)
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

        # ── منطقة التمرير ────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = ResponsiveGrid(max_columns=4, card_width=205)
        self._card_grid = content
        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

        grid = content.grid
        grid.setSpacing(12)
        grid.setContentsMargins(0, 0, 4, 0)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ────────────────────────────────────────────────────────
        # الصف الأول: هوية الجهاز
        # ────────────────────────────────────────────────────────
        self._card_device = InfoCard("اسم الجهاز")
        self._card_user = InfoCard("المستخدم الحالي")
        self._card_os = InfoCard("نظام التشغيل")
        self._card_manufacturer = InfoCard("الشركة المصنّعة / الموديل", small_value=True)

        # ────────────────────────────────────────────────────────
        # الصف الثاني: المعالج والذاكرة
        # ────────────────────────────────────────────────────────
        self._card_cpu_name = InfoCard("المعالج (CPU)", small_value=True)
        self._card_cpu_use = InfoCard("استخدام المعالج")
        self._card_ram_tot = InfoCard("إجمالي الذاكرة RAM")
        self._card_ram_use = InfoCard("استخدام الذاكرة")

        # ────────────────────────────────────────────────────────
        # الصف الثالث: القرص والشبكة
        # ────────────────────────────────────────────────────────
        self._card_disk = InfoCard("مساحة C المتبقية")
        self._card_network = InfoCard("حالة الشبكة")
        self._card_ip = InfoCard("عنوان IP", small_value=True)
        self._card_domain = InfoCard("المجال / مجموعة العمل", small_value=True)

        # ────────────────────────────────────────────────────────
        # الصف الرابع: الحماية والصحة
        # ────────────────────────────────────────────────────────
        self._card_av = InfoCard("برنامج الحماية", small_value=True)
        self._card_wu = InfoCard("Windows Update")
        self._card_dhcp = InfoCard("نوع IP")
        self._card_score = InfoCard("درجة صحة الجهاز")

        # ترتيب البطاقات في الشبكة 4×4
        all_cards = [
            # صف 1
            self._card_device,
            self._card_user,
            self._card_os,
            self._card_manufacturer,
            # صف 2
            self._card_cpu_name,
            self._card_cpu_use,
            self._card_ram_tot,
            self._card_ram_use,
            # صف 3
            self._card_disk,
            self._card_network,
            self._card_ip,
            self._card_domain,
            # صف 4
            self._card_av,
            self._card_wu,
            self._card_dhcp,
            self._card_score,
        ]
        content.set_cards(all_cards)

    # ── Data loading ───────────────────────────────────────────────────

    def _start_refresh(self):
        """تحميل البيانات فوراً ثم كل 30 ثانية."""
        self._load_data()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._load_data)
        self._timer.start(30_000)

    def _load_data(self):
        if self._worker and self._worker.isRunning():
            return
        self._status_lbl.setText("جارٍ التحديث…")
        self._refresh_btn.setEnabled(False)
        self._worker = DashboardWorker()
        self._worker.data_ready.connect(self._on_data_ready)
        self._worker.start()

    def _on_data_ready(self, data: dict):
        self._refresh_btn.setEnabled(True)
        if not data:
            self._status_lbl.setText("⚠ تعذّر تحميل معلومات الجهاز.")
            return

        from datetime import datetime

        self._status_lbl.setText(f"آخر تحديث: {datetime.now().strftime('%H:%M:%S')}")

        # ── الصف الأول: هوية الجهاز ──────────────────────────────
        dom = data.get("domain", {})

        self._card_device.set_value(
            dom.get("computer_name") or data.get("device_name", _NA), "#dcdfe4"
        )
        self._card_user.set_value(dom.get("username") or data.get("username", _NA), "#dcdfe4")

        os_info = data.get("os", {})
        os_caption = dom.get("os_caption") or os_info.get("full", _NA)
        self._card_os.set_value(os_info.get("release", "Win"), "#dcdfe4")
        self._card_os.set_sub(os_caption[:45])

        mfr = dom.get("manufacturer", _NA)
        model = dom.get("model", _NA)
        self._card_manufacturer.set_value(mfr, "#dcdfe4")
        self._card_manufacturer.set_sub(model)

        # ── الصف الثاني: المعالج والذاكرة ────────────────────────
        cpu = data.get("cpu", {})
        cpu_name = cpu.get("name", _NA)
        # اختصار الاسم إن كان طويلاً
        display_name = cpu_name[:24] if len(cpu_name) > 24 else cpu_name
        self._card_cpu_name.set_value(display_name, "#dcdfe4")
        self._card_cpu_name.set_sub(
            f"{cpu.get('physical_cores', '?')} نواة / {cpu.get('logical_cores', '?')} خيط"
        )

        cpu_pct = cpu.get("usage_pct", 0)
        cpu_color = "#3fb950" if cpu_pct < 60 else ("#e5c07b" if cpu_pct < 85 else "#e06c75")
        self._card_cpu_use.set_value(fmt_pct(cpu_pct), cpu_color)
        self._card_cpu_use.set_accent(cpu_color)

        ram = data.get("ram", {})
        self._card_ram_tot.set_value(fmt_bytes(ram.get("total", 0)), "#dcdfe4")

        ram_pct = ram.get("usage_pct", 0)
        ram_color = "#3fb950" if ram_pct < 70 else ("#e5c07b" if ram_pct < 85 else "#e06c75")
        self._card_ram_use.set_value(fmt_pct(ram_pct), ram_color)
        self._card_ram_use.set_sub(f"المتاح: {fmt_bytes(ram.get('available', 0))}")
        self._card_ram_use.set_accent(ram_color)

        # ── الصف الثالث: القرص والشبكة ────────────────────────────
        c_free_str = _NA
        c_free_color = "#abb2bf"
        for disk in data.get("disks", []):
            if disk.get("mountpoint", "").upper().startswith("C"):
                free_pct = 100 - disk.get("usage_pct", 0)
                c_free_str = fmt_bytes(disk.get("free", 0))
                c_free_color = (
                    "#3fb950" if free_pct > 20 else ("#e5c07b" if free_pct > 10 else "#e06c75")
                )
                self._card_disk.set_sub(f"{free_pct:.0f}% متاح")
                break
        self._card_disk.set_value(c_free_str, c_free_color)
        self._card_disk.set_accent(c_free_color)

        net_status = data.get("network_status", {})
        net_ok = net_status.get("connected", False)
        self._card_network.set_value(
            "متصل ✓" if net_ok else "غير متصل ✗", "#3fb950" if net_ok else "#e06c75"
        )
        self._card_network.set_accent("#3fb950" if net_ok else "#e06c75")

        net_detail = data.get("network_detail", {})
        ip = net_detail.get("ip", _NA)
        self._card_ip.set_value(ip, "#61afef")
        self._card_ip.set_sub(net_detail.get("connection_type", _NA))

        if dom.get("is_domain_joined"):
            domain_val = dom.get("domain", _NA)
            domain_color = "#3fb950"
            domain_sub = "منضم للمجال"
        else:
            domain_val = dom.get("workgroup", _NA)
            domain_color = "#e5c07b"
            domain_sub = "مجموعة عمل"
        self._card_domain.set_value(domain_val, domain_color)
        self._card_domain.set_sub(domain_sub)

        # ── الصف الرابع: الحماية والصحة ───────────────────────────
        av = data.get("antivirus", {})
        av_enabled = av.get("enabled", False)
        av_status = av.get("status", "Unknown")
        av_ar = "مفعّل ✓" if av_enabled else ("غير معروف" if av_status == "Unknown" else "معطّل ✗")
        av_color = "#3fb950" if av_enabled else ("#e5c07b" if av_status == "Unknown" else "#e06c75")
        self._card_av.set_value(av_ar, av_color)
        self._card_av.set_sub(av.get("name", ""))
        self._card_av.set_accent(av_color)

        wu = data.get("windows_update", {})
        wu_running = wu.get("service_status") == "Running"
        wu_ar = (
            "غير معروف"
            if wu.get("service_status") == "Unknown"
            else ("يعمل ✓" if wu_running else "متوقف ✗")
        )
        from src.utils.lang import text as tx

        self._card_wu.set_sub(
            tx("حالة الخدمة فقط؛ ليست حداثة التحديثات", "Service status only; not patch recency")
        )
        self._card_wu.set_value(wu_ar, "#3fb950" if wu_running else "#e5c07b")

        dhcp_on = net_detail.get("dhcp_enabled", True)
        self._card_dhcp.set_value(
            "تلقائي (DHCP)" if dhcp_on else "ثابت (Static)", "#3fb950" if dhcp_on else "#e5c07b"
        )
        self._card_dhcp.set_sub(net_detail.get("name", _NA)[:30])

        score = self._quick_score(data)
        color = health_score_color(score)
        self._card_score.set_value(f"{score}/100", color)
        from src.utils.lang import text as tx

        self._card_score.set_sub(
            tx("تقدير جزئي؛ راجع الفحص الكامل", "Partial estimate; see the full scan")
        )
        self._card_score.set_accent(color)

    # ── Health score estimate ──────────────────────────────────────────

    def _quick_score(self, data: dict) -> int:
        from src.core.health_score import calculate_health_score

        cpu = data.get("cpu", {})
        ram = data.get("ram", {})
        av = data.get("antivirus", {})
        net = data.get("network_status", {})
        wu = data.get("windows_update", {})

        c_free_pct = 0.0
        disk_known = False
        for disk in data.get("disks", []):
            if disk.get("mountpoint", "").upper().startswith("C"):
                disk_known = True
                c_free_pct = 100.0 - disk.get("usage_pct", 0)
                break

        result = calculate_health_score(
            cpu_pct=cpu.get("usage_pct", 0),
            ram_pct=ram.get("usage_pct", 0),
            ram_total_gb=ram.get("total_gb", 4),
            c_free_pct=c_free_pct,
            unavailable={"drivers"}
            | ({"disk"} if not disk_known else set())
            | ({"antivirus"} if av.get("status") == "Unknown" else set())
            | ({"windows_update"} if wu.get("service_status") == "Unknown" else set())
            | ({"cpu"} if not cpu.get("query_ok") else set())
            | ({"ram"} if not ram.get("query_ok") else set()),
            av_enabled=av.get("enabled", False),
            av_name=av.get("name", "Unknown"),
            wu_running=wu.get("service_status") == "Running",
            driver_errors=False,
            network_ok=net.get("connected", False),
        )
        return result["score"]

    def on_show(self):
        """تُستدعى من MainWindow عند تفعيل هذه الصفحة."""
        self._load_data()
