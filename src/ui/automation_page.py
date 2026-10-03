"""واجهة الصيانة؛ تجمع الإجراءات في خيوط وتتحقق من الصلاحيات وتأكيد المستخدم.
المؤلف: Meshal Alfaifi."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QProgressBar,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.database.init_db import log_action
from src.utils.admin_check import confirm_action, show_admin_warning
from src.utils.logger import setup_logger
from src.utils.ui_text import (
    QGroupBox,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
)
from src.utils.workers import ManagedThread as QThread

log = setup_logger(__name__)

# ── Generic background worker ─────────────────────────────────────────────


class ActionWorker(QThread):
    """Runs an arbitrary callable off the UI thread."""

    output_line = Signal(str)  # incremental text line
    finished = Signal(bool, str)
    data_ready = Signal(dict)  # (success, full_output)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            # Functions may accept a line_callback kwarg for streaming output
            result = self._fn(*self._args, **self._kwargs)
            # result is (success, output)
            if isinstance(result, dict):
                self.data_ready.emit(result)
            elif isinstance(result, tuple):
                self.finished.emit(result[0], result[1])
            else:
                self.finished.emit(True, str(result))
        except Exception as exc:
            log.error(f"ActionWorker error: {exc}")
            self.finished.emit(False, str(exc))


class StreamingWorker(QThread):
    """Worker for commands that emit output line-by-line (SFC, DISM)."""

    output_line = Signal(str)
    finished = Signal(bool, str)
    data_ready = Signal(dict)

    def __init__(self, fn, *args):
        super().__init__()
        self._fn = fn
        self._args = args
        self._lines: list[str] = []

    def _capture(self, line: str):
        self._lines.append(line)
        self.output_line.emit(line)

    def run(self):
        try:
            ok, _ = self._fn(self._capture, *self._args)
            self.finished.emit(ok, "\n".join(self._lines))
        except Exception as exc:
            self.finished.emit(False, str(exc))


# ── Service status table ──────────────────────────────────────────────────


class ServiceTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(0, 3, parent)
        self.setHorizontalHeaderLabels(["الخدمة", "الحالة", "إجراء"])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

    def populate(self, statuses: dict, restart_callback):
        self.setRowCount(0)
        for display_name, status in statuses.items():
            row = self.rowCount()
            self.insertRow(row)

            self.setItem(row, 0, QTableWidgetItem(display_name))

            status_item = QTableWidgetItem(status)
            color = "#3fb950" if status == "Running" else "#e06c75"
            status_item.setForeground(QColor(color))
            self.setItem(row, 1, status_item)

            btn = QPushButton("إعادة تشغيل")
            btn.setFixedSize(100, 28)
            btn.setStyleSheet(
                "QPushButton { background-color: #282c34; color: #e5c07b; "
                "border: 1px solid #e5c07b; border-radius: 4px; font-size: 11px; }"
                "QPushButton:hover { background-color: #e5c07b; color: #1e2128; }"
            )
            btn.clicked.connect(lambda _, n=display_name: restart_callback(n))
            self.setCellWidget(row, 2, btn)


# ── Automation Center page ────────────────────────────────────────────────


class AutomationPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: QThread | None = None
        self._setup_ui()
        self._refresh_services()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # Title
        title = QLabel("مركز الصيانة")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #dcdfe4;")
        root.addWidget(title)

        subtitle = QLabel(
            "تشغيل مهام دعم IT الشائعة بأمان. العمليات التي تتطلب صلاحيات مسؤول مُعلَّمة بـ 🔑"
        )
        subtitle.setStyleSheet("color: #5c6370; font-size: 12px;")
        root.addWidget(subtitle)

        # Splitter: left = action buttons, right = output panel
        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, stretch=1)

        # ── Left panel: action buttons ─────────────────────────────
        left = QWidget()
        left.setMinimumWidth(300)
        left.setMaximumWidth(380)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(10)

        # Network group
        net_group = QGroupBox("أدوات الشبكة")
        net_grid = QGridLayout(net_group)
        net_grid.setSpacing(8)
        self._btn_flush_dns = self._make_action_btn("تفريغ ذاكرة DNS", "#61afef")
        self._btn_reset_net = self._make_action_btn("🔑 إعادة ضبط الشبكة", "#e5c07b")
        self._btn_net_diag = self._make_action_btn("تشخيص الشبكة", "#61afef")
        net_grid.addWidget(self._btn_flush_dns, 0, 0)
        net_grid.addWidget(self._btn_reset_net, 0, 1)
        net_grid.addWidget(self._btn_net_diag, 1, 0, 1, 2)
        left_layout.addWidget(net_group)

        # Maintenance group
        maint_group = QGroupBox("صيانة النظام")
        maint_layout = QVBoxLayout(maint_group)
        maint_layout.setSpacing(8)
        self._btn_clear_temp = self._make_action_btn("حذف الملفات المؤقتة", "#3fb950")
        self._btn_sfc = self._make_action_btn("🔑 فحص ملفات النظام (SFC)", "#e5c07b")
        self._btn_dism = self._make_action_btn("🔑 إصلاح النظام (DISM)", "#e5c07b")
        maint_layout.addWidget(self._btn_clear_temp)
        maint_layout.addWidget(self._btn_sfc)
        maint_layout.addWidget(self._btn_dism)
        left_layout.addWidget(maint_group)

        # Services group
        svc_group = QGroupBox("إدارة الخدمات")
        svc_layout = QVBoxLayout(svc_group)
        svc_layout.setSpacing(8)
        self._svc_refresh_btn = QPushButton("↻ تحديث حالة الخدمات")
        self._svc_refresh_btn.clicked.connect(self._refresh_services)
        svc_layout.addWidget(self._svc_refresh_btn)
        self._svc_table = ServiceTable()
        self._svc_table.setMaximumHeight(200)
        svc_layout.addWidget(self._svc_table)
        left_layout.addWidget(svc_group)

        left_layout.addStretch()
        splitter.addWidget(left)

        # ── Right panel: output area ───────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(8)

        out_header = QHBoxLayout()
        out_label = QLabel("النتائج")
        out_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        out_label.setStyleSheet("color: #dcdfe4;")
        out_header.addWidget(out_label)
        out_header.addStretch()
        self._clear_btn = QPushButton("مسح")
        self._clear_btn.setFixedSize(70, 28)
        self._clear_btn.clicked.connect(self._clear_output)
        out_header.addWidget(self._clear_btn)
        right_layout.addLayout(out_header)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # indeterminate while running
        self._progress.setVisible(False)
        self._progress.setFixedHeight(6)
        right_layout.addWidget(self._progress)

        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setPlaceholderText("ستظهر نتائج العمليات هنا…")
        right_layout.addWidget(self._output, stretch=1)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("font-size: 12px;")
        right_layout.addWidget(self._status_lbl)

        splitter.addWidget(right)
        splitter.setSizes([340, 700])

        # ── Wire buttons ───────────────────────────────────────────
        self._btn_flush_dns.clicked.connect(self._do_flush_dns)
        self._btn_reset_net.clicked.connect(self._do_reset_network)
        self._btn_net_diag.clicked.connect(self._do_net_diagnostics)
        self._btn_clear_temp.clicked.connect(self._do_clear_temp)
        self._btn_sfc.clicked.connect(self._do_sfc)
        self._btn_dism.clicked.connect(self._do_dism)

    # ── Button factory ─────────────────────────────────────────────────

    def _make_action_btn(self, label: str, color: str = "#61afef") -> QPushButton:
        btn = QPushButton(label)
        btn.setMinimumHeight(38)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: #21262d; color: {color}; "
            f"border: 1px solid {color}; border-radius: 6px; "
            f"font-size: 13px; padding: 4px 10px; }}"
            f"QPushButton:hover {{ background-color: {color}; color: #1e2128; }}"
            "QPushButton:disabled { background-color: #21262d; color: #5c6370; "
            "border-color: #3d4451; }"
        )
        return btn

    # ── Output helpers ─────────────────────────────────────────────────

    def _print(self, text: str):
        self._output.append(text)

    def _clear_output(self):
        self._output.clear()
        self._status_lbl.setText("")

    def _set_running(self, running: bool):
        self._progress.setVisible(running)
        for btn in (
            self._btn_flush_dns,
            self._btn_reset_net,
            self._btn_net_diag,
            self._btn_clear_temp,
            self._btn_sfc,
            self._btn_dism,
        ):
            btn.setEnabled(not running)

    def _on_done(self, success: bool, output: str, action_name: str):
        self._set_running(False)
        status = "Success" if success else "Failed"
        color = "#3fb950" if success else "#e06c75"
        self._status_lbl.setText(f"الحالة: {'نجح' if success else 'فشل'}")
        self._status_lbl.setStyleSheet(f"color: {color}; font-size: 12px;")
        self._print(f"\n[{status}]")
        log_action(action_name, status, output)
        if hasattr(self, "_main_win") and self._main_win:
            self._main_win.show_status(f"{action_name}: {status}")

    # ── Actions ────────────────────────────────────────────────────────

    def _do_flush_dns(self):
        self._clear_output()
        self._print("► جارٍ تفريغ ذاكرة DNS…\n")
        self._set_running(True)
        from src.core.windows_repair import flush_dns

        self._worker = ActionWorker(flush_dns)
        self._worker.finished.connect(
            lambda ok, out: (self._print(out), self._on_done(ok, out, "تفريغ DNS"))
        )
        self._worker.start()

    def _do_reset_network(self):
        if not show_admin_warning(self):
            return
        if not confirm_action(
            "ستقوم هذه العملية بإعادة ضبط:\n"
            "  • Winsock\n"
            "  • TCP/IP Stack\n"
            "  • تحرير وتجديد عنوان IP\n\n"
            "⚠ قد تحتاج إلى إعادة تشغيل الجهاز بعد هذه العملية.\n\n"
            "هل تريد المتابعة؟",
            self,
        ):
            return
        self._clear_output()
        self._print("► جارٍ إعادة ضبط الشبكة (قد يستغرق 30–60 ثانية)…\n")
        self._set_running(True)
        from src.core.windows_repair import reset_network

        self._worker = ActionWorker(reset_network)
        self._worker.finished.connect(
            lambda ok, out: (self._print(out), self._on_done(ok, out, "إعادة ضبط الشبكة"))
        )
        self._worker.start()

    def _do_net_diagnostics(self):
        self._clear_output()
        self._print("► جارٍ تشخيص الشبكة…\n")
        self._set_running(True)
        from src.core.network_tools import run_full_network_diagnostics

        self._worker = ActionWorker(run_full_network_diagnostics)
        self._worker.data_ready.connect(self._show_net_results)
        self._worker.finished.connect(lambda ok, out: self._on_done(ok, out, "Network diagnostics"))
        self._worker.start()

    def _show_net_results(self, r: dict):
        # Re-run to get structured dict (worker returns str repr)
        self._set_running(False)

        # The worker returned string repr; re-run in-place for formatted display
        # (network diag is fast enough)
        try:
            cfg = r.get("ip_config", {})
            self._print(f"عنوان IP      : {cfg.get('ip_address', 'غير متاح')}")
            self._print(f"عنوان MAC     : {cfg.get('mac_address', 'غير متاح')}")
            self._print(f"البوابة       : {cfg.get('default_gateway', 'غير متاح')}")
            dns_list = ", ".join(cfg.get("dns_servers", [])) or "غير متاح"
            self._print(f"خوادم DNS     : {dns_list}\n")

            for key, label in [
                ("ping_gateway", "البوابة"),
                ("ping_google_dns", "8.8.8.8 (Google DNS)"),
                ("ping_cloudflare_dns", "1.1.1.1 (Cloudflare)"),
            ]:
                p = r.get(key, {})
                reach = "✓ متاح" if p.get("reachable") else "✗ غير متاح"
                avg_ms = f"  متوسط {p.get('avg_ms')}ms" if p.get("avg_ms") else ""
                loss = f"  فقدان {p.get('loss_pct')}%" if p.get("loss_pct", 0) > 0 else ""
                self._print(f"Ping {label:<28}: {reach}{avg_ms}{loss}")

            self._print("")
            for key, host in [
                ("resolve_google", "google.com"),
                ("resolve_microsoft", "microsoft.com"),
            ]:
                res = r.get(key, {})
                if res.get("resolved"):
                    self._print(f"DNS {host:<24}: ✓ {res.get('ip')}")
                else:
                    self._print(f"DNS {host:<24}: ✗ فشل – {res.get('error', '')}")

            log_action("تشخيص الشبكة", "Success", str(r))
        except Exception as exc:
            self._print(f"خطأ: {exc}")
            log_action("تشخيص الشبكة", "Failed", str(exc))

        self._status_lbl.setText("الحالة: اكتمل")
        self._status_lbl.setStyleSheet("color: #3fb950; font-size: 12px;")

    def _do_clear_temp(self):
        if not confirm_action(
            "ستقوم هذه العملية بحذف الملفات من:\n"
            "  • مجلد Temp الخاص بالمستخدم\n"
            "  • C:\\Windows\\Temp\n"
            "\n"
            "لن تُمسَّ المستندات الشخصية أو ملفات المستخدم.\n\n"
            "هل تريد المتابعة؟",
            self,
        ):
            return
        self._clear_output()
        self._print("► جارٍ حذف الملفات المؤقتة…\n")
        self._set_running(True)
        from src.core.windows_repair import clear_temp_files

        self._worker = ActionWorker(clear_temp_files)
        self._worker.finished.connect(self._on_temp_cleanup_done)
        self._worker.start()

    def _on_temp_cleanup_done(self, ok: bool, output: str):
        """Display the authoritative summary without parsing translated text."""
        self._set_running(False)
        self._output.setPlainText(output)
        from src.utils.lang import text as tx

        self._status_lbl.setText(
            tx(
                "الحالة: اكتمل مع تخطي الملفات المحمية أو المستخدمة",
                "Status: Completed; protected or in-use items skipped",
            )
            if ok
            else tx(
                "الحالة: اكتمل جزئيًا؛ راجع الملفات المتخطاة",
                "Status: Partially completed; review skipped files",
            )
        )
        self._status_lbl.setStyleSheet(f"color: {'#3fb950' if ok else '#d29922'}; font-size: 12px;")
        log_action("حذف الملفات المؤقتة", "Success" if ok else "Partial", output)

    def _do_sfc(self):
        if not show_admin_warning(self):
            return
        if not confirm_action(
            "سيقوم فحص ملفات النظام (sfc /scannow) بفحص وإصلاح ملفات Windows المحمية.\n\n"
            "قد تستغرق هذه العملية من 10 إلى 20 دقيقة.\n"
            "لا تغلق التطبيق أثناء الفحص.\n\n"
            "هل تريد المتابعة؟",
            self,
        ):
            return
        self._clear_output()
        self._print("► جارٍ تشغيل فحص SFC (قد يستغرق 10–20 دقيقة)…\n")
        self._set_running(True)
        from src.core.windows_repair import run_sfc

        self._worker = StreamingWorker(run_sfc)
        self._worker.output_line.connect(self._print)
        self._worker.finished.connect(lambda ok, out: self._on_done(ok, out, "فحص SFC"))
        self._worker.start()

    def _do_dism(self):
        if not show_admin_warning(self):
            return
        if not confirm_action(
            "سيقوم DISM RestoreHealth بإصلاح مخزن مكونات Windows.\n\n"
            "قد تستغرق هذه العملية من 20 إلى 30 دقيقة وتحتاج إلى اتصال بالإنترنت.\n\n"
            "هل تريد المتابعة؟",
            self,
        ):
            return
        self._clear_output()
        self._print("► جارٍ تشغيل DISM RestoreHealth (قد يستغرق 20–30 دقيقة)…\n")
        self._set_running(True)
        from src.core.windows_repair import run_dism

        self._worker = StreamingWorker(run_dism)
        self._worker.output_line.connect(self._print)
        self._worker.finished.connect(lambda ok, out: self._on_done(ok, out, "إصلاح DISM"))
        self._worker.start()

    # ── Service management ─────────────────────────────────────────────

    def _refresh_services(self):
        try:
            from src.core.service_manager import get_all_managed_statuses

            statuses = get_all_managed_statuses()
            self._svc_table.populate(statuses, self._restart_service)
        except Exception as exc:
            log.error(f"Service refresh error: {exc}")

    def _restart_service(self, display_name: str):
        if not show_admin_warning(self):
            return
        if not confirm_action(
            f"هل تريد إعادة تشغيل الخدمة '{display_name}'؟\n\nقد يؤدي ذلك إلى انقطاع مؤقت للخدمة.",
            self,
        ):
            return
        from src.core.service_manager import MANAGED_SERVICES, restart_service

        short_name = MANAGED_SERVICES.get(display_name, display_name)
        self._print(f"\n► جارٍ إعادة تشغيل {display_name}…")
        ok, msg = restart_service(short_name)
        self._print(msg)
        log_action(f"إعادة تشغيل الخدمة: {display_name}", "Success" if ok else "Failed", msg)
        self._refresh_services()

    def on_show(self):
        self._refresh_services()
