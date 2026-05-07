from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.models.visit import Visit, PaymentStatus
from app.models.patient import Patient
from app.models.reminder import FollowUp, FollowUpStatus


# ─────────────────────────────────────────────
# DAILY REVENUE
# ─────────────────────────────────────────────
def daily_revenue(db: Session, clinic_id: str):

    today = datetime.utcnow().date()

    revenue = db.query(
        func.sum(Visit.fee)
    ).filter(
        Visit.clinic_id == clinic_id,
        Visit.payment_status == PaymentStatus.PAID,
        func.date(Visit.visit_date) == today
    ).scalar()

    return {
        "date": str(today),
        "revenue": float(revenue or 0)
    }


# ─────────────────────────────────────────────
# MONTHLY REVENUE
# ─────────────────────────────────────────────
def monthly_revenue(db: Session, clinic_id: str):

    now = datetime.utcnow()

    revenue = db.query(
        func.sum(Visit.fee)
    ).filter(
        Visit.clinic_id == clinic_id,
        Visit.payment_status == PaymentStatus.PAID,
        func.extract("month", Visit.visit_date) == now.month,
        func.extract("year", Visit.visit_date) == now.year
    ).scalar()

    return {
        "month": now.strftime("%B"),
        "revenue": float(revenue or 0)
    }


# ─────────────────────────────────────────────
# MISSED PATIENTS
# ─────────────────────────────────────────────
def missed_patients(db: Session, clinic_id: str):

    cutoff = datetime.utcnow() - timedelta(days=30)

    patients = db.query(Patient).filter(
        Patient.clinic_id == clinic_id
    ).all()

    missed = []

    for patient in patients:

        last_visit = db.query(Visit).filter(
            Visit.patient_id == patient.id
        ).order_by(
            Visit.visit_date.desc()
        ).first()

        if last_visit and last_visit.visit_date < cutoff:

            missed.append({
                "patient_id": patient.id,
                "name": f"{patient.first_name} {patient.last_name or ''}".strip(),
                "last_visit": str(last_visit.visit_date.date())
            })

    return {
        "count": len(missed),
        "patients": missed
    }


# ─────────────────────────────────────────────
# RETENTION RATE
# ─────────────────────────────────────────────
def retention_rate(db: Session, clinic_id: str):

    total_patients = db.query(Patient).filter(
        Patient.clinic_id == clinic_id
    ).count()

    returning = db.query(
        Visit.patient_id
    ).filter(
        Visit.clinic_id == clinic_id
    ).distinct().count()

    rate = 0

    if total_patients > 0:
        rate = (returning / total_patients) * 100

    return {
        "total_patients": total_patients,
        "returning_patients": returning,
        "retention_rate": round(rate, 2)
    }


# ─────────────────────────────────────────────
# FOLLOWUPS DUE TODAY
# ─────────────────────────────────────────────
def followups_due_today(db: Session, clinic_id: str):

    today = datetime.utcnow().date()

    followups = db.query(FollowUp).filter(
        FollowUp.clinic_id == clinic_id,
        FollowUp.status == FollowUpStatus.PENDING
    ).all()

    due_today = [
        f for f in followups
        if f.due_date and f.due_date.date() <= today
    ]

    return {
        "date": str(today),
        "count": len(due_today)
    }


# ─────────────────────────────────────────────
# TOP PATIENTS
# ─────────────────────────────────────────────
def top_patients(
    db: Session,
    clinic_id: str,
    limit: int = 5
):

    patients = db.query(Patient).filter(
        Patient.clinic_id == clinic_id
    ).limit(limit).all()

    result = []

    for patient in patients:

        visits = db.query(Visit).filter(
            Visit.patient_id == patient.id
        ).count()

        result.append({
            "patient_id": patient.id,
            "name": f"{patient.first_name} {patient.last_name or ''}".strip(),
            "visits": visits
        })

    return result