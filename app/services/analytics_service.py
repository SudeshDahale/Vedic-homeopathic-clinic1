from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/dashboard")
def get_dashboard(clinic_id: str, db: Session = Depends(get_db)):
    """
    WHY this single endpoint: Doctor opens app, ONE call loads everything.
    Today's revenue, missed patients, follow-ups due, growth %.
    No loading 5 screens — one dashboard, all action items.
    """
    return {
        "daily_revenue":    analytics_service.get_daily_revenue(db, clinic_id),
        "monthly_revenue":  analytics_service.get_monthly_revenue(db, clinic_id),
        "missed_patients":  analytics_service.get_missed_patients(db, clinic_id),
        "retention":        analytics_service.get_retention_rate(db, clinic_id),
        "followups_today":  analytics_service.get_followups_due_today(db, clinic_id),
        "top_patients":     analytics_service.get_top_patients(db, clinic_id, limit=5)
    }

@router.get("/revenue/daily")
def daily_revenue(clinic_id: str, db: Session = Depends(get_db)):
    return analytics_service.get_daily_revenue(db, clinic_id)

@router.get("/revenue/monthly")
def monthly_revenue(clinic_id: str, db: Session = Depends(get_db)):
    return analytics_service.get_monthly_revenue(db, clinic_id)

@router.get("/missed-patients")
def missed_patients(clinic_id: str, db: Session = Depends(get_db)):
    """
    WHY: Shows doctor exactly how much money walked out the door.
    '8 missed patients = ₹4,000 potential loss this week' = doctor acts.
    """
    return analytics_service.get_missed_patients(db, clinic_id)

@router.get("/retention")
def retention(clinic_id: str, db: Session = Depends(get_db)):
    return analytics_service.get_retention_rate(db, clinic_id)

@router.get("/top-patients")
def top_patients(clinic_id: str, limit: int = 10, db: Session = Depends(get_db)):
    return analytics_service.get_top_patients(db, clinic_id, limit)

@router.get("/followups/today")
def followups_today(clinic_id: str, db: Session = Depends(get_db)):
    return analytics_service.get_followups_due_today(db, clinic_id)