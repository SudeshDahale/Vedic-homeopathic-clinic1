from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from app.database import get_db
from app.middleware.auth_middleware import doctor_only, get_current_user
from app.models.visit import Visit
from app.models.patient import Patient
from app.models.reminder import FollowUp, FollowUpStatus
from app.models.queue import Queue
from app.models.user import User
import pytz

IST     = pytz.timezone("Asia/Kolkata")
router  = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/health-score")
def clinic_health_score(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(doctor_only)
):
    """
    Clinic health score 0-100.
    WHY: Single number that tells doctor
    if their clinic is growing or declining.
    Below 60 = urgent action needed.
    """
    clinic_id = current_user.clinic_id
    now       = datetime.now(IST)
    score     = 0
    breakdown = {}

    # 1. Retention rate (max 25 points)
    total    = db.query(func.count(Patient.id)).filter(
        Patient.clinic_id == clinic_id
    ).scalar() or 1
    retained = db.query(func.count(Patient.id)).filter(
        Patient.clinic_id   == clinic_id,
        Patient.total_visits >= 2
    ).scalar() or 0
    retention_rate  = (retained / total) * 100
    retention_score = min(25, int(retention_rate / 4))
    score          += retention_score
    breakdown["retention"] = {
        "score": retention_score, "max": 25,
        "value": f"{retention_rate:.1f}% retention"
    }

    # 2. Follow-up send rate (max 25 points)
    total_fu = db.query(func.count(FollowUp.id)).filter(
        FollowUp.clinic_id == clinic_id
    ).scalar() or 1
    sent_fu  = db.query(func.count(FollowUp.id)).filter(
        FollowUp.clinic_id == clinic_id,
        FollowUp.status    == FollowUpStatus.SENT
    ).scalar() or 0
    fu_rate  = (sent_fu / total_fu) * 100
    fu_score = min(25, int(fu_rate / 4))
    score   += fu_score
    breakdown["followups"] = {
        "score": fu_score, "max": 25,
        "value": f"{fu_rate:.1f}% reminders sent"
    }

    # 3. Revenue growth (max 25 points)
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0)
    if now.month == 1:
        last_month_start = now.replace(year=now.year-1, month=12, day=1)
    else:
        last_month_start = now.replace(month=now.month-1, day=1)
    last_month_end = this_month_start - timedelta(seconds=1)

    this_rev = db.query(func.sum(Visit.fee)).filter(
        Visit.clinic_id  == clinic_id,
        Visit.visit_date >= this_month_start
    ).scalar() or 0
    last_rev = db.query(func.sum(Visit.fee)).filter(
        Visit.clinic_id  == clinic_id,
        Visit.visit_date >= last_month_start,
        Visit.visit_date <= last_month_end
    ).scalar() or 1

    growth = ((float(this_rev) - float(last_rev)) / float(last_rev)) * 100
    rev_score = 25 if growth > 0 else max(0, int(25 + growth / 2))
    score    += rev_score
    breakdown["revenue_growth"] = {
        "score": rev_score, "max": 25,
        "value": f"{growth:+.1f}% vs last month"
    }

    # 4. Active patients (max 25 points)
    # Patients seen in last 30 days
    month_ago      = now - timedelta(days=30)
    active_count   = db.query(func.count(func.distinct(Visit.patient_id))).filter(
        Visit.clinic_id  == clinic_id,
        Visit.visit_date >= month_ago
    ).scalar() or 0
    active_score   = min(25, active_count)
    score         += active_score
    breakdown["active_patients"] = {
        "score": active_score, "max": 25,
        "value": f"{active_count} patients seen this month"
    }

    # Grade
    if score >= 80:
        grade, message = "A", "Excellent! Clinic is growing well."
    elif score >= 60:
        grade, message = "B", "Good. Small improvements needed."
    elif score >= 40:
        grade, message = "C", "Average. Focus on follow-ups."
    else:
        grade, message = "D", "Urgent attention needed."

    return {
        "score":     score,
        "max":       100,
        "grade":     grade,
        "message":   message,
        "breakdown": breakdown
    }

@router.get("/activity/recent")
def recent_activity(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user)
):
    """
    Recent clinic activity feed.
    Shows last 20 actions — visits, payments, registrations.
    """
    clinic_id = current_user.clinic_id
    now       = datetime.now(IST)
    week_ago  = now - timedelta(days=7)

    activities = []

    # Recent visits
    visits = db.query(Visit).filter(
        Visit.clinic_id  == clinic_id,
        Visit.visit_date >= week_ago
    ).order_by(Visit.visit_date.desc()).limit(10).all()

    for v in visits:
        patient = db.query(Patient).filter(
            Patient.id == v.patient_id
        ).first()
        activities.append({
            "type":    "visit",
            "icon":    "🏥",
            "message": f"Visit recorded for {patient.first_name if patient else 'Patient'}",
            "amount":  float(v.fee or 0),
            "time":    v.visit_date.strftime("%d-%m-%Y %H:%M") if v.visit_date else None,
            "color":   "green"
        })

    # Recent registrations
    new_patients = db.query(Patient).filter(
        Patient.clinic_id  == clinic_id,
        Patient.created_at >= week_ago
    ).order_by(Patient.created_at.desc()).limit(5).all()

    for p in new_patients:
        activities.append({
            "type":    "registration",
            "icon":    "👤",
            "message": f"New patient: {p.first_name} {p.last_name or ''}",
            "amount":  None,
            "time":    p.created_at.strftime("%d-%m-%Y %H:%M") if p.created_at else None,
            "color":   "blue"
        })

    # Sort by time
    activities.sort(key=lambda x: x["time"] or "", reverse=True)

    return {
        "activities": activities[:20],
        "period":     "Last 7 days"
    }