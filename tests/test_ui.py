"""اختبارات التنقل واللغة والثيم والإغلاق باستخدام خيوط نظام محاكاة."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("IT_TOOLKIT_DATA_DIR", str(Path(__file__).parent / "artifacts" / "data"))
os.environ.setdefault("UI_SCREENSHOTS", str(Path(__file__).parent / "artifacts" / "screenshots"))
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication, QGroupBox, QLabel, QTabWidget

from src.database.init_db import get_setting, initialize_database
from src.ui.main_window import MainWindow
from src.utils.lang import set_lang
from src.utils.ui_text import QComboBox, localize
from src.utils.workers import ManagedThread, active_workers

app = QApplication.instance() or QApplication([])
app.setStyle("Fusion")
QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")
with patch("src.utils.app_paths.legacy_roots", return_value=[]):
    initialize_database()


class UITests(unittest.TestCase):
    def setUp(self):
        self.no_workers = patch.object(ManagedThread, "start", return_value=None)
        self.no_workers.start()
        set_lang(os.environ.get("TEST_LANGUAGE", "ar"))
        app.setLayoutDirection(
            Qt.RightToLeft if os.environ.get("TEST_LANGUAGE", "ar") == "ar" else Qt.LeftToRight
        )
        from src.database.init_db import save_setting

        save_setting("theme", "dark")
        self.window = MainWindow()
        self.window.resize(1240, 680)
        self.window.show()
        app.processEvents()

    def tearDown(self):
        self.window._restart_on_close = False
        self.window.close()
        self.window.deleteLater()
        app.processEvents()
        self.no_workers.stop()

    def test_navigation_all_pages_and_dimensions(self):
        self.assertLessEqual(self.window.minimumWidth(), 800)
        self.assertLessEqual(self.window.minimumHeight(), 600)
        for index in range(13):
            self.window._navigate(index)
            app.processEvents()
            self.assertEqual(self.window.stack.currentIndex(), index)
        for index, name in [(0, "dashboard"), (4, "network"), (9, "security"), (12, "settings")]:
            self.window._navigate(index)
            app.processEvents()
            out = Path(os.environ["UI_SCREENSHOTS"])
            out.mkdir(parents=True, exist_ok=True)
            self.assertTrue(
                self.window.grab().save(
                    str(
                        out
                        / f"{name}-{os.environ.get('TEST_LANGUAGE', 'ar')}-{os.environ.get('QT_SCALE_FACTOR', '1')}.png"
                    )
                )
            )

    def test_language_labels_and_canonical_filter_data(self):
        combo = QComboBox()
        combo.addItems(["الكل", "طابعات"])
        combo.setCurrentIndex(0)
        self.assertEqual(combo.currentText(), "الكل")
        set_lang("en")
        self.assertEqual(localize("↻  تحديث"), "↻ Refresh")
        self.assertEqual(localize("عنوان IP:"), "IP address:")
        self.assertEqual(localize("الطابعات والماسحات"), "Printers and scanners")

    def test_security_cards_unknown_and_public_profile(self):
        page = self.window._pages[9]
        page._on_done(
            dict(
                security_center={"antivirus": [], "query_ok": False},
                firewall={"domain": True, "private": True, "public": False},
                bitlocker={
                    "status": "FullyEncrypted",
                    "protection_enabled": False,
                    "enabled": False,
                },
                nca=[dict(title="Dummy", passed=None, note="Unavailable")],
                installed=[],
            )
        )
        self.assertIn("Public:", page._card_fw._lbl_status.text())
        self.assertIn(localize("معطّل"), page._card_fw._lbl_status.text())
        self.assertEqual(page._nca_table.item(0, 2).text(), localize("غير معروف"))
        self.assertEqual(page._score_bar.value(), 0)

    def test_theme_setting_saved(self):
        self.window.apply_theme("light")
        self.assertEqual(get_setting("theme"), "light")
        self.window.apply_theme("dark")

    def test_absolute_text_alignment_and_theme_keys(self):
        for label in self.window._pages[12].findChildren(QLabel):
            self.assertTrue(label.alignment() & Qt.AlignmentFlag.AlignAbsolute)
        self.assertEqual(self.window._pages[12]._theme_combo.currentText(), "dark")

    def test_network_diagnostics_not_rerun_on_ui_thread(self):
        page = self.window._pages[7]
        with patch(
            "src.core.network_tools.run_full_network_diagnostics",
            side_effect=AssertionError("Must not rerun"),
        ):
            page._show_net_results(
                {
                    "ip_config": {},
                    "ping_gateway": {},
                    "ping_google_dns": {},
                    "ping_cloudflare_dns": {},
                }
            )
        self.assertIn("8.8.8.8", page._output.toPlainText())

    def test_small_window_reflows_cards_and_keeps_settings_visible(self):
        self.window.resize(760, 480)
        self.window._navigate(0)
        app.processEvents()
        self.assertLessEqual(self.window._pages[0]._card_grid._columns, 2)
        settings = self.window._nav_buttons[-1]
        self.assertTrue(settings.isVisible())
        from PySide6.QtCore import QPoint

        top = settings.mapTo(self.window, QPoint(0, 0)).y()
        self.assertLess(top + settings.height(), self.window.height())
        self.window._navigate(9)
        app.processEvents()
        self.assertLessEqual(self.window._pages[9]._feature_grid._columns, 2)

    def test_theme_still_applies_after_card_update(self):
        self.window.apply_theme("light")
        card = self.window._pages[0]._card_device
        card.set_value("Dummy", "#dcdfe4")
        card.set_accent("#3fb950")
        self.assertIn("#1e293b", card._value_lbl.styleSheet())
        self.assertIn("#ffffff", card.styleSheet())
        self.window.apply_theme("dark")
        self.assertIn("#dcdfe4", card._value_lbl.styleSheet())

    def test_failed_theme_write_preserves_current_theme(self):
        previous = self.window._current_theme
        page = self.window._pages[12]
        page._theme_combo.setCurrentText("light")
        with (
            patch("src.database.connection.execute_write", return_value=-1),
            patch("src.ui.settings_page.QMessageBox.warning") as warning,
        ):
            page._apply_theme()
            warning.assert_called_once()
        self.assertEqual(self.window._current_theme, previous)

    def test_saved_theme_survives_new_window(self):
        self.window.apply_theme("light")
        another = MainWindow()
        self.assertEqual(another._current_theme, "light")
        self.assertEqual(get_setting("theme"), "light")
        another.close()
        another.deleteLater()
        app.processEvents()

    def test_dynamic_recommendations_display_in_both_languages(self):
        from src.core.recommendations import generate_recommendations
        from src.utils.lang import get_lang

        data = {
            "cpu": {"usage_pct": 95},
            "ram": {"usage_pct": 95, "total_gb": 4},
            "antivirus": {"name": "Unknown"},
            "windows_update": {"service_status": "Unknown"},
            "network": {"connected": False},
        }
        recs = generate_recommendations(data)
        self.window._pages[3]._pop_recs({"recommendations": recs})
        content = self.window._pages[3]._recs_text.toPlainText()
        self.assertIn("استخدام المعالج" if get_lang() == "ar" else "CPU usage", content)
        self.assertNotIn("CPU usage" if get_lang() == "ar" else "استخدام المعالج", content)

    def test_light_progress_and_combined_bitlocker_translation(self):
        self.window.apply_theme("light")
        page = self.window._pages[9]
        page._on_done(
            dict(
                security_center={"antivirus": [], "query_ok": False},
                firewall={},
                bitlocker={"status": "FullyEncrypted", "protection_enabled": None, "enabled": None},
                nca=[],
                installed=[],
            )
        )
        self.assertIn("#334155", page._score_bar.styleSheet())
        self.assertIn(localize("FullyEncrypted"), page._card_bitlocker._lbl_status.text())

    def test_history_shows_only_action_log_and_full_output(self):
        page = self.window._pages[11]
        tabs = page.findChildren(QTabWidget)
        self.assertEqual(len(tabs), 1)
        self.assertEqual(tabs[0].count(), 1)
        self.assertEqual(tabs[0].tabText(0), localize("سجل العمليات"))
        self.assertFalse(hasattr(page, "_health_table"))
        self.assertFalse(hasattr(page, "_reports_page"))
        output = "Dummy action result\nFull details"
        row = {
            "executed_at": "2026-10-02",
            "action_name": "Dummy action",
            "status": "Success",
            "output": output,
        }
        with patch("src.ui.history_page.get_action_logs", return_value=[row]):
            self.window._navigate(11)
        self.assertEqual(page._action_table.rowCount(), 1)
        page._action_table.setCurrentCell(0, 0)
        self.assertEqual(page._action_output.toPlainText(), output)
        with patch("src.ui.history_page.get_action_logs", return_value=[]):
            page.on_show()
        self.assertEqual(page._action_table.rowCount(), 0)
        self.assertEqual(page._action_output.toPlainText(), "")

    def test_settings_has_no_database_section_and_linkedin_is_clickable(self):
        page = self.window._pages[12]
        self.assertEqual(len(page.findChildren(QGroupBox)), 2)
        self.assertFalse(hasattr(page, "_backup_database"))
        labels = page.findChildren(QLabel)
        author = next(
            label
            for label in labels
            if "https://www.linkedin.com/in/meshal-alfaifi-cs" in label.text()
        )
        self.assertTrue(author.openExternalLinks())
        self.assertIn("href='https://www.linkedin.com/in/meshal-alfaifi-cs'", author.text())
        self.assertIn("https://github.com/MeshalAlfaifi0", author.text())
        from src.utils.lang import get_lang

        self.assertIn("المؤلف:" if get_lang() == "ar" else "Author:", author.text())

    def test_application_branding_has_no_version_badge(self):
        self.assertEqual(self.window.windowTitle(), "IT Operations Console")
        labels = [label.text() for label in self.window.findChildren(QLabel)]
        self.assertTrue(any(label == "IT Operations Console" for label in labels))
        about = next(
            label for label in labels if "https://www.linkedin.com/in/meshal-alfaifi-cs" in label
        )
        self.assertIn("IT Operations Console", about)
        self.assertFalse(
            any("2.0.0" in label or "IT Support Toolkit Pro" in label for label in labels)
        )

    def test_heading_and_compact_navigation(self):
        self.assertIn("font-size:24px", self.window._pages[0]._card_device._value_lbl.styleSheet())
        for button in self.window._nav_buttons:
            self.assertLessEqual(button.height(), 40)
            self.assertGreaterEqual(button.height(), 34)

    def test_close_waits_for_running_worker_without_destroying_thread(self):
        self.no_workers.stop()

        class SlowWorker(ManagedThread):
            def run(self):
                time.sleep(0.3)

        worker = SlowWorker()
        worker.start()
        # Replace page's reference to prove strong lifecycle retention.
        self.window._pages[0]._worker = None
        self.window.close()
        self.assertTrue(self.window.isVisible())
        self.assertTrue(self.window._closing)
        deadline = time.monotonic() + 5
        while self.window.isVisible() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.02)
        self.assertFalse(self.window.isVisible())
        self.assertFalse(active_workers())
        self.no_workers.start()


if __name__ == "__main__":
    unittest.main(verbosity=2)
