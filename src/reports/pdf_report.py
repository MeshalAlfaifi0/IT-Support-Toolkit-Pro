"""إنشاء تقرير PDF تقني مع التفاف القيم الطويلة وبيان حدود تقييم الجهاز."""

from datetime import datetime
from xml.sax.saxutils import escape

from src.utils.app_paths import EXPORTS_DIR as _EXPORTS_DIR
from src.utils.branding import APP_TITLE
from src.utils.formatters import fmt_bytes, fmt_pct
from src.utils.logger import setup_logger

log = setup_logger(__name__)


def export_pdf(scan_data: dict, output_path: str | None = None) -> str:
    """
    Write a formatted PDF health report.

    Returns:
        Absolute path of the written PDF.

    Raises:
        ImportError if reportlab is not installed.
        IOError on write failure.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            HRFlowable,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
        )
    except ImportError as exc:
        raise ImportError(
            "reportlab is required for PDF export. Install it with: pip install reportlab"
        ) from exc

    _EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        device = scan_data.get("device_name", "device").replace(" ", "_")
        output_path = str(_EXPORTS_DIR / f"health_report_{device}_{ts}.pdf")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title2",
        parent=styles["Title"],
        fontSize=18,
        textColor=colors.HexColor("#1a1a2e"),
    )
    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#0f3460"),
        spaceBefore=14,
    )
    normal = styles["Normal"]

    elements = []

    # ── Title ──────────────────────────────────────────────────────────
    elements.append(Paragraph(APP_TITLE, title_style))
    elements.append(Paragraph("Endpoint Health Report", styles["Heading2"]))
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f3460")))
    elements.append(Spacer(1, 0.3 * cm))

    # ── Device info ────────────────────────────────────────────────────
    elements.append(Paragraph("Device Information", section_style))
    device_rows = [
        ["Device Name", scan_data.get("device_name", "Unknown")],
        ["Username", scan_data.get("username", "Unknown")],
        ["OS", scan_data.get("os", {}).get("full", "Unknown")],
        ["Scan Date", scan_data.get("scan_timestamp", "Unknown")],
    ]
    elements.append(_make_table(device_rows))

    # ── Health score ───────────────────────────────────────────────────
    hs = scan_data.get("health_score", {})
    elements.append(Paragraph("Health Score", section_style))
    score_text = (
        f'<font color="{hs.get("color", "#61afef")}" size="20">'
        f"<b>{hs.get('score', 0)}/100 – {escape(str(hs.get('label', '')))}</b></font>"
    )
    elements.append(Paragraph(score_text, styles["Normal"]))
    elements.append(
        Paragraph(
            "Indicative operational score; it does not prove security compliance or current Windows patches.",
            normal,
        )
    )
    coverage = hs.get("coverage", hs.get("coverage_pct"))
    coverage_text = (
        f"{coverage}%" if isinstance(coverage, (int, float)) else "Unknown (legacy scan)"
    )
    elements.append(
        Paragraph(
            f"Check coverage: {coverage_text}. Unavailable checks: {escape(', '.join(hs.get('unavailable', []))) or 'None listed'}",
            normal,
        )
    )
    elements.append(Spacer(1, 0.3 * cm))

    # ── System metrics ─────────────────────────────────────────────────
    cpu = scan_data.get("cpu", {})
    ram = scan_data.get("ram", {})
    elements.append(Paragraph("System Metrics", section_style))
    metrics = [
        ["Component", "Value"],
        ["CPU Name", cpu.get("name", "Unknown")],
        ["CPU Usage", fmt_pct(cpu.get("usage_pct", 0))],
        ["Total RAM", fmt_bytes(ram.get("total", 0))],
        ["RAM Usage", fmt_pct(ram.get("usage_pct", 0))],
        ["Antivirus", scan_data.get("antivirus", {}).get("status", "Unknown")],
        ["Windows Update", scan_data.get("windows_update", {}).get("service_status", "Unknown")],
        ["Network", scan_data.get("network", {}).get("status", "Unknown")],
    ]
    elements.append(_make_table(metrics, header=True))

    # ── Disk info ──────────────────────────────────────────────────────
    elements.append(Paragraph("Disk Drives", section_style))
    disk_rows = [["Drive", "Total", "Used", "Free", "Usage %", "Type"]]
    for disk in scan_data.get("disks", []):
        disk_rows.append(
            [
                disk.get("mountpoint", "?"),
                fmt_bytes(disk.get("total", 0)),
                fmt_bytes(disk.get("used", 0)),
                fmt_bytes(disk.get("free", 0)),
                fmt_pct(disk.get("usage_pct", 0)),
                disk.get("disk_type", "Unknown"),
            ]
        )
    elements.append(_make_table(disk_rows, header=True))

    # ── Recommendations ────────────────────────────────────────────────
    recs = scan_data.get("recommendations", [])
    if recs:
        elements.append(Paragraph("Recommendations", section_style))
        for rec in recs:
            priority = rec.get("priority", "")
            category = rec.get("category", "")
            rec_text = rec.get("recommendation", "")
            p_color = {"High": "#e06c75", "Medium": "#e5c07b", "Low": "#61afef"}.get(
                priority, "#abb2bf"
            )
            elements.append(
                Paragraph(
                    f'<font color="{p_color}"><b>[{escape(str(priority))}] {escape(str(category))}:</b></font> {escape(str(rec_text))}',
                    normal,
                )
            )
            elements.append(Spacer(1, 0.2 * cm))

    # ── Footer ─────────────────────────────────────────────────────────
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    elements.append(Paragraph(f"Generated by {APP_TITLE}", styles["Italic"]))

    try:
        doc = SimpleDocTemplate(output_path, pagesize=A4)
        doc.build(elements)
        log.info(f"PDF report saved: {output_path}")
        return output_path
    except Exception as exc:
        log.error(f"PDF build failed: {exc}")
        raise IOError(f"Could not write PDF: {exc}") from exc


def _make_table(rows: list, header: bool = False):
    """Helper to build a styled ReportLab Table."""
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, Table, TableStyle

    cell_style = ParagraphStyle(
        "Cell", fontName="Helvetica", fontSize=9, leading=12, textColor=colors.HexColor("#abb2bf")
    )
    header_style = ParagraphStyle(
        "HeaderCell", parent=cell_style, fontName="Helvetica-Bold", textColor=colors.white
    )
    cells = [
        [
            Paragraph(escape(str(value)), header_style if header and index == 0 else cell_style)
            for value in row
        ]
        for index, row in enumerate(rows)
    ]
    count = max((len(row) for row in rows), default=2)
    widths = [160, 291] if count == 2 else [451 / count] * count
    t = Table(cells, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0 if header else -1), colors.HexColor("#1e2128")),
        ("TEXTCOLOR", (0, 0), (-1, 0 if header else -1), colors.white),
        ("FONTNAME", (0, 0), (-1, 0 if header else -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        (
            "ROWBACKGROUNDS",
            (0, 1),
            (-1, -1),
            [colors.HexColor("#282c34"), colors.HexColor("#21262d")],
        ),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#abb2bf")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#3d4451")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    t.setStyle(TableStyle(style))
    return t
