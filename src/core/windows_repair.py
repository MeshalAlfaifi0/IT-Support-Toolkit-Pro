"""
عمليات إصلاح ويندوز — تنظيف DNS وإعادة ضبط الشبكة
وحذف الملفات المؤقتة وتشغيل SFC و DISM.
العمليات المدمِّرة تحتاج صلاحيات مسؤول وتأكيد مسبق.
المؤلف : Meshal Alfaifi  (GitHub: MeshalAlfaifi0)
"""

import os
import tempfile
from pathlib import Path

from src.utils.command_runner import run_command
from src.utils.logger import setup_logger

log = setup_logger(__name__)


# ── تنظيف DNS ─────────────────────────────────────────────────────────────


def flush_dns() -> tuple[bool, str]:
    """يمسح ذاكرة DNS المؤقتة عن طريق ipconfig /flushdns."""
    ok, out, err = run_command("ipconfig /flushdns", timeout=15)
    output = out or err
    if ok:
        log.info("DNS cache flushed.")
        return True, output.strip() or "DNS cache flushed successfully."
    log.error(f"DNS flush failed: {output}")
    return False, output.strip() or "DNS flush failed."


# ── إعادة ضبط الشبكة (يحتاج مسؤول) ─────────────────────────────────────


def reset_network() -> tuple[bool, str]:
    """
    يعيد ضبط الشبكة بالكامل: Winsock وIP وتجديد DHCP.
    يحتاج صلاحيات Administrator. قد يحتاج إعادة تشغيل.
    """
    commands = [
        ("netsh winsock reset", "Winsock Reset"),
        ("netsh int ip reset", "IP Stack Reset"),
        ("ipconfig /release", "DHCP Release"),
        ("ipconfig /renew", "DHCP Renew"),
    ]
    results = []
    overall_ok = True
    for cmd, label in commands:
        ok, out, err = run_command(cmd, timeout=30)
        status = "OK" if ok else "FAILED"
        output = (out or err).strip()
        results.append(f"[{status}] {label}:\n{output}\n")
        if not ok:
            overall_ok = False
        log.info(f"Network reset step '{label}': {status}")

    summary = "\n".join(results)
    note = "\n⚠ A system RESTART may be required for all changes to take effect."
    return overall_ok, summary + note


# ── تنظيف الملفات المؤقتة ────────────────────────────────────────────────


def cleanup_directory(folder: Path, protected_paths=()) -> dict:
    """Delete only ordinary files under the requested temp root; never follow links.
    Byte count is logical file size after successful unlink, not disk block savings.
    """
    import sys

    from src.utils.app_paths import DATA_DIR

    protected = [Path(p).resolve() for p in protected_paths]
    protected += [
        DATA_DIR.resolve(),
        Path(sys.executable).resolve().parent,
        Path(__file__).resolve().parents[2],
        Path.cwd().resolve(),
    ]
    if getattr(sys, "_MEIPASS", None):
        protected.append(Path(sys._MEIPASS).resolve())
    stats = dict(deleted=0, folders=0, skipped=0, bytes=0, errors=0)

    def overlaps(path):
        resolved = path.resolve()
        return any(resolved == p or resolved.is_relative_to(p) for p in protected)

    def visit(path, is_root=False):
        try:
            if path.is_symlink() or path.is_junction() or overlaps(path):
                stats["skipped"] += 1
                return
            if path.is_dir():
                for child in path.iterdir():
                    visit(child)
                if not is_root:
                    try:
                        path.rmdir()
                        stats["folders"] += 1
                    except OSError:
                        pass  # Remaining protected/locked children are counted individually.
            elif path.is_file():
                size = path.stat().st_size
                path.unlink()
                stats["deleted"] += 1
                stats["bytes"] += size
        except OSError:
            stats["skipped"] += 1
            stats["errors"] += 1

    if folder.exists():
        visit(folder, True)
    return stats


def clear_temp_files() -> tuple[bool, str]:
    from src.utils.formatters import fmt_bytes
    from src.utils.lang import text as tx

    targets = [
        ("User Temp", Path(tempfile.gettempdir())),
        ("Windows Temp", Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Temp"),
    ]
    # Prefetch is maintained by Windows; do not delete it as temporary user data.
    all_stats = [(label, cleanup_directory(folder)) for label, folder in targets]
    deleted = sum(s["deleted"] for _, s in all_stats)
    folders = sum(s["folders"] for _, s in all_stats)
    skipped = sum(s["skipped"] for _, s in all_stats)
    recovered = sum(s["bytes"] for _, s in all_stats)
    errors = sum(s["errors"] for _, s in all_stats)
    try:
        from src.database.init_db import log_temp_cleanup

        log_temp_cleanup(
            deleted_count=deleted,
            skipped_count=skipped,
            recovered_bytes=recovered,
            status="Partial" if errors else "Success",
        )
    except Exception as exc:
        log.warning("Could not save cleanup result: %s", type(exc).__name__)
    summary = [
        tx("نتيجة تنظيف الملفات المؤقتة", "Temporary file cleanup result"),
        tx("الملفات المحذوفة: ", "Files deleted: ") + str(deleted),
        tx("المجلدات الفارغة المحذوفة: ", "Empty folders removed: ") + str(folders),
        tx("الملفات التي تم تخطيها: ", "Items skipped: ") + str(skipped),
        tx("حجم الملفات المحذوفة: ", "Deleted file size: ") + fmt_bytes(recovered),
    ]
    for label, stats in all_stats:
        summary.append(
            f"{label}: files={stats['deleted']}, skipped={stats['skipped']}, bytes={stats['bytes']}"
        )
    summary.append(
        tx(
            "اكتمل مع تخطي الملفات المحمية أو المستخدمة.",
            "Completed; protected or in-use items were skipped.",
        )
    )
    log.info("Temp cleanup: files=%s skipped=%s bytes=%s", deleted, skipped, recovered)
    return errors == 0, "\n".join(summary)


# ── SFC و DISM (يحتاجان مسؤول وهما طويلان) ─────────────────────────────


def run_sfc(line_callback) -> tuple[bool, str]:
    """
    يشغّل فاحص ملفات النظام (sfc /scannow).
    يستدعي line_callback لكل سطر يطلع عشان يظهر في الواجهة.
    """
    log.info("Starting SFC scan")
    lines = []

    def capture(line):
        lines.append(line)
        line_callback(line)

    from src.utils.command_runner import run_command_streaming

    ok = run_command_streaming("sfc /scannow", capture, timeout=600)
    summary = "\n".join(lines)
    log.info(f"SFC finished: success={ok}")
    return ok, summary


def run_dism(line_callback) -> tuple[bool, str]:
    """
    يشغّل DISM /Online /Cleanup-Image /RestoreHealth.
    يستدعي line_callback لكل سطر عشان تشوف التقدم في الوقت الفعلي.
    """
    log.info("Starting DISM RestoreHealth")
    lines = []

    def capture(line):
        lines.append(line)
        line_callback(line)

    from src.utils.command_runner import run_command_streaming

    cmd = "DISM /Online /Cleanup-Image /RestoreHealth"
    ok = run_command_streaming(cmd, capture, timeout=1800)
    summary = "\n".join(lines)
    log.info(f"DISM finished: success={ok}")
    return ok, summary
