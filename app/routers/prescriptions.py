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


# =====================================================
# ROUTER
# =====================================================

router = APIRouter(

    prefix="/prescriptions",

    tags=["Prescriptions"]
)


# =====================================================
# GENERATE PRESCRIPTION
# =====================================================

@router.post("/generate/{visit_id}")
def create_prescription(
    visit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        doctor_only
    )
):

    return generate_prescription(

        db,

        visit_id,

        current_user.clinic_id
    )


# =====================================================
# DOWNLOAD PRESCRIPTION
# =====================================================

@router.get("/download/{visit_id}")
def download_prescription(
    visit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        doctor_only
    )
):

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


# =====================================================
# SEND PRESCRIPTION WHATSAPP
# =====================================================

@router.post("/send/{visit_id}")
async def send_prescription_whatsapp(
    visit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        doctor_only
    )
):

    result = generate_prescription(

        db,

        visit_id,

        current_user.clinic_id
    )

    visit = db.query(Visit).filter(

        Visit.id == visit_id

    ).first()

    if not visit:

        raise HTTPException(

            status_code=404,

            detail="Visit not found"
        )

    patient = db.query(Patient).filter(

        Patient.id == visit.patient_id

    ).first()

    clinic = db.query(Clinic).filter(

        Clinic.id == current_user.clinic_id

    ).first()

    whatsapp_result = None

    if patient and getattr(
        patient,
        "phone_mobile",
        None
    ):

        clinic_name = (

            clinic.name

            if clinic

            else "Clinic"
        )

        doctor_name = (

            clinic.doctor_name

            if clinic

            else "Doctor"
        )

        clinic_phone = (

            clinic.phone

            if clinic

            else ""
        )

        patient_name = (

            patient.first_name

            if getattr(
                patient,
                "first_name",
                None
            )

            else "Patient"
        )

        message = (

            f"Dear {patient_name}, "

            f"your prescription from "

            f"{clinic_name} is ready.\n\n"

            f"Doctor: Dr. {doctor_name}\n\n"

            f"Prescription PDF:\n"

            f"{result['pdf_url']}\n\n"

            f"For assistance call:\n"

            f"{clinic_phone}\n\n"

            f"- Powered by Vennova"
        )

        try:

            whatsapp_result = await send_text_message(

                patient.phone_mobile,

                message
            )

        except Exception as e:

            whatsapp_result = {

                "success": False,

                "error": str(e)
            }

    return {

        "message":
            "Prescription generated successfully",

        "pdf_url":
            result.get("pdf_url"),

        "patient":
            result.get("patient"),

        "visit_type":
            result.get("visit_type"),

        "whatsapp":
            whatsapp_result
    }