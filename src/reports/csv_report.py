"""تصدير نتائج الفحص إلى CSV بترميز يحافظ على العربية وحدود التقييم."""

import csv
from datetime import datetime

from src.utils.app_paths import EXPORTS_DIR as _EXPORTS_DIR
from src.utils.formatters import fmt_bytes, fmt_pct
from src.utils.logger import setup_logger

log = setup_logger(__name__)


def export_csv(scan_data: dict, output_path: str | None = None) -> str:
    """
    Write a human-readable CSV report from scan_data.

    Returns:
        Absolute path of the written file.
    """
    _EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        device = scan_data.get("device_name", "device").replace(" ", "_")
        output_path = str(_EXPORTS_DIR / f"health_report_{device}_{ts}.csv")

    try:
        with open(output_path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh)
            _write_section(writer, "Device Information", _device_rows(scan_data))
            _write_section(writer, "CPU", _cpu_rows(scan_data))
            _write_section(writer, "RAM", _ram_rows(scan_data))
            _write_section(writer, "Disks", _disk_rows(scan_data))
            _write_section(writer, "Antivirus", _av_rows(scan_data))
            _write_section(writer, "Windows Update", _wu_rows(scan_data))
            _write_section(writer, "Network", _net_rows(scan_data))
            _write_section(writer, "Health Score", _score_rows(scan_data))
            _write_section(writer, "Recommendations", _rec_rows(scan_data))

        log.info(f"CSV report saved: {output_path}")
        return output_path
    except Exception as exc:
        log.error(f"CSV export failed: {exc}")
        raise IOError(f"Could not write CSV report: {exc}") from exc


def _write_section(writer, title: str, rows: list):
    writer.writerow([f"=== {title} ==="])
    for row in rows:
        writer.writerow(row)
    writer.writerow([])  # blank separator


def _device_rows(d: dict) -> list:
    os_info = d.get("os", {})
    return [
        ["Field", "Value"],
        ["Device Name", d.get("device_name", "Unknown")],
        ["Username", d.get("username", "Unknown")],
        ["OS", os_info.get("full", "Unknown")],
        ["OS Version", os_info.get("version", "Unknown")],
        ["Scan Date", d.get("scan_timestamp", "Unknown")],
    ]


def _cpu_rows(d: dict) -> list:
    cpu = d.get("cpu", {})
    return [
        ["Field", "Value"],
        ["CPU Name", cpu.get("name", "Unknown")],
        ["Physical Cores", cpu.get("physical_cores", "?")],
        ["Logical Cores", cpu.get("logical_cores", "?")],
        ["Usage %", fmt_pct(cpu.get("usage_pct", 0))],
    ]


def _ram_rows(d: dict) -> list:
    ram = d.get("ram", {})
    return [
        ["Field", "Value"],
        ["Total RAM", fmt_bytes(ram.get("total", 0))],
        ["Used RAM", fmt_bytes(ram.get("used", 0))],
        ["Available", fmt_bytes(ram.get("available", 0))],
        ["Usage %", fmt_pct(ram.get("usage_pct", 0))],
    ]


def _disk_rows(d: dict) -> list:
    rows = [["Drive", "Total", "Used", "Free", "Usage %", "Type"]]
    for disk in d.get("disks", []):
        rows.append(
            [
                disk.get("mountpoint", "?"),
                fmt_bytes(disk.get("total", 0)),
                fmt_bytes(disk.get("used", 0)),
                fmt_bytes(disk.get("free", 0)),
                fmt_pct(disk.get("usage_pct", 0)),
                disk.get("disk_type", "Unknown"),
            ]
        )
    return rows


def _av_rows(d: dict) -> list:
    av = d.get("antivirus", {})
    return [
        ["Field", "Value"],
        ["Antivirus Name", av.get("name", "Unknown")],
        ["Status", av.get("status", "Unknown")],
    ]


def _wu_rows(d: dict) -> list:
    wu = d.get("windows_update", {})
    return [
        ["Field", "Value"],
        ["Service Status", wu.get("service_status", "Unknown")],
        ["Pending Updates", wu.get("pending_updates", "Unknown")],
    ]


def _net_rows(d: dict) -> list:
    net = d.get("network", {})
    return [
        ["Field", "Value"],
        ["Status", net.get("status", "Unknown")],
    ]


def _score_rows(d: dict) -> list:
    hs = d.get("health_score", {})
    rows = [
        ["Field", "Value"],
        ["Overall Score", f"{hs.get('score', 0)}/100 ({hs.get('label', 'Unknown')})"],
        ["Check Coverage %", hs.get("coverage", hs.get("coverage_pct", "Unknown"))],
        ["Unavailable Checks", ", ".join(hs.get("unavailable", []))],
        [
            "Limitations",
            "Indicative operational score; not security certification or proof of current Windows patches.",
        ],
    ]
    for k, v in hs.get("breakdown", {}).items():
        rows.append([f"  {k.replace('_', ' ').title()}", str(v)])
    return rows


def _rec_rows(d: dict) -> list:
    rows = [["Priority", "Category", "Recommendation"]]
    for rec in d.get("recommendations", []):
        rows.append(
            [
                rec.get("priority", ""),
                rec.get("category", ""),
                rec.get("recommendation", ""),
            ]
        )
    return rows
