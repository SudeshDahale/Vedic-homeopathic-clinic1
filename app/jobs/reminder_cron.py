from apscheduler.schedulers.background import BackgroundScheduler
from app.database import SessionLocal
from app.services.growth_service import flag_missed_patients
from app.services.reminder_service import send_due_reminders
import pytz

IST = pytz.timezone("Asia/Kolkata")

def run_daily_jobs():
    """
    Runs every day at 9:30 AM IST.
    WHY automated:
    1. Flags missed patients → shows on dashboard
    2. Sends due reminders → patients return → revenue
    Zero manual work for doctor or receptionist.
    """
    db = SessionLocal()
    try:
        from app.models.clinic import Clinic
        clinics = db.query(Clinic).all()

        for clinic in clinics:
            print(f"\n🏥 Processing clinic: {clinic.name}")

            # Flag missed patients
            missed = flag_missed_patients(db, clinic.id)
            print(f"   📋 {missed} patients flagged as missed")

            # Send due reminders
            result = send_due_reminders(db, clinic.id)
            print(f"   📱 {result['sent']} reminders sent")
            print(f"   ❌ {result['failed']} reminders failed")

    except Exception as e:
        print(f"❌ Daily job error: {e}")
    finally:
        db.close()

def start_scheduler():
    scheduler = BackgroundScheduler(timezone=IST)

    # Every day 9:30 AM IST
    scheduler.add_job(
        run_daily_jobs,
        trigger = "cron",
        hour    = 9,
        minute  = 30,
        id      = "daily_clinic_jobs"
    )

    scheduler.start()
    print("✅ Scheduler started — runs daily at 9:30 AM IST")
    return scheduler