from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, date
from app.models.reminder import FollowUp, FollowUpStatus, FollowUpType
from app.models.patient import Patient
from app.models.clinic import Clinic
from app.services.notification_service import (
    get_template, fill_template, send_notification
)
import pytz

IST = pytz.timezone("Asia/Kolkata")

def get_template_key(followup_type: FollowUpType) -> str:
    """Map follow-up type to template key"""
    mapping = {
        FollowUpType.THREE_DAY:   "followup_3d",
        FollowUpType.SEVEN_DAY:   "followup_7d",
        FollowUpType.FIFTEEN_DAY: "followup_15d",
        FollowUpType.MONTHLY:     "followup_monthly",
        FollowUpType.CUSTOM:      "followup_7d",
    }
    return mapping.get(followup_type, "followup_7d")

def get_due_reminders(db: Session, clinic_id: str,
                      target_date: date = None) -> list:
    """
    Get all pending reminders due on target date.
    WHY: Your external reminder app calls this endpoint.
    Returns structured data ready to send.
    """
    if not target_date:
        target_date = datetime.now(IST).date()

    followups = db.query(FollowUp).filter(
        and_(
            FollowUp.clinic_id == clinic_id,
            FollowUp.status    == FollowUpStatus.PENDING,
        )
    ).all()

    # Filter by date
    due = [f for f in followups
           if f.due_date and f.due_date.date() <= target_date]

    result = []
    for f in due:
        patient = db.query(Patient).filter(
            Patient.id == f.patient_id
        ).first()
        clinic = db.query(Clinic).filter(
            Clinic.id == clinic_id
        ).first()

        if not patient:
            continue

        template_key = get_template_key(f.type)
        language     = patient.language_pref or "en"
        template     = get_template(template_key, language)
        message      = fill_template(
            template     = template,
            patient_name = f"{patient.first_name} {patient.last_name or ''}".strip(),
            doctor_name  = clinic.doctor_name if clinic else "Doctor",
            clinic_name  = clinic.name if clinic else "Clinic",
            clinic_phone = clinic.phone if clinic else ""
        )

        result.append({
            "followup_id":   f.id,
            "patient_id":    patient.id,
            "patient_name":  f"{patient.first_name} {patient.last_name or ''}".strip(),
            "phone":         patient.phone_mobile,
            "language":      language,
            "channel":       f.channel.value if f.channel else "WHATSAPP",
            "type":          f.type.value if f.type else None,
            "due_date":      f.due_date.strftime("%d-%m-%Y") if f.due_date else None,
            "message":       message,
            "template_key":  template_key
        })

    return result

def send_due_reminders(db: Session, clinic_id: str) -> dict:
    """
    Fetch due reminders and send them all.
    Called by cron job every day at 9:30 AM.
    WHY automated: Zero manual work for doctor or receptionist.
    Patient gets reminded = comes back = revenue.
    """
    due = get_due_reminders(db, clinic_id)

    sent    = 0
    failed  = 0
    results = []

    for reminder in due:
        # Send via correct channel
        result = send_notification(
            channel = reminder["channel"],
            phone   = reminder["phone"] or "",
            message = reminder["message"]
        )

        # Update status in database
        followup = db.query(FollowUp).filter(
            FollowUp.id == reminder["followup_id"]
        ).first()

        if followup:
            if result["status"] in ["sent", "mocked"]:
                followup.status  = FollowUpStatus.SENT
                followup.sent_at = datetime.now(IST)
                sent += 1
            else:
                followup.status = FollowUpStatus.FAILED
                failed += 1
            db.commit()

        results.append({
            "patient": reminder["patient_name"],
            "phone":   reminder["phone"],
            "status":  result["status"],
            "channel": reminder["channel"]
        })

    return {
        "date":         datetime.now(IST).strftime("%d-%m-%Y"),
        "total_due":    len(due),
        "sent":         sent,
        "failed":       failed,
        "results":      results
    }

def mark_reminder_sent(db: Session, followup_id: str) -> dict:
    """
    Mark reminder as sent manually.
    Used by external reminder app after it sends the message.
    """
    followup = db.query(FollowUp).filter(
        FollowUp.id == followup_id
    ).first()

    if not followup:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Reminder not found")

    followup.status  = FollowUpStatus.SENT
    followup.sent_at = datetime.now(IST)
    db.commit()

    return {"message": "Marked as sent", "followup_id": followup_id}

def mark_reminder_done(db: Session, followup_id: str) -> dict:
    """Patient confirmed they are coming / came back"""
    followup = db.query(FollowUp).filter(
        FollowUp.id == followup_id
    ).first()

    if not followup:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Reminder not found")

    followup.status = FollowUpStatus.DONE
    db.commit()

    return {"message": "Marked as done", "followup_id": followup_id}