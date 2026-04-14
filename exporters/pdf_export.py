# exporters/pdf_export.py – Lesson plan → PDF via ReportLab

from __future__ import annotations

import re
from pathlib import Path


# ── colour palette (RGB 0-1) ──────────────────────────────────────────────────
_BLUE   = (0.149, 0.388, 0.922)   # #2563EB
_DARK   = (0.078, 0.078, 0.078)
_GREY   = (0.27,  0.27,  0.27)
_LGREY  = (0.82,  0.82,  0.82)
_WHITE  = (1.0,   1.0,   1.0)


def export_pdf(content: str, filepath: str | Path) -> None:
    """
    Render a lesson plan text to a well-formatted A4 PDF.

    Raises ImportError if reportlab is not installed.
    Raises any reportlab exception on generation failure.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer,
            HRFlowable, KeepTogether,
        )
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
    except ImportError:
        raise ImportError(
            "reportlab is not installed.\n"
            "Run:  pip install reportlab"
        )

    filepath = str(filepath)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2.5 * cm,
        title="Lesson Plan",
        author="EduHelper AI",
    )

    # ── Style definitions ─────────────────────────────────────────────────────
    def _style(name, **kwargs) -> ParagraphStyle:
        base = dict(
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.Color(*_DARK),
            spaceAfter=4,
            spaceBefore=0,
            leftIndent=0,
        )
        base.update(kwargs)
        return ParagraphStyle(name, **base)

    s_title = _style(
        "Title",
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.Color(*_BLUE),
        spaceAfter=4,
    )
    s_meta = _style(
        "Meta",
        fontSize=9,
        textColor=colors.Color(*_GREY),
        spaceAfter=6,
    )
    s_section = _style(
        "Section",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.Color(*_BLUE),
        spaceBefore=10,
        spaceAfter=4,
    )
    s_phase = _style(
        "Phase",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.Color(*_DARK),
        spaceBefore=6,
        spaceAfter=2,
    )
    s_body = _style("Body", spaceAfter=3)
    s_bullet = _style(
        "Bullet",
        leftIndent=14,
        spaceAfter=2,
    )
    s_vocab = _style(
        "Vocab",
        fontName="Helvetica-Oblique",
        leftIndent=10,
        fontSize=10,
        spaceAfter=2,
    )
    s_table_row = _style(
        "TableRow",
        fontName="Courier",
        fontSize=9,
        leading=12,
        spaceAfter=1,
    )

    # ── Parse content → flowables ─────────────────────────────────────────────
    story = []

    def _hr(thickness=0.5, colour=_LGREY):
        return HRFlowable(
            width="100%",
            thickness=thickness,
            color=colors.Color(*colour),
            spaceAfter=4,
            spaceBefore=4,
        )

    def _safe(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    lines = content.split("\n")
    i = 0
    in_timing = False

    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        i += 1

        # ── Divider ───────────────────────────────────────────────────────────
        if re.match(r"^[━─═]{4,}$", line):
            story.append(_hr())
            in_timing = False
            continue

        # ── Empty line ────────────────────────────────────────────────────────
        if not line:
            story.append(Spacer(1, 4))
            continue

        # ── Title ─────────────────────────────────────────────────────────────
        if line.startswith("LESSON PLAN:"):
            title = line.replace("LESSON PLAN:", "").strip()
            story.append(Paragraph(_safe(title), s_title))
            continue

        # ── Meta line (Book: … | …) ───────────────────────────────────────────
        if line.startswith("Book:") or line.startswith("Date:"):
            story.append(Paragraph(_safe(line), s_meta))
            continue

        # ── Section headers (ALL CAPS, no bullet) ────────────────────────────
        is_header = (
            len(line) >= 4
            and line == line.upper()
            and not line.startswith("•")
            and not line.startswith("|")
            and not line.startswith("-")
            and not re.match(r"^\d+\s*min", line, re.I)
        )

        # Phase headers (WARM-UP, PRESENTATION …  (X minutes))
        is_phase = re.match(
            r"^(WARM-UP|PRESENTATION|GUIDED|INDEPENDENT|ASSESSMENT|COOL-DOWN)"
            r".*\(\d+",
            line,
        )

        if is_phase:
            story.append(Spacer(1, 4))
            story.append(Paragraph(_safe(line), s_phase))
            continue

        if is_header and line not in ("TOTAL",):
            in_timing = "LESSON TIMING" in line
            story.append(Paragraph(_safe(line), s_section))
            continue

        # ── Timing table rows ─────────────────────────────────────────────────
        if line.startswith("|") or re.match(r"^-{3,}", line):
            story.append(Paragraph(_safe(line), s_table_row))
            continue

        # ── Bullet points ─────────────────────────────────────────────────────
        if line.startswith("•"):
            story.append(
                Paragraph("&bull; " + _safe(line[1:].strip()), s_bullet)
            )
            continue

        # ── Vocabulary (Term – definition) ────────────────────────────────────
        if "–" in line and not line.startswith("•") and len(line) < 120:
            story.append(Paragraph(_safe(line), s_vocab))
            continue

        # ── Default body text ─────────────────────────────────────────────────
        story.append(Paragraph(_safe(line), s_body))

    # ── Add page footer ───────────────────────────────────────────────────────
    story.append(Spacer(1, 12))
    story.append(_hr(0.3))
    story.append(
        Paragraph(
            "Generated by EduHelper AI — Primary Teacher Toolkit",
            _style("Footer", fontSize=8, textColor=colors.Color(*_LGREY)),
        )
    )

    doc.build(story)


# ── Page number canvas ────────────────────────────────────────────────────────

def _add_page_numbers(canvas, doc):
    """Draw page numbers in the footer."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColorRGB(*_GREY)
    canvas.drawRightString(
        19.5 * 28.35,   # ~A4 right margin in points
        1.5 * 28.35,
        f"Page {doc.page}",
    )
    canvas.restoreState()
