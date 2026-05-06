from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime
from app.models.billing import Payment
from app.models.visit import Visit
from app.models.patient import Patient
from app.models.clinic import Clinic
from app.schemas.billing import ReceiptData
from app.services.pdf_service import generate_receipt_pdf
import uuid


def get_payment_by_visit(db: Session, visit_id: str, clinic_id: str) -> Payment:
    """Get payment record for a visit"""
    visit = db.query(Visit).filter(
        Visit.id        == visit_id,
        Visit.clinic_id == clinic_id
    ).first()

    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found"
        )

    if not visit.payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No payment found for this visit. Close the visit first."
        )

    return visit.payment


def generate_receipt(db: Session, visit_id: str, clinic_id: str) -> dict:
    """
    Generate PDF receipt for a closed visit.
    Pulls clinic info, patient info, payment info —
    combines into professional PDF matching clinic letterhead.
    """
    # Get visit
    visit = db.query(Visit).filter(
        Visit.id        == visit_id,
        Visit.clinic_id == clinic_id
    ).first()

    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    if not visit.closed_at:
        raise HTTPException(
            status_code=400,
            detail="Visit not closed yet. Close visit before generating receipt."
        )

    # Get patient
    patient = db.query(Patient).filter(
        Patient.id == visit.patient_id
    ).first()

    # Get clinic
    clinic = db.query(Clinic).filter(
        Clinic.id == clinic_id
    ).first()

    # Build receipt data
    receipt_no = f"RCP-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"

    receipt_data = ReceiptData(
        # Clinic
        clinic_name    = clinic.name if clinic else "Vedic Homoeopathic Clinic",
        doctor_name    = clinic.doctor_name if clinic else "Doctor",
        qualification  = clinic.qualification if clinic else "B.H.M.S.",
        clinic_address = clinic.address if clinic else "",
        clinic_phone   = clinic.phone if clinic else "",
        clinic_timings = clinic.timings if clinic else "",

        # Patient
        patient_name   = f"{patient.first_name} {patient.last_name or ''}".strip() if patient else "Patient",
        patient_age    = patient.age if patient else None,
        patient_gender = patient.gender.value if patient and patient.gender else None,
        patient_phone  = patient.phone_mobile if patient else None,
        reg_no         = patient.reg_no if patient else 0,

        # Visit
        visit_date      = visit.visit_date.strftime("%d-%m-%Y") if visit.visit_date else "",
        visit_type      = visit.type.value if visit.type else "",
        chief_complaint = visit.chief_complaint,

        # Payment
        amount       = float(visit.fee or 0),
        payment_mode = visit.payment_mode.value if visit.payment_mode else "CASH",
        receipt_no   = receipt_no
    )

    # Generate PDF
    pdf_path = generate_receipt_pdf(receipt_data)

    # Save receipt path to payment record
    if visit.payment:
        visit.payment.receipt_url = pdf_path
        db.commit()

    return {
        "receipt_no":  receipt_no,
        "pdf_path":    pdf_path,
        "patient":     receipt_data.patient_name,
        "amount":      receipt_data.amount,
        "visit_date":  receipt_data.visit_date,
        "message":     "Receipt generated successfully"
    }