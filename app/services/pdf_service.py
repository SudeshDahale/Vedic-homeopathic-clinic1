import os
import uuid
from datetime import datetime
from reportlab.lib.pagesizes import A5
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from app.schemas.billing import ReceiptData

RECEIPTS_DIR      = "receipts"
PRESCRIPTIONS_DIR = "prescriptions"
os.makedirs(RECEIPTS_DIR,      exist_ok=True)
os.makedirs(PRESCRIPTIONS_DIR, exist_ok=True)

# ── Brand Colors ───────────────────────────────────────
VENNOVA_BLUE   = colors.HexColor("#1a237e")
VENNOVA_GREEN  = colors.HexColor("#00897b")
VENNOVA_LIGHT  = colors.HexColor("#e8eaf6")
TEXT_DARK      = colors.HexColor("#1a1a2e")
TEXT_GREY      = colors.HexColor("#666666")


def _base_styles():
    styles = getSampleStyleSheet()
    return styles


def generate_receipt_pdf(data: ReceiptData) -> str:
    """
    Generate payment receipt PDF.
    Header: Clinic name + doctor info (customizable per clinic)
    Footer: Powered by Vennova (always shown — free marketing)
    """
    filename = f"{RECEIPTS_DIR}/receipt_{data.receipt_no}.pdf"
    doc      = SimpleDocTemplate(
        filename,
        pagesize     = A5,
        topMargin    = 10 * mm,
        bottomMargin = 10 * mm,
        leftMargin   = 12 * mm,
        rightMargin  = 12 * mm
    )

    styles  = _base_styles()
    content = []

    # ── Clinic Header ──────────────────────────────────
    content.append(Paragraph(
        f'"{data.clinic_name}"',
        ParagraphStyle("h", parent=styles["Normal"],
                       fontSize=14, fontName="Helvetica-Bold",
                       alignment=TA_CENTER, textColor=VENNOVA_BLUE,
                       spaceAfter=2)
    ))
    content.append(Paragraph(
        f"{data.doctor_name} | {data.qualification or 'B.H.M.S.'}",
        ParagraphStyle("sub", parent=styles["Normal"],
                       fontSize=9, alignment=TA_CENTER,
                       textColor=TEXT_GREY, spaceAfter=1)
    ))
    if data.clinic_address:
        content.append(Paragraph(
            data.clinic_address,
            ParagraphStyle("addr", parent=styles["Normal"],
                           fontSize=8, alignment=TA_CENTER,
                           textColor=TEXT_GREY, spaceAfter=1)
        ))
    if data.clinic_phone:
        content.append(Paragraph(
            f"Mobile: {data.clinic_phone}",
            ParagraphStyle("ph", parent=styles["Normal"],
                           fontSize=8, alignment=TA_CENTER,
                           textColor=TEXT_GREY, spaceAfter=1)
        ))
    if data.clinic_timings:
        content.append(Paragraph(
            f"Timings: {data.clinic_timings}",
            ParagraphStyle("t", parent=styles["Normal"],
                           fontSize=8, alignment=TA_CENTER,
                           textColor=TEXT_GREY, spaceAfter=4)
        ))

    content.append(HRFlowable(width="100%", thickness=1.5,
                               color=VENNOVA_BLUE, spaceAfter=6))

    # ── Receipt Title ──────────────────────────────────
    content.append(Paragraph(
        "PAYMENT RECEIPT",
        ParagraphStyle("title", parent=styles["Normal"],
                       fontSize=11, fontName="Helvetica-Bold",
                       alignment=TA_CENTER, textColor=VENNOVA_BLUE,
                       spaceAfter=8)
    ))

    # ── Details Table ──────────────────────────────────
    lbl = ParagraphStyle("lbl", parent=styles["Normal"],
                          fontSize=9, fontName="Helvetica-Bold")
    val = ParagraphStyle("val", parent=styles["Normal"], fontSize=9)

    details = [
        [Paragraph("Receipt No:", lbl), Paragraph(data.receipt_no, val),
         Paragraph("Date:", lbl),       Paragraph(data.visit_date, val)],
        [Paragraph("Patient:", lbl),    Paragraph(data.patient_name, val),
         Paragraph("Reg. No:", lbl),    Paragraph(str(data.reg_no), val)],
        [Paragraph("Age/Gender:", lbl), Paragraph(
             f"{data.patient_age or '-'} / {data.patient_gender or '-'}", val),
         Paragraph("Contact:", lbl),    Paragraph(data.patient_phone or "-", val)],
        [Paragraph("Visit Type:", lbl), Paragraph(data.visit_type, val),
         Paragraph("Complaint:", lbl),  Paragraph(data.chief_complaint or "-", val)],
    ]
    dt = Table(details, colWidths=[28*mm, 40*mm, 25*mm, 40*mm])
    dt.setStyle(TableStyle([
        ("VALIGN",         (0,0), (-1,-1), "TOP"),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [VENNOVA_LIGHT, colors.white]),
        ("TOPPADDING",     (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",  (0,0), (-1,-1), 4),
        ("LEFTPADDING",    (0,0), (-1,-1), 3),
    ]))
    content.append(dt)
    content.append(Spacer(1, 8*mm))

    # ── Payment Box ────────────────────────────────────
    payment = [
        ["Consultation Fee",  f"Rs. {data.amount:.2f}"],
        ["Payment Mode",      data.payment_mode],
        ["Amount Paid",       f"Rs. {data.amount:.2f}"],
    ]
    pt = Table(payment, colWidths=[80*mm, 50*mm])
    pt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), VENNOVA_BLUE),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("BACKGROUND",    (0,2), (-1,2), colors.HexColor("#e8f5e9")),
        ("FONTNAME",      (0,2), (-1,2), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 10),
        ("GRID",          (0,0), (-1,-1), 0.5, colors.grey),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("ALIGN",         (1,0), (1,-1),  "RIGHT"),
    ]))
    content.append(pt)
    content.append(Spacer(1, 8*mm))

    # ── Signature ──────────────────────────────────────
    sig_data = [
        [Paragraph("Patient's Signature: _______________",
                   ParagraphStyle("sl", parent=styles["Normal"],
                                  fontSize=8)),
         Paragraph(
             f"<b>{data.doctor_name}</b><br/>"
             f"{data.qualification or 'B.H.M.S.'}<br/>"
             f"Homoeopathic Consultant",
             ParagraphStyle("sr", parent=styles["Normal"],
                            fontSize=8, alignment=TA_RIGHT))]
    ]
    st = Table(sig_data, colWidths=[80*mm, 53*mm])
    content.append(st)
    content.append(Spacer(1, 6*mm))

    # ── Footer: Powered by Vennova ─────────────────────
    # WHY always show: Free marketing on every receipt.
    # Every patient who sees receipt knows about Vennova.
    content.append(HRFlowable(width="100%", thickness=0.5,
                               color=colors.grey, spaceAfter=3))
    content.append(Paragraph(
        "Thank you for visiting. Please preserve this receipt.",
        ParagraphStyle("f1", parent=styles["Normal"],
                       fontSize=7, alignment=TA_CENTER,
                       textColor=TEXT_GREY)
    ))
    content.append(Paragraph(
        "Powered by <b>Vennova</b> — Clinic Growth Engine",
        ParagraphStyle("f2", parent=styles["Normal"],
                       fontSize=7, alignment=TA_CENTER,
                       textColor=VENNOVA_BLUE)
    ))

    doc.build(content)
    return filename


