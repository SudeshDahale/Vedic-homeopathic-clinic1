import os
import uuid
import json
import io

from datetime import datetime

from reportlab.lib.pagesizes import A5, A4
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

from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from app.schemas.billing import ReceiptData


# ======================================================
# BRAND COLORS
# ======================================================

VENNOVA_BLUE  = colors.HexColor("#1a237e")
VENNOVA_GREEN = colors.HexColor("#00897b")
VENNOVA_LIGHT = colors.HexColor("#e8eaf6")

TEXT_DARK     = colors.HexColor("#1a1a2e")
TEXT_GREY     = colors.HexColor("#666666")


# ======================================================
# BASE STYLES
# ======================================================

def _base_styles():
    return getSampleStyleSheet()


# ======================================================
# RECEIPT PDF GENERATOR
# ======================================================

def generate_receipt_pdf(
    data: ReceiptData
) -> str:
    """
    Generate payment receipt PDF.

    Railway-safe:
    saves to /tmp/ only.
    """

    output_path = (
        f"/tmp/receipt_"
        f"{str(uuid.uuid4())[:8]}.pdf"
    )

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

    # =================================================
    # CLINIC HEADER
    # =================================================

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

        f"{data.doctor_name} | "
        f"{data.qualification or 'B.H.M.S.'}",

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

    # =================================================
    # RECEIPT TITLE
    # =================================================

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

            Paragraph(
                data.patient_phone or "-",
                val
            )
        ],

        [
            Paragraph("Visit Type:", lbl),

            Paragraph(data.visit_type, val),

            Paragraph("Complaint:", lbl),

            Paragraph(
                data.chief_complaint or "-",
                val
            )
        ]
    ]

    dt = Table(
        details,
        colWidths=[28*mm, 40*mm, 25*mm, 40*mm]
    )

    dt.setStyle(TableStyle([

        ("VALIGN",
         (0, 0), (-1, -1),
         "TOP"),

        ("ROWBACKGROUNDS",
         (0, 0), (-1, -1),
         [VENNOVA_LIGHT, colors.white]),

        ("TOPPADDING",
         (0, 0), (-1, -1),
         4),

        ("BOTTOMPADDING",
         (0, 0), (-1, -1),
         4),

        ("LEFTPADDING",
         (0, 0), (-1, -1),
         3),
    ]))

    content.append(dt)

    content.append(
        Spacer(1, 8*mm)
    )

    payment = [

        [
            "Consultation Fee",
            f"Rs. {data.amount:.2f}"
        ],

        [
            "Payment Mode",
            data.payment_mode
        ],

        [
            "Amount Paid",
            f"Rs. {data.amount:.2f}"
        ],
    ]

    pt = Table(
        payment,
        colWidths=[80*mm, 50*mm]
    )

    pt.setStyle(TableStyle([

        ("BACKGROUND",
         (0, 0), (-1, 0),
         VENNOVA_BLUE),

        ("TEXTCOLOR",
         (0, 0), (-1, 0),
         colors.white),

        ("FONTNAME",
         (0, 0), (-1, 0),
         "Helvetica-Bold"),

        ("BACKGROUND",
         (0, 2), (-1, 2),
         colors.HexColor("#e8f5e9")),

        ("FONTNAME",
         (0, 2), (-1, 2),
         "Helvetica-Bold"),

        ("FONTSIZE",
         (0, 0), (-1, -1),
         10),

        ("GRID",
         (0, 0), (-1, -1),
         0.5,
         colors.grey),

        ("TOPPADDING",
         (0, 0), (-1, -1),
         6),

        ("BOTTOMPADDING",
         (0, 0), (-1, -1),
         6),

        ("LEFTPADDING",
         (0, 0), (-1, -1),
         8),

        ("ALIGN",
         (1, 0), (1, -1),
         "RIGHT"),
    ]))

    content.append(pt)

    content.append(
        Spacer(1, 8*mm)
    )

    sig_data = [[

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
    ]]

    content.append(Table(
        sig_data,
        colWidths=[80*mm, 53*mm]
    ))

    content.append(
        Spacer(1, 6*mm)
    )

    content.append(HRFlowable(
        width="100%",
        thickness=0.5,
        color=colors.grey,
        spaceAfter=3
    ))

    content.append(Paragraph(

        "Thank you for visiting. "
        "Please preserve this receipt.",

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

    doc.build(content)

    return output_path


# ======================================================
# MODERN PRESCRIPTION PDF GENERATOR
# ======================================================

def generate_prescription_pdf(
    visit: dict,
    clinic: dict,
    doctor: dict,
    patient: dict
) -> bytes:
    """
    Premium A4 prescription PDF generator.
    """

    buf = io.BytesIO()

    c = canvas.Canvas(
        buf,
        pagesize=A4
    )

    W, H = A4

    # =================================================
    # HEADER BAND
    # =================================================

    c.setFillColorRGB(
        0.12,
        0.18,
        0.35
    )

    c.rect(
        0,
        H - 60*mm,
        W,
        60*mm,
        fill=1,
        stroke=0
    )

    # =================================================
    # CLINIC LOGO
    # =================================================

    logo_path = clinic.get("logo_url")

    if (
        logo_path
        and os.path.exists(logo_path)
    ):

        c.drawImage(

            ImageReader(logo_path),

            15*mm,

            H - 52*mm,

            width=30*mm,

            height=30*mm,

            preserveAspectRatio=True,

            mask="auto"
        )

    # =================================================
    # CLINIC INFO
    # =================================================

    c.setFillColorRGB(1, 1, 1)

    c.setFont(
        "Helvetica-Bold",
        16
    )

    c.drawString(

        55*mm,

        H - 25*mm,

        clinic.get(
            "name",
            "Clinic"
        )
    )

    c.setFont(
        "Helvetica",
        11
    )

    c.drawString(

        55*mm,

        H - 35*mm,

        f"Dr. {doctor.get('name', '')} · "
        f"{doctor.get('qualification', '')}"
    )

    c.drawString(

        55*mm,

        H - 43*mm,

        clinic.get(
            "address",
            ""
        )
    )

    c.drawString(

        55*mm,

        H - 51*mm,

        f"Ph: {clinic.get('phone', '')} · "
        f"Reg: {clinic.get('reg_number', '')}"
    )

    # =================================================
    # PATIENT INFO BAND
    # =================================================

    c.setFillColorRGB(
        0.95,
        0.96,
        0.98
    )

    c.rect(

        0,

        H - 85*mm,

        W,

        25*mm,

        fill=1,

        stroke=0
    )

    c.setFillColorRGB(
        0.1,
        0.1,
        0.1
    )

    c.setFont(
        "Helvetica-Bold",
        10
    )

    c.drawString(

        15*mm,

        H - 70*mm,

        f"Patient: "
        f"{patient.get('name', '')}"
    )

    c.drawString(

        80*mm,

        H - 70*mm,

        f"Age/Sex: "
        f"{patient.get('age', '')} / "
        f"{patient.get('gender', '')}"
    )

    c.drawString(

        140*mm,

        H - 70*mm,

        f"Date: "
        f"{datetime.now().strftime('%d %b %Y')}"
    )

    c.setFont(
        "Helvetica",
        9
    )

    c.drawString(

        15*mm,

        H - 78*mm,

        f"Reg No: "
        f"{patient.get('reg_no', '')}"
        f" · Visit: "
        f"{str(visit.get('id', ''))[:8]}"
    )

    # =================================================
    # RX SYMBOL
    # =================================================

    c.setFont(
        "Helvetica-Bold",
        28
    )

    c.setFillColorRGB(
        0.12,
        0.18,
        0.35
    )

    c.drawString(

        15*mm,

        H - 108*mm,

        "℞"
    )

    # =================================================
    # PRESCRIPTION CONTENT
    # =================================================

    c.setFont(
        "Helvetica",
        11
    )

    c.setFillColorRGB(
        0.1,
        0.1,
        0.1
    )

    y = H - 112*mm

    notes = (

        visit.get("notes")

        or

        visit.get("rx")

        or

        "—"
    )

    for line in notes.split("\n"):

        c.drawString(

            28*mm,

            y,

            line
        )

        y -= 7*mm

        # MULTI PAGE SUPPORT

        if y < 60*mm:

            c.showPage()

            y = H - 30*mm

    # =================================================
    # SIGNATURE
    # =================================================

    sig_path = clinic.get(
        "signature_url"
    )

    if (
        sig_path
        and os.path.exists(sig_path)
    ):

        c.drawImage(

            ImageReader(sig_path),

            W - 70*mm,

            35*mm,

            width=50*mm,

            height=20*mm,

            preserveAspectRatio=True,

            mask="auto"
        )

    c.setFont(
        "Helvetica",
        9
    )

    c.setFillColorRGB(
        0.4,
        0.4,
        0.4
    )

    c.drawString(

        W - 70*mm,

        28*mm,

        f"Dr. {doctor.get('name', '')}"
    )

    c.line(

        W - 70*mm,

        33*mm,

        W - 20*mm,

        33*mm
    )

    # =================================================
    # FOOTER
    # =================================================

    c.setFont(
        "Helvetica",
        8
    )

    c.setFillColorRGB(
        0.6,
        0.6,
        0.6
    )

    c.drawCentredString(

        W / 2,

        15*mm,

        "This is a computer-generated prescription."
    )

    c.save()

    return buf.getvalue()