"""
دوال التنسيق المشتركة — نستخدمها في كل صفحات البرنامج.
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

from datetime import datetime


def fmt_bytes(value: int | float) -> str:
    """يحوّل عدد البايتات لنص مقروء (KB، MB، GB، TB)."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} PB"


def fmt_pct(value: float) -> str:
    """يحوّل رقم عشري لنسبة مئوية، مثل: 73.4%"""
    return f"{value:.1f}%"


def fmt_datetime(dt: datetime | None = None) -> str:
    """يرجع التاريخ والوقت بشكل واضح، افتراضياً الوقت الحالي."""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def fmt_date(dt: datetime | None = None) -> str:
    """يرجع التاريخ فقط بدون وقت، افتراضياً اليوم."""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d")


def health_score_label(score: int) -> str:
    """يرجع تصنيف نصي لدرجة الصحة من 0 إلى 100."""
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 60:
        return "Warning"
    return "Critical"


def health_score_color(score: int) -> str:
    """يرجع لون CSS مناسب لدرجة الصحة."""
    if score >= 90:
        return "#3fb950"  # أخضر
    if score >= 75:
        return "#61afef"  # أزرق
    if score >= 60:
        return "#e5c07b"  # أصفر
    return "#e06c75"  # أحمر


def priority_color(priority: str) -> str:
    """يرجع لون حسب درجة الأولوية."""
    return {
        "High": "#e06c75",
        "Medium": "#e5c07b",
        "Low": "#61afef",
    }.get(priority, "#abb2bf")
