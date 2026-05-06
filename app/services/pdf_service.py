import os
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
    TA_RIGHT,
    TA_LEFT
)

from app.schemas.billing import ReceiptData

# ─────────────────────────────────────────────────────
# Receipts folder
# ─────────────────────────────────────────────────────
RECEIPTS_DIR = "receipts"
os.makedirs(RECEIPTS_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────
# PDF Receipt Generator
# ─────────────────────────────────────────────────────
def generate_receipt_pdf(data: ReceiptData) -> str:

    filename = f"{RECEIPTS_DIR}/receipt_{data.receipt_no}.pdf"

    doc = SimpleDocTemplate(
        filename,
        pagesize=A5,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        leftMargin=12 * mm,
        rightMargin=12 * mm
    )

    styles = getSampleStyleSheet()
    content = []

    # ─────────────────────────────────────────────────
    # Header Styles
    # ─────────────────────────────────────────────────
    header_style = ParagraphStyle(
        "header",
        parent=styles["Normal"],
        fontSize=15,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1a237e"),
        spaceAfter=2
    )

    sub_style = ParagraphStyle(
        "sub",
        parent=styles["Normal"],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#333333"),
        spaceAfter=1
    )

    label_style = ParagraphStyle(
        "label",
        parent=styles["Normal"],
        fontSize=9,
        fontName="Helvetica-Bold"
    )

    value_style = ParagraphStyle(
        "value",
        parent=styles["Normal"],
        fontSize=9
    )

    footer_style = ParagraphStyle(
        "footer",
        parent=styles["Normal"],
        fontSize=7,
        alignment=TA_CENTER,
        textColor=colors.grey,
        leading=10
    )

    # ─────────────────────────────────────────────────
    # Clinic Header
    # ─────────────────────────────────────────────────
    content.append(
        Paragraph(
            f"{data.clinic_name}",
            header_style
        )
    )

    content.append(
        Paragraph(
            f"{data.doctor_name} | {data.qualification or 'B.H.M.S.'}",
            sub_style
        )
    )

    if data.clinic_address:
        content.append(
            Paragraph(
                data.clinic_address,
                sub_style
            )
        )

    if data.clinic_phone:
        content.append(
            Paragraph(
                f"Mobile: {data.clinic_phone}",
                sub_style
            )
        )

    if data.clinic_timings:
        content.append(
            Paragraph(
                f"Timings: {data.clinic_timings}",
                sub_style
            )
        )

    content.append(
        HRFlowable(
            width="100%",
            thickness=1.5,
            color=colors.HexColor("#1a237e"),
            spaceAfter=6
        )
    )

    # ─────────────────────────────────────────────────
    # Receipt Title
    # ─────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "title",
        parent=styles["Normal"],
        fontSize=11,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1a237e"),
        spaceAfter=8
    )

    content.append(
        Paragraph(
            "PAYMENT RECEIPT",
            title_style
        )
    )

    # ─────────────────────────────────────────────────
    # Patient Details Table
    # ─────────────────────────────────────────────────
    details_data = [
        [
            Paragraph("Receipt No:", label_style),
            Paragraph(data.receipt_no, value_style),

            Paragraph("Date:", label_style),
            Paragraph(data.visit_date, value_style)
        ],

        [
            Paragraph("Patient Name:", label_style),
            Paragraph(data.patient_name, value_style),

            Paragraph("Reg. No:", label_style),
            Paragraph(str(data.reg_no), value_style)
        ],

        [
            Paragraph("Age / Gender:", label_style),
            Paragraph(
                f"{data.patient_age or '-'} / {data.patient_gender or '-'}",
                value_style
            ),

            Paragraph("Contact:", label_style),
            Paragraph(data.patient_phone or "-", value_style)
        ],

        [
            Paragraph("Visit Type:", label_style),
            Paragraph(data.visit_type, value_style),

            Paragraph("Complaint:", label_style),
            Paragraph(data.chief_complaint or "-", value_style)
        ]
    ]

    details_table = Table(
        details_data,
        colWidths=[28 * mm, 40 * mm, 25 * mm, 40 * mm]
    )

    details_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),

        ("ROWBACKGROUNDS",
         (0, 0),
         (-1, -1),
         [colors.HexColor("#f5f5f5"), colors.white]),

        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
    ]))

    content.append(details_table)

    content.append(Spacer(1, 8 * mm))

    # ─────────────────────────────────────────────────
    # Payment Section
    # ─────────────────────────────────────────────────
    payment_data = [
        ["Consultation Fee", f"Rs. {data.amount:.2f}"],
        ["Payment Mode", data.payment_mode or "Cash"],
        ["Amount Paid", f"Rs. {data.amount:.2f}"],
    ]

    payment_table = Table(
        payment_data,
        colWidths=[80 * mm, 50 * mm]
    )

    payment_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0),
         colors.HexColor("#1a237e")),

        ("TEXTCOLOR", (0, 0), (-1, 0),
         colors.white),

        ("FONTNAME", (0, 0), (-1, 0),
         "Helvetica-Bold"),

        ("BACKGROUND", (0, 2), (-1, 2),
         colors.HexColor("#e8f5e9")),

        ("FONTNAME", (0, 2), (-1, 2),
         "Helvetica-Bold"),

        ("FONTSIZE", (0, 0), (-1, -1), 10),

        ("GRID", (0, 0), (-1, -1),
         0.5, colors.grey),

        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),

        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))

    content.append(payment_table)

    content.append(Spacer(1, 10 * mm))

    # ─────────────────────────────────────────────────
    # Signature Section
    # ─────────────────────────────────────────────────
    doctor_sign_style = ParagraphStyle(
        "doctor_sign",
        parent=styles["Normal"],
        fontSize=9,
        alignment=TA_RIGHT,
        leading=12
    )

    patient_sign_style = ParagraphStyle(
        "patient_sign",
        parent=styles["Normal"],
        fontSize=8,
        alignment=TA_LEFT
    )

    sig_data = [
        ["", ""],

        [
            "",
            Paragraph(
                f"""
                <b>{data.doctor_name}</b><br/>
                {data.qualification or 'B.H.M.S.'}<br/>
                Homoeopathic Consultant
                """,
                doctor_sign_style
            )
        ]
    ]

    sig_table = Table(
        sig_data,
        colWidths=[80 * mm, 53 * mm]
    )

    sig_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))

    content.append(sig_table)

    content.append(Spacer(1, 2 * mm))

    sig_line_data = [
        [
            Paragraph(
                "Patient Signature: ____________________",
                patient_sign_style
            ),

            Paragraph(
                "Doctor Signature: ____________________",
                ParagraphStyle(
                    "doctor_line",
                    parent=styles["Normal"],
                    fontSize=8,
                    alignment=TA_RIGHT
                )
            )
        ]
    ]

    sig_line_table = Table(
        sig_line_data,
        colWidths=[80 * mm, 53 * mm]
    )

    sig_line_table.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))

    content.append(sig_line_table)

    content.append(Spacer(1, 4 * mm))

    # ─────────────────────────────────────────────────
    # Footer
    # ─────────────────────────────────────────────────
    content.append(
        HRFlowable(
            width="100%",
            thickness=0.5,
            color=colors.grey,
            spaceAfter=4
        )
    )

    content.append(
        Paragraph(
            "Thank you for visiting Vedic Homoeopathic Clinic.",
            footer_style
        )
    )

    content.append(
        Paragraph(
            "Please preserve this receipt for future consultation and follow-up.",
            footer_style
        )
    )

    content.append(
        Paragraph(
            "This is a computer-generated receipt and does not require physical seal.",
            footer_style
        )
    )

    # ─────────────────────────────────────────────────
    # Build PDF
    # ─────────────────────────────────────────────────
    doc.build(content)

    return filename