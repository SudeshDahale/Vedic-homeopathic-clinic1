from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import os
from app.database import get_db
from app.services.whatsapp_service import (
    send_text_message,
    send_followup_reminder,
    send_thankyou_message,
    send_birthday_message
)
from app.middleware.auth_middleware import receptionist_or_doctor
from app.models.user import User
from app.models.patient import Patient
from app.models.clinic import Clinic

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])

# ── Request schemas ────────────────────────────────────
class SendMessageRequest(BaseModel):
    patient_id: str
    message:    str

class SendReminderRequest(BaseModel):
    patient_id:    str
    followup_type: Optional[str] = "followup_7d"

# ── Webhook verification (Meta requires this) ──────────
@router.get("/webhook")
async def verify_webhook(request: Request):
    """
    Meta calls this once to verify webhook URL.
    WHY: Meta needs to confirm our server is real
    before sending patient reply notifications.
    """
    params      = request.query_params
    mode        = params.get("hub.mode")
    token       = params.get("hub.verify_token")
    challenge   = params.get("hub.challenge")
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "vedic_clinic_webhook_2026")

    if mode == "subscribe" and token == verify_token:
        print("✅ WhatsApp webhook verified")
        return int(challenge)

    raise HTTPException(status_code=403, detail="Webhook verification failed")

@router.post("/webhook")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receives patient replies to WhatsApp messages.
    WHY: When patient replies 'YES' or 'COMING'
    we can auto-update their follow-up status.
    Future: auto-book appointment from reply.
    """
    body = await request.json()

    try:
        entry    = body["entry"][0]
        changes  = entry["changes"][0]
        value    = changes["value"]
        messages = value.get("messages", [])

        for msg in messages:
            phone   = msg["from"].replace("91", "", 1)
            text    = msg.get("text", {}).get("body", "").strip().upper()
            msg_id  = msg.get("id", "")

            print(f"📩 Reply from +91{phone}: {text}")

            # Auto-update follow-up if patient confirms
            if text in ["YES", "COMING", "OK", "WILL COME", "HA", "HAN"]:
                from app.models.reminder import FollowUp, FollowUpStatus
                patient = db.query(Patient).filter(
                    Patient.phone_mobile == phone
                ).first()

                if patient:
                    followup = db.query(FollowUp).filter(
                        FollowUp.patient_id == patient.id,
                        FollowUp.status     == FollowUpStatus.SENT
                    ).order_by(FollowUp.due_date.desc()).first()

                    if followup:
                        followup.status   = FollowUpStatus.DONE
                        followup.response = text
                        db.commit()
                        print(f"✅ Follow-up marked DONE for {patient.first_name}")

    except Exception as e:
        print(f"Webhook error: {e}")

    # Always return 200 to Meta
    return {"status": "ok"}

# ── Send endpoints ─────────────────────────────────────
@router.post("/send/message")
async def send_message(
    data:         SendMessageRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(receptionist_or_doctor)
):
    """Send custom WhatsApp message to a patient"""
    patient = db.query(Patient).filter(
        Patient.id        == data.patient_id,
        Patient.clinic_id == current_user.clinic_id
    ).first()

    if not patient or not patient.phone_mobile:
        raise HTTPException(status_code=404,
                            detail="Patient not found or no phone number")

    result = await send_text_message(patient.phone_mobile, data.message)
    return result

@router.post("/send/reminder")
async def send_reminder(
    data:         SendReminderRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(receptionist_or_doctor)
):
    """
    Manually send follow-up reminder to a patient.
    Receptionist can trigger this from missed patients list.
    """
    patient = db.query(Patient).filter(
        Patient.id        == data.patient_id,
        Patient.clinic_id == current_user.clinic_id
    ).first()

    if not patient or not patient.phone_mobile:
        raise HTTPException(status_code=404,
                            detail="Patient not found or no phone number")

    clinic = db.query(Clinic).filter(
        Clinic.id == current_user.clinic_id
    ).first()

    result = await send_followup_reminder(
        phone         = patient.phone_mobile,
        patient_name  = f"{patient.first_name} {patient.last_name or ''}".strip(),
        doctor_name   = clinic.doctor_name if clinic else "Doctor",
        clinic_name   = clinic.name if clinic else "Clinic",
        clinic_phone  = clinic.phone if clinic else "",
        language      = patient.language_pref or "en",
        followup_type = data.followup_type or "followup_7d"
    )
    return result

@router.post("/send/thankyou/{patient_id}")
async def send_thankyou(
    patient_id:   str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(receptionist_or_doctor)
):
    """
    Send thank-you message after visit.
    Called automatically when visit closes.
    Can also be triggered manually.
    """
    patient = db.query(Patient).filter(
        Patient.id        == patient_id,
        Patient.clinic_id == current_user.clinic_id
    ).first()

    if not patient or not patient.phone_mobile:
        raise HTTPException(status_code=404,
                            detail="Patient not found or no phone number")

    clinic = db.query(Clinic).filter(
        Clinic.id == current_user.clinic_id
    ).first()

    result = await send_thankyou_message(
        phone        = patient.phone_mobile,
        patient_name = f"{patient.first_name} {patient.last_name or ''}".strip(),
        doctor_name  = clinic.doctor_name if clinic else "Doctor",
        clinic_name  = clinic.name if clinic else "Clinic",
        clinic_phone = clinic.phone if clinic else "",
        language     = patient.language_pref or "en"
    )
    return result

@router.post("/send/birthday/{patient_id}")
async def send_birthday(
    patient_id:   str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(receptionist_or_doctor)
):
    """Send birthday greeting to patient"""
    patient = db.query(Patient).filter(
        Patient.id        == patient_id,
        Patient.clinic_id == current_user.clinic_id
    ).first()

    if not patient or not patient.phone_mobile:
        raise HTTPException(status_code=404,
                            detail="Patient not found or no phone number")

    clinic = db.query(Clinic).filter(
        Clinic.id == current_user.clinic_id
    ).first()

    result = await send_birthday_message(
        phone        = patient.phone_mobile,
        patient_name = f"{patient.first_name} {patient.last_name or ''}".strip(),
        doctor_name  = clinic.doctor_name if clinic else "Doctor",
        clinic_name  = clinic.name if clinic else "Clinic",
        language     = patient.language_pref or "en"
    )
    return result