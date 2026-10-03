"""ترجمة نصوص العرض مع الحفاظ على المفاتيح الأصلية للفلاتر والبيانات."""

import json
import re
from pathlib import Path

from PySide6 import QtWidgets as W
from PySide6.QtCore import Qt

from src.utils.lang import get_lang
from src.utils.ui_style import style_widget, themed_style

_catalog = json.loads(Path(__file__).with_name("ui_translations.json").read_text(encoding="utf-8"))
_pattern = re.compile("|".join(re.escape(key) for key in sorted(_catalog, key=len, reverse=True)))
_ar_catalog = json.loads(
    Path(__file__).with_name("ui_translations_ar.json").read_text(encoding="utf-8")
)
_ar_fragments = {
    "CPU usage is critically high (": "استخدام المعالج مرتفع جدًا (",
    "CPU usage is elevated (": "استخدام المعالج مرتفع (",
    "Identify and close resource-heavy processes.": "حدّد العمليات التي تستهلك الموارد وأغلق ما لا تحتاجه.",
    "Consider closing unnecessary background applications.": "يمكنك إغلاق تطبيقات الخلفية غير الضرورية.",
    "Only ": "المتوفر فقط ",
    " GB of RAM installed. ": " جيجابايت من الذاكرة. ",
    "Upgrading to 8 GB or 16 GB is strongly recommended for better performance.": "يُنصح بترقية الذاكرة إلى 8 أو 16 جيجابايت لتحسين الأداء.",
    "RAM usage is very high (": "استخدام الذاكرة مرتفع جدًا (",
    "RAM usage is elevated (": "استخدام الذاكرة مرتفع (",
    "Close unused applications or consider adding more RAM.": "أغلق التطبيقات غير المستخدمة أو قيّم الحاجة لزيادة الذاكرة.",
    "Monitor for memory leaks or plan a RAM upgrade.": "راقب استهلاك الذاكرة أو قيّم الحاجة لترقيتها.",
    "C: drive is critically low on space (": "المساحة المتبقية في القرص C منخفضة جدًا (",
    "C: drive is running low (": "المساحة المتبقية في القرص C منخفضة (",
    "% free).": "% متاح).",
    "Run Temp Cleanup, uninstall unused programs, or expand the drive.": "نظّف الملفات المؤقتة، أو أزل البرامج غير المستخدمة، أو وسّع القرص.",
    "Consider clearing temporary files.": "يمكنك تنظيف الملفات المؤقتة.",
    "The OS drive appears to be a traditional HDD. Upgrading to an SSD would significantly improve Windows boot times and application responsiveness.": "يبدو أن قرص النظام من نوع HDD. قد تساعد ترقية القرص إلى SSD في تحسين بدء التشغيل واستجابة التطبيقات.",
    "Antivirus status could not be verified. This does not prove protection is disabled.": "تعذّر التحقق من حالة برنامج الحماية؛ لا يعني ذلك أن الحماية معطّلة.",
    "Antivirus protection is disabled or could not be detected. Ensure Windows Defender or a third-party AV is active.": "الحماية معطّلة أو لم يُكتشف برنامج حماية. تأكد من تفعيل Windows Defender أو برنامج حماية آخر.",
    "Windows Update service status could not be read. Check it manually; patch currency was not evaluated.": "تعذّرت قراءة حالة خدمة Windows Update. تحقق يدويًا؛ لم يُقيّم هذا الفحص حداثة التصحيحات.",
    "The Windows Update service is not running. This can be normal for a trigger-start service. Check update history and pending updates manually.": "خدمة Windows Update ليست قيد التشغيل. قد يكون ذلك طبيعيًا لخدمة تبدأ عند الحاجة. راجع سجل التحديثات والتحديثات المعلّقة يدويًا.",
    "The test endpoint 8.8.8.8:53 could not be reached. This alone does not prove the device is offline. Check local connectivity and policy.": "تعذّر الوصول إلى عنوان الاختبار 8.8.8.8:53. لا يثبت ذلك وحده انقطاع الاتصال؛ تحقق من الشبكة المحلية والسياسات.",
    " startup applications found. Disable unnecessary startup items via Task Manager → Startup tab to improve boot time.": " تطبيقات تعمل عند بدء التشغيل. عطّل غير الضروري منها عبر مدير المهام ← بدء التشغيل لتحسين وقت الإقلاع.",
    " disk-related errors found in Event Viewer. Run chkdsk and back up data immediately.": " أخطاء مرتبطة بالقرص في سجل الأحداث. أنشئ نسخة احتياطية وقيّم الحاجة لفحص القرص.",
    " driver errors found in Event Viewer. Update or reinstall affected drivers.": " أخطاء تعريفات في سجل الأحداث. حدّث التعريفات المتأثرة أو أعد تثبيتها.",
    " print-related errors found. Restart the Print Spooler service from the Automation Center.": " أخطاء طباعة. يمكنك إعادة تشغيل خدمة الطباعة من مركز الصيانة.",
    "High": "عالية",
    "Medium": "متوسطة",
    "Low": "منخفضة",
    "Disk Health": "صحة القرص",
    "Drivers": "التعريفات",
    "Printing": "الطباعة",
    "Startup": "بدء التشغيل",
    "Network": "الشبكة",
    "Antivirus": "برنامج الحماية",
    "Windows Update Service": "خدمة Windows Update",
    "Real-time Protection:": "الحماية الفورية:",
    "Last Update:": "آخر تحديث:",
    "Name:": "الاسم:",
    "Status:": "الحالة:",
    "Cores:": "الأنوية:",
    "physical /": "فعلية /",
    "logical": "منطقية",
    "Usage:": "الاستخدام:",
    "Total:": "الإجمالي:",
    "Used:": "المستخدم:",
    "Available:": "المتاح:",
    "CPU Load": "استخدام المعالج",
    "Ram Load": "استخدام الذاكرة",
    "Disk Space": "مساحة القرص",
    "Windows Update": "Windows Update",
    "Event Viewer": "سجل الأحداث",
    "Unknown": "غير معروف",
    "Running": "يعمل",
    "Stopped": "متوقف",
}
_ar_fragments.update(
    {
        "Reports": "التقارير",
        "Export Latest Scan": "تصدير آخر فحص",
        "Export  JSON": "تصدير JSON",
        "Export  CSV": "تصدير CSV",
        "Export  PDF": "تصدير PDF",
        "↻ Load Latest Scan": "↻ تحميل آخر فحص",
        "No scan loaded. Click '↻ Load Latest Scan'.": "لم يُحمّل فحص بعد. اضغط «تحميل آخر فحص».",
        "Previous Report Files": "ملفات التقارير السابقة",
        "↻ Refresh File List": "↻ تحديث قائمة الملفات",
        "File Name": "اسم الملف",
        "Type": "النوع",
        "Modified": "آخر تعديل",
        "Open Selected Folder": "فتح مجلد التقارير",
        "No Scan Data": "لا توجد بيانات فحص",
        "No scan data available. Run a Health Check first.": "لا توجد بيانات فحص. شغّل فحص الصحة أولًا.",
        "No scan data found. Go to Health Checker and run a full scan first.": "لم يُعثر على فحص. انتقل إلى فحص صحة الجهاز وشغّل فحصًا كاملًا.",
        "Export Successful": "نجح التصدير",
        "Report saved to:": "حُفظ التقرير في:",
        "Missing Library": "مكتبة غير متوفرة",
        "Export Failed": "فشل التصدير",
        "Export error:": "خطأ في التصدير:",
        "Export the most recent health scan results. Run a Health Check first if no scan data is available.": "صدّر نتائج آخر فحص لصحة الجهاز. شغّل الفحص أولًا إذا لم تتوفر بيانات.",
        "Loaded scan — Device:": "الفحص المحمّل — الجهاز:",
        "Date:": "التاريخ:",
        "Health Score:": "درجة الصحة:",
        "Cannot generate ": "تعذّر إنشاء تقرير ",
        " report:": " :",
    }
)
_ar_pattern = re.compile(
    "|".join(re.escape(key) for key in sorted(_ar_fragments, key=len, reverse=True))
)
_ar_states = {
    "Unknown": "غير معروف",
    "Enabled": "مفعّل",
    "Disabled": "معطّل",
    "dark": "داكن",
    "light": "فاتح",
    "Running": "يعمل",
    "Stopped": "متوقف",
    "Success": "نجح",
    "Failed": "فشل",
    "Excellent": "ممتاز",
    "Good": "جيد",
    "Warning": "تحذير",
    "Critical": "حرج",
    "Incomplete": "غير مكتمل",
    "Local indicator": "مؤشر محلي",
    "FullyEncrypted": "مشفّر بالكامل",
    "FullyDecrypted": "غير مشفّر",
    "EncryptionInProgress": "جارٍ التشفير",
    "DecryptionInProgress": "جارٍ فك التشفير",
    "EncryptionPaused": "التشفير متوقف مؤقتًا",
    "DecryptionPaused": "فك التشفير متوقف مؤقتًا",
}


