"""
PDF Report Service — Generate professional incident reports.

Uses reportlab to create downloadable PDF reports for security incidents.
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.platypus.flowables import Flowable


# ── Color palette ──────────────────────────────────────────────
BRAND_BLUE   = HexColor("#3b82f6")
BRAND_DARK   = HexColor("#09090b")
DARK_BG      = HexColor("#18181b")
MUTED        = HexColor("#71717a")
BORDER       = HexColor("#27272a")
TEXT_PRIMARY  = HexColor("#1a1a2e")
TEXT_MUTED    = HexColor("#64748b")

SEVERITY_COLORS = {
    "Critical": HexColor("#ef4444"),
    "High":     HexColor("#f97316"),
    "Medium":   HexColor("#eab308"),
    "Low":      HexColor("#22c55e"),
}

RISK_COLORS = {
    "high":   HexColor("#ef4444"),
    "medium": HexColor("#eab308"),
    "low":    HexColor("#22c55e"),
}


# ── Custom Flowables ───────────────────────────────────────────
class ColoredBadge(Flowable):
    """Inline colored badge (severity / risk / status)."""

    def __init__(self, text, bg_color, text_color=white, width=80, height=18):
        super().__init__()
        self.text = text
        self.bg_color = bg_color
        self.text_color = text_color
        self.width = width
        self.height = height

    def draw(self):
        self.canv.setFillColor(self.bg_color)
        self.canv.roundRect(0, 0, self.width, self.height, 4, fill=1, stroke=0)
        self.canv.setFillColor(self.text_color)
        self.canv.setFont("Helvetica-Bold", 8)
        self.canv.drawCentredString(self.width / 2, 5, self.text)


class ConfidenceBar(Flowable):
    """Visual progress bar for confidence score."""

    def __init__(self, score, width=200, height=12):
        super().__init__()
        self.score = score
        self.width = width
        self.height = height

    def draw(self):
        # Background track
        self.canv.setFillColor(HexColor("#e2e8f0"))
        self.canv.roundRect(0, 0, self.width, self.height, 3, fill=1, stroke=0)
        # Filled portion
        fill_w = max(self.width * (self.score / 100), 6)
        color = HexColor("#22c55e") if self.score >= 80 else (
            HexColor("#eab308") if self.score >= 50 else HexColor("#ef4444")
        )
        self.canv.setFillColor(color)
        self.canv.roundRect(0, 0, fill_w, self.height, 3, fill=1, stroke=0)
        # Label
        self.canv.setFillColor(white)
        self.canv.setFont("Helvetica-Bold", 7)
        if fill_w > 30:
            self.canv.drawCentredString(fill_w / 2, 3, f"{self.score:.1f}%")


# ── Risk computation (mirrors frontend logic) ─────────────────
def _compute_risk(severity: str, confidence: float) -> dict:
    sev_map = {"critical": "high", "high": "high", "medium": "medium", "low": "low"}
    likelihood = sev_map.get(severity.lower(), "low")

    if confidence >= 80:
        impact = "high"
    elif confidence >= 50:
        impact = "medium"
    else:
        impact = "low"

    order = {"low": 0, "medium": 1, "high": 2}
    levels = ["low", "medium", "high"]
    risk_level = levels[max(order[likelihood], order[impact])]

    return {"likelihood": likelihood, "impact": impact, "riskLevel": risk_level}


# ── Styles ─────────────────────────────────────────────────────
def _build_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "ReportTitle", fontName="Helvetica-Bold", fontSize=20,
        textColor=TEXT_PRIMARY, spaceAfter=4, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        "ReportSubtitle", fontName="Helvetica", fontSize=10,
        textColor=TEXT_MUTED, spaceAfter=12, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        "SectionHeader", fontName="Helvetica-Bold", fontSize=12,
        textColor=BRAND_BLUE, spaceBefore=16, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        "FieldLabel", fontName="Helvetica-Bold", fontSize=9,
        textColor=TEXT_MUTED, spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        "FieldValue", fontName="Helvetica", fontSize=10,
        textColor=TEXT_PRIMARY, spaceAfter=8, leading=14,
    ))
    styles.add(ParagraphStyle(
        "BodyText2", fontName="Helvetica", fontSize=10,
        textColor=TEXT_PRIMARY, leading=14, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "BulletItem", fontName="Helvetica", fontSize=10,
        textColor=TEXT_PRIMARY, leading=14, leftIndent=16,
        bulletIndent=4, spaceBefore=2, spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        "FooterStyle", fontName="Helvetica", fontSize=7,
        textColor=TEXT_MUTED, alignment=TA_CENTER,
    ))
    return styles


# ── Main generator ─────────────────────────────────────────────
def generate_incident_pdf(incident_data: dict) -> bytes:
    """
    Generate a professional PDF report for an incident.

    Args:
        incident_data: Incident detail dict from get_incident_details()

    Returns:
        PDF file as bytes
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=f"Incident Report #{incident_data.get('incident_id', '?')}",
        author="SecureOps Platform",
    )

    styles = _build_styles()
    story: list[Flowable] = []

    severity = incident_data.get("severity", "Medium")
    confidence = incident_data.get("confidence_score", 0)
    risk = _compute_risk(severity, confidence)

    # ── Header ─────────────────────────────────────────────
    story.append(Paragraph("SecureOps — Incident Report", styles["ReportTitle"]))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}",
        styles["ReportSubtitle"],
    ))
    story.append(HRFlowable(
        width="100%", thickness=1, color=BRAND_BLUE, spaceBefore=4, spaceAfter=16,
    ))

    # ── Incident Overview Table ────────────────────────────
    story.append(Paragraph("Incident Overview", styles["SectionHeader"]))

    overview_data = [
        ["Incident ID",  f"#{incident_data.get('incident_id', 'N/A')}",
         "Severity",     severity],
        ["Status",       incident_data.get("status", "N/A"),
         "Timestamp",    incident_data.get("timestamp", "N/A")],
        ["Source IP",    incident_data.get("source_ip", "N/A"),
         "Destination",  incident_data.get("destination", "N/A")],
        ["Anomaly Type", incident_data.get("anomaly_type", "N/A"),
         "Confidence",   f"{confidence}%"],
    ]

    col_widths = [80, 140, 80, 140]
    overview_table = Table(overview_data, colWidths=col_widths)
    overview_table.setStyle(TableStyle([
        ("FONTNAME",   (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",   (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",  (0, 0), (0, -1), TEXT_MUTED),
        ("TEXTCOLOR",  (2, 0), (2, -1), TEXT_MUTED),
        ("TEXTCOLOR",  (1, 0), (1, -1), TEXT_PRIMARY),
        ("TEXTCOLOR",  (3, 0), (3, -1), TEXT_PRIMARY),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW",  (0, 0), (-1, -2), 0.5, HexColor("#e2e8f0")),
        ("LINEBELOW",  (0, -1), (-1, -1), 1, BRAND_BLUE),
    ]))
    story.append(overview_table)
    story.append(Spacer(1, 8))

    # ── Risk Assessment ────────────────────────────────────
    story.append(Paragraph("Risk Assessment", styles["SectionHeader"]))

    risk_data = [
        ["Factor", "Level"],
        ["Likelihood", risk["likelihood"].upper()],
        ["Impact",     risk["impact"].upper()],
        ["Risk Score", risk["riskLevel"].upper()],
    ]

    risk_table = Table(risk_data, colWidths=[200, 240])
    risk_color = RISK_COLORS.get(risk["riskLevel"], MUTED)
    risk_table.setStyle(TableStyle([
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",  (0, 0), (-1, 0), white),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
        ("TEXTCOLOR",  (0, 1), (0, -1), TEXT_MUTED),
        ("TEXTCOLOR",  (1, 1), (1, -1), TEXT_PRIMARY),
        ("FONTNAME",   (1, -1), (1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR",  (1, -1), (1, -1), risk_color),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW",  (0, 1), (-1, -2), 0.5, HexColor("#e2e8f0")),
        ("LINEBELOW",  (0, -1), (-1, -1), 1, risk_color),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(risk_table)
    story.append(Spacer(1, 8))

    # ── ML Confidence Bar ──────────────────────────────────
    story.append(Paragraph("ML Confidence Score", styles["SectionHeader"]))
    story.append(ConfidenceBar(confidence, width=440, height=14))
    story.append(Spacer(1, 12))

    # ── Description ────────────────────────────────────────
    story.append(Paragraph("Incident Description", styles["SectionHeader"]))
    story.append(Paragraph(
        incident_data.get("description", "No description available."),
        styles["BodyText2"],
    ))

    # ── Actions Taken ──────────────────────────────────────
    actions = incident_data.get("actions_taken", [])
    if actions:
        story.append(Paragraph("Actions Taken", styles["SectionHeader"]))
        for action in actions:
            story.append(
                Paragraph(f"• {action}", styles["BulletItem"])
            )

    # ── Recommended Action ─────────────────────────────────
    rec = incident_data.get("recommended_action")
    if rec:
        story.append(Paragraph("Recommended Action", styles["SectionHeader"]))
        story.append(Paragraph(rec, styles["BodyText2"]))

    # ── Footer separator ───────────────────────────────────
    story.append(Spacer(1, 24))
    story.append(HRFlowable(
        width="100%", thickness=0.5, color=MUTED, spaceBefore=8, spaceAfter=8,
    ))
    story.append(Paragraph(
        "Generated by SecureOps — AI-Driven Cloud Security Platform",
        styles["FooterStyle"],
    ))
    story.append(Paragraph(
        f"Report ID: INC-{incident_data.get('incident_id', '?')}-{datetime.now().strftime('%Y%m%d%H%M')}",
        styles["FooterStyle"],
    ))

    # ── Build ──────────────────────────────────────────────
    doc.build(story)
    return buf.getvalue()
