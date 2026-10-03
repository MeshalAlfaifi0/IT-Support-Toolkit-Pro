"""عرض سجل العمليات ونتيجتها الكاملة؛ لا يضم فحوصات الصحة أو التصدير."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QHBoxLayout, QHeaderView, QSplitter, QVBoxLayout, QWidget

from src.database.init_db import get_action_logs
from src.utils.logger import setup_logger
from src.utils.ui_text import (
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
)

log = setup_logger(__name__)


class HistoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("السجل")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #dcdfe4;")
        root.addWidget(title)

        btn_row = QHBoxLayout()
        self._refresh_btn = QPushButton("↻ تحديث")
        self._refresh_btn.setFixedSize(100, 34)
        self._refresh_btn.clicked.connect(self.on_show)
        btn_row.addWidget(self._refresh_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        tabs = QTabWidget()
        root.addWidget(tabs, stretch=1)

        # ── Action log tab ─────────────────────────────────────────
        action_tab = QWidget()
        at_lay = QVBoxLayout(action_tab)

        splitter = QSplitter(Qt.Orientation.Vertical)
        at_lay.addWidget(splitter)

        self._action_table = QTableWidget(0, 4)
        self._action_table.setHorizontalHeaderLabels(
            [
                "التاريخ والوقت",
                "العملية",
                "الحالة",
                "ملخص النتيجة",
            ]
        )
        self._action_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._action_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._action_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._action_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        self._action_table.verticalHeader().setVisible(False)
        self._action_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._action_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._action_table.currentCellChanged.connect(
            lambda row, col, pr, pc: self._show_action_output(row)
        )
        splitter.addWidget(self._action_table)

        self._action_output = QTextEdit()
        self._action_output.setReadOnly(True)
        self._action_output.setPlaceholderText("اختر عملية من القائمة أعلاه لعرض نتيجتها الكاملة.")
        self._action_output.setMaximumHeight(180)
        splitter.addWidget(self._action_output)

        tabs.addTab(action_tab, "سجل العمليات")

    def on_show(self):
        self._action_output.clear()
        self._load_action_log()

    def _load_action_log(self):
        self._action_table.setRowCount(0)
        self._action_rows: list = []
        try:
            rows = get_action_logs(limit=200)
            for row in rows:
                r = self._action_table.rowCount()
                self._action_table.insertRow(r)

                status = row["status"] or ""
                status_color = (
                    "#3fb950"
                    if status == "Success"
                    else ("#e06c75" if status == "Failed" else "#e5c07b")
                )
                status = "نجح" if status == "Success" else ("فشل" if status == "Failed" else status)
                output = row["output"] or ""
                preview = output[:80].replace("\n", " ")

                items = [
                    row["executed_at"] or "",
                    row["action_name"] or "",
                    status,
                    preview,
                ]
                for c, val in enumerate(items):
                    item = QTableWidgetItem(str(val))
                    if c == 2:
                        item.setForeground(QColor(status_color))
                    self._action_table.setItem(r, c, item)

                self._action_rows.append(output)
        except Exception as exc:
            log.error(f"Action log load error: {exc}")

    def _show_action_output(self, row: int):
        if hasattr(self, "_action_rows") and 0 <= row < len(self._action_rows):
            self._action_output.setPlainText(self._action_rows[row])
