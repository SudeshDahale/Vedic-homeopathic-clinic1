from apscheduler.schedulers.background import BackgroundScheduler
from app.database import SessionLocal
from app.services.growth_service import flag_missed_patients
import pytz

IST = pytz.timezone("Asia/Kolkata")

def run_daily_jobs():
    """
    WHY: Runs every day at 9:30 AM IST automatically.
    1. Flags missed patients (so dashboard shows them)
    2. Future: trigger WhatsApp reminders
    """
    db = SessionLocal()
    try:
        # Get all active clinic IDs
        from app.models.clinic import Clinic
        clinics = db.query(Clinic).all()

        for clinic in clinics:
            missed = flag_missed_patients(db, clinic.id)
            print(f"✅ Clinic {clinic.name}: {missed} patients flagged as missed")

    except Exception as e:
        print(f"❌ Cron job error: {e}")
    finally:
        db.close()

def start_scheduler():
    scheduler = BackgroundScheduler(timezone=IST)

    # Run every day at 9:30 AM IST
    scheduler.add_job(
        run_daily_jobs,
        trigger="cron",
        hour=9,
        minute=30,
        id="daily_clinic_jobs"
    )

    scheduler.start()
    print("✅ Reminder scheduler started — runs daily at 9:30 AM IST")
    return scheduler