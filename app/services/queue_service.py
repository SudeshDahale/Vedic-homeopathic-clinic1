from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from fastapi import HTTPException, status
from datetime import datetime, date, timedelta
from app.models.queue import Queue, QueueStatus, VisitTypeQueue
from app.models.patient import Patient
from app.schemas.queue import QueueAdd
import pytz

IST = pytz.timezone("Asia/Kolkata")

def now_ist():
    return datetime.now(IST)

def get_next_token(db: Session, clinic_id: str) -> int:
    """
    Get next token number for today.
    Resets to 1 every day automatically.
    WHY daily reset: Token 1-50 per day is readable.
    Token 1523 is confusing.
    """
    today = now_ist().date()
    max_token = db.query(func.max(Queue.token_number)).filter(
        and_(
            Queue.clinic_id  == clinic_id,
            Queue.queue_date == today
        )
    ).scalar()
    return (max_token or 0) + 1

def add_to_queue(db: Session, data: QueueAdd,
                 clinic_id: str) -> dict:
    """
    Add patient to today's queue.
    Receptionist does this when patient arrives at reception.
    """
    # Check patient exists
    patient = db.query(Patient).filter(
        Patient.id == data.patient_id
    ).first()
    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # Check not already in queue today
    today = now_ist().date()
    existing = db.query(Queue).filter(
        and_(
            Queue.clinic_id  == clinic_id,
            Queue.patient_id == data.patient_id,
            Queue.queue_date == today,
            Queue.status.in_([
                QueueStatus.WAITING,
                QueueStatus.IN_PROGRESS
            ])
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Patient already in queue. Token: {existing.token_number}"
        )

    token = get_next_token(db, clinic_id)

    entry = Queue(
        clinic_id     = clinic_id,
        patient_id    = data.patient_id,
        token_number  = token,
        queue_date    = today,
        visit_type    = VisitTypeQueue.WALKIN if data.visit_type == "WALKIN" else VisitTypeQueue.APPOINTMENT,
        priority      = data.priority or 0,
        notes         = data.notes,
        check_in_time = now_ist()
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "message":      "Added to queue",
        "token_number": token,
        "patient_name": f"{patient.first_name} {patient.last_name or ''}".strip(),
        "queue_id":     entry.id,
        "position":     _get_position(db, clinic_id, token)
    }

def get_todays_queue(db: Session, clinic_id: str) -> list:
    """
    Full queue for today — ordered by priority then token.
    WHY priority first: Urgent patients (elderly, children) go first.
    """
    today = now_ist().date()

    entries = db.query(Queue).filter(
        and_(
            Queue.clinic_id  == clinic_id,
            Queue.queue_date == today
        )
    ).order_by(
        Queue.priority.desc(),
        Queue.token_number.asc()
    ).all()

    result = []
    for e in entries:
        patient = db.query(Patient).filter(
            Patient.id == e.patient_id
        ).first()

        wait_mins = None
        if e.check_in_time and e.status == QueueStatus.WAITING:
            diff      = now_ist() - e.check_in_time.replace(tzinfo=IST)
            wait_mins = int(diff.total_seconds() / 60)

        result.append({
            "id":            e.id,
            "token_number":  e.token_number,
            "patient_id":    e.patient_id,
            "patient_name":  f"{patient.first_name} {patient.last_name or ''}".strip() if patient else "Unknown",
            "patient_phone": patient.phone_mobile if patient else None,
            "status":        e.status.value,
            "visit_type":    e.visit_type.value if e.visit_type else "WALKIN",
            "priority":      e.priority,
            "check_in_time": e.check_in_time.strftime("%H:%M") if e.check_in_time else None,
            "called_time":   e.called_time.strftime("%H:%M") if e.called_time else None,
            "wait_minutes":  wait_mins,
            "notes":         e.notes
        })

    return result

def get_current_patient(db: Session, clinic_id: str) -> dict:
    """Who is with the doctor right now"""
    today = now_ist().date()

    current = db.query(Queue).filter(
        and_(
            Queue.clinic_id  == clinic_id,
            Queue.queue_date == today,
            Queue.status     == QueueStatus.IN_PROGRESS
        )
    ).first()

    if not current:
        return {"message": "No patient with doctor right now"}

    patient = db.query(Patient).filter(
        Patient.id == current.patient_id
    ).first()

    return {
        "token_number":  current.token_number,
        "patient_id":    current.patient_id,
        "patient_name":  f"{patient.first_name} {patient.last_name or ''}".strip() if patient else "Unknown",
        "patient_phone": patient.phone_mobile if patient else None,
        "start_time":    current.start_time.strftime("%H:%M") if current.start_time else None,
        "queue_id":      current.id
    }

def call_next(db: Session, clinic_id: str) -> dict:
    """
    Doctor calls next patient.
    WHY: Marks current as completed, next waiting becomes in_progress.
    Receptionist screen updates — calls patient's name.
    """
    today = now_ist().date()

    # Complete current in-progress if any
    current = db.query(Queue).filter(
        and_(
            Queue.clinic_id  == clinic_id,
            Queue.queue_date == today,
            Queue.status     == QueueStatus.IN_TREATMENT
        )
    ).first()

    if current:
        current.status   = QueueStatus.COMPLETED
        current.end_time = now_ist()
        db.commit()

    # Get next waiting — priority first, then token order
    next_patient = db.query(Queue).filter(
        and_(
            Queue.clinic_id  == clinic_id,
            Queue.queue_date == today,
            Queue.status     == QueueStatus.WAITING
        )
    ).order_by(
        Queue.priority.desc(),
        Queue.token_number.asc()
    ).first()

    if not next_patient:
        return {"message": "Queue is empty — no more patients waiting"}

    next_patient.status      = QueueStatus.IN_PROGRESS
    next_patient.called_time = now_ist()
    next_patient.start_time  = now_ist()
    db.commit()

    patient = db.query(Patient).filter(
        Patient.id == next_patient.patient_id
    ).first()

    return {
        "message":       "Next patient called",
        "token_number":  next_patient.token_number,
        "patient_name":  f"{patient.first_name} {patient.last_name or ''}".strip() if patient else "Unknown",
        "patient_id":    next_patient.patient_id,
        "queue_id":      next_patient.id
    }

def mark_no_show(db: Session, queue_id: str,
                 clinic_id: str) -> dict:
    """Patient didn't show up — mark as no-show"""
    entry = _get_entry(db, queue_id, clinic_id)
    entry.status = QueueStatus.NO_SHOW
    db.commit()
    return {"message": "Marked as no-show", "queue_id": queue_id}

def remove_from_queue(db: Session, queue_id: str,
                      clinic_id: str) -> dict:
    """Remove patient from queue"""
    entry = _get_entry(db, queue_id, clinic_id)
    db.delete(entry)
    db.commit()
    return {"message": "Removed from queue"}

def get_queue_stats(db: Session, clinic_id: str) -> dict:
    """Today's queue statistics"""
    today = now_ist().date()

    entries = db.query(Queue).filter(
        and_(
            Queue.clinic_id  == clinic_id,
            Queue.queue_date == today
        )
    ).all()

    waiting     = len([e for e in entries if e.status == QueueStatus.WAITING])
    in_progress = len([e for e in entries if e.status == QueueStatus.IN_PROGRESS])
    completed   = len([e for e in entries if e.status == QueueStatus.COMPLETED])
    no_show     = len([e for e in entries if e.status == QueueStatus.NO_SHOW])

    # Average wait time for completed patients
    wait_times = []
    for e in entries:
        if e.status == QueueStatus.COMPLETED and e.check_in_time and e.start_time:
            diff = e.start_time - e.check_in_time.replace(tzinfo=None)
            wait_times.append(diff.total_seconds() / 60)

    avg_wait = round(sum(wait_times) / max(len(wait_times), 1), 1)

    return {
        "date":          str(today),
        "total_today":   len(entries),
        "waiting":       waiting,
        "in_progress":   in_progress,
        "completed":     completed,
        "no_show":       no_show,
        "avg_wait_mins": avg_wait
    }

# ── Private helper ─────────────────────────────────────
def _get_entry(db: Session, queue_id: str, clinic_id: str) -> Queue:
    entry = db.query(Queue).filter(
        Queue.id        == queue_id,
        Queue.clinic_id == clinic_id
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    return entry

def _get_position(db: Session, clinic_id: str, token: int) -> int:
    today = datetime.now(IST).date()
    waiting = db.query(func.count(Queue.id)).filter(
        and_(
            Queue.clinic_id     == clinic_id,
            Queue.queue_date    == today,
            Queue.status        == QueueStatus.WAITING,
            Queue.token_number  <= token
        )
    ).scalar() or 1
    return waiting