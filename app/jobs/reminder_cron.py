from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from app.database import SessionLocal
from app.config import settings
from app.services.growth_service import flag_missed_patients
from app.services.reminder_service import send_due_reminders
import pytz
import logging

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")

# Prevent duplicate scheduler instances
_scheduler = None


def run_daily_jobs():
    """
    Runs every day at 9:30 AM IST.

    Automated Tasks:
    1. Flags missed patients → appears on dashboard
    2. Sends due reminders → improves patient return rate
    """

    db = SessionLocal()

    try:
        from app.models.clinic import Clinic

        clinics = db.query(Clinic).all()

        logger.info(f"🏥 Starting daily jobs for {len(clinics)} clinics")

        for clinic in clinics:
            logger.info(f"\n🏥 Processing clinic: {clinic.name}")

            try:
                # =========================
                # 1. Flag Missed Patients
                # =========================
                missed = flag_missed_patients(db, clinic.id)

                logger.info(
                    f"📋 {missed} patients flagged as missed"
                )

                # =========================
                # 2. Send Due Reminders
                # =========================
                result = send_due_reminders(db, clinic.id)

                logger.info(
                    f"📱 {result['sent']} reminders sent"
                )

                logger.info(
                    f"❌ {result['failed']} reminders failed"
                )

            except Exception as clinic_error:
                logger.error(
                    f"❌ Error processing clinic {clinic.name}: {clinic_error}"
                )

        logger.info("✅ Daily jobs completed successfully")

    except Exception as e:
        logger.error(f"❌ Daily scheduler job failed: {e}")

    finally:
        db.close()


def start_scheduler():
    """
    Starts APScheduler with:
    - Persistent jobs in Supabase PostgreSQL
    - IST timezone support
    - Restart-safe scheduling
    """

    global _scheduler

    # Prevent duplicate scheduler on reload/restart
    if _scheduler is not None:
        logger.info("⚠️ Scheduler already running — skipping")
        return _scheduler

    try:
        # ======================================
        # Persistent Job Store (Supabase DB)
        # ======================================
        jobstores = {
            "default": SQLAlchemyJobStore(
                url=settings.DATABASE_URL
            )
        }

        # ======================================
        # Create Scheduler
        # ======================================
        _scheduler = BackgroundScheduler(
            jobstores=jobstores,
            timezone=IST
        )

        # ======================================
        # Daily 9:30 AM IST Job
        # ======================================
        _scheduler.add_job(
            func=run_daily_jobs,
            trigger="cron",
            hour=9,
            minute=30,
            id="daily_clinic_jobs",
            name="Daily Clinic Reminder Jobs",
            replace_existing=True,     # prevents duplicates
            misfire_grace_time=3600    # run within 1hr if server was down
        )

        # ======================================
        # Start Scheduler
        # ======================================
        _scheduler.start()

        logger.info(
            "✅ Scheduler started — runs daily at 9:30 AM IST"
        )

        return _scheduler

    except Exception as e:
        logger.error(f"❌ Failed to start scheduler: {e}")
        raise