def generate_prescription_pdf(prescription_data: dict) -> str:
    """
    Generate homeopathy prescription PDF.
    Layout matches Indian clinic standard format.
    Vennova branding in footer — clinic branding in header.
    """
    rx_id    = str(uuid.uuid4())[:8].upper()
    filename = f"{PRESCRIPTIONS_DIR}/prescription_{rx_id}.pdf"

    doc = SimpleDocTemplate(
        filename,
        pagesize     = A5,
        topMargin    = 10 * mm,
        bottomMargin = 10 * mm,
        leftMargin   = 12 * mm,
        rightMargin  = 12 * mm
    )

    styles  = _base_styles()
    content = []

    clinic  = prescription_data.get("clinic", {})
    patient = prescription_data.get("patient", {})
    visit   = prescription_data.get("visit", {})
    rx      = prescription_data.get("prescription", {})

    # ── Clinic Header ──────────────────────────────────
    content.append(Paragraph(
        clinic.get("name", "Homoeopathic Clinic"),
        ParagraphStyle("ch", parent=styles["Normal"],
                       fontSize=14, fontName="Helvetica-Bold",
                       alignment=TA_CENTER, textColor=VENNOVA_BLUE,
                       spaceAfter=2)
    ))
    content.append(Paragraph(
        f"{clinic.get('doctor_name', 'Doctor')} | "
        f"{clinic.get('qualification', 'B.H.M.S.')}",
        ParagraphStyle("cs", parent=styles["Normal"],
                       fontSize=9, alignment=TA_CENTER,
                       textColor=TEXT_GREY, spaceAfter=1)
    ))
    if clinic.get("address"):
        content.append(Paragraph(
            clinic["address"],
            ParagraphStyle("ca", parent=styles["Normal"],
                           fontSize=8, alignment=TA_CENTER,
                           textColor=TEXT_GREY, spaceAfter=1)
        ))
    if clinic.get("phone"):
        content.append(Paragraph(
            f"Mobile: {clinic['phone']}",
            ParagraphStyle("cp", parent=styles["Normal"],
                           fontSize=8, alignment=TA_CENTER,
                           textColor=TEXT_GREY, spaceAfter=1)
        ))

    content.append(HRFlowable(width="100%", thickness=1.5,
                               color=VENNOVA_BLUE, spaceAfter=4))

    # ── Patient Info ───────────────────────────────────
    content.append(Paragraph(
        "PRESCRIPTION",
        ParagraphStyle("pt", parent=styles["Normal"],
                       fontSize=11, fontName="Helvetica-Bold",
                       alignment=TA_CENTER, textColor=VENNOVA_BLUE,
                       spaceAfter=6)
    ))

    lbl = ParagraphStyle("lbl", parent=styles["Normal"],
                          fontSize=9, fontName="Helvetica-Bold")
    val = ParagraphStyle("val", parent=styles["Normal"], fontSize=9)

    pt_info = [
        [Paragraph("Patient:", lbl),
         Paragraph(patient.get("name", "-"), val),
         Paragraph("Date:", lbl),
         Paragraph(visit.get("date", "-"), val)],
        [Paragraph("Age/Gender:", lbl),
         Paragraph(
             f"{patient.get('age', '-')} / {patient.get('gender', '-')}",
             val),
         Paragraph("Reg. No:", lbl),
         Paragraph(str(patient.get("reg_no", "-")), val)],
        [Paragraph("Complaint:", lbl),
         Paragraph(visit.get("chief_complaint", "-"), val),
         Paragraph("Visit #:", lbl),
         Paragraph(str(patient.get("total_visits", 1)), val)],
    ]
    pit = Table(pt_info, colWidths=[25*mm, 55*mm, 22*mm, 31*mm])
    pit.setStyle(TableStyle([
        ("VALIGN",         (0,0), (-1,-1), "TOP"),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [VENNOVA_LIGHT, colors.white]),
        ("TOPPADDING",     (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",  (0,0), (-1,-1), 4),
        ("LEFTPADDING",    (0,0), (-1,-1), 3),
    ]))
    content.append(pit)
    content.append(Spacer(1, 5*mm))

    # ── Medicines (Homeopathy format) ──────────────────
    medicines = rx.get("medicines", [])
    if medicines:
        content.append(Paragraph(
            "Rx",
            ParagraphStyle("rxtitle", parent=styles["Normal"],
                           fontSize=13, fontName="Helvetica-BoldOblique",
                           textColor=VENNOVA_BLUE, spaceAfter=4)
        ))

        med_data = [
            [
                Paragraph("#",        ParagraphStyle("mh", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold")),
                Paragraph("Medicine", ParagraphStyle("mh", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold")),
                Paragraph("Potency",  ParagraphStyle("mh", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold")),
                Paragraph("Dose",     ParagraphStyle("mh", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold")),
                Paragraph("Duration", ParagraphStyle("mh", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold")),
            ]
        ]

        for i, med in enumerate(medicines, 1):
            med_data.append([
                Paragraph(str(i), val),
                Paragraph(med.get("name", "-"), val),
                Paragraph(med.get("dosage", "-"), val),
                Paragraph(med.get("frequency", "-"), val),
                Paragraph(med.get("duration", "-"), val),
            ])

        mt = Table(med_data, colWidths=[8*mm, 45*mm, 22*mm, 22*mm, 22*mm])
        mt.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), VENNOVA_BLUE),
            ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
            ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, VENNOVA_LIGHT]),
            ("GRID",          (0,0), (-1,-1), 0.3, colors.grey),
            ("FONTSIZE",      (0,0), (-1,-1), 8),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING",   (0,0), (-1,-1), 3),
        ]))
        content.append(mt)
        content.append(Spacer(1, 4*mm))

    # ── Advice ─────────────────────────────────────────
    if rx.get("advice"):
        content.append(Paragraph(
            f"<b>General Advice:</b> {rx['advice']}",
            ParagraphStyle("adv", parent=styles["Normal"],
                           fontSize=9, textColor=TEXT_DARK,
                           spaceAfter=3)
        ))

    if rx.get("next_visit_date"):
        content.append(Paragraph(
            f"<b>Follow-up Date:</b> {rx['next_visit_date']}",
            ParagraphStyle("nv", parent=styles["Normal"],
                           fontSize=9, textColor=VENNOVA_GREEN,
                           spaceAfter=3)
        ))

    content.append(Spacer(1, 6*mm))

    # ── Doctor Signature ───────────────────────────────
    sig = [
        ["",
         Paragraph(
             f"<b>{clinic.get('doctor_name', 'Doctor')}</b><br/>"
             f"{clinic.get('qualification', 'B.H.M.S.')}<br/>"
             f"Homoeopathic Consultant",
             ParagraphStyle("drsig", parent=styles["Normal"],
                            fontSize=8, alignment=TA_RIGHT)
         )]
    ]
    st = Table(sig, colWidths=[90*mm, 43*mm])
    content.append(st)
    content.append(Spacer(1, 4*mm))

    # ── Footer: Vennova ────────────────────────────────
    content.append(HRFlowable(width="100%", thickness=0.5,
                               color=colors.grey, spaceAfter=3))
    content.append(Paragraph(
        "Powered by <b>Vennova</b> — Clinic Growth Engine",
        ParagraphStyle("vf", parent=styles["Normal"],
                       fontSize=7, alignment=TA_CENTER,
                       textColor=VENNOVA_BLUE)
    ))

    doc.build(content)
    return filename