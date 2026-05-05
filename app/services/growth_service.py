from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
from app.models.patient import Patient
from app.models.visit import Visit, VisitType
from app.models.reminder import FollowUp, FollowUpType, Channel
import pytz

IST = pytz.timezone("Asia/Kolkata")

# Follow-up rules per disease type
# WHY: Different diseases need different follow-up timing.
# Acute fever → check in 3 days. Chronic skin → check in 15 days.
FOLLOWUP_RULES = {
    "acute":          [3],
    "acute_fever":    [3, 7],
    "chronic":        [7, 15, 30],
    "chronic_skin":   [15, 30, 90],
    "chronic_joint":  [7, 30, 90],
    "homeopathy":     [7, 15, 30],
    "cardiology":     [30, 180],
    "default":        [7, 15]
}

def schedule_followups(db: Session, visit_id: str, patient_id: str,
                       clinic_id: str, disease_type: str, channel: str = "WHATSAPP"):
    """
    WHY: Auto-scheduling follow-ups means zero manual work.
    After every visit, reminders are automatically queued.
    Doctor doesn't forget, patient doesn't slip away.
    """
    rules     = FOLLOWUP_RULES.get(disease_type, FOLLOWUP_RULES["default"])
    now       = datetime.now(IST)
    created   = []

    for days in rules:
        due_date = now + timedelta(days=days)

        # Map days to FollowUpType
        if days == 3:
            ftype = FollowUpType.THREE_DAY
        elif days == 7:
            ftype = FollowUpType.SEVEN_DAY
        elif days == 15:
            ftype = FollowUpType.FIFTEEN_DAY
        elif days >= 30:
            ftype = FollowUpType.MONTHLY
        else:
            ftype = FollowUpType.CUSTOM

        followup = FollowUp(
            visit_id   = visit_id,
            patient_id = patient_id,
            clinic_id  = clinic_id,
            due_date   = due_date,
            type       = ftype,
            channel    = channel
        )
        db.add(followup)
        created.append({"days": days, "due_date": due_date.strftime("%d-%m-%Y")})

    db.commit()
    return created

def update_patient_stats(db: Session, patient_id: str, fee: float):
    """
    WHY: After every paid visit, update patient's lifetime value.
    This feeds into patient_value_score which identifies VIP patients.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return

    patient.last_visit_date = datetime.now(IST)
    patient.total_visits    = (patient.total_visits or 0) + 1
    patient.total_spent     = float(patient.total_spent or 0) + fee
    patient.is_missed       = False
    patient.missed_since    = None

    # Patient value score = (total_spent * 0.6) + (total_visits * 10 * 0.4)
    # WHY this formula: spending matters more than visit count
    # A patient spending ₹5000 in 5 visits > patient with 10 free visits
    score = (float(patient.total_spent) * 0.6) + (patient.total_visits * 10 * 0.4)
    patient.patient_value_score = round(score, 2)

    db.commit()

def flag_missed_patients(db: Session, clinic_id: str) -> int:
    """
    WHY: Run this daily via cron job.
    If patient's last_visit + expected_followup_days < today = missed.
    Flags them so doctor sees them on dashboard immediately.
    """
    now     = datetime.now(IST)
    flagged = 0

    patients = db.query(Patient).filter(
        and_(
            Patient.clinic_id       == clinic_id,
            Patient.is_active       == True,
            Patient.last_visit_date != None,
            Patient.is_missed       == False
        )
    ).all()

    for p in patients:
        expected_return = p.last_visit_date + timedelta(days=p.expected_followup_days or 7)
        # Add 2 day grace period
        if now > expected_return + timedelta(days=2):
            p.is_missed    = True
            p.missed_since = expected_return
            flagged += 1

    db.commit()
    return flagged