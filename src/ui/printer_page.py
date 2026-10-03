"""عرض الطابعات والمهام وتشخيص الاتصال وإدارة الطابور بعد التأكيد.
المؤلف: Meshal Alfaifi."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.database.init_db import log_action
from src.utils.admin_check import confirm_action, show_admin_warning
from src.utils.logger import setup_logger
from src.utils.ui_text import QGroupBox, QLabel, QPushButton, QTextEdit
from src.utils.workers import ManagedThread as QThread

log = setup_logger(__name__)


class PrinterWorker(QThread):
    finished = Signal(list)

    def run(self):
        try:
            from src.core.printer_tools import get_printers

            self.finished.emit(get_printers())
        except Exception as exc:
            log.error(f"PrinterWorker: {exc}")
            self.finished.emit([])


class PrinterPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._printers: list[dict] = []
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # Title
        title = QLabel("الطابعات والماسحات")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #dcdfe4;")
        root.addWidget(title)

        # Action buttons row
        btn_row = QHBoxLayout()
        self._refresh_btn = self._btn("↻ تحديث القائمة", "#61afef")
        self._spooler_btn = self._btn("🔑 إعادة تشغيل خدمة الطباعة", "#e5c07b")
        self._clear_q_btn = self._btn("🗑 مسح قائمة الطباعة", "#e06c75")
        self._ping_btn = self._btn("فحص اتصال الطابعة", "#3fb950")
        btn_row.addWidget(self._refresh_btn)
        btn_row.addWidget(self._spooler_btn)
        btn_row.addWidget(self._clear_q_btn)
        btn_row.addWidget(self._ping_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, stretch=1)

        # Left: printer list
        left = QWidget()
        left.setMaximumWidth(300)
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 8, 0)
        left_lay.setSpacing(6)

        lbl = QLabel("الطابعات المثبّتة")
        lbl.setStyleSheet("color: #61afef; font-weight: bold;")
        left_lay.addWidget(lbl)

        self._printer_list = QListWidget()
        self._printer_list.setStyleSheet(
            "QListWidget { background-color: #21262d; border: 1px solid #3d4451; "
            "border-radius: 6px; } "
            "QListWidget::item { padding: 8px; } "
            "QListWidget::item:selected { background-color: #3d4451; color: #61afef; }"
        )
        self._printer_list.currentRowChanged.connect(self._on_printer_selected)
        left_lay.addWidget(self._printer_list)
        splitter.addWidget(left)

        # Right: details + output
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(8, 0, 0, 0)
        right_lay.setSpacing(8)

        details_grp = QGroupBox("تفاصيل الطابعة")
        details_lay = QVBoxLayout(details_grp)
        self._detail_lbl = QLabel("اختر طابعة لعرض تفاصيلها.")
        self._detail_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._detail_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._detail_lbl.setStyleSheet("color: #abb2bf; font-size: 13px; padding: 4px;")
        self._detail_lbl.setWordWrap(True)
        details_lay.addWidget(self._detail_lbl)
        right_lay.addWidget(details_grp)

        output_grp = QGroupBox("النتائج")
        output_lay = QVBoxLayout(output_grp)
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setPlaceholderText("ستظهر النتائج هنا…")
        self._output.setMaximumHeight(180)
        output_lay.addWidget(self._output)
        right_lay.addWidget(output_grp)

        right_lay.addStretch()
        splitter.addWidget(right)
        splitter.setSizes([280, 700])

        # Wire buttons
        self._refresh_btn.clicked.connect(self.on_show)
        self._spooler_btn.clicked.connect(self._restart_spooler)
        self._clear_q_btn.clicked.connect(self._clear_queue)
        self._ping_btn.clicked.connect(self._ping_printer)

    def _btn(self, label: str, color: str) -> QPushButton:
        b = QPushButton(label)
        b.setMinimumHeight(36)
        b.setStyleSheet(
            f"QPushButton {{ background-color: #21262d; color: {color}; "
            f"border: 1px solid {color}; border-radius: 6px; padding: 4px 12px; }}"
            f"QPushButton:hover {{ background-color: {color}; color: #1e2128; }}"
        )
        return b

    # ── Load printers ──────────────────────────────────────────────────

    def on_show(self):
        self._printer_list.clear()
        self._detail_lbl.setText("جارٍ تحميل الطابعات…")
        worker = PrinterWorker(self)
        worker.finished.connect(self._on_printers_loaded)
        worker.start()

    def _on_printers_loaded(self, printers: list):
        self._printers = printers
        self._printer_list.clear()
        if not printers:
            self._detail_lbl.setText("لم يتم العثور على طابعات.")
            return
        for p in printers:
            name = p.get("name", "Unknown")
            default = " ★" if p.get("is_default") else ""
            item = QListWidgetItem(f"{name}{default}")
            if p.get("is_default"):
                item.setForeground(QColor("#61afef"))
            self._printer_list.addItem(item)

    def _on_printer_selected(self, row: int):
        if row < 0 or row >= len(self._printers):
            return
        p = self._printers[row]
        status = p.get("status", "Unknown")
        jobs = p.get("jobs", 0)
        status_color = "#3fb950" if status == "Ready" else "#e5c07b"
        html = (
            f"<b>الاسم:</b> {p.get('name', '—')}<br>"
            f"<b>التعريف:</b> {p.get('driver', '—')}<br>"
            f"<b>المنفذ:</b> {p.get('port', '—')}<br>"
            f"<b>الحالة:</b> <span style='color:{status_color}'>{status}</span><br>"
            f"<b>الافتراضية:</b> {'نعم ★' if p.get('is_default') else 'لا'}<br>"
            f"<b>قائمة الانتظار:</b> {jobs} مهمة"
        )
        self._detail_lbl.setText(html)

    # ── Actions ────────────────────────────────────────────────────────

    def _selected_printer(self) -> dict | None:
        row = self._printer_list.currentRow()
        if 0 <= row < len(self._printers):
            return self._printers[row]
        return None

    def _restart_spooler(self):
        if not show_admin_warning(self):
            return
        if not confirm_action(
            "هل تريد إعادة تشغيل خدمة الطباعة (Print Spooler)؟\nقد تتأثر مهام الطباعة الجارية.",
            self,
        ):
            return
        from src.core.printer_tools import restart_spooler

        ok, msg = restart_spooler()
        self._output.append(msg)
        log_action("إعادة تشغيل خدمة الطباعة", "Success" if ok else "Failed", msg)

    def _clear_queue(self):
        printer = self._selected_printer()
        if not printer:
            self._output.append("يرجى اختيار طابعة أولاً.")
            return
        name = printer.get("name", "غير معروف")
        if not confirm_action(f"هل تريد إلغاء جميع مهام الطباعة في '{name}'؟", self):
            return
        from src.core.printer_tools import clear_print_queue

        ok, msg = clear_print_queue(name)
        self._output.append(msg)
        log_action("مسح قائمة الطباعة", "Success" if ok else "Failed", msg)
        self._on_printer_selected(self._printer_list.currentRow())

    def _ping_printer(self):
        printer = self._selected_printer()
        if not printer:
            self._output.append("يرجى اختيار طابعة أولاً.")
            return
        port = printer.get("port", "")
        self._output.append(f"جارٍ فحص اتصال الطابعة عبر المنفذ '{port}'…")
        from src.core.printer_tools import ping_printer

        result = ping_printer(port)
        raw = result.get("raw_output", "")
        reach = result.get("reachable")
        if reach is None:
            self._output.append(result.get("raw_output", "هذا ليس منفذ شبكة."))
        elif reach:
            self._output.append(f"✓ متصل  متوسط {result.get('avg_ms')}ms\n{raw}")
        else:
            self._output.append(f"✗ غير متصل\n{raw}")
