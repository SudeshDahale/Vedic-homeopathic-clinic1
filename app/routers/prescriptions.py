from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from sqlalchemy.orm import Session

from app.database import get_db

from app.services.prescription_service import (
    generate_prescription
)

from app.services.whatsapp_service import (
    send_text_message
)

from app.middleware.auth_middleware import (
    doctor_only
)

from app.models.user import User
from app.models.patient import Patient
from app.models.clinic import Clinic
from app.models.visit import Visit


router = APIRouter(
    prefix="/prescriptions",
    tags=["Prescriptions"]
)


# =========================================================
# Generate Prescription
# =========================================================
@router.post("/generate/{visit_id}")
def create_prescription(
    visit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(doctor_only)
):
    """
    Generate prescription PDF.

    Doctor only.
    """

    return generate_prescription(
        db,
        visit_id,
        current_user.clinic_id
    )


# =========================================================
# Download Prescription
# =========================================================
@router.get("/download/{visit_id}")
def download_prescription(
    visit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(doctor_only)
):
    """
    Redirect user directly to Supabase PDF URL.
    """

    result = generate_prescription(
        db,
        visit_id,
        current_user.clinic_id
    )

    pdf_url = result.get("pdf_url")

    if not pdf_url:
        raise HTTPException(
            status_code=404,
            detail="Prescription file not found"
        )

    return RedirectResponse(
        url=pdf_url
    )


# =========================================================
# Send Prescription on WhatsApp
# =========================================================
@router.post("/send/{visit_id}")
async def send_prescription_whatsapp(
    visit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(doctor_only)
):
    """
    Generate prescription
    +
    Send WhatsApp notification.
    """

    # -----------------------------------------
    # Generate Prescription
    # -----------------------------------------
    result = generate_prescription(
        db,
        visit_id,
        current_user.clinic_id
    )

    # -----------------------------------------
    # Get Visit
    # -----------------------------------------
    visit = db.query(Visit).filter(
        Visit.id == visit_id
    ).first()

    if not visit:
        raise HTTPException(
            status_code=404,
            detail="Visit not found"
        )

    # -----------------------------------------
    # Get Patient
    # -----------------------------------------
    patient = db.query(Patient).filter(
        Patient.id == visit.patient_id
    ).first()

    # -----------------------------------------
    # Get Clinic
    # -----------------------------------------
    clinic = db.query(Clinic).filter(
        Clinic.id == current_user.clinic_id
    ).first()

    # -----------------------------------------
    # WhatsApp Send
    # -----------------------------------------
    whatsapp_result = None

    if (
        patient
        and patient.phone_mobile
    ):

        clinic_name = (
            clinic.name
            if clinic else "Clinic"
        )

        doctor_name = (
            clinic.doctor_name
            if clinic else "Doctor"
        )

        clinic_phone = (
            clinic.phone
            if clinic else ""
        )

        message = (
            f"Dear {patient.first_name}, "
            f"your prescription from "
            f"{clinic_name} is ready.\n\n"

            f"Doctor: Dr. {doctor_name}\n"

            f"Prescription PDF:\n"
            f"{result['pdf_url']}\n\n"

            f"For assistance call:\n"
            f"{clinic_phone}\n\n"

            f"- Powered by Vennova"
        )

        whatsapp_result = await send_text_message(
            patient.phone_mobile,
            message
        )

    # -----------------------------------------
    # Final Response
    # -----------------------------------------
    return {
        "message": (
            "Prescription generated successfully"
        ),

        "pdf_url": result["pdf_url"],

        "patient": result["patient"],

        "visit_type": result["visit_type"],

        "whatsapp": whatsapp_result
    }