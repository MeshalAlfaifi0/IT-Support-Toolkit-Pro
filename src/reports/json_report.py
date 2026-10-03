"""حفظ نتيجة الفحص المنظمة في JSON داخل مجلد التصدير الدائم."""

import json
from datetime import datetime

from src.utils.app_paths import EXPORTS_DIR as _EXPORTS_DIR
from src.utils.logger import setup_logger

log = setup_logger(__name__)


def export_json(scan_data: dict, output_path: str | None = None) -> str:
    """
    Write scan_data to a JSON file.

    Args:
        scan_data:   Full scan result dict from health_checker.run_full_scan().
        output_path: Optional absolute path; auto-generated if None.

    Returns:
        Absolute path of the written file.

    Raises:
        IOError on write failure.
    """
    _EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        device = scan_data.get("device_name", "device").replace(" ", "_")
        output_path = str(_EXPORTS_DIR / f"health_report_{device}_{ts}.json")

    try:
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(scan_data, fh, indent=2, default=str)
        log.info(f"JSON report saved: {output_path}")
        return output_path
    except Exception as exc:
        log.error(f"JSON export failed: {exc}")
        raise IOError(f"Could not write JSON report: {exc}") from exc
