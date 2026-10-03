"""عرض التعريفات ومشكلاتها مع تصنيف وفلاتر قابلة للترجمة.
المؤلف: Meshal Alfaifi."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QHeaderView, QVBoxLayout, QWidget

from src.utils.logger import setup_logger
from src.utils.ui_text import QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem
from src.utils.workers import ManagedThread as QThread

log = setup_logger(__name__)


# ── رموز خطأ PnP الشائعة ─────────────────────────────────────────────────

_ERROR_CODES: dict[int, str] = {
    0: "يعمل بشكل صحيح",
    1: "غير مُهيَّأ بشكل صحيح",
    2: "فشل تحميل الـ Driver",
    3: "Driver تالف",
    10: "الجهاز لا يستطيع البدء",
    12: "لا تتوفر موارد كافية",
    14: "يتطلب إعادة التشغيل",
    16: "موارد غير معروفة",
    18: "يحتاج إعادة تثبيت",
    19: "خطأ في سجل النظام",
    21: "جارٍ الحذف",
    22: "معطّل من قِبَل المستخدم",
    24: "الجهاز غير موجود",
    28: "التعريفات غير مثبّتة",
    29: "معطّل — مشكلة في الـ BIOS",
    31: "لا يعمل بشكل صحيح",
    32: "خدمة الـ Driver معطّلة",
    33: "لا يستطيع تحديد الموارد",
    34: "يحتاج إعدادات يدوية",
    35: "لديه جهاز آخر يحمل نفس الإعدادات",
    36: "PCI Interrupt مطلوب",
    37: "لا يستطيع أن يعمل بالإعدادات الحالية",
    38: "Driver محمّل بالفعل",
    39: "Driver تالف أو مفقود",
    40: "لم تكتمل عملية الـ Driver",
    41: "ويندوز لم يتمكن من الوصول للجهاز",
    42: "Driver آخر محمّل بالفعل",
    43: "أوقفه ويندوز — خطأ في الجهاز",
    44: "تعارض في التطبيقات",
    45: "الجهاز غير متصل",
    46: "ويندوز لا يستطيع الوصول إليه",
    47: "تجاوز الجهاز حد تعيين الـ Windows",
    48: "الـ Driver ممنوع — مشكلة أمنية",
    49: "تجاوز حد أجهزة النظام",
    50: "لا يدعم الـ driver التحديثات الجديدة",
    52: "التوقيع الرقمي للـ Driver غير صحيح",
    54: "تعارض في الـ IRQ",
}

_STATUS_COLORS = {
    "يعمل بشكل صحيح": "#3fb950",
    "معطّل": "#d29922",
    "خطأ": "#f85149",
    "غير مثبّت": "#f85149",
    "تحذير": "#d29922",
}

_CLASS_AR: dict[str, str] = {
    "Display": "كرت الشاشة",
    "Net": "بطاقة الشبكة",
    "AudioEndpoint": "الصوت",
    "Media": "الوسائط",
    "Ports": "المنافذ",
    "USB": "USB",
    "Disk": "الأقراص",
    "DiskDrive": "الأقراص",
    "HDC": "تحكم القرص الصلب",
    "Keyboard": "لوحة المفاتيح",
    "Mouse": "الفأرة",
    "Bluetooth": "بلوتوث",
    "Camera": "الكاميرا",
    "Printer": "الطابعات",
    "Monitor": "الشاشة",
    "Battery": "البطارية",
    "System": "النظام",
    "Computer": "الحاسوب",
    "Processor": "المعالج",
    "Memory": "الذاكرة",
    "SecurityDevices": "الأمان",
    "SmartCardReader": "قارئ البطاقة",
    "Biometric": "البصمة",
    "HIDClass": "أجهزة HID",
    "SCSIAdapter": "SCSI",
    "Infrared": "الأشعة تحت الحمراء",
    "1394": "FireWire",
    "PCMCIA": "PCMCIA",
    "Sensor": "الاستشعار",
    "Firmware": "البرامج الثابتة",
}


# ── Worker ────────────────────────────────────────────────────────────────


class DriverWorker(QThread):
    """يجمع معلومات التعريفات في خلفية منفصلة."""

    done = Signal(list)

    def run(self):
        devices = []
        try:
            import wmi

            w = wmi.WMI()
            for dev in w.Win32_PnPEntity():
                try:
                    code = int(getattr(dev, "ConfigManagerErrorCode", 0) or 0)
                    name = getattr(dev, "Name", "") or ""
                    cls = getattr(dev, "PNPClass", "") or getattr(dev, "ClassGuid", "") or ""
                    if not name.strip():
                        continue

                    if code == 0:
                        status = "يعمل بشكل صحيح"
                        category = "ok"
                    elif code == 22:
                        status = "معطّل"
                        category = "disabled"
                    elif code in (28, 2, 3, 39):
                        status = "غير مثبّت"
                        category = "missing"
                    else:
                        status = "خطأ"
                        category = "error"

                    cls_ar = _CLASS_AR.get(cls, cls or "أخرى")

                    devices.append(
                        {
                            "name": name,
                            "class": cls_ar,
                            "status": status,
                            "category": category,
                            "code": code,
                            "detail": _ERROR_CODES.get(code, f"رمز خطأ {code}"),
                        }
                    )
                except Exception:
                    continue
        except Exception as exc:
            log.error(f"DriverWorker WMI error: {exc}")
            # fallback عبر PowerShell
            devices = self._ps_fallback()

        devices.sort(
            key=lambda d: (
                {"error": 0, "missing": 1, "disabled": 2, "ok": 3}.get(d["category"], 4),
                d["name"].lower(),
            )
        )
        self.done.emit(devices)

    def _ps_fallback(self) -> list[dict]:
        """بديل عبر PowerShell لو WMI ما شتغل."""
        results = []
        try:
            from src.utils.command_runner import run_command

            ok, out, _ = run_command(
                'powershell -NoProfile -Command "'
                "Get-PnpDevice | Select-Object FriendlyName,Status,Class,Problem "
                '| ConvertTo-Csv -NoTypeInformation"',
                timeout=30,
            )
            if ok and out:
                lines = out.strip().splitlines()
                if len(lines) >= 2:
                    for line in lines[1:]:
                        parts = [p.strip().strip('"') for p in line.split(",")]
                        if len(parts) < 4:
                            continue
                        name, status_raw, cls, _problem = parts[0], parts[1], parts[2], parts[3]
                        if not name:
                            continue
                        if status_raw.lower() == "ok":
                            status, category = "يعمل بشكل صحيح", "ok"
                        elif status_raw.lower() == "unknown":
                            status, category = "غير معروف", "warning"
                        else:
                            status, category = "خطأ", "error"
                        cls_ar = _CLASS_AR.get(cls, cls or "أخرى")
                        results.append(
                            {
                                "name": name,
                                "class": cls_ar,
                                "status": status,
                                "category": category,
                                "code": 0,
                                "detail": status_raw,
                            }
                        )
        except Exception as exc:
            log.error(f"PS fallback error: {exc}")
        return results


# ── بطاقة ملخص ───────────────────────────────────────────────────────────


class SummaryCard(QFrame):
    def __init__(self, title: str, color: str, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(160, 90)
        self.setStyleSheet(
            f"SummaryCard {{ background:#161b22; border:2px solid {color}; border-radius:10px; }}}}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)

        self._val = QLabel("—")
        self._val.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        self._val.setStyleSheet(f"color:{color}; border:none;")
        self._val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._val)

        lbl = QLabel(title)
        lbl.setStyleSheet("color:#8b949e; font-size:11px; font-weight:bold; border:none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)

    def set_value(self, v: int):
        self._val.setText(str(v))


# ── صفحة التعريفات ────────────────────────────────────────────────────────


class DriverPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: DriverWorker | None = None
        self._all_devices: list[dict] = []
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # ── رأس الصفحة ────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("🔧  تشخيص التعريفات")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        hdr.addWidget(title)
        hdr.addStretch()

        self._scan_btn = QPushButton("🔍  فحص التعريفات")
        self._scan_btn.setFixedSize(170, 38)
        self._scan_btn.setStyleSheet(
            "QPushButton{background:#1f6feb;color:#f0f6fc;"
            "border:none;border-radius:8px;font-size:13px;font-weight:bold;}"
            "QPushButton:hover{background:#388bfd;}"
            "QPushButton:disabled{background:#21262d;color:#484f58;}"
        )
        self._scan_btn.clicked.connect(self._run_scan)
        hdr.addWidget(self._scan_btn)
        root.addLayout(hdr)

        sub = QLabel("يكشف التعريفات المفقودة أو المعطوبة أو غير المثبّتة لجميع قطع الجهاز")
        sub.setStyleSheet("color:#8b949e; font-size:12px;")
        root.addWidget(sub)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color:#8b949e; font-size:12px;")
        root.addWidget(self._status_lbl)

        # ── بطاقات الملخص ─────────────────────────────────────────────
        cards_row = QHBoxLayout()
        self._card_total = SummaryCard("إجمالي الأجهزة", "#58a6ff")
        self._card_ok = SummaryCard("يعمل بشكل صحيح", "#3fb950")
        self._card_error = SummaryCard("أخطاء / مفقود", "#f85149")
        self._card_disabled = SummaryCard("معطّل", "#d29922")
        for c in [self._card_total, self._card_ok, self._card_error, self._card_disabled]:
            cards_row.addWidget(c)
        root.addLayout(cards_row)

        # ── شريط البحث والفلتر ────────────────────────────────────────
        filter_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  بحث باسم الجهاز أو الفئة…")
        self._search.textChanged.connect(self._filter_table)
        filter_row.addWidget(self._search, stretch=1)

        self._btn_all = self._filter_btn("الكل", None)
        self._btn_errors = self._filter_btn("الأخطاء فقط", "error")
        self._btn_missing = self._filter_btn("غير مثبّت", "missing")
        self._btn_disabled = self._filter_btn("معطّل", "disabled")
        for b in [self._btn_all, self._btn_errors, self._btn_missing, self._btn_disabled]:
            filter_row.addWidget(b)
        root.addLayout(filter_row)

        self._active_filter: str | None = None

        # ── الجدول ────────────────────────────────────────────────────
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["اسم الجهاز", "الفئة", "الحالة", "التفاصيل"])
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        root.addWidget(self._table, stretch=1)

    def _filter_btn(self, text: str, cat: str | None) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(30)
        btn.setCheckable(True)
        btn.setStyleSheet(
            "QPushButton{background:#21262d;color:#8b949e;"
            "border:1px solid #30363d;border-radius:6px;padding:0 12px;font-size:12px;}"
            "QPushButton:checked{background:#1f6feb;color:#f0f6fc;border-color:#1f6feb;}"
            "QPushButton:hover{background:#30363d;}"
        )
        btn.clicked.connect(lambda: self._set_filter(cat, btn))
        return btn

    def _set_filter(self, cat: str | None, btn: QPushButton):
        self._active_filter = cat
        for b in [self._btn_all, self._btn_errors, self._btn_missing, self._btn_disabled]:
            b.setChecked(b is btn)
        self._populate_table(self._all_devices)

    # ── الفحص ────────────────────────────────────────────────────────

    def _run_scan(self):
        if self._worker and self._worker.isRunning():
            return
        self._scan_btn.setEnabled(False)
        self._status_lbl.setText("⏳  جارٍ فحص التعريفات — قد يستغرق بضع ثوانٍ…")
        self._table.setRowCount(0)
        self._worker = DriverWorker()
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, devices: list[dict]):
        self._scan_btn.setEnabled(True)
        self._all_devices = devices
        from datetime import datetime

        self._status_lbl.setText(f"✅  آخر فحص: {datetime.now().strftime('%H:%M:%S')}")

        total = len(devices)
        ok = sum(1 for d in devices if d["category"] == "ok")
        errors = sum(1 for d in devices if d["category"] in ("error", "missing"))
        disabled = sum(1 for d in devices if d["category"] == "disabled")

        self._card_total.set_value(total)
        self._card_ok.set_value(ok)
        self._card_error.set_value(errors)
        self._card_disabled.set_value(disabled)

        self._populate_table(devices)

    def _populate_table(self, devices: list[dict]):
        search_text = self._search.text().lower()
        cat_filter = self._active_filter

        self._table.setRowCount(0)
        for dev in devices:
            if cat_filter and dev["category"] != cat_filter:
                continue
            if (
                search_text
                and search_text not in dev["name"].lower()
                and search_text not in dev["class"].lower()
            ):
                continue

            r = self._table.rowCount()
            self._table.insertRow(r)

            self._table.setItem(r, 0, QTableWidgetItem(dev["name"]))
            self._table.setItem(r, 1, QTableWidgetItem(dev["class"]))

            status_item = QTableWidgetItem(dev["status"])
            status_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            cat = dev["category"]
            if cat == "ok":
                status_item.setForeground(QColor("#3fb950"))
            elif cat == "disabled":
                status_item.setForeground(QColor("#d29922"))
            else:
                status_item.setForeground(QColor("#f85149"))
            self._table.setItem(r, 2, status_item)
            self._table.setItem(r, 3, QTableWidgetItem(dev["detail"]))

    def _filter_table(self):
        self._populate_table(self._all_devices)

    def on_show(self):
        if not self._all_devices:
            self._run_scan()
