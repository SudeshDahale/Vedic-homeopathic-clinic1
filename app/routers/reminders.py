from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from app.database import get_db
from app.services import reminder_service
from app.middleware.auth_middleware import (
    get_current_user, receptionist_or_doctor
)
from app.models.user import User

router = APIRouter(prefix="/reminders", tags=["Reminders"])

@router.get("/due")
def get_due_reminders(
    target_date:  Optional[date] = Query(
        None,
        description="Date to fetch reminders for. Defaults to today."
    ),
    db:           Session = Depends(get_db),
    current_user: User    = Depends(receptionist_or_doctor)
):
    """
    Get all pending reminders due on a date.
    YOUR EXTERNAL REMINDER APP calls this endpoint daily.
    Returns patient name, phone, language, message — ready to send.
    """
    return {
        "clinic_id": current_user.clinic_id,
        "date":      str(target_date or date.today()),
        "reminders": reminder_service.get_due_reminders(
            db, current_user.clinic_id, target_date
        )
    }

@router.post("/send-today")
def send_todays_reminders(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(receptionist_or_doctor)
):
    """
    Manually trigger today's reminders.
    Cron job calls this automatically at 9:30 AM.
    Receptionist can also trigger manually from dashboard.
    """
    return reminder_service.send_due_reminders(
        db, current_user.clinic_id
    )

@router.put("/{followup_id}/mark-sent")
def mark_sent(
    followup_id:  str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(receptionist_or_doctor)
):
    """
    Mark reminder as sent.
    External reminder app calls this after sending WhatsApp.
    """
    return reminder_service.mark_reminder_sent(db, followup_id)

@router.put("/{followup_id}/mark-done")
def mark_done(
    followup_id:  str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(receptionist_or_doctor)
):
    """Patient confirmed or returned — mark as done"""
    return reminder_service.mark_reminder_done(db, followup_id)

@router.get("/patient/{patient_id}")
def get_patient_reminders(
    patient_id:   str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(receptionist_or_doctor)
):
    """All reminders for a specific patient"""
    from app.models.reminder import FollowUp
    followups = db.query(FollowUp).filter(
        FollowUp.patient_id == patient_id,
        FollowUp.clinic_id  == current_user.clinic_id
    ).order_by(FollowUp.due_date).all()

    return {
        "patient_id": patient_id,
        "total":      len(followups),
        "reminders": [
            {
                "id":       f.id,
                "type":     f.type.value if f.type else None,
                "due_date": f.due_date.strftime("%d-%m-%Y") if f.due_date else None,
                "status":   f.status.value if f.status else None,
                "channel":  f.channel.value if f.channel else None,
                "sent_at":  f.sent_at.strftime("%d-%m-%Y %H:%M") if f.sent_at else None
            }
            for f in followups
        ]
    }