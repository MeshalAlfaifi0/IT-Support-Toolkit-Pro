"""تطبيق ألوان الثيم على العناصر المحلية والنتائج التي تصل بعد انتهاء الفحص."""

import re

from PySide6.QtWidgets import QApplication, QLabel, QProgressBar, QTextEdit, QWidget

_LIGHT = {
    "#0d1117": "#edf2f7",
    "#161b22": "#f1f5f9",
    "#1a1d23": "#f6f8fa",
    "#1e2128": "#ffffff",
    "#21262d": "#ffffff",
    "#282c34": "#ffffff",
    "#30363d": "#cbd5e1",
    "#3d4451": "#cbd5e1",
    "#dcdfe4": "#1e293b",
    "#c9d1d9": "#334155",
    "#abb2bf": "#334155",
    "#8b949e": "#526277",
    "#5c6370": "#526277",
    "#484f58": "#64748b",
    "#58a6ff": "#0969da",
    "#61afef": "#0969da",
    "#3fb950": "#167d35",
    "#e5c07b": "#8a6500",
    "#d29922": "#8a6500",
    "#e06c75": "#b42332",
    "#f85149": "#b42332",
}
_DARK = {"#5c6370": "#94a3b8", "#484f58": "#94a3b8"}


def themed_style(stylesheet):
    app = QApplication.instance()
    colors = _LIGHT if app and app.property("toolkitTheme") == "light" else _DARK
    return re.sub(
        r"#[0-9a-fA-F]{6}", lambda m: colors.get(m.group().lower(), m.group()), stylesheet
    )


def style_widget(widget, stylesheet):
    widget._toolkit_style = stylesheet
    resolved = themed_style(stylesheet)
    if isinstance(widget, QProgressBar):
        app = QApplication.instance()
        color = "#334155" if app and app.property("toolkitTheme") == "light" else "#f0f6fc"
        resolved += f"QProgressBar {{ color:{color}; }}"
    QWidget.setStyleSheet(widget, resolved)


def refresh_local_styles(root):
    for widget in root.findChildren(QWidget):
        original = getattr(widget, "_toolkit_style", None)
        if original is None:
            original = widget.styleSheet()
        if original:
            style_widget(widget, original)
        from src.utils.ui_text import localize

        if hasattr(widget, "_toolkit_html"):
            QTextEdit.setHtml(widget, themed_style(localize(widget._toolkit_html)))
        if hasattr(widget, "_toolkit_rich_text"):
            QLabel.setText(widget, themed_style(localize(widget._toolkit_rich_text)))
