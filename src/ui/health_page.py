"""واجهة فحص الصحة والتوصيات، مع بيان الفحوصات غير المتاحة وتغطية التقييم.
المؤلف: Meshal Alfaifi."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QHeaderView, QVBoxLayout, QWidget

from src.utils.formatters import fmt_bytes, fmt_pct
from src.utils.logger import setup_logger
from src.utils.ui_style import style_widget
from src.utils.ui_text import (
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
)
from src.utils.workers import ManagedThread as QThread

log = setup_logger(__name__)


# ── Background worker ─────────────────────────────────────────────────────


class ScanWorker(QThread):
    progress = Signal(int, str)  # (percent, message)
    finished = Signal(dict)  # full scan_data

    def run(self):
        try:
            from src.core.health_checker import run_full_scan

            result = run_full_scan(progress_callback=self.progress.emit)
            self.finished.emit(result)
        except Exception as exc:
            log.error(f"ScanWorker error: {exc}")
            self.finished.emit({"error": str(exc)})


# ── Health Score Circle ───────────────────────────────────────────────────


class ScoreWidget(QFrame):
    """Shows a large coloured health score number."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 160)
        style_widget(
            self,
            "ScoreWidget { background-color: #21262d; border: 2px solid #3d4451; "
            "border-radius: 80px; }",
        )
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._score_lbl = QLabel("—")
        self._score_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._score_lbl.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        layout.addWidget(self._score_lbl)

        self._label_lbl = QLabel("ابدأ الفحص")
        self._label_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label_lbl.setStyleSheet("color: #5c6370; font-size: 13px;")
        layout.addWidget(self._label_lbl)

    def update_score(self, score: int, label: str, color: str):
        self._score_lbl.setText(str(score))
        self._score_lbl.setStyleSheet(f"color: {color}; font-size: 36px; font-weight: bold;")
        self._label_lbl.setText(label)
        self._label_lbl.setStyleSheet(f"color: {color}; font-size: 13px;")
        style_widget(
            self,
            f"ScoreWidget {{ background-color: #21262d; border: 2px solid {color}; "
            "border-radius: 80px; }",
        )


# ── Helpers ───────────────────────────────────────────────────────────────


def _make_table(headers: list[str]) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    t.verticalHeader().setVisible(False)
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    return t


def _add_row(table: QTableWidget, values: list, colors: list[str] | None = None):
    row = table.rowCount()
    table.insertRow(row)
    for col, val in enumerate(values):
        item = QTableWidgetItem(str(val))
        if colors and col < len(colors) and colors[col]:
            item.setForeground(QColor(colors[col]))
        table.setItem(row, col, item)


# ── Health Page ───────────────────────────────────────────────────────────


class HealthPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: ScanWorker | None = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # ── Title row ──────────────────────────────────────────────
        title_row = QHBoxLayout()
        title = QLabel("فحص صحة الجهاز")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #dcdfe4;")
        title_row.addWidget(title)
        title_row.addStretch()

        self._scan_btn = QPushButton("▶  بدء الفحص الكامل")
        self._scan_btn.setFixedSize(160, 40)
        self._scan_btn.setStyleSheet(
            "QPushButton { background-color: #3fb950; color: #1e2128; "
            "border: none; border-radius: 8px; font-size: 14px; font-weight: bold; }"
            "QPushButton:hover { background-color: #58d068; }"
            "QPushButton:disabled { background-color: #3d4451; color: #5c6370; }"
        )
        self._scan_btn.clicked.connect(self._start_scan)
        title_row.addWidget(self._scan_btn)
        root.addLayout(title_row)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        self._progress.setFixedHeight(8)
        root.addWidget(self._progress)

        self._status_lbl = QLabel("اضغط 'بدء الفحص الكامل' لبدء فحص صحة الجهاز.")
        self._status_lbl.setStyleSheet("color: #5c6370; font-size: 12px;")
        root.addWidget(self._status_lbl)

        # ── Score + tabs row ────────────────────────────────────────
        body = QHBoxLayout()
        root.addLayout(body, stretch=1)

        # Score widget on left
        score_col = QVBoxLayout()
        score_col.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self._score_widget = ScoreWidget()
        score_col.addWidget(self._score_widget)
        score_col.addSpacing(16)

        self._score_breakdown = QTextEdit()
        self._score_breakdown.setReadOnly(True)
        self._score_breakdown.setMaximumWidth(180)
        self._score_breakdown.setMaximumHeight(200)
        self._score_breakdown.setPlaceholderText("تفاصيل الدرجة\nتظهر هنا…")
        score_col.addWidget(self._score_breakdown)
        score_col.addStretch()

        body.addLayout(score_col)
        body.addSpacing(16)

        # Tabs for results
        self._tabs = QTabWidget()
        body.addWidget(self._tabs, stretch=1)

        self._tab_cpu = self._make_cpu_tab()
        self._tab_ram = self._make_ram_tab()
        self._tab_disk = self._make_disk_tab()
        self._tab_av = self._make_av_tab()
        self._tab_ev = self._make_ev_tab()
        self._tab_start = self._make_startup_tab()
        self._tab_recs = self._make_recs_tab()

        self._tabs.addTab(self._tab_cpu, "المعالج CPU")
        self._tabs.addTab(self._tab_ram, "الذاكرة RAM")
        self._tabs.addTab(self._tab_disk, "القرص الصلب")
        self._tabs.addTab(self._tab_av, "الحماية والتحديثات")
        self._tabs.addTab(self._tab_ev, "سجل الأحداث")
        self._tabs.addTab(self._tab_start, "تطبيقات بدء التشغيل")
        self._tabs.addTab(self._tab_recs, "التوصيات")

    # ── Tab builders ───────────────────────────────────────────────────

    def _make_cpu_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self._cpu_info_lbl = QLabel("قم بالفحص لعرض تفاصيل المعالج.")
        self._cpu_info_lbl.setStyleSheet("color: #5c6370;")
        lay.addWidget(self._cpu_info_lbl)
        self._cpu_proc_table = _make_table(["PID", "اسم العملية", "استخدام CPU %"])
        lay.addWidget(self._cpu_proc_table)
        return w

    def _make_ram_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self._ram_info_lbl = QLabel("قم بالفحص لعرض تفاصيل الذاكرة.")
        self._ram_info_lbl.setStyleSheet("color: #5c6370;")
        lay.addWidget(self._ram_info_lbl)
        self._ram_proc_table = _make_table(["PID", "اسم العملية", "الذاكرة (MB)"])
        lay.addWidget(self._ram_proc_table)
        return w

    def _make_disk_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self._disk_table = _make_table(
            ["محرك الأقراص", "الحجم الكلي", "المستخدم", "المتاح", "نسبة الاستخدام", "النوع"]
        )
        lay.addWidget(self._disk_table)
        return w

    def _make_av_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self._av_lbl = QLabel("قم بالفحص لعرض حالة برنامج الحماية والتحديثات.")
        self._av_lbl.setStyleSheet("color: #5c6370;")
        lay.addWidget(self._av_lbl)
        lay.addStretch()
        return w

    def _make_ev_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self._ev_summary_lbl = QLabel("")
        lay.addWidget(self._ev_summary_lbl)
        self._ev_table = _make_table(["الوقت", "السجل", "النوع", "المصدر", "الرسالة"])
        lay.addWidget(self._ev_table)
        return w

    def _make_startup_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self._startup_table = _make_table(["الاسم", "الأمر"])
        self._startup_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        lay.addWidget(self._startup_table)
        return w

    def _make_recs_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self._recs_text = QTextEdit()
        self._recs_text.setReadOnly(True)
        self._recs_text.setPlaceholderText("ستظهر التوصيات هنا بعد الفحص.")
        lay.addWidget(self._recs_text)
        return w

    # ── Scan control ───────────────────────────────────────────────────

    def _start_scan(self):
        if self._worker and self._worker.isRunning():
            return
        self._scan_btn.setEnabled(False)
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._status_lbl.setText("جارٍ الفحص…")
        self._clear_results()

        self._worker = ScanWorker()
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_scan_done)
        self._worker.start()

    def _on_progress(self, pct: int, msg: str):
        self._progress.setValue(pct)
        self._status_lbl.setText(msg)

    def _on_scan_done(self, data: dict):
        self._scan_btn.setEnabled(True)
        self._progress.setValue(100)

        if data.get("error"):
            self._status_lbl.setText(f"فشل الفحص: {data['error']}")
            return

        self._status_lbl.setText(f"اكتمل الفحص — {data.get('scan_timestamp', '')}")
        self._populate(data)
        self._tabs.setCurrentIndex(6)  # jump to Recommendations

    def _clear_results(self):
        for table in (
            self._cpu_proc_table,
            self._ram_proc_table,
            self._disk_table,
            self._ev_table,
            self._startup_table,
        ):
            table.setRowCount(0)
        self._recs_text.clear()
        self._score_breakdown.clear()

    # ── Populate tabs from scan data ───────────────────────────────────

    def _populate(self, data: dict):
        self._pop_cpu(data)
        self._pop_ram(data)
        self._pop_disk(data)
        self._pop_av(data)
        self._pop_ev(data)
        self._pop_startup(data)
        self._pop_score(data)
        self._pop_recs(data)

    def _pop_cpu(self, data: dict):
        cpu = data.get("cpu", {})
        pct = cpu.get("usage_pct", 0)
        color = "#3fb950" if pct < 60 else ("#e5c07b" if pct < 85 else "#e06c75")
        self._cpu_info_lbl.setText(
            f"CPU: {cpu.get('name', 'Unknown')}  |  "
            f"Cores: {cpu.get('physical_cores', '?')} physical / "
            f"{cpu.get('logical_cores', '?')} logical  |  "
            f"Usage: {fmt_pct(pct)}"
        )
        self._cpu_info_lbl.setStyleSheet(f"color: {color};")

        self._cpu_proc_table.setRowCount(0)
        for proc in data.get("cpu_top_processes", []):
            _add_row(
                self._cpu_proc_table,
                [
                    proc.get("pid", ""),
                    proc.get("name", ""),
                    f"{proc.get('cpu_percent', 0):.1f}%",
                ],
            )

    def _pop_ram(self, data: dict):
        ram = data.get("ram", {})
        pct = ram.get("usage_pct", 0)
        color = "#3fb950" if pct < 70 else ("#e5c07b" if pct < 85 else "#e06c75")
        self._ram_info_lbl.setText(
            f"Total: {fmt_bytes(ram.get('total', 0))}  |  "
            f"Used: {fmt_bytes(ram.get('used', 0))}  |  "
            f"Available: {fmt_bytes(ram.get('available', 0))}  |  "
            f"Usage: {fmt_pct(pct)}"
        )
        self._ram_info_lbl.setStyleSheet(f"color: {color};")

        self._ram_proc_table.setRowCount(0)
        for proc in data.get("ram_top_processes", []):
            _add_row(
                self._ram_proc_table,
                [
                    proc.get("pid", ""),
                    proc.get("name", ""),
                    f"{proc.get('ram_mb', 0):.1f}",
                ],
            )

    def _pop_disk(self, data: dict):
        self._disk_table.setRowCount(0)
        for disk in data.get("disks", []):
            pct = disk.get("usage_pct", 0)
            color = "#3fb950" if pct < 80 else ("#e5c07b" if pct < 90 else "#e06c75")
            _add_row(
                self._disk_table,
                [
                    disk.get("mountpoint", "?"),
                    fmt_bytes(disk.get("total", 0)),
                    fmt_bytes(disk.get("used", 0)),
                    fmt_bytes(disk.get("free", 0)),
                    fmt_pct(pct),
                    disk.get("disk_type", "Unknown"),
                ],
                colors=[None, None, None, None, color, None],
            )

    def _pop_av(self, data: dict):
        av = data.get("antivirus", {})
        df = data.get("defender", {})
        wu = data.get("windows_update", {})
        av_color = (
            "#3fb950"
            if av.get("enabled") is True
            else ("#e06c75" if av.get("enabled") is False else "#e5c07b")
        )
        df_color = (
            "#3fb950"
            if df.get("enabled") is True
            else ("#e06c75" if df.get("enabled") is False else "#e5c07b")
        )
        text = (
            f"<b>Antivirus</b><br>"
            f"Name: {av.get('name', 'Unknown')}<br>"
            f"Status: <span style='color:{av_color}'>"
            f"{av.get('status', 'Unknown')}</span><br><br>"
            f"<b>Windows Defender</b><br>"
            f"Real-time Protection: "
            f"<span style='color:{df_color}'>"
            f"{df.get('status', 'Unknown')}</span><br>"
            f"Last Update: {df.get('last_update', 'Unknown')}<br><br>"
            f"<b>Windows Update Service</b><br>"
            f"Status: {wu.get('service_status', 'Unknown')}<br>"
            f"Pending Updates: {wu.get('pending_updates', 'Unknown')}"
        )
        self._av_lbl.setText(text)
        self._av_lbl.setTextFormat(Qt.TextFormat.RichText)

    def _pop_ev(self, data: dict):
        ev = data.get("event_viewer", {})
        error_msg = ev.get("error_message")

        if error_msg:
            self._ev_summary_lbl.setText(f"⚠ {error_msg}")
            self._ev_summary_lbl.setStyleSheet("color: #e5c07b;")
            return

        self._ev_summary_lbl.setText(
            f"آخر 7 أيام — "
            f"أخطاء: {ev.get('errors', 0)}  "
            f"تحذيرات: {ev.get('warnings', 0)}  "
            f"أحداث قرص: {ev.get('disk', 0)}  "
            f"أحداث تعريف: {ev.get('driver', 0)}  "
            f"تعطل تطبيقات: {ev.get('app_crash', 0)}  "
            f"أخطاء طباعة: {ev.get('print', 0)}"
        )
        self._ev_summary_lbl.setStyleSheet("color: #abb2bf; font-size: 12px;")

        self._ev_table.setRowCount(0)
        for evt in ev.get("events", [])[:200]:
            t = evt.get("type", "")
            color = "#e06c75" if t == "Error" else "#e5c07b"
            _add_row(
                self._ev_table,
                [
                    evt.get("time", ""),
                    evt.get("log", ""),
                    t,
                    evt.get("source", ""),
                    evt.get("message", ""),
                ],
                colors=[None, None, color, None, None],
            )

    def _pop_startup(self, data: dict):
        self._startup_table.setRowCount(0)
        apps = data.get("startup_apps", [])
        for app in apps:
            _add_row(
                self._startup_table,
                [
                    app.get("name", ""),
                    app.get("command", ""),
                ],
            )
        if len(apps) > 8:
            self._startup_table.setStyleSheet("QTableWidget { border: 1px solid #e5c07b; }")

    def _pop_score(self, data: dict):
        hs = data.get("health_score", {})
        score = hs.get("score", 0)
        label = hs.get("label", "Unknown")
        color = hs.get("color", "#61afef")
        self._score_widget.update_score(score, label, color)

        breakdown = hs.get("breakdown", {})
        from src.utils.lang import text as tx

        lines = [
            tx("تفاصيل مؤشرات الصحة", "Health indicator breakdown"),
            tx("تغطية الفحص: ", "Check coverage: ") + str(hs.get("coverage", "?")) + "%",
            tx(
                "تقييم إرشادي؛ حالة خدمة التحديث لا تثبت حداثة التصحيحات.",
                "Indicative score; update service status does not prove current patches.",
            ),
            tx("فحوصات غير متاحة: ", "Unavailable checks: ") + ", ".join(hs.get("unavailable", [])),
        ]
        for k, v in breakdown.items():
            lines.append(f"{k.replace('_', ' ').title():<16}: {v:.0f}")
        self._score_breakdown.setPlainText("\n".join(lines))

    def _pop_recs(self, data: dict):
        recs = data.get("recommendations", [])
        if not recs:
            self._recs_text.setPlainText(
                "لا توجد توصيات ضمن الفحوصات المتاحة؛ راجع الحالات غير المعروفة."
            )
            return

        color_map = {"High": "#e06c75", "Medium": "#e5c07b", "Low": "#61afef"}
        html = ""
        for rec in recs:
            priority = rec.get("priority", "")
            category = rec.get("category", "")
            text = rec.get("recommendation", "")
            c = color_map.get(priority, "#abb2bf")
            html += (
                f"<p><span style='color:{c};font-weight:bold;'>"
                f"[{priority}] {category}</span><br>"
                f"{text}</p><hr>"
            )
        self._recs_text.setHtml(html)

    def on_show(self):
        pass
