"""
النافذة الرئيسية للبرنامج.
فيها شريط جانبي للتنقل وـ QStackedWidget يبدّل بين الصفحات.
يدعم العربية والإنجليزية.
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QScrollArea,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from src.utils.admin_check import is_admin
from src.utils.branding import APP_TITLE
from src.utils.lang import get_lang, tr
from src.utils.lang import text as tx
from src.utils.logger import setup_logger
from src.utils.ui_style import refresh_local_styles
from src.utils.ui_text import QLabel, QPushButton

log = setup_logger(__name__)


# ── Dark stylesheet ───────────────────────────────────────────────────────
DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1a1d23; color: #c9d1d9;
    font-family: "Segoe UI", Arial, sans-serif; font-size: 13px;
}
QLabel { color: #c9d1d9; }

/* ── أزرار ── */
QPushButton {
    background-color: #21262d; color: #c9d1d9;
    border: 1px solid #30363d; border-radius: 8px;
    padding: 8px 16px; font-size: 13px;
    min-height: 32px;
}
QPushButton:hover {
    background-color: #30363d; color: #f0f6fc;
    border-color: #58a6ff;
}
QPushButton:pressed { background-color: #58a6ff; color: #0d1117; }
QPushButton:disabled { color: #484f58; background-color: #161b22; border-color: #21262d; }

/* ── جداول ── */
QTableWidget {
    background-color: #161b22; gridline-color: #21262d;
    color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px;
    selection-background-color: #1f3a5f;
}
QTableWidget::item { padding: 6px 8px; border-bottom: 1px solid #21262d; }
QTableWidget::item:selected { background-color: #1f3a5f; color: #f0f6fc; }
QTableWidget::item:alternate { background-color: #1c2128; }
QHeaderView::section {
    background-color: #161b22; color: #58a6ff;
    border: none; border-bottom: 2px solid #30363d;
    padding: 8px; font-weight: bold; font-size: 12px;
}

/* ── شريط التمرير ── */
QScrollBar:vertical {
    background: #161b22; width: 8px; border-radius: 4px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #30363d; border-radius: 4px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #58a6ff; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: #161b22; height: 8px; border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #30363d; border-radius: 4px; min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: #58a6ff; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── حقول النص ── */
QTextEdit, QPlainTextEdit {
    background-color: #161b22; color: #c9d1d9;
    border: 1px solid #30363d; border-radius: 8px;
    font-family: "Consolas", "Cascadia Code", monospace; font-size: 12px;
    padding: 6px;
    selection-background-color: #1f3a5f;
}
QLineEdit {
    background-color: #21262d; color: #c9d1d9;
    border: 1px solid #30363d; border-radius: 6px;
    padding: 6px 10px; min-height: 28px;
}
QLineEdit:focus { border-color: #58a6ff; }
QLineEdit:read-only { color: #484f58; background-color: #161b22; }

/* ── شريط التقدم ── */
QProgressBar {
    background-color: #21262d; border: 1px solid #30363d;
    border-radius: 8px; text-align: center; color: #f0f6fc;
    height: 22px; font-weight: bold;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #1f6feb, stop:1 #58a6ff);
    border-radius: 7px;
}

/* ── القوائم المنسدلة ── */
QComboBox {
    background-color: #21262d; color: #c9d1d9;
    border: 1px solid #30363d; border-radius: 6px;
    padding: 5px 12px; min-height: 28px;
}
QComboBox:hover { border-color: #58a6ff; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox::down-arrow { width: 10px; height: 10px; }
QComboBox QAbstractItemView {
    background-color: #21262d; color: #c9d1d9;
    border: 1px solid #30363d; border-radius: 6px;
    selection-background-color: #1f3a5f;
    padding: 4px;
}

/* ── المجموعات ── */
QGroupBox {
    color: #58a6ff; border: 1px solid #30363d;
    border-radius: 10px; margin-top: 18px; padding: 14px 10px 10px 10px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin; subcontrol-position: top left;
    padding: 2px 10px; color: #58a6ff;
    background-color: #1a1d23; border-radius: 4px;
}

/* ── التابات ── */
QTabWidget::pane {
    border: 1px solid #30363d; border-radius: 8px;
    background-color: #161b22;
}
QTabWidget::tab-bar { alignment: left; }
QTabBar::tab {
    background-color: #21262d; color: #8b949e;
    border: 1px solid #30363d; border-bottom: none;
    padding: 9px 20px; border-radius: 8px 8px 0 0; margin-right: 2px;
    font-size: 13px;
}
QTabBar::tab:selected {
    background-color: #161b22; color: #58a6ff;
    border-bottom: 2px solid #58a6ff; font-weight: bold;
}
QTabBar::tab:hover:!selected { background-color: #30363d; color: #c9d1d9; }

/* ── شريط الحالة ── */
QStatusBar { background-color: #0d1117; color: #484f58; font-size: 12px; }

/* ── فاصل ── */
QSplitter::handle { background-color: #30363d; }

/* ── تلميحات ── */
QToolTip {
    background-color: #21262d; color: #c9d1d9;
    border: 1px solid #58a6ff; border-radius: 4px; padding: 4px 8px;
}
"""

