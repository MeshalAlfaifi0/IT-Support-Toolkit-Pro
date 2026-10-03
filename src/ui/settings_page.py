"""
صفحة الإعدادات — تبديل الثيم واللغة ومعلومات البرنامج.
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QVBoxLayout, QWidget

from src.database.init_db import get_setting, save_setting
from src.utils.branding import APP_TITLE
from src.utils.lang import get_lang, tr
from src.utils.lang import text as tx
from src.utils.logger import setup_logger
from src.utils.ui_text import QComboBox, QGroupBox, QLabel, QMessageBox, QPushButton

log = setup_logger(__name__)


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        title = QLabel(tr("settings_title"))
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        root.addWidget(title)

        # ── المظهر ─────────────────────────────────────────────────────
        appear_grp = QGroupBox(tr("settings_appearance"))
        appear_lay = QVBoxLayout(appear_grp)
        appear_lay.setSpacing(14)

        appear_lay.addWidget(QLabel(tr("settings_theme")))
        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["dark", "light"])
        self._theme_combo.setCurrentText(get_setting("theme", "dark"))
        self._theme_combo.setFixedWidth(130)
        appear_lay.addWidget(self._theme_combo)

        self._apply_theme_btn = QPushButton(tr("settings_apply_theme"))
        self._apply_theme_btn.setFixedSize(150, 36)
        self._apply_theme_btn.clicked.connect(self._apply_theme)
        appear_lay.addWidget(self._apply_theme_btn)

        appear_lay.addSpacing(8)

        appear_lay.addWidget(QLabel(tr("settings_language")))
        self._lang_combo = QComboBox()
        self._lang_combo.addItem("العربية", "ar")
        self._lang_combo.addItem("English", "en")
        saved_lang = get_setting("lang", "ar")
        idx = self._lang_combo.findData(saved_lang)
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)
        self._lang_combo.setFixedWidth(130)
        appear_lay.addWidget(self._lang_combo)

        self._apply_lang_btn = QPushButton(tr("settings_apply_lang"))
        self._apply_lang_btn.setFixedSize(150, 36)
        self._apply_lang_btn.clicked.connect(self._apply_language)
        appear_lay.addWidget(self._apply_lang_btn)
        appear_lay.addStretch()
        root.addWidget(appear_grp)

        # ── عن البرنامج ────────────────────────────────────────────────
        about_grp = QGroupBox(tr("settings_about_title"))
        about_lay = QVBoxLayout(about_grp)
        about_lay.setSpacing(10)

        about_info = QLabel(
            tx(
                f"<b style='font-size:15px;'>{APP_TITLE}</b><br>"
                "<span style='color:#8b949e;font-size:12px;'>منصة عمليات تقنية المعلومات</span>"
                "<br><br>"
                "تطبيق سطح مكتب متخصص لمحترفي دعم تقنية المعلومات، "
                "يُمكّن الفنيين من تشخيص أعطال الأجهزة وإدارة الشبكات "
                "وتقييم وضع الأمن السيبراني وتنفيذ مهام الصيانة — "
                "كل ذلك من واجهة موحَّدة وآمنة.<br><br>"
                "<b>المؤلف:</b> &nbsp; Meshal Alfaifi &nbsp;&nbsp;"
                "(<a href='https://github.com/MeshalAlfaifi0' "
                "style='color:#58a6ff;'>GitHub: MeshalAlfaifi0</a>)<br>"
                "<a href='https://www.linkedin.com/in/meshal-alfaifi-cs' "
                "style='color:#58a6ff;'>LinkedIn: Meshal Alfaifi</a><br><br>"
                "<b>نظام التشغيل:</b> &nbsp; Windows 10 / Windows 11",
                f"<b style='font-size:15px;'>{APP_TITLE}</b><br>"
                "<span style='color:#8b949e;font-size:12px;'>IT operations workspace</span>"
                "<br><br>A desktop application for device diagnostics, network management, "
                "local security assessment and maintenance.<br><br>"
                "<b>Author:</b> &nbsp; Meshal Alfaifi &nbsp;&nbsp;"
                "(<a href='https://github.com/MeshalAlfaifi0' "
                "style='color:#58a6ff;'>GitHub: MeshalAlfaifi0</a>)<br>"
                "<a href='https://www.linkedin.com/in/meshal-alfaifi-cs' "
                "style='color:#58a6ff;'>LinkedIn: Meshal Alfaifi</a><br><br>"
                "<b>Operating system:</b> &nbsp; Windows 10 / Windows 11",
            )
        )
        about_info.setTextFormat(Qt.TextFormat.RichText)
        about_info.setOpenExternalLinks(True)
        about_info.setWordWrap(True)
        about_info.setStyleSheet("font-size: 13px; padding: 6px;")
        about_lay.addWidget(about_info)
        root.addWidget(about_grp)

        root.addStretch()

    # ── إجراءات ───────────────────────────────────────────────────────

    def _apply_theme(self):
        theme = self._theme_combo.currentText()
        w = self.parent()
        while w and not hasattr(w, "apply_theme"):
            w = w.parent()
        try:
            if w:
                w.apply_theme(theme)
            else:
                save_setting("theme", theme)
        except Exception:
            QMessageBox.warning(
                self,
                tr("failed"),
                tx(
                    "تعذّر حفظ الإعداد. تحقق من صلاحية الوصول إلى مجلد البيانات.",
                    "Could not save the setting. Check access to the application data folder.",
                ),
            )
            return
        log.info(f"Theme changed to: {theme}")

    def _apply_language(self):
        lang_code = self._lang_combo.currentData()
        if lang_code == get_lang():
            return

        reply = QMessageBox.question(
            self,
            "تغيير اللغة / Change Language",
            tr("settings_lang_restart"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            save_setting("lang", lang_code)
        except Exception:
            QMessageBox.warning(
                self,
                tr("failed"),
                tx(
                    "تعذّر حفظ اللغة. لم يُعد تشغيل البرنامج.",
                    "Could not save the language. The application was not restarted.",
                ),
            )
            return
        log.info(f"Language changed to: {lang_code} — restarting")

        window = self.window()
        window._restart_on_close = True
        window.close()

    def on_show(self):
        self._theme_combo.setCurrentText(get_setting("theme", "dark"))
        saved_lang = get_setting("lang", "ar")
        idx = self._lang_combo.findData(saved_lang)
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)
