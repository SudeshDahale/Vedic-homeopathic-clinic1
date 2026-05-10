import logging
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from app.models.reminder import FollowUp, FollowUpStatus, FollowUpType
from app.models.patient import Patient
from app.models.clinic import Clinic
from app.services.notification_service import (
    get_template, fill_template, send_notification
)
import pytz

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")

# Max days back to send overdue reminders
# Prevents message flood if server was down for days
OVERDUE_CUTOFF_DAYS = 1


def get_template_key(followup_type: FollowUpType) -> str:
    mapping = {
        FollowUpType.THREE_DAY:   "followup_3d",
        FollowUpType.SEVEN_DAY:   "followup_7d",
        FollowUpType.FIFTEEN_DAY: "followup_15d",
        FollowUpType.MONTHLY:     "followup_monthly",
        FollowUpType.CUSTOM:      "followup_7d",
    }
    return mapping.get(followup_type, "followup_7d")


# =====================================================
# GET DUE REMINDERS
# =====================================================

def get_due_reminders(
    db: Session,
    clinic_id: str,
    target_date: date = None
) -> list:
    """
    FIX 1: joinedload eliminates N+1 query problem.
    FIX 2: Overdue cutoff — only send today's and yesterday's max.
            Prevents patient message flood after server downtime.
    FIX 3: Opt-out check — skip patients who replied STOP.
    """
    if not target_date:
        target_date = datetime.now(IST).date()

    # Overdue cutoff: don't send reminders older than 1 day
    cutoff_date = target_date - timedelta(days=OVERDUE_CUTOFF_DAYS)

    # FIX: single query with JOIN — no more per-row patient/clinic fetches
    followups = (
        db.query(FollowUp)
        .options(
            joinedload(FollowUp.patient),   # JOIN patients
            joinedload(FollowUp.visit)      # JOIN visits (for clinic)
        )
        .filter(
            and_(
                FollowUp.clinic_id == clinic_id,
                FollowUp.status    == FollowUpStatus.PENDING,
                FollowUp.due_date  >= datetime(
                    cutoff_date.year,
                    cutoff_date.month,
                    cutoff_date.day
                ),
                FollowUp.due_date  <= datetime(
                    target_date.year,
                    target_date.month,
                    target_date.day,
                    23, 59, 59
                )
            )
        )
        .all()
    )

    # Fetch clinic once — not per reminder
    clinic = db.query(Clinic).filter(
        Clinic.id == clinic_id
    ).first()

    result = []
    for f in followups:
        patient = f.patient
        if not patient:
            logger.warning(f"Reminder {f.id} has no patient — skipping")
            continue

        # FIX: respect WhatsApp opt-out
        if getattr(patient, "whatsapp_opted_out", False):
            logger.info(
                f"Patient {patient.id} opted out — skipping reminder {f.id}"
            )
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
            "followup_id":  f.id,
            "patient_id":   patient.id,
            "patient_name": f"{patient.first_name} {patient.last_name or ''}".strip(),
            "phone":        patient.phone_mobile,
            "language":     language,
            "channel":      f.channel.value if f.channel else "WHATSAPP",
            "type":         f.type.value if f.type else None,
            "due_date":     f.due_date.strftime("%d-%m-%Y") if f.due_date else None,
            "message":      message,
            "template_key": template_key
        })

    return result


# =====================================================
# SEND DUE REMINDERS
# =====================================================

def send_due_reminders(db: Session, clinic_id: str) -> dict:
    """
    FIX: WhatsApp is async — run in a new event loop.
    Called from APScheduler background thread which has no loop.
    """
    import asyncio
    from app.services.whatsapp import send_text_message

    due     = get_due_reminders(db, clinic_id)
    sent    = 0
    failed  = 0
    skipped = 0
    results = []

    # One event loop for all sends in this clinic's batch
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        for reminder in due:
            phone = reminder.get("phone", "")

            if not phone:
                logger.warning(
                    f"No phone for patient {reminder['patient_id']} — skipping"
                )
                skipped += 1
                continue

            try:
                # FIX: properly await async WhatsApp call
                result = loop.run_until_complete(
                    send_text_message(phone, reminder["message"])
                )
            except Exception as e:
                logger.error(
                    f"WhatsApp send error for {reminder['followup_id']}: {e}"
                )
                result = {"status": "failed", "error": str(e)}

            # Update DB status + store message_id
            followup = db.query(FollowUp).filter(
                FollowUp.id == reminder["followup_id"]
            ).first()

            if followup:
                if result.get("status") in ("sent", "mocked"):
                    followup.status     = FollowUpStatus.SENT
                    followup.sent_at    = datetime.now(IST)
                    # FIX: store message_id for delivery audit
                    followup.response   = result.get("message_id", "")
                    sent += 1
                else:
                    followup.status   = FollowUpStatus.FAILED
                    followup.response = result.get("error", "unknown")
                    failed += 1

                db.commit()

            results.append({
                "patient": reminder["patient_name"],
                "phone":   phone,
                "status":  result.get("status"),
                "channel": reminder["channel"]
            })

    finally:
        loop.close()

    logger.info(
        f"Reminders done: clinic={clinic_id} "
        f"sent={sent} failed={failed} skipped={skipped}"
    )

    return {
        "date":      datetime.now(IST).strftime("%d-%m-%Y"),
        "total_due": len(due),
        "sent":      sent,
        "failed":    failed,
        "skipped":   skipped,
        "results":   results
    }


# =====================================================
# MARK REMINDER SENT (manual)
# =====================================================

def mark_reminder_sent(
    db: Session,
    followup_id: str,
    clinic_id: str      # FIX: added — was missing tenant check
) -> dict:

    followup = db.query(FollowUp).filter(
        FollowUp.id        == followup_id,
        FollowUp.clinic_id == clinic_id     # tenant lock
    ).first()

    if not followup:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Reminder not found")

    followup.status  = FollowUpStatus.SENT
    followup.sent_at = datetime.now(IST)
    db.commit()

    return {"message": "Marked as sent", "followup_id": followup_id}


# =====================================================
# MARK REMINDER DONE
# =====================================================

def mark_reminder_done(
    db: Session,
    followup_id: str,
    clinic_id: str      # FIX: added — was missing tenant check
) -> dict:

    followup = db.query(FollowUp).filter(
        FollowUp.id        == followup_id,
        FollowUp.clinic_id == clinic_id     # tenant lock
    ).first()

    if not followup:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Reminder not found")

    followup.status = FollowUpStatus.DONE
    db.commit()

    return {"message": "Marked as done", "followup_id": followup_id}