LIGHT_STYLE = """
QMainWindow, QWidget {
    background-color: #f6f8fa; color: #24292f;
    font-family: "Segoe UI", Arial, sans-serif; font-size: 13px;
}
QLabel { color: #24292f; }

/* ── أزرار ── */
QPushButton {
    background-color: #f6f8fa; color: #24292f;
    border: 1px solid #d0d7de; border-radius: 8px;
    padding: 8px 16px; min-height: 32px;
}
QPushButton:hover { background-color: #eaeef2; border-color: #0969da; }
QPushButton:pressed { background-color: #0969da; color: white; }
QPushButton:disabled { color: #8c959f; background-color: #f6f8fa; }

/* ── جداول ── */
QTableWidget {
    background-color: white; gridline-color: #eaeef2;
    color: #24292f; border: 1px solid #d0d7de; border-radius: 6px;
    selection-background-color: #dbeafe;
}
QTableWidget::item { padding: 6px 8px; border-bottom: 1px solid #eaeef2; }
QTableWidget::item:selected { background-color: #dbeafe; color: #0969da; }
QHeaderView::section {
    background-color: #f6f8fa; color: #0969da;
    border: none; border-bottom: 2px solid #d0d7de;
    padding: 8px; font-weight: bold;
}

/* ── شريط التمرير ── */
QScrollBar:vertical { background: #f6f8fa; width: 8px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #d0d7de; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #0969da; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

/* ── حقول النص ── */
QTextEdit, QPlainTextEdit {
    background-color: white; color: #24292f;
    border: 1px solid #d0d7de; border-radius: 8px;
    font-family: "Consolas", monospace; font-size: 12px; padding: 6px;
}
QLineEdit {
    background-color: white; color: #24292f;
    border: 1px solid #d0d7de; border-radius: 6px; padding: 6px 10px;
}
QLineEdit:focus { border-color: #0969da; }
QLineEdit:read-only { background-color: #f6f8fa; color: #8c959f; }

/* ── شريط التقدم ── */
QProgressBar {
    background-color: #eaeef2; border: 1px solid #d0d7de;
    border-radius: 8px; text-align: center; color: #24292f; height: 22px; font-weight: bold;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #0969da, stop:1 #58a6ff);
    border-radius: 7px;
}

/* ── قوائم منسدلة ── */
QComboBox {
    background-color: white; color: #24292f;
    border: 1px solid #d0d7de; border-radius: 6px; padding: 5px 12px;
}
QComboBox:hover { border-color: #0969da; }
QComboBox QAbstractItemView {
    background-color: white; color: #24292f;
    border: 1px solid #d0d7de; selection-background-color: #dbeafe;
}

/* ── مجموعات ── */
QGroupBox {
    color: #0969da; border: 1px solid #d0d7de;
    border-radius: 10px; margin-top: 18px; padding: 14px 10px 10px 10px; font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin; subcontrol-position: top left;
    padding: 2px 10px; color: #0969da;
    background-color: #f6f8fa; border-radius: 4px;
}

/* ── تابات ── */
QTabWidget::pane { border: 1px solid #d0d7de; border-radius: 8px; background-color: white; }
QTabBar::tab {
    background-color: #f6f8fa; color: #57606a;
    border: 1px solid #d0d7de; border-bottom: none;
    padding: 9px 20px; border-radius: 8px 8px 0 0; margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: white; color: #0969da;
    border-bottom: 2px solid #0969da; font-weight: bold;
}

/* ── شريط الحالة ── */
QStatusBar { background-color: #eaeef2; color: #57606a; font-size: 12px; }

/* ── تلميحات ── */
QToolTip {
    background-color: white; color: #24292f;
    border: 1px solid #0969da; border-radius: 4px; padding: 4px 8px;
}
"""


