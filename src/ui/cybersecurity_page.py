"""عرض مؤشرات الأمان وحالات الحماية المفعلة والمعطلة والمجهولة بصورة مستقلة.
المؤلف: Meshal Alfaifi."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QHeaderView, QScrollArea, QVBoxLayout, QWidget

from src.utils.lang import text as tx
from src.utils.lang import tr
from src.utils.logger import setup_logger
from src.utils.responsive_grid import ResponsiveGrid
from src.utils.ui_style import style_widget
from src.utils.ui_text import (
    QGroupBox,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)
from src.utils.workers import ManagedThread as QThread

log = setup_logger(__name__)


# ── Background worker ─────────────────────────────────────────────────────


class CyberWorker(QThread):
    """يشغّل فحوصات الأمن في thread منفصل حتى ما تتجمد الواجهة."""

    done = Signal(dict)

    def run(self):
        try:
            from src.core.cybersecurity import get_full_security_status

            self.done.emit(get_full_security_status())
        except Exception as exc:
            log.error(f"CyberWorker error: {exc}")
            self.done.emit({})


# ── بطاقة حالة صغيرة ─────────────────────────────────────────────────────


class StatusCard(QFrame):
    """بطاقة تعرض اسم ميزة أمنية وحالتها."""

    _GREEN = "#3fb950"
    _RED = "#f85149"
    _YELLOW = "#d29922"

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(190, 88)
        self._update_style("#30363d")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)

        self._lbl_title = QLabel(title)
        self._lbl_title.setStyleSheet("color:#8b949e; font-size:12px; font-weight:bold;")
        lay.addWidget(self._lbl_title)

        self._lbl_status = QLabel("—")
        self._lbl_status.setWordWrap(True)
        self._lbl_status.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lay.addWidget(self._lbl_status)
        lay.addStretch()

    def _update_style(self, border_color: str):
        style_widget(
            self,
            f"StatusCard {{ background:#161b22; border:1.5px solid {border_color}; "
            "border-radius:10px; }}",
        )

    def set_ok(self, text: str, ok: bool, warn: bool = False):
        color = self._GREEN if ok is True else (self._YELLOW if warn or ok is None else self._RED)
        self._lbl_status.setText(text)
        self._lbl_status.setStyleSheet(f"color:{color}; font-size:13px; font-weight:bold;")
        self._update_style(color if not ok else "#30363d")


# ── صفحة الأمن السيبراني ─────────────────────────────────────────────────


class CybersecurityPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: CyberWorker | None = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # ── رأس الصفحة ────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel(tr("cyber_title"))
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        hdr.addWidget(title)
        hdr.addStretch()

        self._scan_btn = QPushButton("🔍  " + tr("cyber_scan"))
        self._scan_btn.setFixedSize(160, 38)
        self._scan_btn.setStyleSheet(
            "QPushButton{background:#1f6feb;color:#f0f6fc;"
            "border:none;border-radius:8px;font-size:13px;font-weight:bold;}"
            "QPushButton:hover{background:#388bfd;}"
            "QPushButton:disabled{background:#21262d;color:#484f58;}"
        )
        self._scan_btn.clicked.connect(self._run_scan)
        hdr.addWidget(self._scan_btn)
        root.addLayout(hdr)

        sub = QLabel(
            tx(
                "فحوصات محلية إرشادية؛ لا تثبت الامتثال المؤسسي أو غياب الثغرات. الحالة المجهولة تعني تعذّر التحقق.",
                "Local checks only; they do not prove organisational compliance or absence of vulnerabilities. Unknown means verification was unavailable.",
            )
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("color:#8b949e; font-size:12px;")
        root.addWidget(sub)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color:#8b949e; font-size:12px;")
        root.addWidget(self._status_lbl)

        # ── منطقة التمرير ─────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        self._inner_lay = QVBoxLayout(inner)
        self._inner_lay.setSpacing(16)
        scroll.setWidget(inner)
        root.addWidget(scroll, stretch=1)

        # ── شريط نتيجة الأمان ─────────────────────────────────────────
        score_grp = QGroupBox(tr("cyber_score"))
        score_lay = QVBoxLayout(score_grp)
        self._score_bar = QProgressBar()
        self._score_bar.setRange(0, 100)
        self._score_bar.setValue(0)
        self._score_bar.setFixedHeight(24)
        self._score_bar.setFormat("%v / 100")
        score_lay.addWidget(self._score_bar)
        self._score_lbl = QLabel("—")
        self._score_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._score_lbl.setStyleSheet("font-size:13px;")
        score_lay.addWidget(self._score_lbl)
        self._inner_lay.addWidget(score_grp)

        # ── بطاقات حالة الميزات الأساسية ─────────────────────────────
        feat_grp = QGroupBox("حالة ميزات الحماية الأساسية")
        feat_layout = QVBoxLayout(feat_grp)
        feat_content = ResponsiveGrid(max_columns=3, card_width=205)
        self._feature_grid = feat_content
        feat_layout.addWidget(feat_content)

        self._card_av = StatusCard(tr("cyber_antivirus"))
        self._card_fw = StatusCard(tr("cyber_firewall"))
        self._card_defender = StatusCard(tr("cyber_defender"))
        self._card_bitlocker = StatusCard(tr("cyber_bitlocker"))
        self._card_uac = StatusCard(tr("cyber_uac"))
        self._card_ss = StatusCard(tr("cyber_smartscreen"))

        cards = [
            self._card_av,
            self._card_fw,
            self._card_defender,
            self._card_bitlocker,
            self._card_uac,
            self._card_ss,
        ]
        feat_content.set_cards(cards)
        self._inner_lay.addWidget(feat_grp)

        # ── قائمة معايير NCA ──────────────────────────────────────────
        nca_grp = QGroupBox(
            tx(
                "مؤشرات أمن محلية — ليست شهادة امتثال NCA",
                "Local security indicators — not NCA compliance certification",
            )
        )
        nca_lay = QVBoxLayout(nca_grp)
        self._nca_table = QTableWidget(0, 4)
        self._nca_table.setHorizontalHeaderLabels(["المعيار", "رقم ECC", "النتيجة", "الملاحظة"])
        hh = self._nca_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._nca_table.verticalHeader().setVisible(False)
        self._nca_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._nca_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._nca_table.setAlternatingRowColors(True)
        self._nca_table.setMinimumHeight(280)
        nca_lay.addWidget(self._nca_table)
        self._inner_lay.addWidget(nca_grp)

        # ── جدول البرامج الأمنية المثبّتة ────────────────────────────
        inst_grp = QGroupBox(tr("cyber_installed"))
        inst_lay = QVBoxLayout(inst_grp)

        self._inst_summary = QLabel("")
        self._inst_summary.setStyleSheet("color:#8b949e; font-size:12px; padding-bottom:4px;")
        inst_lay.addWidget(self._inst_summary)

        self._inst_table = QTableWidget(0, 5)
        self._inst_table.setHorizontalHeaderLabels(
            [
                tr("cyber_name_col"),
                "الفئة",
                tr("cyber_publisher_col"),
                tr("cyber_version_col"),
                "تاريخ التثبيت",
            ]
        )
        ih = self._inst_table.horizontalHeader()
        ih.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        ih.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        ih.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        ih.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        ih.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._inst_table.verticalHeader().setVisible(False)
        self._inst_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._inst_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._inst_table.setAlternatingRowColors(True)
        inst_lay.addWidget(self._inst_table)
        self._inner_lay.addWidget(inst_grp)

        self._inner_lay.addStretch()

    # ── الفحص ─────────────────────────────────────────────────────────

    def _run_scan(self):
        if self._worker and self._worker.isRunning():
            return
        self._scan_btn.setEnabled(False)
        self._status_lbl.setText("⏳  جارٍ الفحص الأمني…")
        self._worker = CyberWorker()
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, data: dict):
        self._scan_btn.setEnabled(True)
        if not data:
            self._status_lbl.setText("⚠  فشل الفحص.")
            return

        from datetime import datetime

        self._status_lbl.setText(f"✅  آخر فحص: {datetime.now().strftime('%H:%M:%S')}")

        # ── بطاقات الميزات ───────────────────────────────────────────
        sc = data.get("security_center", {})
        av_list = sc.get("antivirus", [])
        av_ok = any(a["enabled"] for a in av_list) if sc.get("query_ok") else None
        av_name = av_list[0]["name"] if av_list else tr("av_unknown")
        self._card_av.set_ok(
            av_name[:24]
            if av_ok
            else (tr("av_unknown") if av_ok is None else tx("غير موجود", "Not detected")),
            av_ok,
        )

        fw = data.get("firewall", {})
        from src.core.cybersecurity import firewall_assessment

        def state_text(value):
            return (
                tr("av_unknown")
                if value is None
                else tr("cyber_enabled" if value else "cyber_disabled")
            )

        fw_ok = firewall_assessment(fw)
        self._card_fw.set_ok(
            "\n".join(
                f"{name.title()}: {state_text(fw.get(name))}"
                for name in ("domain", "private", "public")
            ),
            fw_ok,
        )

        wd = data.get("defender", {})
        self._card_defender.set_ok(
            state_text(wd.get("realtime")),
            wd.get("realtime"),
        )

        bl = data.get("bitlocker", {})
        self._card_bitlocker.set_ok(
            f"{bl.get('status', 'Unknown')}\n{tx('الحماية', 'Protection')}: {state_text(bl.get('protection_enabled'))}",
            bl.get("enabled"),
        )

        uac = data.get("uac", {})
        self._card_uac.set_ok(state_text(uac.get("enabled")), uac.get("enabled"))

        ss = data.get("smartscreen", {})
        self._card_ss.set_ok(state_text(ss.get("enabled")), ss.get("enabled"))

        # ── جدول NCA ─────────────────────────────────────────────────
        nca_checks = data.get("nca", [])
        self._nca_table.setRowCount(0)
        passed = 0
        for check in nca_checks:
            r = self._nca_table.rowCount()
            self._nca_table.insertRow(r)
            self._nca_table.setItem(r, 0, QTableWidgetItem(check["title"]))
            self._nca_table.setItem(r, 1, QTableWidgetItem(check.get("standard", "")))

            ok = check["passed"]
            result_item = QTableWidgetItem(
                tr("av_unknown")
                if ok is None
                else (tx("✔ متحقق", "✔ Verified") if ok else tx("✖ غير متحقق", "✖ Not verified"))
            )
            result_item.setForeground(
                QColor("#d29922")
                if ok is None
                else (QColor("#3fb950") if ok else QColor("#f85149"))
            )
            result_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self._nca_table.setItem(r, 2, result_item)
            self._nca_table.setItem(r, 3, QTableWidgetItem(check.get("note", "")))
            if ok:
                passed += 1

        # ── النتيجة الإجمالية ─────────────────────────────────────────
        total = len(nca_checks) if nca_checks else 1
        score = int((passed / total) * 100)
        self._score_bar.setValue(score)
        unknown = sum(c["passed"] is None for c in nca_checks)
        if score >= 80:
            color, _label = "#3fb950", "ممتاز — مستوى حماية عالٍ"
        elif score >= 60:
            color, _label = "#d29922", "جيد — يوصى بتحسين بعض الإعدادات"
        else:
            color, _label = "#f85149", "ضعيف — يتطلب اتخاذ إجراءات عاجلة"

        self._score_bar.setStyleSheet(
            f"QProgressBar {{ background:#21262d; border:1px solid #30363d; "
            f"border-radius:8px; text-align:center; color:#f0f6fc; height:24px; font-weight:bold; }}"
            f"QProgressBar::chunk {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {color},stop:1 {color}cc); border-radius:7px; }}"
        )
        self._score_lbl.setText(
            tx(
                f"مؤشرات متحققة: {passed}/{total}؛ مجهولة: {unknown}. النسبة إرشادية فقط.",
                f"Verified indicators: {passed}/{total}; unknown: {unknown}. Indicative percentage only.",
            )
        )
        self._score_lbl.setStyleSheet("color:#8b949e; font-weight:bold; font-size:13px;")
        self._score_lbl.setWordWrap(True)

        # ── جدول البرامج الأمنية ──────────────────────────────────────
        installed = data.get("installed", [])
        self._inst_table.setRowCount(0)

        # ألوان الفئات
        cat_colors = {
            "مكافح فيروسات": "#3fb950",
            "جدار حماية": "#58a6ff",
            "EDR / الكشف والاستجابة": "#d2a8ff",
            "DLP / منع تسرب البيانات": "#ffa657",
            "MDM / إدارة الأجهزة": "#79c0ff",
            "SIEM / مراقبة الأحداث": "#f2cc60",
            "VPN / الشبكة الخاصة": "#7ee787",
            "إدارة الهوية والوصول": "#e3b341",
            "أمن عام": "#8b949e",
        }

        for sw in installed:
            r = self._inst_table.rowCount()
            self._inst_table.insertRow(r)
            self._inst_table.setItem(r, 0, QTableWidgetItem(sw.get("name", "")))

            cat = sw.get("category", "أمن عام")
            cat_item = QTableWidgetItem(cat)
            cat_item.setForeground(QColor(cat_colors.get(cat, "#8b949e")))
            cat_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self._inst_table.setItem(r, 1, cat_item)

            self._inst_table.setItem(r, 2, QTableWidgetItem(sw.get("publisher", "")))
            self._inst_table.setItem(r, 3, QTableWidgetItem(sw.get("version", "")))
            self._inst_table.setItem(r, 4, QTableWidgetItem(sw.get("install_date", "")))

        if not installed:
            self._inst_table.setRowCount(1)
            self._inst_table.setItem(0, 0, QTableWidgetItem("لم يتم العثور على برامج أمنية مثبّتة."))

        count_by_cat: dict[str, int] = {}
        for sw in installed:
            cat = sw.get("category", "أمن عام")
            count_by_cat[cat] = count_by_cat.get(cat, 0) + 1

        summary = "  |  ".join(f"{cat}: {n}" for cat, n in count_by_cat.items())
        self._inst_summary.setText(f"إجمالي البرامج المكتشفة: {len(installed)}   —   {summary}")

    def on_show(self):
        """يشغّل الفحص عند فتح الصفحة."""
        self._run_scan()
