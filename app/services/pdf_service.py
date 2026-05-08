import os
import uuid
from datetime import datetime

from reportlab.lib.pagesizes import A5
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable
)
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle
)
from reportlab.lib.enums import (
    TA_CENTER,
    TA_RIGHT
)

from app.schemas.billing import ReceiptData


# ── Local Folders (used for prescriptions only) ───────
PRESCRIPTIONS_DIR = "prescriptions"
os.makedirs(PRESCRIPTIONS_DIR, exist_ok=True)


# ── Brand Colors ──────────────────────────────────────
VENNOVA_BLUE  = colors.HexColor("#1a237e")
VENNOVA_GREEN = colors.HexColor("#00897b")
VENNOVA_LIGHT = colors.HexColor("#e8eaf6")
TEXT_DARK     = colors.HexColor("#1a1a2e")
TEXT_GREY     = colors.HexColor("#666666")


def _base_styles():
    return getSampleStyleSheet()


# ======================================================
# RECEIPT PDF GENERATOR
# ======================================================
def generate_receipt_pdf(data: ReceiptData) -> str:
    """
    Generate payment receipt PDF.

    Railway-safe version:
    - Saves temporarily in /tmp/
    - Gets uploaded to Supabase Storage later
    """

    # ───────────────────────────────────────────────────
    # IMPORTANT:
    # Railway filesystem is temporary.
    # Always save PDFs in /tmp/
    # ───────────────────────────────────────────────────
    output_path = f"/tmp/receipt_{str(uuid.uuid4())[:8]}.pdf"

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A5,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        leftMargin=12 * mm,
        rightMargin=12 * mm
    )

    styles = _base_styles()
    content = []

    # ── Clinic Header ──────────────────────────────────
    content.append(Paragraph(
        f'"{data.clinic_name}"',
        ParagraphStyle(
            "h",
            parent=styles["Normal"],
            fontSize=14,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
            textColor=VENNOVA_BLUE,
            spaceAfter=2
        )
    ))

    content.append(Paragraph(
        f"{data.doctor_name} | {data.qualification or 'B.H.M.S.'}",
        ParagraphStyle(
            "sub",
            parent=styles["Normal"],
            fontSize=9,
            alignment=TA_CENTER,
            textColor=TEXT_GREY,
            spaceAfter=1
        )
    ))

    if data.clinic_address:
        content.append(Paragraph(
            data.clinic_address,
            ParagraphStyle(
                "addr",
                parent=styles["Normal"],
                fontSize=8,
                alignment=TA_CENTER,
                textColor=TEXT_GREY,
                spaceAfter=1
            )
        ))

    if data.clinic_phone:
        content.append(Paragraph(
            f"Mobile: {data.clinic_phone}",
            ParagraphStyle(
                "ph",
                parent=styles["Normal"],
                fontSize=8,
                alignment=TA_CENTER,
                textColor=TEXT_GREY,
                spaceAfter=1
            )
        ))

    if data.clinic_timings:
        content.append(Paragraph(
            f"Timings: {data.clinic_timings}",
            ParagraphStyle(
                "t",
                parent=styles["Normal"],
                fontSize=8,
                alignment=TA_CENTER,
                textColor=TEXT_GREY,
                spaceAfter=4
            )
        ))

    content.append(HRFlowable(
        width="100%",
        thickness=1.5,
        color=VENNOVA_BLUE,
        spaceAfter=6
    ))

    # ── Receipt Title ──────────────────────────────────
    content.append(Paragraph(
        "PAYMENT RECEIPT",
        ParagraphStyle(
            "title",
            parent=styles["Normal"],
            fontSize=11,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
            textColor=VENNOVA_BLUE,
            spaceAfter=8
        )
    ))

    # ── Table Styles ───────────────────────────────────
    lbl = ParagraphStyle(
        "lbl",
        parent=styles["Normal"],
        fontSize=9,
        fontName="Helvetica-Bold"
    )

    val = ParagraphStyle(
        "val",
        parent=styles["Normal"],
        fontSize=9
    )

    # ── Receipt Details ────────────────────────────────
    details = [
        [
            Paragraph("Receipt No:", lbl),
            Paragraph(data.receipt_no, val),
            Paragraph("Date:", lbl),
            Paragraph(data.visit_date, val)
        ],
        [
            Paragraph("Patient:", lbl),
            Paragraph(data.patient_name, val),
            Paragraph("Reg. No:", lbl),
            Paragraph(str(data.reg_no), val)
        ],
        [
            Paragraph("Age/Gender:", lbl),
            Paragraph(
                f"{data.patient_age or '-'} / "
                f"{data.patient_gender or '-'}",
                val
            ),
            Paragraph("Contact:", lbl),
            Paragraph(data.patient_phone or "-", val)
        ],
        [
            Paragraph("Visit Type:", lbl),
            Paragraph(data.visit_type, val),
            Paragraph("Complaint:", lbl),
            Paragraph(data.chief_complaint or "-", val)
        ]
    ]

    dt = Table(
        details,
        colWidths=[28 * mm, 40 * mm, 25 * mm, 40 * mm]
    )

    dt.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS",
         (0, 0), (-1, -1),
         [VENNOVA_LIGHT, colors.white]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
    ]))

    content.append(dt)
    content.append(Spacer(1, 8 * mm))

    # ── Payment Table ──────────────────────────────────
    payment = [
        ["Consultation Fee", f"Rs. {data.amount:.2f}"],
        ["Payment Mode", data.payment_mode],
        ["Amount Paid", f"Rs. {data.amount:.2f}"],
    ]

    pt = Table(
        payment,
        colWidths=[80 * mm, 50 * mm]
    )

    pt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), VENNOVA_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        ("BACKGROUND",
         (0, 2), (-1, 2),
         colors.HexColor("#e8f5e9")),

        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),

        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),

        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))

    content.append(pt)
    content.append(Spacer(1, 8 * mm))

    # ── Signature ──────────────────────────────────────
    sig_data = [
        [
            Paragraph(
                "Patient's Signature: _______________",
                ParagraphStyle(
                    "sl",
                    parent=styles["Normal"],
                    fontSize=8
                )
            ),

            Paragraph(
                f"<b>{data.doctor_name}</b><br/>"
                f"{data.qualification or 'B.H.M.S.'}<br/>"
                f"Homoeopathic Consultant",

                ParagraphStyle(
                    "sr",
                    parent=styles["Normal"],
                    fontSize=8,
                    alignment=TA_RIGHT
                )
            )
        ]
    ]

    st = Table(
        sig_data,
        colWidths=[80 * mm, 53 * mm]
    )

    content.append(st)
    content.append(Spacer(1, 6 * mm))

    # ── Footer ─────────────────────────────────────────
    content.append(HRFlowable(
        width="100%",
        thickness=0.5,
        color=colors.grey,
        spaceAfter=3
    ))

    content.append(Paragraph(
        "Thank you for visiting. Please preserve this receipt.",
        ParagraphStyle(
            "f1",
            parent=styles["Normal"],
            fontSize=7,
            alignment=TA_CENTER,
            textColor=TEXT_GREY
        )
    ))

    content.append(Paragraph(
        "Powered by <b>Vennova</b> — Clinic Growth Engine",
        ParagraphStyle(
            "f2",
            parent=styles["Normal"],
            fontSize=7,
            alignment=TA_CENTER,
            textColor=VENNOVA_BLUE
        )
    ))

    # ── Build PDF ──────────────────────────────────────
    doc.build(content)

    # Return temp file path
    return output_path