class SidebarButton(QPushButton):
    """زر التنقل في الشريط الجانبي."""

    def __init__(self, icon_text: str, label: str, parent=None):
        super().__init__(parent)
        self.setText(f"{icon_text}  {label}".replace("&", "&&"))
        self.setCheckable(True)
        self.setFixedHeight(38)
        self.setToolTip(label)
        self.setAccessibleName(label)
        self.setFont(QFont("Segoe UI", 12))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style(False)

    def _apply_style(self, checked: bool):
        if checked:
            self.setStyleSheet(
                "QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                "stop:0 #1f6feb,stop:1 #388bfd); color: #f0f6fc; "
                "border: none; border-right: 3px solid #58a6ff; border-radius: 0; "
                "text-align: right; padding-right: 18px; font-weight: bold; font-size:13px; }"
            )
        else:
            self.setStyleSheet(
                "QPushButton { background-color: transparent; color: #8b949e; "
                "border: none; border-radius: 0; text-align: right; "
                "padding-right: 18px; font-size:12px; }"
                "QPushButton:hover { background-color: #21262d; color: #c9d1d9; "
                "border-right: 3px solid #30363d; }"
            )

        self.setStyleSheet(
            self.styleSheet()
            + "QPushButton { min-height:38px; max-height:38px; padding-top:0; padding-bottom:0; }"
        )
        if get_lang() == "en":
            self.setStyleSheet(
                self.styleSheet()
                .replace("text-align: right", "text-align: left")
                .replace("padding-right", "padding-left")
                .replace("border-right", "border-left")
            )

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._apply_style(checked)


