import json

from sqlalchemy.orm import Session
from fastapi import HTTPException
from types import SimpleNamespace

from app.models.visit import (
    Visit,
    AllopathyRx,
    HomeopathyCase
)

from app.models.patient import Patient
from app.models.clinic import Clinic

from app.services.pdf_service import generate_prescription_pdf
from app.utils.storage import upload_pdf


def generate_prescription(
    db: Session,
    visit_id: str,
    clinic_id: str
) -> dict:
    """
    Generate prescription PDF for any visit type.

    Railway-safe flow:
    1. Generate PDF in /tmp/
    2. Upload to Supabase Storage
    3. Return permanent URL
    """

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

    # =====================================================
    # Get Clinic
    # =====================================================
    clinic = db.query(Clinic).filter(
        Clinic.id == clinic_id
    ).first()

    # =====================================================
    # Build Medicines
    # =====================================================
    medicines = []

    # Allopathy
    if visit.allopathy_rx and visit.allopathy_rx.medicines:
        try:
            medicines = json.loads(
                visit.allopathy_rx.medicines
            )
        except Exception:
            medicines = []

    # Homeopathy
    elif (
        visit.homeopathy_case
        and visit.homeopathy_case.remedy
    ):

        hc = visit.homeopathy_case

        medicines = [{
            "name": hc.remedy,
            "dosage": hc.potency or "-",
            "frequency": hc.repetition or "-",
            "duration": "As advised",
            "instructions": (
                f"Miasm: {hc.miasm}"
                if hc.miasm else ""
            )
        }]

    # =====================================================
    # Create OBJECT instead of DICT
    # =====================================================
    prescription_data = SimpleNamespace(

        # Clinic
        clinic_name=(
            clinic.name
            if clinic else "Homoeopathic Clinic"
        ),

        doctor_name=(
            clinic.doctor_name
            if clinic else "Doctor"
        ),

        qualification=(
            clinic.qualification
            if clinic else "B.H.M.S."
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
            f"{patient.last_name or ''}".strip()
            if patient else "Patient"
        ),

        patient_age=(
            patient.age
            if patient else "-"
        ),

        patient_gender=(
            str(patient.gender)
            if patient and patient.gender
            else "-"
        ),

        reg_no=(
            patient.reg_no
            if patient else 0
        ),

        total_visits=(
            patient.total_visits
            if patient else 1
        ),

        # Visit
        visit_date=(
            visit.visit_date.strftime("%d-%m-%Y")
            if visit.visit_date else ""
        ),

        chief_complaint=(
            visit.chief_complaint or "-"
        ),

        visit_type=(
            str(visit.type)
            if visit.type else ""
        ),

        # Prescription
        medicines=medicines,

        advice=(
            visit.allopathy_rx.advice
            if visit.allopathy_rx
            else None
        ),

        next_visit_date=(
            str(visit.allopathy_rx.next_visit_date)
            if (
                visit.allopathy_rx
                and visit.allopathy_rx.next_visit_date
            )
            else None
        )
    )

    # =====================================================
    # STEP 1:
    # Generate PDF
    # =====================================================
    pdf_path = generate_prescription_pdf(
        prescription_data
    )

    # =====================================================
    # STEP 2:
    # Upload PDF
    # =====================================================
    pdf_url = upload_pdf(
        pdf_path,
        folder="prescriptions"
    )

    # =====================================================
    # STEP 3:
    # Return Response
    # =====================================================
    return {
        "pdf_url": pdf_url,
        "visit_id": visit_id,

        "patient": (
            prescription_data.patient_name
        ),

        "visit_type": (
            prescription_data.visit_type
        ),

        "message": (
            "Prescription generated successfully"
        )
    }