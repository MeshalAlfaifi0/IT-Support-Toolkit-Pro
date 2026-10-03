"""عرض الأجهزة المتصلة وفرزها وتحديثها دون تغيير بيانات الجهاز.
المؤلف: Meshal Alfaifi."""

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QHBoxLayout, QHeaderView, QVBoxLayout, QWidget

from src.database.init_db import log_action
from src.utils.logger import setup_logger
from src.utils.ui_text import (
    QComboBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)
from src.utils.workers import ManagedThread as QThread

log = setup_logger(__name__)
_NA = "غير متاح"


# ── Background worker ─────────────────────────────────────────────────────


class DeviceScanWorker(QThread):
    finished = Signal(list)

    def run(self):
        try:
            from src.core.connected_devices import get_connected_devices

            devices = get_connected_devices()
            self.finished.emit(devices)
        except Exception as exc:
            log.error(f"DeviceScanWorker: {exc}")
            self.finished.emit([])


# ── Connected Devices Page ────────────────────────────────────────────────


class ConnectedDevicesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_devices: list[dict] = []
        self._worker: DeviceScanWorker | None = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # ── رأس الصفحة ───────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("الأجهزة المتصلة")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #dcdfe4;")
        header.addWidget(title)
        header.addStretch()

        self._scan_btn = QPushButton("↻  تحديث القائمة")
        self._scan_btn.setFixedSize(150, 36)
        self._scan_btn.setStyleSheet(
            "QPushButton { background-color: #282c34; color: #61afef; "
            "border: 1px solid #61afef; border-radius: 6px; font-size: 13px; }"
            "QPushButton:hover { background-color: #61afef; color: #1e2128; }"
        )
        self._scan_btn.clicked.connect(self._start_scan)
        header.addWidget(self._scan_btn)
        root.addLayout(header)

        subtitle = QLabel(
            "يعرض جميع الأجهزة المتصلة: طابعات، ماسحات، USB، شاشات، محولات الشبكة، وغيرها."
        )
        subtitle.setStyleSheet("color: #5c6370; font-size: 12px;")
        root.addWidget(subtitle)

        # ── شريط التصفية ─────────────────────────────────────────
        filter_row = QHBoxLayout()

        filter_lbl = QLabel("تصفية:")
        filter_lbl.setStyleSheet("color: #abb2bf;")
        filter_row.addWidget(filter_lbl)

        self._search_field = QLineEdit()
        self._search_field.setPlaceholderText("ابحث باسم الجهاز أو الشركة…")
        self._search_field.setStyleSheet(
            "QLineEdit { background-color: #21262d; color: #dcdfe4; "
            "border: 1px solid #3d4451; border-radius: 4px; padding: 4px 8px; }"
            "QLineEdit:focus { border-color: #61afef; }"
        )
        self._search_field.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self._search_field, stretch=1)

        type_lbl = QLabel("النوع:")
        type_lbl.setStyleSheet("color: #abb2bf;")
        filter_row.addWidget(type_lbl)

        self._type_combo = QComboBox()
        self._type_combo.addItem("الكل")
        self._type_combo.setMinimumWidth(150)
        self._type_combo.currentTextChanged.connect(self._apply_filter)
        filter_row.addWidget(self._type_combo)

        root.addLayout(filter_row)

        # ── إحصاءات ───────────────────────────────────────────────
        self._status_lbl = QLabel("اضغط 'تحديث القائمة' لبدء الفحص.")
        self._status_lbl.setStyleSheet("color: #5c6370; font-size: 12px;")
        root.addWidget(self._status_lbl)

        # ── جدول الأجهزة ──────────────────────────────────────────
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            [
                "اسم الجهاز",
                "النوع",
                "الشركة المصنّعة",
                "الحالة",
                "رقم الجهاز",
                "نوع الاتصال",
            ]
        )
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet("QTableWidget { alternate-background-color: #1e2128; }")
        root.addWidget(self._table, stretch=1)

    # ── Scan ──────────────────────────────────────────────────────────────

    def _start_scan(self):
        if self._worker and self._worker.isRunning():
            return
        self._scan_btn.setEnabled(False)
        self._scan_btn.setText("⏳  جارٍ الفحص…")
        self._status_lbl.setText("جارٍ فحص الأجهزة المتصلة…")
        self._table.setRowCount(0)

        self._worker = DeviceScanWorker(self)
        self._worker.finished.connect(self._on_scan_done)
        self._worker.start()

    def _on_scan_done(self, devices: list):
        self._scan_btn.setEnabled(True)
        self._scan_btn.setText("↻  تحديث القائمة")
        self._all_devices = devices

        # تحديث قائمة الأنواع للتصفية
        types = sorted({d.get("type", _NA) for d in devices if d.get("type")})
        self._type_combo.clear()
        self._type_combo.addItem("الكل")
        for t in types:
            self._type_combo.addItem(t)

        self._apply_filter()

        log_action("فحص الأجهزة المتصلة", "Success", f"تم اكتشاف {len(devices)} جهاز")

    def _apply_filter(self):
        search = self._search_field.text().strip().lower()
        selected_type = self._type_combo.currentText()

        filtered = [
            d
            for d in self._all_devices
            if (
                not search
                or search in (d.get("name", "")).lower()
                or search in (d.get("manufacturer", "")).lower()
            )
            and (selected_type == "الكل" or d.get("type") == selected_type)
        ]

        self._populate_table(filtered)
        count = len(filtered)
        total = len(self._all_devices)
        self._status_lbl.setText(f"يعرض {count} جهاز من أصل {total} جهاز مكتشف.")

    def _populate_table(self, devices: list):
        self._table.setRowCount(0)

        status_colors = {
            "يعمل": "#3fb950",
            "متصل": "#3fb950",
            "خطأ": "#e06c75",
            "غير متصل": "#e06c75",
            "غير معروف": "#e5c07b",
            "في الصيانة": "#e5c07b",
        }

        for dev in devices:
            row = self._table.rowCount()
            self._table.insertRow(row)

            status = dev.get("status", _NA)
            status_color = status_colors.get(status, "#abb2bf")

            cols = [
                dev.get("name", _NA),
                dev.get("type", _NA),
                dev.get("manufacturer", _NA),
                status,
                dev.get("device_id", _NA),
                dev.get("connection", _NA),
            ]
            for c, val in enumerate(cols):
                item = QTableWidgetItem(str(val))
                if c == 3:
                    item.setForeground(QColor(status_color))
                self._table.setItem(row, c, item)

    def on_show(self):
        if not self._all_devices:
            self._start_scan()
