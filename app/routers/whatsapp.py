from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import PlainTextResponse
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


# ── Webhook router — handles Meta callbacks ────────────────────────────────────
# URL: /webhooks/whatsapp  (GET = verify, POST = receive messages)
router = APIRouter(
    prefix="/webhooks",
    tags=["WhatsApp Webhooks"]
)

# ── Send router — handles outbound messages from dashboard ────────────────────
# URL: /whatsapp/send/...
send_router = APIRouter(
    prefix="/whatsapp",
    tags=["WhatsApp Send"]
)


# ─────────────────────────────────────────────────────────────
# REQUEST SCHEMAS
# ─────────────────────────────────────────────────────────────

class SendMessageRequest(BaseModel):
    patient_id: str
    message: str


class SendReminderRequest(BaseModel):
    patient_id: str
    followup_type: Optional[str] = "followup_7d"


# ─────────────────────────────────────────────────────────────
# WEBHOOK VERIFICATION  (GET /webhooks/whatsapp)
# Meta calls this once to verify your endpoint is real.
# Must return hub.challenge as plain integer.
# ─────────────────────────────────────────────────────────────

@router.get("/whatsapp")
async def verify_webhook(request: Request):
    """
    Meta webhook verification endpoint.
    GET /webhooks/whatsapp?hub.mode=subscribe&hub.challenge=XXX&hub.verify_token=YYY
    Returns the challenge number as plain text.
    """
    params = request.query_params

    mode      = params.get("hub.mode")
    token     = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    verify_token = os.getenv(
        "WHATSAPP_VERIFY_TOKEN",
        "vennova_webhook_verify_2026"
    )

    print(f"🔔 Webhook verify attempt | mode={mode} token={token} challenge={challenge}")
    print(f"🔑 Expected token: {verify_token}")

    if mode == "subscribe" and token == verify_token:
        print("✅ WhatsApp webhook verified successfully")
        # Must return challenge as plain integer text — not JSON
        return PlainTextResponse(content=str(challenge), status_code=200)

    print("❌ Webhook verification failed — token mismatch")
    raise HTTPException(status_code=403, detail="Webhook verification failed")


# ─────────────────────────────────────────────────────────────
# RECEIVE WEBHOOK  (POST /webhooks/whatsapp)
# Meta sends all incoming patient messages here.
# ─────────────────────────────────────────────────────────────

