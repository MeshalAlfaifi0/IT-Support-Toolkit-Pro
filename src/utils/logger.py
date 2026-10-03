"""
إعداد نظام السجلات للبرنامج.
يحفظ في ملف يومي + يطبع في الكونسول.
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

import logging
from datetime import datetime

from src.utils.app_paths import LOG_DIR


def setup_logger(name: str) -> logging.Logger:
    """
    ينشئ logger بالاسم المطلوب مع handler للكونسول وملف يومي.
    مرّر __name__ من كل ملف.
    """
    logger = logging.getLogger(name)

    # ما نضيف handlers مكررة لو الموديول اتستورد أكثر من مرة
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # --- كونسول: يطبع INFO وما فوق ---
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # --- ملف: يحفظ كل شيء من DEBUG وما فوق ---
    try:
        log_dir = LOG_DIR
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        file_h = logging.FileHandler(log_path, encoding="utf-8")
        file_h.setLevel(logging.DEBUG)
        file_h.setFormatter(formatter)
        logger.addHandler(file_h)
    except Exception as exc:
        logger.warning(f"File logging unavailable: {exc}")

    return logger
