#!/usr/bin/env python3
"""نقطة تشغيل IT Operations Console: تهيئة البيانات ثم اللغة ثم واجهة Qt."""

import json
import os
import sys

from PySide6.QtCore import QLibraryInfo, Qt, QTimer, QTranslator
from PySide6.QtWidgets import QApplication, QMessageBox

from src.utils.branding import APP_TITLE
from src.utils.logger import setup_logger


def main() -> int:
    smoke_test = "--smoke-test" in sys.argv
    if smoke_test:
        # اختبار البدء لا يستخدم بيانات المستخدم؛ المجلد المؤقت يحدده مشغل الاختبار.
        if not os.environ.get("IT_TOOLKIT_DATA_DIR"):
            print("Smoke test requires an isolated IT_TOOLKIT_DATA_DIR.")
            return 2
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

    log = setup_logger("app")
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setOrganizationName("Meshal Alfaifi")
    app.setStyle("Fusion")
    log.info("%s starting…", APP_TITLE)

    try:
        from src.database.init_db import get_setting, initialize_database
        from src.utils.lang import get_lang, set_lang

        # التهيئة مرة واحدة؛ الفشل يُعرض بوضوح ولا يُتجاهل قبل إنشاء الصفحات.
        initialize_database()
        set_lang(get_setting("lang", "ar"))
        app.setLayoutDirection(
            Qt.LayoutDirection.RightToLeft if get_lang() == "ar" else Qt.LayoutDirection.LeftToRight
        )
        translator = QTranslator(app)
        if get_lang() == "ar" and translator.load(
            "qtbase_ar", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        ):
            app.installTranslator(translator)

        from src.ui.main_window import MainWindow

        window = MainWindow()
        # MainWindow يستعيد الثيم دون حفظه مجددًا أو تغيير اختيار المستخدم.
        window.show()
        log.info("Main window displayed.")
        if smoke_test:
            QTimer.singleShot(1500, window.close)
        result = app.exec()

        if smoke_test:
            from src.utils.app_paths import DATA_DIR

            # نتيجة الاختبار لا تضم مواصفات الجهاز أو سجلاته؛ فقط حالة تشغيل الواجهة.
            metadata = {
                "title": window.windowTitle(),
                "pages": len(window._pages),
                "language": get_lang(),
                "theme": window._current_theme,
                "exit_code": result,
            }
            (DATA_DIR / "smoke-result.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        return result
    except Exception as exc:
        log.critical("Failed to launch application: %s", exc, exc_info=True)
        if smoke_test:
            print(f"Smoke test failed: {type(exc).__name__}")
        else:
            QMessageBox.critical(None, APP_TITLE, f"Could not start the application:\n{exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
