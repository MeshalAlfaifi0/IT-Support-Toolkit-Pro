"""
فحص صلاحيات المسؤول.
نستخدمه قبل أي عملية تحتاج Administrator.
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

import ctypes

from src.utils.logger import setup_logger

log = setup_logger(__name__)


def is_admin() -> bool:
    """يرجع True لو البرنامج يشتغل بصلاحيات المسؤول."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception as exc:
        log.error(f"Admin check failed: {exc}")
        return False


def show_admin_warning(parent=None) -> bool:
    """
    يعرض رسالة تحذير لما تحتاج صلاحيات مسؤول.

    يرجع True لو الصلاحيات موجودة (تكمّل).
    يرجع False لو ما في صلاحيات (وقّف العملية).
    """
    if is_admin():
        return True

    # نستورد Qt بس لما نحتاجه عشان ما نسبب تعارض في الاستيراد
    from src.utils.ui_text import QMessageBox

    dlg = QMessageBox(parent)
    dlg.setIcon(QMessageBox.Icon.Warning)
    dlg.setWindowTitle("يتطلب صلاحيات المسؤول")
    dlg.setText(
        "هذه العملية تتطلب تشغيل البرنامج كمسؤول (Administrator).\n\n"
        "يرجى إغلاق البرنامج وفتحه بالنقر بزر الماوس الأيمن ثم\n"
        "'تشغيل كمسؤول' (Run as administrator)."
    )
    dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
    dlg.exec()
    return False


def confirm_action(message: str, parent=None) -> bool:
    """
    يطلب تأكيد من المستخدم قبل تنفيذ عملية مهمة.
    يرجع True لو ضغط نعم.
    """
    from src.utils.ui_text import QMessageBox

    dlg = QMessageBox(parent)
    dlg.setIcon(QMessageBox.Icon.Question)
    dlg.setWindowTitle("تأكيد العملية")
    dlg.setText(message)
    dlg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    dlg.setDefaultButton(QMessageBox.StandardButton.No)
    # نغيّر نص الأزرار للعربية
    dlg.button(QMessageBox.StandardButton.Yes).setText("نعم، متابعة")
    dlg.button(QMessageBox.StandardButton.No).setText("إلغاء")
    return dlg.exec() == QMessageBox.StandardButton.Yes