class MainWindow(QMainWindow):
    """Application shell: sidebar + page stack."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(760, 480)
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(min(1240, screen.width() - 40), min(700, screen.height() - 40))
        self._closing = False
        self._restart_on_close = False
        self._close_timer = QTimer(self)
        self._close_timer.setInterval(200)
        self._close_timer.timeout.connect(self._finish_close)
        self._current_theme = "dark"
        QApplication.instance().setProperty("toolkitTheme", "dark")
        self.setStyleSheet(DARK_STYLE)
        self._setup_ui()
        for label in self.findChildren(QLabel):
            if label.alignment() != Qt.AlignmentFlag.AlignCenter:
                label.setAlignment(
                    (
                        Qt.AlignmentFlag.AlignRight
                        if get_lang() == "ar"
                        else Qt.AlignmentFlag.AlignLeft
                    )
                    | Qt.AlignmentFlag.AlignVCenter
                    | Qt.AlignmentFlag.AlignAbsolute
                )
        from PySide6.QtWidgets import QTableWidget

        for table in self.findChildren(QTableWidget):
            table.setAlternatingRowColors(True)
            table.verticalHeader().setDefaultSectionSize(34)
            table.verticalHeader().setMinimumSectionSize(30)
        from src.database.init_db import get_setting

        self.apply_theme(get_setting("theme", "dark"), persist=False)
        self._navigate(0)
        self._update_status_bar()
        log.info("MainWindow initialised")

    # ── UI construction ────────────────────────────────────────────────

    def _setup_ui(self):
        central = QWidget()
        central.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # المحتوى أولاً (يسار) — الشريط الجانبي على اليمين
        self.stack = QStackedWidget()
        root.addWidget(self.stack, stretch=1)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedWidth(1)
        sep.setStyleSheet("background-color: #21262d;")
        root.addWidget(sep)

        sidebar = self._build_sidebar()
        sidebar.setFixedWidth(232)
        root.addWidget(sidebar)
        # Logical ordering puts navigation at the right for Arabic and left for English.
        root.setDirection(
            QHBoxLayout.Direction.LeftToRight
            if get_lang() == "ar"
            else QHBoxLayout.Direction.RightToLeft
        )
        self._load_pages()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._admin_label = QLabel()
        self.status_bar.addPermanentWidget(self._admin_label)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setLayoutDirection(
            Qt.LayoutDirection.RightToLeft if get_lang() == "ar" else Qt.LayoutDirection.LeftToRight
        )
        sidebar.setMinimumWidth(212)
        sidebar.setStyleSheet("background-color: #0d1117;")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── رأس الشريط — اسم المشروع عربي وإنجليزي ──────────────────
        header = QWidget()
        header.setFixedHeight(70)
        header.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 #161b22,stop:1 #0d1117);"
            "border-bottom: 2px solid #1f6feb;"
        )
        h_lay = QVBoxLayout(header)
        h_lay.setContentsMargins(16, 12, 16, 10)
        h_lay.setSpacing(2)

        en_lbl = QLabel(APP_TITLE)
        en_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        en_lbl.setStyleSheet("color:#58a6ff; background:transparent; border:none;")
        en_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        h_lay.addWidget(en_lbl)

        ar_lbl = QLabel(tx("منصة عمليات تقنية المعلومات", "IT operations workspace"))
        ar_lbl.setFont(QFont("Segoe UI", 11))
        ar_lbl.setStyleSheet("color:#c9d1d9; background:transparent; border:none;")
        ar_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        h_lay.addWidget(ar_lbl)

        layout.addWidget(header)

        # ── أزرار التنقل ──────────────────────────────────────────────
        nav_items = [
            ("🏠", tr("nav_dashboard")),
            ("🖥", tr("nav_device_info")),
            ("🔧", tr("nav_drivers")),
            ("❤", tr("nav_health")),
            ("🌐", tr("nav_network")),
            ("🔌", tr("nav_devices")),
            ("🖨", tr("nav_printers")),
            ("⚙", tr("nav_maintenance")),
            ("🏢", tr("nav_domain")),
            ("🔒", tr("nav_cybersecurity")),
            ("💻", tr("nav_cmd")),
            ("📋", tr("nav_history")),
            ("⚙", tr("nav_settings")),
        ]
        nav_scroll = QScrollArea()
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setFrameShape(QFrame.Shape.NoFrame)
        nav_content = QWidget()
        nav_layout = QVBoxLayout(nav_content)
        nav_layout.setContentsMargins(8, 8, 8, 8)
        nav_layout.setSpacing(3)
        nav_scroll.setWidget(nav_content)
        layout.addWidget(nav_scroll, stretch=1)
        self._nav_buttons: list[SidebarButton] = []
        for icon, label in nav_items:
            btn = SidebarButton(icon, label, sidebar)
            btn.clicked.connect(lambda _, idx=len(self._nav_buttons): self._navigate(idx))
            if len(self._nav_buttons) == 12:
                layout.addWidget(btn)  # Settings remains visible while navigation scrolls.
            else:
                nav_layout.addWidget(btn)
            self._nav_buttons.append(btn)
        nav_layout.addStretch()
        self._nav_shortcuts = []
        for index in range(9):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{index + 1}"), self)
            shortcut.activated.connect(lambda idx=index: self._navigate(idx))
            self._nav_shortcuts.append(shortcut)

        # ── أسفل الشريط — اسم المؤلف ─────────────────────────────────
        footer = QWidget()
        footer.setStyleSheet("background-color:#0d1117; border-top:1px solid #21262d;")
        f_lay = QVBoxLayout(footer)
        f_lay.setContentsMargins(12, 8, 12, 10)
        f_lay.setSpacing(2)

        author_lbl = QLabel("Meshal Alfaifi")
        author_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        author_lbl.setStyleSheet(
            "color:#58a6ff; font-size:11px; font-weight:bold; background:transparent; border:none;"
        )
        f_lay.addWidget(author_lbl)

        layout.addWidget(footer)
        return sidebar

    def _load_pages(self):
        """يستورد كل الصفحات الـ 13. الترتيب يطابق nav_items بالضبط."""
        from src.ui.automation_page import AutomationPage
        from src.ui.cmd_page import CmdPage
        from src.ui.connected_devices_page import ConnectedDevicesPage
        from src.ui.cybersecurity_page import CybersecurityPage
        from src.ui.dashboard import DashboardPage
        from src.ui.device_info_page import DeviceInfoPage
        from src.ui.domain_page import DomainPage
        from src.ui.driver_page import DriverPage
        from src.ui.health_page import HealthPage
        from src.ui.history_page import HistoryPage
        from src.ui.network_page import NetworkPage
        from src.ui.printer_page import PrinterPage
        from src.ui.settings_page import SettingsPage

        self._pages = [
            DashboardPage(self),  # 0  لوحة التحكم
            DeviceInfoPage(self),  # 1  معلومات الجهاز
            DriverPage(self),  # 2  تشخيص التعريفات
            HealthPage(self),  # 3  فحص صحة الجهاز
            NetworkPage(self),  # 4  الشبكة و IP
            ConnectedDevicesPage(self),  # 5  الأجهزة المتصلة
            PrinterPage(self),  # 6  الطابعات والماسحات
            AutomationPage(self),  # 7  مركز الصيانة
            DomainPage(self),  # 8  المجال والدومين
            CybersecurityPage(self),  # 9  الأمن السيبراني
            CmdPage(self),  # 10 أوامر CMD
            HistoryPage(self),  # 11 السجل
            SettingsPage(self),  # 12 الإعدادات
        ]
        for page in self._pages:
            page.setLayoutDirection(
                Qt.LayoutDirection.RightToLeft
                if get_lang() == "ar"
                else Qt.LayoutDirection.LeftToRight
            )
            wrapper = QScrollArea()
            wrapper.setWidgetResizable(True)
            wrapper.setFrameShape(QFrame.Shape.NoFrame)
            wrapper.setWidget(page)
            self.stack.addWidget(wrapper)

    # ── Navigation ─────────────────────────────────────────────────────

    def _navigate(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)
        page = self._pages[index]
        if hasattr(page, "on_show"):
            page.on_show()

    # ── Status bar ─────────────────────────────────────────────────────

    def _update_status_bar(self):
        if is_admin():
            self._admin_label.setText(tr("status_admin"))
            self._admin_label.setStyleSheet("color: #3fb950;")
            self.status_bar.showMessage(tr("status_ready_admin"))
        else:
            self._admin_label.setText(tr("status_no_admin"))
            self._admin_label.setStyleSheet("color: #e5c07b;")
            self.status_bar.showMessage(tr("status_ready_no_admin"))

    # ── Theme ──────────────────────────────────────────────────────────

    def apply_theme(self, theme: str, persist: bool = True):
        if persist:
            from src.database.init_db import save_setting

            save_setting("theme", theme)
        self._current_theme = theme
        QApplication.instance().setProperty("toolkitTheme", theme)
        style = DARK_STYLE if theme == "dark" else LIGHT_STYLE
        if get_lang() == "ar":
            style = style.replace(
                "subcontrol-position: top left", "subcontrol-position: top right"
            ).replace("alignment: left", "alignment: right")
        self.setStyleSheet(
            style
            + "\nQLabel { background:transparent; }\nQPushButton:focus, QComboBox:focus, QLineEdit:focus { border: 2px solid #388bfd; }\nQTableWidget { alternate-background-color: "
            + ("#f1f5f9" if theme == "light" else "#1c2128")
            + "; }"
        )
        refresh_local_styles(self)

    def show_status(self, message: str, timeout: int = 4000):
        self.status_bar.showMessage(message, timeout)

    def closeEvent(self, event):
        from src.utils.workers import active_workers

        workers = active_workers()
        if workers:
            event.ignore()
            self._closing = True
            for page in self._pages:
                for timer in page.findChildren(QTimer):
                    timer.stop()
                page.setEnabled(False)
            for worker in workers:
                worker.requestInterruption()
            self.status_bar.showMessage(
                tx(
                    "جارٍ انتظار انتهاء العملية بأمان قبل الإغلاق…",
                    "Waiting for current operations to finish safely before closing…",
                )
            )
            self._close_timer.start()
            return
        self._close_timer.stop()
        if self._restart_on_close:
            from src.utils.restart import restart_application

            try:
                restart_application()
            except OSError as exc:
                from PySide6.QtWidgets import QMessageBox

                QMessageBox.warning(self, APP_TITLE, str(exc))
        event.accept()

    def _finish_close(self):
        from src.utils.workers import active_workers

        if not active_workers():
            self.close()
