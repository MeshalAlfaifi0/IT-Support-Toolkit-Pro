"""
محرّك حساب درجة الصحة.
يحسب درجة مرجّحة من 0 إلى 100 بناءً على نتائج الفحوصات.
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

from src.utils.logger import setup_logger

log = setup_logger(__name__)

# ── الأوزان (مجموعها 100) ────────────────────────────────────────────────
WEIGHTS = {
    "cpu": 15,
    "ram": 20,
    "disk": 20,
    "antivirus": 15,
    "windows_update": 10,
    "drivers": 10,
    "network": 10,
}


def _score_cpu(cpu_pct: float) -> float:
    """درجة كاملة لو أقل من 60%، تنخفض تدريجياً حتى 85%، صفر فوق 85%."""
    if cpu_pct < 60:
        return 1.0
    if cpu_pct < 85:
        return 1.0 - ((cpu_pct - 60) / 25)
    return 0.0


def _score_ram(ram_pct: float, ram_total_gb: float) -> float:
    """نخصم لو الاستخدام عالي أو الذاكرة قليلة جداً (4 GB أو أقل)."""
    base = 1.0
    if ram_total_gb <= 4:
        base -= 0.3  # خصم 30% للذاكرة الصغيرة جداً
    if ram_pct >= 85:
        return max(0.0, base - 0.7)
    if ram_pct >= 70:
        return max(0.0, base - 0.4)
    return base


def _score_disk(c_free_pct: float) -> float:
    """نخصم لو المساحة الحرة في C: قليلة."""
    if c_free_pct > 20:
        return 1.0
    if c_free_pct > 10:
        return 0.5
    return 0.0


def _score_antivirus(av_enabled: bool, av_name: str) -> float:
    """درجة كاملة لو برنامج الحماية شغّال ومعروف."""
    if av_name in ("Unknown", "") and not av_enabled:
        return 0.5  # مجهول — خصم جزئي وليس كامل
    return 1.0 if av_enabled else 0.0


def _score_windows_update(service_running: bool) -> float:
    return 1.0 if service_running else 0.5


def _score_drivers(has_errors: bool) -> float:
    return 0.5 if has_errors else 1.0


def _score_network(connected: bool) -> float:
    return 1.0 if connected else 0.0


def calculate_health_score(
    cpu_pct: float,
    ram_pct: float,
    ram_total_gb: float,
    c_free_pct: float,
    av_enabled: bool,
    av_name: str,
    wu_running: bool,
    driver_errors: bool,
    network_ok: bool,
    unavailable: set | None = None,
) -> dict:
    """
    يحسب درجة صحة الجهاز الإجمالية.
    يرجع dict فيه: score, label, color, breakdown.
    """
    component_scores = {
        "cpu": _score_cpu(cpu_pct),
        "ram": _score_ram(ram_pct, ram_total_gb),
        "disk": _score_disk(c_free_pct),
        "antivirus": _score_antivirus(av_enabled, av_name),
        "windows_update": _score_windows_update(wu_running),
        "drivers": _score_drivers(driver_errors),
        "network": _score_network(network_ok),
    }

    unavailable = set(unavailable or ())
    for key in unavailable:
        if key in component_scores:
            component_scores[key] = 0.0

    # مجموع مرجّح → درجة من 100
    total = sum(component_scores[k] * WEIGHTS[k] for k in WEIGHTS)
    score = max(0, min(100, round(total)))

    label, color = ("Incomplete", "#d29922") if unavailable else _classify(score)

    breakdown = {k: round(component_scores[k] * WEIGHTS[k], 1) for k in WEIGHTS}

    log.info(f"Health score calculated: {score}/100 ({label})")
    return {
        "score": score,
        "label": label,
        "color": color,
        "breakdown": breakdown,
        "unavailable": sorted(unavailable),
        "coverage": 100 - sum(WEIGHTS.get(k, 0) for k in unavailable),
        "note": "Indicative operational score; unknown checks receive no credit. Service status does not prove patch currency.",
    }


def _classify(score: int) -> tuple[str, str]:
    if score >= 90:
        return "Excellent", "#3fb950"
    if score >= 75:
        return "Good", "#61afef"
    if score >= 60:
        return "Warning", "#e5c07b"
    return "Critical", "#e06c75"