_ar_fragments.update({k: v for k, v in _ar_states.items() if k not in ("dark", "light")})
_ar_fragments["Disk"] = "القرص"
_ar_pattern = re.compile(
    "|".join(re.escape(key) for key in sorted(_ar_fragments, key=len, reverse=True))
)


def localize(value):
    if not isinstance(value, str):
        return value
    if get_lang() == "ar":
        return _ar_states.get(
            value,
            _ar_catalog.get(value, _ar_pattern.sub(lambda m: _ar_fragments[m.group()], value)),
        )
    value = _catalog.get(value, _pattern.sub(lambda m: _catalog[m.group()], value))
    return value.replace("direction:rtl", "direction:ltr").replace(
        "text-align:right", "text-align:left"
    )


class _Style:
    def setStyleSheet(self, value):
        style_widget(self, value)


class _Text(_Style):
    def __init__(self, *args, **kwargs):
        if args and isinstance(args[0], str):
            args = (localize(args[0]),) + args[1:]
        super().__init__(*args, **kwargs)

    def setFont(self, font):
        super().setFont(font)
        if font.pointSize() >= 18:
            self._toolkit_heading_size = max(24, font.pointSize())
            self.setStyleSheet(getattr(self, "_toolkit_style", self.styleSheet()))

    def setStyleSheet(self, value):
        if getattr(self, "_toolkit_heading_size", 0):
            value += f"; font-size:{self._toolkit_heading_size}px; font-weight:bold;"
        style_widget(self, value)

    def setText(self, value):
        if isinstance(value, str) and any(tag in value for tag in ("<span", "<p>", "<b>", "<font")):
            self._toolkit_rich_text = value
            value = themed_style(localize(value))
        else:
            self.__dict__.pop("_toolkit_rich_text", None)
        super().setText(localize(value))

    def setToolTip(self, value):
        super().setToolTip(localize(value))


