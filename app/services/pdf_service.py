import os
import uuid
import json
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

from app.schemas.billing import ReceiptData


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
    Railway-safe: saves to /tmp/ only.
    Gets uploaded to Supabase Storage after generation.
    """
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

    lbl = ParagraphStyle("lbl", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold")
    val = ParagraphStyle("val", parent=styles["Normal"], fontSize=9)

    details = [
        [Paragraph("Receipt No:", lbl), Paragraph(data.receipt_no, val),
         Paragraph("Date:", lbl),       Paragraph(data.visit_date, val)],
        [Paragraph("Patient:", lbl),    Paragraph(data.patient_name, val),
         Paragraph("Reg. No:", lbl),    Paragraph(str(data.reg_no), val)],
        [Paragraph("Age/Gender:", lbl), Paragraph(f"{data.patient_age or '-'} / {data.patient_gender or '-'}", val),
         Paragraph("Contact:", lbl),    Paragraph(data.patient_phone or "-", val)],
        [Paragraph("Visit Type:", lbl), Paragraph(data.visit_type, val),
         Paragraph("Complaint:", lbl),  Paragraph(data.chief_complaint or "-", val)]
    ]

    dt = Table(details, colWidths=[28*mm, 40*mm, 25*mm, 40*mm])
    dt.setStyle(TableStyle([
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [VENNOVA_LIGHT, colors.white]),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
    ]))

    content.append(dt)
    content.append(Spacer(1, 8*mm))

    payment = [
        ["Consultation Fee", f"Rs. {data.amount:.2f}"],
        ["Payment Mode",     data.payment_mode],
        ["Amount Paid",      f"Rs. {data.amount:.2f}"],
    ]

    pt = Table(payment, colWidths=[80*mm, 50*mm])
    pt.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  VENNOVA_BLUE),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("BACKGROUND",   (0, 2), (-1, 2),  colors.HexColor("#e8f5e9")),
        ("FONTNAME",     (0, 2), (-1, 2),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 10),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.grey),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("ALIGN",        (1, 0), (1, -1),  "RIGHT"),
    ]))

    content.append(pt)
    content.append(Spacer(1, 8*mm))

    sig_data = [[
        Paragraph("Patient's Signature: _______________",
                  ParagraphStyle("sl", parent=styles["Normal"], fontSize=8)),
        Paragraph(f"<b>{data.doctor_name}</b><br/>{data.qualification or 'B.H.M.S.'}<br/>Homoeopathic Consultant",
                  ParagraphStyle("sr", parent=styles["Normal"], fontSize=8, alignment=TA_RIGHT))
    ]]

    content.append(Table(sig_data, colWidths=[80*mm, 53*mm]))
    content.append(Spacer(1, 6*mm))

    content.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceAfter=3))
    content.append(Paragraph(
        "Thank you for visiting. Please preserve this receipt.",
        ParagraphStyle("f1", parent=styles["Normal"], fontSize=7, alignment=TA_CENTER, textColor=TEXT_GREY)
    ))
    content.append(Paragraph(
        "Powered by <b>Vennova</b> — Clinic Growth Engine",
        ParagraphStyle("f2", parent=styles["Normal"], fontSize=7, alignment=TA_CENTER, textColor=VENNOVA_BLUE)
    ))

    doc.build(content)
    return output_path


# ======================================================
# PRESCRIPTION PDF GENERATOR
# ======================================================

class PrescriptionData:
    """Data object for prescription PDF generation."""
    def __init__(self, **kwargs):
        self.clinic_name      = kwargs.get("clinic_name", "Vedic Homoeopathic Clinic")
        self.doctor_name      = kwargs.get("doctor_name", "Doctor")
        self.qualification    = kwargs.get("qualification", "B.H.M.S.")
        self.reg_number       = kwargs.get("reg_number", "")
        self.clinic_address   = kwargs.get("clinic_address", "")
        self.clinic_phone     = kwargs.get("clinic_phone", "")
        self.clinic_timings   = kwargs.get("clinic_timings", "")

        self.patient_name     = kwargs.get("patient_name", "")
        self.patient_age      = kwargs.get("patient_age")
        self.patient_gender   = kwargs.get("patient_gender", "")
        self.patient_reg_no   = kwargs.get("patient_reg_no", "")
        self.visit_date       = kwargs.get("visit_date", datetime.now().strftime("%d-%m-%Y"))
        self.visit_number     = kwargs.get("visit_number", 1)

        self.chief_complaint  = kwargs.get("chief_complaint", "")
        self.visit_type       = kwargs.get("visit_type", "HOMEOPATHY")

        # Homeopathy fields
        self.remedy           = kwargs.get("remedy", "")
        self.potency          = kwargs.get("potency", "")
        self.repetition       = kwargs.get("repetition", "")
        self.medicines        = kwargs.get("medicines", [])  # list of dicts for allopathy

        self.advice           = kwargs.get("advice", "")
        self.follow_up_date   = kwargs.get("follow_up_date", "")


def generate_prescription_pdf(data: PrescriptionData) -> str:
    """
    Generate professional prescription PDF.
    Works for BOTH homeopathy and allopathy visits.

    Homeopathy: shows Remedy + Potency + Repetition
    Allopathy:  shows medicine table with dose/duration

    Railway-safe: saves to /tmp/ only.
    Gets uploaded to Supabase Storage after generation.
    """
    output_path = f"/tmp/prescription_{str(uuid.uuid4())[:8]}.pdf"

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A5,
        topMargin=10*mm,
        bottomMargin=10*mm,
        leftMargin=12*mm,
        rightMargin=12*mm
    )

    styles = _base_styles()
    content = []

    # ── Clinic Header ──────────────────────────────────
    content.append(Paragraph(
        f'"{data.clinic_name}"',
        ParagraphStyle("ph", parent=styles["Normal"], fontSize=14,
                       fontName="Helvetica-Bold", alignment=TA_CENTER,
                       textColor=VENNOVA_BLUE, spaceAfter=1)
    ))

    content.append(Paragraph(
        f"Dr. {data.doctor_name} | {data.qualification}",
        ParagraphStyle("ps", parent=styles["Normal"], fontSize=9,
                       alignment=TA_CENTER, textColor=TEXT_GREY, spaceAfter=1)
    ))

    if data.reg_number:
        content.append(Paragraph(
            f"Reg. No: {data.reg_number}",
            ParagraphStyle("pr", parent=styles["Normal"], fontSize=8,
                           alignment=TA_CENTER, textColor=TEXT_GREY, spaceAfter=1)
        ))

    if data.clinic_address:
        content.append(Paragraph(
            data.clinic_address,
            ParagraphStyle("pa", parent=styles["Normal"], fontSize=8,
                           alignment=TA_CENTER, textColor=TEXT_GREY, spaceAfter=1)
        ))

    if data.clinic_phone:
        content.append(Paragraph(
            f"Tel: {data.clinic_phone}",
            ParagraphStyle("pp", parent=styles["Normal"], fontSize=8,
                           alignment=TA_CENTER, textColor=TEXT_GREY, spaceAfter=1)
        ))

    if data.clinic_timings:
        content.append(Paragraph(
            f"Timings: {data.clinic_timings}",
            ParagraphStyle("pt", parent=styles["Normal"], fontSize=8,
                           alignment=TA_CENTER, textColor=TEXT_GREY, spaceAfter=3)
        ))

    content.append(HRFlowable(width="100%", thickness=1.5, color=VENNOVA_BLUE, spaceAfter=5))

    # ── Prescription Title ─────────────────────────────
    content.append(Paragraph(
        "PRESCRIPTION",
        ParagraphStyle("ptitle", parent=styles["Normal"], fontSize=11,
                       fontName="Helvetica-Bold", alignment=TA_CENTER,
                       textColor=VENNOVA_BLUE, spaceAfter=6)
    ))

    # ── Patient Info Row ───────────────────────────────
    lbl = ParagraphStyle("lbl", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold")
    val = ParagraphStyle("val", parent=styles["Normal"], fontSize=9)

    patient_info = [
        [Paragraph("Patient:", lbl),   Paragraph(data.patient_name, val),
         Paragraph("Date:", lbl),      Paragraph(data.visit_date, val)],
        [Paragraph("Age/Gender:", lbl),Paragraph(f"{data.patient_age or '-'} / {data.patient_gender or '-'}", val),
         Paragraph("Reg. No:", lbl),   Paragraph(str(data.patient_reg_no), val)],
        [Paragraph("Visit #:", lbl),   Paragraph(str(data.visit_number), val),
         Paragraph("Type:", lbl),      Paragraph(data.visit_type, val)],
    ]

    if data.chief_complaint:
        patient_info.append([
            Paragraph("Complaint:", lbl),
            Paragraph(data.chief_complaint, val),
            Paragraph("", lbl),
            Paragraph("", val)
        ])

    pt = Table(patient_info, colWidths=[24*mm, 48*mm, 22*mm, 39*mm])
    pt.setStyle(TableStyle([
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [VENNOVA_LIGHT, colors.white]),
        ("TOPPADDING",     (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 3),
        ("LEFTPADDING",    (0, 0), (-1, -1), 3),
    ]))

    content.append(pt)
    content.append(Spacer(1, 5*mm))

    # ── Rx Symbol ─────────────────────────────────────
    content.append(Paragraph(
        "<b>Rx</b>",
        ParagraphStyle("rx", parent=styles["Normal"], fontSize=14,
                       textColor=VENNOVA_BLUE, spaceAfter=4)
    ))

    # ── Medicine Section ───────────────────────────────
    if data.visit_type == "HOMEOPATHY" and data.remedy:
        # Homeopathy prescription format
        rx_data = [
            [Paragraph("<b>Remedy</b>", lbl),
             Paragraph("<b>Potency</b>", lbl),
             Paragraph("<b>Repetition / Dose</b>", lbl)],
            [Paragraph(data.remedy or "-", val),
             Paragraph(data.potency or "-", val),
             Paragraph(data.repetition or "-", val)],
        ]

        rx_table = Table(rx_data, colWidths=[55*mm, 30*mm, 48*mm])
        rx_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), VENNOVA_BLUE),
            ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 9),
            ("GRID",          (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white]),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ]))

        content.append(rx_table)

    elif data.visit_type == "ALLOPATHY" and data.medicines:
        # Allopathy prescription format
        medicines = data.medicines
        if isinstance(medicines, str):
            try:
                medicines = json.loads(medicines)
            except Exception:
                medicines = []

        if medicines:
            med_rows = [[
                Paragraph("<b>#</b>", lbl),
                Paragraph("<b>Medicine</b>", lbl),
                Paragraph("<b>Dose</b>", lbl),
                Paragraph("<b>Duration</b>", lbl),
            ]]
            for i, med in enumerate(medicines, 1):
                if isinstance(med, dict):
                    med_rows.append([
                        Paragraph(str(i), val),
                        Paragraph(med.get("name", "-"), val),
                        Paragraph(med.get("dose", "-"), val),
                        Paragraph(med.get("duration", "-"), val),
                    ])

            med_table = Table(med_rows, colWidths=[10*mm, 65*mm, 25*mm, 33*mm])
            med_table.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, 0), VENNOVA_BLUE),
                ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
                ("FONTSIZE",      (0, 0), (-1, -1), 9),
                ("GRID",          (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, VENNOVA_LIGHT]),
                ("TOPPADDING",    (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ]))
            content.append(med_table)
    else:
        # Fallback — empty prescription lines
        for _ in range(3):
            content.append(Paragraph(
                "_" * 80,
                ParagraphStyle("line", parent=styles["Normal"], fontSize=9,
                               textColor=TEXT_GREY, spaceAfter=8)
            ))

    content.append(Spacer(1, 5*mm))

    # ── Advice ────────────────────────────────────────
    if data.advice:
        content.append(Paragraph(
            "<b>Advice / Instructions:</b>",
            ParagraphStyle("albl", parent=styles["Normal"], fontSize=9,
                           textColor=VENNOVA_BLUE, spaceAfter=2)
        ))
        content.append(Paragraph(
            data.advice,
            ParagraphStyle("aval", parent=styles["Normal"], fontSize=9,
                           textColor=TEXT_DARK, spaceAfter=4)
        ))

    # ── Follow-up ─────────────────────────────────────
    if data.follow_up_date:
        content.append(Paragraph(
            f"<b>Next Follow-up:</b>  {data.follow_up_date}",
            ParagraphStyle("fu", parent=styles["Normal"], fontSize=9,
                           textColor=VENNOVA_GREEN, spaceAfter=6)
        ))

    content.append(Spacer(1, 6*mm))

    # ── Signature ─────────────────────────────────────
    content.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceAfter=4))

    sig_data = [[
        Paragraph("", val),
        Paragraph(
            f"<b>Dr. {data.doctor_name}</b><br/>"
            f"{data.qualification}<br/>"
            f"Homoeopathic Consultant",
            ParagraphStyle("sig", parent=styles["Normal"], fontSize=8, alignment=TA_RIGHT)
        )
    ]]
    content.append(Table(sig_data, colWidths=[80*mm, 53*mm]))
    content.append(Spacer(1, 4*mm))

    # ── Footer ────────────────────────────────────────
    content.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceAfter=2))
    content.append(Paragraph(
        "This prescription is valid for 30 days from the date of issue.",
        ParagraphStyle("f1", parent=styles["Normal"], fontSize=7,
                       alignment=TA_CENTER, textColor=TEXT_GREY)
    ))
    content.append(Paragraph(
        "Powered by <b>Vennova</b> — Clinic Growth Engine",
        ParagraphStyle("f2", parent=styles["Normal"], fontSize=7,
                       alignment=TA_CENTER, textColor=VENNOVA_BLUE)
    ))

    doc.build(content)
    return output_path