@router.post("/whatsapp")
async def receive_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Receives ALL patient WhatsApp replies.
    Auto-replies based on patient message in their language.
    """
    body = await request.json()

    try:
        entry    = body["entry"][0]
        changes  = entry["changes"][0]
        value    = changes["value"]
        messages = value.get("messages", [])

        for msg in messages:
            phone = msg["from"].replace("91", "", 1)
            text  = msg.get("text", {}).get("body", "").strip().upper()

            print(f"📩 Patient reply from +91{phone}: {text}")

            patient = db.query(Patient).filter(
                Patient.phone_mobile == phone
            ).first()

            if not patient:
                await send_text_message(
                    phone,
                    "Thank you for contacting us. "
                    "Please call us directly for assistance."
                )
                continue

            clinic = db.query(Clinic).filter(
                Clinic.id == patient.clinic_id
            ).first()

            clinic_name  = clinic.name if clinic else "our clinic"
            doctor_name  = clinic.doctor_name if clinic else "Doctor"
            clinic_phone = clinic.phone if clinic else ""
            language     = patient.language_pref or "en"

            reply = _build_auto_reply(
                text         = text,
                patient_name = patient.first_name,
                clinic_name  = clinic_name,
                doctor_name  = doctor_name,
                clinic_phone = clinic_phone,
                language     = language
            )

            await send_text_message(phone, reply)
            _update_followup_from_reply(db, patient.id, text)

    except Exception as e:
        print(f"Webhook error: {e}")

    # Always return 200 to Meta — otherwise Meta retries endlessly
    return {"status": "ok"}


# ─────────────────────────────────────────────────────────────
# SMART AUTO REPLY SYSTEM
# ─────────────────────────────────────────────────────────────

def _build_auto_reply(
    text: str,
    patient_name: str,
    clinic_name: str,
    doctor_name: str,
    clinic_phone: str,
    language: str
) -> str:

    CONFIRM_WORDS = [
        "YES", "COMING", "OK", "OKAY", "WILL COME",
        "HA", "HAN", "HAAN", "ZAROOR", "AAUNGA",
        "AAUNGI", "CONFIRM", "CONFIRMED", "YEP", "YA"
    ]

    CANCEL_WORDS = [
        "NO", "CANCEL", "NAHI", "NAHIN", "CANNOT",
        "CANT", "NOT COMING", "BUSY", "NOPE"
    ]

    HELP_WORDS = [
        "HELP", "TIMING", "TIME", "TIMINGS", "WHEN",
        "ADDRESS", "WHERE", "LOCATION", "FEES", "FEE",
        "COST", "CHARGE", "DOCTOR"
    ]

    THANKS_WORDS = [
        "THANK", "THANKS", "THANKYOU", "SHUKRIYA",
        "DHANYAWAD", "DHANYABAD"
    ]

    if any(w in text for w in CONFIRM_WORDS):
        if language == "hi":
            return (
                f"धन्यवाद {patient_name}! आपकी visit confirm हो गई है। "
                f"{clinic_name} में आपका स्वागत है। सहायता: {clinic_phone}"
            )
        elif language == "mr":
            return (
                f"धन्यवाद {patient_name}! तुमची visit confirm झाली आहे. "
                f"{clinic_name} मध्ये तुमचे स्वागत आहे. Call: {clinic_phone}"
            )
        else:
            return (
                f"Thank you {patient_name}! Your visit is confirmed. "
                f"We look forward to seeing you at {clinic_name}. "
                f"Call: {clinic_phone}"
            )

    elif any(w in text for w in CANCEL_WORDS):
        if language == "hi":
            return (
                f"कोई बात नहीं {patient_name}। जब भी ready हों call करें: {clinic_phone}"
            )
        elif language == "mr":
            return (
                f"ठीक आहे {patient_name}. तयार असाल तेव्हा call करा: {clinic_phone}"
            )
        else:
            return (
                f"No problem {patient_name}. Call {clinic_phone} to reschedule."
            )

    elif any(w in text for w in HELP_WORDS):
        if language == "hi":
            return (
                f"नमस्ते {patient_name}!\n\n"
                f"🏥 {clinic_name}\n👨‍⚕️ {doctor_name}\n"
                f"⏰ 10am-2pm | 5pm-9pm\n📞 {clinic_phone}"
            )
        elif language == "mr":
            return (
                f"नमस्ते {patient_name}!\n\n"
                f"🏥 {clinic_name}\n👨‍⚕️ {doctor_name}\n"
                f"⏰ 10am-2pm | 5pm-9pm\n📞 {clinic_phone}"
            )
        else:
            return (
                f"Hello {patient_name}!\n\n"
                f"🏥 {clinic_name}\n👨‍⚕️ {doctor_name}\n"
                f"⏰ Timings: 10am-2pm | 5pm-9pm\n📞 {clinic_phone}"
            )

    elif any(w in text for w in THANKS_WORDS):
        if language == "hi":
            return f"आपका स्वागत है {patient_name}! {clinic_name} हमेशा आपकी सेवा में है 🙏"
        elif language == "mr":
            return f"स्वागत आहे {patient_name}! {clinic_name} नेहमी तुमच्या सेवेत आहे 🙏"
        else:
            return f"You are welcome {patient_name}! {clinic_name} is always here for you 🙏"

    else:
        if language == "hi":
            return (
                f"नमस्ते {patient_name}! आपका message मिल गया। "
                f"हमारी team जल्द संपर्क करेगी। Call: {clinic_phone}"
            )
        elif language == "mr":
            return (
                f"नमस्ते {patient_name}! तुमचा message मिळाला. "
                f"आमची team लवकरच संपर्क करेल. Call: {clinic_phone}"
            )
        else:
            return (
                f"Hello {patient_name}! We received your message. "
                f"Our team will contact you shortly. Call: {clinic_phone}"
            )


# ─────────────────────────────────────────────────────────────
# UPDATE FOLLOWUP STATUS FROM REPLY
# ─────────────────────────────────────────────────────────────

def _update_followup_from_reply(db, patient_id: str, text: str):

    from app.models.reminder import FollowUp, FollowUpStatus

    CONFIRM_WORDS = ["YES", "COMING", "OK", "OKAY", "WILL COME", "HA", "HAN", "HAAN", "CONFIRM", "CONFIRMED"]
    CANCEL_WORDS  = ["NO", "CANCEL", "NAHI", "NOT COMING", "BUSY"]

    followup = db.query(FollowUp).filter(
        FollowUp.patient_id == patient_id,
        FollowUp.status.in_([FollowUpStatus.SENT, FollowUpStatus.PENDING])
    ).order_by(FollowUp.due_date.desc()).first()

    if not followup:
        return

    if any(w in text for w in CONFIRM_WORDS):
        followup.status   = FollowUpStatus.DONE
        followup.response = text
    elif any(w in text for w in CANCEL_WORDS):
        followup.status   = FollowUpStatus.SKIPPED
        followup.response = text

    db.commit()


# ─────────────────────────────────────────────────────────────
# SEND ROUTES  (all use send_router → /whatsapp/send/...)
# ─────────────────────────────────────────────────────────────

@send_router.post("/send/message")
async def send_message(
    data: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(receptionist_or_doctor)
):
    patient = db.query(Patient).filter(
        Patient.id == data.patient_id,
        Patient.clinic_id == current_user.clinic_id
    ).first()

    if not patient or not patient.phone_mobile:
        raise HTTPException(status_code=404, detail="Patient not found or no phone")

    return await send_text_message(patient.phone_mobile, data.message)


@send_router.post("/send/reminder")
async def send_reminder(
    data: SendReminderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(receptionist_or_doctor)
):
    patient = db.query(Patient).filter(
        Patient.id == data.patient_id,
        Patient.clinic_id == current_user.clinic_id
    ).first()

    if not patient or not patient.phone_mobile:
        raise HTTPException(status_code=404, detail="Patient not found")

    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    return await send_followup_reminder(
        phone         = patient.phone_mobile,
        patient_name  = f"{patient.first_name} {patient.last_name or ''}".strip(),
        doctor_name   = clinic.doctor_name if clinic else "Doctor",
        clinic_name   = clinic.name if clinic else "Clinic",
        clinic_phone  = clinic.phone if clinic else "",
        language      = patient.language_pref or "en",
        followup_type = data.followup_type
    )


@send_router.post("/send/thankyou/{patient_id}")
async def send_thankyou(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(receptionist_or_doctor)
):
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.clinic_id == current_user.clinic_id
    ).first()

    if not patient or not patient.phone_mobile:
        raise HTTPException(status_code=404, detail="Patient not found")

    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    return await send_thankyou_message(
        phone        = patient.phone_mobile,
        patient_name = f"{patient.first_name} {patient.last_name or ''}".strip(),
        doctor_name  = clinic.doctor_name if clinic else "Doctor",
        clinic_name  = clinic.name if clinic else "Clinic",
        clinic_phone = clinic.phone if clinic else "",
        language     = patient.language_pref or "en"
    )


@send_router.post("/send/birthday/{patient_id}")
async def send_birthday(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(receptionist_or_doctor)
):
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.clinic_id == current_user.clinic_id
    ).first()

    if not patient or not patient.phone_mobile:
        raise HTTPException(status_code=404, detail="Patient not found")

    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    return await send_birthday_message(
        phone        = patient.phone_mobile,
        patient_name = f"{patient.first_name} {patient.last_name or ''}".strip(),
        doctor_name  = clinic.doctor_name if clinic else "Doctor",
        clinic_name  = clinic.name if clinic else "Clinic",
        language     = patient.language_pref or "en"
    )