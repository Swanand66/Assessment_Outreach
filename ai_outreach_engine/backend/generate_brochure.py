"""
generate_brochure.py  —  Hyper-Nova AI Services Brochure
Run: python generate_brochure.py
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor, Color
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

W, H = A4   # 595.27 x 841.89 pt

# ── Palette ──────────────────────────────────────────────────────────────────
INDIGO       = HexColor("#4f46e5")
INDIGO_DARK  = HexColor("#3730a3")
INDIGO_SOFT  = HexColor("#e0e7ff")
INDIGO_LIGHT = HexColor("#c7d2fe")
SLATE        = HexColor("#1e293b")
SLATE_MID    = HexColor("#334155")
SLATE_LITE   = HexColor("#64748b")
WHITE        = HexColor("#ffffff")
BG           = HexColor("#f8fafc")
BORDER       = HexColor("#e2e8f0")
EMERALD      = HexColor("#10b981")
AMBER        = HexColor("#f59e0b")
VIOLET       = HexColor("#8b5cf6")
PINK         = HexColor("#ec4899")
SKY          = HexColor("#0ea5e9")

HERO_H = 190   # height of dark hero block on page 1

# ── Page callback (draws background + hero UNDER content) ───────────────────
def _bg(canvas, doc):
    canvas.saveState()
    pn = doc.page

    # Page background
    canvas.setFillColor(BG)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)

    if pn == 1:
        # Dark hero block
        canvas.setFillColor(SLATE)
        canvas.rect(0, H - HERO_H, W, HERO_H, fill=1, stroke=0)

        # Indigo accent stripe
        canvas.setFillColor(INDIGO)
        canvas.rect(0, H - HERO_H - 4, W, 4, fill=1, stroke=0)

        # Decorative faint circles (top-right)
        canvas.setFillColor(Color(0.39, 0.40, 0.90, alpha=0.12))
        canvas.circle(W - 40, H - 30, 105, fill=1, stroke=0)
        canvas.setFillColor(Color(0.39, 0.40, 0.90, alpha=0.07))
        canvas.circle(W - 110, H - 10, 60, fill=1, stroke=0)

        # ── Hero text drawn directly (reliable positioning) ──────────────
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 28)
        canvas.drawString(1.8 * cm, H - 58, "Hyper-Nova AI")

        canvas.setFont("Helvetica", 11)
        canvas.setFillColor(HexColor("#cbd5e1"))
        canvas.drawString(1.8 * cm, H - 80,
                          "Intelligent Outreach & Automation for Real Estate Firms")

        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(HexColor("#818cf8"))
        canvas.drawString(1.8 * cm, H - 100,
                          "Transform how your agency finds, nurtures, and closes leads — on autopilot.")

        # Tag pills
        _pill(canvas, 1.8 * cm, H - 130, "  AI-Powered  ")
        _pill(canvas, 4.9 * cm, H - 130, "  Real Estate  ")
        _pill(canvas, 8.2 * cm, H - 130, "  Automated Outreach  ")

    # Footer
    canvas.setFillColor(SLATE)
    canvas.rect(0, 0, W, 34, fill=1, stroke=0)
    canvas.setFillColor(INDIGO)
    canvas.rect(0, 33, W, 3, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(18, 11, "Hyper-Nova AI  ·  Intelligent Outreach for Real Estate")
    canvas.drawRightString(W - 18, 11, f"Page {pn}")

    canvas.restoreState()


def _pill(canvas, x, y, text, bg=HexColor("#4f46e5"), fg=WHITE):
    canvas.setFont("Helvetica-Bold", 8)
    tw = canvas.stringWidth(text, "Helvetica-Bold", 8)
    canvas.setFillColor(bg)
    canvas.roundRect(x, y - 3, tw + 4, 15, 4, fill=1, stroke=0)
    canvas.setFillColor(fg)
    canvas.drawString(x + 2, y + 1, text)


# ── Style factory ─────────────────────────────────────────────────────────────
def S(name, **kw):
    return ParagraphStyle(name, **kw)


SEC  = S("Sec",  fontName="Helvetica-Bold", fontSize=14, leading=18,
          textColor=INDIGO, spaceBefore=16, spaceAfter=6)
BODY = S("Body", fontName="Helvetica",      fontSize=10, leading=15,
          textColor=SLATE_MID, spaceAfter=4)
BOLD = S("Bold", fontName="Helvetica-Bold", fontSize=10, leading=15,
          textColor=SLATE)
CTAH = S("CTAH", fontName="Helvetica-Bold", fontSize=14, leading=18,
          textColor=WHITE, alignment=TA_CENTER, spaceAfter=5)
CTAB = S("CTAB", fontName="Helvetica",      fontSize=9.5, leading=14,
          textColor=INDIGO_LIGHT, alignment=TA_CENTER)
CTAC = S("CTAC", fontName="Helvetica-Bold", fontSize=10, leading=16,
          textColor=HexColor("#a5b4fc"), alignment=TA_CENTER)

CW   = W - 3.6 * cm   # content width


# ── Main builder ──────────────────────────────────────────────────────────────
def build_pdf(path: str):
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        topMargin=HERO_H + 18,    # story starts below hero block
        bottomMargin=52,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
    )

    story = []

    # ── Divider ──────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=INDIGO_SOFT,
                             spaceAfter=12))

    # ── Who We Are ───────────────────────────────────────────────────────────
    story += [
        Paragraph("Who We Are", SEC),
        Paragraph(
            "Hyper-Nova AI is a specialised automation firm built for real estate "
            "agencies across India. We replace hours of manual follow-up with "
            "intelligent, human-sounding conversations across email, WhatsApp, "
            "and AI voice calls — all on autopilot.", BODY),
    ]

    # ── Services grid ─────────────────────────────────────────────────────────
    story.append(Paragraph("Our Services", SEC))

    SVCS = [
        ("#10b981", "🤖  AI Lead Nurturing",
         "Follow up with every inquiry within 60 seconds — personalised and "
         "context-aware, day or night."),
        ("#4f46e5", "📧  Personalised Email Drips",
         "Multi-touch campaigns written by AI referencing each lead's property "
         "interest, budget, and city."),
        ("#f59e0b", "📞  AI Voice Calling",
         "Vapi-powered voice agent calls leads, qualifies them, and books site "
         "visits — no human required."),
        ("#8b5cf6", "📊  CRM Intelligence",
         "Auto-enrich your CRM: office addresses, decision-makers, LinkedIn "
         "profiles, and verified emails."),
        ("#ec4899", "🔍  Market Radar",
         "Daily scans of new agencies, listings, and price shifts in your "
         "target cities."),
        ("#0ea5e9", "⚡  WhatsApp Broadcasts",
         "Property updates, reminders, and booking confirmations via "
         "WhatsApp with one click."),
    ]

    rows = []
    for i in range(0, len(SVCS), 2):
        row = []
        for clr, title, desc in SVCS[i:i+2]:
            row.append([
                Paragraph(f'<font color="{clr}"><b>{title}</b></font>',
                          S("st", fontName="Helvetica-Bold", fontSize=10,
                            leading=14, spaceAfter=3)),
                Paragraph(desc, S("sd", fontName="Helvetica", fontSize=9,
                                  leading=13, textColor=SLATE_MID)),
            ])
        if len(row) < 2:
            row.append("")
        rows.append(row)

    svc_t = Table(rows, colWidths=[CW / 2 - 4] * 2, hAlign="LEFT")
    svc_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), WHITE),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW",     (0, 0), (-1, -2), 0.5, BORDER),
        ("LINEAFTER",     (0, 0), (-2, -1), 0.5, BORDER),
        ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
    ]))
    story.append(svc_t)

    # ── Stats bar ─────────────────────────────────────────────────────────────
    story += [Spacer(1, 12), Paragraph("Proven Results", SEC)]

    STATS = [
        ("3–4 hrs", "saved per agent\nevery day"),
        ("2×",      "lead response\nrate increase"),
        ("< 60 s",  "first auto\nfollow-up"),
        ("40%",     "more site visits\nper month"),
    ]

    stat_t = Table(
        [[
            [Paragraph(f'<font color="#4f46e5"><b>{v}</b></font>',
                       S("sv", fontName="Helvetica-Bold", fontSize=20,
                         leading=24, alignment=TA_CENTER)),
             Paragraph(l.replace("\n", "<br/>"),
                       S("sl", fontName="Helvetica", fontSize=8, leading=11,
                         textColor=SLATE_LITE, alignment=TA_CENTER))]
            for v, l in STATS
        ]],
        colWidths=[CW / 4] * 4, hAlign="LEFT",
    )
    stat_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), INDIGO_SOFT),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LINEAFTER",     (0, 0), (-2, -1), 0.5, INDIGO_LIGHT),
    ]))
    story.append(stat_t)

    # ── How It Works ──────────────────────────────────────────────────────────
    story += [Spacer(1, 6), Paragraph("How It Works", SEC)]

    STEPS = [
        ("01", "Onboard in 30 minutes",
         "Plug into your CRM or website form — zero tech expertise needed."),
        ("02", "AI Radar scans the market",
         "Our engine identifies new leads in your target city every day."),
        ("03", "Personalised outreach fires instantly",
         "Tailored email, WhatsApp, or AI voice call sent within 60 seconds."),
        ("04", "You review and close",
         "Hot, pre-qualified leads land in your inbox ready for a site visit."),
    ]

    for num, title, desc in STEPS:
        t = Table([[
            Paragraph(f'<font color="#4f46e5"><b>{num}</b></font>',
                      S("sn", fontName="Helvetica-Bold", fontSize=18,
                        leading=22, alignment=TA_CENTER)),
            [Paragraph(f"<b>{title}</b>", BOLD), Paragraph(desc, BODY)],
        ]], colWidths=[36, CW - 42], hAlign="LEFT")
        t.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("LINEBELOW",     (0, 0), (-1, 0), 0.5, BORDER),
        ]))
        story.append(t)

    # ── Pricing ───────────────────────────────────────────────────────────────
    story += [Spacer(1, 8), Paragraph("Flexible Pricing", SEC)]

    PLANS = [
        ("Starter", "₹9,999/mo", False,
         ["Up to 200 AI emails/month", "Email outreach automation",
          "Basic CRM enrichment", "Email support"]),
        ("Growth",  "₹24,999/mo", True,
         ["Up to 1,000 AI emails/month", "Email + WhatsApp automation",
          "AI voice calls (100/mo)", "Full CRM intelligence", "Priority support"]),
        ("Enterprise", "Custom", False,
         ["Unlimited outreach", "Custom AI assistant",
          "Multi-city radar", "Dedicated success manager", "SLA guarantee"]),
    ]

    def pcell(name, price, highlight, feats):
        nbg = "#4f46e5" if highlight else "#1e293b"
        pbg = "#ffffff" if highlight else "#4f46e5"
        fbg = "#e0e7ff" if highlight else "#334155"
        c = [
            Paragraph(f'<font color="{nbg if not highlight else "#ffffff"}"><b>{name}</b></font>',
                      S("pn", fontName="Helvetica-Bold", fontSize=12, leading=16,
                        alignment=TA_CENTER)),
            Paragraph(f'<font color="{pbg}"><b>{price}</b></font>',
                      S("pp", fontName="Helvetica-Bold", fontSize=15, leading=20,
                        alignment=TA_CENTER, spaceAfter=5)),
        ]
        for f in feats:
            c.append(Paragraph(f'<font color="{fbg}">✓  {f}</font>',
                               S("pf", fontName="Helvetica", fontSize=8.5,
                                 leading=13)))
        return c

    plan_t = Table(
        [[pcell(*p) for p in PLANS]],
        colWidths=[CW / 3] * 3, hAlign="LEFT",
    )
    plan_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, 0), WHITE),
        ("BACKGROUND",    (1, 0), (1, 0), INDIGO),
        ("BACKGROUND",    (2, 0), (2, 0), WHITE),
        ("BOX",           (0, 0), (0, 0), 0.5, BORDER),
        ("BOX",           (1, 0), (1, 0), 0,   INDIGO),
        ("BOX",           (2, 0), (2, 0), 0.5, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(plan_t)

    # ── CTA ───────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 18))
    cta_t = Table([[
        [
            Paragraph("Ready to automate your outreach?", CTAH),
            Paragraph(
                "Book a free 15-minute strategy call and we'll show you exactly "
                "how many leads you're leaving on the table.", CTAB),
            Spacer(1, 8),
            Paragraph(
                "📩  swanandvaidya2204@gmail.com     📞  +91 98765 43210", CTAC),
        ]
    ]], colWidths=[CW], hAlign="LEFT")
    cta_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), SLATE),
        ("TOPPADDING",    (0, 0), (-1, -1), 22),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 22),
        ("LEFTPADDING",   (0, 0), (-1, -1), 22),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 22),
    ]))
    story.append(cta_t)

    # Build with page callbacks (callbacks draw UNDER flowables)
    doc.build(story, onFirstPage=_bg, onLaterPages=_bg)
    print(f"✅  PDF saved → {path}")


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "services_brochure.pdf")
    build_pdf(out)
