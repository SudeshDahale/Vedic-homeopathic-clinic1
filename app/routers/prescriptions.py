from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
from app.database import get_db
from app.services.prescription_service import generate_prescription
from app.services.whatsapp_service import send_text_message
from app.middleware.auth_middleware import doctor_only, receptionist_or_doctor
from app.models.user import User
from app.models.patient import Patient
from app.models.clinic import Clinic

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])

@router.post("/generate/{visit_id}")
def create_prescription(
    visit_id:     str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(doctor_only)
):
    """
    Generate prescription PDF for a visit.
    Doctor only — receptionist cannot generate prescriptions.
    """
    return generate_prescription(db, visit_id, current_user.clinic_id)

@router.get("/download/{visit_id}")
def download_prescription(
    visit_id:     str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(doctor_only)
):
    """Download prescription as PDF"""
    result   = generate_prescription(db, visit_id, current_user.clinic_id)
    pdf_path = result["pdf_path"]

    if not os.path.exists(pdf_path):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path       = pdf_path,
        media_type = "application/pdf",
        filename   = f"prescription_{visit_id[:8]}.pdf"
    )

@router.post("/send/{visit_id}")
async def send_prescription_whatsapp(
    visit_id:     str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(doctor_only)
):
    """
    Generate prescription and send link via WhatsApp.
    WHY: Patient has digital copy instantly.
    They share with family = free clinic marketing.
    """
    result  = generate_prescription(db, visit_id, current_user.clinic_id)

    from app.models.visit import Visit
    visit   = db.query(Visit).filter(Visit.id == visit_id).first()
    patient = db.query(Patient).filter(
        Patient.id == visit.patient_id
    ).first() if visit else None
    clinic  = db.query(Clinic).filter(
        Clinic.id == current_user.clinic_id
    ).first()

    if patient and patient.phone_mobile:
        message = (
            f"Dear {patient.first_name}, your prescription from "
            f"{clinic.name if clinic else 'Clinic'} is ready. "
            f"Dr. {clinic.doctor_name if clinic else 'Doctor'} has prescribed "
            f"your medicines. For any queries call {clinic.phone if clinic else ''}. "
            f"- Powered by Vennova"
        )
        wa_result = await send_text_message(patient.phone_mobile, message)
        result["whatsapp"] = wa_result

    return result