class QLabel(_Text, W.QLabel):
    pass


class QPushButton(_Text, W.QPushButton):
    pass


class QTableWidgetItem(_Text, W.QTableWidgetItem):
    pass


class QGroupBox(_Text, W.QGroupBox):
    def setTitle(self, value):
        super().setTitle(localize(value))


class QLineEdit(_Style, W.QLineEdit):
    def setPlaceholderText(self, value):
        super().setPlaceholderText(localize(value))


class QTextEdit(_Style, W.QTextEdit):
    def setPlaceholderText(self, value):
        super().setPlaceholderText(localize(value))

    def setPlainText(self, value):
        super().setPlainText(localize(value))

    def setHtml(self, value):
        self._toolkit_html = value
        super().setHtml(themed_style(localize(value)))

    def append(self, value):
        super().append(localize(value))

    def insertHtml(self, value):
        super().insertHtml(localize(value))


class QProgressBar(_Style, W.QProgressBar):
    pass


class QTableWidget(_Style, W.QTableWidget):
    def setHorizontalHeaderLabels(self, values):
        super().setHorizontalHeaderLabels([localize(v) for v in values])


class QTabWidget(_Style, W.QTabWidget):
    def addTab(self, *args):
        return super().addTab(*args[:-1], localize(args[-1]))


class QComboBox(_Style, W.QComboBox):
    _CANONICAL = int(Qt.ItemDataRole.UserRole) + 50

    def addItem(self, *args, **kwargs):
        if args and isinstance(args[0], str):
            original = args[0]
            super().addItem(localize(original), *args[1:], **kwargs)
            self.setItemData(self.count() - 1, original, self._CANONICAL)
        else:
            super().addItem(*args, **kwargs)

    def addItems(self, values):
        for value in values:
            self.addItem(value)

    def currentText(self):
        return self.itemData(self.currentIndex(), self._CANONICAL) or super().currentText()

    def setCurrentText(self, value):
        super().setCurrentText(localize(value))


class QMessageBox(_Text, W.QMessageBox):
    @staticmethod
    def information(parent, title, text, *args, **kwargs):
        return W.QMessageBox.information(parent, localize(title), localize(text), *args, **kwargs)

    @staticmethod
    def warning(parent, title, text, *args, **kwargs):
        return W.QMessageBox.warning(parent, localize(title), localize(text), *args, **kwargs)

    @staticmethod
    def critical(parent, title, text, *args, **kwargs):
        return W.QMessageBox.critical(parent, localize(title), localize(text), *args, **kwargs)

    @staticmethod
    def question(parent, title, text, *args, **kwargs):
        return W.QMessageBox.question(parent, localize(title), localize(text), *args, **kwargs)
