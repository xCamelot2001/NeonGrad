"""
pdf_generator.py — Generate clean PDFs for tailored CVs and cover letters (Phase 3).
Uses reportlab for layout; outputs raw bytes suitable for a FastAPI FileResponse.
"""
import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

# ── Brand colours (matching NeonGrad's palette) ──────────────────────────────
BRAND_PURPLE = colors.HexColor("#6D28D9")
BRAND_LIGHT  = colors.HexColor("#8B5CF6")
TEXT_DARK    = colors.HexColor("#111827")
TEXT_GREY    = colors.HexColor("#6B7280")
TEXT_LIGHT   = colors.HexColor("#9CA3AF")


def _base_doc(buffer: io.BytesIO) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        topMargin=2.2 * cm,
        bottomMargin=2.2 * cm,
    )


def _cv_styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "cv_title",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=20,
            textColor=TEXT_DARK,
            spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "cv_subtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=TEXT_GREY,
            spaceAfter=12,
        ),
        "section": ParagraphStyle(
            "cv_section",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=BRAND_PURPLE,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "cv_body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            textColor=TEXT_DARK,
            leading=14,
            spaceAfter=3,
        ),
        "bullet": ParagraphStyle(
            "cv_bullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            textColor=TEXT_DARK,
            leading=14,
            leftIndent=12,
            spaceAfter=3,
        ),
        "label": ParagraphStyle(
            "cv_label",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            textColor=TEXT_GREY,
            spaceAfter=2,
        ),
    }


def generate_cv_pdf(tailored_cv: str, job_title: str, company: str) -> bytes:
    """Return PDF bytes for a tailored CV."""
    buffer = io.BytesIO()
    doc = _base_doc(buffer)
    s = _cv_styles()
    story = []

    # Header
    story.append(Paragraph("Tailored CV", s["title"]))
    story.append(Paragraph(f"Prepared for: {job_title} at {company}  ·  {date.today().strftime('%d %b %Y')}", s["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_PURPLE, spaceAfter=8))

    # Parse the CV text line by line
    for raw_line in tailored_cv.split("\n"):
        line = raw_line.rstrip()

        if not line:
            story.append(Spacer(1, 0.25 * cm))
            continue

        # Markdown-style headings
        if line.startswith("### "):
            story.append(Paragraph(line[4:], s["section"]))
        elif line.startswith("## "):
            story.append(Paragraph(line[3:], s["section"]))
        elif line.startswith("# "):
            story.append(Paragraph(line[2:], s["title"]))

        # Bullet points (-, *, •)
        elif line.lstrip().startswith(("- ", "* ", "• ")):
            text = line.lstrip()[2:]
            story.append(Paragraph(f"&bull; {text}", s["bullet"]))

        # Bold lines (used for role titles / company names)
        elif line.startswith("**") and line.endswith("**"):
            story.append(Paragraph(f"<b>{line[2:-2]}</b>", s["body"]))

        # Italic / label lines
        elif line.startswith("_") and line.endswith("_"):
            story.append(Paragraph(line[1:-1], s["label"]))

        else:
            story.append(Paragraph(line, s["body"]))

    doc.build(story)
    return buffer.getvalue()


def _cl_styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "sender": ParagraphStyle(
            "cl_sender",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=TEXT_DARK,
            spaceAfter=2,
        ),
        "meta": ParagraphStyle(
            "cl_meta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            textColor=TEXT_GREY,
            spaceAfter=16,
        ),
        "salutation": ParagraphStyle(
            "cl_sal",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            textColor=TEXT_DARK,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "cl_body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10.5,
            textColor=TEXT_DARK,
            leading=16,
            spaceAfter=8,
        ),
        "sign": ParagraphStyle(
            "cl_sign",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            textColor=TEXT_DARK,
            spaceBefore=16,
        ),
    }


def generate_cover_letter_pdf(
    cover_letter: str,
    applicant_name: str,
    job_title: str,
    company: str,
) -> bytes:
    """Return PDF bytes for a cover letter."""
    buffer = io.BytesIO()
    doc = _base_doc(buffer)
    s = _cl_styles()
    story = []

    # Header
    story.append(Paragraph(applicant_name or "Applicant", s["sender"]))
    story.append(Paragraph(
        f"{job_title} Application  ·  {company}  ·  {date.today().strftime('%d %b %Y')}",
        s["meta"],
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_PURPLE, spaceAfter=16))

    # Body paragraphs
    paragraphs = [p.strip() for p in cover_letter.split("\n\n") if p.strip()]
    for i, para in enumerate(paragraphs):
        # First paragraph: treat as salutation if it starts with "Dear"
        if i == 0 and para.lower().startswith("dear"):
            story.append(Paragraph(para, s["salutation"]))
        # Last paragraph: signature block
        elif i == len(paragraphs) - 1 and any(
            para.lower().startswith(kw) for kw in ("yours", "sincerely", "regards", "best", "kind")
        ):
            story.append(Paragraph(para.replace("\n", "<br/>"), s["sign"]))
        else:
            story.append(Paragraph(para.replace("\n", " "), s["body"]))

    doc.build(story)
    return buffer.getvalue()
