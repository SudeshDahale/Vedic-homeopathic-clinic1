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

router = APIRouter(
    prefix="/whatsapp",
    tags=["WhatsApp"]
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
# WEBHOOK VERIFICATION
# ─────────────────────────────────────────────────────────────

@router.get("/webhook")
async def verify_webhook(request: Request):
    """
    Meta webhook verification.
    """

    params = request.query_params

    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    verify_token = os.getenv(
        "WHATSAPP_VERIFY_TOKEN",
        "vedic_clinic_webhook_2026"
    )

    if mode == "subscribe" and token == verify_token:
        print("✅ WhatsApp webhook verified")
        return int(challenge)

    raise HTTPException(
        status_code=403,
        detail="Webhook verification failed"
    )


# ─────────────────────────────────────────────────────────────
# RECEIVE WEBHOOK
# ─────────────────────────────────────────────────────────────

@router.post("/webhook")
async def receive_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Receives ALL patient WhatsApp replies.
    Auto-replies based on patient message.
    """

    body = await request.json()

    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        messages = value.get("messages", [])

        for msg in messages:

            phone = msg["from"].replace("91", "", 1)

            text = (
                msg.get("text", {})
                .get("body", "")
                .strip()
                .upper()
            )

            print(f"📩 Patient reply from +91{phone}: {text}")

            # ── Find patient ──────────────────────────

            patient = db.query(Patient).filter(
                Patient.phone_mobile == phone
            ).first()

            # Unknown number
            if not patient:

                await send_text_message(
                    phone,
                    "Thank you for contacting us. "
                    "Please call us directly for assistance."
                )

                continue

            # ── Clinic Info ──────────────────────────

            clinic = db.query(Clinic).filter(
                Clinic.id == patient.clinic_id
            ).first()

            clinic_name = (
                clinic.name if clinic else "our clinic"
            )

            doctor_name = (
                clinic.doctor_name if clinic else "Doctor"
            )

            clinic_phone = (
                clinic.phone if clinic else ""
            )

            language = (
                patient.language_pref or "en"
            )

            # ── Build smart auto reply ───────────────

            reply = _build_auto_reply(
                text=text,
                patient_name=patient.first_name,
                clinic_name=clinic_name,
                doctor_name=doctor_name,
                clinic_phone=clinic_phone,
                language=language
            )

            # ── Send reply ───────────────────────────

            await send_text_message(phone, reply)

            # ── Update followup ──────────────────────

            _update_followup_from_reply(
                db,
                patient.id,
                text
            )

    except Exception as e:
        print(f"Webhook error: {e}")

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

    """
    Smart auto replies for patients.
    """

    # ── Confirmation words ──────────────────────────

    CONFIRM_WORDS = [
        "YES",
        "COMING",
        "OK",
        "OKAY",
        "WILL COME",
        "HA",
        "HAN",
        "HAAN",
        "ZAROOR",
        "AAUNGA",
        "AAUNGI",
        "CONFIRM",
        "CONFIRMED",
        "YEP",
        "YA"
    ]

    # ── Cancellation words ──────────────────────────

    CANCEL_WORDS = [
        "NO",
        "CANCEL",
        "NAHI",
        "NAHIN",
        "CANNOT",
        "CANT",
        "NOT COMING",
        "BUSY",
        "NOPE"
    ]

    # ── Help words ──────────────────────────────────

    HELP_WORDS = [
        "HELP",
        "TIMING",
        "TIME",
        "TIMINGS",
        "WHEN",
        "ADDRESS",
        "WHERE",
        "LOCATION",
        "FEES",
        "FEE",
        "COST",
        "CHARGE",
        "DOCTOR"
    ]

    # ── Thanks words ────────────────────────────────

    THANKS_WORDS = [
        "THANK",
        "THANKS",
        "THANKYOU",
        "SHUKRIYA",
        "DHANYAWAD",
        "DHANYABAD"
    ]

    # ────────────────────────────────────────────────
    # CONFIRM REPLY
    # ────────────────────────────────────────────────

    if any(w in text for w in CONFIRM_WORDS):

        if language == "hi":

            return (
                f"धन्यवाद {patient_name}! "
                f"आपकी visit confirm हो गई है। "
                f"{clinic_name} में आपका स्वागत है। "
                f"सहायता: {clinic_phone}"
            )

        elif language == "mr":

            return (
                f"धन्यवाद {patient_name}! "
                f"तुमची visit confirm झाली आहे. "
                f"{clinic_name} मध्ये तुमचे स्वागत आहे. "
                f"मदतीसाठी call करा: {clinic_phone}"
            )

        else:

            return (
                f"Thank you {patient_name}! "
                f"Your visit is confirmed. "
                f"We look forward to seeing you at "
                f"{clinic_name}. "
                f"Call: {clinic_phone}"
            )

    # ────────────────────────────────────────────────
    # CANCEL REPLY
    # ────────────────────────────────────────────────

    elif any(w in text for w in CANCEL_WORDS):

        if language == "hi":

            return (
                f"कोई बात नहीं {patient_name}। "
                f"जब भी आप ready हों, हम यहाँ हैं। "
                f"Appointment के लिए call करें: "
                f"{clinic_phone}"
            )

        elif language == "mr":

            return (
                f"ठीक आहे {patient_name}. "
                f"तुम्ही तयार असाल तेव्हा संपर्क करा. "
                f"{clinic_phone}"
            )

        else:

            return (
                f"No problem {patient_name}. "
                f"We are here whenever you are ready. "
                f"Please call {clinic_phone} to reschedule."
            )

    # ────────────────────────────────────────────────
    # HELP REPLY
    # ────────────────────────────────────────────────

    elif any(w in text for w in HELP_WORDS):

        if language == "hi":

            return (
                f"नमस्ते {patient_name}!\n\n"
                f"🏥 {clinic_name}\n"
                f"👨‍⚕️ {doctor_name}\n"
                f"⏰ Timing: 10am-2pm | 5pm-9pm\n"
                f"📞 {clinic_phone}"
            )

        elif language == "mr":

            return (
                f"नमस्ते {patient_name}!\n\n"
                f"🏥 {clinic_name}\n"
                f"👨‍⚕️ {doctor_name}\n"
                f"⏰ वेळ: 10am-2pm | 5pm-9pm\n"
                f"📞 {clinic_phone}"
            )

        else:

            return (
                f"Hello {patient_name}!\n\n"
                f"🏥 {clinic_name}\n"
                f"👨‍⚕️ {doctor_name}\n"
                f"⏰ Timings: 10am-2pm | 5pm-9pm\n"
                f"📞 {clinic_phone}"
            )

    # ────────────────────────────────────────────────
    # THANK YOU REPLY
    # ────────────────────────────────────────────────

    elif any(w in text for w in THANKS_WORDS):

        if language == "hi":

            return (
                f"आपका स्वागत है {patient_name}! "
                f"{clinic_name} हमेशा आपकी सेवा में है 🙏"
            )

        elif language == "mr":

            return (
                f"स्वागत आहे {patient_name}! "
                f"{clinic_name} नेहमी तुमच्या सेवेत आहे 🙏"
            )

        else:

            return (
                f"You are welcome {patient_name}! "
                f"{clinic_name} is always here for you 🙏"
            )

    # ────────────────────────────────────────────────
    # DEFAULT REPLY
    # ────────────────────────────────────────────────

    else:

        if language == "hi":

            return (
                f"नमस्ते {patient_name}! "
                f"आपका message मिल गया। "
                f"हमारी team जल्द संपर्क करेगी। "
                f"Call: {clinic_phone}"
            )

        elif language == "mr":

            return (
                f"नमस्ते {patient_name}! "
                f"तुमचा message मिळाला. "
                f"आमची team लवकरच संपर्क करेल. "
                f"Call: {clinic_phone}"
            )

        else:

            return (
                f"Hello {patient_name}! "
                f"We received your message. "
                f"Our team will contact you shortly. "
                f"Call: {clinic_phone}"
            )


# ─────────────────────────────────────────────────────────────
# UPDATE FOLLOWUP STATUS
# ─────────────────────────────────────────────────────────────

def _update_followup_from_reply(
    db,
    patient_id: str,
    text: str
):

    from app.models.reminder import (
        FollowUp,
        FollowUpStatus
    )

    CONFIRM_WORDS = [
        "YES",
        "COMING",
        "OK",
        "OKAY",
        "WILL COME",
        "HA",
        "HAN",
        "HAAN",
        "CONFIRM",
        "CONFIRMED"
    ]

    CANCEL_WORDS = [
        "NO",
        "CANCEL",
        "NAHI",
        "NOT COMING",
        "BUSY"
    ]

    followup = db.query(FollowUp).filter(
        FollowUp.patient_id == patient_id,
        FollowUp.status.in_([
            FollowUpStatus.SENT,
            FollowUpStatus.PENDING
        ])
    ).order_by(
        FollowUp.due_date.desc()
    ).first()

    if not followup:
        return

    if any(w in text for w in CONFIRM_WORDS):

        followup.status = FollowUpStatus.DONE
        followup.response = text

    elif any(w in text for w in CANCEL_WORDS):

        followup.status = FollowUpStatus.SKIPPED
        followup.response = text

    db.commit()


# ─────────────────────────────────────────────────────────────
# SEND CUSTOM MESSAGE
# ─────────────────────────────────────────────────────────────

@router.post("/send/message")
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

        raise HTTPException(
            status_code=404,
            detail="Patient not found or no phone"
        )

    result = await send_text_message(
        patient.phone_mobile,
        data.message
    )

    return result


# ─────────────────────────────────────────────────────────────
# SEND FOLLOWUP REMINDER
# ─────────────────────────────────────────────────────────────

@router.post("/send/reminder")
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

        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    clinic = db.query(Clinic).filter(
        Clinic.id == current_user.clinic_id
    ).first()

    result = await send_followup_reminder(
        phone=patient.phone_mobile,
        patient_name=f"{patient.first_name} "
                     f"{patient.last_name or ''}".strip(),
        doctor_name=clinic.doctor_name if clinic else "Doctor",
        clinic_name=clinic.name if clinic else "Clinic",
        clinic_phone=clinic.phone if clinic else "",
        language=patient.language_pref or "en",
        followup_type=data.followup_type
    )

    return result


# ─────────────────────────────────────────────────────────────
# SEND THANKYOU MESSAGE
# ─────────────────────────────────────────────────────────────

@router.post("/send/thankyou/{patient_id}")
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

        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    clinic = db.query(Clinic).filter(
        Clinic.id == current_user.clinic_id
    ).first()

    result = await send_thankyou_message(
        phone=patient.phone_mobile,
        patient_name=f"{patient.first_name} "
                     f"{patient.last_name or ''}".strip(),
        doctor_name=clinic.doctor_name if clinic else "Doctor",
        clinic_name=clinic.name if clinic else "Clinic",
        clinic_phone=clinic.phone if clinic else "",
        language=patient.language_pref or "en"
    )

    return result


# ─────────────────────────────────────────────────────────────
# SEND BIRTHDAY MESSAGE
# ─────────────────────────────────────────────────────────────

@router.post("/send/birthday/{patient_id}")
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

        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    clinic = db.query(Clinic).filter(
        Clinic.id == current_user.clinic_id
    ).first()

    result = await send_birthday_message(
        phone=patient.phone_mobile,
        patient_name=f"{patient.first_name} "
                     f"{patient.last_name or ''}".strip(),
        doctor_name=clinic.doctor_name if clinic else "Doctor",
        clinic_name=clinic.name if clinic else "Clinic",
        language=patient.language_pref or "en"
    )

    return result