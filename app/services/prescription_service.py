import json

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.visit import Visit
from app.models.patient import Patient
from app.models.clinic import Clinic

from app.services.pdf_service import (
    generate_prescription_pdf,
    PrescriptionData
)

from app.utils.storage import upload_pdf


def generate_prescription(
    db: Session,
    visit_id: str,
    clinic_id: str
) -> dict:

    # =====================================================
    # Get Visit
    # =====================================================
    visit = db.query(Visit).filter(
        Visit.id == visit_id,
        Visit.clinic_id == clinic_id
    ).first()

    if not visit:
        raise HTTPException(
            status_code=404,
            detail="Visit not found"
        )

    # =====================================================
    # Get Patient
    # =====================================================
    patient = db.query(Patient).filter(
        Patient.id == visit.patient_id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # =====================================================
    # Get Clinic
    # =====================================================
    clinic = db.query(Clinic).filter(
        Clinic.id == clinic_id
    ).first()

    # =====================================================
    # Detect Visit Type
    # =====================================================
    visit_type = str(visit.type).upper() if visit.type else "HOMEOPATHY"

    # =====================================================
    # Build Medicine Data
    # =====================================================
    medicines = []

    remedy = ""
    potency = ""
    repetition = ""

    # -------------------------
    # Allopathy
    # -------------------------
    if visit.allopathy_rx:

        rx = visit.allopathy_rx

        if rx.medicines:
            try:
                medicines = json.loads(rx.medicines)
            except Exception:
                medicines = []

    # -------------------------
    # Homeopathy
    # -------------------------
    if visit.homeopathy_case:

        hc = visit.homeopathy_case

        remedy = hc.remedy or ""
        potency = hc.potency or ""
        repetition = hc.repetition or ""

    # =====================================================
    # Build Proper PrescriptionData Object
    # =====================================================
    prescription_data = PrescriptionData(

        # Clinic
        clinic_name=(
            clinic.name
            if clinic else "Vedic Homoeopathic Clinic"
        ),

        doctor_name=(
            clinic.doctor_name
            if clinic else "Doctor"
        ),

        qualification=(
            clinic.qualification
            if clinic else "B.H.M.S."
        ),

        reg_number=(
            clinic.registration_number
            if clinic and hasattr(clinic, "registration_number")
            else ""
        ),

        clinic_address=(
            clinic.address
            if clinic else ""
        ),

        clinic_phone=(
            clinic.phone
            if clinic else ""
        ),

        clinic_timings=(
            clinic.timings
            if clinic else ""
        ),

        # Patient
        patient_name=(
            f"{patient.first_name} "
            f"{patient.last_name or ''}"
        ).strip(),

        patient_age=patient.age,

        patient_gender=(
            str(patient.gender)
            if patient.gender else ""
        ),

        patient_reg_no=(
            patient.reg_no
            if hasattr(patient, "reg_no")
            else ""
        ),

        # Visit
        visit_date=(
            visit.visit_date.strftime("%d-%m-%Y")
            if visit.visit_date else ""
        ),

        visit_number=(
            patient.total_visits
            if patient.total_visits else 1
        ),

        chief_complaint=(
            visit.chief_complaint or ""
        ),

        visit_type=visit_type,

        # Homeopathy
        remedy=remedy,
        potency=potency,
        repetition=repetition,

        # Allopathy
        medicines=medicines,

        # Advice
        advice=(
            visit.allopathy_rx.advice
            if visit.allopathy_rx
            else ""
        ),

        follow_up_date=(
            str(visit.allopathy_rx.next_visit_date)
            if (
                visit.allopathy_rx
                and visit.allopathy_rx.next_visit_date
            )
            else ""
        )
    )

    # =====================================================
    # STEP 1: Generate PDF
    # =====================================================
    pdf_path = generate_prescription_pdf(
        prescription_data
    )

    # =====================================================
    # STEP 2: Upload to Supabase
    # =====================================================
    pdf_url = upload_pdf(
        pdf_path,
        folder="prescriptions"
    )

    # =====================================================
    # STEP 3: Return Response
    # =====================================================
    return {
        "message": "Prescription generated successfully",

        "pdf_url": pdf_url,

        "visit_id": visit_id,

        "patient": prescription_data.patient_name,

        "visit_type": prescription_data.visit_type
    }