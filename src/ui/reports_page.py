"""واجهة التصدير القديمة محفوظة كمكون مستقل، وغير مضافة إلى تنقل التطبيق الحالي."""

import os
from datetime import datetime

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QHeaderView, QVBoxLayout, QWidget

from src.utils.app_paths import EXPORTS_DIR as _EXPORTS_DIR
from src.utils.logger import setup_logger
from src.utils.ui_text import (
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

log = setup_logger(__name__)


class ReportsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scan_data: dict | None = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        title = QLabel("Reports")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #dcdfe4;")
        root.addWidget(title)

        subtitle = QLabel(
            "Export the most recent health scan results. "
            "Run a Health Check first if no scan data is available."
        )
        subtitle.setStyleSheet("color: #5c6370; font-size: 12px;")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        # Export buttons group
        export_grp = QGroupBox("Export Latest Scan")
        export_lay = QHBoxLayout(export_grp)
        export_lay.setSpacing(12)

        self._btn_json = self._export_btn("Export  JSON", "#61afef")
        self._btn_csv = self._export_btn("Export  CSV", "#3fb950")
        self._btn_pdf = self._export_btn("Export  PDF", "#e5c07b")
        self._btn_refresh = QPushButton("↻ Load Latest Scan")
        self._btn_refresh.setMinimumHeight(40)

        export_lay.addWidget(self._btn_json)
        export_lay.addWidget(self._btn_csv)
        export_lay.addWidget(self._btn_pdf)
        export_lay.addStretch()
        root.addWidget(export_grp)
        root.addWidget(self._btn_refresh)

        # Scan summary
        self._scan_info_lbl = QLabel("No scan loaded. Click '↻ Load Latest Scan'.")
        self._scan_info_lbl.setStyleSheet("color: #5c6370; font-size: 12px; padding: 4px;")
        self._scan_info_lbl.setWordWrap(True)
        root.addWidget(self._scan_info_lbl)

        # Previous reports table
        prev_grp = QGroupBox("Previous Report Files")
        prev_lay = QVBoxLayout(prev_grp)

        refresh_files_btn = QPushButton("↻ Refresh File List")
        refresh_files_btn.setFixedWidth(160)
        refresh_files_btn.clicked.connect(self._load_file_list)
        prev_lay.addWidget(refresh_files_btn)

        self._file_table = QTableWidget(0, 3)
        self._file_table.setHorizontalHeaderLabels(["File Name", "Type", "Modified"])
        self._file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._file_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._file_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._file_table.verticalHeader().setVisible(False)
        self._file_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        prev_lay.addWidget(self._file_table)

        open_btn = QPushButton("Open Selected Folder")
        open_btn.setFixedWidth(180)
        open_btn.clicked.connect(self._open_exports_folder)
        prev_lay.addWidget(open_btn)

        root.addWidget(prev_grp, stretch=1)

        # Wire
        self._btn_json.clicked.connect(lambda: self._export("json"))
        self._btn_csv.clicked.connect(lambda: self._export("csv"))
        self._btn_pdf.clicked.connect(lambda: self._export("pdf"))
        self._btn_refresh.clicked.connect(self._load_scan)

    def _export_btn(self, label: str, color: str) -> QPushButton:
        b = QPushButton(label)
        b.setMinimumSize(120, 40)
        b.setStyleSheet(
            f"QPushButton {{ background-color: #21262d; color: {color}; "
            f"border: 1px solid {color}; border-radius: 6px; font-size: 13px; }}"
            f"QPushButton:hover {{ background-color: {color}; color: #1e2128; }}"
            "QPushButton:disabled { color: #5c6370; border-color: #3d4451; }"
        )
        return b

    def on_show(self):
        self._load_scan()
        self._load_file_list()

    def _load_scan(self):
        from src.core.health_checker import get_latest_scan

        self._scan_data = get_latest_scan()
        for button in (self._btn_json, self._btn_csv, self._btn_pdf):
            button.setEnabled(bool(self._scan_data))
        if self._scan_data:
            ts = self._scan_data.get("scan_timestamp", "Unknown")
            device = self._scan_data.get("device_name", "Unknown")
            score = self._scan_data.get("health_score", {}).get("score", "?")
            self._scan_info_lbl.setText(
                f"Loaded scan — Device: {device}  |  Date: {ts}  |  Health Score: {score}/100"
            )
            self._scan_info_lbl.setStyleSheet("color: #3fb950; font-size: 12px; padding: 4px;")
        else:
            self._scan_info_lbl.setText(
                "No scan data found. Go to Health Checker and run a full scan first."
            )
            self._scan_info_lbl.setStyleSheet("color: #e5c07b; font-size: 12px; padding: 4px;")

    def _export(self, fmt: str):
        if not self._scan_data:
            QMessageBox.warning(
                self, "No Scan Data", "No scan data available. Run a Health Check first."
            )
            return

        try:
            if fmt == "json":
                from src.reports.json_report import export_json

                path = export_json(self._scan_data)
            elif fmt == "csv":
                from src.reports.csv_report import export_csv

                path = export_csv(self._scan_data)
            elif fmt == "pdf":
                from src.reports.pdf_report import export_pdf

                path = export_pdf(self._scan_data)
            else:
                return

            QMessageBox.information(self, "Export Successful", f"Report saved to:\n{path}")
            self._load_file_list()
        except ImportError as exc:
            QMessageBox.warning(
                self, "Missing Library", f"Cannot generate {fmt.upper()} report:\n{exc}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Export error:\n{exc}")
            log.error(f"Export {fmt} failed: {exc}")

    def _load_file_list(self):
        self._file_table.setRowCount(0)
        _EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        files = sorted(
            _EXPORTS_DIR.iterdir(),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        for f in files:
            if not f.is_file():
                continue
            row = self._file_table.rowCount()
            self._file_table.insertRow(row)
            self._file_table.setItem(row, 0, QTableWidgetItem(f.name))
            self._file_table.setItem(row, 1, QTableWidgetItem(f.suffix.lstrip(".").upper()))
            mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            self._file_table.setItem(row, 2, QTableWidgetItem(mtime))

    def _open_exports_folder(self):
        _EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(str(_EXPORTS_DIR))
